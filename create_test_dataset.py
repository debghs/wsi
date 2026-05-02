#!/usr/bin/env python3
"""
Create a minimal test dataset with 3-4 synthetic WSI images for quick testing.
This allows you to test the entire pipeline without downloading CAMELYON16.

Usage:
    python create_test_dataset.py --num_slides 4 --output_dir data/test_slides
"""

import os
import argparse
import numpy as np
from pathlib import Path
import cv2
from PIL import Image
import sys


def create_synthetic_wsi(output_path, width=4096, height=4096, label=0):
    """
    Create a synthetic WSI-like image with tissue patterns.
    
    Args:
        output_path: Path to save the image
        width, height: Image dimensions
        label: 0 for normal, 1 for tumor
    
    Returns:
        Path to saved image
    """
    print(f"  Creating synthetic WSI: {os.path.basename(output_path)}")
    
    # Create base tissue image (light pink/beige)
    image = np.ones((height, width, 3), dtype=np.uint8) * 230
    image[:, :, 0] = np.clip(image[:, :, 0] - 20, 0, 255)  # Slightly more red
    
    # Add tissue texture with Perlin-like noise
    noise = np.random.randint(0, 20, (height, width, 3))
    image = np.clip(image.astype(int) + noise, 0, 255).astype(np.uint8)
    
    # Add cellular structures (darker regions)
    for _ in range(50):
        cx = np.random.randint(100, width - 100)
        cy = np.random.randint(100, height - 100)
        radius = np.random.randint(10, 50)
        color = tuple(np.random.randint(100, 180, 3).tolist())
        cv2.circle(image, (cx, cy), radius, color, -1)
    
    # Add tumor/abnormal regions if label=1
    if label == 1:
        print(f"    Adding tumor patterns...")
        # Add darker abnormal regions
        for _ in range(15):
            cx = np.random.randint(500, width - 500)
            cy = np.random.randint(500, height - 500)
            radius = np.random.randint(50, 150)
            color = (50, 50, 100)  # Darker, more purple
            cv2.circle(image, (cx, cy), radius, color, -1)
        
        # Add some irregular shapes
        for _ in range(10):
            pts = np.random.randint(100, 300, (5, 2))
            cv2.polylines(image, [pts], True, (60, 60, 120), 5)
    
    # Save as PNG
    Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).save(output_path)
    print(f"    ✓ Saved: {output_path}")
    return output_path


def create_test_dataset(num_slides=4, output_dir="data/test_slides", use_synthetic=True):
    """
    Create a minimal test dataset.
    
    Args:
        num_slides: Number of test slides to create (3-4 recommended)
        output_dir: Output directory
        use_synthetic: If True, create synthetic images; if False, expect user to provide images
    
    Returns:
        List of slide paths and labels
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    slides_dir = output_dir / "slides"
    slides_dir.mkdir(exist_ok=True)
    
    print(f"\n📊 Creating test dataset with {num_slides} slides in {output_dir}")
    print("=" * 60)
    
    slide_info = []
    
    # Create mix of normal and tumor slides
    num_normal = max(1, num_slides // 2)
    num_tumor = num_slides - num_normal
    
    print(f"\nCreating {num_normal} normal slides and {num_tumor} tumor slides...")
    
    if use_synthetic:
        # Create synthetic normal slides
        for i in range(num_normal):
            slide_name = f"normal_{i:02d}.png"
            slide_path = slides_dir / slide_name
            create_synthetic_wsi(str(slide_path), label=0)
            slide_info.append({"slide": slide_name, "label": 0})
        
        # Create synthetic tumor slides
        for i in range(num_tumor):
            slide_name = f"tumor_{i:02d}.png"
            slide_path = slides_dir / slide_name
            create_synthetic_wsi(str(slide_path), label=1)
            slide_info.append({"slide": slide_name, "label": 1})
    else:
        print("\n⚠️  use_synthetic=False: Place your WSI images in:")
        print(f"    {slides_dir}/")
        print("   Supported formats: .png, .jpg, .tif, .svs")
        print("\nThen create labels.csv manually (see below)")
    
    # Create labels CSV
    csv_path = output_dir / "labels.csv"
    print(f"\nCreating labels CSV: {csv_path}")
    
    with open(csv_path, 'w') as f:
        f.write("slide,label\n")
        for item in slide_info:
            f.write(f"{item['slide']},{item['label']}\n")
    
    print(f"✓ Labels CSV created")
    
    # Create config for test dataset
    config_path = output_dir / "test_config.py"
    with open(config_path, 'w') as f:
        f.write(f"""# Test dataset configuration
DATASET_DIR = "{slides_dir}"
LABELS_CSV = "{csv_path}"
NUM_SLIDES = {num_slides}
NUM_NORMAL = {num_normal}
NUM_TUMOR = {num_tumor}

# For testing - use smaller model and fewer epochs
TEST_CONFIG = {{
    'num_epochs': 5,  # Reduced from 20
    'batch_size': 2,  # Very small batch
    'num_workers': 0,  # No multiprocessing for stability
    'tile_size': 256,
    'top_k_ratio': 0.7,
}}
""")
    
    print(f"\n✓ Test config created: {config_path}")
    
    print("\n" + "=" * 60)
    print(f"✅ Test dataset created successfully!")
    print(f"   Total slides: {num_slides}")
    print(f"   Location: {output_dir}")
    print(f"   Slides dir: {slides_dir}")
    print(f"   Labels CSV: {csv_path}")
    print("=" * 60)
    
    return slide_info, csv_path


def setup_minimal_training():
    """Print instructions for minimal training setup."""
    print("\n" + "=" * 60)
    print("🚀 NEXT STEPS FOR MINIMAL TRAINING")
    print("=" * 60)
    print("""
1. Install dependencies:
   pip install -r requirements.txt

2. Run training with test dataset:
   python train_minimal.py --dataset data/test_slides --epochs 5

3. The training will run through all 3 methods:
   - Uniform tiling
   - Random tiling  
   - Adaptive tiling (ASTRA)

4. Compare results - expect to complete in 5-15 minutes per method

5. After testing works, scale up to CAMELYON16 dataset
""")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a minimal test dataset with synthetic WSI images"
    )
    parser.add_argument(
        "--num_slides",
        type=int,
        default=4,
        help="Number of slides to create (default: 4)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/test_slides",
        help="Output directory for test dataset (default: data/test_slides)"
    )
    parser.add_argument(
        "--use_synthetic",
        type=bool,
        default=True,
        help="Create synthetic images (True) or expect user images (False)"
    )
    
    args = parser.parse_args()
    
    # Create test dataset
    slide_info, csv_path = create_test_dataset(
        num_slides=args.num_slides,
        output_dir=args.output_dir,
        use_synthetic=args.use_synthetic
    )
    
    # Print next steps
    setup_minimal_training()
