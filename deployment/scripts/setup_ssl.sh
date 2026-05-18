#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  Kaleya — SSL setup via Let's Encrypt (certbot) on Ubuntu/Debian
#  Run as root on the Hetzner VPS:
#    sudo bash /var/www/aikaleya/deployment/scripts/setup_ssl.sh
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="aikaleya.com"
WWW_DOMAIN="www.aikaleya.com"
EMAIL="hello@aikaleya.com"
NGINX_CONF="/etc/nginx/sites-available/aikaleya.conf"
NGINX_LINK="/etc/nginx/sites-enabled/aikaleya.conf"

echo "══ Step 1: Install certbot ══"
apt-get update -qq
apt-get install -y certbot python3-certbot-nginx

echo "══ Step 2: Ensure current nginx config is active ══"
cp /var/www/aikaleya/deployment/nginx/aikaleya.conf "$NGINX_CONF"
ln -sf "$NGINX_CONF" "$NGINX_LINK"
nginx -t && systemctl reload nginx

echo "══ Step 3: Obtain SSL certificate ══"
certbot --nginx \
    -d "$DOMAIN" \
    -d "$WWW_DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --redirect

echo "══ Step 4: Verify auto-renewal ══"
certbot renew --dry-run

echo ""
echo "══ DONE ══"
echo "SSL certificate installed for $DOMAIN and $WWW_DOMAIN"
echo "Auto-renewal is configured via certbot timer."
echo "Test: https://$DOMAIN"
echo ""
