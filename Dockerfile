FROM python:3.12-slim

# Install dependencies
RUN apt-get update && apt-get install -y git locales && apt-get clean

# Set the locale
RUN sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen && locale-gen

# Clone the repository
RUN git clone https://github.com/jtoledo1974/cambios.git /app

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install the application in editable mode
RUN pip install -e .

# Run the application
CMD ["python", "-m", "cambios.app"]
