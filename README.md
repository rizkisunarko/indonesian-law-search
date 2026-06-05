# ⚖ LexSearch — Search Engine Hukum Indonesia
**Tugas UAS · Mata Kuliah Temu Kembali Informasi**

Aplikasi search engine tematik berbasis **Hybrid Search (BM25 + Dense Retrieval)**
untuk pencarian peraturan dan informasi hukum Indonesia.

---

## 📦 Dataset

- **Sumber**: [biznetgio/indonesia-law-qa-embeddings](https://huggingface.co/datasets/biznetgio/indonesia-law-qa-embeddings)
- **Jumlah**: 7.170 topik hukum Indonesia
- **Field utama**: title, question, answer (teks panjang), summarize, source
- **Asal konten**: hukumonline.com

---

## 🔍 Metode: Hybrid Search

```
Hybrid Score = (alpha × Dense Score) + ((1 - alpha) × BM25 Score)
```

- **BM25** (rank_bm25): lexical matching berbasis frekuensi kata
- **Dense Retrieval** (sentence-transformers): semantic similarity berbasis embedding
- **Alpha default**: 0.6 (dense lebih dominan untuk query natural language)

---

## 🛠 Instalasi & Menjalankan

### 1. Clone / Download project

```bash
unzip NIM-tugas-UAS.zip
cd NIM-tugas-UAS
```

### 2. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Download dataset

```bash
python data/download_dataset.py
```

> Dataset akan disimpan di `data/hukum_indonesia.csv`

### 4. Build index (BM25 + Dense Embedding)

```bash
python backend/indexer.py
```

> Proses ini butuh beberapa menit (download model ~120MB + hitung 7k embeddings)

### 5. Jalankan server

```bash
uvicorn backend.main:app --reload --port 8000
```

### 6. Buka browser

```
http://localhost:8000
```

---

## 📁 Struktur File

```
indonesian-law-search/
├── dataset_link.txt          # Link dataset
├── README.md                 # Panduan ini
├── render.yaml               # Konfigurasi deploy Render
│
├── data/
│   └── download_dataset.py   # Script download dataset dari HuggingFace
│
├── backend/
│   ├── main.py               # FastAPI application
│   ├── search_engine.py      # Logika Hybrid Search
│   ├── indexer.py            # Build & load BM25 + Dense index
│   ├── requirements.txt      # Library Python
│   ├── bm25_index.pkl        # Index BM25 (hasil build)
│   ├── embeddings.npy        # Dense embeddings (hasil build)
│   └── documents.pkl         # Metadata dokumen (hasil build)
│
├── frontend/
│   ├── index.html            # Halaman utama UI
│   ├── results.html          # Halaman hasil pencarian
│   ├── style.css             # Styling
│   ├── app.js                # Logic JavaScript
│   └── assets/
│       └── gambar.png        # Asset gambar frontend
│
└── docs/                     # Versi static site
    ├── index.html
    ├── results.html
    ├── style.css
    ├── app.js
    └── assets/
        └── gambar.png
```

---

## 📊 API Endpoints

| Method | Endpoint      | Deskripsi                    |
|--------|---------------|------------------------------|
| GET    | `/`           | Halaman utama frontend       |
| GET    | `/api/health` | Status server                |
| POST   | `/api/search` | Endpoint pencarian utama     |
| GET    | `/api/stats`  | Statistik dataset            |

### Contoh request search:

```json
POST /api/search
{
  "query": "cara mengurus sertifikat tanah",
  "top_k": 10,
  "alpha": 0.6
}
```

---

## 📚 Library Utama

| Library | Fungsi |
|---------|--------|
| `fastapi` | Web framework backend |
| `rank-bm25` | BM25 scoring algorithm |
| `sentence-transformers` | Dense embedding model |
| `datasets` | Download dataset HuggingFace |
| `uvicorn` | ASGI server |
