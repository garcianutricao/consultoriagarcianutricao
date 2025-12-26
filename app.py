import streamlit as st
import pandas as pd
import os
# Importa o cérebro do banco de dados
from database import carregar_dados, salvar_novo_registro

# --- 🚑 KIT DE EMERGÊNCIA (APAGUE DEPOIS DE VALIDAR O ACESSO) ---
with st.sidebar.expander("🆘 Resgate do Admin", expanded=False):
    st.write("Use isto apenas se travar fora do sistema.")
    
    # 1. Botão para ver o que tem no banco
    if st.checkbox("Ver Tabela de Usuários"):
        df_users = carregar_dados("usuarios")
        st.write("Colunas encontradas:", df_users.columns.tolist())
        st.dataframe(df_users)

    # 2. Botão para Recriar o Admin
    if st.button("Forçar Criação de Admin"):
        admin_resgate = {
            "username": "admin",
            "password": "123",
            "name": "Admin Resgate",
            "role": "admin",
            "active": "True",
            "data_inicio": "2025-12-25"
        }
        if salvar_novo_registro(admin_resgate, "usuarios"):
            st.success("Admin recriado! Login: admin / Senha: 123")
        else:
            st.error("Erro ao salvar.")
            
    # 3. Botão para Consertar Colunas (Caso estejam em Português)
    if st.button("Reparar Colunas (Login -> username)"):
        from database import atualizar_tabela_completa
        df = carregar_dados("usuarios")
        # Renomeia se encontrar os nomes errados
        df = df.rename(columns={"Login": "username", "Cargo": "role", "Ativo?": "active", "Senha": "password"})
        atualizar_tabela_completa(df, "usuarios")
        st.success("Colunas reparadas! Tente logar.")
# -------------------------------------------------------

# =======================================================
# CONFIGURAÇÃO INICIAL E LOGO
# =======================================================
def get_logo_path():
    """Busca a logo em várias extensões possíveis."""
    caminhos = [
        "assets/logo.png", "assets/logo.PNG",
        "assets/logo.jpg", "assets/logo.JPG",
        "assets/logo.jpeg", "assets/logo.JPEG"
    ]
    for c in caminhos:
        if os.path.exists(c): return c
    return None

caminho_logo = get_logo_path()
icone = caminho_logo if caminho_logo else "🍎"

st.set_page_config(
    page_title="Consultoria Garcia Nutrição",
    page_icon=icone,
    layout="wide"
)

# =======================================================
# IMPORTAÇÃO DAS VIEWS (PÁGINAS)
# =======================================================
# Importamos aqui para garantir que o set_page_config rode antes
from views import home, calculadora, biblioteca, perfil, admin, checkin, financeiro
import views.monitoramento as monitoramento
from views.avisos_admin import show_enviar_avisos

# =======================================================
# CSS VISUAL (ESTILO PROFISSIONAL)
# =======================================================
def configurar_estilo_visual():
    st.markdown("""
        <style>
        /* 1. IMPORTAR FONTES */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

        /* 2. CONFIGURAÇÃO GERAL DA PÁGINA */
        .stApp { background-color: #050A14 !important; }
        
        /* 3. TIPOGRAFIA */
        html, body, p, h2, h3, h4, h5, h6, label, input, textarea, select, .stMarkdown, .stCaption, div {
            font-family: 'Inter', sans-serif !important;
            color: #E0E0E0 !important;
        }

        /* 4. TÍTULOS ESPECIAIS (H1 com Efeito Neon) */
        h1 {
            font-family: 'Montserrat', sans-serif !important;
            background: linear-gradient(90deg, #FFFFFF, #00D4FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            text-shadow: 0px 0px 20px rgba(0, 212, 255, 0.3) !important;
            margin-bottom: 10px !important;
        }
        
        /* 5. INPUTS E CAMPOS */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input, .stTextArea textarea {
            background-color: #0F172A !important;
            color: white !important;
            border: 1px solid #334155 !important;
            border-radius: 6px !important;
        }
        
        /* 6. BOTÕES */
        div.stButton > button {
            background-color: #007BFF !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        div.stButton > button:hover {
            background-color: #00D4FF !important;
            transform: translateY(-2px);
        }
        button[kind="secondary"] {
            background-color: transparent !important;
            border: 1px solid #FF4B4B !important;
            color: #FF4B4B !important;
        }

        /* 7. MENU LATERAL */
        [data-testid="stSidebar"] {
            background-color: #02040A !important;
            border-right: 1px solid #1E293B;
        }
        
        /* 8. CORREÇÃO DE LOGIN COM ENTER */
        [data-testid="stForm"] { border: none; padding: 0; }
        </style>
    """, unsafe_allow_html=True)

