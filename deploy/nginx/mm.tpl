server {
    listen 80;
    listen [::]:80;
    server_name __HOST__;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name __HOST__;

    ssl_certificate __CERT__;
    ssl_certificate_key __KEY__;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 100m;

    # Mattermost: websocket для чата
    location ~ /api/v[0-9]+/(users/)?websocket$ {
        proxy_pass http://127.0.0.1:__PORT__;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Frame-Options SAMEORIGIN;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_buffers 256 16k;
        proxy_buffer_size 16k;
    }

    location / {
        proxy_pass http://127.0.0.1:__PORT__;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Frame-Options SAMEORIGIN;
        proxy_read_timeout 600s;
        proxy_buffers 256 16k;
        proxy_buffer_size 16k;
    }

    access_log /var/log/nginx/__HOST__.access.log;
    error_log /var/log/nginx/__HOST__.error.log;
}
