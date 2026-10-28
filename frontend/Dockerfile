# Stage 1: Base / Dependencies
FROM node:22-alpine AS base

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2: Development (Vite Dev Server with HMR)
FROM base AS dev

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# Stage 3: Build Production Assets
FROM base AS build

COPY . .
RUN npm run build

# Stage 4: Production Server (Nginx)
FROM nginx:stable-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

