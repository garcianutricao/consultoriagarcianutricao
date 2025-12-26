import streamlit as st
import pandas as pd
import os
import altair as alt
import requests
import time
from datetime import datetime, timedelta, date
from database import carregar_dados, salvar_novo_registro, atualizar_tabela_completa

# --- CONFIGURAÇÃO DE ARQUIVOS ---
ARQUIVO_USUARIOS = "data/usuarios.csv"
ARQUIVO_PARCEIROS = "data/parceiros.csv"
ARQUIVO_VIDEOS = "data/videos.csv"
ARQUIVO_CHECKINS = "data/checkins.csv"
ARQUIVO_PERGUNTAS = "data/perguntas_checkin.csv"
ARQUIVO_CONFIG_API = "data/config_api.csv"
ARQUIVO_BELISCADAS = "data/beliscadas.csv"
PASTA_EBOOKS = "assets/ebooks"

LINK_PLATAFORMA = "https://seu-app-nutricao.streamlit.app" 

def exibir_visao_admin():
    st.title("👨‍⚕️ Painel do Nutricionista")
    
    # Criamos abas para organizar
    tab1, tab2 = st.tabs(["📊 Monitoramento", "➕ Cadastrar Paciente"])
    
    with tab1:
        # ... AQUI FICA O TEU CÓDIGO ANTIGO DE GRÁFICOS/BELISCADAS ...
        st.write("Aqui vai a tua revisão de beliscadas atual.")

    with tab2:
        st.subheader("Cadastrar Novo Paciente")
        with st.form("form_cadastro_paciente", clear_on_submit=True):
            nome = st.text_input("Nome Completo")
            usuario = st.text_input("Usuário (Login/Email)")
            senha = st.text_input("Senha Provisória")
            
            if st.form_submit_button("🚀 Cadastrar Paciente"):
                novo_paciente = {
                    "username": usuario,
                    "password": senha,
                    "name": nome,
                    "role": "paciente", # Importante definir como paciente
                    "active": "True",
                    "data_inicio": "2026-01-01"
                }
                
                # Salva no PostgreSQL
                if salvar_novo_registro(novo_paciente, "usuarios"):
                    st.success(f"Paciente {nome} cadastrado com sucesso!")
                else:
                    st.error("Erro ao cadastrar. O login já pode existir.")

    st.divider()
    st.subheader("🕵️ Lista de Usuários no Banco")
    
    # Carrega e mostra a tabela crua do banco
    df_users = carregar_dados("usuarios")
    if not df_users.empty:
        # Mostra senha também por enquanto para debugares (depois tiramos!)
        st.dataframe(df_users, use_container_width=True)
    else:
        st.warning("Nenhum usuário encontrado.")
    st.divider()
    st.subheader("🕵️ Raio-X dos Usuários (Debug)")
    
    # Carregamos a tabela crua do banco
    df_debug = carregar_dados("usuarios")
    
    if not df_debug.empty:
        # Mostra a tabela na tela para você conferir
        st.dataframe(df_debug)
        
        st.warning("⚠️ Apague esta tabela depois que o sistema estiver estável!")
    else:
        st.error("A tabela de usuários está vazia ou não foi possível ler.")       

# --- FUNÇÕES ÚTEIS ---
def carregar_csv(caminho):
    if not os.path.exists(caminho): return pd.DataFrame()
    return pd.read_csv(caminho, dtype=str)

def salvar_csv(df, caminho):
    df.to_csv(caminho, index=False)

def garantir_pasta_ebooks():
    if not os.path.exists(PASTA_EBOOKS):
        os.makedirs(PASTA_EBOOKS)

def limpar_telefone(tel):
    if not tel: return ""
    return "".join(filter(str.isdigit, str(tel)))

def dias_desde_ultimo_checkin(username):
    df = carregar_csv(ARQUIVO_CHECKINS)
    if df.empty: return 999, "Nunca"
    
    df_user = df[df['username'] == username].copy()
    if df_user.empty: return 999, "Nunca"
    
    df_user['data_real'] = pd.to_datetime(df_user['data'], errors='coerce')
    df_user = df_user.dropna(subset=['data_real'])
    
    if df_user.empty: return 999, "Nunca"

    ultima_data = df_user['data_real'].max()
    delta = (datetime.now() - ultima_data).days
    return delta, ultima_data.strftime("%d/%m/%Y")

