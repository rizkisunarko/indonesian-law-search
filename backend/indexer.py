"""
indexer.py - Membangun index BM25 dan Dense Embedding untuk Hybrid Search

Proses:
1. Load dataset CSV
2. Preprocessing teks (tokenisasi untuk BM25)
3. Build BM25 index menggunakan rank_bm25
4. Build Dense index menggunakan sentence-transformers
5. Simpan index ke file (.pkl dan .npy) agar tidak perlu hitung ulang

Library:
- rank_bm25     : untuk BM25 scoring
- sentence-transformers : untuk dense embedding (semantic search)
- numpy         : operasi matrix embedding
- pickle        : simpan/load index BM25
"""

import os
import re
import pickle
import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# ── Path konstanta ─────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH   = os.path.join(BASE_DIR, "..", "data", "hukum_indonesia.csv")
BM25_PATH   = os.path.join(BASE_DIR, "bm25_index.pkl")
EMBED_PATH  = os.path.join(BASE_DIR, "embeddings.npy")
DOCS_PATH   = os.path.join(BASE_DIR, "documents.pkl")

# Model sentence-transformers untuk Bahasa Indonesia
# paraphrase-multilingual-MiniLM-L12-v2 mendukung Bahasa Indonesia dengan baik
# dan ukurannya relatif kecil (~120MB)
MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"


def preprocess_text(text: str) -> list[str]:
    """
    Preprocessing teks untuk BM25:
    - Lowercase
    - Hapus karakter non-alfanumerik
    - Tokenisasi sederhana (split by whitespace)
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    return tokens


def build_index():
    """
    Fungsi utama untuk membangun BM25 index dan Dense embedding index.
    Dipanggil sekali sebelum server dijalankan, atau otomatis jika index belum ada.
    """
    print("=" * 60)
    print("Membangun index Hybrid Search...")
    print("=" * 60)

    # ── 1. Load dataset ────────────────────────────────────────────────────────
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Dataset tidak ditemukan di {DATA_PATH}\n"
            "Jalankan dulu: python data/download_dataset.py"
        )

    df = pd.read_csv(DATA_PATH)
    print(f"[OK] Dataset loaded: {len(df)} dokumen")

    # Simpan dokumen lengkap untuk ditampilkan di hasil pencarian
    documents = df.to_dict(orient="records")

    # ── 2. Build BM25 Index ────────────────────────────────────────────────────
    print("\n[1/3] Membangun BM25 index...")
    # Tokenisasi field 'text' (gabungan title + question + summarize)
    tokenized_corpus = [preprocess_text(str(doc.get("text", ""))) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)
    print(f"      BM25 index selesai ({len(tokenized_corpus)} dokumen)")

    # ── 3. Build Dense Embedding Index ────────────────────────────────────────
    print(f"\n[2/3] Memuat model sentence-transformers: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("      Menghitung embedding... (ini bisa beberapa menit)")
    # Encode field 'text' — show_progress_bar agar terlihat prosesnya
    texts = [str(doc.get("text", "")) for doc in documents]
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True   # normalisasi agar cosine similarity = dot product
    )
    print(f"      Embedding shape: {embeddings.shape}")

    # ── 4. Simpan semua index ke file ─────────────────────────────────────────
    print("\n[3/3] Menyimpan index ke file...")

    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25, f)
    print(f"      BM25 index disimpan: {BM25_PATH}")

    np.save(EMBED_PATH, embeddings)
    print(f"      Embeddings disimpan: {EMBED_PATH}")

    with open(DOCS_PATH, "wb") as f:
        pickle.dump(documents, f)
    print(f"      Documents disimpan:  {DOCS_PATH}")

    print("\n[OK] Index berhasil dibangun!")
    print("=" * 60)
    return bm25, embeddings, documents, model


def load_index():
    """
    Load index yang sudah dibangun sebelumnya dari file.
    Dipanggil saat server FastAPI start.
    """
    print("Memuat index dari file...")

    with open(BM25_PATH, "rb") as f:
        bm25 = pickle.load(f)

    embeddings = np.load(EMBED_PATH)

    with open(DOCS_PATH, "rb") as f:
        documents = pickle.load(f)

    model = SentenceTransformer(MODEL_NAME)

    print(f"[OK] Index loaded: {len(documents)} dokumen")
    return bm25, embeddings, documents, model


def index_exists() -> bool:
    """Cek apakah semua file index sudah ada."""
    return (
        os.path.exists(BM25_PATH) and
        os.path.exists(EMBED_PATH) and
        os.path.exists(DOCS_PATH)
    )


if __name__ == "__main__":
    # Jalankan langsung untuk build index
    build_index()
