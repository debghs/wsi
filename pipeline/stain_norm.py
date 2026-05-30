"""
Stain Normalization Module
Removes staining artifacts for robust image analysis.

Based on Macenko et al. (2009) method:
"A method for normalizing histology slides for quantitative analysis"
"""

import numpy as np
import cv2


def get_default_stain_matrix():
    """
    Get standard H&E stain matrix from literature.
    
    Macenko et al., 2009
    Hematoxylin: blue/purple (nuclei)
    Eosin: pink/red (cytoplasm/background)
    
    Returns:
        np.ndarray: Shape (3, 2), columns are stain vectors
    """
    # Hematoxylin and Eosin color vectors (normalized)
    stain_matrix = np.array([
        [0.65, 0.07],    # Hematoxylin (blue)
        [0.70, 0.99],    # Eosin (red)
        [0.29, 0.11]     # Background
    ])
    
    return stain_matrix


def ensure_uint8(image):
    """
    Convert image to uint8 if needed.
    
    Args:
        image (np.ndarray): Input image
        
    Returns:
        np.ndarray: uint8 image
    """
    if image.dtype == np.uint8:
        return image
    
    if image.dtype in [np.float32, np.float64]:
        # Check if values are in [0, 1] or [0, 255]
        if image.max() <= 1.0:
            return (image * 255).astype(np.uint8)
        else:
            return np.clip(image, 0, 255).astype(np.uint8)
    
    # For other integer types, clip and convert
    return np.clip(image, 0, 255).astype(np.uint8)


def remove_alpha_channel(image):
    """
    Remove alpha channel if present.
    
    Args:
        image (np.ndarray): Image with shape (H, W, C) where C in [3, 4]
        
    Returns:
        np.ndarray: RGB image (H, W, 3)
    """
    if len(image.shape) != 3:
        raise ValueError(f"Expected 3D image, got shape {image.shape}")
    
    if image.shape[2] == 4:
        return image[:, :, :3]
    elif image.shape[2] == 3:
        return image
    else:
        raise ValueError(f"Expected 3 or 4 channels, got {image.shape[2]}")


def estimate_stain_matrix(image, percentile=99):
    """
    Estimate H&E stain colors from image using SVD.
    
    The two largest eigenvectors of the optical density matrix
    correspond to the two main stain colors.
    
    Args:
        image (np.ndarray): RGB image (H, W, 3), uint8
        percentile (int): Percentile for outlier removal (default 99)
        
    Returns:
        np.ndarray: Estimated stain matrix (3, 2)
    """
    
    # Ensure image is RGB uint8
    image = remove_alpha_channel(image)
    image = ensure_uint8(image)
    
    # Convert to float for processing
    img_float = image.astype(np.float32) / 255.0
    
    # Avoid log(0) - set minimum
    img_float = np.clip(img_float, 0.001, 1.0)
    
    # Convert RGB to optical density (OD)
    # OD = -log(RGB)  [standard in histology]
    od = -np.log(img_float)
    
    # Reshape for analysis: (H*W, 3)
    od_flat = od.reshape(-1, 3)
    
    # Remove background (very low OD = white/empty)
    # and outliers (very high OD = black/debris)
    od_min = np.percentile(od_flat, 1, axis=0)
    od_max = np.percentile(od_flat, percentile, axis=0)
    
    # Keep only tissue pixels
    mask = np.all((od_flat >= od_min) & (od_flat <= od_max), axis=1)
    od_tissue = od_flat[mask]
    
    if len(od_tissue) < 100:
        # Not enough tissue pixels - use default stain matrix
        print("⚠️  Warning: Few tissue pixels, using default stain matrix")
        default_stains = get_default_stain_matrix()
        return default_stains
    
    # Find dominant stain colors using SVD
    # The two largest eigenvectors = two stain colors
    try:
        _, _, V = np.linalg.svd(od_tissue, full_matrices=False)
    except:
        print("⚠️  Warning: SVD failed, using default stain matrix")
        return get_default_stain_matrix()
    
    # First two components are the stain vectors
    # V has shape (min(H*W, 3), 3), we want first 2 rows
    stain_matrix = V[:2, :].T  # Shape: (3, 2)
    
    return stain_matrix


