#!/usr/bin/env python3
"""Answer a question from retrieved Government Order chunks, quote-first and grounded.

Contract: the model may only quote text that appears in the retrieved chunks. Every quote is verified
against its chunk after generation; unverifiable quotes are dropped, and if nothing survives the answer
becomes an explicit "not found". That check is what makes the citations trustworthy when the underlying
text came from OCR of a scanned page.

Providers: local Ollama by default (no cost, works offline in a demo); Anthropic when an API key is set.
Both return the same JSON shape so the UI never changes.
"""
import argparse, json, os, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect  # noqa: E402
import search as S  # noqa: E402

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
MIN_SCORE = float(os.environ.get("MIN_SCORE", "0.015"))
# A 7B model on a 6 GB laptop GPU needs well over a minute for a ~3k-token prompt, and much longer
# if the machine is busy. Generous by default; the interface shows progress rather than blocking silently.
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "600"))

SYSTEM = """You answer questions about Uttarakhand Government Orders for a government officer.

Rules, in order of importance:
1. Use ONLY the numbered excerpts provided. Never use outside knowledge.
2. Quote the exact words from the excerpts that support your answer. Copy them character for character.
3. If the excerpts do not contain the answer, say so. Do not guess.
4. Never state a date, Government Order number or amount unless it appears verbatim in an excerpt.
   The excerpts come from OCR of scanned pages, so digits inside them may be wrong; prefer wording over numbers.
5. Answer in the language of the question.

Return ONLY valid JSON:
{"answer": "<2-4 sentences>", "quotes": [{"n": <excerpt number>, "text": "<exact quoted words>"}],
 "found": true|false}"""


def build_prompt(question, chunks):
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] Government Order {c['go_no']}, dated {c['go_date']}, page {c['page']}, "
                     f"category {c['category']}\n{c['text']}")
    excerpts = "\n\n".join(parts)
    return f"{excerpts}\n\nQuestion: {question}\n\nJSON:"


def call_ollama(system, prompt, model=None, timeout=None):
    body = json.dumps({
        "model": model or OLLAMA_MODEL, "system": system, "prompt": prompt,
        "stream": False, "format": "json", "options": {"temperature": 0, "num_ctx": 8192},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout or LLM_TIMEOUT) as r:
        return json.loads(r.read())["response"]


def call_anthropic(system, prompt, model=None, timeout=None):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    body = json.dumps({
        "model": model or ANTHROPIC_MODEL, "max_tokens": 1024, "temperature": 0,
        "system": system, "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=timeout or LLM_TIMEOUT) as r:
        return json.loads(r.read())["content"][0]["text"]


def normalise_for_match(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def verify_quotes(parsed, chunks):
    """Keep only quotes that really occur in the cited chunk; tolerate whitespace differences."""
    kept, dropped = [], []
    for q in parsed.get("quotes", []) or []:
        try:
            n = int(q.get("n"))
        except (TypeError, ValueError):
            dropped.append({**q, "reason": "no excerpt number"}); continue
        if not (1 <= n <= len(chunks)):
            dropped.append({**q, "reason": "excerpt number out of range"}); continue
        c = chunks[n - 1]
        hay = normalise_for_match(c["text"])
        needle = normalise_for_match(q.get("text", ""))
        if len(needle) < 8:
            dropped.append({**q, "reason": "quote too short to verify"}); continue
        if needle in hay:
            kept.append({"chunk_id": c["chunk_id"], "goid": c["goid"], "page": c["page"],
                         "go_no": c["go_no"], "go_date": c["go_date"], "text": q["text"],
                         "box": [c["box_x"], c["box_y"], c["box_w"], c["box_h"]]})
        else:
            dropped.append({**q, "reason": "not found verbatim in the cited excerpt"})
    return kept, dropped


def answer(con, question, provider="ollama", limit=6, filters=None, model=None):
    chunks = S.search(con, question, limit=limit, filters=filters)
    if not chunks or chunks[0]["score"] < MIN_SCORE:
        return {"found": False, "answer": "Nothing in the indexed Government Orders matches this question.",
                "quotes": [], "chunks": chunks, "provider": provider, "reason": "no chunk above score threshold"}
    prompt = build_prompt(question, chunks)
    raw = (call_anthropic if provider == "anthropic" else call_ollama)(SYSTEM, prompt, model)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        parsed = json.loads(m.group(0)) if m else {"answer": raw, "quotes": [], "found": True}
    kept, dropped = verify_quotes(parsed, chunks)
    found = bool(parsed.get("found", True)) and bool(kept)
    return {
        "found": found,
        "answer": parsed.get("answer", "").strip() if found else
                  "The indexed Government Orders do not appear to answer this. "
                  "Try different wording, or widen the filters.",
        "quotes": kept, "dropped_quotes": dropped, "chunks": chunks,
        "provider": provider, "model": model or (ANTHROPIC_MODEL if provider == "anthropic" else OLLAMA_MODEL),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--provider", choices=["ollama", "anthropic"], default="ollama")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=6)
    a = ap.parse_args()
    con = connect()
    r = answer(con, a.question, provider=a.provider, limit=a.limit, model=a.model)
    print(json.dumps({k: v for k, v in r.items() if k != "chunks"}, ensure_ascii=False, indent=1))
    print(f"\nretrieved {len(r['chunks'])} chunks; top: "
          f"{r['chunks'][0]['go_no'] if r['chunks'] else '-'}")
