import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Configuração da Conexão
DATABASE_URL = st.secrets.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")

# 2. Função Genérica para Carregar Dados
def carregar_dados(tabela):
    """Lê uma tabela inteira do banco de dados"""
    if engine is None: return pd.DataFrame()
    
    try:
        # Verifica se a tabela existe antes de tentar ler
        with engine.connect() as conn:
            # Essa query verifica tabelas no Postgres
            verificacao = text(f"SELECT to_regclass('public.{tabela}')")
            if conn.execute(verificacao).scalar() is None:
                return pd.DataFrame() # Retorna vazio se a tabela não existir ainda
            
        return pd.read_sql_table(tabela, engine)
    except Exception as e:
        st.error(f"Erro ao ler tabela '{tabela}': {e}")
        return pd.DataFrame()

# 3. Função Genérica para Salvar (Adicionar nova linha)
def salvar_novo_registro(dados, tabela):
    """Recebe um dicionário e salva como uma nova linha"""
    if engine is None: 
        st.error("Banco de dados não conectado.")
        return False
        
    try:
        df_novo = pd.DataFrame([dados])
        # 'if_exists="append"' cria a tabela se não existir ou adiciona se já existir
        df_novo.to_sql(tabela, engine, if_exists='append', index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# 4. Função para Atualizar Tabela Inteira (Para edições/exclusões)
def atualizar_tabela_completa(df, tabela):
    """Substitui a tabela inteira (usado no Admin para editar/excluir)"""
    if engine is None: return
    try:
        # 'replace' apaga a antiga e escreve a nova
        df.to_sql(tabela, engine, if_exists='replace', index=False)
    except Exception as e:
        st.error(f"Erro ao atualizar banco: {e}")