import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env se existir
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Canvas API
CANVAS_API_URL = os.getenv("CANVAS_API_URL", "").rstrip("/")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN", "").strip()

# Google Calendar
CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))
GOOGLE_TOKEN_FILE = str(BASE_DIR / "token.json")
ICS_OUTPUT_FILE = str(BASE_DIR / "agenda_academica.ics")

# Diretório de saída dos materiais para o Gemini Notebook (NotebookLM)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "estudos_canvas")))

# Fuso horário e ano letivo
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
CURRENT_YEAR = int(os.getenv("YEAR", "2026"))

# Disciplinas ativas do termo especificadas pela Brenda
TARGET_COURSES = [
    "EADCSTAD05 - Arquitetura e Aplicações para Mobile",
    "EADCSTAD05 - Desenvolvimento de Aplicações Híbridas",
    "EADCSTAD05 - Desenvolvimento de Aplicações Web-Mobile",
    "EADCSTAD05 - Design Thinking e Gestão da Inovação",
    "EADCSTAD05 - MVP Mobile Development",
]

# Blocos Semanais Fixos (Recorrência)
WEEKLY_ROUTINE = {
    "weekdays": [
        {
            "summary": "Trabalho",
            "start_time": "09:00",
            "end_time": "18:00",
            "description": "Bloco de trabalho diário.",
        },
        {
            "summary": "Intervalo / Descompressão",
            "start_time": "18:00",
            "end_time": "19:00",
            "description": "Transição de expediente, alimentação e descanso.",
        },
        {
            "summary": "Foco Acadêmico",
            "start_time": "19:00",
            "end_time": "20:15",
            "description": "Estudo diário das disciplinas ativas do termo (Canvas / NotebookLM).",
        },
    ],
    "saturday": [
        {
            "summary": "MVP Mobile Development",
            "start_time": "10:00",
            "end_time": "12:00",
            "description": "Bloco dedicado ao desenvolvimento e entregas do MVP Mobile Development.",
        }
    ]
}

# Marcos Avaliativos Fixos em Destaque
SPECIAL_MILESTONES = [
    {
        "date": f"{CURRENT_YEAR}-10-03",
        "summary": "Avaliações: Unidades 1 a 3 (Prazo Limite)",
        "description": "Data limite e destaque para a conclusão de todas as avaliações das Unidades 1 a 3 de todas as disciplinas ativas.",
    },
    {
        "date": f"{CURRENT_YEAR}-10-31",
        "summary": "Avaliações Finais / Presenciais",
        "description": "Período de avaliações finais e presenciais do termo acadêmico.",
    }
]

