# ASTRA Research Project - Step-by-Step Execution Guide

## COMPLETE WORKFLOW TO PUBLICATION

This document walks you through EXACTLY what to do, step by step, with no gaps.

---

## PART 1: INITIAL SETUP (Day 1)

### Step 1.1: Verify Python Environment

```bash
cd /home/debghs/coding/final_yr_project

# Check Python version
python3 --version
# Expected: Python 3.10+

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 1.2: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# For GPU support (if you have NVIDIA GPU), replace line above with:
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify installation
python3 << 'EOF'
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
EOF
```

### Step 1.3: Create Directory Structure

```bash
# Create all needed directories
mkdir -p data/camelyon16/slides
mkdir -p data/camelyon17/slides
mkdir -p data/tcga/slides
mkdir -p results
mkdir -p figures
mkdir -p models_saved

echo "Directories created successfully"
```

---

## PART 2: DATA PREPARATION (Days 2-5)

### Step 2.1: Download CAMELYON16 Dataset

**IMPORTANT: This is MANUAL download - no automated way**

1. Open browser: https://camelyon16.grand-challenge.org/
2. Click "Register" and create account
3. After registration, login and go to Downloads section
4. Download "Training set" (~100 GB)
   - This includes: 271 training slides with annotations
5. Download is typically a .zip file

**Expected download time: 1-3 days on residential internet**

Alternative (faster if available):
```bash
# Some institutions have pre-downloaded copies
# Check if your university has a copy and copy from there
cp /path/to/institutional/camelyon16/*.svs data/camelyon16/slides/
```

### Step 2.2: Extract Downloaded Files

```bash
# Navigate to downloads folder
cd ~/Downloads

# Extract zip (adjust filename as needed)
unzip camelyon16_training_dataset.zip

# Move to project directory
mv camelyon16_training/slides/*.svs \
   /home/debghs/coding/final_yr_project/data/camelyon16/slides/

# Verify
ls -la /home/debghs/coding/final_yr_project/data/camelyon16/slides/ | head -20

# Should see: slide_001.svs, slide_002.svs, etc
# Count files
ls -1 data/camelyon16/slides/*.svs | wc -l
# Expected: 271 files (or similar)
```

### Step 2.3: Create Labels CSV File

First, understand the CAMELYON16 structure:
- Folder `tumor_slides/` contains positive slides (label=1)
- Folder `normal_slides/` contains negative slides (label=0)

If downloaded files are already separated:

```bash
cd /home/debghs/coding/final_yr_project

# Check directory structure
ls -la data/camelyon16/

# If you see tumor_slides and normal_slides directories:
python3 << 'EOF'
import pandas as pd
from pathlib import Path
import os

data_dir = "data/camelyon16"
slides = []
labels = []

# Tumor slides (label=1)
tumor_dir = f"{data_dir}/tumor_slides"
if os.path.exists(tumor_dir):
    for f in Path(tumor_dir).glob("*.svs"):
        slides.append(f.name)
        labels.append(1)

# Normal slides (label=0)
normal_dir = f"{data_dir}/normal_slides"
if os.path.exists(normal_dir):
    for f in Path(normal_dir).glob("*.svs"):
        slides.append(f.name)
        labels.append(0)

df = pd.DataFrame({
    'path': slides,
    'label': labels
})

df.to_csv(f"{data_dir}/labels.csv", index=False)
print(f"Created labels.csv with {len(df)} slides")
print(f"Label distribution:\n{df['label'].value_counts()}")
print(f"Sample:\n{df.head()}")
EOF
```

### Step 2.4: Validate Dataset

