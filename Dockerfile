FROM node:20-slim

# Install Python3, pip, Chromium, and system libraries
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    chromium \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PORT=5000

WORKDIR /app

# Copy dependency manifests & install packages
COPY package*.json ./
RUN npm install

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages || pip3 install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

EXPOSE 5000

CMD ["sh", "-c", "python3 app.py & node bridge.js"]
