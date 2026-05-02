#!/bin/bash

#############################################################################
# ASTRA Research Project - Complete Setup & Execution Guide
# For computational pathology WSI analysis
#############################################################################

set -e  # Exit on any error

echo "=========================================================================="
echo "ASTRA: Adaptive Semantic Tiling with Reinforced Attention"
echo "Complete Research Project Setup"
echo "=========================================================================="
echo ""

# Configuration
PROJECT_DIR="/home/debghs/coding/final_yr_project"
DATA_DIR="$PROJECT_DIR/data"
ENV_NAME="astra"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}PHASE 0: Environment Setup${NC}"
echo "=========================================================================="
echo ""

# Check conda
if ! command -v conda &> /dev/null; then
    echo -e "${YELLOW}Conda not found. Please install Miniconda first.${NC}"
    echo "Download from: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create conda environment
echo "Creating conda environment: $ENV_NAME"
conda create -n $ENV_NAME python=3.10 -y
conda activate $ENV_NAME

# Install PyTorch (CPU version - change to cuda if you have NVIDIA GPU)
echo "Installing PyTorch..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install requirements
echo "Installing dependencies..."
pip install -r "$PROJECT_DIR/requirements.txt"

echo -e "${GREEN}✓ Environment setup complete${NC}"
echo ""

echo -e "${BLUE}PHASE 1: Verify Installation${NC}"
echo "=========================================================================="
echo ""

# Test imports
python3 << EOF
import sys
print("Python version:", sys.version)

try:
    import torch
    print(f"✓ PyTorch {torch.__version__}")
except ImportError as e:
    print(f"✗ PyTorch error: {e}")

try:
    import cv2
    print(f"✓ OpenCV {cv2.__version__}")
except ImportError as e:
    print(f"✗ OpenCV error: {e}")

try:
    import openslide
    print(f"✓ OpenSlide installed")
except ImportError as e:
    print(f"✗ OpenSlide error: {e}")

try:
    import pandas, numpy, sklearn
    print(f"✓ NumPy, Pandas, Scikit-learn installed")
except ImportError as e:
    print(f"✗ Error: {e}")

print("\nAll dependencies verified!")
EOF

echo -e "${GREEN}✓ Dependencies verified${NC}"
echo ""

echo -e "${BLUE}PHASE 2: Dataset Preparation${NC}"
echo "=========================================================================="
echo ""

echo "Dataset preparation has 3 steps:"
echo ""
echo "STEP 1: Download CAMELYON16"
echo "  URL: https://camelyon16.grand-challenge.org/"
echo "  1. Register account"
echo "  2. Download training dataset (~100 GB)"
echo "  3. Extract to: $DATA_DIR/camelyon16/slides/"
echo ""
echo "STEP 2: Create labels CSV"
echo "  After downloading, run:"
echo "  python3 prepare_datasets.py"
echo ""
echo "STEP 3: Validate dataset"
echo "  python3 -c \"from prepare_datasets import validate_dataset; validate_dataset('$DATA_DIR/camelyon16', '$DATA_DIR/camelyon16/labels.csv')\""
echo ""

# Create data directories
mkdir -p "$DATA_DIR/camelyon16/slides"
mkdir -p "$DATA_DIR/camelyon17/slides"
mkdir -p "$DATA_DIR/tcga/slides"

echo -e "${YELLOW}⚠ Please manually download datasets before proceeding${NC}"
echo ""

echo -e "${BLUE}PHASE 3: Run Training Experiments${NC}"
echo "=========================================================================="
echo ""

echo "After setting up datasets, run experiments with:"
echo ""
echo "# Single experiment (uniform tiling baseline)"
echo "  python3 train.py --dataset camelyon16 --mode uniform --epochs 5"
echo ""
echo "# Adaptive tiling (main method)"
echo "  python3 train.py --dataset camelyon16 --mode adaptive --epochs 20"
echo ""
echo "# Run all experiments"
echo "  python3 experiments.py --mode full --dataset camelyon16"
echo ""
echo "# Run ablation study"
echo "  python3 experiments.py --mode ablation --dataset camelyon16"
echo ""

echo -e "${BLUE}PHASE 4: Evaluate & Visualize${NC}"
echo "=========================================================================="
echo ""

echo "After training, evaluate results:"
echo ""
echo "# Evaluate model"
echo "  python3 evaluate.py --model results/path/to/best_model.pth --dataset camelyon16"
echo ""
echo "# Generate visualizations"
echo "  python3 visualizations.py"
echo ""

echo -e "${BLUE}PHASE 5: Write Paper${NC}"
echo "=========================================================================="
echo ""

echo "Paper template ready at: $PROJECT_DIR/paper/main.tex"
echo ""
echo "To compile LaTeX (on Linux/Mac):"
echo "  cd $PROJECT_DIR/paper"
echo "  pdflatex main.tex"
echo "  bibtex main"
echo "  pdflatex main.tex"
echo "  pdflatex main.tex"
echo ""
echo "Or use Overleaf: https://www.overleaf.com"
echo ""

echo -e "${GREEN}=========================================================================="
echo "Setup Complete!"
echo "=========================================================================="
echo ""

echo "Quick Start Checklist:"
echo "[ ] Download and extract CAMELYON16 dataset"
echo "[ ] Create labels.csv file"
echo "[ ] Run: python3 train.py --dataset camelyon16 --mode uniform --epochs 5"
echo "[ ] Run: python3 train.py --dataset camelyon16 --mode adaptive --epochs 20"
echo "[ ] Compare results"
echo "[ ] Run full experiments: python3 experiments.py --mode full"
echo "[ ] Generate figures: python3 visualizations.py"
echo "[ ] Fill paper tables with results"
echo "[ ] Compile paper"
echo ""

echo "Project Structure:"
echo "  $PROJECT_DIR/"
echo "  ├── pipeline/          # Core components (tiling, graphs, etc)"
echo "  ├── models/            # Neural network models"
echo "  ├── datasets/          # Dataset handling"
echo "  ├── data/              # Data directory (populate with WSIs)"
echo "  ├── results/           # Training outputs"
echo "  ├── figures/           # Generated figures"
echo "  ├── paper/             # LaTeX paper template"
echo "  ├── train.py           # Training script"
echo "  ├── evaluate.py        # Evaluation script"
echo "  ├── experiments.py     # Experiment runner"
echo "  ├── visualizations.py  # Figure generation"
echo "  └── config.py          # Configuration"
echo ""

echo "Documentation:"
echo "  - See README.md for detailed instructions"
echo "  - See paper/main.tex for paper structure"
echo "  - See config.py for adjustable parameters"
echo ""
