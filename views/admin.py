import streamlit as st
import pandas as pd
import os
import altair as alt
import requests
import time
from datetime import datetime, timedelta, date
# IMPORTS DO BANCO DE DADOS
from database import carregar_dados, salvar_novo_registro, atualizar_tabela_completa
from streamlit import fragment

# --- CONFIGURAÇÃO DE ARQUIVOS ---
# Removemos os CSVs que agora são tabelas do banco
# Mantemos apenas o que é arquivo físico ou configuração estática
ARQUIVO_PERGUNTAS = "data/perguntas_checkin.csv"
PASTA_EBOOKS = "assets/ebooks"
LINK_PLATAFORMA = "https://seu-app-nutricao.streamlit.app" 

# --- FUNÇÕES ÚTEIS MANTIDAS/ADAPTADAS ---
def carregar_csv_perguntas(caminho):
    """Função exclusiva para carregar o CSV de perguntas"""
    if not os.path.exists(caminho): return pd.DataFrame()
    return pd.read_csv(caminho, dtype=str)

def salvar_csv_perguntas(df, caminho):
    """Função exclusiva para salvar o CSV de perguntas"""
    df.to_csv(caminho, index=False)

def garantir_pasta_ebooks():
    if not os.path.exists(PASTA_EBOOKS):
        os.makedirs(PASTA_EBOOKS)

def limpar_telefone(tel):
    if not tel: return ""
    return "".join(filter(str.isdigit, str(tel)))

def dias_desde_ultimo_checkin(username):
    # AGORA LÊ DO BANCO
    df = carregar_dados("checkins")
    if df.empty: return 999, "Nunca"
    
    # Garante que a coluna username existe
    if 'username' not in df.columns: return 999, "Nunca"

    df_user = df[df['username'] == username].copy()
    if df_user.empty: return 999, "Nunca"
    
    if 'data' in df_user.columns:
        df_user['data_real'] = pd.to_datetime(df_user['data'], errors='coerce')
        df_user = df_user.dropna(subset=['data_real'])
        
        if df_user.empty: return 999, "Nunca"

        ultima_data = df_user['data_real'].max()
        delta = (datetime.now() - ultima_data).days
        return delta, ultima_data.strftime("%d/%m/%Y")
    
    return 999, "Nunca"

