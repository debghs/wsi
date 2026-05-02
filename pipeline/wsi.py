"""
WSI Reader Module
"""

import numpy as np
from openslide import OpenSlide
import os


class WSIReader:
    """
    Reader for Whole Slide Images using OpenSlide
    """
    
    def __init__(self, path):
        """
        Initialize WSI reader
        
        Args:
            path (str): Path to WSI file (.svs, .tif, etc)
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"WSI file not found: {path}")
        
        self.path = path
        self.slide = OpenSlide(path)
        self.levels = self.slide.level_count
        self.dimensions = self.slide.level_dimensions
        
    def get_level(self, level):
        """
        Read entire level as image
        
        Args:
            level (int): Resolution level (0=highest res, higher=lower res)
            
        Returns:
            np.ndarray: RGB image of shape (H, W, 3)
        """
        if level >= self.levels:
            raise ValueError(f"Invalid level {level}. Available levels: 0-{self.levels-1}")
        
        dims = self.slide.level_dimensions[level]
        img = self.slide.read_region((0, 0), level, dims)
        # Convert RGBA to RGB
        return np.array(img)[:, :, :3]
    
    def get_patch(self, x, y, size, level=0):
        """
        Read a patch from the slide
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            size (int): Patch size
            level (int): Resolution level
            
        Returns:
            np.ndarray: RGB patch of shape (size, size, 3)
        """
        # Convert from level coordinates to base level coordinates
        scale = self.slide.level_downsamples[level]
        x_base = int(x * scale)
        y_base = int(y * scale)
        
        img = self.slide.read_region((x_base, y_base), level, (size, size))
        return np.array(img)[:, :, :3]
    
    def get_thumbnail(self, size=256):
        """
        Get thumbnail of slide
        
        Args:
            size (int): Thumbnail size
            
        Returns:
            np.ndarray: RGB thumbnail
        """
        thumb = self.slide.get_thumbnail((size, size))
        return np.array(thumb)[:, :, :3]
    
    def get_magnification(self):
        """
        Get magnification from slide metadata
        
        Returns:
            float: Magnification (typically 40.0 for 40x, etc)
        """
        props = self.slide.properties
        
        # Try common keys
        for key in ['openslide.objective-power', 'objective-power']:
            if key in props:
                return float(props[key])
        
        return 40.0  # Default assumption
    
    def close(self):
        """Close slide"""
        self.slide.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
