#!/usr/bin/env python3
"""
Simple trainer for DHMC PNG dataset - direct CNN without patching
Tests adaptive vs uniform feature extraction on real tissue images
"""

import os
import sys
import argparse
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import json
import time
from datetime import datetime
from sklearn.model_selection import train_test_split
import cv2
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))


class SimpleRCCClassifier(nn.Module):
    """Simple ResNet-based classifier for tissue images"""
    
    def __init__(self, num_classes=2):
        super().__init__()
        # Load pretrained ResNet18
        from torchvision.models import resnet18
        backbone = resnet18(weights=None)
        backbone.load_state_dict(torch.hub.load_state_dict_from_url(
            'https://download.pytorch.org/models/resnet18-5c106cde.pth',
            progress=False
        ))
        
        # Remove classification head
        self.features = nn.Sequential(*list(backbone.children())[:-1])
        
        # Add classification head
        self.classifier = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )
    
    def forward(self, x):
        x = self.features(x)  # [B, 512, 1, 1]
        x = x.flatten(1)      # [B, 512]
        x = self.classifier(x)
        return x


class DHMCSimpleTrainer:
    """Trainer for DHMC PNG RCC images"""
    
    def __init__(self, dataset_dir, method="adaptive", epochs=10, device=None):
        self.dataset_dir = Path(dataset_dir)
        self.method = method
        self.epochs = epochs
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"\n{'='*70}")
        print(f"🔬 DHMC RCC CLASSIFIER - {method.upper()} METHOD")
        print(f"{'='*70}")
        print(f"Dataset: {self.dataset_dir}")
        print(f"Epochs: {self.epochs}")
        print(f"Device: {self.device}")
        print(f"{'='*70}\n")
        
        # Load labels
        labels_csv = self.dataset_dir / 'labels.csv'
        if not labels_csv.exists():
            print(f"❌ Error: {labels_csv} not found")
            sys.exit(1)
        
        df = pd.read_csv(labels_csv)
        self.slides = []
        self.labels = []
        
        for _, row in df.iterrows():
            slide_path = self.dataset_dir / row['path']
            if slide_path.exists():
                self.slides.append(str(slide_path))
                self.labels.append(int(row['label']))
        
        print(f"✓ Loaded {len(self.slides)} images")
        print(f"  Label 0: {sum(1 for l in self.labels if l == 0)}")
        print(f"  Label 1: {sum(1 for l in self.labels if l == 1)}")
        
        # Split into train/val
        train_slides, val_slides, train_labels, val_labels = train_test_split(
            self.slides, self.labels, test_size=0.2, random_state=42, stratify=self.labels
        )
        
        self.train_slides = train_slides
        self.train_labels = train_labels
        self.val_slides = val_slides
        self.val_labels = val_labels
        
        print(f"  Train: {len(self.train_slides)} images")
        print(f"  Val:   {len(self.val_slides)} images\n")
        
        # Initialize model
        self.model = SimpleRCCClassifier(num_classes=2).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-4)
        self.criterion = nn.CrossEntropyLoss()
        
        print(f"✓ Model: SimpleRCCClassifier")
        print(f"✓ Optimizer: Adam (lr=1e-4)")
        print(f"✓ Loss: CrossEntropyLoss\n")
        
        # Results tracking
        self.train_losses = []
        self.train_accs = []
        self.val_accs = []
    
    def load_and_prepare_image(self, image_path):
        """Load and prepare image for classification"""
        try:
            # Load image with PIL
            img = Image.open(image_path).convert('RGB')
            img_array = np.array(img)
            
            # Resize to 512x512 for processing
            img_array = cv2.resize(img_array, (512, 512))
            
            return img_array
        except Exception as e:
            print(f"Error loading {image_path}: {e}")
            return np.zeros((512, 512, 3), dtype=np.uint8)
    
    def extract_features(self, image_path):
        """Extract features from image using selected method"""
        image = self.load_and_prepare_image(image_path)
        
        if self.method == 'adaptive':
            # Use adaptive approach: extract features from high-complexity regions
            # Simple adaptive: focus on center and corners
            patches = []
            h, w = image.shape[:2]
            
            # Center patch
            y1, y2 = h//4, 3*h//4
            x1, x2 = w//4, 3*w//4
            patches.append(image[y1:y2, x1:x2])
            
            # Corners for diversity
            for y_start, y_end in [(0, h//2), (h//2, h)]:
                for x_start, x_end in [(0, w//2), (w//2, w)]:
                    patch = image[y_start:y_end, x_start:x_end]
                    patches.append(patch)
        
        else:  # uniform
            # Uniform sampling: grid-based patches
            patches = []
            stride = image.shape[0] // 3
            patch_size = 256
            
            for y in range(0, image.shape[0] - patch_size, stride):
                for x in range(0, image.shape[1] - patch_size, stride):
                    patches.append(image[y:y+patch_size, x:x+patch_size])
        
        # Ensure all patches are 224x224
        processed_patches = []
        for patch in patches:
            if patch.size > 0:
                patch = cv2.resize(patch, (224, 224))
                processed_patches.append(patch)
        
        if len(processed_patches) == 0:
            processed_patches = [cv2.resize(image, (224, 224))]
        
        return np.array(processed_patches)
    
    def train_epoch(self):
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        correct = 0
        total_samples = 0
        
        for image_path, label in tqdm(zip(self.train_slides, self.train_labels), 
                                      total=len(self.train_slides),
                                      desc="Train"):
            # Extract patches
            patches = self.extract_features(image_path)
            
            # Convert to tensor
            patches_tensor = torch.from_numpy(patches).float().to(self.device) / 255.0
            patches_tensor = patches_tensor.permute(0, 3, 1, 2)  # NHWC -> NCHW
            
            # Forward pass
            self.optimizer.zero_grad()
            logits = self.model(patches_tensor)
            
            # Create labels for all patches
            labels_tensor = torch.full((logits.shape[0],), label, dtype=torch.long, device=self.device)
            loss = self.criterion(logits, labels_tensor)
            
            # Backward
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            preds = logits.argmax(dim=1)
            correct += (preds == label).sum().item()
            total_samples += len(patches)
        
        avg_loss = total_loss / len(self.train_slides)
        accuracy = correct / total_samples
        
        return avg_loss, accuracy
    
    def val_epoch(self):
        """Validation epoch"""
        self.model.eval()
        correct = 0
        total_samples = 0
        
        with torch.no_grad():
            for image_path, label in tqdm(zip(self.val_slides, self.val_labels), 
                                         total=len(self.val_slides),
                                         desc="Val"):
                patches = self.extract_features(image_path)
                patches_tensor = torch.from_numpy(patches).float().to(self.device) / 255.0
                patches_tensor = patches_tensor.permute(0, 3, 1, 2)
                
                logits = self.model(patches_tensor)
                preds = logits.argmax(dim=1)
                correct += (preds == label).sum().item()
                total_samples += len(patches)
        
        accuracy = correct / total_samples
        return accuracy
    
    def train(self):
        """Run full training"""
        print(f"\n{'='*70}")
        print(f"🚀 TRAINING STARTED")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        best_val_acc = 0
        
        for epoch in range(self.epochs):
            print(f"[Epoch {epoch+1}/{self.epochs}]")
            train_loss, train_acc = self.train_epoch()
            val_acc = self.val_epoch()
            
            self.train_losses.append(train_loss)
            self.train_accs.append(train_acc)
            self.val_accs.append(val_acc)
            
            best_val_acc = max(best_val_acc, val_acc)
            
            print(f"  Loss: {train_loss:.4f} | Train Acc: {train_acc:.1%} | Val Acc: {val_acc:.1%}")
            if val_acc == best_val_acc:
                print(f"  ✓ New best val accuracy!")
            print()
        
        elapsed = time.time() - start_time
        
        # Save results
        results = {
            'method': self.method,
            'dataset': 'dhmc_wsi_03_png',
            'epochs': self.epochs,
            'images_trained': len(self.train_slides),
            'images_validated': len(self.val_slides),
            'final_train_loss': float(self.train_losses[-1]),
            'final_train_acc': float(self.train_accs[-1]),
            'best_train_acc': float(max(self.train_accs)),
            'final_val_acc': float(self.val_accs[-1]),
            'best_val_acc': float(max(self.val_accs)),
            'training_time_seconds': int(elapsed),
            'device': self.device
        }
        
        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path(f'results/{self.method}_dhmc_png_{timestamp}')
        results_dir.mkdir(parents=True, exist_ok=True)
        
        with open(results_dir / 'results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*70}")
        print(f"✅ TRAINING COMPLETE")
        print(f"{'='*70}")
        print(f"Method:          {self.method}")
        print(f"Final Train Acc:  {self.train_accs[-1]:.1%}")
        print(f"Final Val Acc:    {self.val_accs[-1]:.1%}")
        print(f"Best Val Acc:     {max(self.val_accs):.1%}")
        print(f"Training Time:    {elapsed/60:.1f} minutes")
        print(f"Results saved:    {results_dir}/results.json")
        print(f"{'='*70}\n")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Train on DHMC RCC PNG dataset')
    parser.add_argument('--dataset', default='datasets/DHMC_wsi_03')
    parser.add_argument('--method', default='adaptive', choices=['adaptive', 'uniform'])
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--device', default=None, choices=[None, 'cuda', 'cpu'])
    
    args = parser.parse_args()
    
    trainer = DHMCSimpleTrainer(
        dataset_dir=args.dataset,
        method=args.method,
        epochs=args.epochs,
        device=args.device
    )
    
    trainer.train()


if __name__ == '__main__':
    main()
