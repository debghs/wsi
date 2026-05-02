# Test dataset configuration
DATASET_DIR = "data/test_slides/slides"
LABELS_CSV = "data/test_slides/labels.csv"
NUM_SLIDES = 4
NUM_NORMAL = 2
NUM_TUMOR = 2

# For testing - use smaller model and fewer epochs
TEST_CONFIG = {
    'num_epochs': 5,  # Reduced from 20
    'batch_size': 2,  # Very small batch
    'num_workers': 0,  # No multiprocessing for stability
    'tile_size': 256,
    'top_k_ratio': 0.7,
}
