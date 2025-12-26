import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
# IMPORTS DO BANCO DE DADOS
from database import carregar_dados, salvar_novo_registro

# --- CONFIGURAÇÃO ---
# Mantemos apenas o arquivo de configuração das perguntas
ARQUIVO_PERGUNTAS = "data/perguntas_checkin.csv"

# --- FUNÇÕES ---

def get_dados_paciente(username):
    # LÊ DO BANCO
    df = carregar_dados("usuarios")
    if df.empty: return None
    
    # Tratamento seguro de strings
    if 'username' in df.columns:
        df['username_clean'] = df['username'].astype(str).str.strip().str.lower()
        busca = str(username).strip().lower()
        
        user = df[df['username_clean'] == busca]
        if user.empty: return None
        return user.iloc[0].to_dict()
    return None

def get_historico_checkins(username):
    # LÊ DO BANCO
    df = carregar_dados("checkins")
    if df.empty: return pd.DataFrame()
    
    if 'username' in df.columns:
        return df[df['username'] == username]
    return pd.DataFrame()

def renderizar_campo(row, prefixo=""):
    """Gera o componente visual com chave única para evitar erros de ID"""
    tipo = str(row['tipo']).lower().strip()
    label = row['pergunta']
    id_campo = f"{prefixo}{row['id']}" # Chave única
    
    opcoes = []
    if pd.notnull(row['opcoes']) and str(row['opcoes']).strip():
        opcoes = str(row['opcoes']).split("|")
    
    val = None
    if tipo == "texto_curto": val = st.text_input(label, key=id_campo)
    elif tipo == "texto_longo": val = st.text_area(label, key=id_campo)
    elif tipo == "numero": val = st.number_input(label, min_value=0.0, format="%.2f", key=id_campo)
    elif tipo == "radio": val = st.radio(label, options=opcoes, key=id_campo)
    elif tipo == "selectbox": val = st.selectbox(label, options=opcoes, key=id_campo)
    elif tipo == "slider":
        max_val = 10
        if opcoes:
            try: max_val = int(opcoes[0].split("-")[1])
            except: pass
        val = st.slider(label, 0, max_val, 0, key=id_campo)
    elif tipo == "escala (1-10)":
        val = st.slider(label, 1, 10, 5, key=id_campo)
    elif tipo == "sim/não":
        val = st.radio(label, ["Sim", "Não"], horizontal=True, key=id_campo)
        
    return val