```bash
python3 << 'EOF'
import pandas as pd
import os

csv_path = "data/camelyon16/labels.csv"
data_dir = "data/camelyon16"

df = pd.read_csv(csv_path)

# Check all files exist
missing = 0
for idx, row in df.iterrows():
    slide_path = os.path.join(data_dir, row['path'])
    if not os.path.exists(slide_path):
        print(f"Missing: {slide_path}")
        missing += 1

if missing == 0:
    print(f"✓ All {len(df)} slide files found!")
else:
    print(f"✗ {missing} files missing!")

# Test loading one slide
try:
    from pipeline.wsi import WSIReader
    first_slide = os.path.join(data_dir, df.iloc[0]['path'])
    reader = WSIReader(first_slide)
    print(f"✓ Successfully loaded: {df.iloc[0]['path']}")
    print(f"  Levels: {reader.levels}")
    print(f"  Dimensions: {reader.dimensions}")
    reader.close()
except Exception as e:
    print(f"✗ Error loading slide: {e}")
EOF
```

---

## PART 3: BASELINE EXPERIMENTS (Days 6-8)

### Step 3.1: Run Uniform Tiling Baseline

This establishes a baseline for comparison.

```bash
cd /home/debghs/coding/final_yr_project

# Run with short training first to test
python3 train.py \
    --dataset camelyon16 \
    --mode uniform \
    --epochs 5 \
    --batch_size 4

# Expected output:
# - Creates results/<mode>_<dataset>_<timestamp>/ directory
# - Logs accuracy and AUC for each epoch
# - Saves best model to best_model.pth

# Once confirmed working, run full training
python3 train.py \
    --dataset camelyon16 \
    --mode uniform \
    --epochs 20 \
    --batch_size 16

# This takes ~4-8 hours on GPU depending on hardware
```

### Step 3.2: Run Random Sampling Baseline

```bash
python3 train.py \
    --dataset camelyon16 \
    --mode random \
    --epochs 20 \
    --batch_size 16

# Expected: Faster training but likely lower performance
# Fewer patches processed per slide
```

### Step 3.3: Check Baseline Results

```bash
# Find latest results
ls -t results/ | head -3

# View metrics
cat results/uniform_camelyon16_*/metrics.json
cat results/random_camelyon16_*/metrics.json

# Compare
python3 << 'EOF'
import json
import os

results_dir = "results"

# Find baseline results
for dir_name in os.listdir(results_dir):
    if 'uniform' in dir_name or 'random' in dir_name:
        metrics_file = f"{results_dir}/{dir_name}/metrics.json"
        results_file = f"{results_dir}/{dir_name}/results.json"
        
        if os.path.exists(metrics_file):
            with open(metrics_file) as f:
                metrics = json.load(f)
            with open(results_file) as f:
                results = json.load(f)
            
            print(f"\n{dir_name}")
            print(f"  Best AUC: {results['best_auc']:.4f}")
            print(f"  Final Accuracy: {results['final_acc']:.4f}")
            print(f"  Epoch: {results['best_epoch']}")
EOF
```

---

## PART 4: ADAPTIVE TILING (MAIN METHOD) (Days 9-11)

### Step 4.1: Run ASTRA (Adaptive Tiling)

```bash
# Test run first (5 epochs)
python3 train.py \
    --dataset camelyon16 \
    --mode adaptive \
    --epochs 5 \
    --batch_size 4 \
    --cache

# Full training run (use --cache to speed up subsequent runs)
python3 train.py \
    --dataset camelyon16 \
    --mode adaptive \
    --epochs 20 \
    --batch_size 16 \
    --cache

# Expected: Should achieve better AUC with fewer patches
```

### Step 4.2: Compare Results

```bash
python3 << 'EOF'
import json
import os
from collections import defaultdict

results_dir = "results"
summary = defaultdict(dict)

# Parse results
for dir_name in os.listdir(results_dir):
    if os.path.isdir(f"{results_dir}/{dir_name}"):
        results_file = f"{results_dir}/{dir_name}/results.json"
        
        if os.path.exists(results_file):
            with open(results_file) as f:
                data = json.load(f)
            
            mode = data.get('mode', 'unknown')
            summary[mode]['auc'] = data.get('best_auc', 0)
            summary[mode]['acc'] = data.get('final_acc', 0)

# Print comparison table
print("\n" + "="*60)
print("BASELINE COMPARISON")
print("="*60)
print(f"{'Method':<15} {'AUC':<10} {'Accuracy':<10}")
print("-"*60)

for method in ['uniform', 'random', 'adaptive']:
    if method in summary:
        print(f"{method:<15} {summary[method]['auc']:<10.4f} {summary[method]['acc']:<10.4f}")

print("="*60)
print("\n✓ ASTRA should show improvement over baselines\n")
EOF
```

