import os
import shutil
import re
import time
import csv
import urllib.parse
from datetime import datetime, timedelta, date
import streamlit as st
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager


# ========================
# FUNÇÕES DE BACKEND (BASEADAS NO SEU CÓDIGO)
# ========================


def criar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # Adicione esta linha abaixo para disfarçar o robô:
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    # Busca os caminhos do navegador e do driver no servidor Linux
    chrome_path = shutil.which("chromium") or shutil.which("google-chrome")
    driver_path = shutil.which("chromedriver")

    if chrome_path and driver_path:
        # Configuração para o Streamlit Cloud (usa o que está no packages.txt)
        options.binary_location = chrome_path
        service = Service(driver_path)
    else:
        # Configuração fallback para rodar no seu computador local
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def esperar_clicavel(driver, by, locator, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, locator))
    )


def clicar_js(driver, elemento):
    driver.execute_script("arguments[0].click();", elemento)


def fechar_popups(driver):
    try:
        btn_aceitar = esperar_clicavel(
            driver,
            By.XPATH,
            "//button[contains(., 'Aceitar tudo') or contains(., 'Accept all')]",
            timeout=5,
        )
        clicar_js(driver, btn_aceitar)
        time.sleep(1)
    except:
        pass


def filtrar_uma_escala(driver):
    try:
        btn_escalas = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'Escalas') or contains(., 'Paradas') or contains(., 'Stops')]",
                )
            )
        )
        clicar_js(driver, btn_escalas)
        time.sleep(2)
        opcao_1_escala = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//*[contains(text(), '1 parada') or contains(text(), '1 escala') or contains(text(), '1 stop')]",
                )
            )
        )
        clicar_js(driver, opcao_1_escala)
        time.sleep(1.5)
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(4)
        return True
    except Exception:
        return False


def coletar_resultados(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), 'R$')]")
            )
        )
        time.sleep(4)

        # ATUALIZAÇÃO: O Google agora usa div com role='listitem' em vez de li
        cards = driver.find_elements(
            By.XPATH,
            "//div[@role='listitem' and .//*[contains(text(), 'R$')]]"
        )

        return [card.text.strip() for card in cards if card.text.strip()]
    except Exception:
        return []

def extrair_dados_voos(textos, conexao, data_voo):
    resultados = []
    mapa_siglas = {
        "fortaleza": "FOR",
        "brasilia": "BSB",
        "salvador": "SSA",
        "recife": "REC",
        "sao paulo": "GRU",
        "guarulhos": "GRU",
        "congonhas": "CGH",
        "campinas": "VCP",
        "rio de janeiro": "GIG",
        "galeao": "GIG",
        "santos dumont": "SDU",
        "belo horizonte": "CNF",
        "confins": "CNF",
        "goiania": "GYN",
        "manaus": "MAO",
        "belem": "BEL",
        "curitiba": "CWB",
        "porto alegre": "POA",
        "florianopolis": "FLN",
        "vitoria": "VIX",
        "natal": "NAT",
        "sao luis": "SLZ",
        "maceio": "MCZ",
        "joao pessoa": "JPA",
        "aracaju": "AJU",
        "teresina": "THE",
        "campo grande": "CGR",
        "cuiaba": "CGB",
        "palmas": "PMW",
        "porto velho": "PVH",
        "rio branco": "RBR",
        "boa vista": "BVB",
        "macapa": "MCP",
    }

    conexao_limpa = (
        conexao.lower()
        .strip()
        .replace("ã", "a")
        .replace("õ", "o")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í",",","i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ç", "c")
        .replace("â", "a")
        .replace("ê", "e")
        .replace("ô", "o")
    )
    sigla_conexao = mapa_siglas.get(conexao_limpa, conexao.upper()[:3])
    data_formatada = datetime.strptime(data_voo, "%Y-%m-%d").strftime("%d/%m/%Y")

    for texto in textos:
        texto_upper = texto.upper()
        if sigla_conexao not in texto_upper and conexao.upper() not in texto_upper:
            continue

        companhia = "Desconhecida"
        for cia in ["LATAM", "GOL", "AZUL", "VOEPASS"]:
            if cia in texto_upper:
                companhia = cia.capitalize()
                break

        preco_match = re.search(r"R\$\s*[\d.,]+", texto)
        preco = preco_match.group(0) if preco_match else "Não disponível"

        duracao_match = re.search(r"\d+\s*h\s*\d*\s*min", texto)
        duracao = duracao_match.group(0) if duracao_match else "Não disponível"

        horarios = re.findall(r"\d{1,2}:\d{2}", texto)
        partida = horarios[0] if len(horarios) > 0 else "N/A"
        chegada = horarios[1] if len(horarios) > 1 else "N/A"

        resultados.append(
            {
                "data_voo": data_formatada,
                "companhia": companhia,
                "preco": preco,
                "duracao": duracao,
                "escalas": f"1 parada em {sigla_conexao}",
                "partida": partida,
                "chegada": chegada,
                "detalhes": texto.replace("\n", " | "),
            }
        )
    return resultados


