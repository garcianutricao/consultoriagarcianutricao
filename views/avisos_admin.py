import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
# Importamos as funções do Banco de Dados
from database import carregar_dados, salvar_novo_registro, atualizar_tabela_completa

def show_enviar_avisos():
    st.title("📢 Enviar Avisos aos Pacientes")
    st.info("Os avisos aparecerão no topo da Home dos pacientes ativos.")

    with st.form("form_aviso_novo", clear_on_submit=True):
        msg_input = st.text_area("Mensagem do Aviso:", placeholder="Ex: A consulta de grupo começa em 2 horas!")
        # Alterado de dias para horas
        horas = st.number_input("Duração do aviso (horas):", min_value=1, max_value=72, value=1)
        
        if st.form_submit_button("🚀 Publicar Agora", type="primary", use_container_width=True):
            if not msg_input:
                st.warning("Por favor, digite uma mensagem.")
            else:
                # Agora calcula a expiração somando HORAS
                expira = datetime.now() + timedelta(hours=horas)
                
                novo_dado = {
                    "mensagem": f"🚨Aviso: {msg_input}",
                    "expiracao": expira.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # SALVA NO BANCO DE DADOS (POSTGRESQL)
                if salvar_novo_registro(novo_dado, "avisos"):
                    st.success(f"Aviso publicado! Ele ficará ativo por {horas} hora(s).")
                    st.balloons()
                else:
                    st.error("Erro ao salvar aviso no banco.")

    # Carrega os avisos atuais para decidir se mostra o botão de apagar
    df_avisos = carregar_dados("avisos")
    
    if not df_avisos.empty:
        st.divider()
        st.subheader("Avisos Ativos no Momento")
        st.dataframe(df_avisos, use_container_width=True)
        
        if st.button("🗑️ Apagar todos os avisos ativos"):
            # Para "apagar" no banco, nós salvamos uma tabela vazia por cima
            df_limpo = pd.DataFrame(columns=["mensagem", "expiracao"])
            atualizar_tabela_completa(df_limpo, "avisos")
            
            st.success("Todos os avisos foram apagados do Banco de Dados.")
            st.rerun()