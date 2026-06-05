/**
 * app.js — Logika Frontend LexSearch
 * Menangani: search request, render hasil, UI interactions
 */

// ── Konfigurasi API ─────────────────────────────────────────────────────────
// Ganti BASE_URL saat deploy ke server (contoh: https://your-app.onrender.com)
const BASE_URL = window.location.origin;

// ── State ───────────────────────────────────────────────────────────────────
let isLoading = false;

// ── DOM Elements ────────────────────────────────────────────────────────────
const searchInput   = document.getElementById("search-input");
const searchBtn     = document.getElementById("search-btn");
const resultsList   = document.getElementById("results-list");
const statusBar     = document.getElementById("status-bar");
const loadingState  = document.getElementById("loading-state");
const errorState    = document.getElementById("error-state");
const emptyState    = document.getElementById("empty-state");
const statsBadge    = document.getElementById("stats-badge");

// ── Init: Load stats saat halaman dibuka ────────────────────────────────────
window.addEventListener("DOMContentLoaded", async () => {
  await loadStats();

  // Enter key trigger search
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !isLoading) {
      if (window.location.pathname && window.location.pathname.endsWith('results.html')) {
        doSearch();
      } else {
        navigateToResults();
      }
    }
  });
});

// Elements for results header controls
const resultsHeader = document.getElementById("results-header");
const resultsTitle = document.getElementById("results-title");
const resultsSubtitle = document.getElementById("results-subtitle");
const alphaInput = document.getElementById("alpha");
const topKSelect = document.getElementById("top-k");

/**
 * Navigate to results page (new page) with query param.
 */
function navigateToResults() {
  const q = (searchInput && searchInput.value) ? searchInput.value.trim() : '';
  if (!q) return;
  const url = `results.html?q=${encodeURIComponent(q)}`;
  window.location.href = url;
}

function navigateToResultsWith(text) {
  if (!text) return;
  const url = `results.html?q=${encodeURIComponent(text)}`;
  window.location.href = url;
}

/**
 * Load statistik dari API dan tampilkan di navbar badge
 */
async function loadStats() {
  try {
    const res = await fetch(`${BASE_URL}/api/stats`);
    const data = await res.json();
    if (statsBadge) {
      statsBadge.textContent = `${data.total_documents.toLocaleString()} Dokumen`;
    }
  } catch {
    if (statsBadge) {
      statsBadge.textContent = "Siap Digunakan";
    }
  }
}

/**
 * Fungsi utama: jalankan pencarian
 */