def inicializar_perguntas_padrao(forcar=False):
    """Cria o arquivo de perguntas (CSV) se não existir"""
    if not os.path.exists(ARQUIVO_PERGUNTAS) or forcar:
        # (Mantendo seu dicionário original de perguntas aqui)
        dados = [
            {"id": "peso", "pergunta": "Peso Atual (kg)", "tipo": "numero", "opcoes": "", "categoria": "0. Dados Iniciais"},
            {"id": "aderencia", "pergunta": "3. Aderência ao plano alimentar:", "tipo": "radio", "opcoes": "Estou conseguindo seguir tudo tranquilamente|Consigo seguir tudo, mas às vezes passo por alguma dificuldade|Não consigo realizar tudo|Não estou conseguindo realizar nada", "categoria": "1. Comportamento"},
            {"id": "aderencia_expl", "pergunta": "Explicação (se houver dificuldade):", "tipo": "texto_longo", "opcoes": "", "categoria": "1. Comportamento"},
            {"id": "dedicacao", "pergunta": "4. Nível de dedicação geral (dieta e hábitos):", "tipo": "radio", "opcoes": "Dei o meu melhor|Me dediquei|Neutro|Poderia ter feito mais|Não me dediquei nada", "categoria": "1. Comportamento"},
            {"id": "refeicoes_fora", "pergunta": "5. Refeições fora do plano (última semana):", "tipo": "slider", "opcoes": "0-10", "categoria": "1. Comportamento"},
            {"id": "dias_alcool", "pergunta": "6. Dias com consumo de álcool:", "tipo": "slider", "opcoes": "0-7", "categoria": "1. Comportamento"},
            {"id": "treino_forca", "pergunta": "7. Treinos de força realizados (ex: musculação):", "tipo": "slider", "opcoes": "0-7", "categoria": "2. Treinos"},
            {"id": "treino_cardio", "pergunta": "8. Treinos aeróbicos realizados (ex: cardio):", "tipo": "slider", "opcoes": "0-7", "categoria": "2. Treinos"},
            {"id": "disposicao", "pergunta": "9. Disposição durante o dia:", "tipo": "radio", "opcoes": "Muito disposto(a)|Geralmente disposto(a)|Depende do dia|Geralmente indisposto(a)|Zero disposição", "categoria": "3. Bem-estar"},
            {"id": "estresse", "pergunta": "10. Nível de estresse:", "tipo": "radio", "opcoes": "Não estive estressado(a)|Um pouco estressado(a)|Constantemente estressado(a)", "categoria": "3. Bem-estar"},
            {"id": "ansiedade", "pergunta": "11. Nível de ansiedade:", "tipo": "radio", "opcoes": "Não senti ansiedade|Senti ansiedade em momentos específicos|Senti ansiedade de forma constante", "categoria": "3. Bem-estar"},
            {"id": "rotina", "pergunta": "12. Avaliação da rotina diária:", "tipo": "radio", "opcoes": "Bem estruturada e equilibrada|Um pouco desorganizada, mas consigo lidar|Muito desorganizada e me sinto sobrecarregado", "categoria": "4. Rotina e Corpo"},
            {"id": "evolucao", "pergunta": "13. Percepção de evolução corporal:", "tipo": "radio", "opcoes": "Bastante evolução|Consigo notar evolução|Não noto evolução|Talvez esteja regredindo|Estou regredindo", "categoria": "4. Rotina e Corpo"},
            {"id": "sono_qualidade", "pergunta": "14. Qualidade do sono:", "tipo": "radio", "opcoes": "Ótimo|Bom|Neutro|Ruim|Terrível", "categoria": "5. Sono"},
            {"id": "sono_horas", "pergunta": "15. Horas de sono (média):", "tipo": "slider", "opcoes": "0-12", "categoria": "5. Sono"},
            {"id": "alteracoes", "pergunta": "16. Deseja alterações no cardápio?", "tipo": "texto_longo", "opcoes": "", "categoria": "6. Finalização"},
            {"id": "nps", "pergunta": "17. Probabilidade de recomendação:", "tipo": "radio", "opcoes": "Muito provável|Provável|Neutro|Improvável|Muito improvável", "categoria": "6. Finalização"},
            {"id": "avaliacao_atend", "pergunta": "18. Avaliação do atendimento (0-10):", "tipo": "slider", "opcoes": "0-10", "categoria": "6. Finalização"}
        ]
        df = pd.DataFrame(dados)
        salvar_csv_perguntas(df, ARQUIVO_PERGUNTAS)

# --- FUNÇÃO DE ENVIO API (MANTIDA) ---
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

    # CRIA AS COLUNAS DE SCORE
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
             df[col] = 0
        else:
             df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    return df

# --- TABELA VISUAL (HEATMAP) ---
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

    df_view['Aderência'] = df['score_aderencia'].apply(lambda x: get_icon(x))
    df_view['Dedicaçãp'] = df['score_dedicacao'].apply(lambda x: get_icon(x))
    df_view['Sono'] = df['score_sono'].apply(lambda x: get_icon(x))
    df_view['Rotina'] = df['score_rotina'].apply(lambda x: get_icon(x))
    df_view['Disposição'] = df['score_disposicao'].apply(lambda x: get_icon(x))
    
    df_view['Furos'] = df['refeicoes_fora'].apply(lambda x: "🟢" if x <= 2 else ("😐" if x <= 4 else "🔴"))
    df_view['Álcool'] = df['dias_alcool'].apply(lambda x: "🟢" if x == 0 else ("😐" if x <= 2 else "🔴"))
    df_view['Treino'] = df['treino_forca'].apply(lambda x: "🟢" if x >= 3 else ("😐" if x >= 1 else "🔴"))

    df_view['Nota'] = df['nota_geral'].apply(lambda x: f"{x:.0f}")
    return df_view

