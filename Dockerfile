FROM python:3.12-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    locales \
    openssh-client \
    nginx \
    && apt-get clean

# Set the locale
RUN sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen && locale-gen

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Install the application in editable mode
RUN pip install -e .

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the port for Nginx
EXPOSE 8080

# Run the entrypoint script
CMD ["/entrypoint.sh"]
