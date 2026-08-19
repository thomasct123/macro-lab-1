"""
persistencia.py — Repositório de bases, salvamento de outputs e projetos
=======================================================================
Três responsabilidades:
  1. Carregar bases do GitHub (sem upload manual)
  2. Salvar outputs (tabelas, gráficos) em pastas locais ou no GitHub
  3. Salvar e restaurar "projetos" (configurações do app)
"""
import base64
import io
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO PADRÃO — repositório pré-carregado
# ---------------------------------------------------------------------------
GITHUB_PADRAO = {
    "owner": "thomasct123",
    "repo": "macro-lab-1",
    "branch": "main",
}

EXT_DADOS = (".xlsx", ".xls", ".csv")
TIMEOUT = 30


# ===========================================================================
# 1. GITHUB — LEITURA
# ===========================================================================
def url_raw(owner, repo, branch, caminho):
    """Monta a URL de download direto de um arquivo do GitHub."""
    return (f"https://raw.githubusercontent.com/{owner}/{repo}/"
            f"{branch}/{caminho}")


def listar_arquivos_github(owner, repo, branch="main", subpasta="", token=None):
    """
    Lista arquivos de dados de um repositório GitHub.
    Retorna lista de dicts: {nome, caminho, tamanho_kb, url}.
    Sem token funciona em repositório público (limite de 60 req/hora por IP).
    """
    api = (f"https://api.github.com/repos/{owner}/{repo}/contents/"
           f"{subpasta}?ref={branch}")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = requests.get(api, headers=headers, timeout=TIMEOUT)
    if r.status_code == 404:
        raise ValueError("Repositório, branch ou pasta não encontrados. "
                         "Verifique owner/repo/branch.")
    if r.status_code == 403:
        raise ValueError("Limite de requisições do GitHub atingido. "
                         "Aguarde alguns minutos ou informe um token.")
    r.raise_for_status()

    conteudo = r.json()
    if isinstance(conteudo, dict):
        raise ValueError("O caminho informado é um arquivo, não uma pasta.")

    saida = []
    for item in conteudo:
        if item["type"] == "file" and item["name"].lower().endswith(EXT_DADOS):
            saida.append({
                "nome": item["name"],
                "caminho": item["path"],
                "tamanho_kb": round(item.get("size", 0) / 1024, 1),
                "url": url_raw(owner, repo, branch, item["path"]),
            })
        elif item["type"] == "dir":
            saida.append({
                "nome": item["name"] + "/",
                "caminho": item["path"],
                "tamanho_kb": None,
                "url": None,
                "pasta": True,
            })
    return saida


def baixar_base_github(url, token=None):
    """Baixa um arquivo do GitHub e devolve DataFrame (sem gravar em disco)."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    conteudo = io.BytesIO(r.content)
    if url.lower().endswith(".csv"):
        return pd.read_csv(conteudo)
    return pd.read_excel(conteudo)


def testar_conexao_github(owner, repo, branch="main", token=None):
    """Verifica rapidamente se o repositório é acessível."""
    try:
        arquivos = listar_arquivos_github(owner, repo, branch, token=token)
        n_dados = sum(1 for a in arquivos if not a.get("pasta"))
        return True, f"{n_dados} arquivo(s) de dados encontrado(s)."
    except Exception as e:
        return False, str(e)


# ===========================================================================
# 2. SALVAMENTO LOCAL DE OUTPUTS
# ===========================================================================
def resolver_pasta(caminho_base, subpastas=None, criar=True):
    """
    Resolve (e cria, se necessário) uma árvore de pastas.
    subpastas: lista de níveis, ex. ["Projeto X", "VAR", "rodada 3"]
    """
    p = Path(caminho_base).expanduser()
    if subpastas:
        for s in subpastas:
            s = str(s).strip()
            if s:
                p = p / s
    if criar:
        p.mkdir(parents=True, exist_ok=True)
    return p


def listar_subpastas(caminho_base):
    """Lista subpastas existentes — para o usuário selecionar em vez de digitar."""
    p = Path(caminho_base).expanduser()
    if not p.exists() or not p.is_dir():
        return []
    return sorted([d.name for d in p.iterdir() if d.is_dir()])


def carimbo():
    """Timestamp para nomes de arquivo."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def salvar_tabelas(tabelas: dict, pasta, nome_base, com_timestamp=True):
    """
    Salva um dicionário {nome_aba: DataFrame} num único xlsx multi-abas.
    Retorna o caminho gravado.
    """
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    sufixo = f"_{carimbo()}" if com_timestamp else ""
    destino = pasta / f"{nome_base}{sufixo}.xlsx"

    with pd.ExcelWriter(destino, engine="openpyxl") as w:
        for aba, df in tabelas.items():
            if df is None:
                continue
            d = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
            # nomes de aba no Excel: máx. 31 caracteres, sem caracteres proibidos
            aba_limpa = str(aba)[:31]
            for c in r"[]:*?/\\":
                aba_limpa = aba_limpa.replace(c, "-")
            d.to_excel(w, sheet_name=aba_limpa, index=True)
    return destino


