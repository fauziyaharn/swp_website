# README_DEPLOY

Panduan singkat untuk mendeploy backend AI ke Vercel dan menghubungkan frontend.

Ringkasan
- Backend (serverless) root: `ai-vercel/` → endpoint AI: `https://ai-sepasangwp.vercel.app/api/process`
- Frontend (sepasangwpl) akan menggunakan `VITE_API_URL=https://ai-sepasangwp.vercel.app`

Prasyarat
- Akses ke akun Vercel dan repo GitHub (atau push ke GitHub dulu).
- Jika model besar, URL publik model (`MODEL_URL`) atau Git LFS tersedia.
- Vercel CLI opsional: `npm i -g vercel`.

Folder yang harus dipush ke GitHub
- `ai-vercel/` (harus ada `vercel.json`, `api/`, `requirements.txt`, `download_model.py`)
- `transformers_swp/` (kode backend)
- `sepasangwp/` (kode frontend)

Jangan push
- Jangan push file `*.env`, kunci/API secret, atau model besar di `transformers_swp/models/` kecuali pakai Git LFS.
- Hapus/ignore log, `bench_*.json`, `__pycache__`, `node_modules/`.

Environment variables (Backend `ai-sepasangwp`)
- `MODEL_URL` (opsional) — URL publik ke file model (.pt). Jika diset, `ai-vercel/vercel-build` akan mengunduh model saat build.
- `ENABLE_SEQ2SEQ` (0/1) — aktifkan seq2seq generation (default 0 untuk production ringan)
- `LOG_LEVEL` — `INFO`/`DEBUG`
- `ALLOW_SYNC_INIT` — `1` untuk memaksa inisialisasi sinkron saat cold-start (opsional)

Langkah deploy backend (Dashboard)
1. Push repo ke GitHub dengan struktur di atas.
2. Buka Vercel → Import Project → Pilih repository → Set "Root Directory" ke `ai-vercel`.
3. Pada Environment Variables, tambahkan nilai dari bagian Environment variables di atas.
4. Deploy. Setelah build selesai, cek `https://<your-project>.vercel.app/health`.

Langkah deploy backend (CLI)
1. Dari folder `ai-vercel` jalankan:
```
vercel --prod --name ai-sepasangwp
vercel env add MODEL_URL production <your_model_url>
vercel env add ENABLE_SEQ2SEQ production 0
vercel env add LOG_LEVEL production INFO
vercel env add ALLOW_SYNC_INIT production 1
```

Catatan model & batasan serverless
- Vercel serverless memiliki limit ukuran package dan waktu build. Menginstall `torch`/`transformers` selama build seringkali gagal atau memakan waktu dan memori besar.
- Jika model > ~50–100MB: rekomendasi
  - Host model di S3/Hugging Face/Google Cloud Storage dan set `MODEL_URL`.
  - Atau gunakan hosted inference (Hugging Face Inference API / Replicate) dan ubah backend untuk memanggil endpoint tersebut.
  - Alternatif: gunakan VM/GPU (long-running) untuk inference.

Set frontend `sepasangwpl` (Vercel)
1. Di project frontend (`sepasangwpl`) set Environment Variable:
   - `VITE_API_URL` = `https://ai-sepasangwp.vercel.app`
2. Redeploy frontend agar env baru terpakai.

Verifikasi setelah deploy
- Cek health:
  - `GET https://ai-sepasangwp.vercel.app/health`
- Tes endpoint:
  - `POST https://ai-sepasangwp.vercel.app/api/process` dengan JSON `{ "text": "cari catering di bandung budget 20 juta" }`
- Buka frontend `https://sepasangwpl.vercel.app` dan coba UI agent.

Prewarm (opsional)
- Untuk mengurangi cold-start, panggil `GET /prewarm` atau kirim satu request ke `/api/process` segera setelah deploy.

Troubleshooting cepat
- 502 / Build failed: cek log build di Vercel — kemungkinan `pip install torch` gagal.
- 504 / Timeout pada /api/process: fungsi serverless melebihi waktu CPU/memory; pindahkan model ke hosted inference atau gunakan VM.
- CORS: backend sudah memakai `flask-cors`, tapi jika frontend domain berbeda, cek header di response.
- Jika Anda accidentally committed secrets/model: jangan push; hubungi saya untuk langkah `git filter-repo` / BFG.

Files tambahan yang saya buat untuk deploy
- `ai-vercel/vercel.json` — routes + function runtime
- `ai-vercel/api/process.py` & `ai-vercel/api/health.py` — wrapper WSGI untuk Vercel
- `ai-vercel/download_model.py` — helper build untuk download model dari `MODEL_URL`

Butuh bantuan saya?
- Saya bisa bantu membuat PR yang menambahkan `.gitattributes` dengan Git LFS hint, atau membuat contoh `vercel` CLI commands untuk Anda jalankan. Pilih yang mau saya bantu.

---
Ringkas dan cukup untuk memulai deploy. Jika mau, saya bisa buatkan `README_DEPLOY.md` versi ringkas untuk ditampilkan di folder `ai-vercel/` juga.