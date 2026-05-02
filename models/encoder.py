"""
Patch Encoder Module
Extracts features from patches using ResNet backbone
"""

import torch
import torch.nn as nn
import torchvision.models as models


class PatchEncoder(nn.Module):
    """
    Encoder for extracting patch features
    """
    
    def __init__(self, backbone='resnet18', pretrained=True, feature_dim=512):
        """
        Initialize encoder
        
        Args:
            backbone (str): Backbone model name
            pretrained (bool): Use pretrained weights
            feature_dim (int): Output feature dimension
        """
        super().__init__()
        
        # Load backbone
        if backbone == 'resnet18':
            base_model = models.resnet18(pretrained=pretrained)
            in_features = 512
        elif backbone == 'resnet34':
            base_model = models.resnet34(pretrained=pretrained)
            in_features = 512
        elif backbone == 'resnet50':
            base_model = models.resnet50(pretrained=pretrained)
            in_features = 2048
        else:
            raise ValueError(f"Unknown backbone: {backbone}")
        
        # Remove classification head
        self.features = nn.Sequential(*list(base_model.children())[:-1])
        
        # Optional projection layer
        if in_features != feature_dim:
            self.projection = nn.Linear(in_features, feature_dim)
        else:
            self.projection = nn.Identity()
        
        self.feature_dim = feature_dim
    
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x (torch.Tensor): Input tensor (B, 3, H, W)
            
        Returns:
            torch.Tensor: Feature tensor (B, feature_dim)
        """
        # Extract features
        feat = self.features(x)
        
        # Flatten
        feat = feat.view(feat.size(0), -1)
        
        # Project
        feat = self.projection(feat)
        
        return feat


class MultiScaleEncoder(nn.Module):
    """
    Multi-scale feature encoder for global + local context
    """
    
    def __init__(self, backbone='resnet18', feature_dim=512):
        """
        Initialize multi-scale encoder
        
        Args:
            backbone (str): Backbone name
            feature_dim (int): Feature dimension
        """
        super().__init__()
        
        # Low-res encoder (global context)
        self.low_res_encoder = PatchEncoder(backbone=backbone, feature_dim=feature_dim)
        
        # High-res encoder (local details)
        self.high_res_encoder = PatchEncoder(backbone=backbone, feature_dim=feature_dim)
        
        # Fusion layer
        self.fusion = nn.Sequential(
            nn.Linear(2 * feature_dim, feature_dim),
            nn.ReLU(),
            nn.Linear(feature_dim, feature_dim),
        )
        
        self.feature_dim = feature_dim
    
    def forward(self, low_res, high_res):
        """
        Forward pass
        
        Args:
            low_res (torch.Tensor): Low-res image (B, 3, H, W)
            high_res (torch.Tensor): High-res patches (B, 3, H, W)
            
        Returns:
            torch.Tensor: Fused features (B, feature_dim)
        """
        # Extract features
        low_feat = self.low_res_encoder(low_res)
        high_feat = self.high_res_encoder(high_res)
        
        # Concatenate
        combined = torch.cat([low_feat, high_feat], dim=1)
        
        # Fuse
        fused = self.fusion(combined)
        
        return fused
