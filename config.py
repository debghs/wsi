"""
ASTRA Configuration File
"""

CONFIG = {
    # Dataset
    "data_root": "/home/debghs/coding/final_yr_project/data",
    "dataset_name": "camelyon16",  # Options: camelyon16, camelyon17, tcga
    
    # WSI
    "wsi_level": 2,  # Magnification level (0=40x, 1=10x, 2=2.5x, etc)
    "tile_size": 256,
    "patch_size": 224,  # Final patch size for model input
    
    # Tiling modes
    "tiling_mode": "adaptive",  # Options: adaptive, uniform, random
    "top_k_ratio": 0.7,  # Keep top 70% of patches
    
    # Model
    "backbone": "resnet18",
    "pretrained": True,
    "feature_dim": 512,
    "num_classes": 2,
    
    # MIL Head
    "mil_hidden": 128,
    
    # Graph Transformer
    "graph_dim": 512,
    "graph_heads": 4,
    "graph_layers": 2,
    
    # Policy Network
    "policy_hidden": 64,
    
    # Training
    "batch_size": 16,
    "num_epochs": 20,
    "learning_rate": 1e-4,
    "weight_decay": 1e-5,
    "device": "cuda",
    
    # RL Policy
    "lambda_patches": 0.001,  # Reward = AUC - lambda * num_patches
    
    # Paths
    "model_save_dir": "/home/debghs/coding/final_yr_project/models_saved",
    "result_save_dir": "/home/debghs/coding/final_yr_project/results",
    "figure_save_dir": "/home/debghs/coding/final_yr_project/figures",
    
    # Logging
    "log_interval": 10,
    "save_interval": 5,
    
    # Augmentation
    "augment": False,
    
    # Random seed
    "seed": 42,
}
