#!/usr/bin/env bash
# На сервере: включить персональные токены, взять временный токен админа, создать бота, отозвать временный токен.
set -euo pipefail
cd /var/www/syntropy.test-rms.ru
MM="docker exec syntropy-mattermost mmctl --local"
$MM config set ServiceSettings.EnableUserAccessTokens true >/dev/null
OUT=$($MM token generate vladimir setup-tmp 2>&1)
T=$(echo "$OUT" | grep -oE '[a-z0-9]{26}' | tail -1)
python3 mm_bot_setup.py "$T" sintrop
ID=$($MM token list vladimir 2>&1 | grep -B2 setup-tmp | grep -oE '^[a-z0-9]{26}' | head -1 || true)
if [ -n "$ID" ]; then $MM token revoke "$ID" >/dev/null && echo "временный токен отозван"; else echo "не нашёл id временного токена:"; $MM token list vladimir; fi
rm -f mm_bot_setup.py mm_bot_setup.sh
ls -l .mm_bot_token | cut -c1-40
