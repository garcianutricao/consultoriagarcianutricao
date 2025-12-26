import streamlit as st
import pandas as pd
import os
import altair as alt
from datetime import datetime
from database import carregar_dados, salvar_novo_registro

# --- CONFIGURAÇÃO ---
ARQUIVO_BELISCADAS = "data/beliscadas.csv"
ARQUIVO_USUARIOS = "data/usuarios.csv"

# --- FUNÇÕES AUXILIARES ---
def carregar_csv(caminho):
    if not os.path.exists(caminho): return pd.DataFrame()
    return pd.read_csv(caminho, dtype=str)

def salvar_csv_completo(df, caminho):
    """Salva o DataFrame inteiro (usado na revisão)"""
    df.to_csv(caminho, index=False)

def salvar_beliscada_unica(dados):
    """Versão ultra-robusta para gravar novos registros (Append)"""
    pasta = os.path.dirname(ARQUIVO_BELISCADAS)
    if not os.path.exists(pasta):
        os.makedirs(pasta)

    df_novo = pd.DataFrame([dados])

    if not os.path.exists(ARQUIVO_BELISCADAS):
        df_novo.to_csv(ARQUIVO_BELISCADAS, index=False, encoding='utf-8')
    else:
        df_novo.to_csv(ARQUIVO_BELISCADAS, mode='a', header=False, index=False, encoding='utf-8')

# --- VISÃO DO NUTRICIONISTA (ADMIN) ---
def exibir_visao_admin():
    """Lógica para o admin monitorar os 58 inscritos [cite: 2025-12-21]"""
    st.title("🕵️ Revisão de Beliscadas")
    
    df_users = carregar_csv(ARQUIVO_USUARIOS)
    if df_users.empty:
        st.warning("Nenhum usuário encontrado no sistema.")
        return

    dict_nomes = dict(zip(df_users['username'], df_users['name']))
    pacs_list = df_users[df_users['role'] == 'paciente']['username'].unique()
    
    sel_user = st.selectbox(
        "Selecione o paciente para analisar o comportamento:", 
        options=pacs_list,
        format_func=lambda x: dict_nomes.get(x, x)
    )

    if sel_user:
        if not os.path.exists(ARQUIVO_BELISCADAS):
            st.info("Nenhum registro de beliscada encontrado até o momento.")
            return

        # Carregamos todos os registros para poder atualizar o status
        df_all = carregar_dados("beliscadas")
        df_paciente = df_all[df_all['username'] == sel_user].copy()

        if df_paciente.empty:
            st.write(f"✅ O paciente **{dict_nomes.get(sel_user, sel_user)}** ainda não registrou beliscadas.")
        else:
            # --- LÓGICA DE REVISÃO ---
            # Verificamos se há registros pendentes APENAS deste paciente
            pendentes = df_paciente[df_paciente['status'] == 'Pendente']
            
            if not pendentes.empty:
                st.warning(f"🔔 Existem {len(pendentes)} novos registros para revisar.")
                if st.button(f"✅ Marcar registros de {dict_nomes.get(sel_user)} como Lidos", type="primary", use_container_width=True):
                    # Atualiza o status no DataFrame principal onde o usuário coincide e está pendente
                    df_all.loc[(df_all['username'] == sel_user) & (df_all['status'] == 'Pendente'), 'status'] = 'Revisado'
                    salvar_csv_completo(df_all, ARQUIVO_BELISCADAS)
                    st.success("Registros revisados com sucesso!")
                    st.rerun() # Recarrega para limpar os avisos
            else:
                st.success("✅ Todos os registros deste paciente já foram revisados por você.")

            st.divider()

            # --- TABELA ESTILIZADA ---
            st.dataframe(
                df_paciente,
                column_order=("data", "hora", "alimento", "gatilho", "sentimento", "plano_futuro"),
                column_config={
                    "data": st.column_config.DateColumn("📅 Data", format="DD/MM/YYYY"),
                    "hora": st.column_config.TimeColumn("⏰ Hora", format="HH:mm"),
                    "alimento": st.column_config.TextColumn("🍽️ Alimento", width="medium"),
                    "gatilho": st.column_config.TextColumn("🎯 Gatilho", width="small"),
                    "sentimento": st.column_config.TextColumn("🧠 Sentimento", width="medium"),
                    "plano_futuro": st.column_config.TextColumn("💡 Plano de Ação", width="large"),
                },
                use_container_width=True,
                hide_index=True
            )

# --- VISÃO DO PACIENTE (FORMULÁRIO) ---
def exibir_visao_paciente():
    st.title("🍫 Monitor de Beliscadas")
    st.info("Este é um espaço sem julgamentos. O objetivo é entender seus gatilhos.")

    usuario_atual = st.session_state.get("usuario_atual")
    
    with st.form("form_beliscada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", datetime.now())
        with col2:
            hora = st.time_input("Hora aproximada", datetime.now())

        alimento = st.text_input("O que você comeu?")
        motivo = st.text_area("Por que comeu? (Fome, vontade ou ambiente?)")
        gatilho = st.text_input("Qual foi o gatilho/motivo principal?")
        sentimento = st.text_input("Como se sentiu logo depois de comer?")
        plano_futuro = st.text_area("O que você acha que dá para fazer para isso não acontecer de novo?")

        if st.form_submit_button("Registrar Beliscada", type="primary", use_container_width=True):
            dados = {
                "username": usuario_atual,
                "data": str(data),
                "hora": str(hora),
                "alimento": alimento,
                "motivo": motivo,
                "gatilho": gatilho,
                "sentimento": sentimento,
                "plano_futuro": plano_futuro,
                "status": "Pendente" # Garante que o Admin receba o alerta
            }
            sucesso = salvar_novo_registro(dados, "beliscadas")

            if sucesso:
                st.success("✅ Registro salvo no Banco de Dados!")
                st.balloons()
                st.rerun()
    st.divider()
st.subheader("📜 Seu Histórico Recente")

# Carrega do Banco
df_historico = carregar_dados("beliscadas")

if not df_historico.empty:
    # Filtra só o usuário atual
    df_seu = df_historico[df_historico["username"] == st.session_state["usuario_atual"]]
    st.dataframe(df_seu, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum registro encontrado.")

# --- FUNÇÃO PRINCIPAL ---
def show_monitoramento():
    role = st.session_state.get("role")
    if role == "admin":
        exibir_visao_admin()
    else:
        exibir_visao_paciente()