def inicializar_perguntas_padrao(forcar=False):
    """Cria o arquivo de perguntas com base no PDF enviado"""
    if not os.path.exists(ARQUIVO_PERGUNTAS) or forcar:
        dados = [
            # 0. Dados Iniciais
            {"id": "peso", "pergunta": "Peso Atual (kg)", "tipo": "numero", "opcoes": "", "categoria": "0. Dados Iniciais"},
            
            # 1. Comportamento
            {"id": "aderencia", "pergunta": "3. Aderência ao plano alimentar:", "tipo": "radio", "opcoes": "Estou conseguindo seguir tudo tranquilamente|Consigo seguir tudo, mas às vezes passo por alguma dificuldade|Não consigo realizar tudo|Não estou conseguindo realizar nada", "categoria": "1. Comportamento"},
            {"id": "aderencia_expl", "pergunta": "Explicação (se houver dificuldade):", "tipo": "texto_longo", "opcoes": "", "categoria": "1. Comportamento"},
            
            {"id": "dedicacao", "pergunta": "4. Nível de dedicação geral (dieta e hábitos):", "tipo": "radio", "opcoes": "Dei o meu melhor|Me dediquei|Neutro|Poderia ter feito mais|Não me dediquei nada", "categoria": "1. Comportamento"},
            
            {"id": "refeicoes_fora", "pergunta": "5. Refeições fora do plano (última semana):", "tipo": "slider", "opcoes": "0-10", "categoria": "1. Comportamento"},
            {"id": "dias_alcool", "pergunta": "6. Dias com consumo de álcool:", "tipo": "slider", "opcoes": "0-7", "categoria": "1. Comportamento"},
            
            # 2. Treinos
            {"id": "treino_forca", "pergunta": "7. Treinos de força realizados (ex: musculação):", "tipo": "slider", "opcoes": "0-7", "categoria": "2. Treinos"},
            {"id": "treino_cardio", "pergunta": "8. Treinos aeróbicos realizados (ex: cardio):", "tipo": "slider", "opcoes": "0-7", "categoria": "2. Treinos"},
            
            # 3. Bem-estar
            {"id": "disposicao", "pergunta": "9. Disposição durante o dia:", "tipo": "radio", "opcoes": "Muito disposto(a)|Geralmente disposto(a)|Depende do dia|Geralmente indisposto(a)|Zero disposição", "categoria": "3. Bem-estar"},
            {"id": "estresse", "pergunta": "10. Nível de estresse:", "tipo": "radio", "opcoes": "Não estive estressado(a)|Um pouco estressado(a)|Constantemente estressado(a)", "categoria": "3. Bem-estar"},
            {"id": "ansiedade", "pergunta": "11. Nível de ansiedade:", "tipo": "radio", "opcoes": "Não senti ansiedade|Senti ansiedade em momentos específicos|Senti ansiedade de forma constante", "categoria": "3. Bem-estar"},
            
            # 4. Rotina e Corpo
            {"id": "rotina", "pergunta": "12. Avaliação da rotina diária:", "tipo": "radio", "opcoes": "Bem estruturada e equilibrada|Um pouco desorganizada, mas consigo lidar|Muito desorganizada e me sinto sobrecarregado", "categoria": "4. Rotina e Corpo"},
            {"id": "evolucao", "pergunta": "13. Percepção de evolução corporal:", "tipo": "radio", "opcoes": "Bastante evolução|Consigo notar evolução|Não noto evolução|Talvez esteja regredindo|Estou regredindo", "categoria": "4. Rotina e Corpo"},
            
            # 5. Sono
            {"id": "sono_qualidade", "pergunta": "14. Qualidade do sono:", "tipo": "radio", "opcoes": "Ótimo|Bom|Neutro|Ruim|Terrível", "categoria": "5. Sono"},
            {"id": "sono_horas", "pergunta": "15. Horas de sono (média):", "tipo": "slider", "opcoes": "0-12", "categoria": "5. Sono"},
            
            # 6. Finalização
            {"id": "alteracoes", "pergunta": "16. Deseja alterações no cardápio?", "tipo": "texto_longo", "opcoes": "", "categoria": "6. Finalização"},
            {"id": "nps", "pergunta": "17. Probabilidade de recomendação:", "tipo": "radio", "opcoes": "Muito provável|Provável|Neutro|Improvável|Muito improvável", "categoria": "6. Finalização"},
            {"id": "avaliacao_atend", "pergunta": "18. Avaliação do atendimento (0-10):", "tipo": "slider", "opcoes": "0-10", "categoria": "6. Finalização"}
        ]
        df = pd.DataFrame(dados)
        salvar_csv(df, ARQUIVO_PERGUNTAS)

