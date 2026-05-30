"""
Stain-Robust Adaptive Tiling Module
Intelligently samples image regions based on tissue complexity, 
resistant to staining artifacts.
"""

import numpy as np
from scipy import ndimage


def adaptive_tiles_complexity_based(image,
                                   base_patch_size=256,
                                   min_patch_size=128,
                                   complexity_threshold=0.4,
                                   target_patch_count=None,
                                   normalize_stains=True):
    """
    Generate tiles adaptively based on stain-robust complexity map.
    
    Strategy:
    1. Compute complexity map (stain-normalized, structure-based)
    2. In high-complexity regions: sample patches densely
    3. In low-complexity regions: sample patches sparsely
    4. Ensure coverage while minimizing redundancy
    
    Args:
        image (np.ndarray): Input RGB image (H, W, 3), uint8
        base_patch_size (int): Target patch size (default 256)
        min_patch_size (int): Minimum patch size (default 128)
        complexity_threshold (float): 0-1, regions above this are "interesting"
        target_patch_count (int): If set, adjust number of patches to this count
        normalize_stains (bool): Whether to normalize stains before complexity
        
    Returns:
        tuple: (tiles, complexity_map) where tiles is list of dicts with:
               - 'coords': (x1, y1, x2, y2) coordinates
               - 'complexity_score': float 0-1
               - 'type': 'adaptive_high' or 'adaptive_low'
               - 'size': (width, height) in pixels
    """
    
    from .complexity_maps import compute_stain_robust_complexity_map
    
    # Validate input
    if image.dtype != np.uint8:
        if image.dtype in [np.float32, np.float64]:
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            else:
                image = np.clip(image, 0, 255).astype(np.uint8)
        else:
            image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Remove alpha if present
    if len(image.shape) == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    
    H, W = image.shape[:2]
    
    # Step 1: Compute complexity map
    complexity_map = compute_stain_robust_complexity_map(
        image,
        window_size=32,
        normalize_stains=normalize_stains
    )
    
    # Step 2: Identify high-complexity regions
    high_complexity_mask = complexity_map > complexity_threshold
    
    # Step 3: Adaptive sampling
    tiles = []
    stride_high = base_patch_size // 2      # Dense in high-complexity (50% overlap)
    stride_low = base_patch_size            # Sparse in low-complexity (no overlap)
    
    # Process high-complexity regions with dense sampling
    for y in range(0, H - base_patch_size, stride_high):
        for x in range(0, W - base_patch_size, stride_high):
            
            # Check mean complexity in this region
            region_complexity = complexity_map[
                y:y+base_patch_size,
                x:x+base_patch_size
            ].mean()
            
            # Always include high-complexity regions
            if region_complexity >= complexity_threshold:
                x2 = min(x + base_patch_size, W)
                y2 = min(y + base_patch_size, H)
                
                # Check size
                if (x2 - x) >= min_patch_size and (y2 - y) >= min_patch_size:
                    tiles.append({
                        'coords': (x, y, x2, y2),
                        'type': 'adaptive_high',
                        'complexity_score': float(region_complexity),
                        'size': (x2 - x, y2 - y)
                    })
    
    # Process low-complexity regions with sparse sampling
    # Only take 25% of potential tiles in low-complexity areas
    for y in range(0, H - base_patch_size, stride_low):
        for x in range(0, W - base_patch_size, stride_low):
            
            # Check mean complexity in this region
            region_complexity = complexity_map[
                y:y+base_patch_size,
                x:x+base_patch_size
            ].mean()
            
            # Sparse sampling in low-complexity
            if region_complexity < complexity_threshold:
                if np.random.random() > 0.75:  # Keep 25%
                    x2 = min(x + base_patch_size, W)
                    y2 = min(y + base_patch_size, H)
                    
                    # Check size
                    if (x2 - x) >= min_patch_size and (y2 - y) >= min_patch_size:
                        tiles.append({
                            'coords': (x, y, x2, y2),
                            'type': 'adaptive_low',
                            'complexity_score': float(region_complexity),
                            'size': (x2 - x, y2 - y)
                        })
    
    # Step 4: Remove overlapping tiles (keep higher complexity ones)
    tiles = _deduplicate_tiles(tiles)
    
    # Step 5: Adjust to target count if specified
    if target_patch_count is not None and len(tiles) != target_patch_count:
        tiles = _resample_tiles_to_count(
            tiles,
            target_count=target_patch_count,
            complexity_map=complexity_map,
            image_shape=(H, W),
            base_patch_size=base_patch_size
        )
    
    return tiles, complexity_map