# --- TELA PRINCIPAL ---
def show_checkin():
    st.title("📝 Check-in")
    st.markdown("---")

    usuario_atual = st.session_state.get("usuario_atual")
    role = st.session_state.get("role")
    
    if not usuario_atual:
        st.error("Sessão expirada. Por favor, faça login novamente.")
        return

    # --- MODO ADMIN (PREVIEW) ---
    if role == "admin":
        st.warning("👁️ **Modo Visualização (Admin):** Você está vendo o formulário como seu paciente vê.")
        
        if not os.path.exists(ARQUIVO_PERGUNTAS):
            st.error("⚠️ O arquivo de perguntas não foi encontrado em 'data/perguntas_checkin.csv'.")
            return
            
        df_perguntas = pd.read_csv(ARQUIVO_PERGUNTAS)
        if df_perguntas.empty:
            st.info("ℹ️ O formulário está configurado, mas não contém perguntas.")
            return

        with st.form("preview_admin"):
            st.subheader("Prévia do Formulário")
            respostas_mock = {}
            
            # Renderização idêntica ao paciente
            if 'categoria' in df_perguntas.columns:
                categorias = sorted(df_perguntas['categoria'].unique())
                for cat in categorias:
                    st.markdown(f"### {cat}")
                    df_cat = df_perguntas[df_perguntas['categoria'] == cat]
                    for _, row in df_cat.iterrows():
                        respostas_mock[row['id']] = renderizar_campo(row, prefixo="adm_")
                    st.markdown("---")
            else:
                for _, row in df_perguntas.iterrows():
                    respostas_mock[row['id']] = renderizar_campo(row, prefixo="adm_")
            
            st.form_submit_button("Testar Envio (Não salva no banco de dados)")
        return

    # --- MODO PACIENTE ---
    info_paciente = get_dados_paciente(usuario_atual)
    if not info_paciente: 
        st.error("Erro ao carregar dados do usuário. Contate o suporte.")
        return

    # Lógica de bloqueio por data/frequência
    dia_agendado = str(info_paciente.get('dia_checkin', 'Segunda')).strip()
    frequencia = str(info_paciente.get('frequencia', 'Semanal')).strip()
    
    data_str = str(info_paciente.get('data_inicio', date.today())).strip()
    try: data_inicio = datetime.strptime(data_str, "%Y-%m-%d").date()
    except: data_inicio = date.today()

    dias_semana = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
    hoje = datetime.now().date()
    hoje_nome = dias_semana[hoje.weekday()]

    df_checks = get_historico_checkins(usuario_atual)
    total_feitos = len(df_checks)

    bloqueado = False
    motivo = ""
    mostrar_info_azul = True

    if hoje_nome != dia_agendado:
        bloqueado = True
        motivo = f"Hoje é **{hoje_nome}**. Seu dia de check-in é **{dia_agendado}**."
        if total_feitos == 0: mostrar_info_azul = False
    else:
        dias_de_plano = (hoje - data_inicio).days
        if dias_de_plano < 0: dias_de_plano = 0

        if total_feitos == 0:
            periodo = 7 if frequencia == "Semanal" else 15
            if dias_de_plano < periodo:
                bloqueado = True
                motivo = f"⏳ **Aguarde!** Seu primeiro check-in será liberado em {periodo - dias_de_plano} dias."
                mostrar_info_azul = False
        else:
            if 'data' in df_checks.columns:
                df_checks['data_real'] = pd.to_datetime(df_checks['data'], errors='coerce')
                ultimo_check = df_checks['data_real'].max().date()
                dias_desde_ultimo = (hoje - ultimo_check).days
                
                periodo_trava = 6 if frequencia == "Semanal" else 13
                if dias_desde_ultimo < periodo_trava:
                    bloqueado = True
                    motivo = f"✅ Você já realizou seu check-in {frequencia.lower()}!"

    if bloqueado:
        st.error(motivo)
        if mostrar_info_azul:
            st.info(f"Frequência: {frequencia} | Início do Plano: {data_inicio.strftime('%d/%m/%Y')}")
    else:
        st.success(f"🔓 Check-in Liberado! ({frequencia})")
        
        if not os.path.exists(ARQUIVO_PERGUNTAS):
            st.warning("⚠️ O formulário de perguntas ainda não foi configurado pelo nutricionista.")
            return
            
        df_perguntas = pd.read_csv(ARQUIVO_PERGUNTAS)
        if df_perguntas.empty:
            st.warning("O formulário de perguntas está vazio.")
            return

        with st.form("form_checkin_dinamico"):
            respostas = {
                "username": usuario_atual,
                "data": str(date.today()),
                "status": "Pendente"
            }
            
            c1, c2 = st.columns(2)
            c1.text_input("Paciente", value=st.session_state.get('nome', usuario_atual), disabled=True)
            c2.text_input("Data de Envio", value=datetime.now().strftime("%d/%m/%Y"), disabled=True)
            
            st.markdown("---")
            
            # Renderiza perguntas
            if 'categoria' in df_perguntas.columns:
                categorias = sorted(df_perguntas['categoria'].unique())
                for cat in categorias:
                    st.subheader(cat)
                    df_cat = df_perguntas[df_perguntas['categoria'] == cat]
                    for _, row in df_cat.iterrows():
                        respostas[row['id']] = renderizar_campo(row, prefixo="pac_")
                    st.markdown("---")
            else:
                for _, row in df_perguntas.iterrows():
                    respostas[row['id']] = renderizar_campo(row, prefixo="pac_")

            if st.form_submit_button("✅ Enviar Relatório", type="primary", use_container_width=True):
                # Validação básica
                if 'peso' in respostas and (respostas['peso'] is None or float(respostas['peso']) <= 0):
                    st.warning("Por favor, preencha o seu peso atual corretamente.")
                else:
                    # SALVA NO BANCO POSTGRESQL
                    if salvar_novo_registro(respostas, "checkins"):
                        st.balloons()
                        st.success("Relatório enviado com sucesso! Aguarde o feedback do seu nutricionista.")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar o check-in. Tente novamente.")