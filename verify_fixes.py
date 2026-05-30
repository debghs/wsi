#!/usr/bin/env python3
"""
Quick verification script to ensure all fixes are working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    print("\n[TEST 1] Verifying imports...")
    try:
        from train_minimal import MinimalTrainer
        from pipeline.graph import TissueGraph
        from pipeline.tiling import adaptive_tiles, uniform_tiles, random_tiles
        from pipeline.maps import compute_tissue_mask, compute_complexity_map, compute_uncertainty_map
        from models.astra_combined import ASTRACombined
        print("    ✅ All critical imports successful")
        return True
    except Exception as e:
        print(f"    ❌ Import failed: {e}")
        return False

def test_image_formats():
    """Test various image format handling"""
    print("\n[TEST 2] Testing image format handling...")
    try:
        import numpy as np
        from pipeline.maps import compute_tissue_mask
        
        # Test uint8 RGB
        img_rgb = np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)
        mask = compute_tissue_mask(img_rgb)
        assert mask.shape == (128, 128)
        print("    ✅ uint8 RGB image: OK")
        
        # Test uint8 RGBA
        img_rgba = np.random.randint(0, 256, (128, 128, 4), dtype=np.uint8)
        mask = compute_tissue_mask(img_rgba)
        assert mask.shape == (128, 128)
        print("    ✅ uint8 RGBA image: OK")
        
        # Test float32 image
        img_float = np.random.rand(128, 128, 3).astype(np.float32)
        mask = compute_tissue_mask(img_float)
        assert mask.shape == (128, 128)
        print("    ✅ float32 RGB image: OK")
        
        return True
    except Exception as e:
        print(f"    ❌ Image format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_graph_construction():
    """Test TissueGraph with various inputs"""
    print("\n[TEST 3] Testing graph construction...")
    try:
        import numpy as np
        from pipeline.graph import TissueGraph
        from pipeline.maps import compute_tissue_mask, compute_complexity_map
        
        # Test with uint8 RGB
        img = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        tissue_mask = compute_tissue_mask(img)
        complexity = compute_complexity_map(img)
        graph = TissueGraph(img, tissue_mask, complexity, n_segments=20)
        assert graph.get_num_nodes() > 0
        print(f"    ✅ Graph construction (uint8 RGB): {graph.get_num_nodes()} nodes")
        
        # Test with RGBA (should auto-convert)
        img_rgba = np.random.randint(0, 256, (256, 256, 4), dtype=np.uint8)
        graph_rgba = TissueGraph(img_rgba, tissue_mask, complexity, n_segments=20)
        assert graph_rgba.get_num_nodes() > 0
        print(f"    ✅ Graph construction (RGBA auto-convert): {graph_rgba.get_num_nodes()} nodes")
        
        return True
    except Exception as e:
        print(f"    ❌ Graph construction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tiling_methods():
    """Test all tiling methods"""
    print("\n[TEST 4] Testing tiling methods...")
    try:
        import numpy as np
        from pipeline.tiling import adaptive_tiles, uniform_tiles, random_tiles
        from pipeline.graph import TissueGraph
        from pipeline.maps import compute_tissue_mask, compute_complexity_map
        
        # Setup
        img = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        tissue_mask = compute_tissue_mask(img)
        complexity = compute_complexity_map(img)
        graph = TissueGraph(img, tissue_mask, complexity, n_segments=30)
        
        # Test uniform
        uniform = uniform_tiles(img, tile_size=128)
        assert len(uniform) > 0 and isinstance(uniform[0], dict)
        print(f"    ✅ uniform_tiles: {len(uniform)} tiles")
        
        # Test random
        random = random_tiles(img, n_tiles=10, tile_size=128)
        assert len(random) > 0 and isinstance(random[0], dict)
        print(f"    ✅ random_tiles: {len(random)} tiles")
        
        # Test adaptive
        adaptive = adaptive_tiles(img, graph)
        assert len(adaptive) > 0 and isinstance(adaptive[0], dict)
        print(f"    ✅ adaptive_tiles: {len(adaptive)} tiles")
        
        # Verify tile format
        tile = uniform[0]
        required_keys = ['patch', 'coords']  # At least one of these
        assert 'patch' in tile or 'coords' in tile
        print(f"    ✅ Tile format: {list(tile.keys())}")
        
        return True
    except Exception as e:
        print(f"    ❌ Tiling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model():
    """Test model initialization and forward pass"""
    print("\n[TEST 5] Testing model...")
    try:
        import torch
        from models.astra_combined import ASTRACombined
        
        # Initialize model
        model = ASTRACombined(backbone='resnet18', feature_dim=256, num_classes=2)
        print(f"    ✅ Model initialized: ASTRACombined")
        
        # Forward pass
        patches = torch.randn(4, 3, 224, 224)
        output = model(patches)
        
        assert 'logits' in output
        assert 'attention' in output
        assert 'features' in output
        print(f"    ✅ Forward pass: {list(output.keys())}")
        
        return True
    except Exception as e:
        print(f"    ❌ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 COMPREHENSIVE VERIFICATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_image_formats,
        test_graph_construction,
        test_tiling_methods,
        test_model,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"    ❌ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("=" * 60)
        print("\n🎉 The codebase is ready for production!")
        print("\nYou can now run:")
        print("  python3 train_minimal.py --epochs 5 --method adaptive")
        print("  python3 train_minimal.py --epochs 5 --method uniform")
        print("  python3 train_minimal.py --epochs 5 --method random")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