def _deduplicate_tiles(tiles, overlap_threshold=0.3):
    """
    Remove overlapping tiles, keeping ones with higher complexity.
    
    Args:
        tiles (list): List of tile dicts with 'coords' and 'complexity_score'
        overlap_threshold (float): IoU threshold (default 0.3)
        
    Returns:
        list: Deduplicated tiles
    """
    
    if not tiles:
        return tiles
    
    # Sort by complexity (descending) to keep high-complexity tiles
    tiles = sorted(tiles, key=lambda t: t['complexity_score'], reverse=True)
    
    kept_tiles = []
    
    for tile in tiles:
        x1, y1, x2, y2 = tile['coords']
        
        # Check overlap with already-kept tiles
        overlaps_existing = False
        
        for kept_tile in kept_tiles:
            kx1, ky1, kx2, ky2 = kept_tile['coords']
            
            # Calculate intersection area
            intersection_x = max(0, min(x2, kx2) - max(x1, kx1))
            intersection_y = max(0, min(y2, ky2) - max(y1, ky1))
            intersection_area = intersection_x * intersection_y
            
            # Calculate areas
            tile_area = (x2 - x1) * (y2 - y1)
            kept_area = (kx2 - kx1) * (ky2 - ky1)
            union_area = tile_area + kept_area - intersection_area
            
            # IoU (Intersection over Union)
            iou = intersection_area / union_area if union_area > 0 else 0
            
            if iou > overlap_threshold:
                overlaps_existing = True
                break
        
        if not overlaps_existing:
            kept_tiles.append(tile)
    
    return kept_tiles


