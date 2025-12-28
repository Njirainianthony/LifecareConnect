---
description: Production deployment checklist for Lifecare Connect
---

# 🚀 Deployment Checklist

Before deploying to production, complete these steps:

## 1. Generate New Secret Key
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Copy the output and update `DJANGO_SECRET_KEY` in your production `.env` file.

## 2. Update Environment Variables
In your production environment, set:
```
DJANGO_SECRET_KEY=<your-new-secret-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

## 3. Update M-Pesa Callback URL
Change `MPESA_CALLBACK_URL` in `.env` to your production domain:
```
MPESA_CALLBACK_URL=https://your-domain.com/mpesa/callback/
```

## 4. Collect Static Files
```bash
// turbo
python manage.py collectstatic --noinput
```

## 5. Run Database Migrations
```bash
python manage.py migrate
```

## 6. Verify Deployment Check
```bash
// turbo
python manage.py check --deploy
```
All warnings should be resolved (or intentionally silenced).

## 7. Start with Gunicorn (Linux/Production Server)
```bash
gunicorn LifecareConnect.wsgi:application --bind 0.0.0.0:8000
```

## 8. Configure Reverse Proxy (Nginx/Apache)
Set up your web server to:
- Serve static files from `/staticfiles/`
- Proxy requests to Gunicorn
- Handle SSL/HTTPS certificates

---

## Quick Reference
| Setting | Development | Production |
|---------|-------------|------------|
| `DJANGO_DEBUG` | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | `your-domain.com` |
| `MPESA_ENVIRONMENT` | `sandbox` | `production` |
| `EMAIL_BACKEND` | Console | SMTP |
