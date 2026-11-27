"""Export the built corpus from the Modal Volume to the HF artifacts bucket (D38/D40).

The Modal Volume is working storage; the durable home is HF. Uploads /corpus
(store + vectors + passages + manifest) to keypa/exa-replica-artifacts, excluding
the raw WARC (D40: raw WARC is streamed, never stored).

Run: modal run bench/modal_export.py
"""

from __future__ import annotations

import modal

app = modal.App("exa-replica-export")

image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub")

corpus_vol = modal.Volume.from_name("exa-replica-corpus-vol", create_if_missing=True)


@app.function(
    image=image,
    volumes={"/corpus": corpus_vol},
    secrets=[modal.Secret.from_name("exa-hf")],
    timeout=1800,
)
def export(repo_id: str, path_in_repo: str) -> str:
    from huggingface_hub import HfApi

    api = HfApi()
    api.upload_folder(
        folder_path="/corpus",
        repo_id=repo_id,
        repo_type="dataset",
        path_in_repo=path_in_repo,
        ignore_patterns=["*.warc.gz", "*.warc"],
    )
    return f"uploaded /corpus -> {repo_id}/{path_in_repo}"


@app.local_entrypoint()
def main():
    print(export.remote("keypa/exa-replica-artifacts", "corpus/cc-main-2026-43-t0"))