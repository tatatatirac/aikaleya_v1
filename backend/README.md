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
Admin: admin@aikaleya.com / admin123
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

## Radni dashboard

Za svakodnevni rad koristi:

```txt
http://127.0.0.1:8000/dashboard/
http://127.0.0.1:8000/admin/
```

`/admin/` i `/dashboard/` vode na lep Kaleya radni panel. Tehnički Django panel je pomeren na `/django-admin/`.

## `.env` za Claude Haiku 4.5 i ElevenLabs

Ako koristiš Claude, OpenAI polja mogu ostati prazna:

```txt
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=ovde_ide_tvoj_claude_api_key
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
OPENAI_API_KEY=
OPENAI_MODEL=
ELEVENLABS_API_KEY=ovde_ide_tvoj_elevenlabs_api_key
ELEVENLABS_VOICE_ID=lxYfHSkYm1EzQzGhdbfca
```

## Produkcija

Za VPS koristi PostgreSQL kroz `DATABASE_URL`, pravi `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, domen u `DJANGO_ALLOWED_HOSTS`, i API kljuceve samo u `.env`.
