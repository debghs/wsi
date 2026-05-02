"""
Dataset Preparation Guide and Helper Scripts
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path


DATASET_SOURCES = {
    'camelyon16': {
        'name': 'CAMELYON16 - Lymph Node Metastasis Detection',
        'url': 'https://camelyon16.grand-challenge.org/',
        'download': 'Manual download after registration',
        'size': '~100 GB',
        'task': 'Binary classification (normal/metastasis)',
        'slides': '400 training slides',
    },
    'camelyon17': {
        'name': 'CAMELYON17 - Lymph Node Metastasis Detection',
        'url': 'https://camelyon17.grand-challenge.org/',
        'download': 'Manual download after registration',
        'size': '~130 GB',
        'task': 'Tumor classification',
        'slides': '1000 slides',
    },
    'tcga': {
        'name': 'TCGA - The Cancer Genome Atlas',
        'url': 'https://portal.gdc.cancer.gov/',
        'download': 'GDC Data Transfer Tool or web browser',
        'size': 'Varies (~1+ TB)',
        'task': 'Multiple cancer types',
        'slides': '10,000+ slides',
    },
}


def create_labels_csv(dataset_dir, output_path, dataset_name='camelyon16'):
    """
    Create labels CSV for dataset
    
    Args:
        dataset_dir (str): Directory containing slides
        output_path (str): Output CSV path
        dataset_name (str): Dataset name
    """
    slides = []
    labels = []
    
    if dataset_name == 'camelyon16':
        # CAMELYON16 structure:
        # data/
        #   ├── tumor_slides/  (label=1)
        #   └── normal_slides/ (label=0)
        
        tumor_dir = os.path.join(dataset_dir, 'tumor_slides')
        normal_dir = os.path.join(dataset_dir, 'normal_slides')
        
        # Tumor slides
        if os.path.exists(tumor_dir):
            for slide in Path(tumor_dir).glob('*.svs'):
                slides.append(slide.name)
                labels.append(1)
        
        # Normal slides
        if os.path.exists(normal_dir):
            for slide in Path(normal_dir).glob('*.svs'):
                slides.append(slide.name)
                labels.append(0)
    
    elif dataset_name == 'tcga':
        # TCGA structure: organize by cancer type
        # You need to manually label based on pathology reports
        for slide_file in Path(dataset_dir).glob('*.svs'):
            slides.append(slide_file.name)
            # Placeholder - you need actual labels
            labels.append(np.random.randint(0, 2))
    
    # Create DataFrame
    df = pd.DataFrame({
        'path': slides,
        'label': labels,
    })
    
    df.to_csv(output_path, index=False)
    print(f"Created labels CSV: {output_path}")
    print(f"Total slides: {len(df)}")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    
    return df


def validate_dataset(dataset_dir, csv_path):
    """
    Validate dataset integrity
    
    Args:
        dataset_dir (str): Dataset directory
        csv_path (str): Labels CSV path
    """
    df = pd.read_csv(csv_path)
    
    missing = 0
    for idx, row in df.iterrows():
        slide_path = os.path.join(dataset_dir, row['path'])
        if not os.path.exists(slide_path):
            print(f"Missing: {slide_path}")
            missing += 1
    
    print(f"\nValidation Results:")
    print(f"Total slides: {len(df)}")
    print(f"Missing files: {missing}")
    print(f"Status: {'OK' if missing == 0 else 'ERRORS FOUND'}")
    
    return missing == 0


if __name__ == '__main__':
    print("DATASET PREPARATION GUIDE")
    print("=" * 70)
    print()
    
    for name, info in DATASET_SOURCES.items():
        print(f"{name.upper()}")
        print(f"  Name: {info['name']}")
        print(f"  URL: {info['url']}")
        print(f"  Download: {info['download']}")
        print(f"  Size: {info['size']}")
        print(f"  Task: {info['task']}")
        print(f"  Slides: {info['slides']}")
        print()
