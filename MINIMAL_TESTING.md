# QUICK START: TEST WITH 3-4 WSI IMAGES

## Option 1: Use Synthetic Test Dataset (Fastest - 5 minutes)

Perfect for testing the pipeline without any downloads.

### Step 1: Create Synthetic Dataset
```bash
cd /home/debghs/coding/final_yr_project

# Create 4 synthetic WSI images (2 normal, 2 tumor)
python3 create_test_dataset.py --num_slides 4 --output_dir data/test_slides

# What this does:
# ✓ Creates synthetic_normal_00.png, synthetic_normal_01.png
# ✓ Creates synthetic_tumor_00.png, synthetic_tumor_01.png
# ✓ Creates labels.csv with ground truth
# ✓ All in: data/test_slides/slides/
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Train on Minimal Dataset
```bash
# Test all 3 methods quickly
python3 train_minimal.py --dataset data/test_slides --epochs 5 --method adaptive

# Or test each method:
python3 train_minimal.py --dataset data/test_slides --epochs 5 --method uniform
python3 train_minimal.py --dataset data/test_slides --epochs 5 --method random
python3 train_minimal.py --dataset data/test_slides --epochs 5 --method adaptive
```

**Expected Runtime**: ~2-5 minutes per method (5-15 minutes total for all 3)

---

## Option 2: Use Your Own WSI Images

If you have your own WSI files:

### Step 1: Prepare Your Slides
```bash
# Create directory structure
mkdir -p data/test_slides/slides

# Copy your WSI images (supports .png, .jpg, .tif, .svs)
cp /path/to/your/*.svs data/test_slides/slides/
cp /path/to/your/*.tif data/test_slides/slides/
```

### Step 2: Create Labels File
Create `data/test_slides/labels.csv`:
```csv
slide,label
your_slide_1.svs,0
your_slide_2.svs,1
your_slide_3.tif,0
your_slide_4.tif,1
```

Or create it programmatically:
```bash
python3 -c "
import pandas as pd
from pathlib import Path

slides_dir = Path('data/test_slides/slides')
slides = list(slides_dir.glob('*'))
labels = [0 if 'normal' in s.name.lower() else 1 for s in slides]

df = pd.DataFrame({'slide': [s.name for s in slides], 'label': labels})
df.to_csv('data/test_slides/labels.csv', index=False)
print('✓ Created labels.csv')
"
```

### Step 3: Train
```bash
python3 train_minimal.py --dataset data/test_slides --epochs 5 --method adaptive
```

---

## Option 3: Mix of Synthetic + Your Own

```bash
# Create 2 synthetic
python3 create_test_dataset.py --num_slides 2 --output_dir data/test_slides

# Copy your 2 real images
cp /path/to/your/slide1.svs data/test_slides/slides/
cp /path/to/your/slide2.svs data/test_slides/slides/

# Update labels.csv to include your images
# Then train
python3 train_minimal.py --dataset data/test_slides --epochs 5 --method adaptive
```

---

## What Gets Tested

When you run `train_minimal.py`, it tests:

1. **WSI Reading** - Load images from various formats
2. **Tissue Map Generation** - Compute complexity & uncertainty
3. **Graph Construction** - Build spatial tissue graph
4. **Tiling Algorithms** - Generate patches using all 3 methods
5. **Patch Extraction** - Extract image patches
6. **Model Forward Pass** - Run patches through neural network
7. **Training Loop** - Gradient updates and loss reduction

This validates the **entire pipeline** in 5-15 minutes.

---

## After Testing Works: Scale Up to Full Dataset

Once you verify the pipeline works with 3-4 images:

### Option A: Download CAMELYON16 (Recommended for Publication)
```bash
# Go to: https://camelyon16.grand-challenge.org/
# Download training dataset (~100 GB)
# Extract to: data/camelyon16/slides/

# Create labels
python3 prepare_datasets.py

# Run full training (this takes 1-2 weeks)
python3 train.py --dataset camelyon16 --epochs 20
```

### Option B: Use Full-Featured Training Script
Once confident with minimal version:
```bash
# For production training on CAMELYON16
python3 experiments.py  # Runs all 3 methods with full validation
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'xxx'"
```bash
pip install -r requirements.txt
```

### "No module named 'torch'"
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# Or with GPU support:
pip install torch torchvision torchaudio
```

### "Could not read slide" warning
- Synthetic dataset: This is expected, dummy patches are used
- Real images: Make sure format is supported (.png, .jpg, .tif, .svs)

### Out of Memory error
Edit `config.py`:
```python
TILE_SIZE = 128  # Smaller patches
BATCH_SIZE = 1   # Smaller batches
```

### Very slow
- GPU inference: Install CUDA if available
- CPU is fine for testing with 3-4 images
- Full CAMELYON16 requires GPU

---

## Files Created by `create_test_dataset.py`

```
data/test_slides/
├── slides/
│   ├── normal_00.png      (4096×4096, tissue-like)
│   ├── normal_01.png      (4096×4096, tissue-like)
│   ├── tumor_00.png       (4096×4096, with abnormal regions)
│   └── tumor_01.png       (4096×4096, with abnormal regions)
├── labels.csv             (ground truth labels)
└── test_config.py         (test-specific config)
```

Each synthetic image is ~6 MB PNG with tissue-like patterns.

---

## Next Steps

1. **Test with synthetic data** (5 min)
   ```bash
   python3 create_test_dataset.py --num_slides 4
   python3 train_minimal.py --dataset data/test_slides --epochs 5
   ```

2. **Verify it works** (look for "✓ Training complete!")

3. **Optionally**: Add your own WSI images

4. **When ready**: Download full CAMELYON16 and scale up

---

## Summary

| Approach | Setup Time | Runtime | Data Download | Best For |
|----------|-----------|---------|---------------|----------|
| Synthetic (Option 1) | 5 min | 5-15 min | None | Testing pipeline quickly |
| Your Images (Option 2) | 10 min | 5-15 min | None | Testing on real data |
| Mixed (Option 3) | 15 min | 5-15 min | None | Hybrid testing |
| Full CAMELYON16 | 1 hour | 1-2 weeks | ~100 GB | Publishing research |

**Recommended workflow**:
1. Test with synthetic → 5 minutes
2. Test with your images (if you have) → 10 minutes
3. Make sure it works → Use full dataset for publication

You now have a complete, testable research system without waiting for dataset downloads! 🚀
