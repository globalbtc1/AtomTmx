# AtomTmx
Lightweight AI chat TUI for Termux with OpenAI API compatibility
## Features

- AI chat TUI untuk Termux
- OpenAI-compatible API
- OpenAI
- OpenRouter
- Groq
- DeepSeek
- Streaming response
- Chat history
- Model list
- Multiple conversations
- Local API key storage
- Tidak membutuhkan server


# Panduan Instalasi TermChat (untuk Pemula)

TermChat adalah aplikasi chat AI yang berjalan di dalam Termux di HP Android. Tampilannya mirip aplikasi chat biasa dan bisa memakai API key yang kompatibel dengan OpenAI. Tidak perlu server tambahan.

## Yang Perlu Disiapkan

- HP Android
- Koneksi internet
- API key (dari OpenAI, OpenRouter, Groq, DeepSeek, atau penyedia lain)
- File `install.sh` 

---

## Langkah 1: Pasang Termux

> ⚠️ Jangan pasang Termux dari Play Store, versinya sudah usang dan sering gagal.

1. Buka browser, lalu kunjungi **https://f-droid.org/packages/com.termux/**
2. Unduh dan pasang **Termux** (file APK).
3. Jika diminta izin "Pasang dari sumber tidak dikenal", izinkan.

## Langkah 2: Siapkan File Installer

1. Simpan file **install.sh**.
2. File biasanya masuk ke folder **Download**.

## Langkah 3: Beri Termux Akses ke Penyimpanan

Buka Termux, lalu ketik perintah ini dan tekan Enter:

```
termux-setup-storage
```

Akan muncul jendela izin. Tekan **Izinkan**.

## Langkah 4: Jalankan Installer

Ketik perintah ini satu per satu, tekan Enter setelah tiap baris:

```
cd ~/storage/downloads
```

```
bash install.sh
```

Tunggu sampai muncul tulisan:

```
==> Selesai. Jalankan dengan perintah: termchat
```

Proses ini butuh beberapa menit, tergantung internet. Jika ada pertanyaan `Y/n`, ketik `y` lalu Enter.

> 💡 Jika muncul error "No such file", nama file mungkin berbeda (misalnya `install (1).sh`). Ketik `ls` untuk melihat daftar file, lalu ganti nama di perintah `bash` sesuai yang tampil.

## Langkah 5: Jalankan Aplikasi

```
termchat
```

Pada pemakaian pertama, jendela **Pengaturan** akan terbuka otomatis.

## Langkah 6: Isi Pengaturan API

| Kolom | Isi |
|---|---|
| **Base URL** | Alamat API penyedia (lihat tabel di bawah) |
| **API key** | Kunci API Anda |
| **Model** | Nama model, misalnya `gpt-4o-mini` |
| **System prompt** | Boleh dibiarkan bawaan |
| **Temperature** | Kosongkan saja |

Contoh Base URL:

| Penyedia | Base URL |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |

Tips:
- Tekan tombol **Daftar model** untuk memilih model dari daftar, jadi tidak perlu mengetik nama model.
- Tekan **Simpan** setelah selesai.

## Cara Memakai

Ketik pesan di kolom bawah, lalu tekan **Enter**. Jawaban AI muncul sedikit demi sedikit.

| Tombol | Fungsi |
|---|---|
| ☰ | Buka/tutup daftar percakapan |
| Baru | Mulai percakapan baru |
| Stop | Hentikan jawaban yang sedang berjalan |
| Ulang | Minta jawaban baru untuk pesan terakhir |
| Salin | Salin jawaban terakhir |
| Hapus | Hapus percakapan (tekan **dua kali** untuk konfirmasi) |
| ⚙ | Buka pengaturan API |

Untuk pindah percakapan, tekan **☰** lalu pilih judul percakapan.

## Cara Keluar

Tekan **Ctrl + Q**. Di Termux, tombol Ctrl ada di baris tombol tambahan di atas keyboard. Bisa juga ditekan bersamaan dengan tombol **Volume Bawah**.

## Membuka Lagi Nanti

Cukup buka Termux, lalu ketik:

```
termchat
```

Semua percakapan dan pengaturan tersimpan otomatis.

---

## Jika Ada Masalah

| Pesan / Masalah | Penyebab & Solusi |
|---|---|
| `HTTP 401` | API key salah atau kadaluarsa. Buka ⚙ dan periksa lagi. |
| `HTTP 404` | Base URL salah. Biasanya harus diakhiri `/v1`. |
| `model not found` | Nama model salah. Pakai tombol **Daftar model** di ⚙. |
| `HTTP 429` | Kuota habis atau terlalu sering mengirim. Tunggu sebentar atau cek saldo API. |
| `ConnectError` | Tidak ada internet, atau Base URL salah. |
| Tombol **Salin** tidak berfungsi | Jalankan `pkg install termux-api` dan pasang aplikasi **Termux:API** dari F-Droid. |
| Tampilan berantakan | Putar HP ke mode **landscape** atau perkecil ukuran font Termux. |
| Instalasi gagal | Jalankan `pkg update -y`, lalu ulangi `bash install.sh`. |

## Keamanan

- **Jangan bagikan API key** ke siapa pun.
- Kunci disimpan di `~/.config/termchat/config.json`, hanya di HP Anda.
- Untuk memperbarui atau mengganti API key, buka ⚙ di dalam aplikasi.
