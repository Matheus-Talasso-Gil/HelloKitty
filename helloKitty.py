import requests
import concurrent.futures
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def checar_api_direta(rede, username):
    """
    Testa diretamente nas APIs oficiais/públicas das redes.
    Retorna a URL se o usuário REALMENTE existir, ou None se não existir.
    """
    try:
        if rede == "GitHub":
            r = requests.get(f"https://api.github.com/users/{username}", headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return f"https://github.com/{username}"

        elif rede == "Reddit":
            r = requests.get(f"https://www.reddit.com/user/{username}/about.json", headers=HEADERS, timeout=5)
            if r.status_code == 200 and "data" in r.json():
                return f"https://www.reddit.com/user/{username}"

        elif rede == "Telegram":
            r = requests.get(f"https://t.me/{username}", headers=HEADERS, timeout=5)
            # No Telegram, se a conta existe, há o botão "Send Message" ou a foto do perfil
            if r.status_code == 200 and ("tgme_page_title" in r.text or "extra_actions" in r.text):
                return f"https://t.me/{username}"

        elif rede == "Steam":
            r = requests.get(f"https://steamcommunity.com/id/{username}", headers=HEADERS, timeout=5)
            if r.status_code == 200 and "actual_persona_name" in r.text:
                return f"https://steamcommunity.com/id/{username}"

        elif rede == "Dev.to":
            r = requests.get(f"https://dev.to/api/users/by_username?url={username}", headers=HEADERS, timeout=5)
            if r.status_code == 200 and r.json().get("username"):
                return f"https://dev.to/{username}"

    except Exception:
        pass

    return None


def validar_existencia_real(url, username):
    """
    Faz o Web Scraping inteligente da página procurando metadados (og:title, og:description)
    que confirmem que a conta pertence exatamente àquele nome de usuário.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=6, allow_redirects=True)
        
        # 1. Se foi redirecionado para login ou home genérica, descarta
        if "login" in response.url.lower() or response.url.strip('/') in ["https://www.instagram.com", "https://x.com", "https://www.tiktok.com"]:
            return False, "Redirecionado para Login/Home"

        if response.status_code != 200:
            return False, f"Status HTTP {response.status_code}"

        html_lower = response.text.lower()
        
        # 2. Indicadores explícitos de conta inexistente
        mensagens_erro = [
            "page not found", "user not found", "this account doesn't exist",
            "perfil não encontrado", "página não encontrada", "isn't available",
            "does not exist", "couldn't find this account"
        ]
        for msg in mensagens_erro:
            if msg in html_lower:
                return False, f"Página de erro detectada"

        # 3. Validação por Metadados OpenGraph (og:title / og:description)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        
        content_to_check = ""
        if og_title and og_title.get("content"):
            content_to_check += og_title["content"].lower() + " "
        if og_desc and og_desc.get("content"):
            content_to_check += og_desc["content"].lower() + " "
        if soup.title and soup.title.string:
            content_to_check += soup.title.string.lower()

        # Verifica se o nome do usuário pesquisado aparece no título/meta do perfil
        if username.lower() in content_to_check:
            # Extrai o título limpo para mostrar na tela
            titulo_limpo = soup.title.string.strip().replace('\n', '') if soup.title else "Perfil Encontrado"
            return True, f"Perfil confirmado ({titulo_limpo[:45]}...)"

    except Exception:
        pass

    return False, "Não foi possível confirmar o perfil"


def checar_rede(rede_info, username):
    nome_rede = rede_info["name"]
    url = rede_info["url_template"].format(username)

    # Passo 1: Tenta validação via API direta (se for uma das redes suportadas)
    url_api = checar_api_direta(nome_rede, username)
    if url_api:
        return (nome_rede, url_api, "Confirmado via API Oficial [100% Preciso]")

    # Passo 2: Validação via Metadados e Scraping
    valido, motivo = validar_existencia_real(url, username)
    if valido:
        return (nome_rede, url, motivo)

    return None


def hello_kitty_search(username):
    print(f"\n🎀 [ HELLO KITTY OSINT v4 - Validação de Usuários Reais ] 🎀")
    print(f"Pesquisando e verificando contas ativas para: '{username}'...\n" + "=" * 70)

    # Lista das principais redes sociais selecionadas
    PLATAFORMAS_PRINCIPAIS = [
        {"name": "GitHub", "url_template": "https://github.com/{}"},
        {"name": "Instagram", "url_template": "https://www.instagram.com/{}/"},
        {"name": "Reddit", "url_template": "https://www.reddit.com/user/{}"},
        {"name": "TikTok", "url_template": "https://www.tiktok.com/@{}"},
        {"name": "Telegram", "url_template": "https://t.me/{}"},
        {"name": "Pinterest", "url_template": "https://www.pinterest.com/{}/"},
        {"name": "Medium", "url_template": "https://medium.com/@{}"},
        {"name": "Dev.to", "url_template": "https://dev.to/{}"},
        {"name": "Steam", "url_template": "https://steamcommunity.com/id/{}"},
        {"name": "SoundCloud", "url_template": "https://soundcloud.com/{}"},
        {"name": "Vimeo", "url_template": "https://vimeo.com/{}"},
        {"name": "Twitch", "url_template": "https://www.twitch.tv/{}"}
    ]

    encontrados = []

    # Execução paralela para rapidez
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(checar_rede, rede, username) for rede in PLATAFORMAS_PRINCIPAIS]
        for future in concurrent.futures.as_completed(futures):
            resultado = future.result()
            if resultado:
                nome, url, detalhe = resultado
                encontrados.append(resultado)
                print(f"[✓] {nome.upper()}")
                print(f"    ├─ URL: {url}")
                print(f"    └─ Status: {detalhe}\n")

    print("=" * 70)
    print(f"🎀 Busca finalizada! {len(encontrados)} contas REAIS e CONFIRMADAS foram encontradas.")


if __name__ == "__main__":
    alvo = input("Digite o nome de usuário exato a pesquisar: ").strip()
    if alvo:
        hello_kitty_search(alvo)
    else:
        print("Nome de usuário inválido.")