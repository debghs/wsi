#!/usr/bin/env python3
"""
Comprehensive test and demonstration of stain-robust adaptive tiling.

This script:
1. Tests all new modules
2. Demonstrates the difference between uniform and adaptive tiling
3. Shows impact of stain normalization
4. Generates comparison visualizations
"""

import sys
sys.path.insert(0, '/home/debghs/coding/final_yr_project')

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def test_all_modules():
    """Test all new modules."""
    
    print("\n" + "="*70)
    print("TESTING ALL NEW MODULES")
    print("="*70)
    
    # Test 1: Stain normalization
    print("\n[1/3] Testing Stain Normalization...")
    try:
        from pipeline.stain_norm import test_stain_normalization
        result = test_stain_normalization()
        if not result:
            raise Exception("Test failed")
        print("      ✅ Stain normalization module OK")
    except Exception as e:
        print(f"      ❌ Stain normalization module FAILED: {e}")
        return False
    
    # Test 2: Complexity maps
    print("\n[2/3] Testing Complexity Maps...")
    try:
        from pipeline.complexity_maps import test_complexity_maps
        result = test_complexity_maps()
        if not result:
            raise Exception("Test failed")
        print("      ✅ Complexity maps module OK")
    except Exception as e:
        print(f"      ❌ Complexity maps module FAILED: {e}")
        return False
    
    # Test 3: Adaptive tiling
    print("\n[3/3] Testing Adaptive Tiling...")
    try:
        from pipeline.adaptive_tiling import test_adaptive_tiling
        result = test_adaptive_tiling()
        if not result:
            raise Exception("Test failed")
        print("      ✅ Adaptive tiling module OK")
    except Exception as e:
        print(f"      ❌ Adaptive tiling module FAILED: {e}")
        return False
    
    print("\n" + "="*70)
    print("✅ ALL MODULES TESTED SUCCESSFULLY")
    print("="*70)
    return True


def demonstrate_stain_robustness():
    """Demonstrate stain robustness with synthetic images."""
    
    print("\n" + "="*70)
    print("DEMONSTRATING STAIN ROBUSTNESS")
    print("="*70)
    
    from pipeline.complexity_maps import (
        compute_stain_robust_complexity_map,
        compute_laplacian_of_gaussian,
        compute_entropy_map
    )
    from pipeline.stain_norm import normalize_stain
    
    # Create test image with staining gradient
    print("\n[1/2] Creating synthetic image with staining gradient...")
    img = np.random.randint(100, 200, (512, 512, 3), dtype=np.uint8)
    
    # Add strong staining gradient (artifact)
    x = np.linspace(0, 100, 512)
    gradient = np.outer(x, np.ones(512))
    gradient_3d = np.stack([gradient, gradient, gradient], axis=2)
    img_with_stain = np.clip(img.astype(float) + gradient_3d, 0, 255).astype(np.uint8)
    
    print(f"      Original image: {img.shape}, range [{img.min()}-{img.max()}]")
    print(f"      Stained image:  {img_with_stain.shape}, range [{img_with_stain.min()}-{img_with_stain.max()}]")
    
    # Compute complexity with and without stain normalization
    print("\n[2/2] Computing complexity maps...")
    
    complexity_before = compute_stain_robust_complexity_map(img_with_stain, normalize_stains=False)
    print(f"      Before normalization: mean={complexity_before.mean():.3f}, std={complexity_before.std():.3f}")
    
    complexity_after = compute_stain_robust_complexity_map(img_with_stain, normalize_stains=True)
    print(f"      After normalization:  mean={complexity_after.mean():.3f}, std={complexity_after.std():.3f}")
    
    print("\n✅ Stain robustness demonstration complete")
    return True


def demonstrate_adaptive_vs_uniform():
    """Compare adaptive and uniform tiling."""
    
    print("\n" + "="*70)
    print("COMPARING ADAPTIVE VS UNIFORM TILING")
    print("="*70)
    
    from pipeline.adaptive_tiling import (
        adaptive_tiles_complexity_based,
        uniform_tiles
    )
    
    # Create synthetic image with high-complexity region
    print("\n[1/1] Creating image with high-complexity region...")
    img = np.random.randint(150, 200, (512, 512, 3), dtype=np.uint8)
    
    # Add a high-complexity region (e.g., tumor-like)
    img[150:350, 150:350] = np.random.randint(50, 250, (200, 200, 3), dtype=np.uint8)
    
    # Get adaptive tiles
    tiles_adaptive, complexity_map = adaptive_tiles_complexity_based(
        img,
        base_patch_size=256,
        complexity_threshold=0.4,
        normalize_stains=False
    )
    
    # Get uniform tiles
    tiles_uniform = uniform_tiles(img, patch_size=256, stride=128)
    
    # Print statistics
    print(f"\n      Uniform tiling:")
    print(f"        Total patches: {len(tiles_uniform)}")
    print(f"        Average complexity: N/A (uniform doesn't compute)")
    
    print(f"\n      Adaptive tiling:")
    print(f"        Total patches: {len(tiles_adaptive)}")
    
    high_complexity = sum(1 for t in tiles_adaptive if t['type'] == 'adaptive_high')
    low_complexity = sum(1 for t in tiles_adaptive if t['type'] == 'adaptive_low')
    print(f"        High-complexity regions: {high_complexity}")
    print(f"        Low-complexity regions: {low_complexity}")
    
    avg_complexity = np.mean([t['complexity_score'] for t in tiles_adaptive])
    print(f"        Average complexity score: {avg_complexity:.3f}")
    
    reduction = 100 * (1 - len(tiles_adaptive) / len(tiles_uniform))
    print(f"\n      Efficiency gain: {reduction:.1f}% fewer patches")
    
    print("\n✅ Adaptive vs uniform comparison complete")
    return True


def main():
    """Run all tests and demonstrations."""
    
    print("\n" + "="*70)
    print("  STAIN-ROBUST ADAPTIVE TILING - COMPLETE TEST SUITE")
    print("="*70)
    
    # Test all modules
    if not test_all_modules():
        print("\n❌ Module tests failed")
        return False
    
    # Demonstrate stain robustness
    if not demonstrate_stain_robustness():
        print("\n❌ Stain robustness demo failed")
        return False
    
    # Demonstrate adaptive vs uniform
    if not demonstrate_adaptive_vs_uniform():
        print("\n❌ Adaptive vs uniform demo failed")
        return False
    
    # Final summary
    print("\n" + "="*70)
    print("✅ ALL TESTS AND DEMONSTRATIONS PASSED")
    print("="*70)
    print("\nYou can now run:")
    print("  python train_minimal.py --epochs 5 --method adaptive")
    print("  python train_minimal.py --epochs 5 --method uniform")
    print("  python train_minimal.py --epochs 5 --method random")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
