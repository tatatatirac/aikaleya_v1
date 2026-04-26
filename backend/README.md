# Kaleya Backend

Django backend za Kaleya platformu.

## Sta backend trenutno sadrzi

- Token login i role sistem: admin / client
- Klijentska podesavanja: jezik, glas, radno vreme, slotovi, kanali, Kaleya on/off
- Kalendar: kupci, termini, statusi, blokirani termini, dostupnost po danu
- AI command endpoint: check today, Kaleya on/off
- Alarm podesavanja po klijentu: notification, urgent, announcement
- Integracije: WhatsApp, Viber, Telegram, SMS, phone
- Billing: Basic, Pro, Business, GOD MODE
- Support ticket API za buducu human support integraciju

## Lokalno pokretanje

```powershell
cd "C:\Users\taxi0\Documents\Codex\KALEYA PROJEKAT"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python backend\manage.py migrate
python backend\manage.py seed_demo
python backend\manage.py runserver
```

## Demo nalozi

```txt
Admin: admin@aikaleya.com / admin12345
Client: klijent@test.com / test123
```

Ove lozinke su samo za lokalni development i ne smeju ostati u produkciji.

## Glavni API endpointi

```txt
POST /api/auth/login/
GET  /api/auth/me/
POST /api/auth/logout/

GET/PATCH /api/clients/business-clients/current/
GET       /api/appointments/appointments/availability/?date=YYYY-MM-DD
GET       /api/appointments/appointments/today-summary/
GET       /api/appointments/appointments/search/?q=ime
POST      /api/appointments/appointments/{id}/cancel/

POST /api/ai/command/
GET  /api/ai/alarm-settings/
GET  /api/integrations/connections/
GET  /api/billing/plans/
GET  /api/support/tickets/
```

## Produkcija

Za VPS koristi PostgreSQL kroz `DATABASE_URL`, pravi `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, domen u `DJANGO_ALLOWED_HOSTS`, i API kljuceve samo u `.env`.
