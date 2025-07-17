FROM docker:dind-rootless

# Switch to root to install packages
USER root

# Update package index and install Node.js and Python3
RUN apk update && \
    apk add --no-cache \
    nodejs \
    npm \
    python3 \
    py3-pip \
    && rm -rf /var/cache/apk/*

# Create symbolic link for python command
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Set working directory
WORKDIR /app

# Copy application files
COPY . ./

# Create and activate virtual environment, then install dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory
RUN mkdir -p /app/data

# Expose ports
EXPOSE 8776 8777 8778

# Create a simple startup script that runs both dockerd and your app
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'dockerd-entrypoint.sh &' >> /start.sh && \
    echo 'sleep 5' >> /start.sh && \
    echo 'exec python src/main.py' >> /start.sh && \
    chmod +x /start.sh

# Run both dockerd and your application
CMD ["/start.sh"]