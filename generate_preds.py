#!/bin/env python
import os
import sys
from pathlib import Path
import json
from datasets import load_dataset

if len(sys.argv) < 2:
    print("Usage: python read_path.py <path>")
    sys.exit(1)

input_path = Path(sys.argv[1])

if not input_path.exists():
        print("The path does NOT exist.")
        sys.exit(1)

ds = load_dataset("SWE-bench/SWE-bench_Lite")["test"]
swe_dict = {item["instance_id"]: item for item in ds}

predictions=[]
for filename in os.listdir(input_path):
    full_path = os.path.join(input_path, filename)

    if not os.path.isdir(full_path):
        continue

    prediction_path = os.path.join(full_path, f"{filename}.pred")

    if not os.path.exists(prediction_path):
         continue
    
    model_patch=""
    with open(prediction_path, 'r', encoding='utf-8') as f:
        preds_data = json.load(f)
        f.close()

    if preds_data["model_patch"] != None:
        model_patch=preds_data["model_patch"]
    else:
        patch_path = os.path.join(full_path, f"{filename}.patch")

        if not os.path.exists(patch_path):
            continue
        
        with open(patch_path, 'r', encoding='utf-8') as f:
            content = f.read()
            model_patch = content.replace('"', r'\\"')
            f.close()

    base_commit = swe_dict[filename]["base_commit"]
        
    entry = {
        "instance_id": filename,
        "model_patch": model_patch,
        "base_commit": base_commit,
        "model_name_or_path": "original_model"
    }

    predictions.append(entry)

with open("predictions.json", "w", encoding="utf-8") as f:
    json.dump(predictions, f, indent=2)
    f.close()