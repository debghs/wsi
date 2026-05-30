#!/usr/bin/env python3
"""
Minimal training script for testing with 3-4 WSI images.
This is a simplified version of train.py optimized for small datasets.

Usage:
    python train_minimal.py --dataset data/test_slides --epochs 5 --method adaptive
"""

import os
import sys
import argparse
import torch
import numpy as np
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from models.encoder import PatchEncoder
    from models.mil import ASTRA
    from models.astra_combined import ASTRACombined
    from pipeline.wsi import WSIReader
    from pipeline.maps import compute_tissue_mask, compute_complexity_map
    from pipeline.graph import TissueGraph
    from pipeline.tiling import adaptive_tiles, uniform_tiles, random_tiles
    from pipeline.scoring import PatchScorer
    from pipeline.adaptive_tiling import adaptive_tiles_complexity_based
    from pipeline.complexity_maps import compute_stain_robust_complexity_map
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the project directory and dependencies are installed.")
    sys.exit(1)


class MinimalTrainer:
    """Trainer for minimal datasets."""
    
    def __init__(self, dataset_dir, method="adaptive", epochs=5, device=None):
        """
        Args:
            dataset_dir: Path to test dataset directory
            method: "uniform", "random", or "adaptive"
            epochs: Number of epochs
            device: torch device
        """
        self.dataset_dir = Path(dataset_dir)
        self.method = method
        self.epochs = epochs
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"\n{'='*60}")
        print(f"🔧 MINIMAL TRAINER CONFIG")
        print(f"{'='*60}")
        print(f"Dataset dir: {self.dataset_dir}")
        print(f"Method: {self.method}")
        print(f"Epochs: {self.epochs}")
        print(f"Device: {self.device}")
        print(f"{'='*60}\n")
        
        # Load dataset info
        self.labels_csv = self.dataset_dir / "labels.csv"
        if not self.labels_csv.exists():
            print(f"❌ Error: {self.labels_csv} not found")
            print(f"   First run: python create_test_dataset.py")
            sys.exit(1)
        
        self.slides_dir = self.dataset_dir / "slides"
        self.load_slide_list()
        
        # Initialize model
        self.model = ASTRACombined(
            backbone='resnet18',
            feature_dim=256,  # Smaller for faster testing
            num_classes=2
        ).to(self.device)
        
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-4)
        self.criterion = torch.nn.CrossEntropyLoss()
        
        print(f"✓ Model initialized: {self.model.__class__.__name__}")
        print(f"✓ Optimizer: Adam (lr=1e-4)")
        print(f"✓ Loss: CrossEntropyLoss\n")
    
    def load_slide_list(self):
        """Load slide paths and labels from CSV."""
        df = pd.read_csv(self.labels_csv)
        self.slides = []
        self.labels = []
        
        for _, row in df.iterrows():
            slide_path = self.slides_dir / row['slide']
            if slide_path.exists():
                self.slides.append(str(slide_path))
                self.labels.append(int(row['label']))
            else:
                print(f"⚠️  Missing: {slide_path}")
        
        print(f"✓ Loaded {len(self.slides)} slides")
        print(f"  Normal: {sum(1 for l in self.labels if l == 0)}")
        print(f"  Tumor:  {sum(1 for l in self.labels if l == 1)}\n")
    
    def extract_patches(self, slide_path):
        """
        Extract patches from a slide using the specified method.
        
        Returns:
            (patches, valid_count): numpy array of patches and count
        """
        try:
            import cv2
            
            # Read slide - use cv2 for PNG/JPG, fallback to WSIReader for SVS
            if isinstance(slide_path, str) and (slide_path.endswith('.png') or slide_path.endswith('.jpg') or slide_path.endswith('.jpeg')):
                slide_image = cv2.imread(slide_path)
                if slide_image is not None:
                    slide_image = cv2.cvtColor(slide_image, cv2.COLOR_BGR2RGB)
                    # Remove alpha channel if present
                    if len(slide_image.shape) == 3 and slide_image.shape[2] == 4:
                        slide_image = slide_image[:, :, :3]
            else:
                reader = WSIReader(slide_path)
                slide_image = reader.get_thumbnail(level=2)
                # Ensure it's RGB (remove alpha if present)
                if slide_image is not None and len(slide_image.shape) == 3 and slide_image.shape[2] == 4:
                    slide_image = slide_image[:, :, :3]
            
            if slide_image is None or slide_image.size == 0:
                print(f"    ⚠️  Could not read slide, returning dummy patches")
                # Return dummy patches for testing
                return np.random.rand(5, 224, 224, 3).astype(np.uint8), 5
            
            # Ensure image is uint8
            if slide_image.dtype != np.uint8:
                if slide_image.max() <= 1.0:
                    slide_image = (slide_image * 255).astype(np.uint8)
                else:
                    slide_image = np.clip(slide_image, 0, 255).astype(np.uint8)
            
            # Generate tiles based on method
            if self.method == "uniform":
                from pipeline.adaptive_tiling import uniform_tiles
                tiles = uniform_tiles(slide_image, patch_size=256, stride=128)
            elif self.method == "random":
                from pipeline.adaptive_tiling import random_tiles
                tiles = random_tiles(slide_image, num_tiles=10, patch_size=256)
            elif self.method == "adaptive":
                # Use NEW stain-robust adaptive tiling
                tiles, complexity_map = adaptive_tiles_complexity_based(
                    slide_image,
                    base_patch_size=256,
                    complexity_threshold=0.4,
                    normalize_stains=True  # Use stain normalization
                )
            else:
                raise ValueError(f"Unknown method: {self.method}")
            
            # Extract patch images from tiles
            patches = []
            for tile_dict in tiles[:20]:  # Limit to 20 patches per slide
                # Handle dict format from tiling functions
                if isinstance(tile_dict, dict):
                    # Dict format with 'coords' key: (x1, y1, x2, y2)
                    if 'coords' in tile_dict:
                        x1, y1, x2, y2 = tile_dict['coords']
                        patch = slide_image[max(0, y1):min(slide_image.shape[0], y2),
                                          max(0, x1):min(slide_image.shape[1], x2)]
                    else:
                        continue
                else:
                    continue
                
                if patch.size > 0:
                    # Resize to 224x224 for ResNet
                    patch = cv2.resize(patch, (224, 224))
                    patches.append(patch)
            
            if len(patches) == 0:
                # Return dummy patches if no patches were extracted
                return np.random.rand(5, 224, 224, 3).astype(np.uint8), 5
            
            return np.array(patches), len(patches)
        
        except Exception as e:
            import traceback
            print(f"    ⚠️  Error processing slide: {e}")
            traceback.print_exc()
            # Return dummy patches for testing
            return np.random.rand(5, 224, 224, 3).astype(np.uint8), 5
    
    def train_epoch(self):
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        print(f"\n  Training epoch...")
        for slide_idx, (slide_path, label) in enumerate(zip(self.slides, self.labels)):
            print(f"    [{slide_idx+1}/{len(self.slides)}] Processing {Path(slide_path).name}...", end=' ')
            
            # Extract patches
            patches, num_patches = self.extract_patches(slide_path)
            
            if num_patches == 0:
                print("⚠️  No patches extracted")
                continue
            
            # Convert to tensors
            patches_tensor = torch.FloatTensor(patches).to(self.device) / 255.0
            patches_tensor = patches_tensor.permute(0, 3, 1, 2)  # CHW
            label_tensor = torch.LongTensor([label]).to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            output = self.model(patches_tensor)  # Returns dict
            logits = output['logits']  # (1, 2)
            loss = self.criterion(logits, label_tensor)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            
            pred = logits.argmax(dim=1)
            correct += (pred == label_tensor).sum().item()
            total += 1
            
            print(f"✓ Loss: {loss.item():.4f}")
        
        avg_loss = total_loss / max(total, 1)
        accuracy = correct / max(total, 1)
        
        return avg_loss, accuracy
    
    def validate(self):
        """Validate model."""
        self.model.eval()
        correct = 0
        total = 0
        
        print(f"\n  Validating...")
        with torch.no_grad():
            for slide_path, label in zip(self.slides[-1:], self.labels[-1:]):  # Use last slide as validation
                print(f"    Validating {Path(slide_path).name}...", end=' ')
                
                patches, num_patches = self.extract_patches(slide_path)
                if num_patches == 0:
                    continue
                
                patches_tensor = torch.FloatTensor(patches).to(self.device) / 255.0
                patches_tensor = patches_tensor.permute(0, 3, 1, 2)
                label_tensor = torch.LongTensor([label]).to(self.device)
                
                output = self.model(patches_tensor)
                logits = output['logits']
                pred = logits.argmax(dim=1)
                correct += (pred == label_tensor).sum().item()
                total += 1
                
                print(f"✓")
        
        accuracy = correct / max(total, 1)
        return accuracy
    
    def train(self):
        """Run training loop."""
        print(f"\n{'='*60}")
        print(f"🚀 STARTING TRAINING - Method: {self.method.upper()}")
        print(f"{'='*60}")
        
        best_accuracy = 0
        
        for epoch in range(self.epochs):
            print(f"\n[Epoch {epoch+1}/{self.epochs}]")
            
            train_loss, train_acc = self.train_epoch()
            val_acc = self.validate()
            
            print(f"\n  Summary:")
            print(f"    Train Loss:  {train_loss:.4f}")
            print(f"    Train Acc:   {train_acc:.4f}")
            print(f"    Val Acc:     {val_acc:.4f}")
            
            if val_acc > best_accuracy:
                best_accuracy = val_acc
        
        print(f"\n{'='*60}")
        print(f"✅ Training complete!")
        print(f"   Best accuracy: {best_accuracy:.4f}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Minimal training on 3-4 WSI images")
    parser.add_argument("--dataset", type=str, default="data/test_slides",
                        help="Test dataset directory")
    parser.add_argument("--epochs", type=int, default=5,
                        help="Number of epochs")
    parser.add_argument("--method", type=str, default="adaptive",
                        choices=["uniform", "random", "adaptive"],
                        help="Tiling method")
    parser.add_argument("--device", type=str, default=None,
                        help="torch device (cpu or cuda)")
    
    args = parser.parse_args()
    
    # Create trainer and train
    trainer = MinimalTrainer(
        dataset_dir=args.dataset,
        method=args.method,
        epochs=args.epochs,
        device=args.device
    )
    
    trainer.train()


if __name__ == "__main__":
    main()
