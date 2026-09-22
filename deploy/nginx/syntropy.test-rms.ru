server {
    listen 80;
    listen [::]:80;
    server_name syntropy.test-rms.ru;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name syntropy.test-rms.ru;

    ssl_certificate /etc/letsencrypt/live/syntropy.test-rms.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/syntropy.test-rms.ru/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 100m;

    # BookStack (база знаний, вариант 2) в подпапке /kb
    location = /kb { return 301 /kb/; }
    location /kb/ {
        proxy_pass http://127.0.0.1:3300/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s;
    }

    # Open WebUI (чат Синтропии)
    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    access_log /var/log/nginx/syntropy.test-rms.ru.access.log;
    error_log /var/log/nginx/syntropy.test-rms.ru.error.log;
}
