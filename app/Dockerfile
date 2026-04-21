FROM python:3.11-slim

WORKDIR /workspace

# Dependências do sistema (psycopg2 precisa de libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY app/ ./app/

EXPOSE 8000

# Sem --reload: evita downloads repetidos do fastembed a cada mudança de arquivo.
# Para aplicar mudanças de código: docker compose restart api
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
