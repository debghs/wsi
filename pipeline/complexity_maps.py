"""
Enhanced Complexity Maps with Stain-Robustness
Computes complexity using structure detection and texture analysis
instead of variance (which is fooled by staining).
"""

import numpy as np
import cv2
from scipy import ndimage
from skimage import filters
from skimage.feature import local_binary_pattern


def normalize_0_1(arr):
    """
    Normalize array to [0, 1].
    
    Args:
        arr (np.ndarray): Input array
        
    Returns:
        np.ndarray: Normalized array
    """
    arr_min = arr.min()
    arr_max = arr.max()
    
    if arr_max == arr_min:
        return arr
    
    return (arr - arr_min) / (arr_max - arr_min)


def compute_laplacian_of_gaussian(image, sigma_range=(1, 5)):
    """
    Compute Laplacian of Gaussian - detects blob-like structures (nuclei, glands).
    
    More biologically meaningful than Sobel edges.
    Ignores linear edges (stain boundaries, folds).
    
    Args:
        image (np.ndarray): RGB or grayscale image
        sigma_range (tuple): (min_sigma, max_sigma) for scale range
        
    Returns:
        np.ndarray: LoG response map (0-1 normalized)
    """
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = np.mean(image, axis=2).astype(float) / 255.0
    else:
        gray = image.astype(float) / 255.0
    
    # Compute LoG at multiple scales
    log_responses = []
    for sigma in np.linspace(sigma_range[0], sigma_range[1], 5):
        # Laplacian of Gaussian
        log = ndimage.gaussian_laplace(gray, sigma=sigma)
        log_responses.append(np.abs(log))
    
    # Take maximum response across scales
    structure_map = np.max(log_responses, axis=0)
    
    return normalize_0_1(structure_map)


def compute_entropy_map(image, window_size=32):
    """
    Compute entropy (information content) map.
    
    High entropy = diverse pixel values = potentially biologically interesting.
    
    Args:
        image (np.ndarray): RGB or grayscale image
        window_size (int): Window size for local entropy
        
    Returns:
        np.ndarray: Entropy map (0-1 normalized)
    """
    
    if image.dtype == np.float32 or image.dtype == np.float64:
        image = (image * 255).astype(np.uint8)
    elif image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image
    
    H, W = gray.shape
    entropy_map = np.zeros((H, W))
    
    stride = window_size // 2
    
    for y in range(0, H - window_size, stride):
        for x in range(0, W - window_size, stride):
            window = gray[y:y+window_size, x:x+window_size]
            
            # Compute histogram
            hist, _ = np.histogram(window, bins=256, range=(0, 256))
            hist = hist / hist.sum()
            
            # Entropy = -sum(p * log2(p))
            # Avoid log(0)
            entropy = -np.sum(hist[hist > 0] * np.log2(hist[hist > 0]))
            
            entropy_map[y:y+window_size, x:x+window_size] = entropy
    
    return normalize_0_1(entropy_map)


def compute_nuclei_density_map(image, dark_threshold=50, window_size=32):
    """
    Compute nuclei density map.
    
    Nuclei appear as dark regions in H&E staining.
    
    Args:
        image (np.ndarray): RGB image
        dark_threshold (int): Threshold for dark pixels (0-255)
        window_size (int): Window size for local density
        
    Returns:
        np.ndarray: Nuclei density map (0-1 normalized)
    """
    
    if image.dtype == np.float32 or image.dtype == np.float64:
        image = (image * 255).astype(np.uint8)
    elif image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Dark regions (nuclei)
    dark_mask = gray < dark_threshold
    
    H, W = gray.shape
    nuclei_map = np.zeros((H, W))
    
    stride = window_size // 2
    
    for y in range(0, H - window_size, stride):
        for x in range(0, W - window_size, stride):
            window = dark_mask[y:y+window_size, x:x+window_size]
            
            # Nuclei density = fraction of dark pixels
            density = np.mean(window.astype(float))
            nuclei_map[y:y+window_size, x:x+window_size] = density
    
    return normalize_0_1(nuclei_map)


