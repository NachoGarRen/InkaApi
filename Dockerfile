# Usa una imagen base oficial de Python
FROM python:3.10-slim

# Instalar dependencias del sistema necesarias para OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Crear un usuario no root (requerido por Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Configurar el directorio de trabajo
WORKDIR $HOME/app

# Copiar el archivo de dependencias
COPY --chown=user requirements.txt requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Configurar el caché del modelo rembg
ENV U2NET_HOME=$HOME/.u2net

# Copiar el código de la aplicación
COPY --chown=user . $HOME/app

# Iniciar FastAPI en el puerto 7860 (requerido por Hugging Face)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
