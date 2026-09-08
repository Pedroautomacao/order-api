FROM python:3.12-slim

# Evita cache de bytecode
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Sem cache do pip: só aumentaria o tamanho da imagem final.
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Usuário sem privilégio: a aplicação não escreve nada no filesystem (o log vai
# para stdout e PYTHONDONTWRITEBYTECODE evita .pyc), então não precisa de root.
RUN useradd --create-home --uid 1000 appuser

# Copia o projeto
COPY --chown=appuser:appuser . .

USER appuser

# Expor porta
EXPOSE 8000

# Usa o /health que já existe na aplicação. Via stdlib para não instalar curl,
# que a imagem slim não traz — e o container não publica porta no host, então
# esta é a única forma de checar o serviço de fora (docker compose ps).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

# Comando default (prod-like)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