# --- GRÁFICO ---
def plot_evolucao(df, y_col, color, title, domain=[0, 100]):
    if df.empty or y_col not in df.columns: 
        st.caption(f"Sem dados para: {title}")
        return None
    
    df_chart = df.dropna(subset=[y_col]).copy()
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

def exibir_monitoramento_comportamental(username_paciente):
    st.subheader("🍫 Monitor de beliscadas")
    
    # CARREGA DO BANCO
    df = carregar_dados("beliscadas")
    
    if df.empty or 'username' not in df.columns:
        st.info("Nenhum registro de beliscada encontrado no sistema.")
        return

    df_paciente = df[df['username'] == username_paciente].copy()

    if df_paciente.empty:
        st.write("✅ Este paciente ainda não registrou beliscadas.")
    else:
        st.markdown("**Principais Gatilhos Identificados:**")
        if 'gatilho' in df_paciente.columns:
            chart = alt.Chart(df_paciente).mark_bar().encode(
                x=alt.X('count()', title='Frequência'),
                y=alt.Y('gatilho', sort='-x', title='Gatilho'),
                color=alt.Color('gatilho', legend=None)
            ).properties(height=200)
            st.altair_chart(chart, use_container_width=True)

        st.markdown("**Histórico de Registros:**")
        cols_possiveis = ['data', 'hora', 'alimento', 'gatilho', 'sentimento', 'plano_futuro']
        colunas_visiveis = [c for c in cols_possiveis if c in df_paciente.columns]
        st.dataframe(df_paciente[colunas_visiveis], use_container_width=True, hide_index=True)

