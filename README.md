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

Lokalno pokretanje backend-a:

```powershell
cd "C:\Users\taxi0\Documents\Codex\KALEYA PROJEKAT"
.\.venv\Scripts\Activate.ps1
copy .env.example .env
python backend\manage.py migrate
python backend\manage.py seed_demo
python backend\manage.py runserver
```

API provera:

```txt
http://127.0.0.1:8000/api/health/
http://127.0.0.1:8000/admin/
```

Demo login:

```txt
Admin: admin@aikaleya.com / admin12345
Client: klijent@test.com / test123
```
