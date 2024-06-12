FROM python:3.12-slim

# Install dependencies
RUN apt-get update && apt-get install -y git locales openssh-client && apt-get clean

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

# Set environment variables for SSH
ENV SSH_HOST=""
ENV SSH_PORT=22
ENV SSH_USER=root
ENV SSH_PRIVATE_KEY=""
ENV SSH_KEY_PATH=/root/.ssh/id_rsa

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the application
CMD ["/entrypoint.sh"]
