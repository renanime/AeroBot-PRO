import json
import random
import string
import os
import shutil
import re
import time
import csv
import urllib.parse
from datetime import datetime, timedelta
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
        # 1. Encontra e clica no botão principal "Escalas"
        btn_escalas = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[contains(text(), 'Escalas')] or contains(., 'Escalas')]")
            )
        )
        driver.execute_script("arguments[0].click();", btn_escalas)
        time.sleep(2)

        # 2. Encontra e clica na opção "1 parada ou menos"
        opcao_1_escala = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(), '1 parada') or contains(text(), '1 escala')]")
            )
        )
        driver.execute_script("arguments[0].click();", opcao_1_escala)
        time.sleep(2)

        # 3. Fecha o menu flutuante para a página atualizar
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(4) 
        return True
    except Exception as e:
        print(f"Erro ao filtrar escalas: {e}")
        return False


def coletar_resultados(driver):
    try:
        # Espera até o símbolo de Real aparecer em qualquer lugar da página
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(., 'R$')]")
            )
        )
        time.sleep(4) # Tempo extra para a página renderizar os cards

        # Lista de possíveis estruturas HTML que o Google usa para os cards de voo
        xpaths_para_testar = [
            "//li[.//span[contains(., 'R$')]]",                                      # Estrutura 1 (Listas)
            "//div[@role='listitem' and .//*[contains(., 'R$')]]",                   # Estrutura 2 (Itens de lista em Div)
            "//div[@role='button' and .//*[contains(., 'R$')] and .//*[contains(., 'min')]]", # Estrutura 3 (Botões clicáveis)
            "//div[contains(@class, 'pIav2d')]"                                      # Estrutura 4 (Classe genérica atual)
        ]

        cards = []
        # Testa cada estrutura até encontrar uma que retorne resultados
        for xpath in xpaths_para_testar:
            elementos = driver.find_elements(By.XPATH, xpath)
            if len(elementos) > 0:
                cards = elementos
                break # Achou os cards, pode parar de procurar

        # Extrai o texto de cada card encontrado
        return [card.text.strip() for card in cards if card.text.strip()]
    except Exception as e:
        print(f"Erro na coleta: {e}")
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
        .replace("í", "i")
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

st.set_page_config(page_title="AeroBot Pro | Buscador", page_icon="✈️", layout="centered")

