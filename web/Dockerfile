FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY web/package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY web/ .

EXPOSE 3000

CMD ["npm", "run", "dev"]
