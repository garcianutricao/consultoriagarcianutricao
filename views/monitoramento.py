import streamlit as st
import pandas as pd
from datetime import datetime
# IMPORTS DO BANCO DE DADOS
from database import carregar_dados, salvar_novo_registro, atualizar_tabela_completa

# --- VISÃO DO NUTRICIONISTA (ADMIN) ---
def exibir_visao_admin():
    """Lógica para o admin monitorar os 58 inscritos"""
    st.title("🕵️ Revisão de Beliscadas")
    
    # Carrega usuários do Banco
    df_users = carregar_dados("usuarios")
    
    if df_users.empty:
        st.warning("Nenhum usuário encontrado no sistema.")
        return

    # Dicionário para mostrar nomes bonitos no selectbox
    dict_nomes = {}
    if 'username' in df_users.columns and 'name' in df_users.columns:
        dict_nomes = dict(zip(df_users['username'], df_users['name']))
        
    # Filtra apenas pacientes
    pacs_list = []
    if 'role' in df_users.columns:
        pacs_list = df_users[df_users['role'] == 'paciente']['username'].unique()
    
    sel_user = st.selectbox(
        "Selecione o paciente para analisar o comportamento:", 
        options=pacs_list,
        format_func=lambda x: dict_nomes.get(x, x)
    )

    if sel_user:
        # Carregamos todos os registros do Banco
        df_all = carregar_dados("beliscadas")
        
        if df_all.empty:
            st.info("Nenhum registro de beliscada encontrado até o momento.")
            return

        # Filtra visualização
        df_paciente = df_all[df_all['username'] == sel_user].copy()

        if df_paciente.empty:
            st.write(f"✅ O paciente **{dict_nomes.get(sel_user, sel_user)}** ainda não registrou beliscadas.")
        else:
            # --- LÓGICA DE REVISÃO ---
            # Verificamos se há registros pendentes APENAS deste paciente
            pendentes = df_paciente[df_paciente['status'] == 'Pendente']
            
            if not pendentes.empty:
                st.warning(f"🔔 Existem {len(pendentes)} novos registros para revisar.")
                
                if st.button(f"✅ Marcar registros de {dict_nomes.get(sel_user, sel_user)} como Lidos", type="primary", use_container_width=True):
                    # Atualiza o status no DataFrame PRINCIPAL (df_all) e não na cópia
                    # Localiza as linhas desse usuário que estão pendentes e muda para Revisado
                    df_all.loc[(df_all['username'] == sel_user) & (df_all['status'] == 'Pendente'), 'status'] = 'Revisado'
                    
                    # Salva a tabela inteira atualizada no Postgres
                    atualizar_tabela_completa(df_all, "beliscadas")
                    
                    st.success("Registros revisados com sucesso!")
                    st.rerun() # Recarrega para limpar os avisos
            else:
                st.success("✅ Todos os registros deste paciente já foram revisados por você.")

            st.divider()

            # --- TABELA ESTILIZADA ---
            # Ordena por data (se possível)
            if 'data' in df_paciente.columns:
                df_paciente['data_dt'] = pd.to_datetime(df_paciente['data'], errors='coerce')
                df_paciente = df_paciente.sort_values('data_dt', ascending=False)

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
            # SALVA NO BANCO
            sucesso = salvar_novo_registro(dados, "beliscadas")

            if sucesso:
                st.success("✅ Registro salvo no Banco de Dados!")
                st.balloons()
                st.rerun()
    
    # --- HISTÓRICO (Agora dentro da função correta) ---
    st.divider()
    st.subheader("📜 Seu Histórico Recente")

    # Carrega do Banco
    df_historico = carregar_dados("beliscadas")

    if not df_historico.empty:
        # Filtra só o usuário atual
        if 'username' in df_historico.columns:
            df_seu = df_historico[df_historico["username"] == usuario_atual]
            
            # Ordena decrescente
            if 'data' in df_seu.columns:
                df_seu['data_dt'] = pd.to_datetime(df_seu['data'], errors='coerce')
                df_seu = df_seu.sort_values('data_dt', ascending=False)
            
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