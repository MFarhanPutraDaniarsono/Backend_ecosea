import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from flask import current_app

from .loader import Chunk, load_kb_chunks
from .vector_store import BM25Index, ScoredChunk, build_index


@dataclass(frozen=True)
class RetrievalResult:
    reply: str
    contexts: List[str]


# Intent detection (sederhana)
_INTENT_QUICK = re.compile(r"\b(lapor|melapor|report|titik|koordinat|lokasi|foto|kotor|numpuk|muara|rob)\b", re.I)
_INTENT_WHY = re.compile(r"\b(kenapa|mengapa|alasan|dampak|bahaya|pengaruh|akibat)\b", re.I)
_INTENT_TRAVEL = re.compile(r"\b(wisata|liburan|rekomendasi|jalan\s?jalan|spot|pantai\s+mana|destinasi)\b", re.I)


def _pick_beach_name(question: str) -> Optional[str]:
    q = question.lower()
    # Tangkap beberapa referensi lokal yang sering dipakai
    mapping = {
        "pai": "Pantai Alam Indah (PAI)",
        "alam indah": "Pantai Alam Indah (PAI)",
        "muarareja": "Pantai Muarareja",
        "dampyak": "Pantai Dampyak",
        "purwahamba": "Pantai Purwahamba Indah",
        "randusanga": "Pantai Randusanga",
        "pulau kodok": "Pulau Kodok",
        "komodo": "Pantai Komodo",
        "batam sari": "Pantai Batam Sari",
    }
    for k, v in mapping.items():
        if k in q:
            return v
    if "tegal" in q:
        return "pantai sekitar Tegal"
    return None


def _extract_key_sentences(contexts: List[str], *, max_sentences: int = 2) -> List[str]:
    """Ambil 1-2 kalimat yang paling 'berisi' dari konteks."""
    if not contexts:
        return []

    # Normalisasi whitespace biar kalimatnya gak kepotong aneh
    text = "\n".join(contexts)
    text = re.sub(r"\s+", " ", text).strip()

    # Pisah kalimat (kasar tapi cukup)
    sentences = re.split(r"(?<=[\.!\?])\s+", text)
    # Skor kalimat: banyak kata kunci penting
    keywords = [
        "sampah", "plastik", "puntung", "jaring", "biota", "mangrove", "lamun",
        "edukasi", "konservasi", "wisata", "muara", "lapor", "EcoSea",
    ]

    scored: List[Tuple[int, str]] = []
    for s in sentences:
        ss = s.strip()
        if len(ss) < 40:
            continue
        # Hindari "kalimat" hasil gabungan list panjang yang bikin output berantakan
        if ss.count("-") >= 3:
            continue
        if "Lokasi pantai" in ss or "Konteks lokal" in ss:
            continue
        score = 0
        low = ss.lower()
        for k in keywords:
            if k.lower() in low:
                score += 1
        scored.append((score, ss))

    scored.sort(key=lambda x: (x[0], len(x[1])), reverse=True)
    out = []
    for _, s in scored[:max_sentences]:
        ss = s.strip()
        # Biar ringkas
        if len(ss) > 220:
            ss = ss[:217].rstrip() + "..."
        out.append(ss)
    return out


