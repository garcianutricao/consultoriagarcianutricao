import streamlit as st
import pandas as pd
import os
from database import carregar_dados, salvar_novo_registro
# Importando todas as views do sistema (INCLUINDO FINANCEIRO)
from views import home, calculadora, biblioteca, perfil, admin, checkin, financeiro


if st.sidebar.button("🔧 Reparar Colunas do Banco"):
    from database import carregar_dados, atualizar_tabela_completa
    
    # 1. Carrega a tabela "estragada"
    df = carregar_dados("usuarios")
    
    # 2. Renomeia de volta para o inglês (o padrão do sistema)
    # Ajuste os nomes da esquerda conforme aparecem no seu print
    df = df.rename(columns={
        "Login": "username",
        "Cargo": "role",
        "Ativo?": "active",
        "WhatsApp": "telefone" # Se tiver mudado esse também
    })
    
    # 3. Grava a tabela corrigida por cima da errada
    atualizar_tabela_completa(df, "usuarios")
    st.success("✅ Banco reparado! As colunas voltaram para inglês.")
    st.rerun()

    
DATABASE_URL = st.secrets.get("DATABASE_URL")

# =======================================================
# CONFIGURAÇÃO INICIAL E LOGO
# =======================================================
def get_logo_path():
    """Busca a logo em várias extensões possíveis para evitar erros."""
    caminhos = [
        "assets/logo.png", 
        "assets/logo.PNG",
        "assets/logo.jpg", 
        "assets/logo.JPG",
        "assets/logo.jpeg", 
        "assets/logo.JPEG"
    ]
    for c in caminhos:
        if os.path.exists(c):
            return c
    return None

caminho_logo = get_logo_path()
icone = caminho_logo if caminho_logo else "🍎"

# Configuração da página deve ser a primeira chamada Streamlit
st.set_page_config(
    page_title="Consultoria Garcia Nutrição",
    page_icon=icone,
    layout="wide"
)

# =======================================================
# CSS VISUAL (ESTILO COMPLETO)
# =======================================================
def configurar_estilo_visual():
    st.markdown("""
        <style>
        /* 1. IMPORTAR FONTES */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

        /* 2. CONFIGURAÇÃO GERAL DA PÁGINA */
        .stApp {
            background-color: #050A14 !important;
        }
        
        /* 3. LIMPEZA TOTAL DE TEXTO (Remove contornos indesejados da calculadora) */
        * {
            text-shadow: none !important;
            -webkit-text-stroke: 0px !important;
        }

        /* 4. TIPOGRAFIA PADRÃO */
        html, body, p, h2, h3, h4, h5, h6, label, input, textarea, select, .stMarkdown, .stCaption, div {
            font-family: 'Inter', sans-serif !important;
            color: #E0E0E0 !important;
            letter-spacing: normal !important;
        }

        /* 5. TÍTULOS ESPECIAIS (H1 com Efeito Neon) */
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
        
        /* Cores para subtítulos */
        h2, h3 { 
            color: #FFFFFF !important; 
            font-weight: 700 !important; 
        }

        /* 6. CORREÇÃO DE ÍCONES DO MENU */
        /* Garante que as setas do menu não virem texto */
        button[kind="header"] span, [data-testid="stSidebarCollapseButton"] span, .material-icons, i {
            font-family: 'Material Icons' !important;
            font-style: normal !important;
            font-weight: normal !important;
            font-variant: normal !important;
            text-transform: none !important;
            line-height: 1 !important;
            -webkit-font-smoothing: antialiased; 
        }

        /* 7. ESTILIZAÇÃO DOS CAMPOS DE INPUT (Calculadora e Login) */
        label, .stTextInput label, .stSelectbox label, .stNumberInput label {
            color: #FFFFFF !important;
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            letter-spacing: 0px !important;
        }

        .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input, .stTextArea textarea {
            background-color: #0F172A !important;
            color: white !important;
            border: 1px solid #334155 !important;
            border-radius: 6px !important;
            box-shadow: none !important;
        }
        
        /* Foco nos inputs (Borda Azul) */
        .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
            border-color: #00D4FF !important;
        }

        /* 8. BOTÕES ESTILIZADOS */
        div.stButton > button {
            background-color: #007BFF !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 10px rgba(0, 123, 255, 0.3) !important;
            transition: all 0.3s ease !important;
        }
        
        div.stButton > button:hover {
            background-color: #00D4FF !important;
            box-shadow: 0 6px 20px rgba(0, 212, 255, 0.6) !important;
            transform: translateY(-2px);
        }

        /* Botão Secundário (Sair) */
        button[kind="secondary"] {
            background-color: transparent !important;
            border: 1px solid #FF4B4B !important;
            color: #FF4B4B !important;
            box-shadow: none !important;
        }

        /* 9. SIDEBAR (MENU LATERAL) */
        [data-testid="stSidebar"] {
            background-color: #02040A !important;
            border-right: 1px solid #1E293B;
        }
        
        /* 10. FORMULÁRIO INVISÍVEL (Para o Login funcionar com Enter) */
        [data-testid="stForm"] {
            border: none;
            padding: 0;
        }
        </style>
    """, unsafe_allow_html=True)

# Aplica o estilo visual
configurar_estilo_visual()

