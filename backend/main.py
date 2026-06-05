import os
import sys
# Tambahkan folder backend ke path pencarian modul Python agar import lokal berjalan lancar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from indexer import build_index, load_index, index_exists
from search_engine import hybrid_search

# ── Global state untuk menyimpan index ────────────────────────────────────────
# Index dimuat sekali saat server start, lalu digunakan terus
bm25_index   = None
embeddings   = None
documents    = None
model        = None
total_docs   = 0


# ── Lifespan: load index saat server start ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager FastAPI:
    - Saat startup: load atau build index
    - Saat shutdown: cleanup (tidak diperlukan di sini)
    """
    global bm25_index, embeddings, documents, model, total_docs

    print("\n[START] Server starting...")

    if index_exists():
        # Index sudah ada → langsung load dari file (lebih cepat)
        bm25_index, embeddings, documents, model = load_index()
    else:
        # Index belum ada → build dulu (butuh beberapa menit)
        print("Index belum ditemukan, membangun index baru...")
        bm25_index, embeddings, documents, model = build_index()

    total_docs = len(documents)
    print(f"[READY] Server siap! Total dokumen: {total_docs}\n")

    yield  # server berjalan di sini

    print("Server shutting down...")


# ── Inisialisasi FastAPI ───────────────────────────────────────────────────────
app = FastAPI(
    title="Search Engine Hukum Indonesia",
    description="Hybrid Search (BM25 + Dense Retrieval) untuk peraturan perundang-undangan Indonesia",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware: izinkan request dari frontend (HTML lokal atau deployed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# ── Pydantic Models ───────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Query pencarian")
    top_k: int = Field(default=10, ge=1, le=20, description="Jumlah hasil yang dikembalikan")
    alpha: float = Field(default=0.6, ge=0.0, le=1.0, description="Bobot dense vs BM25 (0=pure BM25, 1=pure dense)")


class SearchResult(BaseModel):
    title: str
    question: str
    summarize: str
    answer_preview: str
    source: str
    hybrid_score: float
    bm25_score: float
    dense_score: float
    rank: int


class SearchResponse(BaseModel):
    query: str
    total_results: int
    search_time_ms: float
    alpha_used: float
    results: list[SearchResult]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve halaman utama frontend."""
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Search Engine Hukum Indonesia API", "docs": "/docs"}


@app.get("/style.css")
async def get_style():
    """Serve style.css ke root path."""
    return FileResponse(os.path.join(frontend_path, "style.css"))


@app.get("/app.js")
async def get_app():
    """Serve app.js ke root path."""
    return FileResponse(os.path.join(frontend_path, "app.js"))


@app.get("/{path_name:path}")
async def serve_frontend_file(path_name: str):
    """Serve arbitrary frontend file (e.g. results.html) from the frontend folder.

    Specific API routes (like /api/*) are defined earlier and will take precedence.
    If the requested file does not exist, fall back to index.html when available.
    """
    # sanitize path_name to avoid directory traversal
    safe_path = os.path.normpath(os.path.join(frontend_path, path_name))
    if safe_path.startswith(os.path.abspath(frontend_path)) and os.path.exists(safe_path) and os.path.isfile(safe_path):
        return FileResponse(safe_path)

    # fallback to index.html (useful for SPA-like navigation)
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/api/health")
async def health_check():
    """Cek status server dan index."""
    return {
        "status": "ok",
        "total_documents": total_docs,
        "index_loaded": bm25_index is not None,
        "model_loaded": model is not None
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Endpoint utama pencarian Hybrid Search.
    Menggabungkan BM25 (lexical) dan Dense Retrieval (semantic).
    """
    if bm25_index is None or embeddings is None:
        raise HTTPException(status_code=503, detail="Index belum siap, coba beberapa saat lagi.")

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")

    # Catat waktu mulai untuk menghitung search time
    start_time = time.time()

    # Jalankan hybrid search
    results = hybrid_search(
        query=request.query,
        bm25=bm25_index,
        embeddings=embeddings,
        documents=documents,
        model=model,
        top_k=request.top_k,
        alpha=request.alpha
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return SearchResponse(
        query=request.query,
        total_results=len(results),
        search_time_ms=elapsed_ms,
        alpha_used=request.alpha,
        results=results
    )


@app.get("/api/stats")
async def get_stats():
    """Statistik dataset yang digunakan."""
    return {
        "total_documents": total_docs,
        "dataset_source": "biznetgio/indonesia-law-qa-embeddings (HuggingFace)",
        "model_used": "paraphrase-multilingual-MiniLM-L12-v2",
        "search_method": "Hybrid Search (BM25 + Dense Retrieval)",
        "description": "Dataset berisi 7.170 topik hukum Indonesia dari hukumonline.com"
    }
