"""
Graph Construction Module
Builds graph representation of tissue regions
"""

import numpy as np
import networkx as nx
from skimage.segmentation import slic
from scipy import ndimage


class TissueGraph:
    """
    Constructs and manages a graph representation of tissue regions
    """
    
    def __init__(self, image, tissue_mask, complexity, n_segments=2000):
        """
        Build graph from tissue image
        
        Args:
            image (np.ndarray): RGB image (H, W, 3)
            tissue_mask (np.ndarray): Tissue probability map (H, W)
            complexity (np.ndarray): Complexity map (H, W)
            n_segments (int): Number of superpixels
        """
        # Ensure image is 3D RGB (remove alpha channel if present)
        if len(image.shape) == 3:
            if image.shape[2] == 4:
                # RGBA -> RGB
                image = image[:, :, :3]
            elif image.shape[2] != 3:
                raise ValueError(f"Expected RGB image with 3 channels, got {image.shape[2]}")
        else:
            raise ValueError(f"Expected 3D image, got shape {image.shape}")
        
        # Ensure image is in proper format for SLIC
        if image.dtype == np.uint8:
            # uint8 is expected by SLIC
            pass
        elif image.dtype in [np.float32, np.float64]:
            # Convert to uint8
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            else:
                image = np.clip(image, 0, 255).astype(np.uint8)
        
        self.image = image
        self.tissue_mask = tissue_mask
        self.complexity = complexity
        self.n_segments = n_segments
        
        # Generate superpixels
        try:
            self.segments = slic(self.image, n_segments=n_segments, compactness=10)
        except Exception as e:
            print(f"    ⚠️  Error in SLIC segmentation: {e}")
            # Fallback: create simple grid-based segments
            self.segments = self._fallback_segments()
        
        # Build graph
        self.graph = self._build_graph()
    
    def _fallback_segments(self):
        """Create simple grid-based segments as fallback."""
        h, w = self.image.shape[:2]
        seg_size = int(np.sqrt(h * w / self.n_segments))
        segments = np.zeros((h, w), dtype=np.int32)
        seg_id = 0
        
        for y in range(0, h, seg_size):
            for x in range(0, w, seg_size):
                segments[y:y+seg_size, x:x+seg_size] = seg_id
                seg_id += 1
        
        return segments
    
    def _build_graph(self):
        """
        Build networkx graph from segments
        
        Returns:
            nx.Graph: Graph with node features
        """
        G = nx.Graph()
        
        # Add nodes for each segment
        for seg_id in np.unique(self.segments):
            mask = (self.segments == seg_id)
            
            # Skip if mostly background
            if self.tissue_mask[mask].mean() < 0.1:
                continue
            
            # Extract node features
            region_pixels = self.image[mask]
            mean_color = region_pixels.mean(axis=0)
            
            node_features = {
                'id': int(seg_id),
                'mean_color': mean_color,
                'complexity': float(self.complexity[mask].mean()),
                'tissue_prob': float(self.tissue_mask[mask].mean()),
                'area': int(mask.sum()),
                'mask': mask,
            }
            
            G.add_node(seg_id, **node_features)
        
        # Add edges based on adjacency
        G = self._add_edges(G)
        
        return G
    
    def _add_edges(self, G):
        """
        Add edges between adjacent segments
        
        Args:
            G (nx.Graph): Graph
            
        Returns:
            nx.Graph: Graph with edges
        """
        h, w = self.segments.shape
        edges_added = set()
        
        # Check 4-connectivity
        for y in range(h):
            for x in range(w-1):
                seg_a = self.segments[y, x]
                seg_b = self.segments[y, x+1]
                
                if seg_a != seg_b and seg_a in G and seg_b in G:
                    edge = tuple(sorted([seg_a, seg_b]))
                    if edge not in edges_added:
                        G.add_edge(seg_a, seg_b)
                        edges_added.add(edge)
        
        for y in range(h-1):
            for x in range(w):
                seg_a = self.segments[y, x]
                seg_b = self.segments[y+1, x]
                
                if seg_a != seg_b and seg_a in G and seg_b in G:
                    edge = tuple(sorted([seg_a, seg_b]))
                    if edge not in edges_added:
                        G.add_edge(seg_a, seg_b)
                        edges_added.add(edge)
        
        return G
    
    def get_node_mask(self, node_id):
        """
        Get pixel mask for a node
        
        Args:
            node_id: Node ID
            
        Returns:
            np.ndarray: Binary mask
        """
        return (self.segments == node_id)
    
    def get_node_features(self, node_id):
        """
        Get features for a node
        
        Args:
            node_id: Node ID
            
        Returns:
            dict: Node features
        """
        return dict(self.graph.nodes[node_id])
    
    def get_adjacency(self):
        """
        Get adjacency matrix
        
        Returns:
            np.ndarray: Adjacency matrix
        """
        return nx.adjacency_matrix(self.graph).toarray()
    
    def get_node_list(self):
        """
        Get list of valid node IDs
        
        Returns:
            list: Node IDs
        """
        return list(self.graph.nodes())
    
    def get_num_nodes(self):
        """Get number of nodes"""
        return len(self.graph)
    
    def filter_by_tissue_probability(self, threshold=0.2):
        """
        Filter nodes by tissue probability
        
        Args:
            threshold (float): Minimum tissue probability
            
        Returns:
            list: Valid node IDs
        """
        valid_nodes = []
        for node_id in self.graph.nodes():
            tissue_prob = self.graph.nodes[node_id]['tissue_prob']
            if tissue_prob >= threshold:
                valid_nodes.append(node_id)
        
        return valid_nodes
