# Развёртывание контура «Синтропия»

Всё ставится одним скриптом `server-setup.sh` из этой папки. Нужен Ubuntu 22.04/24.04, пользователь с sudo, Docker и выход в интернет.

## 1. Подготовка сервера (один раз)

```bash
# отдельный диск под данные Docker (если есть, здесь /dev/vdb)
sudo mkfs.ext4 -L docker-data /dev/vdb
sudo mkdir -p /var/lib/docker
echo 'LABEL=docker-data /var/lib/docker ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
sudo mount /var/lib/docker

# Docker из официального репозитория
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER   # перелогиниться
```

## 2. Файлы и окружение

```bash
git clone https://github.com/Korvova/syntropy.git ~/syntropy   # или скопировать папку deploy/
cd ~/syntropy/deploy
bash server-setup.sh env      # создаёт .env с секретами
nano .env                     # CHAT_HOST, WIKI_HOST, MM_HOST, MAIL_DOMAIN, TLS, EMAIL, OPENAI_API_*
```

| Переменная | Что это |
|---|---|
| `CHAT_HOST` / `WIKI_HOST` / `MM_HOST` | DNS-имена чата, базы знаний, мессенджера (A-записи на этот сервер) |
| `MAIL_DOMAIN`, `SMTP_FROM_EMAIL` | домен и адрес отправителя писем входа |
| `TLS` | `letsencrypt` (нужны открытые 80/443 из интернета), `selfsigned`, `custom` (свои сертификаты в `certs/<host>.crt|.key`) |
| `OPENAI_API_BASE`, `OPENAI_API_KEY` | адрес и ключ шлюза к модели (LiteLLM вуза или внешний сервис) |

## 3. Запуск

```bash
bash server-setup.sh main         # чат Open WebUI + шлюз LiteLLM
bash server-setup.sh outline      # база знаний Outline (+ Postgres, Redis, Postfix)
bash server-setup.sh mattermost   # мессенджер Mattermost
bash server-setup.sh sites        # nginx + сертификаты для трёх имён
# или всё сразу:
bash server-setup.sh all
```

Проверка: `docker ps` — все контейнеры `healthy`; три адреса открываются по HTTPS.

## 4. После запуска

1. Открыть чат `https://$CHAT_HOST`, зарегистрировать первого пользователя — он администратор.
2. Открыть базу знаний `https://$WIKI_HOST`, войти по письму, создать API-ключ (Settings → API), записать в `.secrets/outline_token`.
3. Установить агента в чат: `python tools/webui_install.py` (нужны ключи чата и Outline в `.secrets/`).
4. Шаблоны и стандарт: `python wiki/templates.py`.
5. Бот в Mattermost: зарегистрировать первого пользователя (администратор), затем `bash tools/mm_bot_setup.sh` — создаёт бота «Синтропия» и кладёт токен в `.mm_bot_token`.
6. Ссылка «База знаний» в чате: `docker exec -i syntropy-webui python3 - < webui/set_banner.py` (предварительно заменить `__WIKI_HOST__`).

## 5. Обслуживание

```bash
docker compose pull && docker compose up -d                         # обновление образов
docker compose -f docker-compose.outline.yml logs -f outline         # журналы
docker exec syntropy-outline-db pg_dump -U outline outline > outline-$(date +%F).sql   # копия базы знаний
docker exec syntropy-mm-db pg_dump -U mmuser mattermost > mm-$(date +%F).sql          # копия мессенджера
```

Все данные — в docker volumes на `/var/lib/docker`; для полной копии достаточно этих дампов и папки volumes.

## Известные грабли

- Реестр `docker.getoutline.com` отдаёт 403 из Яндекс Облака — образ берётся с Docker Hub (`outlinewiki/outline`).
- Если 80/443 закрыты белым списком, Let's Encrypt не пройдёт — временно `TLS=selfsigned`, потом сменить и повторить `sites`.
- Русского интерфейса у Outline нет; Mattermost и чат — на русском.
