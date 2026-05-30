#!/usr/bin/env python3
"""Save DHMC slide tiling overlays (adaptive vs uniform) for inspection."""

import argparse
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline.adaptive_tiling import adaptive_tiles_complexity_based, uniform_tiles
from pipeline.complexity_maps import compute_stain_robust_complexity_map

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = PROJECT_ROOT / "datasets" / "DHMC_wsi_03"
DEFAULT_OUT = (
    PROJECT_ROOT
    / "results"
    / "dhmc_wsi_03_experiment_20260530_144415"
    / "tiling_visualizations"
)


def load_slide(path, max_dim=2000):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max(h, w) / max_dim
        img = cv2.resize(img, (int(w / scale), int(h / scale)), interpolation=cv2.INTER_AREA)
    return img


def draw_tiles(image, tiles, color, max_draw=80):
    vis = image.copy()
    for tile in tiles[:max_draw]:
        x1, y1, x2, y2 = tile["coords"]
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
    return vis


def patch_montage(image, tiles, n=12, size=128):
    thumbs = []
    for tile in tiles[:n]:
        x1, y1, x2, y2 = tile["coords"]
        patch = image[y1:y2, x1:x2]
        if patch.size == 0:
            continue
        thumbs.append(cv2.resize(patch, (size, size)))
    if not thumbs:
        return None
    cols = min(4, len(thumbs))
    rows = int(np.ceil(len(thumbs) / cols))
    grid = np.ones((rows * size, cols * size, 3), dtype=np.uint8) * 255
    for i, t in enumerate(thumbs):
        r, c = divmod(i, cols)
        grid[r * size : (r + 1) * size, c * size : (c + 1) * size] = t
    return grid


def visualize_slide(slide_path, diagnosis, out_dir, max_dim=2000):
    name = Path(slide_path).stem
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    image = load_slide(slide_path, max_dim=max_dim)
    adaptive, _ = adaptive_tiles_complexity_based(
        image, base_patch_size=256, complexity_threshold=0.4, normalize_stains=True
    )
    uniform = uniform_tiles(image, patch_size=256, stride=128)

    complexity = compute_stain_robust_complexity_map(image, normalize_stains=True)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(f"{name} — {diagnosis}", fontsize=14)

    axes[0, 0].imshow(image)
    axes[0, 0].set_title("Slide (resized)")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(draw_tiles(image, uniform, (0, 200, 255)))
    axes[0, 1].set_title(f"Uniform tiles ({len(uniform)} total)")
    axes[0, 1].axis("off")

    axes[0, 2].imshow(draw_tiles(image, adaptive, (255, 80, 80)))
    axes[0, 2].set_title(f"Adaptive tiles ({len(adaptive)} total)")
    axes[0, 2].axis("off")

    axes[1, 0].imshow(complexity, cmap="hot")
    axes[1, 0].set_title("Complexity map")
    axes[1, 0].axis("off")

    u_grid = patch_montage(image, uniform)
    a_grid = patch_montage(image, adaptive)
    if u_grid is not None:
        axes[1, 1].imshow(u_grid)
    axes[1, 1].set_title("Uniform patch samples")
    axes[1, 1].axis("off")
    if a_grid is not None:
        axes[1, 2].imshow(a_grid)
    axes[1, 2].set_title("Adaptive patch samples")
    axes[1, 2].axis("off")

    out_path = out_dir / f"{name}_tiling_comparison.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()

    meta = {
        "slide": name,
        "diagnosis": diagnosis,
        "uniform_tile_count": len(uniform),
        "adaptive_tile_count": len(adaptive),
        "image_shape": list(image.shape),
    }
    return out_path, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--slides",
        nargs="*",
        default=["DHMC_0100.png", "DHMC_0117.png", "DHMC_0134.png"],
        help="Filenames to visualize (default: one Oncocytoma, two Clearcell)",
    )
    args = parser.parse_args()

    labels = pd.read_csv(args.dataset / "labels.csv")
    rows = {r["path"]: r for _, r in labels.iterrows()}

    print(f"Saving visualizations to {args.out_dir}\n")
    for fname in args.slides:
        if fname not in rows:
            print(f"  skip (not in labels): {fname}")
            continue
        path = args.dataset / fname
        diag = rows[fname].get("diagnosis", "?")
        out_path, meta = visualize_slide(path, diag, args.out_dir)
        print(f"  {out_path.name}")
        print(
            f"    uniform={meta['uniform_tile_count']} tiles, "
            f"adaptive={meta['adaptive_tile_count']} tiles"
        )


if __name__ == "__main__":
    main()
