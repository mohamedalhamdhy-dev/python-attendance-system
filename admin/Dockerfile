FROM nginx:1.27-alpine
COPY nginx/admin.conf /etc/nginx/conf.d/default.conf
COPY admin/index.html admin/app.css admin/app.js admin/v2.css admin/saas.css admin/v4.css /usr/share/nginx/html/
COPY ui/shared/themes.css /usr/share/nginx/html/themes.css
COPY ui/shared/status.html ui/shared/status.js /usr/share/nginx/html/
