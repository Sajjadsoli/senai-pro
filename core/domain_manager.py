#!/usr/bin/env python3
"""
SenAI Pro - Domain Manager
مدیریت دامنه‌ها و ضد‌فیلتر دامنه
"""

import os
import json
import subprocess

class DomainManager:
    """مدیریت دامنه‌های متصل به سرور"""

    def __init__(self):
        self.config_dir = "/opt/senai-pro/config"
        self.domain_file = os.path.join(self.config_dir, "domain.json")
        self.nginx_sites = "/etc/nginx/sites-available"
        self.nginx_enabled = "/etc/nginx/sites-enabled"

    def _run(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return r.returncode == 0, r.stdout.strip() or r.stderr.strip()
        except Exception as e:
            return False, str(e)

    def _load(self):
        try:
            with open(self.domain_file) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, cfg):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.domain_file, "w") as f:
            json.dump(cfg, f, indent=2)

    def add_domain(self, domain, email=""):
        """افزودن دامنه به Nginx"""
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
        conf_path = os.path.join(self.nginx_sites, domain)
        with open(conf_path, "w") as f:
            f.write(nginx_conf)

        enabled_path = os.path.join(self.nginx_enabled, domain)
        if os.path.islink(enabled_path) or os.path.exists(enabled_path):
            os.remove(enabled_path)
        os.symlink(conf_path, enabled_path)

        ok, msg = self._run("nginx -t && systemctl reload nginx")

        cfg = self._load()
        cfg.update({"domain": domain, "email": email, "ssl_enabled": False, "cloudflare_proxy": False})
        self._save(cfg)

        return ok, f"دامنه {domain} اضافه شد"

    def remove_domain(self, domain):
        """حذف دامنه از Nginx"""
        enabled = os.path.join(self.nginx_enabled, domain)
        available = os.path.join(self.nginx_sites, domain)

        if os.path.islink(enabled) or os.path.exists(enabled):
            os.remove(enabled)
        if os.path.exists(available):
            os.remove(available)

        ok, msg = self._run("nginx -t && systemctl reload nginx")
        return ok, f"دامنه {domain} حذف شد"

    def list_domains(self):
        """لیست دامنه‌های کانفیگ شده"""
        domains = []
        if os.path.exists(self.nginx_enabled):
            for f in os.listdir(self.nginx_enabled):
                if f != "senai-pro" and f != "default":
                    domains.append(f)
        return domains

    def get_current(self):
        """دامنه فعلی"""
        return self._load()
