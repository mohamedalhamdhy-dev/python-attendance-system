FROM nginx:1.27-alpine
COPY nginx/client.conf /etc/nginx/conf.d/default.conf
COPY client/index.html client/app.css client/app.js client/v2.css /usr/share/nginx/html/
COPY ui/shared/themes.css /usr/share/nginx/html/themes.css
COPY client/employee.html client/employee.js client/employee.css /usr/share/nginx/html/
COPY ui/shared/status.html ui/shared/status.js /usr/share/nginx/html/
