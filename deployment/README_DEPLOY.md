# Kaleya VPS deployment

Ovo je produkcioni deploy plan za Ubuntu VPS.

## 1. Folder na serveru

```bash
sudo mkdir -p /var/www/aikaleya
sudo chown -R $USER:www-data /var/www/aikaleya
cd /var/www/aikaleya
```

Kod možeš ubaciti preko `git clone`, `git pull`, SFTP upload-a ili ZIP upload-a.

## 2. Sistemski paketi

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib redis-server nginx
```

## 3. PostgreSQL baza

```bash
sudo -u postgres psql
```

U PostgreSQL konzoli:

```sql
CREATE DATABASE kaleya_db;
CREATE USER kaleya_user WITH PASSWORD 'CHANGE_PASSWORD';
ALTER ROLE kaleya_user SET client_encoding TO 'utf8';
ALTER ROLE kaleya_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE kaleya_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE kaleya_db TO kaleya_user;
\q
```

## 4. `.env`

```bash
cp .env.production.example .env
nano .env
```

Obavezno promeni:

```txt
DJANGO_SECRET_KEY
DATABASE_URL
ANTHROPIC_API_KEY
ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID
DJANGO_ALLOWED_HOSTS
DJANGO_CSRF_TRUSTED_ORIGINS
CORS_ALLOWED_ORIGINS
EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD
DATA_BACKUP_DIR
```

Ne koristi `seed_demo` na produkciji.

## 5. Python okruženje

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Baza i static fajlovi

```bash
python backend/manage.py check --deploy
python backend/manage.py migrate
python backend/manage.py production_check
python backend/manage.py collectstatic --noinput
python backend/manage.py createsuperuser
```

## 7. Systemd servis

```bash
sudo cp deployment/systemd/kaleya.service /etc/systemd/system/kaleya.service
sudo systemctl daemon-reload
sudo systemctl enable kaleya
sudo systemctl start kaleya
sudo systemctl status kaleya
```

## 8. Nginx

```bash
sudo cp deployment/nginx/aikaleya.conf /etc/nginx/sites-available/aikaleya.conf
sudo ln -s /etc/nginx/sites-available/aikaleya.conf /etc/nginx/sites-enabled/aikaleya.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 9. SSL

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d aikaleya.com -d www.aikaleya.com
```

## 10. Provera

```txt
https://aikaleya.com/
https://aikaleya.com/admin/
https://aikaleya.com/api/health/
```

`/admin/` je Kaleya radni dashboard. Tehnički Django admin je na `/django-admin/`.

## 11. Backup baze

### pg_dump (preporučeno za produkciju)

Zahteva `postgresql-client` na serveru:

```bash
apt-get install -y postgresql-client
```

Ručni pg_dump:

```bash
cd /var/www/aikaleya && .venv/bin/python backend/manage.py pg_dump_backup
```

Restore iz dump fajla:

```bash
pg_restore --clean --if-exists -h localhost -U <db_user> -d <db_name> /var/www/aikaleya/backups/kaleya-pgdump-YYYYMMDD-HHMMSS.dump
```

Cron za svaku noć u 03:15 (`crontab -e`):

```bash
15 3 * * * cd /var/www/aikaleya && .venv/bin/python backend/manage.py pg_dump_backup >> /var/log/kaleya-backup.log 2>&1
```

### JSON backup (fallback)

```bash
cd /var/www/aikaleya && .venv/bin/python backend/manage.py backup_data
```

**Restore test obavezan pre launch-a** — verifikuj da pg_restore vraća bazu u ispravno stanje na staging-u.
