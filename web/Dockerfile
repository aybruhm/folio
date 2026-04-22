FROM dhi.io/node:25-debian13-sfw-dev

# Set working directory
WORKDIR /app

# Install dependencies (using legacy-peer-deps for Svelte version compatibility)
COPY web/package*.json ./
RUN npm ci --legacy-peer-deps

# Copy application code
COPY web/ .

# Expose Vite dev server port
EXPOSE 3000