# --- FUNÇÃO DE ENVIO API ---
def enviar_mensagem_api(telefone, mensagem, instancia, token):
    try:
        url = f"https://api.z-api.io/instances/{instancia}/token/{token}/send-text"
        payload = {"phone": "55" + telefone, "message": mensagem}
        headers = {"Content-Type": "application/json"}
        # response = requests.post(url, json=payload, headers=headers)
        time.sleep(0.5) 
        return True, "Simulado" 
    except Exception as e:
        return False, str(e)

# --- SCORES (MAPEAMENTO COMPLETO) ---
def calcular_scores(df):
    df = df.copy()
    
    def map_score(col_name, mapping):
        if col_name in df.columns:
            return df[col_name].map(mapping).fillna(0)
        return 0

    # Mapas de Pontuação
    map_aderencia = {"Estou conseguindo seguir tudo tranquilamente": 100, "Consigo seguir tudo, mas às vezes passo por alguma dificuldade": 75, "Não consigo realizar tudo": 40, "Não estou conseguindo realizar nada": 0, "100%": 100, "75%": 75}
    map_dedicacao = {"Dei o meu melhor": 100, "Me dediquei": 75, "Neutro": 50, "Poderia ter feito mais": 25, "Não me dediquei nada": 0}
    map_disposicao = {"Muito disposto(a)": 100, "Geralmente disposto(a)": 75, "Depende do dia": 50, "Geralmente indisposto(a)": 25, "Zero disposição": 0}
    map_rotina = {"Bem estruturada e equilibrada": 100, "Um pouco desorganizada, mas consigo lidar": 50, "Muito desorganizada e me sinto sobrecarregado": 0}
    map_evolucao = {"Bastante evolução": 100, "Consigo notar evolução": 75, "Não noto evolução": 50, "Talvez esteja regredindo": 25, "Estou regredindo": 0}
    map_sono = {"Ótimo": 100, "Bom": 75, "Neutro": 50, "Ruim": 25, "Terrível": 0}
    map_estresse = {"Não estive estressado(a)": 0, "Um pouco estressado(a)": 50, "Constantemente estressado(a)": 100}
    map_ansiedade = {"Não senti ansiedade": 0, "Senti ansiedade em momentos específicos": 50, "Senti ansiedade de forma constante": 100}

    # CRIA AS COLUNAS DE SCORE (Garante que existam)
    df['score_aderencia'] = map_score('aderencia', map_aderencia)
    df['score_dedicacao'] = map_score('dedicacao', map_dedicacao)
    df['score_disposicao'] = map_score('disposicao', map_disposicao)
    df['score_rotina'] = map_score('rotina', map_rotina)
    df['score_evolucao'] = map_score('evolucao', map_evolucao)
    df['score_sono'] = map_score('sono_qualidade', map_sono)
    df['score_estresse'] = map_score('estresse', map_estresse)
    df['score_ansiedade'] = map_score('ansiedade', map_ansiedade)

    df['nota_geral'] = (df['score_aderencia'] + df['score_dedicacao']) / 2
    
    numericos = ['peso', 'refeicoes_fora', 'dias_alcool', 'treino_forca', 'treino_cardio', 'sono_horas', 'nps', 'avaliacao_atend']
    for col in numericos:
        if col not in df.columns:
             df[col] = 0 # Cria zerado se não existir para não quebrar gráfico
        else:
             df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    return df

# --- TABELA VISUAL (HEATMAP LEGÍVEL) ---
def gerar_tabela_visual(df):
    df_view = pd.DataFrame()
    df_view['Data'] = df['data_visual']
    
    if 'peso' in df.columns: df_view['Peso'] = df['peso']

    def get_icon(val, invertido=False):
        try: val = float(val)
        except: return "⚪"
        if invertido:
            if val == 0: return "🟢"
            if val <= 50: return "😐"
            return "🔴"
        else:
            if val >= 75: return "🟢"
            if val >= 50: return "😐"
            return "🔴"

    # Nomes Claros
    df_view['Aderência'] = df['score_aderencia'].apply(lambda x: get_icon(x))
    df_view['Dedicaçãp'] = df['score_dedicacao'].apply(lambda x: get_icon(x))
    df_view['Sono'] = df['score_sono'].apply(lambda x: get_icon(x))
    df_view['Rotina'] = df['score_rotina'].apply(lambda x: get_icon(x))
    df_view['Disposição'] = df['score_disposicao'].apply(lambda x: get_icon(x))
    
    # Numéricos com ícones
    df_view['Furos'] = df['refeicoes_fora'].apply(lambda x: "🟢" if x <= 2 else ("😐" if x <= 4 else "🔴"))
    df_view['Álcool'] = df['dias_alcool'].apply(lambda x: "🟢" if x == 0 else ("😐" if x <= 2 else "🔴"))
    df_view['Treino'] = df['treino_forca'].apply(lambda x: "🟢" if x >= 3 else ("😐" if x >= 1 else "🔴"))

    df_view['Nota'] = df['nota_geral'].apply(lambda x: f"{x:.0f}")
    return df_view

