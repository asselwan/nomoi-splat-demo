FROM nginx:1.27-alpine
COPY index.html main.js scene.splat trained.splat submitted-scenes.json VIEWER-LICENSE.txt /usr/share/nginx/html/
COPY submitted/ /usr/share/nginx/html/submitted/
COPY sparse/ /usr/share/nginx/html/sparse/
COPY spz/ /usr/share/nginx/html/spz/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
