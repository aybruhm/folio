FROM dhi.io/node:25-debian13-sfw-dev

# Set working directory
WORKDIR /app

# Install dependencies (using legacy-peer-deps for Svelte version compatibility)
COPY web/package*.json ./
RUN npm ci --legacy-peer-deps

# Copy application code
COPY web/ .

# Expose Vite dev server port
LABEL org.opencontainers.image.source=https://github.com/aybruhm/folio
LABEL org.opencontainers.image.description="Folio Web — self-hosted investment portfolio tracking frontend built with SvelteKit"
LABEL org.opencontainers.image.licenses=GPL-2.0

EXPOSE 3000
