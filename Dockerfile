FROM python:3.12-slim

WORKDIR /app

# Instala dependências do sistema operacional
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copia TODOS os arquivos do projeto (incluindo o pyproject.toml) para dentro do Docker
COPY . .

# O pip vai procurar o pyproject.toml na pasta atual (.) e instalar as dependências
RUN pip install --no-cache-dir .

EXPOSE 8550

CMD ["python", "main.py"]
