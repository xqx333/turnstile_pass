# Use the official Ubuntu image as the base image
FROM --platform=linux/amd64 ubuntu:22.04

# Set environment variables to avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

# Install necessary packages for Xvfb and pyvirtualdisplay
RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-tk \
        python3-dev \
        wget \
        gnupg \
        ca-certificates \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libxss1 \
        libxtst6 \
        libnss3 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        x11-apps \
        fonts-liberation \
        libappindicator3-1 \
        libu2f-udev \
        libvulkan1 \
        libdrm2 \
        xdg-utils \
        xvfb \
        && rm -rf /var/lib/apt/lists/*

RUN wget -q "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" -O chrome.deb \
    && apt-get update \
    && apt-get install -y ./chrome.deb --no-install-recommends \
    && rm chrome.deb \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies including pyvirtualdisplay
RUN pip3 install --upgrade pip
RUN pip3 install pyvirtualdisplay

# Create ~/.Xauthority file
RUN mkdir -p /root && touch /root/.Xauthority

# Set up a working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt

# 暴露端口
EXPOSE 5000

# 使用 Gunicorn 作为生产环境的 WSGI 服务器，并配置多工作进程和线程
CMD Xvfb :99 -screen 0 1024x768x24 -nolisten tcp & exec gunicorn --bind 0.0.0.0:5000 --workers=1 --threads=1 turnstile_pass_api_pyautogui:app
