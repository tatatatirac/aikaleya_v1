# Kaleya AI sekretarica - produkciona arhitektura

Ovaj dokument pretvara dijagram "AI SEKRETARICA - sistem arhitektura" u konkretan plan za Kaleya web aplikaciju, backend, integracije i kasniju mobilnu aplikaciju.

## 1. Cilj sistema

Kaleya je AI sekretarica za firme koje primaju pozive, poruke i zahteve za zakazivanje. Sistem mora da:

- primi zahtev preko telefona, WhatsApp-a, Vibera, SMS-a, email-a ili društvenih mreža;
- razume nameru korisnika;
- proveri slobodne termine, usluge, radno vreme i pravila firme;
- zakaže, pomeri, otkaže ili proveri termin;
- odgovori glasom ili porukom;
- obavesti vlasnika, osoblje i krajnjeg korisnika;
- čuva istoriju, preferencije, audit log i podatke bezbedno.

## 2. Glavni slojevi

### Frontend web app

Web aplikacija za vlasnika firme i klijente:

- kontrolna tabla;
- kalendar;
- klijenti/krajnji korisnici;
- usluge i cene;
- zaposleni i radno vreme;
- AI podešavanja;
- integracije;
- notifikacije;
- billing/paketi;
- support.

### Backend API

Django i Django REST Framework su centralni izvor istine:

- autentifikacija i role;
- business tenant sistem;
- termini;
- klijenti;
- osoblje;
- usluge;
- AI agent;
- voice servisi;
- integracije;
- notifikacije;
- audit log;
- admin dashboard.

### AI core

AI core ne sme da bude direktno u frontendu. Frontend samo šalje zahtev backendu. Backend kontroliše:

- API ključeve;
- izbor modela po klijentu;
- istoriju razgovora;
- dozvoljene alate;
- proveru termina;
- generisanje odgovora;
- sigurnosne limite.

### Integracije

Svaki kanal ulaza i izlaza mora da se normalizuje u isti interni format:

- Telefon / VoIP / Cloud PBX;
- WhatsApp Business API;
- Viber Business API;
- SMS gateway;
- Email IMAP/SMTP;
- Google Calendar;
- Instagram/TikTok poruke kada provider dozvoli zvaničan API pristup.

### Mobilna aplikacija

Mobilna aplikacija ne treba da bude poseban sistem. Ona koristi isti backend API kao web app:

- isti login;
- isti kalendar;
- isti status Kaleye;
- iste notifikacije;
- isti podaci u realnom vremenu.

## 3. Backend moduli

Postojeći backend treba proširiti ovim aplikacijama:

### accounts

Korisnici, login, role i prava pristupa:

- super admin;
- vlasnik firme;
- zaposleni;
- support;
- krajnji korisnik ako kasnije treba korisnički portal.

### clients

Firme koje koriste Kaleyu:

- naziv firme;
- paket;
- domen;
- status;
- globalni ili posebni AI model;
- jezik;
- vremenska zona;
- radna podešavanja.

### staff_services

Zaposleni, usluge, cene i trajanje:

- zaposleni/frizer/doktor/serviser;
- usluga;
- cena;
- trajanje;
- pauze;
- radno vreme;
- neradni dani;
- pravila otkazivanja.

### appointments

Termini:

- zakazano;
- pomereno;
- otkazano;
- završeno;
- no-show;
- blokirano vreme;
- izvor zakazivanja;
- potvrda termina.

### communications

Jedinstveni inbox za sve kanale:

- pozivi;
- WhatsApp poruke;
- Viber poruke;
- SMS;
- email;
- Instagram/TikTok poruke;
- outbound odgovori.

### ai_agent

Mozak Kaleye:

- prepoznavanje namere;
- planiranje koraka;
- izbor alata;
- izvršavanje alata;
- generisanje odgovora;
- sigurnosna provera pre akcije.

### voice

Glasovni sloj:

- STT - govor u tekst;
- TTS - tekst u glas;
- ElevenLabs glas;
- voice ID po jeziku ili klijentu;
- snimci poziva ako je dozvoljeno;
- transkripti.

### integrations

Konekcije ka spoljnim servisima:

- Twilio/Vonage za telefon i SMS;
- Meta WhatsApp Business;
- Viber Business;
- Google Calendar;
- email SMTP/IMAP;
- webhooks.

### notifications

Automatizacija i obaveštenja:

- podsetnik dan ranije;
- podsetnik dva sata ranije;
- potvrda termina;
- promena termina;
- otkazivanje;
- queue status;
- support alarm;
- izveštaji vlasniku.

### billing

Paketi i plaćanje:

- Basic;
- Pro;
- Business;
- GOD MODE;
- trial 14 dana;
- status pretplate;
- ograničenja paketa.

### audit_log

Bezbednost i pregled:

- ko je promenio termin;
- koji AI alat je izvršen;
- kada je poslata poruka;
- kada je promenjen API ključ;
- greške integracija;
- login pokušaji.

## 4. Ključni tok sistema

Svaki kanal koristi isti tok:

