"""
Policy Network for Adaptive Tiling
Uses reinforcement learning to learn sampling strategy
"""

import torch
import torch.nn as nn


class TilingPolicy(nn.Module):
    """
    Policy network for learning adaptive tiling parameters
    """
    
    def __init__(self, feature_dim=10, hidden_dim=64):
        """
        Initialize policy network
        
        Args:
            feature_dim (int): Input feature dimension (e.g., complexity, uncertainty)
            hidden_dim (int): Hidden layer dimension
        """
        super().__init__()
        
        self.net = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 2),  # Output: tile_size, stride
        )
    
    def forward(self, features):
        """
        Forward pass
        
        Args:
            features (torch.Tensor): Region features (B, feature_dim)
            
        Returns:
            torch.Tensor: Tiling parameters (B, 2)
        """
        return self.net(features)


class PolicyGradient:
    """
    REINFORCE policy gradient optimizer
    """
    
    def __init__(self, policy, learning_rate=1e-4):
        """
        Initialize policy gradient optimizer
        
        Args:
            policy (nn.Module): Policy network
            learning_rate (float): Learning rate
        """
        self.policy = policy
        self.optimizer = torch.optim.Adam(policy.parameters(), lr=learning_rate)
    
    def compute_loss(self, log_probs, rewards):
        """
        Compute policy loss
        
        Args:
            log_probs (torch.Tensor): Log probabilities of actions
            rewards (torch.Tensor): Rewards for actions
            
        Returns:
            torch.Tensor: Loss value
        """
        # Policy gradient loss: -log_prob * reward
        loss = -(log_probs * rewards).mean()
        return loss
    
    def update(self, log_probs, rewards):
        """
        Update policy
        
        Args:
            log_probs (torch.Tensor): Log probabilities
            rewards (torch.Tensor): Rewards
        """
        loss = self.compute_loss(log_probs, rewards)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