# ========================================================
# VIEW DO ADMIN (PRINCIPAL)
# ========================================================
def show_admin():
    inicializar_perguntas_padrao()

    # 1. CONFIGURAÇÃO DE DATAS E NOMES
    dias_semana = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
    hoje_idx = datetime.now().weekday()
    hoje_nome = dias_semana[hoje_idx]
    display_hoje = f"{hoje_nome}-feira" if hoje_idx < 5 else hoje_nome

    # 2. CARREGAMENTO DO BANCO DE DADOS
    df_users_notify = carregar_dados("usuarios")
    df_check_all = carregar_dados("checkins")
    df_beliscadas_all = carregar_dados("beliscadas")
    
    dict_nomes = {}
    if not df_users_notify.empty and 'username' in df_users_notify.columns and 'name' in df_users_notify.columns:
        dict_nomes = dict(zip(df_users_notify['username'], df_users_notify['name']))

    # Cálculo de Check-ins Pendentes
    total_pendentes = 0
    pendentes_df = pd.DataFrame()
    if not df_check_all.empty:
        if 'status' not in df_check_all.columns: 
            df_check_all['status'] = 'Revisado'
        pendentes_df = df_check_all[df_check_all['status'] == 'Pendente']
        total_pendentes = len(pendentes_df)
    
    # Cálculo de Beliscadas Novas
    total_beliscadas = 0
    beliscadas_pend = pd.DataFrame()
    if not df_beliscadas_all.empty and 'status' in df_beliscadas_all.columns:
        beliscadas_pend = df_beliscadas_all[df_beliscadas_all['status'] == 'Pendente']
        total_beliscadas = len(beliscadas_pend)

    # 3. INTERFACE INICIAL
    st.title("🕵️ Painel Administrativo")
    st.info(f"📅 Hoje é **{display_hoje}**. Verifique as cobranças abaixo:")

    if total_pendentes > 0:
        st.error(f"🚨 **ATENÇÃO:** Você tem {total_pendentes} check-ins aguardando revisão!")
    
    if total_beliscadas > 0:
        st.warning(f"🍫 **NOTIFICAÇÃO:** Existem {total_beliscadas} novos registros de beliscadas!")
        if 'username' in beliscadas_pend.columns:
            usuarios_novos = beliscadas_pend['username'].unique()
            nomes_lista = [dict_nomes.get(user, user) for user in usuarios_novos]
            st.warning(f"Pacientes: **{', '.join(nomes_lista)}**")

    # 4. LÓGICA DE COBRANÇA E DISPARO
    lista_disparo = []
    
    df_conf = carregar_dados("config_api")
    instancia_api = ""
    token_api = ""
    if not df_conf.empty:
        if 'instancia' in df_conf.columns: instancia_api = str(df_conf.iloc[0]['instancia'])
        if 'token' in df_conf.columns: token_api = str(df_conf.iloc[0]['token'])

    if not df_users_notify.empty:
        for c in ['role', 'active', 'dia_checkin', 'frequencia', 'telefone', 'data_inicio']:
            if c not in df_users_notify.columns: df_users_notify[c] = ""

        # Filtro de disparo (Paciente + Ativo + Dia Certo)
        # Tratamento seguro de booleanos/strings do banco
        df_users_notify['active_bool'] = df_users_notify['active'].astype(str).map({'True':True, 'False':False, 'true':True, 'false':False, '1':True, '0':False}).fillna(True)
        
        pendentes_hoje = df_users_notify[
            (df_users_notify['role'] == 'paciente') & 
            (df_users_notify['active_bool'] == True) &
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
            if 'data' in df_p_calc.columns:
                df_p_calc['data_real'] = pd.to_datetime(df_p_calc['data'], errors='coerce')
                df_p_calc = df_p_calc.sort_values('data_real')

            for idx, row in df_p_calc.iterrows():
                u_info = df_users_notify[df_users_notify['username'] == row['username']]
                nome_exibicao = dict_nomes.get(row['username'], row['username'])
                
                with st.expander(f"👤 {nome_exibicao} | Nota: {row.get('nota_geral', 0):.0f}", expanded=True):
                    c1, c2 = st.columns(2)
                    if 'peso' in row: c1.write(f"📉 **Peso:** {row['peso']}kg")
                    if 'score_aderencia' in row: c2.write(f"🧠 **Nota:** {row['score_aderencia']}")
                    st.divider()
                    
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
                    
                    if b2.button("✅ Arquivar (Marcar como Revisado)", key=f"rev_{idx}", type="primary"):
                        # ATUALIZA NO BANCO DE DADOS
                        # Localiza a linha correta no DataFrame original e atualiza
                        # Para simplificar a migração, vamos filtrar pelo username e data
                        df_check_all.loc[(df_check_all['username'] == row['username']) & (df_check_all['data'] == row['data']), 'status'] = 'Revisado'
                        atualizar_tabela_completa(df_check_all, "checkins")
                        st.success("Arquivado!")
                        st.rerun()
        else: st.info("Caixa de entrada limpa.")

    # --- ABA 2: HISTÓRICO ---
    with tab_evol:
        st.subheader("Histórico")
        pacs = []
        if not df_users_notify.empty and 'role' in df_users_notify.columns:
            pacs = df_users_notify[df_users_notify['role']=='paciente']['username'].unique()
        
        sel = st.selectbox("Paciente:", options=pacs, format_func=lambda x: dict_nomes.get(x, x))
        
        if sel and not df_check_all.empty:
            df_user_hist = df_check_all[df_check_all['username'] == sel].copy()
            if not df_user_hist.empty:
                df_h = calcular_scores(df_user_hist)
                df_h['data_real'] = pd.to_datetime(df_h['data'], errors='coerce')
                df_h = df_h.sort_values('data_real')
                df_h['data_visual'] = df_h['data_real'].dt.strftime('%d/%m')

                st.markdown("### 🚦 Visão Geral")
                df_visual = gerar_tabela_visual(df_h)
                st.dataframe(df_visual, hide_index=True, use_container_width=True)
                
                st.markdown("### 📈 Evolução")
                col_a, col_b = st.columns(2)
                with col_a: plot_evolucao(df_h, 'peso', '#FF4B4B', 'Peso (kg)', [40, 150])
                with col_b: plot_evolucao(df_h, 'score_aderencia', '#00D4FF', 'Aderência')
                
                # ... (outros gráficos mantidos) ...

                st.divider()
                exibir_monitoramento_comportamental(sel)
            else: st.warning("Sem dados para este paciente.")

    # --- ABA 3: PACIENTES ---
    with tab_user:
            st.subheader("Gestão de Pacientes")
            
            if not df_users_notify.empty:
                # --- PREPARAÇÃO DOS DADOS PARA EXIBIÇÃO ---
                # 1. Tratamento de Data
                if 'data_inicio' in df_users_notify.columns:
                    df_users_notify['data_inicio'] = pd.to_datetime(df_users_notify['data_inicio'], errors='coerce')
                
                # 2. Tratamento do Ativo (Para o Checkbox funcionar)
                # Converte tudo para string minúscula e verifica se é 'true'
                df_users_notify['active'] = df_users_notify['active'].astype(str).str.lower().isin(['true', '1', 'yes', 'on'])
                
                # 3. Limpeza de Strings (Remove espaços extras nos nomes)
                if 'username' in df_users_notify.columns:
                    df_users_notify['username'] = df_users_notify['username'].astype(str).str.strip()

                # --- EDITOR DE DADOS ---
                df_ed = st.data_editor(
                    df_users_notify,
                    column_config={
                        "active": st.column_config.CheckboxColumn("Ativo?", default=True),
                        "username": st.column_config.TextColumn("Login", disabled=True),
                        "role": st.column_config.SelectboxColumn("Cargo", options=["admin", "paciente"]),
                        "data_inicio": st.column_config.DateColumn("Início", format="YYYY-MM-DD")
                    },
                    hide_index=True, num_rows="fixed", use_container_width=True,
                    key="editor_usuarios_tabela"
                )
                
                # --- BOTÃO DE SALVAR (EDIÇÃO) ---
                if st.button("💾 Salvar Alterações na Tabela", type="primary"):
                    # PREPARAÇÃO PARA SALVAR (O PULO DO GATO)
                    # O Banco não gosta de tipos misturados. Vamos converter tudo para String Pura.
                    
                    df_salvar = df_ed.copy()
                    
                    # 1. Converte Data para String
                    if 'data_inicio' in df_salvar.columns:
                        df_salvar['data_inicio'] = df_salvar['data_inicio'].apply(
                            lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) and x != "" else None
                        )
                    
                    # 2. Converte Booleano (Checkbox) para String 'True'/'False'
                    df_salvar['active'] = df_salvar['active'].apply(lambda x: 'True' if x is True else 'False')

                    # 3. Salva no Banco (Substitui a tabela inteira)
                    atualizar_tabela_completa(df_salvar, "usuarios")
                    
                    st.success("✅ Banco de Dados atualizado com sucesso!")
                    time.sleep(1)
                    st.rerun()

            # --- EXCLUSÃO DE PACIENTE ---
            with st.expander("🗑️ Excluir Paciente"):
                if not df_users_notify.empty:
                    # Lista apenas quem é paciente
                    lista_pacs = df_users_notify[df_users_notify['role']=='paciente']['username'].unique() if 'role' in df_users_notify.columns else []
                    
                    if len(lista_pacs) > 0:
                        sel_del = st.selectbox("Selecione o usuário para EXCLUIR:", lista_pacs, key="sel_del_user")
                        
                        if st.button("❌ Confirmar Exclusão Definitiva", type="secondary"):
                            # Filtra mantendo apenas quem NÃO é o selecionado
                            df_nov = df_users_notify[df_users_notify['username'] != sel_del].copy()
                            
                            # --- TRATAMENTO IGUAL AO DE SALVAR ---
                            if 'data_inicio' in df_nov.columns:
                                df_nov['data_inicio'] = df_nov['data_inicio'].apply(
                                    lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) and x != "" else None
                                )
                            
                            # Importante: O df_users_notify original (que usamos no filtro) 
                            # já estava com 'active' como booleano por causa da preparação lá em cima.
                            # Precisamos converter de volta para String antes de salvar.
                            df_nov['active'] = df_nov['active'].apply(lambda x: 'True' if x is True else 'False')

                            # Salva a nova tabela (agora sem o usuário excluído)
                            atualizar_tabela_completa(df_nov, "usuarios")
                            
                            st.success(f"Usuário '{sel_del}' excluído do Banco!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.info("Nenhum paciente encontrado para excluir.")

            st.markdown("---")
            
            # --- NOVO PACIENTE ---
            st.markdown("##### Cadastrar Novo Paciente")
            with st.form("add_user_form", clear_on_submit=False): 
                c1, c2, c3 = st.columns(3)
                n = c1.text_input("Nome", key="cad_nome")
                u = c2.text_input("Login (Usuário)", key="cad_user")
                p = c3.text_input("Senha", key="cad_senha")
                
                c4, c5, c6 = st.columns(3)
                t = c4.text_input("WhatsApp", key="cad_zap")
                f = c5.selectbox("Frequência", ["Semanal", "Quinzenal"], key="cad_freq")
                d_chk = c6.selectbox("Dia Check-in", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"], key="cad_dia")
                
                d_ini = date.today()

                if st.form_submit_button("🚀 Criar Paciente", type="primary"):
                    if u and p and n:
                        # Verifica duplicidade
                        u_final = u.strip().lower()
                        ja_existe = False
                        if not df_users_notify.empty:
                             ja_existe = u_final in df_users_notify['username'].str.lower().values
                        
                        if ja_existe:
                             st.error("Erro: Este Login já existe! Escolha outro.")
                        else:
                            novo_paciente = {
                                "username": u_final,
                                "password": p.strip(),
                                "name": n.strip(),
                                "role": "paciente",
                                "active": "True", # Salva direto como string
                                "telefone": str(t),
                                "dia_checkin": d_chk,
                                "frequencia": f,
                                "data_inicio": str(d_ini)
                            } 
                            if salvar_novo_registro(novo_paciente, "usuarios"):
                                st.success(f"Paciente {n} criado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Erro ao conectar com o Banco de Dados.")    
                    else:
                        st.warning("Preencha Nome, Login e Senha para continuar.")

    # --- ABA 4: EDITOR (Mantém CSV) ---
    with tab_editor:
        st.subheader("Editor de Perguntas")
        if st.button("🔄 Restaurar Modelo do PDF"):
            inicializar_perguntas_padrao(forcar=True)
            st.success("Restaurado!")
            st.rerun()
            
        df_perg = carregar_csv_perguntas(ARQUIVO_PERGUNTAS)
        df_perg_ed = st.data_editor(df_perg, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Salvar Perguntas"):
            salvar_csv_perguntas(df_perg_ed, ARQUIVO_PERGUNTAS)
            st.success("Atualizado!")

    # --- ABA 5: CONTEÚDO (Misto: Ebooks Local / Parceiros DB) ---
    with tab_cont:
        st.subheader("📚 Gestão de Ebooks")
        garantir_pasta_ebooks()
        up = st.file_uploader("Upload PDF", type="pdf")
        if up:
            with open(os.path.join(PASTA_EBOOKS, up.name), "wb") as f: f.write(up.getbuffer())
            st.success("Salvo!")
            st.rerun()
            
        if os.path.exists(PASTA_EBOOKS):
            for arq in os.listdir(PASTA_EBOOKS):
                if arq.endswith(".pdf"):
                    c1, c2 = st.columns([4,1])
                    c1.text(f"📄 {arq}")
                    if c2.button("🗑️", key=f"del_{arq}"): os.remove(os.path.join(PASTA_EBOOKS, arq)); st.rerun()
        
        st.divider()
        st.subheader("🤝 Gestão de Parceiros & Cupons")
        
        # 1. CARREGAMENTO DOS DADOS E CORREÇÃO DE ESQUEMA (AUTO-REPARO)
        df_parc = carregar_dados("parceiros")
        
        # --- AQUI É A CORREÇÃO MÁGICA ---
        # Força as colunas a existirem no DataFrame, mesmo que o banco não tenha
        colunas_padrao = ["nome", "desconto", "cupom", "link", "ativo"]
        for col in colunas_padrao:
            if col not in df_parc.columns:
                df_parc[col] = "" # Cria coluna vazia na memória
        
        # Limpeza das chaves {} estranhas
        if not df_parc.empty:
            for col in ["nome", "desconto", "cupom", "link"]:
                if col in df_parc.columns:
                    df_parc[col] = df_parc[col].astype(str).str.replace(r'[{}"\']', '', regex=True)

        # 2. FORMULÁRIO DE ADIÇÃO
        with st.expander("➕ Adicionar Novo Parceiro"):
            with st.form("form_add_parceiro", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome_p = c1.text_input("Nome da Loja")
                desc_p = c2.text_input("Desconto (Ex: 10% OFF)")
                
                c3, c4 = st.columns(2)
                cupom_p = c3.text_input("Código do Cupom")
                link_p = c4.text_input("Link do Site")
                
                if st.form_submit_button("Salvar Parceiro", type="primary"):
                    # Só permite salvar se tivermos certeza que a tabela tem a estrutura certa
                    # Por isso avisamos para clicar no Salvar Alterações primeiro se for a primeira vez
                    if nome_p:
                        novo_parc = {
                            "nome": nome_p, "desconto": desc_p, "cupom": cupom_p, 
                            "link": link_p, "ativo": "True"
                        }
                        if salvar_novo_registro(novo_parc, "parceiros"):
                            st.success("Parceiro adicionado com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Erro no Banco. Tente clicar no botão 'Salvar Alterações de Parceiros' abaixo primeiro para corrigir a tabela.")
                    else:
                        st.warning("O nome do parceiro é obrigatório.")

        # 3. TABELA DE EDIÇÃO
        if 'ativo' in df_parc.columns:
            df_parc['ativo'] = df_parc['ativo'].astype(str).str.lower().isin(['true', '1', 'yes', 'on'])

        st.write("📋 **Lista de Parceiros (Edite direto na tabela)**")
        df_parc_ed = st.data_editor(
            df_parc,
            column_config={
                "nome": st.column_config.TextColumn("Nome"),
                "desconto": st.column_config.TextColumn("Desconto"),
                "cupom": st.column_config.TextColumn("Cupom"),
                "link": st.column_config.LinkColumn("Link"),
                "ativo": st.column_config.CheckboxColumn("Ativo?", default=True)
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_parceiros_tab"
        )
        
        if st.button("💾 Salvar Alterações de Parceiros (Clique aqui para Corrigir a Tabela)"):
            # Converte booleano de volta para string antes de salvar
            if 'ativo' in df_parc_ed.columns:
                df_parc_ed['ativo'] = df_parc_ed['ativo'].apply(lambda x: 'True' if x is True else 'False')
            
            # ISSO VAI RE-CRIAR A TABELA COM AS COLUNAS CERTAS (INCLUINDO CUPOM)
            atualizar_tabela_completa(df_parc_ed, "parceiros")
            st.success("Lista de parceiros atualizada e Banco corrigido!")
            time.sleep(1)
            st.rerun()
            
    # --- ABA 6: AULAS (NO BANCO) ---
    with tab_vid:
        st.subheader("Aulas")
        df_v = carregar_dados("videos")
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
                    salvar_novo_registro(nv, "videos")
                    st.success("Adicionado!"); st.rerun()
        
        df_ved = st.data_editor(df_v, num_rows="dynamic", use_container_width=True)
        if st.button("Salvar Vídeos"):
            if not df_ved.empty: df_ved = df_ved.sort_values(by='modulo')
            atualizar_tabela_completa(df_ved, "videos")
            st.success("Salvo no Banco!")
        
    # --- ABA 7: CONFIG (NO BANCO) ---
    with tab_conf:
        st.subheader("⚙️ Configuração API")
        df_conf = carregar_dados("config_api")
        if df_conf.empty: df_conf = pd.DataFrame([{"instancia": "", "token": ""}])
        conf_ed = st.data_editor(df_conf, num_rows=1)
        if st.button("Salvar Config"):
            atualizar_tabela_completa(conf_ed, "config_api")
            st.success("Salvo no Banco!")