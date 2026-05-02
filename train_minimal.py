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
    from pipeline.wsi import WSIReader
    from pipeline.maps import compute_tissue_mask, compute_complexity_map
    from pipeline.graph import TissueGraph
    from pipeline.tiling import adaptive_tiles, uniform_tiles, random_tiles
    from pipeline.scoring import PatchScorer
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
        self.model = ASTRA(
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
            # Read slide
            reader = WSIReader(slide_path)
            slide_image = reader.get_thumbnail(level=2)
            
            if slide_image is None or slide_image.size == 0:
                print(f"    ⚠️  Could not read slide, returning dummy patches")
                # Return dummy patches for testing
                return np.random.rand(5, 256, 256, 3).astype(np.uint8), 5
            
            # Compute maps
            tissue_mask = compute_tissue_mask(slide_image)
            complexity_map = compute_complexity_map(slide_image)
            
            # Build graph
            graph = TissueGraph(slide_image)
            graph.build_from_superpixels(tissue_mask, num_superpixels=50)
            
            # Generate tiles based on method
            if self.method == "uniform":
                tiles = uniform_tiles(slide_image, tile_size=256, stride=128)
            elif self.method == "random":
                tiles = random_tiles(slide_image, num_tiles=10, tile_size=256)
            elif self.method == "adaptive":
                tiles = adaptive_tiles(graph, complexity_map, num_tiles=10)
            else:
                raise ValueError(f"Unknown method: {self.method}")
            
            # Extract patch images
            patches = []
            for tile in tiles[:20]:  # Limit to 20 patches per slide
                x, y, w, h = tile
                patch = slide_image[max(0, y):min(slide_image.shape[0], y+h),
                                   max(0, x):min(slide_image.shape[1], x+w)]
                
                if patch.size > 0:
                    # Resize to 256x256
                    import cv2
                    patch = cv2.resize(patch, (256, 256))
                    patches.append(patch)
            
            return np.array(patches), len(patches)
        
        except Exception as e:
            print(f"    ⚠️  Error processing slide: {e}")
            # Return dummy patches for testing
            return np.random.rand(5, 256, 256, 3).astype(np.uint8), 5
    
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
            logits = self.model(patches_tensor.unsqueeze(0))  # Add batch dim
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
                
                logits = self.model(patches_tensor.unsqueeze(0))
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
