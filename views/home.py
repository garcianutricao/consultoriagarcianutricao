import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
# Importamos as funções vitais do banco de dados
from database import carregar_dados, salvar_novo_registro, atualizar_tabela_completa

# --- CALLBACKS DE NAVEGAÇÃO ---
def ir_para_calculadora(): st.session_state["menu_opcao"] = "🧮 Calculadora"
def ir_para_biblioteca(): st.session_state["menu_opcao"] = "📚 Biblioteca"
def ir_para_checkin(): st.session_state["menu_opcao"] = "📝 Check-in"

# --- FUNÇÕES DE DADOS DE USUÁRIO (MIGRADAS PARA DB) ---

def get_dados_paciente(username):
    # Carrega tabela usuarios do banco
    df = carregar_dados("usuarios")
    if df.empty: return None
    
    # Procura o usuário (tratando minúsculas/espaços)
    username = str(username).strip().lower()
    
    # Cria coluna temporária pra busca segura (caso o banco tenha sujeira)
    if 'username' in df.columns:
        df['user_clean'] = df['username'].astype(str).str.strip().str.lower()
        user = df[df['user_clean'] == username]
        
        if user.empty: return None
        return user.iloc[0].to_dict()
    return None

def ja_fez_checkin_recente(username):
    # Carrega tabela checkins do banco
    df = carregar_dados("checkins")
    if df.empty: return False

    # Filtra pelo usuário
    if 'username' in df.columns:
        df_user = df[df['username'] == username].copy()
        if df_user.empty: return False

        # Converte data e vê a última
        if 'data' in df_user.columns:
            df_user['data'] = pd.to_datetime(df_user['data'], errors='coerce')
            ultima_data = df_user['data'].max().date()
            
            hoje = datetime.now().date()
            dias_desde = (hoje - ultima_data).days
            
            return dias_desde < 4 # Se fez há menos de 4 dias, retorna True
    return False

# --- FUNÇÕES DO CHECKLIST (AGORA NO BANCO) ---
def carregar_checklist():
    # Lê direto do Postgres
    df = carregar_dados("checklist")
    # Se vier vazio ou sem colunas, cria a estrutura padrão
    colunas_padrao = ["username", "data", "agua", "cardio", "treino", "dieta", "sono"]
    if df.empty:
        return pd.DataFrame(columns=colunas_padrao)
    return df

def salvar_tarefa(usuario, tarefa, feito):
    """Atualiza o checklist no banco de dados"""
    df = carregar_checklist()
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    # Garante que as colunas existem (caso seja a primeira vez)
    colunas_padrao = ["username", "data", "agua", "cardio", "treino", "dieta", "sono"]
    for col in colunas_padrao:
        if col not in df.columns:
            df[col] = "False"

    # Procura se já existe registro hoje
    filtro = (df['username'] == usuario) & (df['data'] == hoje)
    
    novo_valor = "True" if feito else "False"

    if filtro.any():
        # Se existe, atualiza a linha
        idx = df[filtro].index[0]
        df.at[idx, tarefa] = novo_valor
    else:
        # Se não existe, cria nova linha
        nova_linha = {
            "username": usuario, 
            "data": hoje, 
            "agua": "False", "cardio": "False", "treino": "False", "dieta": "False", "sono": "False"
        }
        nova_linha[tarefa] = novo_valor
        df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
    
    # Salva a tabela atualizada no banco
    atualizar_tabela_completa(df, "checklist")