custom_css = """
<style>
/* Fundo geral com imagem de aviação e película escura */
[data-testid="stAppViewContainer"] {
    background-image: linear-gradient(rgba(11, 15, 25, 0.80), rgba(11, 15, 25, 0.95)), url("https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2074&auto=format&fit=crop");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

/* Mantém a barra lateral (Painel Admin) escura para não confundir a leitura */
[data-testid="stSidebar"] {
    background: #0B0F19;
}
/* Títulos com cor mais suave e elegante */
h1, h2, h3, h4, h5, h6 {
    color: #F8FAFC;
    font-family: "Inter", "Roboto", sans-serif;
    font-weight: 700;
}
body, [data-testid="stMarkdownContainer"] {
    color: #CBD5E1;
}
/* Campos de digitação estilo SaaS Premium */
input, textarea {
    background-color: #151E32 !important;
    color: #F8FAFC !important;
    border-radius: 8px !important;
    border: 1px solid #2A3B5C !important;
    transition: all 0.3s ease;
}
/* Estilo para as caixas de seleção (Dropdowns e Multiselect) */
[data-baseweb="select"] > div {
    background-color: #151E32 !important;
    color: #F8FAFC !important;
    border-radius: 8px !important;
    border: 1px solid #2A3B5C !important;
}
/* Cor das etiquetas (tags) dos destinos selecionados */
[data-baseweb="tag"] {
    background-color: #2A3B5C !important;
    color: #F8FAFC !important;
    border-radius: 6px !important;
}
input:focus, textarea:focus {
    border: 1px solid #FFD700 !important;
    box-shadow: 0 0 8px rgba(255, 215, 0, 0.2) !important;
}
label {
    color: #94A3B8 !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
}
/* Botões Principais (Amarelos) */
button[kind="primary"] {
    background-color: #FFD700 !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 0.7rem 2rem !important;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.15) !important;
    transition: all 0.3s ease !important;
}
button[kind="primary"] * {
    color: #111111 !important;
    font-weight: 800 !important;
    letter-spacing: 0.5px;
}
button[kind="primary"]:hover {
    background-color: #FACC15 !important;
    box-shadow: 0 6px 20px rgba(255, 215, 0, 0.3) !important;
    transform: translateY(-2px);
}

/* Botões Secundários (Lixeira) - CORRIGIDO PARA NÃO FICAR AMARELO */
button[kind="secondary"] {
    background-color: #151E32 !important;
    border: 1px solid #EF4444 !important;
    border-radius: 8px !important;
    color: #F8FAFC !important;
    box-shadow: none !important;
    transition: all 0.3s ease !important;
}
button[kind="secondary"]:hover {
    background-color: #EF4444 !important;
    color: #ffffff !important;
}

/* Barra de progresso mais limpa */
[data-baseweb="progress-bar"] {
    background-color: #151E32;
    border-radius: 10px;
}
[data-baseweb="progress-bar"] > div {
    background-color: #FFD700;
}
/* Rodapé discreto */
.footer-text {
    text-align: center;
    color: #64748B;
    font-size: 13px;
    margin-top: 2rem;
}
/* Botão WhatsApp com hover */
.whatsapp-btn {
    background-color: #25D366;
    color: #111111;
    padding: 10px 20px;
    border: none;
    border-radius: 10px;
    font-weight: 800;
    cursor: pointer;
    width: 100%;
    max-width: 260px;
    box-shadow: 0 4px 15px rgba(37, 211, 102, 0.2);
    transition: all 0.3s ease;
}
.whatsapp-btn:hover {
    background-color: #22C55E;
    box-shadow: 0 6px 20px rgba(37, 211, 102, 0.3);
    transform: translateY(-2px);
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Logo centralizada usando colunas do Streamlit
logo_path = "ICONE_AEROBOT.png"
if os.path.exists(logo_path):
    img_logo = Image.open(logo_path)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.image(img_logo, use_container_width=True)
else:
    st.markdown("<h3 style='text-align: center;'>✈️ AeroBot Pro</h3>", unsafe_allow_html=True)

st.markdown(
    "<h1 style='text-align: center; color: #00e5ff;'>AeroBot Pro</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #aaaaaa;'>Versão Web • Rastreador de oportunidades com conexão</p>",
    unsafe_allow_html=True
)
st.markdown("---")

# ========================
# TELA DE LOGIN E GERENCIADOR DE USUÁRIOS (PRO)
# ========================
SENHA_ADMIN = "RenanAdmin"  # <-- Sua senha mestre
ARQUIVO_USUARIOS = "usuarios_cadastrados.json"

def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS):
        try:
            with open(ARQUIVO_USUARIOS, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_usuarios(lista_usuarios):
    with open(ARQUIVO_USUARIOS, "w") as f:
        json.dump(lista_usuarios, f)

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.is_admin = False
    st.session_state.usuario_logado = ""

usuarios_validos = carregar_usuarios()
data_hoje = datetime.now().date()

# TELA DE BLOQUEIO (LOGIN POR E-MAIL E SENHA)
if not st.session_state.logado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_login1, col_login2, col_login3 = st.columns([1, 2, 1])

    with col_login2:
        st.markdown("<h3 style='text-align: center;'>🔒 Acesso Restrito</h3>", unsafe_allow_html=True)
        email_digitado = st.text_input("E-mail:")
        senha_digitada = st.text_input("Senha:", type="password")

        if st.button("Entrar", type="primary", use_container_width=True):
            if not email_digitado or not senha_digitada:
                st.warning("Preencha o e-mail e a senha!")
            else:
                # Verifica se é o Administrador
                if email_digitado.lower() == "admin" and senha_digitada == SENHA_ADMIN:
                    st.session_state.logado = True
                    st.session_state.is_admin = True
                    st.session_state.usuario_logado = "Administrador"
                    st.rerun()
                else:
                    # Verifica se é um Cliente
                    usuario_encontrado = False
                    for u in usuarios_validos:
                        if email_digitado.lower() == u["email"].lower() and senha_digitada == u["senha"]:
                            if u["expira_em"] == "2099-12-31":
                                st.session_state.logado = True
                                st.session_state.is_admin = False
                                st.session_state.usuario_logado = u["email"]
                                usuario_encontrado = True
                                st.rerun()
                            else:
                                data_expiracao = datetime.strptime(u["expira_em"], "%Y-%m-%d").date()
                                if data_hoje <= data_expiracao:
                                    st.session_state.logado = True
                                    st.session_state.is_admin = False
                                    st.session_state.usuario_logado = u["email"]
                                    usuario_encontrado = True
                                    st.rerun()
                                else:
                                    st.error("❌ Sua assinatura expirou! Contate o suporte.")
                                    usuario_encontrado = True
                            break

                    if not usuario_encontrado:
                        st.error("❌ E-mail ou senha incorretos!")
    st.stop()

# PAINEL DO ADMINISTRADOR
if st.session_state.is_admin:
    with st.sidebar:
        st.markdown("### 👑 Painel Admin")

        st.markdown("**Cadastrar Novo Cliente:**")
        novo_email = st.text_input("E-mail do cliente:")
        nova_senha = st.text_input("Senha de acesso:")
        is_permanente = st.checkbox("⭐ Acesso Definitivo (Vitalício)")

        if not is_permanente:
            dias_validade = st.number_input("Dias de teste:", min_value=1, value=7)

        if st.button("➕ Cadastrar Cliente", type="primary", use_container_width=True):
            if not novo_email or not nova_senha:
                st.warning("Preencha o e-mail e a senha!")
            else:
                if is_permanente:
                    data_exp = "2099-12-31"
                else:
                    data_exp = (datetime.now() + timedelta(days=dias_validade)).strftime("%Y-%m-%d")

                usuarios_validos.append({"email": novo_email, "senha": nova_senha, "expira_em": data_exp})
                salvar_usuarios(usuarios_validos)
                st.success("Cliente cadastrado com sucesso!")
                st.rerun()

        st.markdown("---")
        st.markdown("**Clientes Ativos:**")

        if len(usuarios_validos) == 0:
            st.info("Nenhum cliente cadastrado.")
        else:
            for i, u in enumerate(usuarios_validos):
                col_texto, col_btn = st.columns([3, 1]) 

                with col_texto:
                    if u["expira_em"] == "2099-12-31":
                        status = "⭐"
                        texto_validade = "Vitalício"
                    else:
                        data_exp_obj = datetime.strptime(u["expira_em"], "%Y-%m-%d").date()
                        status = "🟢" if data_hoje <= data_exp_obj else "🔴"
                        texto_validade = f"Vence: {u['expira_em']}"

                    st.markdown(
                        f"{status} **{u['email']}**<br><span style='color: #94A3B8; font-size: 12px;'>Senha: {u['senha']} | {texto_validade}</span>", 
                        unsafe_allow_html=True
                    )

                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True) 
                    # AQUI ESTÁ A CORREÇÃO DA LIXEIRA: type="secondary" e apenas o ícone
                    if st.button("🗑️", key=f"del_{u['email']}_{i}", type="secondary", use_container_width=True):
                        usuarios_validos.remove(u)
                        salvar_usuarios(usuarios_validos)
                        st.rerun()

                st.markdown("<hr style='margin: 0.2em 0; border-color: #2A3B5C;'>", unsafe_allow_html=True)
# ========================
# PAINEL DO CLIENTE (TROCAR SENHA E SAIR)
# ========================
elif st.session_state.logado and not st.session_state.is_admin:
    with st.sidebar:
        st.markdown("### 👤 Meu Perfil")
        st.markdown(f"**Logado como:**<br><span style='color:#00e5ff;'>{st.session_state.usuario_logado}</span>", unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("🔐 Trocar minha senha"):
            senha_atual = st.text_input("Senha atual:", type="password")
            nova_senha = st.text_input("Nova senha:", type="password")

            if st.button("💾 Salvar Senha", type="primary", use_container_width=True):
                if not senha_atual or not nova_senha:
                    st.warning("Preencha os dois campos!")
                else:
                    usuarios = carregar_usuarios()
                    sucesso = False
                    for u in usuarios:
                        if u["email"].lower() == st.session_state.usuario_logado.lower() and u["senha"] == senha_atual:
                            u["senha"] = nova_senha
                            sucesso = True
                            break

                    if sucesso:
                        salvar_usuarios(usuarios)
                        st.success("Senha alterada com sucesso!")
                    else:
                        st.error("Senha atual incorreta!")

        st.markdown("---")
        if st.button("🚪 Sair da Conta", type="secondary", use_container_width=True):
            st.session_state.logado = False
            st.session_state.usuario_logado = ""
            st.rerun()

# ========================
# A PARTIR DAQUI COMEÇA O SEU APLICATIVO NORMAL
# ========================


# ========================
# CAMPOS DE BUSCA INTELIGENTES
# ========================

# Lista dos principais aeroportos do Brasil
lista_aeroportos = [
    "Aracaju (AJU)", "Belém (BEL)", "Belo Horizonte (CNF)", "Boa Vista (BVB)", 
    "Brasília (BSB)", "Campinas (VCP)", "Campo Grande (CGR)", "Cuiabá (CGB)", 
    "Curitiba (CWB)", "Florianópolis (FLN)", "Fortaleza (FOR)", "Goiânia (GYN)", 
    "João Pessoa (JPA)", "Macapá (MCP)", "Maceió (MCZ)", "Manaus (MAO)", 
    "Natal (NAT)", "Palmas (PMW)", "Porto Alegre (POA)", "Porto Velho (PVH)", 
    "Recife (REC)", "Rio Branco (RBR)", "Rio de Janeiro (GIG)", "Rio de Janeiro (SDU)", 
    "Salvador (SSA)", "São Luís (SLZ)", "São Paulo (CGH)", "São Paulo (GRU)", 
    "Teresina (THE)", "Vitória (VIX)"
]

col_origem, col_conexao = st.columns(2)
with col_origem:
    origem_selecionada = st.selectbox("📍 Cidade de Origem", options=lista_aeroportos, index=lista_aeroportos.index("Brasília (BSB)"))
    # O código abaixo extrai apenas a sigla (ex: BSB) para o robô pesquisar mais rápido
    origem = origem_selecionada.split("(")[-1].replace(")", "") 

with col_conexao:
    conexao_selecionada = st.selectbox("🔄 Cidade de Conexão", options=lista_aeroportos, index=lista_aeroportos.index("Fortaleza (FOR)"))
    conexao = conexao_selecionada.split("(")[-1].replace(")", "")

col_data, col_margem = st.columns(2)
with col_data:
    data_base = st.date_input("📅 Data base da viagem", date.today())
with col_margem:
    margem = st.number_input("⏳ Margem de dias (+/-)", min_value=0, max_value=7, value=2, step=1)

# O multiselect substitui a caixa de texto gigante
destinos_selecionados = st.multiselect(
    "🎯 **Selecione os Destinos (máximo 5):**",
    options=lista_aeroportos,
    default=["Belém (BEL)", "Salvador (SSA)", "São Luís (SLZ)", "Manaus (MAO)", "Recife (REC)"],
    max_selections=5,
    placeholder="Clique ou digite para buscar o aeroporto..."
)
# Extrai apenas as siglas dos destinos selecionados para o robô
destinos = [d.split("(")[-1].replace(")", "") for d in destinos_selecionados]

with st.expander("💡 Guia e Dicas de Viagem"):
    st.markdown(
        """
        **📌 COMO PREENCHER:**
        - Selecione a origem, conexão e data base.
        - A margem de dias pesquisa datas antes e depois da data base.
        - Escolha até 5 destinos na lista (você pode digitar o nome da cidade para achar mais rápido).

        **⚠️ AVISOS IMPORTANTES PARA VOOS SEPARADOS:**
        - 🎒 **Bagagem:** evite despachar; prefira mala de mão.
        - ✈️ **Milhas:** evite usar milhas em conexões montadas.
        - 🛒 **Onde comprar:** prefira sempre o site oficial da companhia aérea.
        """
    )

st.markdown("---")

# Botão principal centralizado com colunas
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    botao = st.button("🚀 INICIAR RASTREAMENTO", type="primary", use_container_width=True)

if botao:
    # Cria a tela de carregamento com a hélice
    tela_carregamento = st.empty()
    tela_carregamento.markdown(
        """
        <style>
        .helice-girando {
            display: inline-block;
            animation: spin 0.8s linear infinite;
            font-size: 28px;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        </style>
        <div style='text-align: center; padding: 20px; background-color: #151E32; border-radius: 12px; border: 1px solid #2A3B5C; margin-bottom: 20px;'>
            <span class='helice-girando'>⚙️</span> 
            <span style='color: #F8FAFC; font-weight: bold; font-size: 16px; margin-left: 15px;'>
                Ligando turbinas e buscando as melhores rotas...
            </span>
        </div>
        """, 
        unsafe_allow_html=True
    )

    if not origem or not conexao or not destinos:
        st.error("Preencha origem, conexão e pelo menos 1 destino.")
        tela_carregamento.empty() # Apaga a hélice se der erro
    else:
        datas_busca = []
        for i in range(-margem, margem + 1):
            d = data_base + timedelta(days=i)
            datas_busca.append(d.strftime("%Y-%m-%d"))

        st.write("⏳ Espere um pouco, leva pouco tempo... ✈️ ✈️ ✈️ ✈️ ✈️  ")
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

        # Apaga a hélice quando a busca terminar
        tela_carregamento.empty()

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

# Botão de suporte centralizado com texto escuro
st.markdown(
    """
    <div style="display: flex; justify-content: center; margin-top: 0.5rem;">
        <a href="https://wa.me/5589994080305?text=Olá%20Renan!%20Gostaria%20de%20falar%20sobre%20o%20AeroBot."
           target="_blank"
           style="text-decoration: none; width: 100%; max-width: 260px;">
            <button class="whatsapp-btn">
                💬 Suporte via WhatsApp
            </button>
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
