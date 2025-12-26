import streamlit as st
import pandas as pd
import os

# --- CONFIGURAÇÃO DO ARQUIVO ---
# Mantemos o Excel pois é uma base de dados estática (apenas leitura)
CAMINHO_TABELA = "data/tabela_alimentoseutaco.xlsx"

# --- FUNÇÃO PARA TRADUZIR OS GRUPOS ---
def normalizar_grupo(nome_grupo):
    """
    Padroniza os nomes dos grupos do Excel para 4 categorias principais.
    """
    # Converte para texto, minúsculo e remove espaços
    g = str(nome_grupo).lower().strip()
    
    # ORDEM DE VERIFICAÇÃO IMPORTA!
    
    # 1. Frutas
    if 'fruta' in g:
        return 'Fruta'
    
    # 2. Gorduras
    elif any(x in g for x in ['gord', 'lip', 'oleo', 'óleo', 'azeite', 'castanha', 'noze', 'manteiga', 'amendoim']):
        return 'Gordura'
    
    # 3. Proteínas
    elif any(x in g for x in ['prot', 'carne', 'ovo', 'ave', 'peixe', 'leite', 'queijo', 'frio', 'iogurte']):
        return 'Proteína'
    
    # 4. Carboidratos
    elif any(x in g for x in ['carbo', 'cereal', 'massa', 'pão', 'raiz', 'tuberculo', 'leguminosa', 'farinha', 'bisc', 'bolo']):
        return 'Carboidrato'
    
    # 5. Se não achou nada
    else:
        return 'Outros'

# --- CARREGAMENTO DE DADOS (COM CACHE) ---
@st.cache_data
def carregar_dados_alimentos():
    if not os.path.exists(CAMINHO_TABELA):
        return pd.DataFrame()
    
    try:
        # Lê o Excel usando openpyxl (engine padrão para xlsx)
        df = pd.read_excel(CAMINHO_TABELA, engine='openpyxl')
        
        # 1. Limpeza de colunas
        df.columns = df.columns.str.strip()
        
        # 2. Renomeia colunas para facilitar o código
        mapa_colunas = {
            'Alimento': 'alimento',
            'Grupo': 'grupo',
            'Kcal': 'calorias',      
            'Proteína': 'proteina',  
            'Carboidrato': 'carboidrato',
            'Gordura': 'gordura'
        }
        df = df.rename(columns=mapa_colunas)
        
        # 3. Conversão Numérica (Segurança contra textos escondidos nas colunas de números)
        cols_numericas = ['calorias', 'proteina', 'carboidrato', 'gordura']
        for col in cols_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 4. CRIAÇÃO DO GRUPO SIMPLIFICADO
        if 'grupo' in df.columns:
            df['grupo_display'] = df['grupo'].apply(normalizar_grupo)
            # Remove "Outros" para não sujar o menu com alimentos irrelevantes
            df = df[df['grupo_display'] != 'Outros']
            
        return df
        
    except Exception as e:
        st.error(f"Erro ao ler tabela nutricional: {e}")
        return pd.DataFrame()

