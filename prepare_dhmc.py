"""
Build labels.csv for DHMC_wsi_03 from MetaData_Release_1.1.csv.

Subset DHMC_0100–0149: Oncocytoma (0) vs Clearcell (1).
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_ROOT / "datasets" / "DHMC_wsi_03"
METADATA_PATH = PROJECT_ROOT / "datasets" / "MetaData_Release_1.1.csv"

# Binary task for this release slice (two diagnoses present in wsi_03)
DIAGNOSIS_TO_LABEL = {
    "Oncocytoma": 0,
    "Clearcell": 1,
}


def build_labels(dataset_dir=None, metadata_path=None):
    dataset_dir = Path(dataset_dir or DATASET_DIR)
    metadata_path = Path(metadata_path or METADATA_PATH)

    meta = pd.read_csv(metadata_path)
    meta.columns = [c.strip() for c in meta.columns]
    meta = meta.rename(
        columns={
            "File Name": "path",
            "Diagnosis": "diagnosis",
            "Data Split": "split",
        }
    )

    rows = []
    for _, row in meta.iterrows():
        slide_path = dataset_dir / row["path"]
        if not slide_path.exists():
            continue
        diagnosis = row["diagnosis"].strip()
        if diagnosis not in DIAGNOSIS_TO_LABEL:
            print(f"  skip unknown diagnosis: {diagnosis} ({row['path']})")
            continue
        rows.append(
            {
                "path": row["path"],
                "label": DIAGNOSIS_TO_LABEL[diagnosis],
                "diagnosis": diagnosis,
                "split": row["split"].strip(),
            }
        )

    df = pd.DataFrame(rows)
    out_path = dataset_dir / "labels.csv"
    df.to_csv(out_path, index=False)

    print(f"Wrote {out_path} ({len(df)} slides)")
    print("Diagnosis counts:\n", df["diagnosis"].value_counts().to_string())
    print("\nOfficial split:\n", df["split"].value_counts().to_string())
    print("\nLabel counts:\n", df["label"].value_counts().to_string())
    return df


if __name__ == "__main__":
    build_labels()
