#!/usr/bin/env python3
"""
Run DHMC_wsi_03 experiment: adaptive vs uniform tiling (ASTRA pipeline).
"""

import json
from datetime import datetime
from pathlib import Path

from prepare_dhmc import build_labels
from train_dhmc_png import DHMCPNGTrainer

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_ROOT / "datasets" / "DHMC_wsi_03"


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--device", default=None)
    parser.add_argument("--methods", nargs="+", default=["adaptive", "uniform"])
    parser.add_argument("--split-mode", default="stratified", choices=["stratified", "official"])
    args = parser.parse_args()

    print("Building labels from MetaData_Release_1.1.csv ...")
    build_labels()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir = PROJECT_ROOT / "results" / f"dhmc_wsi_03_experiment_{timestamp}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for method in args.methods:
        print(f"\n{'=' * 60}\nRunning method: {method}\n{'=' * 60}")
        method_dir = exp_dir / method
        trainer = DHMCPNGTrainer(
            dataset_dir=DATASET_DIR,
            method=method,
            epochs=args.epochs,
            device=args.device,
            split_mode=args.split_mode,
        )
        results, _ = trainer.train(results_dir=method_dir)
        all_results[method] = results

    comparison = {
        "dataset": "DHMC_wsi_03",
        "metadata": "datasets/MetaData_Release_1.1.csv",
        "task": "Oncocytoma (0) vs Clearcell (1)",
        "epochs": args.epochs,
        "split_mode": args.split_mode,
        "methods": all_results,
    }
    if "adaptive" in all_results and "uniform" in all_results:
        u = all_results["uniform"]["avg_patches_per_slide"]
        a = all_results["adaptive"]["avg_patches_per_slide"]
        if u > 0:
            comparison["patch_reduction_vs_uniform_pct"] = round(100 * (1 - a / u), 1)

    summary_path = exp_dir / "comparison.json"
    with open(summary_path, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\nExperiment complete. Summary: {summary_path}")
    for method, res in all_results.items():
        print(
            f"  {method:8s} val_acc={res['best_val_slide_acc']:.3f} "
            f"val_auc={res['best_val_auc']:.3f} "
            f"avg_patches={res['avg_patches_per_slide']:.1f}"
        )


if __name__ == "__main__":
    main()