def calcular_streak(usuario):
    df = carregar_checklist()
    if df.empty: return 0
    
    if 'username' not in df.columns: return 0
    df_user = df[df['username'] == usuario].copy()
    if df_user.empty: return 0
    
    if 'data' in df_user.columns:
        df_user['data'] = pd.to_datetime(df_user['data'])
        df_user = df_user.sort_values('data', ascending=False)
        
        colunas_tarefas = ["agua", "cardio", "treino", "dieta", "sono"]
        
        # Função auxiliar para verificar se fez pelo menos 1 coisa no dia
        def fez_algo(row): 
            return any(str(row.get(col, 'False')) == 'True' for col in colunas_tarefas)
        
        streak = 0
        hoje = datetime.now().date()
        ontem = hoje - timedelta(days=1)
        datas_ativas = set()
        
        for idx, row in df_user.iterrows():
            if fez_algo(row): datas_ativas.add(row['data'].date())
                
        current_check = hoje
        # Se não fez hoje ainda, checa a partir de ontem para não zerar o streak
        if current_check not in datas_ativas: current_check = ontem 
        
        while current_check in datas_ativas:
            streak += 1
            current_check -= timedelta(days=1)
            
        return streak
    return 0

# --- FUNÇÕES AUXILIARES VÍDEO (MIGRADAS) ---
def verificar_se_video_concluido(usuario, modulo_video):
    df = carregar_dados("conclusao_aulas") # Nome da tabela no banco
    if df.empty: return False
    
    if 'username' in df.columns and 'modulo' in df.columns:
        concluido = df[(df['username'] == usuario) & (df['modulo'] == modulo_video)]
        return not concluido.empty
    return False

def marcar_video_concluido(usuario, modulo_video):
    novo = {
        "username": usuario, 
        "modulo": modulo_video, 
        "data": str(datetime.now())
    }
    # Salva apenas o novo registro (mais eficiente que reescrever tudo)
    salvar_novo_registro(novo, "conclusao_aulas")

# --- POP-UP DE CHECK-IN ---
@st.dialog("🔔 Lembrete Importante")
def popup_checkin():
    st.markdown("### Dia de check-in!")
    st.write("Ajude o nutri a manter a qualidade do suporte enviando suas informações.")
    st.write("")
    
    if st.button("👉 Responder Agora", type="primary", use_container_width=True):
        st.session_state["menu_opcao"] = "📝 Check-in"
        st.rerun()