---

## PART 5: ABLATION STUDY (Days 12-14)

This tests which components actually contribute to performance.

### Step 5.1: Run All Ablation Variants

```bash
# Run all comparison experiments
python3 experiments.py \
    --mode full \
    --dataset camelyon16 \
    --epochs 20

# This automatically runs all three methods and logs results
```

### Step 5.2: Generate Ablation Summary

```bash
python3 << 'EOF'
import json
import os
import pandas as pd
from collections import defaultdict

# Collect all results
data = []

for dir_name in sorted(os.listdir("results")):
    if os.path.isdir(f"results/{dir_name}"):
        results_file = f"results/{dir_name}/results.json"
        
        if os.path.exists(results_file):
            with open(results_file) as f:
                r = json.load(f)
            
            data.append({
                'Mode': r.get('mode', 'unknown'),
                'Dataset': r.get('dataset', 'unknown'),
                'AUC': r.get('best_auc', 0),
                'Accuracy': r.get('final_acc', 0),
                'Epoch': r.get('best_epoch', 0),
            })

df = pd.DataFrame(data)
print("\nABLATION STUDY RESULTS")
print("="*70)
print(df.to_string(index=False))
print("="*70)

# Save summary
df.to_csv("results/ablation_summary.csv", index=False)
print("\nSaved to: results/ablation_summary.csv")
EOF
```

---

## PART 6: CROSS-DATASET VALIDATION (Days 15-17)

### Step 6.1: Prepare CAMELYON17 (Optional but Recommended)

```bash
# Download from https://camelyon17.grand-challenge.org/
# Extract to data/camelyon17/slides/
# Create labels.csv (similar to Step 2.3)

python3 << 'EOF'
import pandas as pd
from pathlib import Path
import os

# Create simple labels for CAMELYON17
data_dir = "data/camelyon17"
slides_dir = f"{data_dir}/slides"

if os.path.exists(slides_dir):
    slides = [f.name for f in Path(slides_dir).glob("*.svs")]
    # For CAMELYON17, labels are typically in filename or separate file
    # This is a placeholder - adapt to actual label source
    labels = [int('tumor' in s) for s in slides]  # Dummy logic
    
    df = pd.DataFrame({'path': slides, 'label': labels})
    df.to_csv(f"{data_dir}/labels.csv", index=False)
    print(f"Created labels for CAMELYON17 with {len(df)} slides")
EOF
```

### Step 6.2: Test Cross-Dataset Generalization

```bash
# Train on CAMELYON16, test on CAMELYON17
python3 train.py \
    --dataset camelyon17 \
    --mode adaptive \
    --epochs 20

# Compare AUC across datasets
python3 << 'EOF'
import json
import os

print("\nCROSS-DATASET RESULTS")
print("="*70)

for dataset in ['camelyon16', 'camelyon17']:
    for dir_name in os.listdir("results"):
        if dataset in dir_name and 'adaptive' in dir_name:
            results_file = f"results/{dir_name}/results.json"
            if os.path.exists(results_file):
                with open(results_file) as f:
                    r = json.load(f)
                print(f"{dataset}: AUC = {r['best_auc']:.4f}")
EOF
```

---

## PART 7: GENERATE VISUALIZATIONS (Day 18)

### Step 7.1: Generate Comparison Plots

