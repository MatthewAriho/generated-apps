FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nuke-sw.js /etc/nginx/nuke-sw.js
COPY dist/ /usr/share/nginx/html/
RUN chmod -R 755 /usr/share/nginx/html
