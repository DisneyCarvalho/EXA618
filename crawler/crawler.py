import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import json

import sqlite3
 
 
import time as tm

DB = "receitas.db"



def criar_tabelas():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
 
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS receitas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo          TEXT NOT NULL,
            tempo_preparo   TEXT,
            tempo_forno     TEXT
        );
 
        CREATE TABLE IF NOT EXISTS ingredientes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            receita_id  INTEGER NOT NULL,
            descricao   TEXT NOT NULL,
            FOREIGN KEY (receita_id) REFERENCES receitas(id)
        );
 
        CREATE TABLE IF NOT EXISTS preparo (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            receita_id  INTEGER NOT NULL,
            numero_passo INTEGER NOT NULL,
            descricao   TEXT NOT NULL,
            FOREIGN KEY (receita_id) REFERENCES receitas(id)
        );
    """)
 
    conn.commit()
    conn.close()




def salvar_receita(dados):
    if dados is None:
        return

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    tempo_preparo = ""
    tempo_forno = ""
    for tempo in (dados.get("tempo") or []):
        if tempo is None:
            continue
        if "preparo" in tempo:
            tempo_preparo = tempo
        elif "fogo" in tempo or "forno" in tempo:
            tempo_forno = tempo

    cursor.execute("""
        INSERT INTO receitas (titulo, tempo_preparo, tempo_forno)
        VALUES (?, ?, ?)
    """, (dados["titulo"], tempo_preparo, tempo_forno))

    receita_id = cursor.lastrowid

    for descricao in (dados.get("ingredientes") or []):
        cursor.execute("""
            INSERT INTO ingredientes (receita_id, descricao)
            VALUES (?, ?)
        """, (receita_id, descricao))

    preparo = dados.get("preparo") or {}

    if isinstance(preparo, dict):
        for chave, descricao in preparo.items():
            numero = int(chave.replace("passo", "").replace("-", ""))
            cursor.execute("""
                INSERT INTO preparo (receita_id, numero_passo, descricao)
                VALUES (?, ?, ?)
            """, (receita_id, numero, descricao))


    conn.commit()
    conn.close()
    print(f"[DB] Salvo: {dados['titulo']}")


fila = []
visitados = set()
receitas = []
bnb_receitas = []

def classificar_links(links, dominio_base):

    receitas = []
    navegacao = []
 
    for link in links:
        h_link = link["href"]
        parsed = urlparse(h_link)
 
        if parsed.netloc != dominio_base:
            continue
 
        if "/receita/" in parsed.path:
            receitas.append(h_link)
        else:
            navegacao.append(h_link)
 
    return receitas, navegacao



def coletar_links(url):
  


    try:
        resposta = requests.get(url, timeout=20)
        resposta.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERRO] Não foi possível acessar '{url}': {e}")
        return []

    soup = BeautifulSoup(resposta.text, "html.parser")
    dominio_base = urlparse(url).netloc

    links_encontrados = []
    vistos = set()  # set

    for tag_a in soup.find_all("a", href=True):
        h_link = tag_a["href"].strip()


        if not h_link or h_link.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue


        link_abs = urljoin(url, h_link)

        if link_abs in vistos:
            continue
        vistos.add(link_abs)

        if urlparse(link_abs).netloc == dominio_base:
            mesmo_dominio = True
        else:
            mesmo_dominio = False

        texto = tag_a.get_text(strip=True) ##Pega o texto do link

        links_encontrados.append({
            "href": link_abs,
            "texto": texto,
            "mesmo_dominio": mesmo_dominio,
        })

    return links_encontrados


def exibir_links(links: list[dict], apenas_mesmo_dominio: bool = False):
    if apenas_mesmo_dominio:
        aux = []
        for i in links:
            if i["mesmo_dominio"]:
                aux.append(i)
        links = aux

    print(f"\n{'─'*70}")
    print(f"  {len(links)} link(s) encontrado(s)")
    print(f"{'─'*70}")

    for i, link in enumerate(links, 1):
        tm.sleep(0.3)
        dominio_tag = "✓ mesmo domínio" if link["mesmo_dominio"] else "↗ externo"
        texto = f'  "{link["texto"]}"' if link["texto"] else ""
        print(f"[{i:03d}] {dominio_tag}")
        print(f"       {link['href']}{texto}")

    print(f"{'─'*70}\n")




def adicionar_na_fila(url):
    if url not in visitados and url not in fila:
        fila.append(url)
def proximo_da_fila():
    if not fila:
        return None
    url = fila.pop(0)
    visitados.add(url)
    return url
def adicionar_receita_url(url):
    if url not in receitas:
        receitas.append(url)
def status():
    print(f"  Na fila    : {len(fila)}")
    print(f"  Visitados  : {len(visitados)}")
    print(f"  Receitas   : {len(receitas)}")



def pegaReceita(receitaurl):
    total = {}
    try:
        resposta = requests.get(receitaurl, timeout=20)
        resposta.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERRO] Não foi possível acessar '{receitaurl}': {e}")
        return []
    soup = BeautifulSoup(resposta.text, "html.parser")

    ingredientes_soup = soup.find_all("label", attrs={"for": lambda v: v and v.startswith("ingrediente-")})
    title = soup.find("div", attrs={"class": lambda v: v and v.startswith("title")})

    ingredientes = []  ##INGREDIENTEs
    for ingre in ingredientes_soup:
        ingredientes.append(ingre.get_text(strip=True))

    titulo = title.find("h1").get_text(strip=True)  ##TITULO

    
    preparo = {}  ## preparo


    try:
        preparo_soup = soup.find("div", attrs={"class": lambda v: v and v.startswith("preparo mt-4 mb-2")}).find("ol", class_="lista-preparo-1").find_all("li", attrs={"id": lambda v: v and v.startswith("passo")})
        for i in preparo_soup:
            preparo[i["id"]] = {
    "descricao": None,
    "foto": i.find("img")["src"]
}

    except Exception as e:
        print(f"Erro {e} no foto_preparo, URL {receitaurl}")
        preparo = [None]
    
    try:
        preparo_soup = soup.find("div", attrs={"class": lambda v: v and v.startswith("preparo mt-4 mb-2")}).find("ol", class_="lista-preparo-1").find_all("li", attrs={"id": lambda v: v and v.startswith("passo")})
        for i in preparo_soup:
            preparo[i["id"]]["descricao"] = i.find("span").get_text(strip=True)

            

    except Exception as e:
        print(f"Erro {e} no preparo, URL {receitaurl}")
        preparo = [None]
    try:
        tempo_soup = soup.find("div", attrs={"class": lambda v: v and v.startswith("container tempos mb-3")})
        tempo = []  ##TEMPO
        span = tempo_soup.find_all("div", class_="col-6")
        for i in span:
            i.find("div", class_="tempo").find("span")
            tempo.append(i.get_text(separator=" ",strip=True))
    except Exception as e:
        print(f"Erro {e} no tempo, URL {receitaurl}")
        tempo.append(None)
        
    total["ingredientes"] = ingredientes
    total["titulo"] = titulo
    total["tempo"] = tempo
    total["preparo"] = preparo


    return total


if __name__ == "__main__":
    criar_tabelas()
    url_alvo = "https://www.receiteria.com.br/".strip()

    if not url_alvo.startswith("http"):
        url_alvo = "https://" + url_alvo


    adicionar_na_fila(url_alvo)

    while fila and len(visitados) < 10 and len(receitas) < 20:
        url = proximo_da_fila()
        print(f"Acessando {url}")
        links = coletar_links(url)

        recei , navega = classificar_links(links,urlparse(url_alvo).netloc)

        for i in recei:
            adicionar_receita_url(i)
        for j in navega:
            adicionar_na_fila(j)

        '''receita_bnb = pegaReceita(receitas[2])
        print(receita_bnb)'''
    for i in receitas:
        receita_bnb = pegaReceita(i)
        if receita_bnb:
            ##salvar_receita(receita_bnb)
            bnb_receitas.append(receita_bnb)


    with open("bnb.json", "w", encoding="utf-8") as file_bnb:
        json.dump(bnb_receitas, file_bnb, ensure_ascii=False, indent=4)
    with open("receitar.txt","w") as file_rer:
        for i in receitas:
            file_rer.write(str(i)+"\n")
    with open("navegar.txt","w") as file_nav:
        for i in visitados:
            file_nav.write(str(i)+"\n")

    ##print(receitas,"receita\n", navega,"neavbe")


    if 1 > 2:
        filtrar = input("\nMostrar apenas links do mesmo domínio? (s/n): ").strip().lower() == "s"

        exibir_links(links, apenas_mesmo_dominio=filtrar)


        internos = sum(1 for l in links if l["mesmo_dominio"])
        externos = len(links) - internos
        print(f"Resumo: {internos} internos | {externos} externos | {len(links)} total")
