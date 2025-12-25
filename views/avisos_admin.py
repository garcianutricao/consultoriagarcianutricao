import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

ARQUIVO_AVISOS = "data/avisos.csv"

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
                
                # Proteção contra o EmptyDataError
                if not os.path.exists(ARQUIVO_AVISOS) or os.path.getsize(ARQUIVO_AVISOS) == 0:
                    pd.DataFrame([novo_dado]).to_csv(ARQUIVO_AVISOS, index=False)
                else:
                    df = pd.read_csv(ARQUIVO_AVISOS)
                    df = pd.concat([df, pd.DataFrame([novo_dado])], ignore_index=True)
                    df.to_csv(ARQUIVO_AVISOS, index=False)
                
                st.success(f"Aviso publicado! Ele ficará ativo por {horas} hora(s).")
                st.balloons()

    if os.path.exists(ARQUIVO_AVISOS) and os.path.getsize(ARQUIVO_AVISOS) > 0:
        st.divider()
        if st.button("🗑️ Apagar todos os avisos ativos"):
            os.remove(ARQUIVO_AVISOS)
            st.rerun()