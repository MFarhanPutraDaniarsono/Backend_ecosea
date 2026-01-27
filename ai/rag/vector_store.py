import math
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .loader import Chunk


_TOKEN_RE = re.compile(r"[A-Za-z0-9À-ÿ]+", flags=re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class BM25Index:
    """BM25 sederhana (tanpa dependensi eksternal).

    Cocok untuk KB kecil-menengah seperti chatbot.txt.
    """

    def __init__(self, chunks: List[Chunk], *, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b

        self._doc_tokens: List[List[str]] = []
        self._tf: List[Dict[str, int]] = []
        self._df: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._doc_lens: List[int] = []
        self._avg_len: float = 0.0

        self._build()

    def _build(self) -> None:
        n = len(self.chunks)
        if n == 0:
            self._avg_len = 0.0
            return

        for ch in self.chunks:
            toks = _tokenize(ch.text)
            self._doc_tokens.append(toks)
            tf: Dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            self._tf.append(tf)
            self._doc_lens.append(len(toks))

            for t in tf.keys():
                self._df[t] = self._df.get(t, 0) + 1

        self._avg_len = sum(self._doc_lens) / max(1, n)

        # IDF BM25 klasik
        for t, df in self._df.items():
            self._idf[t] = math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, query: str, *, k: int = 4) -> List[ScoredChunk]:
        if not query or not self.chunks:
            return []

        q_toks = _tokenize(query)
        if not q_toks:
            return []

        # hitung skor untuk tiap dokumen
        results: List[ScoredChunk] = []
        for idx, ch in enumerate(self.chunks):
            score = self._score_doc(idx, q_toks)
            if score > 0:
                results.append(ScoredChunk(chunk=ch, score=score))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[: max(1, k)]

    def _score_doc(self, doc_idx: int, q_toks: List[str]) -> float:
        tf = self._tf[doc_idx]
        dl = self._doc_lens[doc_idx]
        avg = self._avg_len or 1.0

        score = 0.0
        for t in q_toks:
            if t not in tf:
                continue
            f = tf[t]
            idf = self._idf.get(t, 0.0)
            denom = f + self.k1 * (1 - self.b + self.b * (dl / avg))
            score += idf * (f * (self.k1 + 1) / (denom or 1.0))
        return score


def build_index(chunks: List[Chunk]) -> BM25Index:
    return BM25Index(chunks)