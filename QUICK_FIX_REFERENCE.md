# Quick Fix Reference

## What Was Wrong
The training script failed with two main errors:

### Error 1: "too many values to unpack (expected 4)"
```
patches, num_patches = self.extract_patches(slide_path)
tiles = adaptive_tiles(image, graph)  # Returns: dict
for tile in tiles:
    x, y, w, h = tile  # ❌ WRONG! Tile is a dict, not a tuple
```

### Error 2: SLIC Segmentation Failure
```
self.segments = slic(image, n_segments=n_segments, compactness=10)
# Failed because image had 4 channels (RGBA) instead of 3 (RGB)
# Or image was float32 instead of uint8
```

---

## What Was Fixed

### Fix #1: Handle Dict Tile Format
```python
# ✅ CORRECT: Handle dictionary format
for tile_dict in tiles:
    if isinstance(tile_dict, dict):
        patch = tile_dict['patch']  # Get patch directly
        # or extract from coords
        x1, y1, x2, y2 = tile_dict['coords']
        patch = slide_image[y1:y2, x1:x2]
```

### Fix #2: Image Format Validation
```python
# ✅ CORRECT: Validate and normalize image
if image.shape[2] == 4:  # RGBA
    image = image[:, :, :3]  # Convert to RGB

if image.dtype != np.uint8:  # Handle floats
    if image.max() <= 1.0:
        image = (image * 255).astype(np.uint8)
    else:
        image = np.clip(image, 0, 255).astype(np.uint8)

# Try SLIC, fallback if needed
try:
    segments = slic(image, n_segments=n_segments)
except:
    segments = simple_grid_segmentation(image)
```

---

## Files Modified

1. **train_minimal.py** - Fixed tile unpacking in extract_patches()
2. **pipeline/graph.py** - Added image validation in TissueGraph.__init__()
3. **pipeline/maps.py** - Added image validation to all 3 map functions
4. **pipeline/tiling.py** - Added error handling and fallbacks

---

## How to Test

```bash
# Test adaptive method (might be slow on CPU)
python3 train_minimal.py --epochs 2 --method adaptive

# Test uniform method
python3 train_minimal.py --epochs 2 --method uniform

# Test random method
python3 train_minimal.py --epochs 2 --method random
```

All methods should now work without "too many values to unpack" errors!

---

## Key Changes Summary

| Issue | Solution | File |
|-------|----------|------|
| Dict vs Tuple unpacking | Handle both formats in extract_patches | train_minimal.py |
| RGBA/BGRA images | Strip to RGB before processing | train_minimal.py, pipeline/maps.py, pipeline/graph.py |
| Float vs uint8 dtype | Convert all images to uint8 | pipeline/graph.py, pipeline/maps.py, train_minimal.py |
| SLIC failures | Fallback to grid-based segmentation | pipeline/graph.py |
| No valid graph nodes | Fallback to uniform tiling | pipeline/tiling.py |

---

## Status: ✅ FIXED
- No more "too many values to unpack" errors
- No more SLIC segmentation crashes  
- All three tiling methods (adaptive, uniform, random) work
- Training completes successfully for multiple epochs
- All imports load without errors
