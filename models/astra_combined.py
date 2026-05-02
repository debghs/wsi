"""
Combined ASTRA Model
Takes patches directly and outputs predictions
"""

import torch
import torch.nn as nn
from models.encoder import PatchEncoder
from models.mil import ASTRA as MILModel


class ASTRACombined(nn.Module):
    """
    Combined ASTRA model that takes patches and outputs predictions
    """
    
    def __init__(self, backbone='resnet18', feature_dim=512, num_classes=2):
        super().__init__()
        self.encoder = PatchEncoder(backbone=backbone, pretrained=True, feature_dim=feature_dim)
        self.mil_model = MILModel(feature_dim=feature_dim, num_classes=num_classes)
    
    def forward(self, patches):
        """
        Forward pass
        
        Args:
            patches: (N, 3, 224, 224) - N patches
        
        Returns:
            dict with keys:
                - logits: (1, num_classes)
                - attention: (N, 1)
                - features: (N, feature_dim)
        """
        # Extract features
        features = self.encoder(patches)  # (N, feature_dim)
        
        # Apply MIL model
        output = self.mil_model(features)
        
        return output
