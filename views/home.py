import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, date

# --- ARQUIVOS DE DADOS ---
ARQUIVO_VIDEOS = "data/videos.csv"
ARQUIVO_CONCLUSAO = "data/conclusao_aulas.csv"
ARQUIVO_CHECKLIST = "data/checklist_diario.csv"
ARQUIVO_USUARIOS = "data/usuarios.csv" # Adicionado para ler configs do paciente
ARQUIVO_CHECKINS = "data/checkins.csv" # Adicionado para verificar histórico
ARQUIVO_AVISOS = "data/avisos.csv"

# --- CALLBACKS DE NAVEGAÇÃO ---
def ir_para_calculadora(): st.session_state["menu_opcao"] = "🧮 Calculadora"
def ir_para_biblioteca(): st.session_state["menu_opcao"] = "📚 Biblioteca"
def ir_para_checkin(): st.session_state["menu_opcao"] = "📝 Check-in" # Novo callback

# --- FUNÇÕES DE DADOS DE USUÁRIO (NOVAS) ---
def carregar_csv_seguro(caminho):
    if not os.path.exists(caminho): return pd.DataFrame()
    return pd.read_csv(caminho, dtype=str)

def get_dados_paciente(username):
    df = carregar_csv_seguro(ARQUIVO_USUARIOS)
    if df.empty: return None
    df['username'] = df['username'].astype(str).str.strip()
    user = df[df['username'] == str(username).strip()]
    if user.empty: return None
    return user.iloc[0].to_dict()

def ja_fez_checkin_recente(username):
    df = carregar_csv_seguro(ARQUIVO_CHECKINS)
    if df.empty: return False
    
    df['data_real'] = pd.to_datetime(df['data'], errors='coerce')
    df_user = df[df['username'] == username].dropna(subset=['data_real'])
    
    if df_user.empty: return False
    
    ultima_data = df_user['data_real'].max().date()
    hoje = datetime.now().date()
    dias_desde = (hoje - ultima_data).days
    
    return dias_desde < 4 # Se fez há menos de 4 dias, conta como feito

# --- FUNÇÕES DO CHECKLIST (MANTIDAS) ---
def carregar_checklist():
    if not os.path.exists(ARQUIVO_CHECKLIST):
        return pd.DataFrame(columns=["username", "data", "agua", "cardio", "treino", "dieta", "sono"])
    try:
        return pd.read_csv(ARQUIVO_CHECKLIST, dtype=str)
    except:
        return pd.DataFrame(columns=["username", "data", "agua", "cardio", "treino", "dieta", "sono"])

def salvar_tarefa(usuario, tarefa, feito):
    df = carregar_checklist()
    hoje = datetime.now().strftime("%Y-%m-%d")
    filtro = (df['username'] == usuario) & (df['data'] == hoje)
    
    if filtro.any():
        idx = df[filtro].index[0]
        df.at[idx, tarefa] = "True" if feito else "False"
    else:
        nova_linha = {"username": usuario, "data": hoje, "agua": "False", "cardio": "False", "treino": "False", "dieta": "False", "sono": "False"}
        nova_linha[tarefa] = "True" if feito else "False"
        df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
    
    df.to_csv(ARQUIVO_CHECKLIST, index=False)

def calcular_streak(usuario):
    df = carregar_checklist()
    if df.empty: return 0
    df_user = df[df['username'] == usuario].copy()
    if df_user.empty: return 0
    
    df_user['data'] = pd.to_datetime(df_user['data'])
    df_user = df_user.sort_values('data', ascending=False)
    colunas_tarefas = ["agua", "cardio", "treino", "dieta", "sono"]
    
    def fez_algo(row): return any(str(row[col]) == 'True' for col in colunas_tarefas)
    
    streak = 0
    hoje = datetime.now().date()
    ontem = hoje - timedelta(days=1)
    datas_ativas = set()
    
    for idx, row in df_user.iterrows():
        if fez_algo(row): datas_ativas.add(row['data'].date())
            
    current_check = hoje
    if current_check not in datas_ativas: current_check = ontem 
    
    while current_check in datas_ativas:
        streak += 1
        current_check -= timedelta(days=1)
        
    return streak

# --- FUNÇÕES AUXILIARES VÍDEO (MANTIDAS) ---
def verificar_se_video_concluido(usuario, modulo_video):
    if not os.path.exists(ARQUIVO_CONCLUSAO): return False
    try:
        df = pd.read_csv(ARQUIVO_CONCLUSAO)
        concluido = df[(df['username'] == usuario) & (df['modulo'] == modulo_video)]
        return not concluido.empty
    except: return False

def marcar_video_concluido(usuario, modulo_video):
    novo = {"username": usuario, "modulo": modulo_video, "data": str(datetime.now())}
    if os.path.exists(ARQUIVO_CONCLUSAO):
        try:
            df = pd.read_csv(ARQUIVO_CONCLUSAO)
            pd.concat([df, pd.DataFrame([novo])]).to_csv(ARQUIVO_CONCLUSAO, index=False)
        except:
            pd.DataFrame([novo]).to_csv(ARQUIVO_CONCLUSAO, index=False)
    else:
        pd.DataFrame([novo]).to_csv(ARQUIVO_CONCLUSAO, index=False)