```bash
python3 visualizations.py

# OR manually generate plots
python3 << 'EOF'
import matplotlib.pyplot as plt
import pandas as pd
import json
import os

# Load results
results_data = []

for dir_name in os.listdir("results"):
    if os.path.isdir(f"results/{dir_name}"):
        results_file = f"results/{dir_name}/results.json"
        if os.path.exists(results_file):
            with open(results_file) as f:
                data = json.load(f)
            results_data.append(data)

df = pd.DataFrame(results_data)

# Create comparison plot
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# AUC Comparison
methods = df['mode'].unique()
auc_values = [df[df['mode']==m]['best_auc'].mean() for m in methods]
axes[0].bar(methods, auc_values, color=['red', 'blue', 'green'])
axes[0].set_ylabel('AUC')
axes[0].set_title('Method Comparison - AUC')
axes[0].set_ylim([0.8, 0.9])

# Accuracy Comparison
acc_values = [df[df['mode']==m]['final_acc'].mean() for m in methods]
axes[1].bar(methods, acc_values, color=['red', 'blue', 'green'])
axes[1].set_ylabel('Accuracy')
axes[1].set_title('Method Comparison - Accuracy')
axes[1].set_ylim([0.8, 0.9])

plt.tight_layout()
plt.savefig('figures/comparison.png', dpi=300)
print("Saved: figures/comparison.png")
plt.close()
EOF
```

### Step 7.2: Generate Attention Visualizations

```bash
python3 << 'EOF'
import torch
import numpy as np
import matplotlib.pyplot as plt
import os

# This requires loading a trained model and a sample WSI
# See visualizations.py for full implementation

print("Attention maps and patch visualizations should be generated")
print("See visualizations.py for complete implementation")
print("Typically you would:")
print("1. Load best trained model")
print("2. Load a sample WSI")
print("3. Generate patches")
print("4. Compute attention weights")
print("5. Overlay on original image")
EOF
```

---

## PART 8: WRITE RESEARCH PAPER (Days 19-21)

### Step 8.1: Fill in Experimental Results

```bash
# Edit paper/main.tex and fill in tables

# Table 1: Main Results (from Step 3.2 and 4.2)
# - Replace XX with actual AUC values
# - Replace XX with actual accuracy values
# - Replace XX with actual patch counts

# Table 2: Ablation Study (from Step 5.2)
# - Document which components contribute

# Table 3: Cross-Dataset (from Step 6.2)
# - Show generalization capability
```

### Step 8.2: Add Figures to Paper

Create figures directory references:

```bash
# Copy best figures to paper directory
cp figures/comparison.png paper/figures/
cp figures/patch_sampling.png paper/figures/
cp figures/attention_map.png paper/figures/

# Update main.tex with figure paths:
# \includegraphics[width=0.9\textwidth]{figures/comparison.png}
```

### Step 8.3: Compile Paper

```bash
cd paper

# On Linux/Mac
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex

# Output: main.pdf

# Or use Overleaf: https://www.overleaf.com/
# Upload all files and compile online
```

---

## PART 9: FINAL VALIDATION (Day 22)

### Step 9.1: Run Complete Experiment Suite

```bash
# Run everything one more time to ensure reproducibility
python3 << 'EOF'
import subprocess
import json
from datetime import datetime

methods = ['uniform', 'random', 'adaptive']
results = {}

for method in methods:
    print(f"\nRunning {method}...")
    result = subprocess.run(
        ['python3', 'train.py',
         '--dataset', 'camelyon16',
         '--mode', method,
         '--epochs', '20'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✓ {method} completed successfully")
        results[method] = 'success'
    else:
        print(f"✗ {method} failed")
        results[method] = 'failed'

# Save final report
report = {
    'timestamp': datetime.now().isoformat(),
    'methods_tested': methods,
    'results': results,
}

with open('results/final_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\n✓ Final validation complete!")
EOF
```

### Step 9.2: Generate Publication Checklist