def _resample_tiles_to_count(tiles, 
                            target_count, 
                            complexity_map, 
                            image_shape,
                            base_patch_size):
    """
    Adjust number of tiles to match target count.
    
    If too many: Remove lowest-complexity tiles
    If too few: Add more from highest-complexity regions
    
    Args:
        tiles (list): Current tiles
        target_count (int): Target number of tiles
        complexity_map (np.ndarray): Complexity map
        image_shape (tuple): (H, W)
        base_patch_size (int): Patch size for new tiles
        
    Returns:
        list: Resampled tiles
    """
    
    current_count = len(tiles)
    
    if current_count == target_count:
        return tiles
    
    elif current_count > target_count:
        # Too many: remove lowest-complexity tiles
        tiles = sorted(tiles, key=lambda t: t['complexity_score'], reverse=True)
        return tiles[:target_count]
    
    else:
        # Too few: add new tiles in high-complexity regions
        needed = target_count - current_count
        H, W = image_shape
        
        # Mark occupied regions
        occupied = np.zeros((H, W), dtype=bool)
        for tile in tiles:
            x1, y1, x2, y2 = tile['coords']
            occupied[y1:y2, x1:x2] = True
        
        # Probability map: high complexity + unoccupied
        available_complexity = complexity_map.copy()
        available_complexity[occupied] = 0
        
        new_tiles = []
        
        for _ in range(needed):
            if available_complexity.sum() == 0:
                break
            
            # Weighted sampling by complexity
            prob = available_complexity.flatten() / available_complexity.sum()
            flat_idx = np.random.choice(H * W, p=prob)
            y, x = np.unravel_index(flat_idx, (H, W))
            
            # Create tile centered at (x, y)
            x1 = max(0, x - base_patch_size // 2)
            y1 = max(0, y - base_patch_size // 2)
            x2 = min(W, x1 + base_patch_size)
            y2 = min(H, y1 + base_patch_size)
            
            # Mark as occupied
            occupied[y1:y2, x1:x2] = True
            available_complexity[y1:y2, x1:x2] = 0
            
            new_tiles.append({
                'coords': (x1, y1, x2, y2),
                'type': 'adaptive_added',
                'complexity_score': float(complexity_map[y1:y2, x1:x2].mean()),
                'size': (x2 - x1, y2 - y1)
            })
        
        tiles.extend(new_tiles)
        return _deduplicate_tiles(tiles)


def uniform_tiles(image, patch_size=256, stride=None):
    """
    Generate uniform grid tiles (baseline for comparison).
    
    Args:
        image (np.ndarray): Input image
        patch_size (int): Patch size
        stride (int): Stride (if None, equals patch_size)
        
    Returns:
        list: List of tile dicts
    """
    
    if stride is None:
        stride = patch_size
    
    H, W = image.shape[:2]
    tiles = []
    
    for y in range(0, H - patch_size + 1, stride):
        for x in range(0, W - patch_size + 1, stride):
            tiles.append({
                'coords': (x, y, x + patch_size, y + patch_size),
                'type': 'uniform',
                'complexity_score': 0.5,  # Unknown
                'size': (patch_size, patch_size)
            })
    
    return tiles


def random_tiles(image, num_tiles=10, patch_size=256):
    """
    Generate random tiles (baseline for comparison).
    
    Args:
        image (np.ndarray): Input image
        num_tiles (int): Number of random tiles
        patch_size (int): Patch size
        
    Returns:
        list: List of tile dicts
    """
    
    H, W = image.shape[:2]
    tiles = []
    
    for _ in range(num_tiles):
        if W <= patch_size or H <= patch_size:
            break
        
        x = np.random.randint(0, W - patch_size)
        y = np.random.randint(0, H - patch_size)
        
        tiles.append({
            'coords': (x, y, x + patch_size, y + patch_size),
            'type': 'random',
            'complexity_score': 0.5,  # Unknown
            'size': (patch_size, patch_size)
        })
    
    return tiles


# Test function
def test_adaptive_tiling():
    """
    Test adaptive tiling implementation.
    """
    try:
        # Create synthetic image
        img = np.random.randint(100, 200, (512, 512, 3), dtype=np.uint8)
        
        # Test adaptive tiling
        tiles_adaptive, complexity_map = adaptive_tiles_complexity_based(
            img,
            base_patch_size=256,
            complexity_threshold=0.4,
            normalize_stains=False
        )
        
        assert isinstance(tiles_adaptive, list), "Adaptive tiles not a list"
        assert len(tiles_adaptive) > 0, "No tiles generated"
        assert isinstance(complexity_map, np.ndarray), "Complexity map not ndarray"
        assert complexity_map.shape == (512, 512), "Complexity map shape wrong"
        
        # Check tile format
        for tile in tiles_adaptive:
            assert 'coords' in tile, "Missing coords"
            assert 'complexity_score' in tile, "Missing complexity_score"
            assert 'type' in tile, "Missing type"
            assert 'size' in tile, "Missing size"
            
            x1, y1, x2, y2 = tile['coords']
            assert x1 >= 0 and y1 >= 0 and x2 <= 512 and y2 <= 512, "Coords out of bounds"
        
        # Test uniform for comparison
        tiles_uniform = uniform_tiles(img, patch_size=256)
        assert isinstance(tiles_uniform, list), "Uniform tiles not a list"
        assert len(tiles_uniform) > 0, "No uniform tiles generated"
        
        print(f"✅ Adaptive tiling test passed")
        print(f"   Adaptive tiles: {len(tiles_adaptive)}")
        print(f"   Uniform tiles: {len(tiles_uniform)}")
        print(f"   Reduction: {100*(1 - len(tiles_adaptive)/len(tiles_uniform)):.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Adaptive tiling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_adaptive_tiling()
