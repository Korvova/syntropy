#!/usr/bin/env bash
# Разворачивание контура на сервере. Запуск: bash server-setup.sh [main|wiki]
#   main — чат + шлюз + вики в Docker, nginx и SSL для syntropy.test-rms.ru
#   wiki — nginx и SSL для wiki.syntropy.test-rms.ru (когда появится DNS-запись)
set -euo pipefail
ROOT=/var/www/syntropy.test-rms.ru
EMAIL=korvova888@gmail.com
cd "$ROOT"

if [ ! -f .env ]; then
  cat > .env <<EOF
LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)
WEBUI_SECRET_KEY=$(openssl rand -hex 32)
WIKI_DB_PASSWORD=$(openssl rand -hex 16)
# ключ модели — вписать, когда выдан (агрегатор или Astra)
OPENAI_API_KEY=
OPENAI_API_BASE=https://api.openai.com/v1
EOF
  chmod 600 .env
  echo ".env создан"
fi

site() {  # $1 = домен
  local d=$1
  mkdir -p /var/www/certbot
  if [ ! -d /etc/letsencrypt/live/$d ]; then
    # сначала только http-блок, чтобы certbot прошёл проверку
    sed -n '1,/^}/p' nginx/$d > /etc/nginx/sites-available/$d
    ln -sf /etc/nginx/sites-available/$d /etc/nginx/sites-enabled/$d
    nginx -t && systemctl reload nginx
    certbot certonly --webroot -w /var/www/certbot -d $d --non-interactive --agree-tos -m $EMAIL
  fi
  cp nginx/$d /etc/nginx/sites-available/$d
  ln -sf /etc/nginx/sites-available/$d /etc/nginx/sites-enabled/$d
  nginx -t && systemctl reload nginx
  echo "nginx+ssl: $d готов"
}

case "${1:-main}" in
  main)
    docker compose pull -q
    docker compose up -d
    site syntropy.test-rms.ru
    docker compose ps
    ;;
  wiki)
    site wiki.syntropy.test-rms.ru
    ;;
esac
