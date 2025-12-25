import streamlit as st
import pandas as pd
import os
import altair as alt
from datetime import datetime, date

# --- CONFIGURAÇÃO ---
ARQUIVO_FINANCEIRO = "data/financeiro.csv"
ARQUIVO_USUARIOS = "data/usuarios.csv"

# --- FUNÇÕES ÚTEIS ---
def carregar_dados():
    if not os.path.exists(ARQUIVO_FINANCEIRO):
        df = pd.DataFrame(columns=["data", "tipo", "categoria", "descricao", "valor"])
        return df
    return pd.read_csv(ARQUIVO_FINANCEIRO)

def carregar_pacientes():
    if not os.path.exists(ARQUIVO_USUARIOS):
        return pd.DataFrame()
    return pd.read_csv(ARQUIVO_USUARIOS, dtype=str)

def salvar_dados(df):
    df.to_csv(ARQUIVO_FINANCEIRO, index=False)

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INTERFACE PRINCIPAL ---
def show_financeiro():
    st.title("💰 Gestão Financeira & Métricas")
    
    # 1. LANÇAMENTO DE CAIXA (FORA DO FORM PARA SER DINÂMICO)
    with st.expander("➕ Novo Lançamento (Receita ou Despesa)", expanded=False):
        
        # Colunas fora do form para atualizar interativamente
        c_tipo, c_cat = st.columns(2)
        
        # O radio agora tem uma key e atualiza a página ao mudar
        tipo_selecionado = c_tipo.radio(
            "Tipo de Lançamento", 
            ["Receita (Entrada)", "Despesa (Saída)"], 
            horizontal=True
        )
        
        # Define as categorias com base na escolha acima (Dinâmico)
        if "Receita" in tipo_selecionado:
            opcoes_cat = ["Plano Mensal", "Plano Trimestral", "Plano Semestral", "Renovação (mensal)", "Renovação (trimestral)", "Renovação (semestral)", "Outros"]
            tipo_clean = "Receita"
        else:
            opcoes_cat = ["Marketing/Ads", "Ferramentas/Software", "Aluguel/Fixo", "Impostos", "Pró-labore", "Outros"]
            tipo_clean = "Despesa"
            
        categoria_selecionada = c_cat.selectbox("Categoria", opcoes_cat)

        # O restante fica no form para agrupar o envio
        with st.form("form_financas_dados"):
            c1, c2, c3 = st.columns([1, 2, 1])
            data_lanc = c1.date_input("Data", date.today())
            descricao = c2.text_input("Descrição (Ex: Nome do Paciente - Parcela/Inteiro)")
            valor = c3.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")
            
            if st.form_submit_button("💾 Confirmar Lançamento", type="primary", use_container_width=True):
                if valor > 0:
                    df_atual = carregar_dados()
                    novo = {
                        "data": str(data_lanc),
                        "tipo": tipo_clean,
                        "categoria": categoria_selecionada,
                        "descricao": descricao,
                        "valor": valor
                    }
                    df_final = pd.concat([df_atual, pd.DataFrame([novo])], ignore_index=True)
                    salvar_dados(df_final)
                    st.success("Registrado com sucesso!")
                    st.rerun()
                else:
                    st.warning("O valor deve ser maior que zero.")

    # 2. PROCESSAMENTO DE DADOS
    df = carregar_dados()
    df_pacientes = carregar_pacientes()
    
    # Conta apenas pacientes (exclui admin)
    qtd_pacientes = 0
    if not df_pacientes.empty:
        qtd_pacientes = len(df_pacientes[df_pacientes['role'] == 'paciente'])

    if df.empty:
        st.info("Comece lançando suas receitas e despesas acima para ver os gráficos.")
        return

    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    
    # Ordena por data (mais recente primeiro) e reseta o índice para facilitar exclusão
    df = df.sort_values('data', ascending=False).reset_index(drop=True)

    # Filtros
    col_filtro, col_vazio = st.columns([1, 3])
    with col_filtro:
        df['mes_ano'] = df['data'].dt.strftime('%Y-%m')
        meses = df['mes_ano'].unique().tolist()
        mes_selecionado = st.selectbox("📅 Filtrar Período:", ["Todos"] + meses)

    df_view = df.copy()
    if mes_selecionado != "Todos":
        df_view = df[df['mes_ano'] == mes_selecionado]

    # 3. KPIs GERAIS ( Fluxo de Caixa )
    receitas = df_view[df_view['tipo'] == 'Receita']['valor'].sum()
    despesas = df_view[df_view['tipo'] == 'Despesa']['valor'].sum()
    saldo = receitas - despesas

    # 4. CÁLCULO DE LTV e CAC (Considera SEMPRE o histórico todo)
    receita_total_historica = df[df['tipo'] == 'Receita']['valor'].sum()
    investimento_mkt_historico = df[(df['tipo'] == 'Despesa') & (df['categoria'] == 'Marketing/Ads')]['valor'].sum()
    
    ltv = receita_total_historica / qtd_pacientes if qtd_pacientes > 0 else 0
    cac = investimento_mkt_historico / qtd_pacientes if qtd_pacientes > 0 else 0
    roi = ((receita_total_historica - investimento_mkt_historico) / investimento_mkt_historico * 100) if investimento_mkt_historico > 0 else 0

    st.markdown("### 📊 Indicadores Financeiros")
    
    # Linha 1: Caixa do Mês
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Entradas", formatar_moeda(receitas), border=True)
    k2.metric("💸 Saídas", formatar_moeda(despesas), f"-{despesas:.2f}", delta_color="inverse", border=True)
    k3.metric("⚖️ Lucro Líquido", formatar_moeda(saldo), f"{saldo:.2f}", border=True)
    k4.metric("👥 Pacientes Ativos", f"{qtd_pacientes}", border=True)

    st.markdown("---")
    st.markdown("### 🧠 Inteligência de Negócio (Histórico)")
    
    # Linha 2: Métricas Estratégicas
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("💎 LTV (Valor Vitalício)", formatar_moeda(ltv), help="Média de quanto cada paciente já gastou com você.")
        st.caption(f"Cada paciente vale em média **{formatar_moeda(ltv)}**.")
    with m2:
        st.metric("📢 CAC (Custo Aquisição)", formatar_moeda(cac), f"-{cac:.2f}", delta_color="inverse", help="Quanto gasta em MKT para trazer 1 paciente.")
        st.caption("Custo 'Marketing/Ads' / Total Pacientes")
    with m3:
        st.metric("🚀 ROI Marketing", f"{roi:.0f}%", help="Retorno sobre anúncios.")
        ratio = ltv / cac if cac > 0 else 0
        st.caption(f"Relação LTV/CAC: **{ratio:.1f}x** (Ideal > 3x)")

    # 5. SIMULADOR DE METAS
    with st.expander("🧮 Simulador de Metas (Brinque com os números)", expanded=False):
        st.write("Quanto você quer faturar por mês?")
        s1, s2 = st.columns(2)
        meta_fat = s1.number_input("Meta de Faturamento (R$)", value=5000.0, step=500.0)
        ticket_medio = s2.number_input("Valor Médio da Consulta/Plano (R$)", value=250.0, step=10.0)
        
        pacientes_necessarios = meta_fat / ticket_medio if ticket_medio > 0 else 0
        st.info(f"🎯 Para faturar **{formatar_moeda(meta_fat)}**, você precisa de **{int(pacientes_necessarios)} pacientes** pagando {formatar_moeda(ticket_medio)}.")

    st.markdown("---")

    # 6. GRÁFICOS
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("Fluxo de Caixa")
        if not df.empty:
            df_chart = df.copy()
            df_chart['mes'] = df_chart['data'].dt.strftime('%Y-%m')
            chart_data = df_chart.groupby(['mes', 'tipo'])['valor'].sum().reset_index()
            
            c = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('mes', title='Mês'),
                y=alt.Y('valor', title='Reais (R$)'),
                color=alt.Color('tipo', scale=alt.Scale(domain=['Receita', 'Despesa'], range=['#2ECC71', '#E74C3C'])),
                tooltip=['mes', 'tipo', 'valor']
            ).interactive()
            st.altair_chart(c, use_container_width=True)

    with col_g2:
        st.subheader("Despesas por Categoria")
        df_desp = df_view[df_view['tipo'] == 'Despesa']
        if not df_desp.empty:
            df_pie = df_desp.groupby('categoria')['valor'].sum().reset_index()
            pie = alt.Chart(df_pie).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field="valor", type="quantitative"),
                color=alt.Color(field="categoria", type="nominal"),
                tooltip=['categoria', 'valor']
            )
            st.altair_chart(pie, use_container_width=True)
        else:
            st.caption("Sem despesas registradas no período.")

    # 7. TABELA DE EXTRATO
    st.subheader("📝 Extrato de Lançamentos")
    df_edit = df_view.copy()
    df_edit['data'] = df_edit['data'].dt.date
    
    df_final_edit = st.data_editor(
        df_edit[['data', 'tipo', 'categoria', 'descricao', 'valor']],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "tipo": st.column_config.SelectboxColumn("Tipo", options=["Receita", "Despesa"]),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=[
                "Consulta Avulsa", "Plano Mensal", "Plano Trimestral", "Renovação", 
                "Marketing/Ads", "Ferramentas/Software", "Aluguel/Fixo", "Impostos", "Outros"
            ])
        }
    )

    if st.button("💾 Salvar Alterações na Tabela"):
        if mes_selecionado == "Todos":
            salvar_dados(df_final_edit)
            st.success("Tabela atualizada!")
            st.rerun()
        else:
            st.warning("Para editar, selecione o filtro 'Todos' nos meses.")

    # 8. OPÇÃO DE EXCLUSÃO (NOVA)
    st.markdown("---")
    with st.expander("🗑️ Excluir Lançamento Específico"):
        if not df_view.empty:
            st.warning("Cuidado: Esta ação não pode ser desfeita.")
            
            # Cria lista legível usando o índice original para garantir exclusão correta
            opcoes_exclusao = df_view.apply(
                lambda x: f"{x['data'].strftime('%d/%m/%Y')} | {x['tipo']} | {x['descricao']} | R$ {x['valor']:.2f}", 
                axis=1
            ).to_dict()
            
            id_para_excluir = st.selectbox(
                "Selecione o lançamento para apagar:", 
                options=list(opcoes_exclusao.keys()),
                format_func=lambda x: opcoes_exclusao[x]
            )
            
            if st.button("❌ Confirmar Exclusão do Lançamento"):
                # Remove pelo índice
                df_novo = df.drop(id_para_excluir)
                salvar_dados(df_novo)
                st.success("Lançamento removido com sucesso!")
                st.rerun()
        else:
            st.info("Não há lançamentos visíveis para excluir.")