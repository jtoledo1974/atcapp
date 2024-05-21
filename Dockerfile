FROM python:3.12-slim

# Install dependencies
RUN apt-get update && apt-get install -y git

# Clone the repository
RUN git clone https://github.com/jtoledo1974/cambios.git /app

# Set the working directory
WORKDIR /app

# Install Python dependencies
RUN pip install -e .
# Run the application
CMD ["python", "-m", "cambios.app"]