class EcoSeaRAG:
    """RAG engine untuk EcoSea.

    - Retrieval: BM25 dari knowledge base (chatbot.txt)
    - Generation: rule-based template agar tidak bergantung ke API/model eksternal.

    Catatan: kalau nanti mau pakai LLM, tinggal ganti fungsi _generate().
    """

    def __init__(self, *, kb_path: str, top_k: int = 4, chunk_size: int = 650, chunk_overlap: int = 120):
        self.kb_path = kb_path
        self.top_k = max(1, int(top_k))
        self.chunk_size = max(200, int(chunk_size))
        self.chunk_overlap = max(0, int(chunk_overlap))

        self._chunks: List[Chunk] = load_kb_chunks(
            kb_path,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        self._index: BM25Index = build_index(self._chunks)

    def retrieve(self, question: str, *, k: Optional[int] = None) -> List[str]:
        k = self.top_k if k is None else max(1, int(k))
        hits = self._index.search(question, k=k)
        return [h.chunk.text for h in hits]

    def answer(self, question: str, *, history: Optional[list] = None) -> RetrievalResult:
        contexts = self.retrieve(question, k=self.top_k)
        reply = self._generate(question, contexts, history=history)
        return RetrievalResult(reply=reply, contexts=contexts)

    def _generate(self, question: str, contexts: List[str], *, history: Optional[list] = None) -> str:
        q = (question or "").strip()
        if not q:
            return "Pesannya kosong nih. Coba tulis pertanyaanmu ya 😊"

        beach = _pick_beach_name(q)
        key_sents = _extract_key_sentences(contexts, max_sentences=2)

        # 1) Tindakan cepat / pelaporan
        if _INTENT_QUICK.search(q):
            headline = f"Oke, aku bantu. {('Kalau ini di ' + beach + ', ') if beach else ''}yang paling cepat bisa kamu lakukan:".strip()
            steps = [
                "1) Foto kondisi dari beberapa sudut + catat jam (kalau bisa) dan lokasi/titiknya.",
                "2) Pilah cepat: plastik (kresek/botol/sedotan) vs residu. Pakai sarung tangan kalau ada.",
                "3) Laporkan lewat EcoSea (foto + lokasi + detail). Kalau di area wisata, kabari juga pengelola/penjaga.",
            ]
            extra = ""
            if "muara" in q.lower() or "rob" in q.lower():
                extra = "\n\nCatatan: muara/drainase itu sering jadi titik sampah kiriman (apalagi pas hujan/rob), jadi laporannya penting banget."
            context_line = f"\n\nInfo singkat: {key_sents[0]}" if key_sents else ""
            return headline + "\n" + "\n".join(steps) + extra + context_line

        # 2) Kenapa / dampak
        if _INTENT_WHY.search(q):
            expl = key_sents[0] if key_sents else "Sampah (terutama plastik) bisa terbawa arus/ombak ke laut, merusak ekosistem, dan membahayakan biota."
            prevent = [
                "Yang bisa dicegah bareng-bareng:",
                "- Kurangi plastik sekali pakai (botol isi ulang, tas belanja ulang).",
                "- Buang sampah di tempatnya / bawa pulang kalau tempat sampah penuh.",
                "- Ikut bersih pantai atau ajak teman 2–5 menit ambil sampah sebelum pulang.",
            ]
            local = ""
            if beach or "pantura" in q.lower() or "tegal" in q.lower():
                local = "\n\nDi Pantura (terutama dekat muara/pemukiman), sampah juga sering kiriman dari sungai—jadi selain bersihin, laporan titik rawan itu ngebantu banget."
            return f"Singkatnya: {expl}\n\n" + "\n".join(prevent) + local

        # 3) Wisata / rekomendasi
        if _INTENT_TRAVEL.search(q):
            picks = [
                "Pantai Alam Indah (PAI)",
                "Pantai Muarareja",
                "Pantai Dampyak",
                "Pantai Purwahamba Indah",
                "Pantai Randusanga",
            ]
            if "tegal" in q.lower() or (beach and "Tegal" in beach):
                header = "Kalau sekitar Tegal/Pantura, beberapa opsi yang sering jadi pilihan:" 
            else:
                header = "Kalau kamu cari wisata pantai, coba pertimbangkan ini (terutama Pantura):"
            tips = [
                "Etika wisata bersih (biar pantainya tetap enak):",
                "- Datang tanpa ninggal sampah (bawa kantong sampah kecil).",
                "- Bawa botol minum isi ulang, kurangi jajan kemasan sekali pakai.",
                "- Sebelum pulang, 2–5 menit ambil sampah kecil di sekitar spotmu.",
            ]
            context_line = f"\n\nTambahan: {key_sents[0]}" if key_sents else ""
            return header + "\n- " + "\n- ".join(picks) + "\n\n" + "\n".join(tips) + context_line

        # 4) Default
        expl = key_sents[0] if key_sents else "Pantai itu penyangga ekosistem laut dan juga ruang wisata, jadi kebersihannya penting banget." 
        actions = [
            "Yang bisa kamu lakukan sekarang:",
            "- Bawa kantong sampah + botol minum isi ulang.",
            "- Pilah sampah (plastik / logam-kaca / organik / residu).",
            "- Kalau lihat titik kotor, foto + lokasi lalu lapor lewat EcoSea.",
        ]
        return f"{expl}\n\n" + "\n".join(actions)


_ENGINE: Optional[EcoSeaRAG] = None


def get_engine() -> EcoSeaRAG:
    """Singleton engine, dibuat saat pertama dipakai."""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    cfg = current_app.config
    kb_path = cfg.get("RAG_KB_PATH")
    _ENGINE = EcoSeaRAG(
        kb_path=kb_path,
        top_k=int(cfg.get("RAG_TOP_K", 4)),
        chunk_size=int(cfg.get("RAG_CHUNK_SIZE", 650)),
        chunk_overlap=int(cfg.get("RAG_CHUNK_OVERLAP", 120)),
    )
    return _ENGINE


def answer_question(question: str, *, history: Optional[list] = None) -> RetrievalResult:
    engine = get_engine()
    return engine.answer(question, history=history)
