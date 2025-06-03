#!/bin/env python

# Dependencies:
# patch-ng

import re
from datasets import load_dataset
import requests
import base64

GITHUB_TOKEN = '<GITHUB_TOKEN>'  # Replace with your actual token

# Login using e.g. `huggingface-cli login` to access this dataset
ds = load_dataset("SWE-bench/SWE-bench_Lite", split="test")

ds = ds.select(range(60, len(ds)))

def get_file_content(repo, file_path, commit_sha):
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'  # request JSON, not raw
    }

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={commit_sha}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    content_json = response.json()
    content = base64.b64decode(content_json["content"]).decode("utf-8")
    return content

def get_edited_files(patch):
    """
    Extract a list of edited files from a unified diff patch.
    """
    return re.findall(r'^diff --git a/(\S+)', patch, re.MULTILINE)


def patch_code_with_tempfile(code: str, patch_text: str) -> str:
    # Remove leading lines until you find one starting with ---
    lines = patch_text.splitlines(keepends=True)
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("--- "):
            start_idx = i
            break
    filtered_patch = ''.join(lines[start_idx:])

    import tempfile, os
    import patch_ng

    with tempfile.TemporaryDirectory() as tmpdir:
        # Guess file path from the patch
        first_line = filtered_patch.splitlines()[0]
        if first_line.startswith('--- '):
            patch_path = first_line.split()[1]
            patch_path = patch_path.lstrip('ab/')  # Remove 'a/' or 'b/' if present
        else:
            raise ValueError("Patch does not have a valid header")

        full_path = os.path.join(tmpdir, patch_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)
            f.close()

        patch_file_path = os.path.join(tmpdir, "patch.diff")
        with open(patch_file_path, "w", encoding="utf-8") as f:
            f.write(filtered_patch)
            f.close()

        pset = patch_ng.fromfile(patch_file_path)
        success = pset.apply(strip=0, root=tmpdir)
        if not success:
            raise RuntimeError("Patch failed to apply")

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            f.close()
            return content

final_ds = []
for instance in ds:
    edited_files = get_edited_files(instance["patch"])

    if len(edited_files) <= 1:
        try:
            edited_file = edited_files[0]
            print(instance["instance_id"])

            github_file_content = get_file_content(instance["repo"], edited_file, instance["base_commit"])
            patched_file_content = patch_code_with_tempfile(github_file_content, instance["patch"])

            # Aqui filtrar por por classful python

            final_ds.append({"problem_sattement": instance["problem_statement"],"original_code": github_file_content, "patched_code": patched_file_content})
        except Exception:
            continue