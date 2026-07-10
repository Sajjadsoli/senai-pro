# 📖 راهنمای نصب کامل SenAI Pro

## نصب سریع (یک خط)

```bash
bash <(curl -sL https://raw.githubusercontent.com/Sajjadsoli/senai-pro/main/scripts/install.sh)
```

## نصب دستی

```bash
git clone https://github.com/Sajjadsoli/senai-pro.git
cd senai-pro
chmod +x scripts/install.sh
sudo bash scripts/install.sh
```

## مراحل نصب

### ۱. پیش‌نیازها
نصب‌کننده به‌طور خودکار این بسته‌ها را نصب می‌کند:
- Python 3, pip, venv
- Nginx
- Certbot + Certbot Nginx plugin
- UFW (فایروال)
- Cloudflare Warp
- curl, wget, git, dnsutils

### ۲. ضد‌فیلتر
- نصب و فعال‌سازی Cloudflare Warp
- کانفیگ DNS over HTTPS (DoH)
- تنظیم DNS ضد‌فیلتر (1.1.1.1, 8.8.8.8)

### ۳. Nginx
- کانفیگ Reverse Proxy
- فعال‌سازی Gzip
- Security Headers
- Rate Limiting

### ۴. فایروال
- فعال‌سازی UFW
- باز کردن پورت‌های: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8443 (Panel)

### ۵. پنل وب
- نصب Flask و وابستگی‌ها
- ساخت سرویس systemd
- تولید رمز عبور خودکار

### ۶. دامنه و SSL
- دریافت دامنه و ایمیل از کاربر
- کانفیگ Nginx برای دامنه
- دریافت گواهی SSL از Let's Encrypt

## دسترسی به پنل

بعد از نصب:

```
http://YOUR_SERVER_IP:8443
```

یا با دامنه:
```
https://YOUR_DOMAIN
```

رمز عبور در پایان نصب نمایش داده می‌شود و در فایل زیر ذخیره می‌شود:
```
/opt/senai-pro/config/.env
```

## مدیریت سرویس

```bash
# شروع
systemctl start senai-pro

# توقف
systemctl stop senai-pro

# راه‌اندازی مجدد
systemctl restart senai-pro

# وضعیت
systemctl status senai-pro

# لاگ
journalctl -u senai-pro -f
```

## مدیریت ضد‌فیلتر

```bash
# فعال‌سازی Warp
bash /opt/senai-pro/scripts/anti-filter.sh --enable-warp

# غیرفعال‌سازی Warp
bash /opt/senai-pro/scripts/anti-filter.sh --disable-warp

# فعال‌سازی DoH
bash /opt/senai-pro/scripts/anti-filter.sh --enable-doh

# وضعیت
bash /opt/senai-pro/scripts/anti-filter.sh --status

# همه را فعال کن
bash /opt/senai-pro/scripts/anti-filter.sh --all
```

## حذف

```bash
sudo bash /opt/senai-pro/scripts/uninstall.sh
```
