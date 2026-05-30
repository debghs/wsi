"""
Adaptive Tiling Module
Generates patches using different strategies
"""

import numpy as np
from tqdm import tqdm


def adaptive_tiles(image, graph, base_tile=256, min_tile=64, max_tile=512):
    """
    Generate tiles adaptively based on complexity
    
    Args:
        image (np.ndarray): RGB image (H, W, 3)
        graph (TissueGraph): Tissue graph
        base_tile (int): Base tile size
        min_tile (int): Minimum tile size
        max_tile (int): Maximum tile size
        
    Returns:
        list: List of dicts with keys: 'patch', 'coords', 'node_id', 'size'
    """
    tiles = []
    h, w = image.shape[:2]
    
    try:
        valid_nodes = graph.filter_by_tissue_probability(threshold=0.1)
        
        if len(valid_nodes) == 0:
            # Fallback if no valid nodes
            return uniform_tiles(image, tile_size=base_tile, stride=base_tile//2)
        
        for node_id in valid_nodes:
            try:
                node_data = graph.get_node_features(node_id)
                complexity = node_data.get('complexity', 0.5)
                
                # Adaptive sizing: high complexity → smaller tiles
                tile_size = int(base_tile / (1.0 + complexity * 3.0))
                tile_size = max(min_tile, min(tile_size, max_tile))
                
                # Get region centroid
                mask = graph.get_node_mask(node_id)
                coords = np.argwhere(mask)
                
                if len(coords) == 0:
                    continue
                
                cy, cx = coords.mean(axis=0).astype(int)
                
                # Extract patch centered at region
                x1 = max(0, cx - tile_size // 2)
                y1 = max(0, cy - tile_size // 2)
                x2 = min(w, x1 + tile_size)
                y2 = min(h, y1 + tile_size)
                
                # Ensure valid patch
                if x2 - x1 < 32 or y2 - y1 < 32:
                    continue
                
                patch = image[y1:y2, x1:x2]
                
                tiles.append({
                    'patch': patch,
                    'coords': (x1, y1, x2, y2),
                    'node_id': node_id,
                    'size': tile_size,
                    'complexity': complexity,
                })
            except Exception as e:
                continue
        
        # Fallback if no tiles were generated
        if len(tiles) == 0:
            return uniform_tiles(image, tile_size=base_tile, stride=base_tile//2)
        
        return tiles
    
    except Exception as e:
        # Fallback to uniform tiling
        return uniform_tiles(image, tile_size=base_tile, stride=base_tile//2)


def uniform_tiles(image, tile_size=256, stride=None):
    """
    Generate tiles in uniform grid pattern
    
    Args:
        image (np.ndarray): RGB image
        tile_size (int): Tile size
        stride (int): Stride (if None, equals tile_size)
        
    Returns:
        list: List of tile dicts
    """
    if stride is None:
        stride = tile_size
    
    tiles = []
    h, w = image.shape[:2]
    
    for y in range(0, h - tile_size + 1, stride):
        for x in range(0, w - tile_size + 1, stride):
            patch = image[y:y+tile_size, x:x+tile_size]
            
            if patch.shape[0] != tile_size or patch.shape[1] != tile_size:
                continue
            
            tiles.append({
                'patch': patch,
                'coords': (x, y, x + tile_size, y + tile_size),
                'node_id': -1,
                'size': tile_size,
                'complexity': 0.0,
            })
    
    return tiles


def random_tiles(image, n_tiles=200, tile_size=256):
    """
    Generate random tiles
    
    Args:
        image (np.ndarray): RGB image
        n_tiles (int): Number of tiles to extract
        tile_size (int): Tile size
        
    Returns:
        list: List of tile dicts
    """
    tiles = []
    h, w = image.shape[:2]
    
    for _ in range(n_tiles):
        if w < tile_size or h < tile_size:
            break
        
        x = np.random.randint(0, w - tile_size)
        y = np.random.randint(0, h - tile_size)
        patch = image[y:y+tile_size, x:x+tile_size]
        
        tiles.append({
            'patch': patch,
            'coords': (x, y, x + tile_size, y + tile_size),
            'node_id': -1,
            'size': tile_size,
            'complexity': 0.0,
        })
    
    return tiles


def filter_tiles_by_area(tiles, min_area=0.3):
    """
    Filter out tiles that are mostly white/empty
    
    Args:
        tiles (list): List of tile dicts
        min_area (float): Minimum tissue area ratio
        
    Returns:
        list: Filtered tiles
    """
    filtered = []
    
    for tile_dict in tiles:
        patch = tile_dict['patch']
        
        # Check if mostly white (background)
        gray = patch.mean(axis=2)
        tissue_ratio = (gray < 240).mean()
        
        if tissue_ratio > min_area:
            filtered.append(tile_dict)
    
    return filtered