# =======================================================
# FUNÇÕES DE AUTENTICAÇÃO E DADOS
# =======================================================
def carregar_usuarios():
    """Carrega a tabela de usuários direto do PostgreSQL."""
    return carregar_dados("usuarios")

def login(u, s):
    """Verifica credenciais de login."""
    df = carregar_usuarios()
    if df.empty: return None
    
    u = str(u).strip()
    user = df[df['username'] == u]
    
    if not user.empty:
        dados = user.iloc[0]
        # Verifica senha
        if str(s).strip() == str(dados['password']):
            # Verifica se está ativo
            if str(dados.get('active','True')).lower() in ['true','1','yes']:
                return dados.to_dict()
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
        
        # Exibe Logo ou GN Gigante
        if caminho_logo: 
            st.image(caminho_logo, width=180)
        else: 
            st.markdown("""
                <div style="text-align: center; margin-bottom: 20px;">
                    <span style="
                        font-family: 'Montserrat', sans-serif;
                        font-weight: 900;
                        font-size: 8rem; 
                        background: linear-gradient(90deg, #FFFFFF, #00D4FF);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        filter: drop-shadow(0px 0px 15px rgba(0, 212, 255, 0.5));
                        line-height: 1;
                        -webkit-text-stroke: 0px !important;
                    ">
                        GN
                    </span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Consultoria Garcia Nutrição - Área de membros")
        
        # Formulário para permitir login com "Enter"
        with st.form("login_form"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            
            # Botão de submissão do formulário
            submitted = st.form_submit_button("ENTRAR", type="primary", use_container_width=True)
            
            if submitted:
                res = login(u, s)
                if res == "BLOQUEADO":
                    st.error("Sua conta está inativa. Contate o suporte.")
                elif isinstance(res, dict):
                    # Login com sucesso: Salva na sessão
                    st.session_state.update({
                        "logado": True,
                        "usuario_atual": res['username'],
                        "role": res['role'],
                        "nome": res['name']
                    })
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# =======================================================
# ÁREA LOGADA (SIDEBAR E ROTEAMENTO)
# =======================================================
else:
    with st.sidebar:
        # Logo no Menu
        if caminho_logo: 
            st.image(caminho_logo, width=130)
        else: 
            st.markdown("""
                <div style="margin-bottom: 20px;">
                    <span style="
                        font-size: 4rem; 
                        font-weight: 900; 
                        font-family: 'Montserrat', sans-serif; 
                        color: #00D4FF; 
                        text-shadow: 0px 0px 15px rgba(0, 212, 255, 0.4); 
                        line-height: 1;
                    ">
                        GN
                    </span>
                </div>
            """, unsafe_allow_html=True)
            st.sidebar.markdown("<div style='text-align: left; color: #CCCCCC; font-size: 15px; margin-top: -15px; margin-bottom: 20px; padding-left: 5px;'>""Consultoria Garcia Nutrição""</div>", unsafe_allow_html=True)
        st.write(f"Olá, **{st.session_state['nome']}**!")
        st.write("")
        
        # --- MENU DE NAVEGAÇÃO ---
        # A chave 'menu_opcao' permite que o botão da Home altere a página automaticamente
        
        if st.session_state["role"] == "admin":
            st.caption("PAINEL GESTOR")
            if "menu_opcao" not in st.session_state: 
                st.session_state["menu_opcao"] = "Painel Admin"
                
            menu = st.radio(
                "Menu", 
                ["Painel Admin", "💰 Financeiro", "Visualizar Check-in", "Monitorar beliscadas", "📢 Enviar Avisos"], 
                key="menu_opcao"
            )
        else:
            if "menu_opcao" not in st.session_state: 
                st.session_state["menu_opcao"] = "🏠 Início"
                
            menu = st.radio(
                "Menu", 
                ["🏠 Início", "📝 Check-in", "🍫 Beliscadas", "🧮 Calculadora", "📚 Biblioteca", "👤 Meu Perfil"], 
                key="menu_opcao"
            )

        st.markdown("---")
        if st.button("Sair", type="secondary"):
            st.session_state["logado"] = False
            # Limpa estado do menu ao sair
            if "menu_opcao" in st.session_state: del st.session_state["menu_opcao"]
            st.rerun()

    # --- ROTEAMENTO DAS PÁGINAS ---
    # Admin
    if st.session_state["role"] == "admin":
        if menu == "Painel Admin":
            admin.show_admin()
        elif menu == "💰 Financeiro":
            financeiro.show_financeiro()
        elif menu == "Visualizar Check-in":
            checkin.show_checkin()
        elif menu == "Monitorar beliscadas":
            import views.monitoramento as monitoramento
            monitoramento.show_monitoramento()
        elif menu == "📢 Enviar Avisos":
            from views.avisos_admin import show_enviar_avisos
            show_enviar_avisos()
    
    # Paciente
    elif menu == "🏠 Início":
        home.show_home()
    elif menu == "📝 Check-in":
        checkin.show_checkin()
    elif menu == "🍫 Beliscadas":
        import views.monitoramento as monitoramento
        monitoramento.show_monitoramento()
    elif "Calculadora" in menu:
        calculadora.show_calculadora()
    elif "Biblioteca" in menu:
        biblioteca.show_biblioteca()
    elif "Perfil" in menu:
        perfil.show_perfil()