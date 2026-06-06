import re
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


def preprocess_text(text: str) -> list[str]:
    """Preprocessing teks untuk BM25 (sama dengan indexer.py)."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def clean_answer_text(text: str) -> str:
    """
    Membersihkan teks jawaban dari sisa-sisa style sheet, font definitions,
    dan komentar CSS/HTML bawaan MS Word / Hukumonline.
    """
    if not text or not isinstance(text, str):
        return ""
    
    cleaned = text
    
    # 1. Hapus komentar HTML <!-- ... -->
    cleaned = re.sub(r"<!--[\s\S]*?-->", "", cleaned)
    
    # 2. Hapus elemen <style>...</style> beserta isinya jika ada
    cleaned = re.sub(r"<style[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
    
    # 3. Hapus komentar CSS /* ... */
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)
    
    # 4. Hapus deklarasi aturan CSS seperti @font-face { ... }
    cleaned = re.sub(r"@[a-zA-Z\-]+\b[^{]*\{[^}]*\}", "", cleaned)
    
    # 5. Hapus deklarasi selector CSS seperti class atau tag { ... }
    cleaned = re.sub(r"[a-zA-Z0-9\.\#\s\-:\@]+\{[^}]*\}", "", cleaned)
    
    # 6. Bersihkan sisa kurung kurawal atau karakter @ yang terlepas
    cleaned = re.sub(r"\{[^}]*\}", "", cleaned)
    cleaned = re.sub(r"@[a-zA-Z\-]+", "", cleaned)
    
    # 7. Hapus entitas &nbsp; HTML menjadi spasi biasa
    cleaned = re.sub(r"&nbsp;", " ", cleaned, flags=re.IGNORECASE)
    
    # 8. Hapus label ULASAN LENGKAP di awal teks
    cleaned = re.sub(r"^ULASAN LENGKAP\s*[:.-]*\s*", "", cleaned, flags=re.IGNORECASE)
    
    # 9. Hapus baris kosong beruntun agar rapi
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    
    return cleaned.strip()


def hybrid_search(
    query: str,
    bm25: BM25Okapi,
    embeddings: np.ndarray,
    documents: list[dict],
    model: SentenceTransformer,
    top_k: int = 10,
    alpha: float = 0.6
) -> list[dict]:
    """
    Fungsi utama Hybrid Search.

    Parameter:
    ----------
    query     : string pencarian dari user
    bm25      : objek BM25Okapi yang sudah di-index
    embeddings: matrix embedding semua dokumen (shape: N x dim)
    documents : list dokumen original
    model     : SentenceTransformer model untuk encode query
    top_k     : jumlah hasil yang dikembalikan
    alpha     : bobot dense score (0.0 = pure BM25, 1.0 = pure dense)

    Return:
    -------
    List of dict berisi dokumen + skor similarity
    """

    # ── 1. BM25 Scoring ───────────────────────────────────────────────────────
    # Tokenisasi query dengan preprocessing yang sama saat indexing
    tokenized_query = preprocess_text(query)

    # Hitung skor BM25 untuk semua dokumen
    bm25_scores = bm25.get_scores(tokenized_query)

    # Normalisasi BM25 score ke range [0, 1] menggunakan min-max normalization
    bm25_min = bm25_scores.min()
    bm25_max = bm25_scores.max()
    if bm25_max - bm25_min > 0:
        bm25_scores_norm = (bm25_scores - bm25_min) / (bm25_max - bm25_min)
    else:
        bm25_scores_norm = bm25_scores

    # ── 2. Dense Scoring ──────────────────────────────────────────────────────
    # Encode query menjadi embedding vector
    query_embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True   # normalisasi agar dot product = cosine similarity
    )

    # Hitung cosine similarity antara query embedding dan semua dokumen
    # Karena sudah dinormalisasi, cukup dengan dot product
    dense_scores = np.dot(embeddings, query_embedding)

    # Normalisasi dense score ke range [0, 1]
    dense_min = dense_scores.min()
    dense_max = dense_scores.max()
    if dense_max - dense_min > 0:
        dense_scores_norm = (dense_scores - dense_min) / (dense_max - dense_min)
    else:
        dense_scores_norm = dense_scores

    # ── 3. Hybrid Score ───────────────────────────────────────────────────────
    # Gabungkan BM25 dan Dense dengan bobot alpha
    # alpha = 0.6 → dense lebih dominan (cocok untuk query bahasa sehari-hari)
    hybrid_scores = (alpha * dense_scores_norm) + ((1 - alpha) * bm25_scores_norm)

    # ── 4. Ambil Top-K Hasil ──────────────────────────────────────────────────
    # Urutkan berdasarkan hybrid score tertinggi
    top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

    results = []
    for rank, idx in enumerate(top_indices):
        doc = documents[idx].copy()

        # Tambahkan informasi skor ke dokumen
        doc["hybrid_score"]  = round(float(hybrid_scores[idx]), 4)
        doc["bm25_score"]    = round(float(bm25_scores_norm[idx]), 4)
        doc["dense_score"]   = round(float(dense_scores_norm[idx]), 4)
        doc["rank"]          = rank + 1

        # Bersihkan dan potong field 'answer' agar tidak terlalu panjang di response API
        raw_answer = doc.get("answer", "")
        clean_ans = clean_answer_text(raw_answer)
        if len(clean_ans) > 800:
            doc["answer_preview"] = clean_ans[:800] + "..."
        else:
            doc["answer_preview"] = clean_ans

        results.append(doc)

    return results
