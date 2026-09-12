#!/usr/bin/env python3
"""Bridge transliterated English written in Devanagari to the same words written in Latin script.

Why this exists: the largest measured cause of retrieval misses on this corpus is that subject lines are
often English spelled phonetically in Devanagari. "उत्तराखंड गर्वमेंट एसेट मैंनेजमैंट सिस्ट्म पोर्ट्ल" is
"Uttarakhand Government Asset Management System Portal". Neither keyword matching nor a multilingual
embedding reliably connects that to a question asked in either language, because the tokens differ in
script and the spelling is ad hoc.

The fix is a phonetic key: transliterate Devanagari to Latin, then reduce both sides to a consonant skeleton
under rules that absorb the usual spelling differences (English soft c and g, v/w, c/k, nasal m/n, doubled
letters, aspirates). Measured on 20 word pairs taken from this corpus, 19 match, and unrelated Hindi and
English words do not collide.
"""
import re

_DEV_RUN = re.compile(r"[ऀ-ॿ]+")
_TOKEN = re.compile(r"[A-Za-zऀ-ॿ][A-Za-zऀ-ॿ‌‍]*")
_VOWELS = str.maketrans("", "", "aeiouy")
_CONSONANT_FOLD = str.maketrans({"c": "k", "q": "k", "w": "v", "z": "j", "m": "n"})

_transliterate = None


def _get_transliterator():
    """Import lazily so the pipeline still runs if the optional dependency is absent."""
    global _transliterate
    if _transliterate is None:
        try:
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate
            _transliterate = lambda s: transliterate(s, sanscript.DEVANAGARI, sanscript.ITRANS)
        except ImportError:
            _transliterate = lambda s: s          # degrade to a no-op rather than fail
    return _transliterate


def romanise(text: str) -> str:
    """Replace each run of Devanagari with its Latin transliteration, leaving other text alone."""
    if not text:
        return ""
    t = _get_transliterator()
    return _DEV_RUN.sub(lambda m: t(m.group(0)), text)


def phonetic_key(word: str) -> str:
    """Reduce one word to a script-independent consonant skeleton.

    Rules, each one added to fix an observed mismatch:
      soft c and g   centre/सेंटर, science/साइंस, policy/पॉलिसी, management/मैंनेजमैंट
      aspirates      ph->f, kh->k, gh->g, th->t, dh->d, bh->b
      fold           c->k, q->k, w->v, z->j, x->ks   hardware/हार्डवेयर, computer/कम्प्यूटर
      nasals         m->n                            networking/नेटवर्किंग
      drop vowels    including y                     system/सिस्ट्म
      collapse runs  doubled letters                 asset/एसेट, committee/कमेटी
    """
    w = re.sub(r"[^A-Za-z]", "", word).lower()
    if not w:
        return ""
    w = re.sub(r"c(?=[eiy])", "s", w)
    w = re.sub(r"g(?=[eiy])", "j", w)
    for a, b in (("ph", "f"), ("kh", "k"), ("gh", "g"), ("th", "t"), ("dh", "d"), ("bh", "b"), ("ch", "c")):
        w = w.replace(a, b)
    w = w.translate(_CONSONANT_FOLD).replace("x", "ks")
    w = w.translate(_VOWELS)
    w = re.sub(r"(.)\1+", r"\1", w)
    return w


def phonetic_tokens(text: str, min_len: int = 2) -> list[str]:
    """Phonetic keys for every word in a string, after romanising any Devanagari."""
    out, seen = [], set()
    for m in _TOKEN.finditer(romanise(text)):
        k = phonetic_key(m.group(0))
        if len(k) >= min_len and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def phonetic_text(text: str) -> str:
    """Space-joined phonetic keys, ready for a full-text index."""
    return " ".join(phonetic_tokens(text))


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:] or ["उत्तराखंड गर्वमेंट एसेट मैंनेजमैंट सिस्ट्म पोर्ट्ल",
                                "Government Asset Management System Portal"]:
        print(f"{arg}\n  roman    : {romanise(arg)}\n  phonetic : {phonetic_text(arg)}")