def salvar_resultados(resultados, conexao):
    if not resultados:
        return 0, None, None

    melhor_voo_info = None
    caminho_arquivo = None

    try:
        for r in resultados:
            preco_bruto = r.get("preco", "")
            preco_limpo = (
                preco_bruto.replace("R$", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )
            r["_preco_num"] = float(preco_limpo)

        menor_preco = min(r["_preco_num"] for r in resultados)

        for r in resultados:
            r["Destaque"] = "⭐ MAIS BARATO" if r["_preco_num"] == menor_preco else ""

        voo_mais_barato = min(resultados, key=lambda x: x["_preco_num"])

        melhor_voo_info = {
            "preco": voo_mais_barato["preco"],
            "data": voo_mais_barato["data_voo"],
            "cia": voo_mais_barato["companhia"],
        }

        def chave_ordem(r):
            try:
                data = datetime.strptime(r["data_voo"], "%d/%m/%Y")
            except Exception:
                data = datetime.max
            return (data, r["_preco_num"])

        resultados.sort(key=chave_ordem)

    except:
        pass

    colunas = [
        "Destaque",
        "data_voo",
        "companhia",
        "preco",
        "duracao",
        "escalas",
        "partida",
        "chegada",
        "detalhes",
    ]

    nome_arquivo = f"voos_conexao_{conexao}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    caminho_arquivo = os.path.join(os.getcwd(), nome_arquivo)

    with open(caminho_arquivo, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=colunas)
        writer.writeheader()
        for r in resultados:
            linha = {col: r.get(col, "") for col in colunas}
            writer.writerow(linha)

    return len(resultados), melhor_voo_info, caminho_arquivo


def realizar_busca(origem, conexao, datas, destinos, progress_callback=None):
    driver = criar_driver()
    todos_resultados = []

    mapa_siglas_url = {
        "fortaleza": "FOR",
        "brasilia": "BSB",
        "salvador": "SSA",
        "recife": "REC",
        "sao paulo": "SAO",
        "rio de janeiro": "RIO",
        "belo horizonte": "BHZ",
        "goiania": "GYN",
        "manaus": "MAO",
        "belem": "BEL",
        "curitiba": "CWB",
        "porto alegre": "POA",
        "florianopolis": "FLN",
        "vitoria": "VIX",
        "natal": "NAT",
        "sao luis": "SLZ",
        "maceio": "MCZ",
        "joao pessoa": "JPA",
        "aracaju": "AJU",
        "teresina": "THE",
        "campo grande": "CGR",
        "cuiaba": "CGB",
        "palmas": "PMW",
        "porto velho": "PVH",
        "rio branco": "RBR",
        "boa vista": "BVB",
        "macapa": "MCP",
    }

    def limpar_nome(nome):
        return (
            nome.lower()
            .strip()
            .replace("ã", "a")
            .replace("õ", "o")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ç", "c")
            .replace("â", "a")
            .replace("ê", "e")
            .replace("ô", "o")
        )

    origem_url = mapa_siglas_url.get(limpar_nome(origem), origem)

    total_passos = max(1, len(destinos) * len(datas))
    passo_atual = 0

    try:
        for destino in destinos:
            destino_url = mapa_siglas_url.get(limpar_nome(destino), destino)
            for data in datas:
                passo_atual += 1
                if progress_callback:
                    progress_callback(passo_atual, total_passos, destino, data)

                query = f"voos de {origem_url} para {destino_url} em {data} so ida"
                query_codificada = urllib.parse.quote(query)
                url_direta = f"https://www.google.com/travel/flights?q={query_codificada}&hl=pt-BR&curr=BRL"
                driver.get(url_direta)
                time.sleep(8)
                                           
                fechar_popups(driver)
                filtrar_uma_escala(driver)
                textos = coletar_resultados(driver)
                resultados = extrair_dados_voos(textos, conexao, data)
                todos_resultados.extend(resultados)
                time.sleep(2)
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        driver.quit()

    return todos_resultados


# ========================
# INTERFACE STREAMLIT (DESKTOP + MOBILE)
# ========================

st.set_page_config(page_title="AeroBot Pro Web", page_icon="✈️")

custom_css = """
<style>
[data-testid="stAppViewContainer"] {
    background: #0B0F19;
}
[data-testid="stSidebar"] {
    background: #0B0F19;
}
.block-container {
    max-width: 600px;
    margin: 0 auto;
}
h1, h2, h3, h4, h5, h6 {
    color: #00e5ff;
    font-family: "Roboto", sans-serif;
}
body, [data-testid="stMarkdownContainer"] {
    color: #ffffff;
}
input, textarea {
    background-color: #121a2f !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    border: 1px solid #1a65d4 !important;
}
label {
    color: #00e5ff !important;
    font-weight: 600 !important;
}
div.stButton {
    text-align: center;
}
div.stButton > button:first-child {
    background-color: #FFD700;
    color: #000000;
    font-weight: 700;
    border-radius: 15px;
    border: none;
    padding: 0.6rem 1.8rem;
}
div.stButton > button:first-child:hover {
    background-color: #DAA520;
    color: #000000;
}
[data-baseweb="progress-bar"] {
    background-color: #121a2f;
}
[data-baseweb="progress-bar"] > div {
    background-color: #1a65d4;
}
img {
    display: block;
    margin-left: auto;
    margin-right: auto;
}
.footer-text {
    text-align: center;
    color:#aaaaaa;
    font-size: 12px;
}
@media (max-width: 600px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Logo centralizada automaticamente pelo CSS
logo_path = "ICONE_AEROBOT.png"
if os.path.exists(logo_path):
    img_logo = Image.open(logo_path)
    st.image(img_logo, width=200)
else:
    st.markdown("### ✈️ AeroBot Pro")

st.markdown(
    "<h1 style='text-align: center; color: #00e5ff;'>AeroBot Pro</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #aaaaaa;'>Versão Web • Rastreador de oportunidades com conexão</p>",
    unsafe_allow_html=True
)
st.markdown("---")

# Campos principais
col_origem, col_conexao = st.columns(2)
with col_origem:
    origem = st.text_input("📍 Cidade de Origem", "Brasília")
with col_conexao:
    conexao = st.text_input("🔄 Cidade de Conexão", "Fortaleza")

col_data, col_margem = st.columns(2)
with col_data:
    data_base = st.date_input("📅 Data base da viagem", date.today())
with col_margem:
    margem = st.number_input("⏳ Margem de dias (+/-)", min_value=0, max_value=7, value=2, step=1)

st.markdown("🎯 **Destinos (máximo 5, um por linha):**")
destinos_texto = st.text_area(
    "",
    value="Belém\nSalvador\nSão Luís\nManaus\nRecife",
    height=100
)
destinos = [d.strip() for d in destinos_texto.splitlines() if d.strip()]
if len(destinos) > 5:
    st.error("Por favor, insira no máximo 5 destinos.")
    destinos = destinos[:5]

with st.expander("💡 Guia e Dicas de Viagem"):
    st.markdown(
        """
        **📌 COMO PREENCHER:**
        - Insira a origem, conexão e data base.
        - A margem de dias pesquisa datas antes e depois da data base.
        - Coloque no máximo 5 destinos, um em cada linha.

        **⚠️ AVISOS IMPORTANTES PARA VOOS SEPARADOS:**
        - 🎒 **Bagagem:** evite despachar; prefira mala de mão.
        - ✈️ **Milhas:** evite usar milhas em conexões montadas.
        - 🛒 **Onde comprar:** prefira sempre o site oficial da companhia aérea.
        """
    )

st.markdown("---")

# Botão principal (centralizado por CSS)
botao = st.button("🚀 INICIAR RASTREAMENTO")

if botao:
    if not origem or not conexao or not destinos:
        st.error("Preencha origem, conexão e pelo menos 1 destino.")
    else:
        datas_busca = []
        for i in range(-margem, margem + 1):
            d = data_base + timedelta(days=i)
            datas_busca.append(d.strftime("%Y-%m-%d"))

        st.write("⏳ Iniciando motores... isso pode levar alguns minutos.")
        progresso = st.progress(0)
        status_text = st.empty()

        def atualizar_progresso(passo_atual, total, destino_atual, data_atual):
            pct = passo_atual / total
            progresso.progress(pct)
            status_text.text(
                f"📡 Rastreando {destino_atual.upper()} na data {data_atual} "
                f"({passo_atual}/{total})"
            )

        resultados = realizar_busca(origem, conexao, datas_busca, destinos, atualizar_progresso)
        total_salvo, melhor_voo, caminho_arquivo = salvar_resultados(resultados, conexao)

        if total_salvo > 0:
            st.success(f"Rastreamento finalizado! {total_salvo} voos encontrados.")
            if melhor_voo:
                st.subheader("🏆 Melhor oportunidade encontrada")
                st.write(f"💰 **Valor**: {melhor_voo['preco']}")
                st.write(f"📅 **Data**: {melhor_voo['data']}")
                st.write(f"✈️ **Companhia**: {melhor_voo['cia']}")

            if caminho_arquivo and os.path.exists(caminho_arquivo):
                with open(caminho_arquivo, "rb") as f:
                    st.download_button(
                        "📥 Baixar relatório em CSV",
                        data=f,
                        file_name=os.path.basename(caminho_arquivo),
                        mime="text/csv"
                    )
        else:
            st.warning("Varredura concluída, mas nenhum voo com essa conexão foi encontrado.")

# Rodapé
st.markdown(
    """
    <br>
    <p class="footer-text">
    Versão 1.0 | Desenvolvido por Renan
    </p>
    """,
    unsafe_allow_html=True
)

# Botão de suporte centralizado
st.markdown(
    """
    <div style="text-align: center; margin-top: 0.5rem;">
        <a href="https://wa.me/5589994080305?text=Olá%20Renan!%20Gostaria%20de%20falar%20sobre%20o%20AeroBot."
           target="_blank"
           style="text-decoration: none;">
            <button style="
                background-color:#25D366;
                color:white;
                padding:6px 14px;
                border:none;
                border-radius:10px;
                font-weight:600;
                cursor:pointer;
                max-width: 260px;
                width: 100%;
                ">
                💬 Suporte via WhatsApp
            </button>
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