1. Provider pošalje webhook ili backend primi zahtev.
2. Backend normalizuje događaj u `CommunicationEvent`.
3. Sistem identifikuje firmu i krajnjeg korisnika.
4. AI agent učitava memoriju, pravila firme, kalendar i prethodne razgovore.
5. AI agent prepoznaje nameru.
6. Planner bira akciju.
7. Tool layer izvršava proveru ili promenu u bazi.
8. Response layer pravi tekstualni odgovor.
9. Voice layer pravi glas ako je kanal telefonski.
10. Integration layer šalje odgovor nazad.
11. Audit log čuva šta se desilo.

## 5. Minimalni produkcioni MVP

Prva verzija koja može realno da se koristi treba da ima:

- login i role;
- admin/vlasnik dashboard;
- firme i paketi;
- zaposleni;
- usluge;
- radno vreme;
- kalendar;
- ručno zakazivanje;
- AI tekst agent za proveru i zakazivanje;
- ElevenLabs TTS servis;
- SMS/WhatsApp integracioni adapter;
- audit log;
- `.env` konfiguraciju;
- PostgreSQL;
- Redis queue;
- deploy spreman za VPS.

Telefon, Viber, Instagram/TikTok i napredni voice tok idu posle osnovnog stabilnog jezgra.

## 6. Podaci u bazi

Osnovne tabele:

- `BusinessClient`;
- `BusinessLocation`;
- `StaffMember`;
- `Service`;
- `WorkingHours`;
- `BlockedTime`;
- `Customer`;
- `Appointment`;
- `Conversation`;
- `Message`;
- `CallSession`;
- `AIIntent`;
- `AIToolRun`;
- `IntegrationConnection`;
- `NotificationJob`;
- `AuditLog`;
- `SubscriptionPlan`;
- `TenantApiCredential`.

## 7. API rute

Predložene produkcione rute:

- `/api/auth/login/`;
- `/api/auth/me/`;
- `/api/business/current/`;
- `/api/staff/`;
- `/api/services/`;
- `/api/calendar/`;
- `/api/appointments/`;
- `/api/customers/`;
- `/api/conversations/`;
- `/api/ai/handle-message/`;
- `/api/ai/check-availability/`;
- `/api/voice/tts/`;
- `/api/integrations/`;
- `/api/webhooks/twilio/`;
- `/api/webhooks/whatsapp/`;
- `/api/webhooks/viber/`;
- `/api/webhooks/email/`;
- `/api/notifications/`;
- `/api/audit-log/`.

## 8. AI alati

AI ne sme direktno da menja bazu bez backend validacije. Dozvoljeni alati:

- `find_customer`;
- `create_customer`;
- `check_availability`;
- `create_appointment`;
- `reschedule_appointment`;
- `cancel_appointment`;
- `block_time`;
- `send_confirmation`;
- `send_reminder`;
- `handoff_to_support`;
- `get_queue_status`;
- `create_audit_log`.

## 9. Integracije po prioritetu

### Prioritet 1

- Claude/OpenAI kompatibilni AI provider preko backend servisa;
- ElevenLabs TTS;
- email SMTP;
- SMS gateway;
- WhatsApp Business preko zvaničnog providera;
- Google Calendar sync.

### Prioritet 2

- telefon preko Twilio/Vonage/Cloud PBX;
- STT provider za pozive;
- Viber Business;
- real-time status preko WebSocket-a.

### Prioritet 3

- Instagram/TikTok DM ako zvanični API i nalog to dozvoljavaju;
- marketing automatizacije;
- napredni reporting;
- mobilna aplikacija.

## 10. Bezbednost

Produkcija mora imati:

- API ključeve samo u `.env` ili šifrovano u bazi;
- HTTPS;
- CSRF/CORS pravilno podešen;
- rate limit;
- role permissions;
- audit log;
- backup baze;
- enkripciju osetljivih podataka;
- odvojene dev/prod konfiguracije;
- zabranu direktnog pozivanja AI providera iz browsera.

## 11. Redosled izrade

### Faza 1 - stabilno jezgro

1. Srediti postojeći Django backend kao centralni API.
2. Dodati staff/services/work hours.
3. Ojačati appointments model.
4. Dodati communications inbox.
5. Dodati audit log.

### Faza 2 - AI agent

1. Napraviti `ai_agent` servis.
2. Dodati intent detection.
3. Dodati tool execution.
4. Dodati Claude/OpenAI provider adapter.
5. Dodati fallback na human support.

### Faza 3 - kanali

1. Email/SMS.
2. WhatsApp.
3. ElevenLabs TTS.
4. Telefonija.
5. Viber.

### Faza 4 - frontend kao pravi proizvod

1. Povezati dashboard na realne API-je.
2. Izbaciti demo podatke iz UI-ja.
3. Dodati realne forme za klijente, usluge, termine i integracije.
4. Dodati real-time statuse.

### Faza 5 - mobile app

1. Napraviti mobilni frontend nad istim API-jem.
2. Dodati push notifikacije.
3. Dodati mobile dashboard za vlasnika.
4. Dodati proveru termina i brze akcije.

## 12. Zaključak

Dijagram pokazuje da Kaleya nije samo landing page i admin panel, nego multi-channel AI operativni sistem za zakazivanje i komunikaciju. Zato pravi pristup treba da bude backend-first:

- baza i API prvo;
- zatim AI agent;
- zatim integracije;
- zatim web app UI;
- zatim mobile app.

Tako web i mobilna aplikacija rade sinhronizovano, jer obe koriste isti backend i istu bazu.
