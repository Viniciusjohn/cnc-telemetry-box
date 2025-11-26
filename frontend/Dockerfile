FROM node:20-alpine AS build

WORKDIR /app

# Instala dependencias do frontend
COPY package*.json ./
RUN npm install

# Copia codigo fonte e builda para producao
COPY . .
RUN npm run build

FROM nginx:alpine AS runtime

# Copia artefatos buildados para o nginx
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
