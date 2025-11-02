# --- Stage 1: Build the React App ---
# Use an official Node.js image as the builder
FROM node:18-alpine AS build-stage

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all source code
COPY . .

# Build the production-ready static files
RUN npm run build

# --- Stage 2: Serve the App with Nginx ---
# Use a lightweight Nginx image
FROM nginx:1.25-alpine

# Copy the built static files from the build-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# --- THIS IS THE NEW LINE ---
# Copy our custom Nginx config file
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80 (which Nginx listens on by default)
EXPOSE 80

# The default Nginx command will run, using our new config
CMD ["nginx", "-g", "daemon off;"]
