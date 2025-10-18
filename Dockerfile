# Portfolio News Scraper - Dockerfile
# Imagen base optimizada con Python 3.9
FROM python:3.9-slim

# Metadata
LABEL maintainer="Miguel Murillo <mikia@example.com>"
LABEL description="Portfolio News Scraper - Financial news aggregator for trading portfolios"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema (necesarias para algunas librerías Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY *.py .

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Healthcheck (opcional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from supabase_client import get_supabase_client; get_supabase_client()" || exit 1

# Comando por defecto
CMD ["python", "orchestrator.py"]
