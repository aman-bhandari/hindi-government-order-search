#!/usr/bin/env python3
"""Embed chunks with a multilingual model so a Hindi question can match an English chunk and vice versa.

bge-m3 is chosen because it handles Devanagari and Latin in one vector space; an English-only model would
break cross-lingual search, which matters here because GO subjects are often English while bodies are Hindi.
Runs on the laptop GPU in fp16 with a small batch size to stay inside 6 GB of VRAM.
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect, DATA  # noqa: E402

MODEL_NAME = "BAAI/bge-m3"
VEC_FILE = DATA / "chunk_vectors.npy"
VEC_IDS = DATA / "chunk_vector_ids.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--cpu", action="store_true")
    a = ap.parse_args()

    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer

    con = connect()
    rows = con.execute("SELECT chunk_id, text FROM chunks ORDER BY chunk_id").fetchall()
    if not rows:
        sys.exit("no chunks in db — run pipeline/chunk.py first")
    ids = [r["chunk_id"] for r in rows]
    texts = [r["text"] for r in rows]

    device = "cpu" if a.cpu or not torch.cuda.is_available() else "cuda"
    print(f"model={a.model} device={device} chunks={len(texts)}", flush=True)
    model = SentenceTransformer(a.model, device=device)
    if device == "cuda":
        model.half()
    t0 = time.time()
    vecs = model.encode(texts, batch_size=a.batch, normalize_embeddings=True,
                        show_progress_bar=True, convert_to_numpy=True)
    vecs = vecs.astype("float32")
    np.save(VEC_FILE, vecs)
    VEC_IDS.write_text(json.dumps(ids))
    print(f"embedded {len(ids)} chunks in {round(time.time()-t0)}s -> {VEC_FILE} shape={vecs.shape}")


if __name__ == "__main__":
    main()
