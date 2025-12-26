import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ===================================================
# 1. CONFIGURAÇÃO DA CONEXÃO
# ===================================================

# Pega o link secreto lá do .streamlit/secrets.toml (Local) ou da Nuvem
DATABASE_URL = st.secrets.get("DATABASE_URL")

# Correção necessária para o SQLAlchemy (O Railway usa 'postgres://' mas o Python quer 'postgresql://')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Cria o motor de conexão
engine = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        st.error(f"Erro ao conectar no banco de dados: {e}")

# ===================================================
# 2. FUNÇÕES DE LEITURA E ESCRITA
# ===================================================

def carregar_dados(tabela):
    """
    Lê uma tabela inteira do banco de dados e retorna como DataFrame.
    Se a tabela não existir (primeiro uso), retorna um DataFrame vazio.
    """
    if engine is None: 
        return pd.DataFrame()
    
    try:
        # Abre uma conexão rápida apenas para verificar se a tabela existe
        with engine.connect() as conn:
            # Comando específico do PostgreSQL para checar existência de tabela
            verificacao = text(f"SELECT to_regclass('public.{tabela}')")
            if conn.execute(verificacao).scalar() is None:
                return pd.DataFrame() # Tabela não existe, retorna vazio
            
        # Se existe, lê tudo
        return pd.read_sql_table(tabela, engine)
    
    except Exception as e:
        # Se der erro (ex: conexão caiu), retorna vazio para não travar o site
        print(f"Erro silencioso ao ler '{tabela}': {e}") # Log no terminal
        return pd.DataFrame()

def salvar_novo_registro(dados, tabela):
    """
    Recebe um dicionário (ex: {'nome': 'Joao', 'idade': 25}) 
    e salva como uma nova linha na tabela especificada.
    """
    if engine is None: 
        st.error("Banco de dados não conectado. Verifique os Secrets.")
        return False
        
    try:
        # Transforma o dicionário em uma linha de tabela (DataFrame)
        df_novo = pd.DataFrame([dados])
        
        # 'append': Adiciona ao final sem apagar o que já existe
        df_novo.to_sql(tabela, engine, if_exists='append', index=False)
        return True
    
    except Exception as e:
        st.error(f"Erro ao salvar registro: {e}")
        return False

def atualizar_tabela_completa(df, tabela):
    """
    ⚠️ PERIGO: Substitui a tabela inteira do banco pelo DataFrame fornecido.
    Usado quando editamos/excluímos usuários ou limpamos avisos.
    """
    if engine is None: return
    
    try:
        # 'replace': Apaga a tabela antiga e cria uma nova com os dados atuais
        df.to_sql(tabela, engine, if_exists='replace', index=False)
    except Exception as e:
        st.error(f"Erro ao atualizar banco de dados: {e}")