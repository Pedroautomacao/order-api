FROM python:3.12-slim

# Evita cache de bytecode
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema
RUN apt-get update \
    && apt-get install -y build-essential libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copia o projeto
COPY . .

# Expor porta
EXPOSE 8000

# Comando default (prod-like)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
