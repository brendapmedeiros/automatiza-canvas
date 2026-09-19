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

def setup_logger(name: str = "canvas_automation", level: int = logging.INFO) -> logging.Logger:
    """Configura um logger padronizado e limpo para o console."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
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


def html_to_clean_markdown(
    html_content: str,
    course_title: str = "",
    module_title: str = "",
    item_title: str = "",
    source_url: str = ""
) -> str:
    """
    Converte HTML do Canvas em Markdown limpo, estruturado e otimizado
    para ingestão direta no Gemini Notebook (NotebookLM).
    """
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove elementos irrelevantes para estudo textual
    for tag in soup(["script", "style", "iframe", "noscript", "svg"]):
        tag.decompose()

    # Ajusta links relativos para manter integridade se necessário
    for a in soup.find_all("a", href=True):
        a["href"] = a["href"].strip()

    # Converte para Markdown
    md_content = markdownify.markdownify(
        str(soup),
        heading_style=markdownify.ATX,
        bullets="-",
        strip=["script", "style"]
    )

    # Limpeza de linhas em branco excessivas
    md_content = re.sub(r"\n{3,}", "\n\n", md_content).strip()

    # Monta cabeçalho semântico com metadados para o NotebookLM
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

    return header + md_content + "\n"
