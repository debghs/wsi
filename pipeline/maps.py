"""
Multi-Scale Maps Generation
Generates tissue probability, complexity, and uncertainty maps
"""

import numpy as np
import cv2
from scipy import ndimage


def compute_tissue_mask(image, s_threshold=20):
    """
    Compute tissue probability map using HSV thresholding
    
    Args:
        image (np.ndarray): RGB image of shape (H, W, 3)
        s_threshold (int): Saturation threshold
        
    Returns:
        np.ndarray: Tissue mask of shape (H, W) in [0, 1]
    """
    # Ensure image is 3D RGB
    if len(image.shape) != 3 or image.shape[2] not in [3, 4]:
        raise ValueError(f"Expected RGB image, got shape {image.shape}")
    
    # Remove alpha channel if present
    if image.shape[2] == 4:
        image = image[:, :, :3]
    
    # Ensure uint8
    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255).astype(np.uint8)
        else:
            image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Convert to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    
    # Tissue typically has saturation > threshold
    s = hsv[:, :, 1].astype(np.float32)
    tissue_mask = (s > s_threshold).astype(np.float32)
    
    return tissue_mask


def compute_complexity_map(image, window_size=7):
    """
    Compute texture complexity map using gradient variance
    
    Args:
        image (np.ndarray): RGB image
        window_size (int): Local window size
        
    Returns:
        np.ndarray: Complexity map in [0, 1]
    """
    # Ensure image is 3D RGB
    if len(image.shape) != 3 or image.shape[2] not in [3, 4]:
        raise ValueError(f"Expected RGB image, got shape {image.shape}")
    
    # Remove alpha channel if present
    if image.shape[2] == 4:
        image = image[:, :, :3]
    
    # Ensure uint8
    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255).astype(np.uint8)
        else:
            image = np.clip(image, 0, 255).astype(np.uint8)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Compute Laplacian (edge detection)
    grad = cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F)
    grad = np.abs(grad)
    
    # Compute local variance
    complexity = cv2.GaussianBlur(grad, (window_size, window_size), 0)
    
    # Normalize
    complexity = (complexity - complexity.min()) / (complexity.max() - complexity.min() + 1e-8)
    
    return complexity.astype(np.float32)


def compute_uncertainty_map(image, edge_threshold_low=50, edge_threshold_high=150):
    """
    Compute uncertainty map using edge density
    
    Args:
        image (np.ndarray): RGB image
        edge_threshold_low (int): Canny lower threshold
        edge_threshold_high (int): Canny upper threshold
        
    Returns:
        np.ndarray: Uncertainty map in [0, 1]
    """
    # Ensure image is 3D RGB
    if len(image.shape) != 3 or image.shape[2] not in [3, 4]:
        raise ValueError(f"Expected RGB image, got shape {image.shape}")
    
    # Remove alpha channel if present
    if image.shape[2] == 4:
        image = image[:, :, :3]
    
    # Ensure uint8
    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255).astype(np.uint8)
        else:
            image = np.clip(image, 0, 255).astype(np.uint8)
    
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Canny edge detection
    edges = cv2.Canny(gray, edge_threshold_low, edge_threshold_high)
    
    # Smooth edge density
    uncertainty = cv2.GaussianBlur(edges.astype(np.float32), (7, 7), 0)
    
    # Normalize
    uncertainty = uncertainty / 255.0
    
    return uncertainty.astype(np.float32)


def compute_all_maps(image):
    """
    Compute all maps at once
    
    Args:
        image (np.ndarray): RGB image
        
    Returns:
        tuple: (tissue_mask, complexity, uncertainty) each of shape (H, W)
    """
    tissue_mask = compute_tissue_mask(image)
    complexity = compute_complexity_map(image)
    uncertainty = compute_uncertainty_map(image)
    
    return tissue_mask, complexity, uncertainty


def apply_morphology(mask, operation='open', kernel_size=5):
    """
    Apply morphological operations to refine mask
    
    Args:
        mask (np.ndarray): Binary mask
        operation (str): 'open', 'close', 'dilate', 'erode'
        kernel_size (int): Kernel size
        
    Returns:
        np.ndarray: Refined mask
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    if operation == 'open':
        return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    elif operation == 'close':
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    elif operation == 'dilate':
        return cv2.dilate(mask, kernel, iterations=1)
    elif operation == 'erode':
        return cv2.erode(mask, kernel, iterations=1)
    else:
        return mask
