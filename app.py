import os
import re
import subprocess
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
import requests

app = Flask(__name__)
app.secret_key = "super_secret_nginx_portal_key_change_me"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=5)

PORTAL_PASSWORD = "password"
AVAILABLE_DIR = "/etc/nginx/sites-available"
ENABLED_DIR = "/etc/nginx/sites-enabled"
# ================= cek id certbot =================
#  sudo ls /etc/letsencrypt/accounts/acme-v02.api.letsencrypt.org/directory/
CERTBOT_ACCOUNT_ID = "5a0a"

# ================= KREDENSIAL CLOUDFLARE =================
# Isi dengan API Token Cloudflare Anda (Permissions: Zone.Zone Read, Zone.DNS Edit)
CF_API_TOKEN = "PASTE_CLOUDFLARE_API_TOKEN_ANDA_DISINI"
# =========================================================


def run_command(cmd):
    try:
        res = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        return True, res.stdout or "Success"
    except subprocess.CalledProcessError as e:
        err = (e.stderr or "") + "\n" + (e.stdout or "")
        return False, err.strip() or str(e)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized. Silakan login."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def check_idle_timeout():
    session.modified = True
    if session.get("authenticated"):
        now = datetime.now().timestamp()
        last_active = session.get("last_active")
        if last_active and (now - last_active > 300):
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify({"error": "Sesi habis karena 5 menit idle."}), 401
            return redirect(url_for("login"))
        session["last_active"] = now


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password")
        if password == PORTAL_PASSWORD:
            session.permanent = True
            session["authenticated"] = True
            session["last_active"] = datetime.now().timestamp()
            return redirect(url_for("index"))
        else:
            error = "Password salah!"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


# --- ENDPOINT NGINX ---
@app.route("/api/sites", methods=["GET"])
@login_required
def get_sites():
    if not os.path.exists(AVAILABLE_DIR):
        return jsonify({"error": f"{AVAILABLE_DIR} tidak ditemukan"}), 500
    files = os.listdir(AVAILABLE_DIR)
    sites = []
    for f in files:
        is_enabled = os.path.islink(os.path.join(ENABLED_DIR, f))
        sites.append({"name": f, "enabled": is_enabled})
    return jsonify(sites)


@app.route("/api/sites/<name>", methods=["GET"])
@login_required
def get_site_content(name):
    path = os.path.join(AVAILABLE_DIR, name)
    if not os.path.exists(path):
        return jsonify({"error": "File tidak ditemukan"}), 404
    with open(path, "r") as f:
        content = f.read()
    return jsonify({"name": name, "content": content})


@app.route("/api/sites", methods=["POST"])
@login_required
def save_site():
    data = request.json or {}
    name = data.get("name")
    content = data.get("content")
    if not name or not content:
        return jsonify({"error": "Nama file dan konten wajib diisi"}), 400
    path = os.path.join(AVAILABLE_DIR, name)
    with open(path, "w") as f:
        f.write(content)
    return jsonify({"message": f"Konfigurasi {name} berhasil disimpan"})


@app.route("/api/sites/<name>/toggle", methods=["POST"])
@login_required
def toggle_site(name):
    avail_path = os.path.join(AVAILABLE_DIR, name)
    enabled_path = os.path.join(ENABLED_DIR, name)
    if os.path.islink(enabled_path):
        os.unlink(enabled_path)
        return jsonify({"message": f"Site {name} dinonaktifkan", "enabled": False})
    else:
        if not os.path.exists(avail_path):
            return jsonify({"error": "File sites-available tidak ada"}), 404
        os.symlink(avail_path, enabled_path)
        return jsonify({"message": f"Site {name} diaktifkan", "enabled": True})


@app.route("/api/service/<action>", methods=["POST"])
@login_required
def service_action(action):
    commands = {
        "test": "nginx -t",
        "reload": "systemctl reload nginx",
        "restart": "systemctl restart nginx",
    }
    if action not in commands:
        return jsonify({"error": "Action tidak valid"}), 400
    success, output = run_command(commands[action])
    return jsonify({"success": success, "output": output}), (200 if success else 400)


# --- ENDPOINT CERTBOT ---
@app.route("/api/certbot", methods=["POST"])
@login_required
def generate_ssl():
    data = request.json or {}
    domain = data.get("domain", "").strip()
    email = data.get("email", "").strip()

    if not domain:
        return jsonify({"error": "Domain wajib diisi"}), 400

    domain = re.sub(r"^https?://", "", domain).rstrip("/")
    domain_pattern = r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    if not re.match(domain_pattern, domain):
        return jsonify({"error": f"Format domain '{domain}' tidak valid."}), 400

    cmd = f"certbot --nginx -d {domain} --account {CERTBOT_ACCOUNT_ID} --non-interactive --agree-tos --redirect"
    if email:
        cmd += f" -m {email}"

    success, output = run_command(cmd)
    return jsonify({"success": success, "output": output}), (200 if success else 400)


# --- CLOUDFLARE ENDPOINTS ---
@app.route("/api/cloudflare/zones", methods=["GET"])
@login_required
def get_cloudflare_zones():
    url = "https://api.cloudflare.com/client/v4/zones?per_page=50&status=active"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if not data.get("success"):
            return jsonify({"error": data.get("errors", [{}])[0].get("message", "Gagal memuat zones")}), 400

        zones = [{"id": z["id"], "name": z["name"]} for z in data.get("result", [])]
        return jsonify(zones)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cloudflare/dns", methods=["POST"])
@login_required
def create_cloudflare_dns():
    data = request.json or {}
    zone_id = data.get("zone_id", "").strip()
    record_name = data.get("name", "").strip().lower()
    ip_address = data.get("ip_address", "").strip()
    proxied = data.get("proxied", False)

    if not zone_id or not record_name or not ip_address:
        return jsonify({"error": "Domain Utama (Zone), Nama Record/Subdomain, dan IP wajib diisi."}), 400

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "type": "A",
        "name": record_name,
        "content": ip_address,
        "ttl": 1,
        "proxied": proxied,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        res_data = response.json()
        if res_data.get("success"):
            return jsonify({
                "success": True,
                "message": f"DNS A-Record untuk '{record_name}' -> {ip_address} berhasil dibuat di Cloudflare!",
                "full_domain": res_data.get("result", {}).get("name")
            })
        else:
            errors = res_data.get("errors", [])
            error_msg = errors[0].get("message") if errors else "Gagal membuat DNS."
            return jsonify({"success": False, "error": f"Cloudflare API Error: {error_msg}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
