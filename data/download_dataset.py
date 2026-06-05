"""
Script untuk mendownload dataset hukum Indonesia dari HuggingFace
Dataset: biznetgio/indonesia-law-qa-embeddings
Jalankan script ini SEKALI sebelum menjalankan aplikasi utama.

Cara pakai:
    pip install datasets pandas
    python download_dataset.py
"""

from datasets import load_dataset
import pandas as pd
import os

def download_and_prepare():
    print("=" * 60)
    print("Mendownload dataset hukum Indonesia dari HuggingFace...")
    print("=" * 60)

    # Load dataset dari HuggingFace
    ds = load_dataset("biznetgio/indonesia-law-qa-embeddings", split="train")

    # Konversi ke DataFrame pandas
    df = pd.DataFrame(ds)

    # Pilih kolom yang diperlukan untuk search engine
    # - title    : judul topik/peraturan
    # - question : pertanyaan hukum
    # - answer   : jawaban lengkap (teks panjang, field utama untuk similarity)
    # - summarize: ringkasan jawaban
    # - source   : URL sumber artikel
    kolom = ["title", "question", "answer", "summarize", "source"]
    df = df[kolom]

    # Bersihkan data: hapus baris yang kosong pada kolom penting
    df = df.dropna(subset=["title", "answer"])
    df = df.reset_index(drop=True)

    # Buat kolom 'text' sebagai gabungan title + question + summarize
    # Field ini yang akan digunakan sebagai input BM25 dan Dense Retrieval
    df["text"] = (
        df["title"].fillna("") + ". " +
        df["question"].fillna("") + " " +
        df["summarize"].fillna("")
    )

    # Simpan ke file CSV di folder data/
    output_path = os.path.join(os.path.dirname(__file__), "hukum_indonesia.csv")
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\n[OK] Dataset berhasil didownload!")
    print(f"   Total dokumen : {len(df)} baris")
    print(f"   Kolom         : {list(df.columns)}")
    print(f"   Disimpan di   : {output_path}")
    print(f"\nContoh data:")
    print(df[["title", "question"]].head(3).to_string())
    print("=" * 60)

if __name__ == "__main__":
    download_and_prepare()