def normalize_stain(image, target_stain_matrix=None, source_stain_matrix=None):
    """
    Normalize stain colors in image using Macenko method.
    
    This removes staining intensity variations while preserving tissue structure.
    
    Args:
        image (np.ndarray): Input RGB image (H, W, 3)
        target_stain_matrix (np.ndarray): Target stain matrix (3, 2). 
                                         If None, uses default H&E.
        source_stain_matrix (np.ndarray): Source stain matrix (3, 2).
                                         If None, estimates from image.
        
    Returns:
        np.ndarray: Stain-normalized image (H, W, 3), uint8
    """
    
    # Ensure proper format
    image = remove_alpha_channel(image)
    image = ensure_uint8(image)
    
    # If no source stain matrix provided, estimate from image
    if source_stain_matrix is None:
        source_stain_matrix = estimate_stain_matrix(image)
    
    # If no target provided, use standard H&E
    if target_stain_matrix is None:
        target_stain_matrix = get_default_stain_matrix()
    
    # Convert RGB to optical density (OD)
    img_float = image.astype(np.float32) / 255.0
    img_float = np.clip(img_float, 0.001, 1.0)
    od = -np.log(img_float)
    
    # Store original shape
    original_shape = od.shape
    
    # Reshape for processing: (H*W, 3)
    od_reshaped = od.reshape(-1, 3)
    
    # Compute stain concentrations
    # C = OD × M^-1  (M = stain matrix)
    try:
        source_inv = np.linalg.pinv(source_stain_matrix)
        concentrations = od_reshaped @ source_inv
    except:
        print("⚠️  Stain matrix singular, skipping normalization")
        return image
    
    # Normalize stain concentrations
    # Remove intensity differences for each stain
    concentrations_norm = concentrations.copy()
    
    for i in range(2):  # Two stains (Hematoxylin and Eosin)
        c_min = np.percentile(concentrations[:, i], 1)
        c_max = np.percentile(concentrations[:, i], 99)
        
        if c_max > c_min:
            # Normalize to [0, 1]
            concentrations_norm[:, i] = (concentrations[:, i] - c_min) / (c_max - c_min)
        else:
            # No variation in this stain
            concentrations_norm[:, i] = 0
    
    # Clip to [0, 1]
    concentrations_norm = np.clip(concentrations_norm, 0, 1)
    
    # Reconstruct optical density with target stain colors
    od_normalized = concentrations_norm @ target_stain_matrix.T
    
    # Convert back to RGB
    # RGB = exp(-OD)
    img_normalized = np.exp(-od_normalized)
    img_normalized = np.clip(img_normalized, 0, 1)
    
    # Reshape back to image
    img_normalized = img_normalized.reshape(original_shape)
    
    # Convert to uint8
    img_normalized = (img_normalized * 255).astype(np.uint8)
    
    return img_normalized


def batch_normalize_stains(images, target_stain_matrix=None):
    """
    Normalize multiple images to same stain matrix.
    
    Useful for ensuring consistency across an image batch.
    
    Args:
        images (list): List of RGB images
        target_stain_matrix (np.ndarray): Target stain matrix.
                                         If None, computed from first image.
        
    Returns:
        list: List of stain-normalized images
    """
    
    # Estimate target if not provided
    if target_stain_matrix is None:
        if len(images) > 0:
            target_stain_matrix = estimate_stain_matrix(images[0])
        else:
            target_stain_matrix = get_default_stain_matrix()
    
    normalized = []
    for img in images:
        norm_img = normalize_stain(img, target_stain_matrix=target_stain_matrix)
        normalized.append(norm_img)
    
    return normalized


# Test function to verify stain normalization works
def test_stain_normalization():
    """
    Quick test to verify stain normalization.
    """
    # Create a synthetic image with staining gradient
    img = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
    
    # Add staining gradient (apply to all channels)
    x = np.linspace(0, 50, 256)
    gradient = np.outer(x, np.ones(256))
    gradient_3d = np.stack([gradient, gradient, gradient], axis=2)
    img = np.clip(img.astype(float) + gradient_3d, 0, 255).astype(np.uint8)
    
    # Test normalization
    try:
        normalized = normalize_stain(img)
        assert normalized.shape == img.shape, "Shape mismatch"
        assert normalized.dtype == np.uint8, "dtype mismatch"
        print("✅ Stain normalization test passed")
        return True
    except Exception as e:
        print(f"❌ Stain normalization test failed: {e}")
        return False


if __name__ == "__main__":
    test_stain_normalization()
