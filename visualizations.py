"""
Visualization Scripts for Paper Figures
"""

import numpy as np
import cv2
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import os

from config import CONFIG


def draw_patch_boxes(image, tiles, title="Patch Sampling"):
    """
    Draw patch boxes on image
    
    Args:
        image (np.ndarray): WSI image
        tiles (list): List of tile dicts with 'coords' key
        title (str): Figure title
    """
    fig, ax = plt.subplots(1, 1, figsize=(15, 12))
    
    # Downsample image for visualization
    h, w = image.shape[:2]
    scale = max(1, max(h, w) // 1000)  # Make it manageable
    display_image = image[::scale, ::scale]
    
    ax.imshow(display_image)
    
    # Draw patch boxes
    for tile_dict in tiles:
        x1, y1, x2, y2 = tile_dict['coords']
        
        # Scale coordinates
        x1, y1, x2, y2 = x1 // scale, y1 // scale, x2 // scale, y2 // scale
        
        # Draw rectangle
        rect = patches.Rectangle((x1, y1), x2-x1, y2-y1,
                                 linewidth=1, edgecolor='r', facecolor='none', alpha=0.3)
        ax.add_patch(rect)
    
    ax.set_title(f"{title} (n_patches={len(tiles)})")
    ax.axis('off')
    
    return fig


def plot_patch_comparison(image, uniform_tiles, adaptive_tiles):
    """
    Compare uniform vs adaptive tiling
    
    Args:
        image (np.ndarray): WSI image
        uniform_tiles (list): Tiles from uniform tiling
        adaptive_tiles (list): Tiles from adaptive tiling
    """
    fig, axes = plt.subplots(1, 2, figsize=(30, 12))
    
    # Downsample for visualization
    h, w = image.shape[:2]
    scale = max(1, max(h, w) // 1000)
    display_image = image[::scale, ::scale]
    
    # Uniform
    axes[0].imshow(display_image)
    for tile_dict in uniform_tiles:
        x1, y1, x2, y2 = tile_dict['coords']
        x1, y1, x2, y2 = x1 // scale, y1 // scale, x2 // scale, y2 // scale
        rect = patches.Rectangle((x1, y1), x2-x1, y2-y1,
                                 linewidth=1, edgecolor='r', facecolor='none', alpha=0.3)
        axes[0].add_patch(rect)
    
    axes[0].set_title(f"Uniform Tiling (n_patches={len(uniform_tiles)})")
    axes[0].axis('off')
    
    # Adaptive
    axes[1].imshow(display_image)
    for tile_dict in adaptive_tiles:
        x1, y1, x2, y2 = tile_dict['coords']
        x1, y1, x2, y2 = x1 // scale, y1 // scale, x2 // scale, y2 // scale
        rect = patches.Rectangle((x1, y1), x2-x1, y2-y1,
                                 linewidth=1, edgecolor='g', facecolor='none', alpha=0.3)
        axes[1].add_patch(rect)
    
    axes[1].set_title(f"Adaptive Tiling (n_patches={len(adaptive_tiles)})")
    axes[1].axis('off')
    
    plt.tight_layout()
    
    return fig


def plot_attention_heatmap(image, tiles, attention_scores):
    """
    Plot attention heatmap
    
    Args:
        image (np.ndarray): WSI image
        tiles (list): List of tile dicts
        attention_scores (np.ndarray): Attention scores for each tile
    """
    # Create heatmap
    h, w = image.shape[:2]
    heatmap = np.zeros((h, w), dtype=np.float32)
    
    for tile_dict, score in zip(tiles, attention_scores):
        x1, y1, x2, y2 = tile_dict['coords']
        heatmap[y1:y2, x1:x2] += float(score)
    
    # Smooth heatmap
    heatmap = cv2.GaussianBlur(heatmap, (51, 51), 0)
    heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min() + 1e-8)
    
    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    
    # Original image
    axes[0].imshow(image)
    axes[0].set_title("Original WSI")
    axes[0].axis('off')
    
    # Heatmap overlay
    axes[1].imshow(image)
    im = axes[1].imshow(heatmap, cmap='jet', alpha=0.4)
    axes[1].set_title("Attention Heatmap")
    axes[1].axis('off')
    
    plt.colorbar(im, ax=axes[1])
    plt.tight_layout()
    
    return fig


def plot_results_comparison(results_dict):
    """
    Plot comparison of results across methods
    
    Args:
        results_dict (dict): Results from different methods
            Example: {'uniform': {'auc': 0.85, ...}, 'adaptive': {'auc': 0.87, ...}}
    """
    methods = list(results_dict.keys())
    
    # Prepare data
    metrics = ['auc', 'accuracy']
    x_pos = np.arange(len(methods))
    width = 0.35
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # AUC comparison
    auc_values = [results_dict[m].get('auc', 0) for m in methods]
    axes[0].bar(x_pos, auc_values, width, color='steelblue')
    axes[0].set_ylabel('AUC')
    axes[0].set_title('AUC Comparison')
    axes[0].set_xticks(x_pos)
    axes[0].set_xticklabels(methods)
    axes[0].set_ylim([0.7, 1.0])
    
    # Accuracy comparison
    acc_values = [results_dict[m].get('accuracy', 0) for m in methods]
    axes[1].bar(x_pos, acc_values, width, color='darkorange')
    axes[1].set_ylabel('Accuracy')
    axes[1].set_title('Accuracy Comparison')
    axes[1].set_xticks(x_pos)
    axes[1].set_xticklabels(methods)
    axes[1].set_ylim([0.7, 1.0])
    
    # Patch count comparison
    patch_values = [results_dict[m].get('n_patches', 0) for m in methods]
    axes[2].bar(x_pos, patch_values, width, color='forestgreen')
    axes[2].set_ylabel('Number of Patches')
    axes[2].set_title('Computational Efficiency')
    axes[2].set_xticks(x_pos)
    axes[2].set_xticklabels(methods)
    
    plt.tight_layout()
    
    return fig


def save_figure(fig, name):
    """Save figure"""
    path = os.path.join(CONFIG['figure_save_dir'], f'{name}.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    print(f"Figure saved to: {path}")
    return path


def generate_all_visualizations():
    """
    Generate all visualizations for paper
    This is a template - you need to provide actual data
    """
    print("Visualization generation requires actual WSI data and model predictions.")
    print("Please run complete training pipeline first.")
    print(f"Figures will be saved to: {CONFIG['figure_save_dir']}")