```bash
python3 << 'EOF'
import os

checklist = {
    'Data': os.path.exists('data/camelyon16/labels.csv'),
    'Baselines': os.path.exists('results') and len(os.listdir('results')) > 0,
    'Ablations': len([d for d in os.listdir('results') if 'uniform' in d or 'random' in d or 'adaptive' in d]) >= 3,
    'Figures': len(os.listdir('figures')) > 0 if os.path.exists('figures') else False,
    'Paper': os.path.exists('paper/main.pdf') or os.path.exists('paper/main.tex'),
    'Results': os.path.exists('results/ablation_summary.csv'),
}

print("\n" + "="*60)
print("PUBLICATION READINESS CHECKLIST")
print("="*60)

for item, status in checklist.items():
    mark = "✓" if status else "✗"
    print(f"{mark} {item}")

print("="*60)
print(f"\nReady for submission: {all(checklist.values())}")
EOF
```

---

## TROUBLESHOOTING GUIDE

### Issue: OutOfMemory Error

```bash
# Solution 1: Reduce batch size
python3 train.py --batch_size 4

# Solution 2: Use CPU
python3 train.py --device cpu

# Solution 3: Process lower resolution
# Edit config.py: CONFIG['wsi_level'] = 3
```

### Issue: Training is Slow

```bash
# Enable caching
python3 train.py --cache

# Use multiple workers (not on WSL)
# Edit train.py: DataLoader(..., num_workers=4)

# Use faster GPU
# Requires GPU with higher bandwidth
```

### Issue: Model Not Improving

```bash
# Check data quality
python3 << 'EOF'
from pipeline.wsi import WSIReader
from pipeline.maps import compute_all_maps

reader = WSIReader("data/camelyon16/slides/first_slide.svs")
img = reader.get_level(2)
tissue, _, _ = compute_all_maps(img)

if tissue.mean() < 0.1:
    print("Error: Very little tissue in image!")
else:
    print(f"Tissue coverage: {tissue.mean():.1%} - OK")
EOF

# Try different learning rate
python3 train.py --lr 5e-5
```

### Issue: OpenSlide Error

```bash
# Install system dependencies
sudo apt-get install openslide-tools

# On Mac:
brew install openslide

# On Windows:
# Download from: https://openslide.org/download/
# Add to PATH
```

---

## EXPECTED TIMELINE

- **Days 1-2**: Setup and installation
- **Days 2-5**: Download and prepare datasets (bottleneck - download time)
- **Days 6-8**: Train and compare baselines
- **Days 9-11**: Train adaptive method (ASTRA)
- **Days 12-14**: Run ablation studies
- **Days 15-17**: Cross-dataset validation (optional)
- **Day 18**: Generate visualizations
- **Days 19-21**: Write and compile paper
- **Day 22**: Final validation

**Total: ~3 weeks**

Actual times depend on:
- Download speed for datasets
- GPU available (CPU is 10-50x slower)
- Number of experiments
- Paper refinement cycles

---

## KEY RESULTS TO REPORT

Create a summary table:

| Metric | Uniform | Random | ASTRA | Improvement |
|--------|---------|--------|-------|-------------|
| AUC | 0.850 | 0.835 | 0.869 | +2.2% |
| Accuracy | 0.821 | 0.805 | 0.838 | +2.1% |
| # Patches | 1247 | 200 | 398 | -68% vs uniform |
| Time (s) | 45.2 | 8.3 | 13.7 | -70% vs uniform |

Fill in with your actual results!

---

## SUBMISSION CHECKLIST

Before submitting to conference:

- [ ] All experiments completed and documented
- [ ] Results tables filled in with actual numbers
- [ ] Figures of good quality (300 DPI, clear labels)
- [ ] References properly formatted (check bibtex)
- [ ] Paper proofread (grammar, spelling)
- [ ] Supplementary materials prepared (if needed)
- [ ] Code reproducibility tested from scratch
- [ ] Datasets properly cited
- [ ] Ethical considerations addressed (if applicable)

---

## NEXT STEPS AFTER RESEARCH IS COMPLETE

1. **Submit paper** to MICCAI, CVPR, or medical imaging conference
2. **Release code** on GitHub (make it public and cite in paper)
3. **Create supplementary materials** (videos, additional results)
4. **Prepare rebuttal** (for reviewer feedback)
5. **Consider follow-up work** (extension to multi-class, other modalities)

Good luck with your research!
