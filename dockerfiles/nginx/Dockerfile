FROM node:17-alpine as builder
ARG node

COPY ./ui/package*.json ./
RUN npm install && mkdir -p /react-ui && mv ./node_modules /react-ui
WORKDIR /react-ui
COPY ./ui .
RUN npm run build:${node}

# production state
FROM nginx:1.21.6-alpine as prod
ARG node

COPY ./dockerfiles/nginx/${node}/nginx.conf /etc/nginx/nginx.conf
COPY ./dockerfiles/nginx/${node}/sites-enabled /etc/nginx/sites-enabled
COPY ./dockerfiles/nginx/${node}/ssl /etc/nginx/ssl
COPY --from=builder /react-ui/build /srv/web

EXPOSE 80 443

ENTRYPOINT ["nginx", "-g", "daemon off;"]