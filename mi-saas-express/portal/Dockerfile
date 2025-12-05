# Dockerfile para el Portal Flask
FROM docker.io/python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Exponer puerto
EXPOSE 5000

# Ejecutar Flask
CMD ["python", "app.py"]
