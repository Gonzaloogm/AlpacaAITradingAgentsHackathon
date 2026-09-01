# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app

# Accept VITE_API_URL as a build arg and set it as an env var
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Copy package.json and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Serve static files with Nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Use default nginx configuration
CMD ["nginx", "-g", "daemon off;"]