# ========================================================
# VIEW PRINCIPAL (HOME)
# ========================================================
def show_home():
    nome_usuario = st.session_state.get("nome", "Paciente")
    login_usuario = st.session_state.get("usuario_atual", "")
    
    # 1. AVISOS (Carrega do Banco)
    df_avisos = carregar_dados("avisos")
    if not df_avisos.empty:
        try:
            agora = datetime.now()
            # Garante que as colunas existem
            if 'expiracao' in df_avisos.columns and 'mensagem' in df_avisos.columns:
                for _, row in df_avisos.iterrows():
                    try:
                        expira = pd.to_datetime(row['expiracao'])
                        if agora < expira:
                            st.error(row['mensagem'])
                    except: pass
        except Exception:
            pass      

    # 2. LÓGICA DE COBRANÇA DE CHECK-IN
    info = get_dados_paciente(login_usuario)
    deve_cobrar = False
    
    if info:
        dia_agendado = str(info.get('dia_checkin', 'Segunda')).strip()
        frequencia = str(info.get('frequencia', 'Semanal')).strip()
        
        dias_semana = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
        hoje = datetime.now().date()
        hoje_nome = dias_semana[hoje.weekday()]
        
        data_str = str(info.get('data_inicio', date.today())).strip()
        try: data_inicio = datetime.strptime(data_str, "%Y-%m-%d").date()
        except: data_inicio = date.today()
        
        dias_de_plano = (hoje - data_inicio).days
        if dias_de_plano < 0: dias_de_plano = 0
        
        eh_dia = (hoje_nome == dia_agendado)
        carencia_ok = False
        
        # Verifica carência olhando no banco de checkins
        df_checks = carregar_dados("checkins")
        fez_antes = False
        if not df_checks.empty:
            if 'username' in df_checks.columns:
                if not df_checks[df_checks['username'] == login_usuario].empty:
                    fez_antes = True
        
        if not fez_antes: # Novato
            if frequencia == "Semanal" and dias_de_plano >= 7: carencia_ok = True
            elif frequencia == "Quinzenal" and dias_de_plano >= 15: carencia_ok = True
        else: # Veterano
            carencia_ok = True

        if eh_dia and carencia_ok:
            if not ja_fez_checkin_recente(login_usuario):
                deve_cobrar = True

    # EXIBE O POP-UP SE NECESSÁRIO
    if deve_cobrar:
        if "popup_visto" not in st.session_state:
            popup_checkin()
            st.session_state["popup_visto"] = True
        
        st.warning("📢 **Hoje é dia de Check-in!** Não esqueça de enviar seu relatório.")
        if st.button("👉 Ir para Check-in", type="primary"):
            st.session_state["menu_opcao"] = "📝 Check-in"
            st.rerun()
        st.markdown("---")

    # 3. CONTEÚDO DA HOME
    hora = datetime.now().hour
    saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 18 else "Boa noite"
    dias_foco = calcular_streak(login_usuario)
    
    col_texto, col_streak = st.columns([3, 1])
    with col_texto:
        st.title(f"{saudacao}, {nome_usuario}! 👋")
        st.caption("Vambora fi")
    with col_streak:
        st.metric("🔥 Foco", f"{dias_foco} dias", "+1" if dias_foco > 0 else "")

    st.markdown("---")

    # Vídeo e Dieta
    ja_viu = verificar_se_video_concluido(login_usuario, "Boas Vindas")
    dados_video = None
    
    # Tenta carregar vídeo do banco
    if not ja_viu:
        df_videos = carregar_dados("videos")
        if not df_videos.empty and 'modulo' in df_videos.columns:
            video_bv = df_videos[df_videos['modulo'] == 'Boas Vindas']
            if not video_bv.empty: dados_video = video_bv.iloc[0]

    if dados_video is not None:
        col_video, col_dieta = st.columns(2, gap="medium")
        with col_video:
            with st.container(border=True):
                st.subheader("👋 Comece por aqui!")
                st.caption(str(dados_video.get('descricao', 'Assista antes de começar.')))
                # Garante que tem link
                link_video = dados_video.get('link', '')
                if link_video:
                    st.video(link_video)
                if st.button("✅ Já assisti! (Ocultar)", type="primary", use_container_width=True):
                    marcar_video_concluido(login_usuario, "Boas Vindas")
                    st.rerun()
        with col_dieta:
            with st.container(border=True):
                st.subheader("🥗 Seu Plano")
                st.info("Cardápio, Evolução e Metas.")
                st.markdown("**Acesse a plataforma parceira:**")
                st.link_button("🔗 Acessar Minha Dieta", "https://app.dietitian.com.br/login?redirect_to=%2F", type="primary", use_container_width=True)
                st.caption("Verifique seu plano toda semana.")
    else:
        st.subheader("🥗 Seu Plano Alimentar")
        with st.container(border=True):
            col_icon, col_info, col_btn = st.columns([1, 4, 3])
            with col_icon: st.markdown("# 📊")
            with col_info:
                st.markdown("**Dieta, Evolução e Antropometria**")
                st.write("Acesse seu cardápio completo na plataforma parceira.")
            with col_btn:
                st.write("") 
                st.link_button("🔗 Acessar Minha Dieta", "https://app.dietitian.com.br/login?redirect_to=%2F", type="primary", use_container_width=True)

    st.markdown("---")
    # Atalhos
    col_calc, col_ebook = st.columns(2)
    with col_calc:
        st.info("💡 **Dúvida na refeição?**")
        st.button("🧮 Abrir Calculadora de Trocas", on_click=ir_para_calculadora, use_container_width=True) 
    with col_ebook:
        st.success("📚 **Quer ler algo?**")
        st.button("📖 Ver Meus Ebooks", on_click=ir_para_biblioteca, use_container_width=True)