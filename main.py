#!/usr/bin/env python3
"""
================================================================================
Automacao Academica: Canvas LMS -> Gemini Notebook (NotebookLM) & Google Calendar
Desenvolvido para Brenda Medeiros - Engenharia de Automacao & Operacoes
================================================================================
"""

import sys
import os
import io
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

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Automacao completa do Canvas LMS para NotebookLM e Google Calendar."
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Executa apenas o Modulo 1 (Extracao de conteudos em Markdown e PDFs para NotebookLM)."
    )
    parser.add_argument(
        "--calendar-only",
        action="store_true",
        help="Executa apenas o Modulo 2 (Sincronizacao de prazos e geracao de calendario)."
    )
    parser.add_argument(
        "--ics-only",
        action="store_true",
        help="Gera apenas o arquivo .ics sem tentar autenticacao OAuth2 do Google Calendar."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Testa credenciais do Canvas e lista as disciplinas identificadas sem baixar arquivos."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    print("\n" + "=" * 75)
    print("SISTEMA DE AUTOMACAO ACADEMICA: CANVAS LMS -> NOTEBOOKLM & CALENDAR")
    print("=" * 75 + "\n")

    # 1. Validação inicial de ambiente
    if not CANVAS_API_URL or not CANVAS_API_TOKEN:
        logger.error("Configurações do Canvas ausentes no arquivo .env!")
        print("\n[Atencao] Siga estes passos para configurar:")
        print("  1. Copie o arquivo '.env.example' para '.env'")
        print("  2. Preencha CANVAS_API_URL (ex: https://canvas.instructure.com)")
        print("  3. Preencha CANVAS_API_TOKEN com seu token de acesso pessoal")
        sys.exit(1)

    # 2. Inicialização do Cliente Canvas
    logger.info("Inicializando conexão com a API do Canvas...")
    canvas_client = CanvasClient()
    connected, msg = canvas_client.test_connection()
    if not connected:
        logger.error(f"Falha na conexão com o Canvas: {msg}")
        sys.exit(1)
    logger.info(msg)

    # 3. Busca e Identificação das Disciplinas Ativas
    matched_courses = canvas_client.get_target_courses()
    if not matched_courses:
        logger.warning(
            "Nenhuma das disciplinas da lista TARGET_COURSES foi encontrada como ativa. "
            "Verifique os nomes listados no log acima."
        )
        if args.dry_run:
            sys.exit(0)

    # Se for apenas validação rápida (--dry-run)
    if args.dry_run:
        print("\n--- MODO DE DIAGNOSTICO (DRY-RUN) ---")
        print(f"Total de disciplinas ativas selecionadas: {len(matched_courses)}")
        for c in matched_courses:
            print(f"  - {c.name} (ID: {c.id})")
        print("\nConexão e disciplinas validadas com sucesso. Pronto para execução completa!")
        sys.exit(0)

    run_extract = not args.calendar_only
    run_calendar = not args.extract_only

    # =========================================================================
    # MODULO 1: EXTRACAO DE CONTEUDOS PARA GEMINI NOTEBOOK (NOTEBOOKLM)
    # =========================================================================
    if run_extract:
        print("\n" + "-" * 75)
        print("MODULO 1: Extraindo Conteudos Textuais e PDFs")
        print("-" * 75)
        extractor = ContentExtractor(output_base_dir=OUTPUT_DIR)
        extractor.run_all(matched_courses)
        logger.info(f"Conteudos gerados com sucesso na pasta: {OUTPUT_DIR.resolve()}")

    # =========================================================================
    # MODULO 2: SINCRONIZACAO DE PRAZOS E CALENDARIO (GOOGLE CALENDAR / ICS)
    # =========================================================================
    if run_calendar:
        print("\n" + "-" * 75)
        print("MODULO 2: Sincronizacao de Prazos e Calendario")
        print("-" * 75)
        calendar_mgr = CalendarSyncManager()
        deadlines = calendar_mgr.collect_deadlines_from_canvas(matched_courses)

        # Sempre gera o arquivo .ics como entregável imediato
        ics_path = calendar_mgr.generate_ics_file(deadlines, output_path=ICS_OUTPUT_FILE)
        logger.info(f"Arquivo iCalendar gerado: {Path(ics_path).resolve()}")

        # Se não for --ics-only, tenta sincronizar diretamente via API
        if not args.ics_only:
            logger.info("Tentando sincronizacao direta via Google Calendar API...")
            calendar_mgr.sync_with_google_calendar_api(deadlines)

    # =========================================================================
    # RESUMO FINAL DE EXECUCAO
    # =========================================================================
    print("\n" + "=" * 75)
    print("PROCESSO CONCLUIDO COM SUCESSO!")
    print("=" * 75)
    if run_extract:
        print(f"Base de Estudos (NotebookLM): {OUTPUT_DIR.resolve()}")
        print("   -> Faca upload dos arquivos .md e PDFs diretamente como fontes no NotebookLM.")
    if run_calendar:
        print(f"Arquivo de Agenda (.ics): {Path(ICS_OUTPUT_FILE).resolve()}")
        print("   -> Para importar no Google Calendar: Configuracoes > Importar e Exportar > Importar.")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    main()

