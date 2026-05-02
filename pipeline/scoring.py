"""
Patch Scoring Module
Scores patches for information content and diversity
"""

import numpy as np
from scipy.stats import entropy as scipy_entropy
from sklearn.cluster import KMeans


def compute_entropy(patch):
    """
    Compute Shannon entropy of patch
    
    Args:
        patch (np.ndarray): RGB patch
        
    Returns:
        float: Entropy value in [0, 1]
    """
    # Convert to grayscale
    gray = patch.mean(axis=2)
    
    # Compute histogram
    hist, _ = np.histogram(gray, bins=256, range=(0, 256))
    
    # Normalize
    hist = hist / hist.sum()
    
    # Remove zeros for log
    hist = hist[hist > 0]
    
    # Compute entropy and normalize
    ent = scipy_entropy(hist)
    
    return ent / np.log(256)  # Normalize to [0, 1]


def score_patches_by_entropy(tiles, top_k_ratio=0.7):
    """
    Score patches by entropy and keep top-k
    
    Args:
        tiles (list): List of tile dicts with 'patch' key
        top_k_ratio (float): Ratio of patches to keep
        
    Returns:
        list: Scored and filtered tiles
    """
    scores = []
    
    for tile_dict in tiles:
        patch = tile_dict['patch']
        ent = compute_entropy(patch)
        scores.append((tile_dict, ent))
    
    # Sort by entropy descending
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Keep top-k
    k = max(1, int(len(scores) * top_k_ratio))
    
    scored_tiles = [t for t, s in scores[:k]]
    
    return scored_tiles


class PatchScorer:
    """
    More sophisticated patch scoring using embeddings
    """
    
    def __init__(self, use_embeddings=False):
        """
        Initialize scorer
        
        Args:
            use_embeddings (bool): Use deep embeddings (requires model)
        """
        self.use_embeddings = use_embeddings
        self.embeddings = None
        self.cluster_centers = None
    
    def score_diversity(self, embeddings, n_clusters=50):
        """
        Score patches based on embedding diversity
        
        Args:
            embeddings (np.ndarray): Patch embeddings (N, D)
            n_clusters (int): Number of clusters
            
        Returns:
            np.ndarray: Diversity scores
        """
        # Cluster embeddings
        kmeans = KMeans(n_clusters=min(n_clusters, len(embeddings)), random_state=42)
        labels = kmeans.fit_predict(embeddings)
        
        # Distance to nearest cluster center
        distances = np.linalg.norm(embeddings - kmeans.cluster_centers_[labels], axis=1)
        
        # Normalize
        scores = distances / (distances.max() + 1e-8)
        
        return scores
    
    def score_patches(self, tiles, embeddings=None, top_k_ratio=0.7):
        """
        Score and filter patches
        
        Args:
            tiles (list): List of tile dicts
            embeddings (np.ndarray): Optional embeddings (N, D)
            top_k_ratio (float): Keep top-k ratio
            
        Returns:
            list: Scored and filtered tiles
        """
        scores = []
        
        for i, tile_dict in enumerate(tiles):
            patch = tile_dict['patch']
            
            # Entropy score
            entropy_score = compute_entropy(patch)
            
            # Diversity score (if embeddings provided)
            if embeddings is not None and i < len(embeddings):
                diversity_score = self.score_diversity(embeddings[[i]])[0]
            else:
                diversity_score = 0.0
            
            # Combined score
            combined = 0.6 * entropy_score + 0.4 * diversity_score
            
            scores.append((tile_dict, combined))
        
        # Sort and filter
        scores.sort(key=lambda x: x[1], reverse=True)
        k = max(1, int(len(scores) * top_k_ratio))
        
        return [t for t, s in scores[:k]]