configurar_estilo_visual()

# =======================================================
# FUNÇÕES DE AUTENTICAÇÃO
# =======================================================
def login(u, s):
    """Verifica credenciais no Banco de Dados."""
    # Carrega tabela
    df = carregar_dados("usuarios")
    if df.empty: return None
    
    # Tratamento de string para evitar erros de digitação
    u_login = str(u).strip().lower()
    s_login = str(s).strip()
    
    # Cria coluna auxiliar para busca
    if 'username' in df.columns:
        df['user_clean'] = df['username'].astype(str).str.strip().str.lower()
        user = df[df['user_clean'] == u_login]
        
        if not user.empty:
            dados = user.iloc[0]
            # Verifica senha (exata)
            if str(dados.get('password', '')).strip() == s_login:
                # Verifica status (aceita várias formas de True)
                status = str(dados.get('active', 'True')).lower()
                if status in ['true', '1', 'yes', 'on']:
                    return dados.to_dict()
                else:
                    return "BLOQUEADO"
    return None

# Inicializa variáveis de sessão
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = None
    st.session_state["role"] = None
    st.session_state["nome"] = None

# =======================================================
# TELA DE LOGIN
# =======================================================
if not st.session_state["logado"]:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("")
        st.write("")
        
        if caminho_logo: 
            st.image(caminho_logo, width=180)
        else: 
            st.markdown("<h1 style='text-align: center; font-size: 5rem;'>GN</h1>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Área de membros")
        
        with st.form("login_form"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("ENTRAR", type="primary", use_container_width=True)
            
            if submitted:
                res = login(u, s)
                if res == "BLOQUEADO":
                    st.error("Sua conta está inativa. Contate o suporte.")
                elif isinstance(res, dict):
                    st.session_state.update({
                        "logado": True,
                        "usuario_atual": res.get('username'),
                        "role": res.get('role'),
                        "nome": res.get('name')
                    })
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# =======================================================
# ÁREA LOGADA (SIDEBAR E ROTEAMENTO)
# =======================================================
else:
    with st.sidebar:
        if caminho_logo: 
            st.image(caminho_logo, width=130)
        else: 
            st.header("GN")
            
        st.write(f"Olá, **{st.session_state['nome']}**!")
        st.write("")
        
        # --- MENU DE NAVEGAÇÃO ---
        if st.session_state["role"] == "admin":
            st.caption("PAINEL GESTOR")
            if "menu_opcao" not in st.session_state: st.session_state["menu_opcao"] = "Painel Admin"
                
            menu = st.radio(
                "Menu", 
                ["Painel Admin", "💰 Financeiro", "Visualizar Check-in", "Monitorar beliscadas", "📢 Enviar Avisos"], 
                key="menu_opcao"
            )
        else:
            if "menu_opcao" not in st.session_state: st.session_state["menu_opcao"] = "🏠 Início"
                
            menu = st.radio(
                "Menu", 
                ["🏠 Início", "📝 Check-in", "🍫 Beliscadas", "🧮 Calculadora", "📚 Biblioteca", "👤 Meu Perfil"], 
                key="menu_opcao"
            )

        st.markdown("---")
        if st.button("Sair", type="secondary"):
            st.session_state["logado"] = False
            st.rerun()

    # --- ROTEAMENTO ---
    # ADMIN
    if st.session_state["role"] == "admin":
        if menu == "Painel Admin": admin.show_admin()
        elif menu == "💰 Financeiro": financeiro.show_financeiro()
        elif menu == "Visualizar Check-in": checkin.show_checkin()
        elif menu == "Monitorar beliscadas": monitoramento.show_monitoramento()
        elif menu == "📢 Enviar Avisos": show_enviar_avisos()
    
    # PACIENTE
    elif menu == "🏠 Início": home.show_home()
    elif menu == "📝 Check-in": checkin.show_checkin()
    elif menu == "🍫 Beliscadas": monitoramento.show_monitoramento()
    elif "Calculadora" in menu: calculadora.show_calculadora()
    elif "Biblioteca" in menu: biblioteca.show_biblioteca()
    elif "Perfil" in menu: perfil.show_perfil()