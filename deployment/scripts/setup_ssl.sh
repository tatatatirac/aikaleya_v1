#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Kaleya SSL setup — run as root on the Hetzner VPS:
#    sudo bash /var/www/aikaleya/deployment/scripts/setup_ssl.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="aikaleya.com"
WWW_DOMAIN="www.aikaleya.com"
EMAIL="hello@aikaleya.com"
NGINX_CONF="/etc/nginx/sites-available/aikaleya.conf"
NGINX_LINK="/etc/nginx/sites-enabled/aikaleya.conf"

echo ""
echo "== 1/5  Installing certbot =="
apt-get update -qq
apt-get install -y certbot python3-certbot-nginx

echo ""
echo "== 2/5  Copying HTTP-only nginx config =="
cp /var/www/aikaleya/deployment/nginx/aikaleya.conf "$NGINX_CONF"
ln -sf "$NGINX_CONF" "$NGINX_LINK"

# Remove default site if it exists (can conflict)
rm -f /etc/nginx/sites-enabled/default

echo ""
echo "== 3/5  Testing and reloading nginx =="
nginx -t
systemctl reload nginx

echo ""
echo "== 4/5  Obtaining SSL certificate (certbot will edit nginx config) =="
certbot --nginx \
    -d "$DOMAIN" \
    -d "$WWW_DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --redirect

echo ""
echo "== 5/5  Verifying auto-renewal =="
certbot renew --dry-run

echo ""
echo "====================================="
echo "  SSL is LIVE!"
echo "  https://$DOMAIN"
echo "  https://$WWW_DOMAIN"
echo "  Auto-renewal: active"
echo "====================================="