def salvar_texto(texto, pasta, nome_base, ext="txt", com_timestamp=True):
    """Salva texto puro (resumos de modelos, por exemplo)."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    sufixo = f"_{carimbo()}" if com_timestamp else ""
    destino = pasta / f"{nome_base}{sufixo}.{ext}"
    destino.write_text(str(texto), encoding="utf-8")
    return destino


def salvar_figura(fig, pasta, nome_base, formato="html", com_timestamp=True):
    """
    Salva figura Plotly. 'html' é sempre possível; 'png' exige o pacote kaleido.
    """
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    sufixo = f"_{carimbo()}" if com_timestamp else ""
    destino = pasta / f"{nome_base}{sufixo}.{formato}"
    if formato == "html":
        fig.write_html(str(destino), include_plotlyjs="cdn")
    else:
        fig.write_image(str(destino))  # requer kaleido
    return destino


def df_para_bytes(df, formato="xlsx"):
    """Converte DataFrame em bytes — para o botão de download do Streamlit."""
    buf = io.BytesIO()
    if formato == "csv":
        return df.to_csv(index=True).encode("utf-8")
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=True)
    return buf.getvalue()


def tabelas_para_bytes(tabelas: dict):
    """Converte {aba: DataFrame} em bytes de um xlsx multi-abas."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for aba, df in tabelas.items():
            if df is None:
                continue
            d = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
            aba_limpa = str(aba)[:31]
            for c in r"[]:*?/\\":
                aba_limpa = aba_limpa.replace(c, "-")
            d.to_excel(w, sheet_name=aba_limpa, index=True)
    return buf.getvalue()


# ===========================================================================
# 3. SALVAMENTO NO GITHUB (requer token com escopo de escrita)
# ===========================================================================
def enviar_para_github(conteudo_bytes, caminho_destino, owner, repo,
                       branch="main", token=None, mensagem=None):
    """
    Envia (ou atualiza) um arquivo no repositório via API do GitHub.
    Exige token pessoal com permissão de escrita no repositório.
    """
    if not token:
        raise ValueError("Envio ao GitHub exige um token de acesso pessoal.")

    api = f"https://api.github.com/repos/{owner}/{repo}/contents/{caminho_destino}"
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json"}

    # se o arquivo já existe, é preciso informar o SHA para substituí-lo
    sha = None
    r0 = requests.get(f"{api}?ref={branch}", headers=headers, timeout=TIMEOUT)
    if r0.status_code == 200:
        sha = r0.json().get("sha")

    payload = {
        "message": mensagem or f"Atualiza {caminho_destino} via Laboratório Macro",
        "content": base64.b64encode(conteudo_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(api, headers=headers, json=payload, timeout=TIMEOUT)
    if r.status_code not in (200, 201):
        raise ValueError(f"Falha no envio ({r.status_code}): "
                         f"{r.json().get('message', 'erro desconhecido')}")
    return r.json()["content"]["path"]


# ===========================================================================
# 4. PROJETOS — salvar e restaurar configurações do app
# ===========================================================================
def pasta_projetos(base=None):
    """Diretório onde os projetos ficam guardados."""
    p = Path(base).expanduser() if base else Path.home() / ".macro_lab" / "projetos"
    p.mkdir(parents=True, exist_ok=True)
    return p


def salvar_projeto(nome, config: dict, base=None):
    """Grava a configuração do app num arquivo JSON."""
    p = pasta_projetos(base)
    seguro = "".join(c for c in nome if c.isalnum() or c in " -_").strip()
    if not seguro:
        raise ValueError("Nome de projeto inválido.")
    destino = p / f"{seguro}.json"
    registro = {
        "nome": nome,
        "salvo_em": datetime.now().isoformat(timespec="seconds"),
        "config": config,
    }
    destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    return destino


def listar_projetos(base=None):
    """Lista projetos salvos com data de gravação."""
    p = pasta_projetos(base)
    saida = []
    for f in sorted(p.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            saida.append({"nome": d.get("nome", f.stem),
                          "arquivo": f.name,
                          "salvo_em": d.get("salvo_em", ""),
                          "caminho": str(f)})
        except Exception:
            continue
    return saida


def carregar_projeto(caminho):
    """Lê um projeto salvo e devolve o dicionário de configuração."""
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return d.get("config", {})


def excluir_projeto(caminho):
    Path(caminho).unlink(missing_ok=True)


def config_serializavel(d: dict):
    """
    Converte a configuração para tipos serializáveis em JSON.
    Descarta objetos não-serializáveis (DataFrames, modelos estimados).
    """
    saida = {}
    for k, v in d.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            saida[k] = v
        elif isinstance(v, (list, tuple)):
            saida[k] = [x for x in v if isinstance(x, (str, int, float, bool))]
        elif isinstance(v, dict):
            saida[k] = config_serializavel(v)
        elif isinstance(v, pd.Timestamp):
            saida[k] = v.isoformat()
    return saida
