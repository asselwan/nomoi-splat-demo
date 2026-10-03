FROM nginx:1.27-alpine
COPY index.html main.js scene.splat VIEWER-LICENSE.txt /usr/share/nginx/html/
EXPOSE 80
