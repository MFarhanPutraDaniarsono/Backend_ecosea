import os
import re
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Chunk:
    """Potongan teks dari knowledge base."""

    id: str
    text: str


_MULTI_NEWLINE = re.compile(r"\n{3,}")


def _normalize_text(text: str) -> str:
    # rapikan newline, spasi, dll
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTI_NEWLINE.sub("\n\n", text)

    # Banyak KB yang berasal dari dokumen dengan line-wrap, jadi ada newline di tengah kalimat.
    # Kita rapikan: simpan pemisah paragraf (\n\n) lalu gabungkan newline tunggal.
    para_token = "<<PARA_BREAK>>"  # placeholder unik
    text = text.replace("\n\n", para_token)

    # Newline tunggal dianggap spasi (karena banyak dokumen hasil export punya wrap per baris).
    text = text.replace("\n", " ")

    # Perbaiki kasus umum split kata jadi "p antai", dll.
    # Heuristik aman: gabungkan hanya kalau gabungan katanya memang muncul di KB (vocab).
    vocab = set(re.findall(r"[A-Za-zÀ-ÿ]+", text.lower()))

    def _join_if_known(m: re.Match) -> str:
        left = m.group(1)
        right = m.group(2)
        combined = f"{left}{right}"
        return combined if combined in vocab else m.group(0)

    text = re.sub(r"\b([a-z]{1,2})\s+([a-z]{2,})\b", _join_if_known, text)
    text = text.replace(para_token, "\n\n")

    return text.strip()


def split_into_chunks(text: str, *, chunk_size: int = 650, chunk_overlap: int = 120) -> List[str]:
    """Split text berbasis karakter, tapi berusaha memotong di batas paragraf."""

    text = _normalize_text(text)
    if not text:
        return []

    # Pecah dulu per paragraf biar chunk lebih enak dibaca
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: List[str] = []
    cur = ""
    for p in paragraphs:
        candidate = (cur + "\n\n" + p).strip() if cur else p
        if len(candidate) <= chunk_size:
            cur = candidate
            continue

        if cur:
            chunks.append(cur)
            cur = ""

        # kalau paragraf panjang banget, potong pakai sliding window
        if len(p) > chunk_size:
            start = 0
            while start < len(p):
                end = min(len(p), start + chunk_size)
                chunks.append(p[start:end].strip())
                if end >= len(p):
                    break
                start = max(0, end - chunk_overlap)
        else:
            cur = p

    if cur:
        chunks.append(cur)

    # Catatan: overlap antar chunk sering bikin kata kepotong (mis. "p antai").
    # Untuk KB EcoSea yang paragrafnya cukup jelas, kita kembalikan chunk apa adanya.
    return chunks


def load_kb_chunks(kb_path: str, *, chunk_size: int = 650, chunk_overlap: int = 120) -> List[Chunk]:
    if not kb_path:
        raise ValueError("kb_path kosong")
    if not os.path.exists(kb_path):
        raise FileNotFoundError(f"Knowledge base tidak ditemukan: {kb_path}")

    with open(kb_path, "r", encoding="utf-8") as f:
        text = f.read()

    parts = split_into_chunks(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [Chunk(id=f"kb:{i}", text=p) for i, p in enumerate(parts)]
