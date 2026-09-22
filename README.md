# Синтропия

ИИ-агент ведения проектов: эпик → таблицы требований → уроки. Люди работают там, где привыкли (чат с ИИ, Битрикс24, Telegram, Mattermost, git), агент обходит точки проекта и собирает структуру в базе знаний.

## Контур

- `deploy/docker-compose.yml` — Open WebUI (чат), LiteLLM (шлюз к моделям), Wiki.js + Postgres (база знаний). Всё на loopback, наружу отдаёт nginx.
- `deploy/nginx/` — сайты `syntropy.test-rms.ru` (чат) и `wiki.syntropy.test-rms.ru` (вики).
- `deploy/server-setup.sh main|wiki` — развёртывание, SSL через certbot. Секреты в `.env` на сервере, в репозиторий не попадают.

Сервер: `/var/www/syntropy.test-rms.ru`. Документация проекта — в папке `wiki/` (публикуется в базу знаний скриптом).
