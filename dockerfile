# Usa uma versão leve do Python
FROM python:3.9-slim

# Define a pasta de trabalho
WORKDIR /app

# Instala dependências do sistema operacional necessárias para o Postgres
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos do seu computador para o servidor
COPY . .

# Instala as bibliotecas do Python
RUN pip3 install -r requirements.txt

# Expõe a porta do Streamlit
EXPOSE 8501

# Verifica se o Streamlit está rodando (Healthcheck)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# O comando que liga o site
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]