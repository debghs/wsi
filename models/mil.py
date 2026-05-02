"""
Multiple Instance Learning (MIL) Module
Aggregates patch-level features for slide-level prediction
"""

import torch
import torch.nn as nn


class MILAttention(nn.Module):
    """
    Attention-based Multiple Instance Learning
    """
    
    def __init__(self, feature_dim, hidden_dim=128, num_classes=2):
        """
        Initialize MIL attention module
        
        Args:
            feature_dim (int): Input feature dimension
            hidden_dim (int): Hidden dimension for attention network
            num_classes (int): Number of classification classes
        """
        super().__init__()
        
        # Attention network
        self.attention_net = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )
        
        # Classifier
        self.classifier = nn.Linear(feature_dim, num_classes)
        
        self.feature_dim = feature_dim
        self.num_classes = num_classes
    
    def forward(self, features):
        """
        Forward pass
        
        Args:
            features (torch.Tensor): Patch features (N, feature_dim)
                where N is number of patches
            
        Returns:
            torch.Tensor: Logits (1, num_classes)
            torch.Tensor: Attention weights (N, 1)
        """
        # Compute attention weights
        attention_scores = self.attention_net(features)  # (N, 1)
        
        # Softmax over patches
        attention_weights = torch.softmax(attention_scores, dim=0)
        
        # Weighted aggregation
        aggregated = (attention_weights * features).sum(dim=0, keepdim=True)
        
        # Classification
        logits = self.classifier(aggregated)
        
        return logits, attention_weights
    
    def get_attention_map(self, features):
        """
        Get attention weights for visualization
        
        Args:
            features (torch.Tensor): Patch features (N, feature_dim)
            
        Returns:
            torch.Tensor: Attention weights (N,)
        """
        attention_scores = self.attention_net(features)
        attention_weights = torch.softmax(attention_scores, dim=0)
        return attention_weights.squeeze(-1)


class GraphTransformer(nn.Module):
    """
    Graph-based Transformer for spatial modeling
    """
    
    def __init__(self, feature_dim, num_heads=4, num_layers=2):
        """
        Initialize Graph Transformer
        
        Args:
            feature_dim (int): Feature dimension
            num_heads (int): Number of attention heads
            num_layers (int): Number of transformer layers
        """
        super().__init__()
        
        self.feature_dim = feature_dim
        
        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=feature_dim,
            nhead=num_heads,
            dim_feedforward=4 * feature_dim,
            batch_first=True,
        )
        
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
    
    def forward(self, features):
        """
        Forward pass
        
        Args:
            features (torch.Tensor): Patch features (N, feature_dim)
            
        Returns:
            torch.Tensor: Refined features (N, feature_dim)
        """
        # Add batch dimension
        if features.dim() == 2:
            features = features.unsqueeze(0)
        
        # Apply transformer
        refined = self.transformer(features)
        
        # Remove batch dimension if added
        if refined.shape[0] == 1:
            refined = refined.squeeze(0)
        
        return refined


class ASTRA(nn.Module):
    """
    Complete ASTRA model combining encoder, graph transformer, and MIL
    """
    
    def __init__(self, feature_dim=512, num_classes=2, graph_heads=4, mil_hidden=128):
        """
        Initialize ASTRA model
        
        Args:
            feature_dim (int): Feature dimension
            num_classes (int): Number of classes
            graph_heads (int): Number of transformer heads
            mil_hidden (int): MIL hidden dimension
        """
        super().__init__()
        
        # Graph transformer for spatial modeling
        self.graph_transformer = GraphTransformer(
            feature_dim=feature_dim,
            num_heads=graph_heads,
        )
        
        # MIL attention head
        self.mil_head = MILAttention(
            feature_dim=feature_dim,
            hidden_dim=mil_hidden,
            num_classes=num_classes,
        )
        
        self.feature_dim = feature_dim
        self.num_classes = num_classes
    
    def forward(self, features):
        """
        Forward pass
        
        Args:
            features (torch.Tensor): Patch features (N, feature_dim)
            
        Returns:
            dict: Dictionary with keys:
                - 'logits': Classification logits (1, num_classes)
                - 'attention': Attention weights (N, 1)
                - 'features': Refined features (N, feature_dim)
        """
        # Refine features with graph transformer
        refined_features = self.graph_transformer(features)
        
        # MIL aggregation
        logits, attention = self.mil_head(refined_features)
        
        return {
            'logits': logits,
            'attention': attention,
            'features': refined_features,
        }
    
    def get_attention_weights(self, features):
        """
        Get attention weights for visualization
        
        Args:
            features (torch.Tensor): Patch features (N, feature_dim)
            
        Returns:
            torch.Tensor: Attention weights (N,)
        """
        refined_features = self.graph_transformer(features)
        return self.mil_head.get_attention_map(refined_features)
