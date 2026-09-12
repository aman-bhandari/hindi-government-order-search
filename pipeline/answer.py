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
# Refusal is decided by the model plus quote verification, NOT by a retrieval threshold.
#
# Measured on this corpus with 26 answerable and 4 unanswerable questions: semantic similarity to the best
# passage ran 0.453-0.697 for answerable questions and 0.478-0.571 for unanswerable ones. The distributions
# overlap, so no single cutoff works: the best possible one kept 22 of 26 real questions while refusing only
# 2 of 4 bogus ones. Share of question terms present in the corpus fails the same way (answerable from 0.62,
# unanswerable up to 1.00), because bureaucratic Hindi shares most of its common vocabulary.
#
# So these gates are only a cheap filter to avoid spending a slow local model call on something with no
# lexical or semantic footing at all. The real decision is made downstream, where the model sees the passages
# and every quote it produces is checked against them.
MIN_COSINE = float(os.environ.get("MIN_COSINE", "0.40"))
MIN_COVERAGE = float(os.environ.get("MIN_COVERAGE", "0.20"))
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
        where = "subject line" if c.get("kind") == "subject" else f"page {c['page']}"
        subj = f"\nThat order is about: {c['subject']}" if c.get("kind") != "subject" and c.get("subject") else ""
        parts.append(f"[{i}] Government Order {c['go_no']}, dated {c['go_date']}, {where}, "
                     f"category {c['category']}{subj}\n{c['text']}")
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


# Compare quotes on their words alone. OCR of a scanned table produces markup noise ("|[6. |" for a row
# number), and a model reading that excerpt will tidy it; rejecting such a quote refuses a faithful answer
# over punctuation. Dropping non-word characters tolerates that, while still requiring the same words in the
# same order, so a paraphrase cannot pass.
_WORDISH = re.compile(r"[^\w\u0900-\u097F]+")


def normalise_for_match(s):
    return _WORDISH.sub(" ", (s or "").lower()).strip()


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
        if len(needle.replace(" ", "")) < 8:
            dropped.append({**q, "reason": "quote too short to verify"}); continue
        if needle in hay:
            kept.append({"chunk_id": c["chunk_id"], "goid": c["goid"], "page": c["page"],
                         "go_no": c["go_no"], "go_date": c["go_date"], "text": q["text"],
                         "box": [c["box_x"], c["box_y"], c["box_w"], c["box_h"]]})
        else:
            dropped.append({**q, "reason": "not found verbatim in the cited excerpt"})
    return kept, dropped


def is_relevant(chunks, top_n=3):
    """Cheap pre-filter: is anything retrieved worth spending a model call on?

    Returns (worth_trying, reason). This deliberately errs towards trying: see the note above on why a
    retrieval threshold cannot decide answerability on this corpus.
    """
    if not chunks:
        return False, "nothing matched the question"
    head = chunks[:top_n]
    cos = [c["cosine"] for c in head if c.get("cosine") is not None]
    cov = [c.get("lexical_coverage", 0.0) for c in head]
    best_cos = max(cos) if cos else None
    best_cov = max(cov) if cov else 0.0
    if best_cos is not None and best_cos >= MIN_COSINE:
        return True, f"semantic similarity {best_cos:.2f}"
    if best_cov >= MIN_COVERAGE:
        return True, f"term overlap {best_cov:.0%}"
    detail = f"term overlap {best_cov:.0%}"
    if best_cos is not None:
        detail += f", semantic similarity {best_cos:.2f}"
    return False, f"closest passages are not relevant ({detail})"


NOT_FOUND = ("The indexed Government Orders do not appear to cover this. "
             "This collection holds Information Technology Department orders only.")


def answer(con, question, provider="ollama", limit=6, filters=None, model=None):
    # Following subject hits into the order body was tried twice and measured worse both times; see
    # docs/RESULTS.md. Opt in per deployment with EXPAND_SUBJECTS=1.
    chunks = S.search(con, question, limit=limit, filters=filters,
                      expand_subjects=os.environ.get("EXPAND_SUBJECTS") == "1")
    relevant, reason = is_relevant(chunks)
    if not relevant:
        return {"found": False, "answer": NOT_FOUND, "quotes": [], "dropped_quotes": [],
                "chunks": chunks, "provider": provider, "reason": reason}
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
                  "No passage in these orders supported an answer to this question.",
        "reason": reason if found else "the model produced no quote that survived verification",
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
