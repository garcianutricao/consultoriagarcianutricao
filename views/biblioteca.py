import streamlit as st
import os
import pandas as pd
import fitz  # PyMuPDF
from streamlit_pdf_viewer import pdf_viewer

PASTA_EBOOKS = "assets/ebooks"
ARQUIVO_PARCEIROS = "data/parceiros.csv"
ARQUIVO_VIDEOS = "data/videos.csv"

# --- CACHE DE ALTA RESOLUÇÃO ---
@st.cache_data
def gerar_capa_thumbnail(caminho_arquivo):
    try:
        doc = fitz.open(caminho_arquivo)
        pagina = doc.load_page(0)
        pix = pagina.get_pixmap(matrix=fitz.Matrix(3, 3)) 
        return pix.tobytes("png")
    except:
        return None

def show_biblioteca():
    if "livro_aberto" not in st.session_state:
        st.session_state["livro_aberto"] = None

    # ==========================================
    # MODO LEITURA
    # ==========================================
    if st.session_state["livro_aberto"]:
        caminho_livro = st.session_state["livro_aberto"]
        nome_livro = os.path.basename(caminho_livro).replace(".pdf", "").replace("_", " ").title()
        
        col1, col2 = st.columns([1, 6])
        with col1:
            if st.button("⬅️ Voltar"):
                st.session_state["livro_aberto"] = None
                st.rerun()
        with col2:
            st.markdown(f"### 📖 Lendo: {nome_livro}")
            
        st.markdown("---")

        col_aviso, col_btn_down = st.columns([3, 1])
        with col_aviso:
            st.info("ℹ️ **Dica:** Para usar os links clicáveis, faça o download.")
        with col_btn_down:
            with open(caminho_livro, "rb") as f:
                st.download_button("⬇️ Baixar PDF", f, file_name=os.path.basename(caminho_livro), mime="application/pdf", type="primary", use_container_width=True)

        try:
            pdf_viewer(input=caminho_livro, width=700, height=900)
        except Exception as e:
            st.error("Erro ao visualizar.")

        st.markdown("---")
        if st.button("⬅️ Fechar Leitura"):
            st.session_state["livro_aberto"] = None
            st.rerun()
            
        return

    # ==========================================
    # MODO NAVEGAÇÃO
    # ==========================================
    st.title("📚 Materiais úteis.")
    
    tab1, tab_videos, tab2 = st.tabs(["📖 Ebooks", "▶️ Aulas", "🏷️ Cupons de desconto"])

    # --- ABA 1: EBOOKS ---
    with tab1:
        st.subheader("Seus Manuais")
        
        if not os.path.exists(PASTA_EBOOKS):
            st.warning("Pasta de ebooks vazia.")
        else:
            pdfs = [f for f in os.listdir(PASTA_EBOOKS) if f.lower().endswith('.pdf')]
            
            if not pdfs:
                st.info("Nenhum ebook disponível.")
            else:
                cols = st.columns(5) 
                
                for i, arquivo_pdf in enumerate(pdfs):
                    with cols[i % 5]: 
                        with st.container(): 
                            caminho_pdf = os.path.join(PASTA_EBOOKS, arquivo_pdf)
                            img_bytes = gerar_capa_thumbnail(caminho_pdf)
                            
                            if img_bytes:
                                st.image(img_bytes, use_container_width=True)
                            else:
                                st.image("https://placehold.co/600x900?text=Capa", use_container_width=True)

                            nome_bonito = arquivo_pdf.replace(".pdf", "").replace("_", " ").title()
                            st.markdown(f"<div style='text-align:center; font-size:12px; font-weight:bold; margin-bottom:5px'>{nome_bonito}</div>", unsafe_allow_html=True)
                            
                            if st.button("Ler", key=f"ler_{arquivo_pdf}", use_container_width=True):
                                st.session_state["livro_aberto"] = caminho_pdf
                                st.rerun()
                        st.write("")

    # --- ABA 2: AULAS (COM ANIMAÇÃO SUAVE) ---
    with tab_videos:
        st.subheader("🎓 Área de Aprendizado")
        
        try:
            df_videos = pd.read_csv(ARQUIVO_VIDEOS)
            
            ordem_modulos = [
                "Instruções Iniciais", 
                "O Processo de Emagrecimento", 
                "Evolução",
                "Mentoria Gravada",
                "Outros"
            ]
            
            modulos_existentes = [m for m in ordem_modulos if m in df_videos['modulo'].unique()]
            extras = [m for m in df_videos['modulo'].unique() if m not in ordem_modulos and m != "Boas Vindas"]
            lista_final_modulos = modulos_existentes + extras

            if not lista_final_modulos:
                st.info("Nenhuma aula cadastrada.")
            else:
                col_menu, col_conteudo = st.columns([1, 3])
                
                with col_menu:
                    st.markdown("### 📂 Módulos")
                    modulo_escolhido = st.radio(
                        "Navegue pelos módulos:",
                        options=lista_final_modulos,
                        label_visibility="collapsed"
                    )
                
                with col_conteudo:
                    # --- AQUI ESTÁ A MÁGICA DA ANIMAÇÃO ---
                    # Injetamos um CSS específico que afeta os elementos dessa coluna
                    st.markdown("""
                        <style>
                        /* Animação para os itens que aparecem na área de conteúdo */
                        div[data-testid="stVerticalBlock"] > div.element-container {
                            animation: fadeInUp 0.5s ease-out;
                        }
                        
                        @keyframes fadeInUp {
                            from {
                                opacity: 0;
                                transform: translate3d(0, 15px, 0); /* Vem um pouco de baixo */
                            }
                            to {
                                opacity: 1;
                                transform: translate3d(0, 0, 0);
                            }
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    # ----------------------------------------

                    st.markdown(f"## {modulo_escolhido}")
                    st.markdown("---")
                    
                    videos_do_modulo = df_videos[df_videos['modulo'] == modulo_escolhido]
                    
                    if videos_do_modulo.empty:
                        st.info("Nenhum vídeo neste módulo.")
                    else:
                        grid_videos = st.columns(2)
                        for idx, row in videos_do_modulo.reset_index().iterrows():
                            with grid_videos[idx % 2]:
                                # Container para agrupar visualmente o card do vídeo
                                with st.container():
                                    st.markdown(f"**{row['titulo']}**")
                                    st.video(row['link'])
                                    if pd.notna(row['descricao']):
                                        st.caption(row['descricao'])
                                    st.write("") 

        except FileNotFoundError:
            st.warning("Base de vídeos não encontrada.")

    # --- ABA 3: PARCEIROS ---
    with tab2:
        st.subheader("Descontos Exclusivos")
        try:
            df = pd.read_csv(ARQUIVO_PARCEIROS)
            df['ativo'] = df['ativo'].astype(str).str.lower()
            df = df[df['ativo'].isin(['true', '1', 'yes'])]
            
            for index, row in df.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 3, 2])
                    with c1: st.markdown("## 🏷️")
                    with c2:
                        st.markdown(f"**{row['nome']}**")
                        st.caption(row['descricao'])
                    with c3:
                        st.code(row['cupom'], language="text")
                        if str(row['link']) != "nan": st.link_button("Ir para Loja", row['link'], use_container_width=True)
        except:
            st.info("Nenhum parceiro cadastrado.")