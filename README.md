# Nginx Control Portal

Web Portal berbasis Python (Flask) dan Tailwind CSS untuk mengelola virtual host Nginx, integrasi DNS Cloudflare (semua domain/zone otomatis), penerbitan sertifikat SSL via Certbot (Let's Encrypt), serta kontrol service Nginx (`nginx -t`, `reload`, `restart`).

---

## Fitur Utama

- **Manajemen Virtual Host Nginx**:
  - Membaca, menambah, dan mengedit file konfigurasi di `/etc/nginx/sites-available`.
  - Toggle Aktif / Nonaktif (symlink otomatis ke `/etc/nginx/sites-enabled`).
  - Fitur pencarian realtime, filter status (Aktif/Nonaktif), dan pengurutan alfabetis (A-Z / Z-A).
- **Integrasi Cloudflare DNS**:
  - Otomatis mengambil seluruh domain utama (Zone ID) dari akun Cloudflare.
  - Menambahkan Subdomain / A-Record baru langsung ke Cloudflare.
  - Opsi toggle Cloudflare Proxy (Orange Cloud / DNS Only).
- **Let's Encrypt SSL Generator (Certbot)**:
  - Eksekusi `certbot --nginx` non-interaktif langsung dari web.
  - Dukungan pemilihan akun certbot default (`--account`).
- **Kontrol Service Nginx**:
  - Test konfigurasi (`nginx -t`).
  - Reload service (`systemctl reload nginx`).
  - Restart service (`systemctl restart nginx`).
- **Keamanan**:
  - Single password authentication (`K0song!n`).
  - Idle session auto-logout timeout selama 5 menit.
  - Terminal log execution realtime di dashboard.

---

## Struktur Direktori

```text
nginx-portal/
├── app.py
├── nginx-portal.service
├── README.md
└── templates/
    ├── index.html
    └── login.html
```

---

## Prasyarat Server (Ubuntu / Debian)

Pastikan paket Nginx, Python 3, pip, dan Certbot sudah terpasang:

```bash
sudo apt update
sudo apt install -y python3 python3-pip nginx certbot python3-certbot-nginx git
pip3 install flask requests
```

---

## Konfigurasi Aplikasi (`app.py`)

Buka `app.py` dan sesuaikan variabel konfigurasi berikut:

1. **`CF_API_TOKEN`**: Isi dengan Cloudflare API Token Anda yang memiliki izin `Zone:Read` dan `DNS:Edit` pada semua domain.
2. **`CERTBOT_ACCOUNT_ID`**: Sesuaikan hash akun Let's Encrypt Anda (bisa dicek lewat `ls /etc/letsencrypt/accounts/acme-v02.api.letsencrypt.org/directory/`). Default saat ini: `5a0a`.
3. **`PORTAL_PASSWORD`**: Password login default: `K0song!n`.

---

## Instalasi dan Setup Systemd Service

Agar aplikasi berjalan di background dan otomatis aktif saat server menyala:

1. Letakkan seluruh project ini di folder server, misalnya `/opt/nginx-portal`:
   ```bash
   sudo mkdir -p /opt/nginx-portal
   # Salin seluruh file ke /opt/nginx-portal
   ```

2. Pasang service systemd:
   ```bash
   sudo cp /opt/nginx-portal/nginx-portal.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable nginx-portal
   sudo systemctl start nginx-portal
   ```

3. Cek status service:
   ```bash
   sudo systemctl status nginx-portal
   ```

4. Buka portal di browser:
   ```text
   http://IP_SERVER:5000
   ```

---

## Cara Push ke GitHub Repo

Jalankan perintah berikut di direktori server tempat file berada untuk mengunggah ke GitHub:

```bash
git init
git remote add origin https://github.com/barangbaru/nginx-portal.git
git branch -M main
git add .
git commit -m "feat: complete nginx web portal with cloudflare dns, certbot ssl, and systemd service"
git push -u origin main
```
