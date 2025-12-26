import streamlit as st
import pandas as pd
import time
# IMPORTAÇÃO DO BANCO
from database import carregar_dados, atualizar_tabela_completa

def show_perfil():
    st.title("👤 Meu Perfil")
    st.caption("Gerencie suas informações de acesso.")
    st.markdown("---")

    # Verifica login
    usuario_atual = st.session_state.get("usuario_atual")
    if not usuario_atual:
        st.error("Sessão expirada. Faça login novamente.")
        return

    # Carrega dados do Banco
    df = carregar_dados("usuarios")
    
    # Verifica se a tabela está vazia ou se não tem a coluna username
    if df.empty or 'username' not in df.columns:
        st.error("Erro ao carregar dados do usuário.")
        return

    # Filtra o usuário atual com segurança
    filtro_usuario = df['username'] == usuario_atual
    
    if not filtro_usuario.any():
        st.error("Erro crítico: Usuário não encontrado no banco de dados.")
        return

    # Pega os dados da primeira ocorrência encontrada
    dados_usuario = df[filtro_usuario].iloc[0]

    # Layout
    col_info, col_seguranca = st.columns([1, 1.5], gap="large")

    # --- COLUNA 1: DADOS ---
    with col_info:
        st.subheader("Dados da Conta")
        
        with st.container(border=True):
            nome_display = str(dados_usuario.get('name', 'Usuário'))
            iniciais = nome_display[:2].upper() if len(nome_display) >= 2 else "U"
            
            st.markdown(
                f"""
                <div style="
                    width: 80px; height: 80px; 
                    background-color: #262730; 
                    color: #4CAF50;
                    border-radius: 50%; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    font-size: 30px; 
                    font-weight: bold; 
                    border: 2px solid #4CAF50;
                    margin-bottom: 15px;
                ">
                    {iniciais}
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            st.text_input("Nome Completo", value=nome_display, disabled=True)
            st.text_input("Usuário (Login)", value=dados_usuario.get('username', ''), disabled=True)
            
            status = str(dados_usuario.get('active', 'True')).lower()
            if status in ['true', '1', 'yes']:
                st.success("✅ Conta Ativa")
            else:
                st.error("❌ Conta Inativa")

            st.markdown("---")
            st.link_button("💬 Falar com o nutri", "https://wa.me/5521966887924", use_container_width=True)

    # --- COLUNA 2: ALTERAÇÃO DE SENHA ---
    with col_seguranca:
        st.subheader("🔐 Segurança")
        
        with st.container(border=True):
            st.markdown("##### Alterar Senha")
            st.caption("Defina uma nova senha para acessar a plataforma.")
            
            with st.form("form_troca_senha"):
                senha_atual_input = st.text_input("Senha Atual", type="password")
                nova_senha = st.text_input("Nova Senha", type="password")
                confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
                
                btn_salvar = st.form_submit_button("🔄 Atualizar Senha", type="primary", use_container_width=True)

                if btn_salvar:
                    # Senha armazenada no Banco
                    senha_real = str(dados_usuario.get('password', '')).strip()
                    senha_digitada = str(senha_atual_input).strip()
                    
                    # 1. Validações
                    if not senha_atual_input or not nova_senha or not confirma_senha:
                        st.warning("Preencha todos os campos.")
                    
                    elif senha_digitada != senha_real:
                        st.error(f"A senha atual está incorreta.")
                    
                    elif nova_senha != confirma_senha:
                        st.error("A nova senha e a confirmação não batem.")
                        
                    else:
                        # 2. ATUALIZAÇÃO SEGURA NO BANCO
                        try:
                            # Localiza e atualiza no DataFrame original
                            df.loc[df['username'] == usuario_atual, 'password'] = str(nova_senha).strip()
                            
                            # Salva a tabela inteira atualizada no PostgreSQL
                            atualizar_tabela_completa(df, "usuarios")
                            
                            st.success("Senha alterada com sucesso! 🔒")
                            st.info("A página será recarregada em instantes...")
                            time.sleep(2)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco: {e}")

    st.markdown("---")
    col_logout, _ = st.columns([1, 4])
    with col_logout:
        if st.button("🚪 Sair da Conta", type="secondary", use_container_width=True):
            st.session_state["logado"] = False
            st.session_state["usuario_atual"] = None
            st.rerun()