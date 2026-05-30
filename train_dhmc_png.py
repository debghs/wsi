#!/usr/bin/env python3
"""
Training on DHMC_wsi_03 PNG slides with stain-robust adaptive tiling.

Labels: datasets/DHMC_wsi_03/labels.csv (from prepare_dhmc.py + metadata).
Task: binary Oncocytoma (0) vs Clearcell (1) for slides DHMC_0100–0149.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from models.astra_combined import ASTRACombined
from pipeline.adaptive_tiling import (
    adaptive_tiles_complexity_based,
    random_tiles,
    uniform_tiles,
)

IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


class DHMCPNGTrainer:
    def __init__(
        self,
        dataset_dir,
        method="adaptive",
        epochs=5,
        device=None,
        split_mode="stratified",
        max_patches=20,
        max_dim=2000,
    ):
        self.dataset_dir = Path(dataset_dir)
        self.method = method
        self.epochs = epochs
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.split_mode = split_mode
        self.max_patches = max_patches
        self.max_dim = max_dim

        labels_csv = self.dataset_dir / "labels.csv"
        if not labels_csv.exists():
            raise FileNotFoundError(
                f"{labels_csv} not found. Run: python prepare_dhmc.py"
            )

        df = pd.read_csv(labels_csv)
        self.slides = []
        self.labels = []
        self.diagnoses = []
        for _, row in df.iterrows():
            slide_path = self.dataset_dir / row["path"]
            if slide_path.exists():
                self.slides.append(str(slide_path))
                self.labels.append(int(row["label"]))
                self.diagnoses.append(row.get("diagnosis", ""))

        if len(self.slides) < 2:
            raise RuntimeError("Need at least 2 slides in dataset directory")

        self._assign_splits(df)

        self.model = ASTRACombined(
            backbone="resnet18", feature_dim=256, num_classes=2
        ).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-4)
        self.criterion = nn.CrossEntropyLoss()

        self.train_losses = []
        self.train_slide_accs = []
        self.val_slide_accs = []
        self.val_aucs = []
        self.patches_per_slide = []

        print(f"\nDHMC trainer | method={method} | device={self.device}")
        print(f"Slides: {len(self.slides)} | train={len(self.train_slides)} | val={len(self.val_slides)}")
        print(f"Labels 0/1: {self.labels.count(0)} / {self.labels.count(1)} | split_mode={split_mode}\n")

    def _assign_splits(self, df):
        if self.split_mode == "official" and "split" in df.columns:
            train_idx = [i for i, s in enumerate(self.slides) if self._official_split(s) == "train"]
            val_idx = [i for i, s in enumerate(self.slides) if self._official_split(s) == "val"]
            if train_idx and val_idx:
                self.train_slides = [self.slides[i] for i in train_idx]
                self.train_labels = [self.labels[i] for i in train_idx]
                self.val_slides = [self.slides[i] for i in val_idx]
                self.val_labels = [self.labels[i] for i in val_idx]
                return

        tr_s, va_s, tr_l, va_l = train_test_split(
            self.slides,
            self.labels,
            test_size=0.2,
            random_state=42,
            stratify=self.labels,
        )
        self.train_slides, self.val_slides = tr_s, va_s
        self.train_labels, self.val_labels = tr_l, va_l

    def _official_split(self, slide_path):
        name = Path(slide_path).name
        row = pd.read_csv(self.dataset_dir / "labels.csv")
        match = row[row["path"] == name]
        if match.empty:
            return "train"
        split = str(match.iloc[0]["split"]).strip().lower()
        return "val" if split in ("test", "val") else "train"

    def _normalize_patches(self, patches_tensor):
        x = patches_tensor.to(self.device) / 255.0
        mean = IMAGENET_MEAN.to(self.device)
        std = IMAGENET_STD.to(self.device)
        return (x - mean) / std

    def extract_patches(self, image_path, count_patch=False):
        image_array = cv2.imread(str(image_path))
        if image_array is None:
            raise ValueError(f"Could not read image: {image_path}")
        image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)

        h, w = image_array.shape[:2]
        if max(h, w) > self.max_dim:
            scale = max(h, w) / self.max_dim
            image_array = cv2.resize(
                image_array,
                (int(w / scale), int(h / scale)),
                interpolation=cv2.INTER_AREA,
            )

        if self.method == "adaptive":
            tiles, _ = adaptive_tiles_complexity_based(
                image_array,
                base_patch_size=256,
                complexity_threshold=0.4,
                normalize_stains=True,
            )
        elif self.method == "random":
            tiles = random_tiles(
                image_array, num_tiles=self.max_patches, patch_size=256
            )
        else:
            tiles = uniform_tiles(image_array, patch_size=256, stride=128)

        patches = []
        for tile in tiles[: self.max_patches]:
            if isinstance(tile, dict) and "coords" in tile:
                x1, y1, x2, y2 = tile["coords"]
                patch = image_array[
                    max(0, y1) : min(image_array.shape[0], y2),
                    max(0, x1) : min(image_array.shape[1], x2),
                ]
            elif isinstance(tile, dict) and "patch" in tile:
                patch = tile["patch"]
            else:
                continue
            if patch.size > 0:
                patches.append(cv2.resize(patch, (224, 224)))

        if not patches:
            raise ValueError(f"No patches extracted from {image_path}")

        if count_patch:
            self.patches_per_slide.append(len(patches))
        return np.stack(patches, axis=0)

    def _forward_slide(self, patches_np):
        patches_tensor = torch.from_numpy(patches_np).float().permute(0, 3, 1, 2)
        patches_tensor = self._normalize_patches(patches_tensor)
        output = self.model(patches_tensor)
        return output["logits"]

    def train_epoch(self, record_patches=False):
        if record_patches:
            self.patches_per_slide = []

        self.model.train()
        total_loss = 0.0
        y_true, y_pred = [], []

        for image_path, label in tqdm(
            zip(self.train_slides, self.train_labels),
            total=len(self.train_slides),
            desc="train",
            leave=False,
        ):
            patches = self.extract_patches(image_path, count_patch=record_patches)
            label_tensor = torch.tensor([label], dtype=torch.long, device=self.device)

            self.optimizer.zero_grad()
            logits = self._forward_slide(patches)
            loss = self.criterion(logits, label_tensor)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            y_true.append(label)
            y_pred.append(int(logits.argmax(dim=1).item()))

        acc = accuracy_score(y_true, y_pred) if y_true else 0.0
        return total_loss / max(len(self.train_slides), 1), acc

    @torch.no_grad()
    def val_epoch(self):
        self.model.eval()
        y_true, y_prob = [], []

        for image_path, label in tqdm(
            zip(self.val_slides, self.val_labels),
            total=len(self.val_slides),
            desc="val",
            leave=False,
        ):
            patches = self.extract_patches(image_path)
            logits = self._forward_slide(patches)
            prob = torch.softmax(logits, dim=1)[0, 1].item()
            y_true.append(label)
            y_prob.append(prob)

        if not y_true:
            return 0.0, 0.0

        y_pred = [1 if p >= 0.5 else 0 for p in y_prob]
        acc = accuracy_score(y_true, y_pred)
        try:
            auc = roc_auc_score(y_true, y_prob)
        except ValueError:
            auc = 0.0
        return acc, auc

    def train(self, results_dir=None):
        start = time.time()
        best_val_acc = 0.0

        for epoch in range(self.epochs):
            print(f"Epoch {epoch + 1}/{self.epochs}")
            train_loss, train_acc = self.train_epoch(record_patches=(epoch == 0))
            val_acc, val_auc = self.val_epoch()

            self.train_losses.append(train_loss)
            self.train_slide_accs.append(train_acc)
            self.val_slide_accs.append(val_acc)
            self.val_aucs.append(val_auc)
            best_val_acc = max(best_val_acc, val_acc)

            print(
                f"  loss={train_loss:.4f} train_acc={train_acc:.3f} "
                f"val_acc={val_acc:.3f} val_auc={val_auc:.3f}"
            )

        elapsed = int(time.time() - start)
        avg_patches = (
            float(np.mean(self.patches_per_slide)) if self.patches_per_slide else 0
        )

        results = {
            "method": self.method,
            "dataset": "DHMC_wsi_03",
            "task": "Oncocytoma(0)_vs_Clearcell(1)",
            "epochs": self.epochs,
            "split_mode": self.split_mode,
            "n_train": len(self.train_slides),
            "n_val": len(self.val_slides),
            "final_train_loss": self.train_losses[-1],
            "final_train_slide_acc": self.train_slide_accs[-1],
            "final_val_slide_acc": self.val_slide_accs[-1],
            "best_val_slide_acc": max(self.val_slide_accs),
            "final_val_auc": self.val_aucs[-1],
            "best_val_auc": max(self.val_aucs),
            "avg_patches_per_slide": avg_patches,
            "training_time_seconds": elapsed,
            "device": str(self.device),
            "train_slide_accs_per_epoch": self.train_slide_accs,
            "val_slide_accs_per_epoch": self.val_slide_accs,
            "val_aucs_per_epoch": self.val_aucs,
        }

        if results_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = Path(f"results/{self.method}_dhmc_png_{timestamp}")
        results_dir = Path(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

        with open(results_dir / "results.json", "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nDone ({elapsed}s). Results: {results_dir / 'results.json'}")
        return results, results_dir


def main():
    parser = argparse.ArgumentParser(description="Train on DHMC_wsi_03 PNG dataset")
    parser.add_argument("--dataset", default="datasets/DHMC_wsi_03")
    parser.add_argument("--method", default="adaptive", choices=["adaptive", "uniform", "random"])
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--device", default=None)
    parser.add_argument("--split-mode", default="stratified", choices=["stratified", "official"])
    parser.add_argument("--max-patches", type=int, default=20)
    parser.add_argument("--results-dir", default=None)
    args = parser.parse_args()

    trainer = DHMCPNGTrainer(
        dataset_dir=args.dataset,
        method=args.method,
        epochs=args.epochs,
        device=args.device,
        split_mode=args.split_mode,
        max_patches=args.max_patches,
    )
    trainer.train(results_dir=args.results_dir)


if __name__ == "__main__":
    main()