# ==========================================
# VIEW DA CALCULADORA
# ==========================================
def show_calculadora():
    st.title("🧮 Calculadora de Substituição")
    st.caption("Planeje suas trocas mantendo o equilíbrio calórico.")
    st.markdown("---")

    df_alimentos = carregar_dados_alimentos()

    if df_alimentos.empty:
        st.error(f"⚠️ Erro ao carregar a tabela de alimentos. Verifique se o arquivo '{CAMINHO_TABELA}' está na pasta data e se a biblioteca 'openpyxl' está instalada.")
        return

    # --- INTERFACE ---
    col_input, col_resultado = st.columns([1.5, 2], gap="large")

    with col_input:
        st.subheader("Alimento que tem na dieta")
        
        # 1. Filtra Grupos
        ordem_desejada = ['Carboidrato', 'Fruta', 'Gordura', 'Proteína']
        grupos_no_excel = df_alimentos['grupo_display'].unique() if 'grupo_display' in df_alimentos.columns else []
        
        # Cria a lista final apenas com os grupos que realmente existem
        grupos_finais = [g for g in ordem_desejada if g in grupos_no_excel]
        
        if not grupos_finais:
            st.warning("Não foi possível identificar os grupos. Verifique se o Excel tem a coluna 'Grupo'.")
            st.stop()
            
        grupo_sel = st.selectbox("Grupo Alimentar", options=grupos_finais)
        
        # 2. Filtra Alimentos
        df_grupo = df_alimentos[df_alimentos['grupo_display'] == grupo_sel].sort_values('alimento')
        alimentos_disponiveis = df_grupo['alimento'].unique()
        
        alimento_base_nome = st.selectbox("Alimento da Dieta", options=alimentos_disponiveis)
        
        # 3. Quantidade
        qtd_base = st.number_input(f"Quantidade (g)", min_value=0.0, value=100.0, step=10.0)
        
        st.markdown("⬇️ **Trocar por:**")
        
        # 4. Alimento Alvo (Mesmo Grupo)
        alimentos_alvo_lista = [a for a in alimentos_disponiveis if a != alimento_base_nome]
        alimento_alvo_nome = st.selectbox("Alimento Substituto", options=alimentos_alvo_lista)

    # --- CÁLCULOS ---
    if alimento_base_nome and alimento_alvo_nome:
        dados_base = df_alimentos[df_alimentos['alimento'] == alimento_base_nome].iloc[0]
        dados_alvo = df_alimentos[df_alimentos['alimento'] == alimento_alvo_nome].iloc[0]

        # Calorias
        calorias_totais_base = (qtd_base * dados_base['calorias']) / 100

        if dados_alvo['calorias'] > 0:
            qtd_final = (calorias_totais_base * 100) / dados_alvo['calorias']
        else:
            qtd_final = 0 

        # Macros
        if grupo_sel == 'Proteína':
            macro_foco = 'proteina'
            label_macro = "Proteína"
        elif grupo_sel == 'Gordura':
            macro_foco = 'gordura'
            label_macro = "Gordura"
        else:
            macro_foco = 'carboidrato'
            label_macro = "Carboidrato"

        qtd_macro_base = (qtd_base * dados_base[macro_foco]) / 100
        qtd_macro_novo = (qtd_final * dados_alvo[macro_foco]) / 100
        dif_macro = qtd_macro_novo - qtd_macro_base

        # --- EXIBIÇÃO ---
        with col_resultado:
            st.subheader("⚖️ Resultado")
            
            with st.container(border=True):
                st.markdown(f"Para consumir as mesmas **{calorias_totais_base:.0f} kcal**, você precisa de:")
                
                st.markdown(
                    f"""
                    <div style="font-size: 35px; font-weight: 800; color: #4CAF50; margin: 10px 0;">
                        {qtd_final:.0f} g
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                st.markdown(f"de {alimento_alvo_nome}")
                
                st.markdown("---")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(f"{label_macro} Original", f"{qtd_macro_base:.1f} g")
                with c2:
                    st.metric(f"Variação de {label_macro}", f"{qtd_macro_novo:.1f} g", f"{dif_macro:.1f} g")

            with st.expander("Ver Tabela Nutricional Completa"):
                comp_df = pd.DataFrame({
                    "Nutriente": ["Calorias (kcal)", "Carboidrato (g)", "Proteína (g)", "Gordura (g)"],
                    f"Origem ({qtd_base:.0f}g)": [
                        calorias_totais_base, 
                        (qtd_base * dados_base['carboidrato'])/100,
                        (qtd_base * dados_base['proteina'])/100,
                        (qtd_base * dados_base['gordura'])/100
                    ],
                    f"Troca ({qtd_final:.0f}g)": [
                        calorias_totais_base,
                        (qtd_final * dados_alvo['carboidrato'])/100,
                        (qtd_final * dados_alvo['proteina'])/100,
                        (qtd_final * dados_alvo['gordura'])/100
                    ]
                })
                st.dataframe(comp_df.style.format(precision=1), hide_index=True, use_container_width=True)