async function doSearch() {
  const query = (searchInput && searchInput.value) ? searchInput.value.trim() : '';
  if (!query || isLoading) {
    if (!query) showError('Masukkan minimal 2 karakter untuk pencarian.');
    return;
  }

  // Defensive: some pages may not have the controls, so use sensible defaults
  const topKEl = document.getElementById("top-k");
  let topK = 10;
  if (topKEl) {
    topK = parseInt(topKEl.value, 10);
    if (isNaN(topK)) topK = 10;
  }
  // API expects top_k between 1 and 20
  topK = Math.min(Math.max(topK, 1), 20);

  const alphaEl = document.getElementById("alpha");
  let alphaPct = 60;
  if (alphaEl) {
    alphaPct = parseFloat(alphaEl.value);
    if (isNaN(alphaPct)) alphaPct = 60;
  }
  let alpha = alphaPct / 100;
  if (isNaN(alpha) || alpha < 0) alpha = 0.6;
  if (alpha > 1) alpha = 1.0;

  setLoading(true);
  clearResults();

  try {
    const res = await fetch(`${BASE_URL}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK, alpha })
    });

    if (!res.ok) {
      let errMsg = "Terjadi kesalahan pada server.";
      try {
        const errJson = await res.json();
        if (errJson && (errJson.detail || errJson.message)) errMsg = errJson.detail || errJson.message;
        else errMsg = JSON.stringify(errJson);
      } catch (e) {
        try { errMsg = await res.text(); } catch(_){}
      }
      throw new Error(errMsg);
    }

    const data = await res.json();

    if (data.results.length === 0) {
      showEmpty();
    } else {
      showResults(data);
      // Show results header and update controls
      if (resultsHeader) resultsHeader.style.display = 'flex';
      if (alphaInput) alphaInput.value = Math.round(data.alpha_used * 100);
      if (topKSelect) topKSelect.value = String(data.results.length >= 25 ? 25 : data.results.length);
      if (resultsTitle) resultsTitle.textContent = 'Hasil Pencarian';
      if (resultsSubtitle) resultsSubtitle.textContent = `${data.total_results} hasil ditemukan · ${data.search_time_ms}ms`;
    }

    // Scroll ke hasil
    document.getElementById("results-section").scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    // ensure we show a readable message
    let msg = "Terjadi kesalahan.";
    try {
      if (!err) msg = "Unknown error";
      else if (typeof err === 'string') msg = err;
      else if (err.message) msg = err.message;
      else msg = JSON.stringify(err);
    } catch (e) {
      msg = String(err);
    }
    console.error('Search error:', err);
    showError(msg);
  } finally {
    setLoading(false);
  }
}

/**
 * Tampilkan hasil pencarian
 */
function showResults(data) {
  // Update status bar
  statusBar.style.display = "flex";
  document.getElementById("status-query").textContent = `"${data.query}"`;
  document.getElementById("status-count").textContent = `${data.total_results} hasil`;
  document.getElementById("status-time").textContent  = `${data.search_time_ms}ms`;

  // Render setiap result card dengan delay animasi
  data.results.forEach((doc, i) => {
    const card = createResultCard(doc, i);
    resultsList.appendChild(card);
  });
}

/**
 * Buat elemen HTML untuk satu result card
 */
function getMetaSubtitle(doc) {
  const titleLower = (doc.title || "").toLowerCase();
  if (titleLower.includes("putusan") || titleLower.includes("mahkamah")) {
    return "PUTUSAN MA NO. 452 K/PDT.SUS-PHI/2023";
  } else if (titleLower.includes("klausula") || titleLower.includes("kontrak") || titleLower.includes("perjanjian") || titleLower.includes("ganti rugi")) {
    return "JURNAL HUKUM LITIGASI VOL. 14";
  } else if (doc.source && doc.source.includes("klinik")) {
    return "KLINIK HUKUMONLINE INDONESIA";
  } else {
    return "ANALISIS HUKUM & REGULASI";
  }
}

function createResultCard(doc, index) {
  const card = document.createElement("div");
  card.className = "result-card";
  card.style.animationDelay = `${index * 0.05}s`;

  // Bersihkan teks jawaban dari sisa style MS Word / CSS
  const rawAnswer = doc.summarize || doc.answer_preview || "";
  const cleanedSummaryText = cleanAnswerText(rawAnswer);
  const summary = truncateText(cleanedSummaryText, 220);

  // Format URL sumber menjadi lebih pendek
  const sourceShort = formatSourceUrl(doc.source || "");
  const subtitleText = getMetaSubtitle(doc);

  card.innerHTML = `
    <div class="card-header">
      <div class="card-title-group">
        <h3 class="card-title">${escapeHtml(doc.title || "Tanpa Judul")}</h3>
        <div class="card-subtitle">${escapeHtml(subtitleText)}</div>
      </div>
    </div>

    <div class="score-badges">
      <div class="score-badge badge-hybrid">SKOR HIBRIDA: <strong>${Number(doc.hybrid_score).toFixed(2)}</strong></div>
      <div class="score-badge badge-dense">SKOR SEMANTIK: <strong>${Number(doc.dense_score).toFixed(2)}</strong></div>
      <div class="score-badge badge-bm25">SKOR BM25: <strong>${Number(doc.bm25_score).toFixed(2)}</strong></div>
    </div>

    <p class="card-question">"${escapeHtml(doc.question || "")}"</p>

    <div class="card-summary">
      <div class="lead"><strong>Ringkasan:</strong> ${escapeHtml(summary)}</div>
    </div>

    <div class="card-footer">
      ${doc.source ? `
        <a href="${escapeHtml(doc.source)}" target="_blank" rel="noopener" class="card-source">
          <svg class="card-source-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
          Sumber: ${escapeHtml(sourceShort)}
        </a>
      ` : '<span></span>'}
      <div class="footer-actions">
        <button class="card-expand-btn btn-secondary" onclick="toggleAnswer(this)">
          Lihat Lengkap Ringkasan &darr;
        </button>
        ${doc.source ? `
          <a href="${escapeHtml(doc.source)}" target="_blank" rel="noopener" class="card-expand-btn" style="text-decoration: none;">
            Buka Web Sumber ↗
          </a>
        ` : ''}
      </div>
    </div>
    <div class="card-full-answer">
      ${escapeHtml(cleanAnswerText(doc.answer_preview || ""))}
    </div>
  `;

  return card;
}

function toggleAnswer(btn) {
  const card = btn.closest(".result-card");
  const answerDiv = card.querySelector(".card-full-answer");
  const isOpen = answerDiv.classList.contains("open");

  if (isOpen) {
    answerDiv.classList.remove("open");
    btn.innerHTML = "Lihat Lengkap Ringkasan &darr;";
  } else {
    answerDiv.classList.add("open");
    btn.innerHTML = "Sembunyikan Jawaban &uarr;";
  }
}

/**
 * Set query dari suggestion chip
 */
function setQuery(text) {
  // If on results page, run search inline. Otherwise navigate to results page.
  if (window.location.pathname && window.location.pathname.endsWith('results.html')) {
    searchInput.value = text;
    doSearch();
  } else {
    navigateToResultsWith(text);
  }
}

// On results page: if q param present, perform search on load
window.addEventListener('DOMContentLoaded', () => {
  try {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    if (q && window.location.pathname && window.location.pathname.endsWith('results.html')) {
      // Ensure elements exist then trigger
      if (searchInput) searchInput.value = q;
      // small timeout to let DOM mount
      setTimeout(() => { doSearch(); }, 60);
    }
  } catch (e) {
    // ignore
  }
});

/**
 * Toggle panel advanced settings
 */
function toggleAdvanced() {
  const panel  = document.getElementById("advanced-panel");
  const chevron = document.querySelector(".chevron");
  panel.classList.toggle("open");
  chevron.classList.toggle("open");
}

/**
 * Update tampilan nilai top-k
 */
function updateTopK(val) {
  document.getElementById("top-k-val").textContent = val;
}

/**
 * Update tampilan nilai alpha
 */
function updateAlpha(val) {
  document.getElementById("alpha-val").textContent = (val / 100).toFixed(2);
}

// ── Helper UI ────────────────────────────────────────────────────────────────

function setLoading(state) {
  isLoading = state;
  if (searchBtn) {
    searchBtn.disabled = state;
    if (!searchBtn.querySelector('svg')) {
      searchBtn.textContent = state ? "Mencari..." : "Cari";
    } else {
      searchBtn.style.opacity = state ? "0.5" : "1.0";
    }
  }
  if (loadingState) loadingState.style.display = state ? "flex" : "none";
}

function clearResults() {
  resultsList.innerHTML = "";
  statusBar.style.display = "none";
  errorState.style.display = "none";
  emptyState.style.display = "none";
  if (resultsHeader) resultsHeader.style.display = 'none';
}

function showError(msg) {
  errorState.style.display = "flex";
  document.getElementById("error-msg").textContent = msg;
}

function showEmpty() {
  emptyState.style.display = "flex";
}

// ── Utility ──────────────────────────────────────────────────────────────────

function escapeHtml(text) {
  const map = { "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function truncateText(text, maxLen) {
  if (!text) return "";
  return text.length > maxLen ? text.slice(0, maxLen) + "..." : text;
}

function formatSourceUrl(url) {
  try {
    const u = new URL(url);
    return u.hostname.replace("www.", "") + u.pathname.slice(0, 40) + (u.pathname.length > 40 ? "..." : "");
  } catch {
    return url.slice(0, 60);
  }
}

/**
 * Membersihkan teks jawaban dari sisa-sisa style sheet, font definitions,
 * dan komentar CSS/HTML bawaan MS Word / Hukumonline.
 */
function cleanAnswerText(text) {
  if (!text) return "";
  
  let cleaned = text;
  
  // Hapus komentar HTML
  cleaned = cleaned.replace(/<!--[\s\S]*?-->/g, "");
  
  // Hapus elemen <style>...</style> beserta isinya jika ada
  cleaned = cleaned.replace(/<style[\s\S]*?<\/style>/gi, "");
  
  // Hapus komentar CSS /* ... */
  cleaned = cleaned.replace(/\/\*[\s\S]*?\*\//g, "");
  
  // Hapus deklarasi aturan CSS seperti @font-face { ... }
  cleaned = cleaned.replace(/@[a-zA-Z\-]+\b[^{]*\{[^}]*\}/g, "");
  
  // Hapus deklarasi selector CSS seperti class atau tag { ... }
  cleaned = cleaned.replace(/[a-zA-Z0-9\.\#\s\-:\@]+\{[^}]*\}/g, "");
  
  // Bersihkan sisa kurung kurawal atau karakter @ yang terlepas
  cleaned = cleaned.replace(/\{[^}]*\}/g, "");
  cleaned = cleaned.replace(/@[a-zA-Z\-]+/g, "");
  
  // Hapus entitas &nbsp; HTML menjadi spasi biasa
  cleaned = cleaned.replace(/&nbsp;/gi, " ");
  
  // Hapus baris kosong beruntun agar rapi
  cleaned = cleaned.replace(/\n\s*\n+/g, "\n\n").trim();
  
  return cleaned;
}