# --- POP-UP DE CHECK-IN (NOVO) ---
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
    
    if os.path.exists(ARQUIVO_AVISOS) and os.path.getsize(ARQUIVO_AVISOS) > 0:
        try:
            df_avisos = pd.read_csv(ARQUIVO_AVISOS)
            agora = datetime.now()
        
            for _, row in df_avisos.iterrows():
                expira = datetime.strptime(row['expiracao'], "%Y-%m-%d %H:%M:%S")
                # Só mostra o aviso se estiver dentro do prazo configurado
                if agora < expira:
                    st.error(row['mensagem']) # Exibe a tarja vermelha com "🚨Aviso: ..."
        except Exception:
            pass # Ignora erros silenciosamente para não travar a home do paciente         

    # 1. VERIFICAÇÃO DE CHECK-IN (NOVA LÓGICA INSERIDA AQUI)
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
        
        # Verifica carência
        df_checks = carregar_csv_seguro(ARQUIVO_CHECKINS)
        fez_antes = False
        if not df_checks.empty:
            if not df_checks[df_checks['username'] == login_usuario].empty:
                fez_antes = True
        
        if not fez_antes: # Novato
            if frequencia == "Semanal" and dias_de_plano >= 7: carencia_ok = True
            elif frequencia == "Quinzenal" and dias_de_plano >= 15: carencia_ok = True
        else: # Veterano (já passou carência)
            carencia_ok = True

        # Se é o dia, passou da carência e não fez hoje
        if eh_dia and carencia_ok:
            if not ja_fez_checkin_recente(login_usuario):
                deve_cobrar = True

    # EXIBE O POP-UP SE NECESSÁRIO
    if deve_cobrar:
        if "popup_visto" not in st.session_state:
            popup_checkin()
            st.session_state["popup_visto"] = True
        
        # Aviso fixo também
        st.warning("📢 **Hoje é dia de Check-in!** Não esqueça de enviar seu relatório.")
        if st.button("👉 Ir para Check-in", type="primary"):
            st.session_state["menu_opcao"] = "📝 Check-in"
            st.rerun()
        st.markdown("---")

    # 2. CONTEÚDO ORIGINAL DA HOME (MANTIDO)
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

    # Vídeo e Dieta (Lado a Lado)
    ja_viu = verificar_se_video_concluido(login_usuario, "Boas Vindas")
    dados_video = None
    if not ja_viu:
        try:
            df_videos = pd.read_csv(ARQUIVO_VIDEOS)
            video_bv = df_videos[df_videos['modulo'] == 'Boas Vindas']
            if not video_bv.empty: dados_video = video_bv.iloc[0]
        except: pass

    if dados_video is not None:
        col_video, col_dieta = st.columns(2, gap="medium")
        with col_video:
            with st.container(border=True):
                st.subheader("👋 Comece por aqui!")
                st.caption(str(dados_video.get('descricao', 'Assista antes de começar.')))
                st.video(dados_video['link'])
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

    # Checklist Diário
    st.subheader("✅ Checklist do Dia")
    
    df_check = carregar_checklist()
    hoje_str = datetime.now().strftime("%Y-%m-%d")
    linha_hoje = df_check[(df_check['username'] == login_usuario) & (df_check['data'] == hoje_str)]
    
    status = {"agua": False, "cardio": False, "treino": False, "dieta": False, "sono": False}
    
    if not linha_hoje.empty:
        for k in status.keys():
            status[k] = str(linha_hoje.iloc[0][k]) == "True"

    c1, c2, c3 = st.columns(3)
    
    def criar_checkbox(label, chave_bd, col):
        with col:
            val = st.checkbox(label, value=status[chave_bd], key=f"chk_{chave_bd}")
            if val != status[chave_bd]:
                salvar_tarefa(login_usuario, chave_bd, val)
                st.rerun()

    criar_checkbox("💧 Xixi claro durante o dia", "agua", c1)
    criar_checkbox("🏃 Cardio", "cardio", c2)
    criar_checkbox("🥗 Dieta 100%", "dieta", c3)
    criar_checkbox("🏋️ Treino", "treino", c2)
    criar_checkbox("📵 Sono", "sono", c3)

    total_feitos = sum(1 for v in status.values() if v)
    total_itens = 5
    progresso = total_feitos / total_itens
    
    st.progress(progresso, text=f"Você completou {total_feitos} de {total_itens} metas hoje!")
    
    if progresso == 1.0:
        st.success("🎉 Parabéns! Dia perfeito!")

    st.markdown("---")
    
    # Atalhos
    col_calc, col_ebook = st.columns(2)
    with col_calc:
        st.info("💡 **Dúvida no almoço?**")
        st.button("🧮 Abrir Calculadora de Trocas", on_click=ir_para_calculadora, use_container_width=True) 
    with col_ebook:
        st.success("📚 **Quer ler algo?**")
        st.button("📖 Ver Meus Ebooks", on_click=ir_para_biblioteca, use_container_width=True)