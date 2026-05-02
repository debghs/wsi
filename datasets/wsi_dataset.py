"""
WSI Dataset Module
"""

import os
import pandas as pd
import numpy as np
import torch
import cv2
from torch.utils.data import Dataset
from tqdm import tqdm
import torchvision.transforms as T

from pipeline.wsi import WSIReader
from pipeline.maps import compute_all_maps, apply_morphology
from pipeline.graph import TissueGraph
from pipeline.tiling import adaptive_tiles, uniform_tiles, random_tiles, filter_tiles_by_area
from pipeline.scoring import score_patches_by_entropy


class WSIDataset(Dataset):
    """
    Dataset for WSI analysis
    """
    
    def __init__(self, csv_path, data_root, mode='adaptive', patch_size=224, 
                 wsi_level=2, top_k_ratio=0.7, cache=False):
        """
        Initialize WSI Dataset
        
        Args:
            csv_path (str): Path to CSV with slide paths and labels
            data_root (str): Root directory for data
            mode (str): Tiling mode ('adaptive', 'uniform', 'random')
            patch_size (int): Final patch size for model
            wsi_level (int): WSI resolution level
            top_k_ratio (float): Keep top-k% of patches
            cache (bool): Cache patches to disk
        """
        self.df = pd.read_csv(csv_path)
        self.data_root = data_root
        self.mode = mode
        self.patch_size = patch_size
        self.wsi_level = wsi_level
        self.top_k_ratio = top_k_ratio
        self.cache = cache
        
        # Transform for patches
        self.transform = T.Compose([
            T.ToPILImage(),
            T.Resize((patch_size, patch_size)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406],
                       std=[0.229, 0.224, 0.225]),
        ])
        
        # Cache directory
        if cache:
            self.cache_dir = os.path.join(data_root, f'cache_{mode}')
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        """
        Get sample
        
        Returns:
            dict: 'patches' (Tensor list), 'label' (int), 'n_patches' (int)
        """
        row = self.df.iloc[idx]
        slide_path = os.path.join(self.data_root, row['path'])
        label = int(row['label'])
        
        # Check cache
        cache_key = os.path.basename(slide_path).replace('.svs', '')
        cached_file = None
        
        if self.cache:
            cached_file = os.path.join(self.cache_dir, f'{cache_key}.npy')
            if os.path.exists(cached_file):
                patches = np.load(cached_file, allow_pickle=True)
                return {
                    'patches': patches,
                    'label': label,
                    'n_patches': len(patches),
                }
        
        # Load and process WSI
        try:
            with WSIReader(slide_path) as reader:
                image = reader.get_level(self.wsi_level)
        except Exception as e:
            print(f"Error reading {slide_path}: {e}")
            return None
        
        # Generate segmentation maps
        tissue_mask, complexity, uncertainty = compute_all_maps(image)
        tissue_mask = apply_morphology(tissue_mask, 'close')
        
        # Build tissue graph
        graph = TissueGraph(image, tissue_mask, complexity, n_segments=2000)
        
        # Extract tiles based on mode
        if self.mode == 'adaptive':
            tiles = adaptive_tiles(image, graph)
        elif self.mode == 'uniform':
            tiles = uniform_tiles(image, tile_size=256)
        elif self.mode == 'random':
            tiles = random_tiles(image, n_tiles=200, tile_size=256)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
        
        # Filter and score tiles
        tiles = filter_tiles_by_area(tiles)
        tiles = score_patches_by_entropy(tiles, self.top_k_ratio)
        
        # Extract patches and convert to tensors
        patches = []
        for tile_dict in tiles:
            patch = tile_dict['patch']
            
            # Resize if needed
            if patch.shape[0] != self.patch_size or patch.shape[1] != self.patch_size:
                patch = cv2.resize(patch, (self.patch_size, self.patch_size))
            
            # Transform
            patch_tensor = self.transform(patch)
            patches.append(patch_tensor)
        
        # Convert to tensor
        if len(patches) > 0:
            patches = torch.stack(patches)
        else:
            # Return empty tensor if no patches
            patches = torch.zeros((1, 3, self.patch_size, self.patch_size))
        
        # Cache patches
        if self.cache and cached_file:
            np.save(cached_file, patches.numpy())
        
        return {
            'patches': patches,
            'label': label,
            'n_patches': len(patches),
        }


def collate_fn(batch):
    """
    Custom collate function for variable-length patch sequences
    """
    # Filter out None entries
    batch = [b for b in batch if b is not None]
    
    if len(batch) == 0:
        return None
    
    # For now, return batch as-is (will need special handling in training loop)
    return batch
