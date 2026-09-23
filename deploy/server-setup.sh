#!/usr/bin/env bash
# Разворачивание контура Синтропии на любом сервере. Запуск из папки deploy: bash server-setup.sh <шаг>
#   env        — создать .env (домены, секреты); домены потом править руками
#   main       — чат Open WebUI + шлюз LiteLLM
#   outline    — база знаний Outline (+ Postgres, Redis, Postfix)
#   mattermost — мессенджер Mattermost
#   sites      — nginx + сертификаты для трёх доменов (TLS=letsencrypt | selfsigned | custom)
#   all        — env + main + outline + mattermost + sites
# Домены и режим TLS берутся из .env: CHAT_HOST, WIKI_HOST, MM_HOST, MAIL_DOMAIN, TLS, EMAIL.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

make_env() {
  [ -f .env ] && { echo ".env уже есть"; return; }
  cat > .env <<EOF
# --- адреса контура (править под сервер) ---
CHAT_HOST=syntropy.test-rms.ru
WIKI_HOST=wiki.syntropy.test-rms.ru
MM_HOST=mm.syntropy.test-rms.ru
MAIL_DOMAIN=syntropy.test-rms.ru
# TLS: letsencrypt (нужны открытые 80/443 из интернета) | selfsigned | custom (сертификаты в certs/<host>.crt|.key)
TLS=letsencrypt
EMAIL=korvova888@gmail.com
# имя docker-сети основного compose: <имя папки без спецсимволов>_default
COMPOSE_NETWORK=$(basename "$ROOT" | tr -cd 'a-z0-9')_default
# --- секреты ---
LITELLM_MASTER_KEY=sk-$(openssl rand -hex 24)
WEBUI_SECRET_KEY=$(openssl rand -hex 32)
OUTLINE_DB_PASSWORD=$(openssl rand -hex 16)
OUTLINE_SECRET_KEY=$(openssl rand -hex 32)
OUTLINE_UTILS_SECRET=$(openssl rand -hex 32)
MM_DB_PASSWORD=$(openssl rand -hex 16)
# SMTP для писем входа: Postfix «только отправка» из compose Outline
SMTP_HOST=outline-mail
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=outline@syntropy.test-rms.ru
SMTP_SECURE=false
# ключ модели — вписать, когда выдан (LiteLLM вуза, агрегатор и т.п.)
OPENAI_API_KEY=
OPENAI_API_BASE=https://api.openai.com/v1
EOF
  chmod 600 .env
  echo ".env создан — проверь домены и SMTP_FROM_EMAIL"
}

load_env() { set -a; . ./.env; set +a; }

need_nginx() {
  command -v nginx >/dev/null || { $SUDO apt-get update -qq; $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx >/dev/null; }
  if [ "$TLS" = "letsencrypt" ]; then command -v certbot >/dev/null || $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot >/dev/null; fi
  # общие ssl-параметры, если certbot их не создал
  [ -f /etc/letsencrypt/options-ssl-nginx.conf ] || { $SUDO mkdir -p /etc/letsencrypt; printf 'ssl_session_cache shared:le_nginx_SSL:10m;\nssl_session_timeout 1440m;\nssl_protocols TLSv1.2 TLSv1.3;\nssl_prefer_server_ciphers off;\n' | $SUDO tee /etc/letsencrypt/options-ssl-nginx.conf >/dev/null; }
  [ -f /etc/letsencrypt/ssl-dhparams.pem ] || $SUDO openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048 2>/dev/null
}

site() {  # $1 = домен, $2 = шаблон nginx (chat|wiki|mm), $3 = локальный порт
  local d=$1 tpl=$2 port=$3 cert key
  $SUDO mkdir -p /var/www/certbot
  case "$TLS" in
    letsencrypt)
      cert=/etc/letsencrypt/live/$d/fullchain.pem; key=/etc/letsencrypt/live/$d/privkey.pem
      if [ ! -f "$cert" ]; then
        sed -e "s/__HOST__/$d/g" nginx/http-only.tpl | $SUDO tee /etc/nginx/sites-available/$d >/dev/null
        $SUDO ln -sf /etc/nginx/sites-available/$d /etc/nginx/sites-enabled/$d
        $SUDO nginx -t && $SUDO systemctl reload nginx
        $SUDO certbot certonly --webroot -w /var/www/certbot -d "$d" --non-interactive --agree-tos -m "$EMAIL"
      fi ;;
    selfsigned)
      $SUDO mkdir -p /etc/ssl/syntropy; cert=/etc/ssl/syntropy/$d.crt; key=/etc/ssl/syntropy/$d.key
      [ -f "$cert" ] || $SUDO openssl req -x509 -nodes -days 825 -newkey rsa:2048 -subj "/CN=$d" -addext "subjectAltName=DNS:$d" -keyout "$key" -out "$cert" 2>/dev/null ;;
    custom)
      $SUDO mkdir -p /etc/ssl/syntropy; cert=/etc/ssl/syntropy/$d.crt; key=/etc/ssl/syntropy/$d.key
      $SUDO cp "certs/$d.crt" "$cert"; $SUDO cp "certs/$d.key" "$key"; $SUDO chmod 600 "$key" ;;
    *) echo "TLS=$TLS не поддерживается"; exit 1 ;;
  esac
  sed -e "s/__HOST__/$d/g" -e "s#__CERT__#$cert#g" -e "s#__KEY__#$key#g" -e "s/__PORT__/$port/g" -e "s#__ROOT__#$ROOT#g" "nginx/$tpl.tpl" | $SUDO tee /etc/nginx/sites-available/$d >/dev/null
  $SUDO ln -sf /etc/nginx/sites-available/$d /etc/nginx/sites-enabled/$d
  $SUDO rm -f /etc/nginx/sites-enabled/default
  $SUDO nginx -t && $SUDO systemctl reload nginx
  echo "nginx ($TLS): https://$d готов"
}

dc() { docker compose "$@"; }

case "${1:-help}" in
  env) make_env ;;
  main)
    load_env; dc pull -q; dc up -d; dc ps ;;
  outline)
    load_env; dc -f docker-compose.outline.yml pull -q; dc -f docker-compose.outline.yml up -d; dc -f docker-compose.outline.yml ps ;;
  mattermost)
    load_env; dc -f docker-compose.mattermost.yml pull -q; dc -f docker-compose.mattermost.yml up -d; dc -f docker-compose.mattermost.yml ps ;;
  sites)
    load_env; need_nginx
    # ссылка «База знаний» в боковой панели чата — подставить адрес базы знаний
    sed "s#__WIKI_URL__#https://$WIKI_HOST#g" webui/sidebar-link.js > webui/sidebar-link.rendered.js
    site "$CHAT_HOST" chat 3100
    site "$WIKI_HOST" wiki 3400
    site "$MM_HOST" mm 3500 ;;
  all)
    bash "$0" env; bash "$0" main; bash "$0" outline; bash "$0" mattermost; bash "$0" sites ;;
  # старые имена шагов для своего сервера
  outline-site) load_env; need_nginx; site "$WIKI_HOST" wiki 3400 ;;
  mattermost-site) load_env; need_nginx; site "$MM_HOST" mm 3500 ;;
  *) sed -n '2,9p' "$0" ;;
esac
