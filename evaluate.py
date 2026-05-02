"""
Evaluation Script
"""

import os
import argparse
import torch
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
from torch.utils.data import DataLoader
import json

from config import CONFIG
from datasets.wsi_dataset import WSIDataset, collate_fn
from models.encoder import PatchEncoder
from models.mil import ASTRA


@torch.no_grad()
def evaluate(model_path, dataset, device='cuda'):
    """
    Evaluate model on dataset
    
    Args:
        model_path (str): Path to saved model
        dataset (str): Dataset name
        device (str): Device to use
    """
    device = torch.device(device if torch.cuda.is_available() else 'cpu')
    
    # Load dataset
    csv_path = os.path.join(CONFIG['data_root'], dataset, 'labels.csv')
    data_root = os.path.join(CONFIG['data_root'], dataset)
    
    dataset_obj = WSIDataset(
        csv_path=csv_path,
        data_root=data_root,
        mode='adaptive',
    )
    
    loader = DataLoader(
        dataset_obj,
        batch_size=1,
        collate_fn=collate_fn,
    )
    
    # Load models
    encoder = PatchEncoder(
        backbone=CONFIG['backbone'],
        feature_dim=CONFIG['feature_dim'],
    ).to(device)
    
    model = ASTRA(
        feature_dim=CONFIG['feature_dim'],
        num_classes=CONFIG['num_classes'],
    ).to(device)
    
    checkpoint = torch.load(model_path, map_location=device)
    encoder.load_state_dict(checkpoint['encoder'])
    model.load_state_dict(checkpoint['model'])
    
    encoder.eval()
    model.eval()
    
    # Evaluate
    y_true = []
    y_pred = []
    y_prob = []
    
    for batch in loader:
        if batch is None:
            continue
        
        for sample in batch:
            patches = sample['patches'].to(device)
            label = sample['label']
            
            features = encoder(patches)
            output = model(features)
            logits = output['logits']
            
            prob = torch.softmax(logits, dim=1)[0, 1].item()
            pred = logits.argmax(dim=1).item()
            
            y_true.append(label)
            y_pred.append(pred)
            y_prob.append(prob)
    
    # Metrics
    acc = accuracy_score(y_true, y_pred)
    auc = roc_auc_score(y_true, y_prob)
    cm = confusion_matrix(y_true, y_pred)
    
    print(f"Accuracy: {acc:.4f}")
    print(f"AUC: {auc:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    
    return {
        'accuracy': acc,
        'auc': auc,
        'confusion_matrix': cm.tolist(),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, required=True, help='Path to saved model')
    parser.add_argument('--dataset', type=str, default='camelyon16')
    parser.add_argument('--device', type=str, default='cuda')
    
    args = parser.parse_args()
    
    results = evaluate(args.model, args.dataset, args.device)
    print("\nEvaluation complete!")
