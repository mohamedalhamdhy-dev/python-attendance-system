FROM nginx:1.27-alpine
COPY nginx/company.conf /etc/nginx/conf.d/default.conf
COPY company/index.html /usr/share/nginx/html/index.html
COPY admin/app.css admin/app.js admin/v2.css admin/saas.css admin/v4.css /usr/share/nginx/html/
COPY ui/shared/themes.css /usr/share/nginx/html/themes.css
COPY ui/shared/status.html ui/shared/status.js /usr/share/nginx/html/
