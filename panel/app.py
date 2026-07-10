#!/usr/bin/env python3
"""
SenAI Pro - Panel Backend (Flask)
پنل مدیریت سرور ضد‌فیلتر
"""

import os
import json
import subprocess
import psutil
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "senai-pro-secret-change-me")

CONFIG_DIR = "/opt/senai-pro/config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DOMAIN_FILE = os.path.join(CONFIG_DIR, "domain.json")
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "admin")

# ─── Auth ───────────────────────────────────────────────────

def check_auth():
    return session.get("authenticated", False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == PANEL_PASSWORD:
            session["authenticated"] = True
            return redirect("/")
        return render_template("login.html", error="رمز عبور اشتباه است")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ─── Auth middleware ────────────────────────────────────────

@app.before_request
def require_auth():
    if request.endpoint in ("login", "static"):
        return None
    if not check_auth():
        return redirect("/login")
    return None

# ─── Helpers ────────────────────────────────────────────────

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def load_domain_config():
    try:
        with open(DOMAIN_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_domain_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(DOMAIN_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return False, str(e)

def get_warp_status():
    ok, output = run_cmd("warp-cli status 2>/dev/null")
    if ok and "Connected" in output:
        return "connected", output
    elif ok and "Disconnected" in output:
        return "disconnected", output
    return "not_installed", "Warp نصب نیست"

def get_doh_status():
    if os.path.exists("/etc/systemd/resolved.conf.d/doh.conf"):
        return True
    try:
        with open("/etc/resolv.conf") as f:
            return "1.1.1.1" in f.read()
    except Exception:
        return False

# ─── Routes ─────────────────────────────────────────────────

@app.route("/")
def dashboard():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    
    warp_status, warp_detail = get_warp_status()
    doh_status = get_doh_status()
    domain_cfg = load_domain_config()
    
    return render_template("dashboard.html",
        cpu=cpu,
        ram_total=ram.total,
        ram_used=ram.used,
        ram_percent=ram.percent,
        disk_total=disk.total,
        disk_used=disk.used,
        disk_percent=disk.percent,
        net_sent=net.bytes_sent,
        net_recv=net.bytes_recv,
        warp_status=warp_status,
        warp_detail=warp_detail,
        doh_status=doh_status,
        domain=domain_cfg.get("domain", ""),
        ssl_enabled=domain_cfg.get("ssl_enabled", False),
        uptime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

@app.route("/domains")
def domains_page():
    domain_cfg = load_domain_config()
    return render_template("domains.html", domain_cfg=domain_cfg)

@app.route("/ssl")
def ssl_page():
    domain_cfg = load_domain_config()
    return render_template("ssl.html", domain_cfg=domain_cfg)

@app.route("/anti-filter")
def anti_filter_page():
    warp_status, warp_detail = get_warp_status()
    doh_status = get_doh_status()
    return render_template("anti-filter.html",
        warp_status=warp_status,
        warp_detail=warp_detail,
        doh_status=doh_status)

@app.route("/firewall")
def firewall_page():
    ok, output = run_cmd("ufw status numbered 2>/dev/null")
    rules = output if ok else "فایروال نصب نیست"
    return render_template("firewall.html", rules=rules)

@app.route("/settings")
def settings_page():
    config = load_config()
    return render_template("settings.html", config=config)

# ─── API ────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    warp_status, _ = get_warp_status()
    return jsonify({
        "cpu": cpu,
        "ram_percent": ram.percent,
        "ram_used": ram.used,
        "ram_total": ram.total,
        "warp": warp_status,
        "doh": get_doh_status(),
        "timestamp": datetime.now().isoformat(),
    })

@app.route("/api/warp/<action>")
def api_warp(action):
    if action == "enable":
        ok, msg = run_cmd("warp-cli connect 2>/dev/null")
    elif action == "disable":
        ok, msg = run_cmd("warp-cli disconnect 2>/dev/null")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/doh/<action>")
def api_doh(action):
    if action == "enable":
        ok, msg = run_cmd("bash /opt/senai-pro/scripts/anti-filter.sh --enable-doh")
    elif action == "disable":
        ok, msg = run_cmd("bash /opt/senai-pro/scripts/anti-filter.sh --disable-doh")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/domain", methods=["POST"])
def api_domain():
    data = request.json or {}
    domain = data.get("domain", "").strip()
    email = data.get("email", "").strip()
    
    if not domain:
        return jsonify({"ok": False, "error": "دامنه الزامی است"})
    
    cfg = {"domain": domain, "email": email, "ssl_enabled": False, "cloudflare_proxy": False}
    save_domain_config(cfg)
    
    # Add to nginx
    nginx_conf = f"""server {{
    listen 80;
    server_name {domain} www.{domain};
    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
    client_max_body_size 50M;
}}"""
    
    with open(f"/etc/nginx/sites-available/{domain}", "w") as f:
        f.write(nginx_conf)
    
    os.symlink(f"/etc/nginx/sites-available/{domain}",
               f"/etc/nginx/sites-enabled/{domain}")
    
    ok, msg = run_cmd("nginx -t && systemctl reload nginx")
    return jsonify({"ok": ok, "message": f"دامنه {domain} اضافه شد"})

@app.route("/api/ssl", methods=["POST"])
def api_ssl():
    data = request.json or {}
    domain = data.get("domain", "").strip()
    email = data.get("email", "").strip()
    
    if not domain or not email:
        return jsonify({"ok": False, "error": "دامنه و ایمیل الزامی است"})
    
    cmd = f"certbot --nginx -d {domain} -d www.{domain} -m {email} --agree-tos --no-eff-email --non-interactive --redirect"
    ok, msg = run_cmd(cmd)
    
    if ok:
        cfg = load_domain_config()
        cfg["ssl_enabled"] = True
        save_domain_config(cfg)
    
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/firewall", methods=["POST"])
def api_firewall():
    data = request.json or {}
    action = data.get("action", "")
    port = data.get("port", "")
    proto = data.get("proto", "tcp")
    
    if action == "allow" and port:
        ok, msg = run_cmd(f"ufw allow {port}/{proto}")
    elif action == "deny" and port:
        ok, msg = run_cmd(f"ufw deny {port}/{proto}")
    elif action == "reload":
        ok, msg = run_cmd("ufw reload")
    elif action == "status":
        ok, msg = run_cmd("ufw status numbered")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/nginx/<action>")
def api_nginx(action):
    if action == "reload":
        ok, msg = run_cmd("nginx -t && systemctl reload nginx")
    elif action == "restart":
        ok, msg = run_cmd("systemctl restart nginx")
    elif action == "status":
        ok, msg = run_cmd("systemctl status nginx --no-pager")
    elif action == "test":
        ok, msg = run_cmd("nginx -t")
    else:
        return jsonify({"ok": False, "error": "action نامعتبر"})
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/logs")
def api_logs():
    log_type = request.args.get("type", "nginx")
    lines = request.args.get("lines", "50")
    
    log_files = {
        "nginx_access": "/var/log/nginx/access.log",
        "nginx_error": "/var/log/nginx/error.log",
        "senai": "/var/log/syslog",
    }
    
    log_file = log_files.get(log_type, log_files["nginx_error"])
    ok, output = run_cmd(f"tail -n {lines} {log_file} 2>/dev/null")
    return jsonify({"ok": ok, "logs": output})

# ─── Main ───────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PANEL_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
