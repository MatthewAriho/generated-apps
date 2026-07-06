FROM nginx:alpine

COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nuke-sw.js /etc/nginx/nuke-sw.js
RUN chmod -R 755 /usr/share/nginx/html
