"""
Feedback Loop for Iterative Refinement
"""

import numpy as np


class FeedbackRefinement:
    """
    Refines tiling strategy based on model attention
    """
    
    def __init__(self, graph):
        """
        Initialize feedback system
        
        Args:
            graph (TissueGraph): Tissue graph
        """
        self.graph = graph
        self.attention_history = {}
    
    def update_node_importance(self, attention_scores, tiles):
        """
        Update node importance based on model attention
        
        Args:
            attention_scores (np.ndarray): Attention scores for each patch
            tiles (list): List of tiles with node_id
        """
        for tile_dict, score in zip(tiles, attention_scores):
            node_id = tile_dict['node_id']
            
            if node_id not in self.attention_history:
                self.attention_history[node_id] = []
            
            self.attention_history[node_id].append(float(score))
    
    def get_node_importance(self):
        """
        Get average importance for each node
        
        Returns:
            dict: Node ID -> importance score
        """
        importance = {}
        
        for node_id, scores in self.attention_history.items():
            importance[node_id] = np.mean(scores)
        
        return importance
    
    def refine_sampling_weights(self, importance_threshold=0.5):
        """
        Suggest refinement weights for next iteration
        
        Args:
            importance_threshold (float): Threshold for high importance
            
        Returns:
            dict: Node ID -> sampling weight
        """
        importance = self.get_node_importance()
        
        weights = {}
        for node_id in self.graph.get_node_list():
            if node_id in importance:
                imp = importance[node_id]
            else:
                imp = 0.0
            
            # High importance regions get higher sampling weight
            if imp > importance_threshold:
                weight = 2.0  # Oversample
            else:
                weight = 1.0  # Normal
            
            weights[node_id] = weight
        
        return weights
