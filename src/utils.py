import re
import os
import logging
from typing import Optional
from bs4 import BeautifulSoup
import markdownify

import sys

# Garante que o console do Windows exiba caracteres acentuados e emojis sem erro de encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class CleanConsoleFormatter(logging.Formatter):
    """Formatador minimalista e limpo para o terminal de desenvolvimento."""
    def format(self, record):
        if record.levelno == logging.ERROR:
            return f"[erro] {record.getMessage()}"
        elif record.levelno == logging.WARNING:
            return f"[alerta] {record.getMessage()}"
        return record.getMessage()

def setup_logger(name: str = "canvas_automation", level: int = logging.INFO) -> logging.Logger:
    """Configura um logger minimalista e limpo para o console."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(CleanConsoleFormatter())
        logger.addHandler(ch)
    return logger

logger = setup_logger()


def clean_filename(filename: str, max_length: int = 100) -> str:
    """
    Limpeza de nomes de arquivo: remove caracteres proibidos no Windows (\\ / : * ? " < > |)
    e normaliza espaços e comprimentos para evitar problemas de caminho.
    """
    if not filename:
        return "sem_titulo"
    
    # Remove tags HTML acidentais
    cleaned = re.sub(r"<[^>]+>", "", filename)
    # Substitui caracteres inválidos por underline ou remove
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", cleaned)
    # Remove múltiplos espaços ou underlines
    cleaned = re.sub(r'[\s_]+', "_", cleaned).strip(" ._")
    
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(" ._")
        
    return cleaned or "item"

# Alias para compatibilidade
sanitize_filename = clean_filename


import requests

def fetch_and_parse_liviu(uuid: str) -> str:
    """
    Busca o conteudo estruturado completo da plataforma Liviu (integrada via iframe no Canvas)
    e converte em Markdown rico com topicos, textos, listas e blocos de codigo.
    """
    url = f"https://api.liviu.com.br/public-link/{uuid}"
    try:
        resp = requests.get(url, timeout=25)
        if resp.status_code != 200:
            return f"> Material externo Liviu indisponivel (HTTP {resp.status_code})\n"
        
        data = resp.json()
        sections_output = []
        items = data.get("data", {}).get("items", [])
        
        for item in items:
            unit_title = item.get("name", "").strip()
            if unit_title:
                sections_output.append(f"## {unit_title}\n")
                
            for section in item.get("children", []):
                sec_name = section.get("name", "").strip()
                if sec_name and sec_name != unit_title:
                    sections_output.append(f"### {sec_name}\n")
                
                blocks_text = []
                
                def traverse_blocks(node):
                    if isinstance(node, dict):
                        # Detecta blocos de codigo
                        settings = node.get("settings") or {}
                        if isinstance(settings, dict) and settings.get("type") == "code":
                            code_content = node.get("content") or node.get("text") or ""
                            if code_content:
                                blocks_text.append(f"```\n{code_content.strip()}\n```")
                                return
                        
                        # Extrai campos de texto rico
                        for field in ["text", "title", "description", "content"]:
                            val = node.get(field)
                            if val and isinstance(val, str) and len(val.strip()) > 1:
                                if "<" in val and ">" in val:
                                    clean_md = markdownify.markdownify(
                                        val,
                                        heading_style=markdownify.ATX,
                                        bullets="-",
                                        strip=["script", "style"]
                                    ).strip()
                                    if clean_md:
                                        blocks_text.append(clean_md)
                                elif not val.strip().startswith("http"):
                                    blocks_text.append(val.strip())
                                    
                        for v in node.values():
                            traverse_blocks(v)
                    elif isinstance(node, list):
                        for el in node:
                            traverse_blocks(el)
                            
                traverse_blocks(section)
                
                # Remove duplicatas sequenciais
                deduped = []
                for b in blocks_text:
                    if not deduped or deduped[-1] != b:
                        deduped.append(b)
                
                if deduped:
                    sections_output.append("\n\n".join(deduped))
                    sections_output.append("\n---\n")
                    
        return "\n\n".join(sections_output).strip()
    except Exception as e:
        return f"> Erro ao extrair material Liviu: {e}\n"


def html_to_clean_markdown(
    html_content: str,
    course_title: str = "",
    module_title: str = "",
    item_title: str = "",
    source_url: str = ""
) -> str:
    """
    Converte HTML do Canvas em Markdown limpo, estruturado e otimizado
    para ingestao direta no Gemini Notebook (NotebookLM).
    Extrai inclusive conteudos externos incorporados via iframe (ex: Liviu).
    """
    if not html_content or not html_content.strip():
        return ""

    # Detecta se ha materiais incorporados do Liviu via iframe ou links
    liviu_uuids = re.findall(
        r"liviu\.com\.br/(?:public/material/|embed/|[^\"\'\s]+/)?([a-f0-9\-]{36})",
        html_content,
        re.IGNORECASE
    )
    unique_liviu_uuids = list(dict.fromkeys(liviu_uuids))

    liviu_texts = []
    for uuid in unique_liviu_uuids:
        liviu_md = fetch_and_parse_liviu(uuid)
        if liviu_md:
            liviu_texts.append(liviu_md)

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove elementos irrelevantes para estudo textual
    for tag in soup(["script", "style", "iframe", "noscript", "svg"]):
        tag.decompose()

    # Ajusta links relativos para manter integridade se necessario
    for a in soup.find_all("a", href=True):
        a["href"] = a["href"].strip()

    # Converte HTML nativo para Markdown
    native_md = markdownify.markdownify(
        str(soup),
        heading_style=markdownify.ATX,
        bullets="-",
        strip=["script", "style"]
    )

    # Limpeza de linhas em branco excessivas
    native_md = re.sub(r"\n{3,}", "\n\n", native_md).strip()

    # Monta cabecalho semantico com metadados para o NotebookLM
    header_lines = [
        f"# {item_title or 'Conteúdo de Aula'}",
        "",
        f"- **Disciplina:** {course_title}",
    ]
    if module_title:
        header_lines.append(f"- **Módulo/Unidade:** {module_title}")
    if source_url:
        header_lines.append(f"- **Link Canvas:** [{item_title or 'Acessar no Canvas'}]({source_url})")
    
    header_lines.extend(["", "---", ""])
    header = "\n".join(header_lines)

    body_parts = []
    if native_md:
        body_parts.append(native_md)
    if liviu_texts:
        body_parts.extend(liviu_texts)

    full_body = "\n\n".join(body_parts).strip()
    return header + full_body + "\n"