# --- GRÁFICO (COM CHECK DE DADOS) ---
def plot_evolucao(df, y_col, color, title, domain=[0, 100]):
    # Garante que a coluna existe e tem dados, senão retorna aviso
    if df.empty or y_col not in df.columns: 
        st.caption(f"Sem dados para: {title}")
        return None
    
    df_chart = df.dropna(subset=[y_col]).copy()
    # Se só tiver zeros (coluna criada artificialmente), não plota ou plota zerado
    if df_chart[y_col].sum() == 0 and df_chart[y_col].max() == 0:
         st.caption(f"Aguardando dados para: {title}")
         return None

    base = alt.Chart(df_chart).encode(
        x=alt.X('data_visual', sort=None, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y_col, title=None, scale=alt.Scale(domain=domain)),
        tooltip=[alt.Tooltip('data_visual', title='Data'), alt.Tooltip(y_col, title='Valor')]
    )
    linha = base.mark_line(color=color, strokeWidth=3)
    pontos = base.mark_circle(color=color, size=80)
    
    st.markdown(f"**{title}**")
    st.altair_chart((linha + pontos).interactive(), use_container_width=True)

# ========================================================
# VIEW DO ADMIN
# ========================================================
def show_admin():
    inicializar_perguntas_padrao()

    # 1. CONFIGURAÇÃO DE DATAS E NOMES
    dias_semana = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
    hoje_idx = datetime.now().weekday()
    hoje_nome = dias_semana[hoje_idx]
    display_hoje = f"{hoje_nome}-feira" if hoje_idx < 5 else hoje_nome

    # 2. CARREGAMENTO E CÁLCULO DE PENDÊNCIAS
    df_users_notify = carregar_csv(ARQUIVO_USUARIOS)
    df_check_all = carregar_csv(ARQUIVO_CHECKINS)
    df_beliscadas_all = carregar_csv(ARQUIVO_BELISCADAS)
    
    # Criar dicionário de nomes logo no início
    dict_nomes = dict(zip(df_users_notify['username'], df_users_notify['name'])) if not df_users_notify.empty else {}

    # Cálculo de Check-ins Pendentes
    if not df_check_all.empty and 'status' not in df_check_all.columns: 
        df_check_all['status'] = 'Revisado'
        salvar_csv(df_check_all, ARQUIVO_CHECKINS)
    
    pendentes_df = df_check_all[df_check_all['status'] == 'Pendente'] if not df_check_all.empty else pd.DataFrame()
    total_pendentes = len(df_check_all[df_check_all['status'] == 'Pendente']) if not df_check_all.empty else 0
    
    # Cálculo de Beliscadas Novas
    total_beliscadas = len(df_beliscadas_all[df_beliscadas_all['status'] == 'Pendente']) if not df_beliscadas_all.empty and 'status' in df_beliscadas_all.columns else 0

    beliscadas_pend = df_beliscadas_all[df_beliscadas_all['status'] == 'Pendente'] if not df_beliscadas_all.empty and 'status' in df_beliscadas_all.columns else pd.DataFrame()
    total_beliscadas = len(beliscadas_pend)

    # 3. INTERFACE INICIAL E TÍTULO
    st.title("🕵️ Painel Administrativo")
    
    # --- BLOCO DE AVISOS (ORDEM SOLICITADA) ---
    
    # Aviso 1: Data (Azul)
    st.info(f"📅 Hoje é **{display_hoje}**. Verifique as cobranças abaixo:")

    # Aviso 2: Check-ins para Revisar (Vermelho)
    if total_pendentes > 0:
        st.error(f"🚨 **ATENÇÃO:** Você tem {total_pendentes} check-ins aguardando revisão!")
    
    # Aviso 3: Notificação de Beliscadas (Amarelo)
    if total_beliscadas > 0:
        st.warning(f"🍫 **NOTIFICAÇÃO:** Existem {total_beliscadas} novos registros de beliscadas para analisar!")
    if total_beliscadas > 0:
    # Pegamos os nomes únicos de quem beliscou usando o dicionário
        usuarios_novos = beliscadas_pend['username'].unique()
        nomes_lista = [dict_nomes.get(user, user) for user in usuarios_novos]
        nomes_formatados = ", ".join(nomes_lista)
    
        st.warning(f"🍫 **NOTIFICAÇÃO:** Novos registros de: **{nomes_formatados}**")

    # 4. LÓGICA DE COBRANÇA E DISPARO
    lista_disparo = []
    
    df_conf = carregar_csv(ARQUIVO_CONFIG_API)
    instancia_api = str(df_conf.iloc[0].get('instancia', '')) if not df_conf.empty else ""
    token_api = str(df_conf.iloc[0].get('token', '')) if not df_conf.empty else ""

    if not df_users_notify.empty:
        # Garante colunas necessárias
        for c in ['role', 'active', 'dia_checkin', 'frequencia', 'telefone', 'data_inicio']:
            if c not in df_users_notify.columns: df_users_notify[c] = ""

        # Filtra quem deve fazer check-in hoje
        pendentes_hoje = df_users_notify[
            (df_users_notify['role'] == 'paciente') & 
            (df_users_notify['active'] != 'False') &
            (df_users_notify['dia_checkin'] == hoje_nome)
        ]
        
        for idx, row in pendentes_hoje.iterrows():
            dias_atras, _ = dias_desde_ultimo_checkin(row['username'])
            freq = str(row.get('frequencia', 'Semanal'))
            data_ini_str = str(row.get('data_inicio', ''))
            
            try: data_inicio = datetime.strptime(data_ini_str, "%Y-%m-%d").date()
            except: data_inicio = date.today()
            
            dias_de_plano = (datetime.now().date() - data_inicio).days
            
            cobrar = False
            if dias_atras == 999: # Paciente novo
                if freq == "Semanal" and dias_de_plano >= 7: cobrar = True
                elif freq == "Quinzenal" and dias_de_plano >= 15: cobrar = True
            else: # Paciente veterano
                if freq == "Semanal" and dias_atras >= 6: cobrar = True
                elif freq == "Quinzenal" and dias_atras >= 13: cobrar = True
            
            if cobrar: lista_disparo.append(row)

    # Exibição das opções de cobrança
    if lista_disparo:
        col_auto, col_manual = st.columns([1, 1])
        with col_auto:
            st.markdown(f"**⚡ Envio Automático ({len(lista_disparo)} aptos)**")
            if st.button(f"🚀 Disparar para Todos (API)", type="primary"):
                if not instancia_api or not token_api:
                    st.error("⚠️ Configure a API na aba Config.")
                else:
                    bar = st.progress(0)
                    for i, p in enumerate(lista_disparo):
                        tel = limpar_telefone(p.get('telefone', ''))
                        if tel:
                            msg = f"Oi {p['name']}! Hoje é dia de check-in. Acesse: {LINK_PLATAFORMA}"
                            enviar_mensagem_api(tel, msg, instancia_api, token_api)
                        bar.progress((i + 1) / len(lista_disparo))
                    st.success("Disparo concluído!")

        with col_manual:
            with st.expander("🔗 Envio Manual (Links)"):
                for p in lista_disparo:
                    tel = limpar_telefone(p.get('telefone', ''))
                    if tel:
                        link = f"https://wa.me/55{tel}?text=Oi%20{p['name']}!%20Hoje%20é%20dia%20de%20check-in.%20Acesse:%20{LINK_PLATAFORMA}"
                        st.markdown(f"[{p['name']}]({link})")
                    else: st.write(f"{p['name']} (Sem telefone)")
    else:
        # Aviso 4: Tudo em dia (Verde)
        st.success("✅ Não há check-ins para enviar hoje.")

    st.markdown("---")
    
    label_p = f"📥 Pendentes ({total_pendentes})" if total_pendentes > 0 else "📥 Pendentes"
    tab_pend, tab_evol, tab_user, tab_editor, tab_cont, tab_vid, tab_conf = st.tabs([
        label_p, "📊 Histórico", "👥 Pacientes", "📝 Editor de Check-in", "📂 Conteúdo", "🎥 Aulas", "⚙️ Config"
    ])

    # --- ABA 1: PENDENTES ---
    with tab_pend:
        st.subheader("Caixa de Entrada")
        if total_pendentes > 0:
            df_p_calc = calcular_scores(pendentes_df)
            df_p_calc['data_real'] = pd.to_datetime(df_p_calc['data'], errors='coerce')
            df_p_calc = df_p_calc.sort_values('data_real')

            for idx, row in df_p_calc.iterrows():
                u_info = df_users_notify[df_users_notify['username'] == row['username']]
                nome_exibicao = dict_nomes.get(row['username'], row['username'])
                nome_display = u_info.iloc[0]['name'] if not u_info.empty else row['username']
                
                with st.expander(f"👤 {nome_exibicao} | Nota: {row.get('nota_geral', 0):.0f}", expanded=True):
                    c1, c2 = st.columns(2)
                    if 'peso' in row: c1.write(f"📉 **Peso:** {row['peso']}kg")
                    if 'score_aderencia' in row: c2.write(f"🧠 **Nota:** {row['score_aderencia']}")
                    st.divider()
                    
                    # Mostra respostas
                    ignore = ['username', 'data', 'status', 'data_real', 'nota_geral', 'score_aderencia', 'score_dedicacao', 'score_disposicao', 'score_rotina', 'score_evolucao', 'score_sono', 'score_estresse', 'score_ansiedade', 'peso', 'aderencia', 'dedicacao']
                    for c in row.index:
                        if c not in ignore and pd.notnull(row[c]) and str(row[c]) != "":
                            st.write(f"**{c.capitalize().replace('_', ' ')}:** {row[c]}")
                    
                    st.write("---")
                    txt_feed = st.text_area("Feedback:", key=f"feed_{idx}")
                    b1, b2 = st.columns([1, 1])
                    
                    phone = ""
                    if not u_info.empty: phone = limpar_telefone(u_info.iloc[0].get('telefone', ''))
                    if phone:
                        link_zap = f"https://wa.me/55{phone}?text={txt_feed.replace(' ', '%20')}"
                        b1.markdown(f'<a href="{link_zap}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px 20px;border-radius:5px;width:100%">📱 Zap</button></a>', unsafe_allow_html=True)
                    
                    if b2.button("✅ Arquivar", key=f"rev_{idx}", type="primary", use_container_width=True):
                        df_check_all.at[idx, 'status'] = 'Revisado'
                        salvar_csv(df_check_all, ARQUIVO_CHECKINS)
                        st.success("Arquivado!")
                        st.rerun()
        else: st.info("Caixa de entrada limpa.")

    # --- ABA 2: HISTÓRICO COMPLETO ---
    with tab_evol:
        st.subheader("Histórico")
        pacs = df_users_notify[df_users_notify['role']=='paciente']['username'].unique() if not df_users_notify.empty else []
        sel = st.selectbox("Paciente:", options=pacs, format_func=lambda x: dict_nomes.get(x, x))
        
        if sel and not df_check_all.empty:
            df_user_hist = df_check_all[df_check_all['username'] == sel].copy()
            if not df_user_hist.empty:
                df_h = calcular_scores(df_user_hist)
                df_h['data_real'] = pd.to_datetime(df_h['data'], errors='coerce')
                df_h = df_h.sort_values('data_real')
                df_h['data_visual'] = df_h['data_real'].dt.strftime('%d/%m')

                # --- HEATMAP ---
                st.markdown("### 🚦 Visão Geral")
                df_visual = gerar_tabela_visual(df_h)
                st.dataframe(df_visual, hide_index=True, use_container_width=True)
                

                st.markdown("### 📈 Evolução")
                # GRUPO 1
                col_a, col_b = st.columns(2)
                with col_a: plot_evolucao(df_h, 'peso', '#FF4B4B', 'Peso (kg)', [40, 150])
                with col_b: plot_evolucao(df_h, 'score_aderencia', '#00D4FF', 'Aderência')
                
                col_c, col_d = st.columns(2)
                with col_c: plot_evolucao(df_h, 'score_dedicacao', '#2ECC71', 'Dedicação')
                with col_d: plot_evolucao(df_h, 'refeicoes_fora', '#F39C12', 'Refeições Fora', [0, 15])

                # GRUPO 2
                col_e, col_f = st.columns(2)
                with col_e: plot_evolucao(df_h, 'treino_forca', '#9B59B6', 'Treino Força', [0, 7])
                with col_f: plot_evolucao(df_h, 'score_sono', '#8E44AD', 'Qualidade Sono')
                
                col_g, col_h = st.columns(2)
                with col_g: plot_evolucao(df_h, 'score_disposicao', '#E67E22', 'Disposição')
                with col_h: plot_evolucao(df_h, 'score_estresse', '#E74C3C', 'Estresse (Intensidade)')

                st.dataframe(df_h.drop(columns=['data_real', 'data_visual', 'username'], errors='ignore'))
                st.divider()
                exibir_monitoramento_comportamental(sel)
            else: st.warning("Sem dados para este paciente.")

                

    # --- ABA 3: PACIENTES ---
    with tab_user:
            st.subheader("Gestão de Pacientes")
            if not df_users_notify.empty:
                if 'data_inicio' in df_users_notify.columns:
                    df_users_notify['data_inicio'] = pd.to_datetime(df_users_notify['data_inicio'], errors='coerce')
                df_users_notify['active'] = df_users_notify['active'].astype(str).map({'True':True, 'False':False, 'true':True, 'false':False}).fillna(True)
            
                df_ed = st.data_editor(
                    df_users_notify,
                    column_config={
                        "active": st.column_config.CheckboxColumn("Ativo?"),
                        "username": st.column_config.TextColumn("Login", disabled=True),
                        "role": st.column_config.SelectboxColumn("Cargo", options=["admin", "paciente"]),
                        "telefone": st.column_config.TextColumn("WhatsApp"),
                        "dia_checkin": st.column_config.SelectboxColumn("Dia", options=["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]),
                        "frequencia": st.column_config.SelectboxColumn("Plano", options=["Semanal", "Quinzenal"]),
                        "data_inicio": st.column_config.DateColumn("Início", format="YYYY-MM-DD")
                    },
                    hide_index=True, num_rows="fixed", use_container_width=True
                )
                if st.button("💾 Salvar Alterações"):
                    if 'data_inicio' in df_ed.columns:
                        df_ed['data_inicio'] = df_ed['data_inicio'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else '')
                    salvar_csv(df_ed, ARQUIVO_USUARIOS)
                    st.success("Salvo!")
                    st.rerun()

            with st.expander("🗑️ Excluir Paciente"):
                sel_del = st.selectbox("Excluir quem?", df_users_notify[df_users_notify['role']=='paciente']['username'].unique())
                if st.button("❌ Confirmar Exclusão"):
                    df_nov = df_users_notify[df_users_notify['username'] != sel_del]
                    if 'data_inicio' in df_nov.columns:
                        df_nov['data_inicio'] = df_nov['data_inicio'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else '')
                    salvar_csv(df_nov, ARQUIVO_USUARIOS)
                    st.success("Excluído.")
                    st.rerun()

            st.markdown("---")
            st.markdown("##### Novo Paciente")
            with st.form("add_user"):
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Nome")
                u = c2.text_input("Login")
                p = c3.text_input("Senha")
                c4, c5, c6 = st.columns(3)
                t = c4.text_input("WhatsApp")
                f = c5.selectbox("Frequência", ["Semanal", "Quinzenal"])
                d_ini = c6.date_input("Início", date.today())
                d_chk = st.selectbox("Dia Check-in", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"])
                if st.form_submit_button("Criar Paciente"):
                    if u and u not in df_users_notify['username'].values:
                        nv = {"username": u, "password": p, "name": n, "role": "paciente", "active": True, "telefone": t, "dia_checkin": d_chk, "frequencia": f, "data_inicio": str(d_ini)}
                        df_o = carregar_csv(ARQUIVO_USUARIOS)
                        salvar_csv(pd.concat([df_o, pd.DataFrame([nv])], ignore_index=True), ARQUIVO_USUARIOS)
                        st.success("Criado!")
                        st.rerun()
                    else: st.error("Erro.")

    # --- ABA 4: EDITOR ---
    with tab_editor:
        st.subheader("Editor de Perguntas")
        if st.button("🔄 Restaurar Modelo do PDF"):
            inicializar_perguntas_padrao(forcar=True)
            st.success("Restaurado!")
            st.rerun()
            
        df_perg = carregar_csv(ARQUIVO_PERGUNTAS)
        df_perg_ed = st.data_editor(df_perg, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Salvar Perguntas"):
            salvar_csv(df_perg_ed, ARQUIVO_PERGUNTAS)
            st.success("Atualizado!")

    # --- ABA 5: CONTEÚDO ---
    with tab_cont:
        st.subheader("Ebooks")
        garantir_pasta_ebooks()
        up = st.file_uploader("Upload PDF", type="pdf")
        if up:
            with open(os.path.join(PASTA_EBOOKS, up.name), "wb") as f: f.write(up.getbuffer())
            st.success("Salvo!")
        if os.path.exists(PASTA_EBOOKS):
            for arq in os.listdir(PASTA_EBOOKS):
                if arq.endswith(".pdf"):
                    c1, c2 = st.columns([4,1])
                    c1.text(f"📄 {arq}")
                    if c2.button("🗑️", key=f"del_{arq}"): os.remove(os.path.join(PASTA_EBOOKS, arq)); st.rerun()
        st.divider()
        st.subheader("Parceiros")
        df_ped = st.data_editor(carregar_csv(ARQUIVO_PARCEIROS), num_rows="dynamic")
        if st.button("Salvar Parceiros"): salvar_csv(df_ped, ARQUIVO_PARCEIROS)

    # --- ABA 6: AULAS ---
    with tab_vid:
        st.subheader("Aulas")
        df_v = carregar_csv(ARQUIVO_VIDEOS)
        if df_v.empty: df_v = pd.DataFrame(columns=["titulo", "modulo", "link", "descricao"])
        
        with st.expander("✨ Criar Novo Módulo / Aula"):
            mods = df_v['modulo'].unique().tolist() if not df_v.empty else []
            mods.insert(0, "Criar Novo...")
            sm = st.selectbox("Módulo:", mods)
            nm = st.text_input("Nome Novo:") if sm == "Criar Novo..." else sm
            at = st.text_input("Título:")
            al = st.text_input("Link:")
            ad = st.text_input("Desc:")
            if st.button("Adicionar"):
                if nm and at:
                    nv = {"titulo": at, "modulo": nm, "link": al, "descricao": ad}
                    df_v = pd.concat([df_v, pd.DataFrame([nv])], ignore_index=True)
                    salvar_csv(df_v, ARQUIVO_VIDEOS)
                    st.success("Adicionado!"); st.rerun()
        
        with st.expander("📂 Renomear Módulos"):
            if not df_v.empty:
                m = st.selectbox("Módulo Antigo:", df_v['modulo'].unique())
                n = st.text_input("Novo Nome:")
                if st.button("Renomear"):
                    df_v.loc[df_v['modulo'] == m, 'modulo'] = n
                    salvar_csv(df_v, ARQUIVO_VIDEOS); st.success("Feito!"); st.rerun()

        df_ved = st.data_editor(df_v, num_rows="dynamic", use_container_width=True)
        if st.button("Salvar Vídeos"):
            if not df_ved.empty: df_ved = df_ved.sort_values(by='modulo')
            salvar_csv(df_ved, ARQUIVO_VIDEOS); st.success("Salvo!")
        
        with st.expander("🗑️ Excluir Aula"):
            if not df_v.empty:
                d = st.selectbox("Apagar:", df_v['titulo'].unique())
                if st.button("Apagar"):
                    df_v = df_v[df_v['titulo'] != d]
                    salvar_csv(df_v, ARQUIVO_VIDEOS); st.rerun()

    # --- ABA 7: CONFIG ---
    with tab_conf:
        st.subheader("⚙️ Configuração API")
        df_conf = carregar_csv(ARQUIVO_CONFIG_API)
        if df_conf.empty: df_conf = pd.DataFrame([{"instancia": "", "token": ""}])
        conf_ed = st.data_editor(df_conf, num_rows=1)
        if st.button("Salvar Config"):
            salvar_csv(conf_ed, ARQUIVO_CONFIG_API)
            st.success("Salvo!")

def exibir_monitoramento_comportamental(username_paciente):
    st.subheader("🍫 Monitor de beliscadas")
    
    if not os.path.exists(ARQUIVO_BELISCADAS):
        st.info("Nenhum registro de beliscada encontrado no sistema.")
        return

    df = pd.read_csv(ARQUIVO_BELISCADAS)
    # Filtra apenas os registros do paciente que você está visualizando agora
    df_paciente = df[df['username'] == username_paciente].copy()

    if df_paciente.empty:
        st.write("✅ Este paciente ainda não registrou beliscadas.")
    else:
        # 1. Resumo Visual de Gatilhos
        st.markdown("**Principais Gatilhos Identificados:**")
        chart = alt.Chart(df_paciente).mark_bar().encode(
            x=alt.X('count()', title='Frequência'),
            y=alt.Y('gatilho', sort='-x', title='Gatilho'),
            color=alt.Color('gatilho', legend=None)
        ).properties(height=200)
        st.altair_chart(chart, use_container_width=True)

        # 2. Tabela Detalhada
        st.markdown("**Histórico de Registros:**")
        # Reordenando para mostrar o que comeu e o sentimento primeiro
        colunas_visiveis = ['data', 'hora', 'alimento', 'gatilho', 'sentimento', 'plano_futuro']
        st.dataframe(df_paciente[colunas_visiveis], use_container_width=True, hide_index=True)