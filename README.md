Kaleya / aikaleya.com

Projekat je podeljen na frontend i backend:

```txt
frontend/  staticki UI fajlovi
backend/   Django + Django REST Framework API
```

Frontend fajlovi su u folderu:

```txt
frontend/
  index.html
  demo.html
  god-mode.html
  privacy.html
  terms.html
  register-basic.html
  register-pro.html
  register-business.html
  logo.png
  assets/
    audio/
    css/
    js/
```

Root `index.html` samo preusmerava na `frontend/index.html`.

Za lokalno otvaranje:

```txt
frontend/index.html
```

Za kasniji backend:

```txt
backend/
```

Za pravi rad preko backend-a koristi:

```txt
http://127.0.0.1:8000/
http://127.0.0.1:8000/admin/
```

Lokalno pokretanje backend-a:

```powershell
cd "C:\Users\taxi0\Documents\Codex\KALEYA PROJEKAT"
.\.venv\Scripts\Activate.ps1
copy .env.example .env
python backend\manage.py migrate
python backend\manage.py seed_plans
python backend\manage.py seed_demo
python backend\manage.py runserver
```

API provera:

```txt
http://127.0.0.1:8000/api/health/
http://127.0.0.1:8000/admin/
http://127.0.0.1:8000/django-admin/
http://127.0.0.1:8000/dashboard/
```

Lemon Squeezy payment provera:

```txt
http://127.0.0.1:8000/api/billing/payment/public-config/
http://127.0.0.1:8000/register-basic.html
```

Lemon Squeezy `.env` vrednosti koje se popunjavaju posle otvaranja naloga:

```env
PAYMENT_PROVIDER=lemonsqueezy
LEMONSQUEEZY_API_KEY=
LEMONSQUEEZY_STORE_ID=
LEMONSQUEEZY_WEBHOOK_SECRET=
LEMONSQUEEZY_TEST_MODE=True
LEMONSQUEEZY_VARIANT_BASIC=
LEMONSQUEEZY_VARIANT_PRO=
LEMONSQUEEZY_VARIANT_BUSINESS=
LEMONSQUEEZY_VARIANT_BUSINESS_PLUS=
LEMONSQUEEZY_VARIANT_BUSINESS_PRO_PLUS=
```

Webhook za aktivaciju pretplate posle deploy-a:

```powershell
python backend\manage.py create_lemonsqueezy_webhook --url https://aikaleya.com/api/billing/lemonsqueezy/webhook/
```

Ako komanda generise secret, isti secret upisati u `.env`:

```env
LEMONSQUEEZY_WEBHOOK_SECRET=PASTE_SECRET_HERE
```

Demo login:

```txt
Admin: bane@aikaleya.com / tvoja lokalna admin lozinka iz .env
Client test: administrator@test.com / test123
Employee test: employee / emp123
```

Deploy uputstvo za VPS:

```txt
deployment/README_DEPLOY.md
```
