#!/bin/sh
envsubst '${PORT_PDF_CHAT_FRONTEND} ${DOMAIN} ${PORT_PDF_CHAT_BACKEND}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'