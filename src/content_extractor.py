import os
import re
from pathlib import Path
from typing import List, Set
import requests
from canvasapi.course import Course
from canvasapi.module import Module, ModuleItem
from canvasapi.page import Page
from canvasapi.file import File

from src.config import OUTPUT_DIR
from src.utils import logger, sanitize_filename, html_to_clean_markdown, fetch_and_parse_liviu

class ContentExtractor:
    """
    Módulo 1: Extrai módulos, páginas e arquivos oficiais de cada disciplina do Canvas,
    convertendo conteúdos textuais em Markdown limpo para o Gemini Notebook (NotebookLM).
    """

    def __init__(self, output_base_dir: Path = OUTPUT_DIR):
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

    def extract_course_content(self, course: Course):
        """Extrai todos os módulos, páginas e arquivos de um curso específico."""
        course_name = getattr(course, "name", f"Curso_{course.id}")
        logger.info(f"\n[extract] {course_name}")

        clean_course_dir_name = sanitize_filename(course_name)
        course_dir = self.output_base_dir / clean_course_dir_name
        files_dir = course_dir / "arquivos"
        course_dir.mkdir(parents=True, exist_ok=True)
        files_dir.mkdir(parents=True, exist_ok=True)

        processed_page_urls: Set[str] = set()

        # 1. Extrair por Módulos
        self._extract_modules(course, course_name, course_dir, processed_page_urls)

        # 2. Extrair Páginas avulsas (que possam não estar linkadas em módulos)
        self._extract_standalone_pages(course, course_name, course_dir, processed_page_urls)

        # 3. Baixar Arquivos Oficiais do Curso (PDFs, apostilas, apresentações)
        self._download_course_files(course, files_dir)

    def _extract_modules(self, course: Course, course_name: str, course_dir: Path, processed_pages: Set[str]):
        """Itera pelos módulos do curso e processa itens de página e documentos."""
        try:
            modules = list(course.get_modules())
        except Exception as e:
            logger.warning(f"Não foi possível obter módulos do curso {course_name}: {e}")
            return

        if not modules:
            logger.info("Nenhum módulo estruturado encontrado no curso.")
            return

        for idx, module in enumerate(modules, start=1):
            module_name = getattr(module, "name", f"Modulo_{idx}")

            try:
                items = list(module.get_module_items())
            except Exception as e:
                logger.warning(f"Erro ao listar itens do módulo '{module_name}': {e}")
                continue

            for item_idx, item in enumerate(items, start=1):
                item_type = getattr(item, "type", "")
                item_title = getattr(item, "title", f"Item_{item_idx}")

                if item_type == "Page":
                    page_url = getattr(item, "page_url", None)
                    if page_url:
                        self._process_and_save_page(
                            course=course,
                            course_name=course_name,
                            module_name=module_name,
                            module_idx=idx,
                            page_url=page_url,
                            page_title=item_title,
                            course_dir=course_dir,
                            processed_pages=processed_pages
                        )
                elif item_type == "ExternalUrl":
                    # Gera uma referência em Markdown para links externos
                    self._save_external_link(item, module_name, idx, course_dir, course_name)

    def _process_and_save_page(
        self,
        course: Course,
        course_name: str,
        module_name: str,
        module_idx: int,
        page_url: str,
        page_title: str,
        course_dir: Path,
        processed_pages: Set[str]
    ):
        """Busca o HTML da página, converte para Markdown e salva no padrão Unidade_X_[Titulo].md."""
        processed_pages.add(page_url)

        try:
            page = course.get_page(page_url)
            html_body = getattr(page, "body", "")
            if not html_body:
                logger.debug(f"Página '{page_title}' vazia ou sem conteúdo HTML.")
                return

            # Nome do arquivo estruturado: Unidade_X_[Titulo].md ou similar
            prefix = f"Unidade_{module_idx:02d}"
            clean_title = sanitize_filename(page_title)
            filename = f"{prefix}_{clean_title}.md"
            filepath = course_dir / filename

            source_url = getattr(page, "html_url", "")
            md_content = html_to_clean_markdown(
                html_content=html_body,
                course_title=course_name,
                module_title=module_name,
                item_title=page_title,
                source_url=source_url
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)

            size_kb = filepath.stat().st_size / 1024
            logger.info(f"  -> {filename} ({size_kb:.1f} KB)")


        except Exception as e:
            logger.warning(f"    Falha ao extrair página '{page_title}' ({page_url}): {e}")

    def _extract_standalone_pages(self, course: Course, course_name: str, course_dir: Path, processed_pages: Set[str]):
        """Processa páginas que não foram mapeadas em nenhum módulo."""
        try:
            pages = list(course.get_pages())
        except Exception as e:
            logger.debug(f"Não foi possível listar páginas gerais: {e}")
            return

        unlinked = [p for p in pages if getattr(p, "url", "") not in processed_pages]
        if not unlinked:
            return

        logger.info(f"Encontradas {len(unlinked)} páginas avulsas fora dos módulos...")
        for page_summary in unlinked:
            page_url = getattr(page_summary, "url", "")
            title = getattr(page_summary, "title", "Pagina_Avulsa")
            self._process_and_save_page(
                course=course,
                course_name=course_name,
                module_name="Material Complementar / Páginas Avulsas",
                module_idx=99,
                page_url=page_url,
                page_title=title,
                course_dir=course_dir,
                processed_pages=processed_pages
            )

    def _save_external_link(self, item: ModuleItem, module_name: str, module_idx: int, course_dir: Path, course_name: str):
        """Salva referência limpa a materiais externos e links de apoio, extraindo conteúdo se for Liviu."""
        title = getattr(item, "title", "Link Externo")
        external_url = getattr(item, "external_url", "")
        if not external_url:
            return

        filename = f"Unidade_{module_idx:02d}_Link_{sanitize_filename(title)}.md"
        filepath = course_dir / filename

        # Verifica se o link externo aponta para a plataforma Liviu
        liviu_match = re.search(r"liviu\.com\.br/[^\"\'\s]+/([a-f0-9\-]{36})", external_url, re.IGNORECASE)
        liviu_content = ""
        if liviu_match:
            uuid = liviu_match.group(1)
            liviu_content = fetch_and_parse_liviu(uuid)

        content = (
            f"# {title}\n\n"
            f"- **Disciplina:** {course_name}\n"
            f"- **Módulo:** {module_name}\n"
            f"- **Recurso Externo:** [{title}]({external_url})\n\n"
            "---\n\n"
        )
        if liviu_content:
            content += liviu_content + "\n"
        else:
            content += f"Link oficial de apoio: <{external_url}>\n"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"  -> [link] {filename}")
        except Exception as e:
            logger.debug(f"Erro ao salvar link externo: {e}")

    def _download_course_files(self, course: Course, files_dir: Path):
        """Baixa PDFs e documentos do curso evitando duplicidades desnecessárias."""
        try:
            files = list(course.get_files())
        except Exception as e:
            logger.warning(f"Não foi possível listar arquivos do curso: {e}")
            return

        if not files:
            logger.info("Nenhum arquivo para download neste curso.")
            return

        # Foco em documentos de estudo (PDFs, apresentações, docs)
        valid_extensions = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".zip", ".epub"}
        relevant_files = [
            f for f in files
            if any(getattr(f, "filename", "").lower().endswith(ext) for ext in valid_extensions)
        ]

        logger.info(f"Baixando {len(relevant_files)} arquivos/documentos oficiais...")

        for c_file in relevant_files:
            orig_name = getattr(c_file, "filename", "documento.pdf")
            safe_name = sanitize_filename(orig_name)
            target_path = files_dir / safe_name
            expected_size = getattr(c_file, "size", 0)

            # Evita re-download se o arquivo já existir com tamanho idêntico
            if target_path.exists() and target_path.stat().st_size == expected_size and expected_size > 0:
                logger.debug(f"    [Pular] Já baixado: {safe_name}")
                continue

            download_url = getattr(c_file, "url", None)
            if not download_url:
                continue

            try:
                resp = requests.get(download_url, stream=True, timeout=30)
                if resp.status_code == 200:
                    with open(target_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    logger.info(f"    [OK] Baixado: {safe_name} ({expected_size / 1024:.1f} KB)")

                else:
                    logger.warning(f"    Falha ao baixar {orig_name}: HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"    Erro de conexão ao baixar {orig_name}: {e}")

    def run_all(self, courses: List[Course]):
        """Executa a extração em lote para a lista de cursos fornecida."""
        for course in courses:
            self.extract_course_content(course)
