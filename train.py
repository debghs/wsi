"""
Main Training Script for ASTRA
"""

import os
import sys
import argparse
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import Adam
import numpy as np
from tqdm import tqdm
import json
from datetime import datetime

from config import CONFIG
from datasets.wsi_dataset import WSIDataset, collate_fn
from models.encoder import PatchEncoder
from models.mil import ASTRA
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix


def setup_directories():
    """Create necessary directories"""
    os.makedirs(CONFIG['model_save_dir'], exist_ok=True)
    os.makedirs(CONFIG['result_save_dir'], exist_ok=True)
    os.makedirs(CONFIG['figure_save_dir'], exist_ok=True)


def setup_logging(mode, dataset_name):
    """Setup logging directory for current run"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(CONFIG['result_save_dir'], f'{mode}_{dataset_name}_{timestamp}')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def train_epoch(encoder, model, train_loader, optimizer, device, epoch):
    """Train for one epoch"""
    encoder.train()
    model.train()
    
    total_loss = 0
    num_batches = 0
    
    pbar = tqdm(train_loader, desc=f"Epoch {epoch} - Train")
    
    for batch in pbar:
        if batch is None or len(batch) == 0:
            continue
        
        # Handle variable-length batches (MIL)
        for sample in batch:
            patches = sample['patches'].to(device)
            label = torch.tensor([sample['label']], dtype=torch.long, device=device)
            
            # Extract features
            with torch.no_grad():
                features = encoder(patches)
            
            # MIL prediction
            output = model(features)
            logits = output['logits']
            
            # Compute loss
            loss_fn = nn.CrossEntropyLoss()
            loss = loss_fn(logits, label)
            
            # Backprop
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
            
            pbar.set_postfix({'loss': total_loss / num_batches})
    
    avg_loss = total_loss / max(num_batches, 1)
    return avg_loss


@torch.no_grad()
def validate(encoder, model, val_loader, device):
    """Validate model"""
    encoder.eval()
    model.eval()
    
    y_true = []
    y_pred = []
    y_prob = []
    
    pbar = tqdm(val_loader, desc="Validate")
    
    for batch in pbar:
        if batch is None or len(batch) == 0:
            continue
        
        for sample in batch:
            patches = sample['patches'].to(device)
            label = sample['label']
            
            # Extract features
            features = encoder(patches)
            
            # Prediction
            output = model(features)
            logits = output['logits']
            
            prob = torch.softmax(logits, dim=1)[0, 1].item()
            pred = logits.argmax(dim=1).item()
            
            y_true.append(label)
            y_pred.append(pred)
            y_prob.append(prob)
    
    if len(y_true) == 0:
        return 0.0, 0.0, 0.0
    
    acc = accuracy_score(y_true, y_pred)
    auc = roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else 0.0
    
    return acc, auc, np.array(y_true), np.array(y_pred), np.array(y_prob)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='camelyon16',
                       choices=['camelyon16', 'camelyon17', 'tcga'])
    parser.add_argument('--mode', type=str, default='adaptive',
                       choices=['adaptive', 'uniform', 'random'])
    parser.add_argument('--epochs', type=int, default=CONFIG['num_epochs'])
    parser.add_argument('--batch_size', type=int, default=CONFIG['batch_size'])
    parser.add_argument('--lr', type=float, default=CONFIG['learning_rate'])
    parser.add_argument('--seed', type=int, default=CONFIG['seed'])
    parser.add_argument('--cache', action='store_true', help='Cache patches')
    
    args = parser.parse_args()
    
    # Setup
    setup_directories()
    log_dir = setup_logging(args.mode, args.dataset)
    print(f"Logging to: {log_dir}")
    
    # Seed
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    
    # Device
    device = torch.device(CONFIG['device'] if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    # Load dataset
    csv_path = os.path.join(CONFIG['data_root'], args.dataset, 'labels.csv')
    data_root = os.path.join(CONFIG['data_root'], args.dataset)
    
    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        print("Please prepare your dataset first.")
        return
    
    dataset = WSIDataset(
        csv_path=csv_path,
        data_root=data_root,
        mode=args.mode,
        cache=args.cache,
    )
    
    # Split train/val
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(args.seed)
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        collate_fn=collate_fn,
        shuffle=True,
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=1,
        collate_fn=collate_fn,
    )
    
    print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    
    # Models
    encoder = PatchEncoder(
        backbone=CONFIG['backbone'],
        pretrained=CONFIG['pretrained'],
        feature_dim=CONFIG['feature_dim'],
    ).to(device)
    
    model = ASTRA(
        feature_dim=CONFIG['feature_dim'],
        num_classes=CONFIG['num_classes'],
        graph_heads=CONFIG['graph_heads'],
        mil_hidden=CONFIG['mil_hidden'],
    ).to(device)
    
    # Optimizer
    optimizer = Adam(
        list(encoder.parameters()) + list(model.parameters()),
        lr=args.lr,
        weight_decay=CONFIG['weight_decay'],
    )
    
    # Training loop
    best_auc = 0.0
    best_epoch = 0
    
    metrics_history = {
        'train_loss': [],
        'val_acc': [],
        'val_auc': [],
    }
    
    for epoch in range(args.epochs):
        print(f"\n{'='*50}")
        print(f"Epoch {epoch + 1}/{args.epochs}")
        print(f"{'='*50}")
        
        # Train
        train_loss = train_epoch(encoder, model, train_loader, optimizer, device, epoch)
        print(f"Train Loss: {train_loss:.4f}")
        
        # Validate
        val_acc, val_auc, y_true, y_pred, y_prob = validate(encoder, model, val_loader, device)
        print(f"Val Accuracy: {val_acc:.4f}")
        print(f"Val AUC: {val_auc:.4f}")
        
        # Log metrics
        metrics_history['train_loss'].append(train_loss)
        metrics_history['val_acc'].append(val_acc)
        metrics_history['val_auc'].append(val_auc)
        
        # Save best model
        if val_auc > best_auc:
            best_auc = val_auc
            best_epoch = epoch
            
            model_path = os.path.join(log_dir, 'best_model.pth')
            torch.save({
                'encoder': encoder.state_dict(),
                'model': model.state_dict(),
                'epoch': epoch,
                'auc': val_auc,
            }, model_path)
            print(f"Saved best model to {model_path}")
        
        # Save metrics
        metrics_file = os.path.join(log_dir, 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(metrics_history, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"Best AUC: {best_auc:.4f} at epoch {best_epoch}")
    print(f"{'='*50}")
    
    # Save final results
    results = {
        'dataset': args.dataset,
        'mode': args.mode,
        'best_auc': best_auc,
        'best_epoch': best_epoch,
        'final_acc': metrics_history['val_acc'][-1] if metrics_history['val_acc'] else 0.0,
    }
    
    results_file = os.path.join(log_dir, 'results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {results_file}")


if __name__ == '__main__':
    main()
