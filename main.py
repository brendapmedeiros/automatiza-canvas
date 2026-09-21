#!/usr/bin/env python3
"""
Automacao Academica: Canvas LMS -> Gemini Notebook (NotebookLM) & Google Calendar
Desenvolvido para Brenda Medeiros - Engenharia de Automacao & Operacoes
"""

import sys
import os
import argparse
from pathlib import Path

# Garante que o console do Windows exiba caracteres acentuados sem erro de encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.config import (
    CANVAS_API_URL,
    CANVAS_API_TOKEN,
    OUTPUT_DIR,
    ICS_OUTPUT_FILE,
    TARGET_COURSES
)
from src.utils import logger
from src.canvas_client import CanvasClient
from src.content_extractor import ContentExtractor
from src.calendar_sync import CalendarSyncManager

def show_markdown_preview():
    """Exibe no terminal uma amostra legivel e estruturada do Markdown para captura de tela."""
    preview_file = (
        OUTPUT_DIR
        / "EADCSTAD05_-_DESENVOLVIMENTO_DE_APLICAÇÕES_HÍBRIDAS"
        / "Unidade_02_Desenvolvimento_de_Interfaces_com_HTML5,_CSS3_e_JavaScript.md"
    )
    if not preview_file.exists():
        mds = list(OUTPUT_DIR.glob("**/*.md"))
        if not mds:
            print("[alerta] Nenhum arquivo gerado ainda. Execute 'python app.py' para extrair os materiais.")
            return
        preview_file = mds[0]

    with open(preview_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print("\n--- PREVIA DO MATERIAL GERADO ---")
    print(f"Arquivo: {preview_file.name}")
    print(f"Volume: {preview_file.stat().st_size / 1024:.1f} KB | {len(lines)} linhas de conteudo didatico")
    print("-" * 65 + "\n")

    # Exibe trecho rico com titulo, objetivos, teoria e blocos de codigo
    sample_text = "".join(lines[:50]).strip()
    print(sample_text)

    print("\n" + "-" * 65)
    print(f"[ok] Conteudo integro com mais de {len(lines)} linhas pronto para o NotebookLM.")
    print(f"[ok] Caminho: {preview_file.resolve()}\n")

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Automacao do Canvas LMS para NotebookLM e Google Calendar."
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Executa apenas a extracao de conteudos em Markdown e apostilas."
    )
    parser.add_argument(
        "--calendar-only",
        action="store_true",
        help="Executa apenas a sincronizacao de prazos e geracao de calendario."
    )
    parser.add_argument(
        "--ics-only",
        action="store_true",
        help="Gera apenas o arquivo .ics sem tentar autenticacao OAuth2 do Google Calendar."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Testa credenciais do Canvas e lista as disciplinas identificadas."
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Exibe no terminal uma previa do Markdown gerado para capturas de tela."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    if args.preview:
        show_markdown_preview()
        sys.exit(0)

    print("\nCanvas Academic Automation (v1.0)")
    print("Termo 5 - Integracao Canvas LMS, NotebookLM & Calendar\n")

    # 1. Validacao inicial de ambiente
    if not CANVAS_API_URL or not CANVAS_API_TOKEN:
        logger.error("Configuracoes do Canvas ausentes no arquivo .env")
        sys.exit(1)

    # 2. Inicializacao do Cliente Canvas
    canvas_client = CanvasClient()
    connected, msg = canvas_client.test_connection()
    if not connected:
        logger.error(f"Falha na conexao: {msg}")
        sys.exit(1)
    logger.info(msg)

    # 3. Busca e Identificacao das Disciplinas Ativas
    matched_courses = canvas_client.get_target_courses()
    if not matched_courses:
        logger.warning("Nenhuma disciplina da lista foi encontrada como ativa.")
        sys.exit(0 if args.dry_run else 1)

    if args.dry_run:
        print("\n[ok] Diagnostico concluido: conexao e disciplinas validadas com sucesso.\n")
        sys.exit(0)

    run_extract = not args.calendar_only
    run_calendar = not args.extract_only

    # =========================================================================
    # MODULO 1: EXTRACAO DE CONTEUDOS PARA GEMINI NOTEBOOK (NOTEBOOKLM)
    # =========================================================================
    if run_extract:
        print("\n[extract] Processando conteudos didaticos das disciplinas...")
        extractor = ContentExtractor(output_base_dir=OUTPUT_DIR)
        extractor.run_all(matched_courses)

    # =========================================================================
    # MODULO 2: SINCRONIZACAO DE PRAZOS E CALENDARIO (GOOGLE CALENDAR / ICS)
    # =========================================================================
    if run_calendar:
        print("\n[calendar] Coletando prazos e gerando agenda academica...")
        calendar_mgr = CalendarSyncManager()
        deadlines = calendar_mgr.collect_deadlines_from_canvas(matched_courses)

        ics_path = calendar_mgr.generate_ics_file(deadlines, output_path=ICS_OUTPUT_FILE)
        logger.info(f"[calendar] Arquivo iCalendar gerado: {Path(ics_path).name}")

        if not args.ics_only:
            calendar_mgr.sync_with_google_calendar_api(deadlines)

    # =========================================================================
    # RESUMO FINAL DE EXECUCAO
    # =========================================================================
    print("\n[done] Concluido com sucesso.")
    if run_extract:
        print(f"  Materiais (NotebookLM): {OUTPUT_DIR.resolve()}")
    if run_calendar:
        print(f"  Agenda (.ics): {Path(ICS_OUTPUT_FILE).resolve()}")
    print()

if __name__ == "__main__":
    main()