def compute_lbp_texture_map(image, window_size=32):
    """
    Compute Local Binary Pattern texture map.
    
    Detects recurring texture patterns.
    
    Args:
        image (np.ndarray): RGB or grayscale image
        window_size (int): Window size for local texture
        
    Returns:
        np.ndarray: LBP texture map (0-1 normalized)
    """
    
    if image.dtype == np.float32 or image.dtype == np.float64:
        image = (image * 255).astype(np.uint8)
    elif image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image
    
    H, W = gray.shape
    lbp_map = np.zeros((H, W))
    
    stride = window_size // 2
    
    for y in range(0, H - window_size, stride):
        for x in range(0, W - window_size, stride):
            window = gray[y:y+window_size, x:x+window_size]
            
            # Compute LBP
            lbp = local_binary_pattern(window, 8, 1, method='uniform')
            
            # Texture complexity = std of LBP values
            texture_complexity = np.std(lbp)
            lbp_map[y:y+window_size, x:x+window_size] = texture_complexity
    
    return normalize_0_1(lbp_map)


def compute_stain_robust_complexity_map(image, 
                                       window_size=32,
                                       normalize_stains=True):
    """
    Compute complexity map robust to staining artifacts.
    
    Combines:
    - Laplacian of Gaussian (structure detection)
    - Entropy (information content)
    - Nuclei density (cell count)
    - LBP texture (texture patterns)
    
    Does NOT use variance (too sensitive to staining artifacts).
    
    Args:
        image (np.ndarray): RGB image
        window_size (int): Window size for local analysis
        normalize_stains (bool): Whether to normalize stains first
        
    Returns:
        np.ndarray: Complexity map (0-1 normalized)
    """
    
    # Validate input
    if image.dtype == np.float32 or image.dtype == np.float64:
        image = (image * 255).astype(np.uint8)
    elif image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Remove alpha if present
    if len(image.shape) == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    
    # Step 1: Stain normalization (optional, recommended)
    if normalize_stains:
        try:
            from .stain_norm import normalize_stain
            image = normalize_stain(image)
        except Exception as e:
            # If normalization fails, continue without it
            pass
    
    # Step 2: Compute component maps
    structure_map = compute_laplacian_of_gaussian(image)
    entropy_map = compute_entropy_map(image, window_size)
    nuclei_map = compute_nuclei_density_map(image, window_size=window_size)
    lbp_map = compute_lbp_texture_map(image, window_size)
    
    # Step 3: Weighted combination
    complexity = (
        0.40 * structure_map +    # Blob detection (nuclei, glands)
        0.25 * entropy_map +      # Information content
        0.20 * nuclei_map +       # Cell density
        0.15 * lbp_map            # Texture patterns
    )
    
    # Step 4: Smooth to reduce noise
    complexity = ndimage.gaussian_filter(complexity, sigma=window_size/4)
    
    return normalize_0_1(complexity)


# Test function
def test_complexity_maps():
    """
    Test all complexity map functions.
    """
    try:
        # Create synthetic image
        img = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
        
        # Test each component
        structure = compute_laplacian_of_gaussian(img)
        assert structure.shape == (256, 256), "Structure map shape wrong"
        assert 0 <= structure.min() <= structure.max() <= 1, "Structure values out of range"
        
        entropy = compute_entropy_map(img)
        assert entropy.shape == (256, 256), "Entropy map shape wrong"
        assert 0 <= entropy.min() <= entropy.max() <= 1, "Entropy values out of range"
        
        nuclei = compute_nuclei_density_map(img)
        assert nuclei.shape == (256, 256), "Nuclei map shape wrong"
        assert 0 <= nuclei.min() <= nuclei.max() <= 1, "Nuclei values out of range"
        
        lbp = compute_lbp_texture_map(img)
        assert lbp.shape == (256, 256), "LBP map shape wrong"
        assert 0 <= lbp.min() <= lbp.max() <= 1, "LBP values out of range"
        
        complexity = compute_stain_robust_complexity_map(img, normalize_stains=False)
        assert complexity.shape == (256, 256), "Complexity map shape wrong"
        assert 0 <= complexity.min() <= complexity.max() <= 1, "Complexity values out of range"
        
        print("✅ All complexity map tests passed")
        return True
    except Exception as e:
        print(f"❌ Complexity map test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_complexity_maps()
