FROM nginx:1.27-alpine
COPY index.html main.js scene.splat VIEWER-LICENSE.txt /usr/share/nginx/html/
COPY sparse/ /usr/share/nginx/html/sparse/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
