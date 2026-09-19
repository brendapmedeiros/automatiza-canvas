import os
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import pytz
from dateutil import parser as date_parser

from icalendar import Calendar, Event, vRecur
from canvasapi.course import Course

from src.config import (
    CALENDAR_ID,
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE,
    ICS_OUTPUT_FILE,
    TIMEZONE,
    CURRENT_YEAR,
    WEEKLY_ROUTINE,
    SPECIAL_MILESTONES,
)
from src.utils import logger

# Google API imports opcionais
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class CalendarSyncManager:
    """
    Módulo 2: Coleta tarefas e questionários do Canvas, gerencia blocos fixos semanais
    e sincroniza com o Google Calendar via API OAuth2 ou arquivo universal .ics.
    """

    def __init__(self, tz_name: str = TIMEZONE):
        self.tz = pytz.timezone(tz_name)

    def collect_deadlines_from_canvas(self, courses: List[Course]) -> List[Dict[str, Any]]:
        """Extrai todas as tarefas (assignments) e questionários (quizzes) com prazo do Canvas."""
        events = []
        logger.info("Coletando prazos avaliativos dos cursos no Canvas...")

        for course in courses:
            course_name = getattr(course, "name", f"Curso {course.id}")
            # 1. Tarefas (Assignments)
            try:
                assignments = list(course.get_assignments())
                for a in assignments:
                    due_at = getattr(a, "due_at", None)
                    if due_at:
                        dt = date_parser.parse(due_at).astimezone(self.tz)
                        title = f"[{course_name}] Tarefa: {getattr(a, 'name', 'Sem Titulo')}"
                        desc = (
                            f"Tarefa da disciplina {course_name}\n"
                            f"Pontos possíveis: {getattr(a, 'points_possible', 'N/A')}\n"
                            f"Link: {getattr(a, 'html_url', '')}"
                        )
                        events.append({
                            "type": "deadline",
                            "summary": title,
                            "due_datetime": dt,
                            "is_all_day": True,
                            "description": desc,
                            "course": course_name,
                        })
            except Exception as e:
                logger.warning(f"Erro ao buscar tarefas em '{course_name}': {e}")

            # 2. Questionários (Quizzes)
            try:
                quizzes = list(course.get_quizzes())
                for q in quizzes:
                    due_at = getattr(q, "due_at", None)
                    if due_at:
                        dt = date_parser.parse(due_at).astimezone(self.tz)
                        title = f"[{course_name}] Questionário: {getattr(q, 'title', 'Sem Titulo')}"
                        desc = (
                            f"Questionário/Avaliação da disciplina {course_name}\n"
                            f"Pontos: {getattr(q, 'points_possible', 'N/A')}\n"
                            f"Link: {getattr(q, 'html_url', '')}"
                        )
                        events.append({
                            "type": "quiz",
                            "summary": title,
                            "due_datetime": dt,
                            "is_all_day": True,
                            "description": desc,
                            "course": course_name,
                        })
            except Exception as e:
                logger.warning(f"Erro ao buscar questionários em '{course_name}': {e}")

        logger.info(f"Total de prazos avaliativos encontrados no Canvas: {len(events)}")
        return events

    def generate_ics_file(self, deadlines: List[Dict[str, Any]], output_path: str = ICS_OUTPUT_FILE) -> str:
        """Gera um arquivo .ics completo com prazos do Canvas, blocos fixos e marcos avaliativos."""
        cal = Calendar()
        cal.add("prodid", "-//Organização Acadêmica - Brenda Medeiros//PT-BR//")
        cal.add("version", "2.0")
        cal.add("x-wr-calname", "Agenda Acadêmica & Rotina")
        cal.add("x-wr-timezone", str(self.tz))

        now = datetime.now(self.tz)

        # 1. Adiciona Prazos Oficiais do Canvas
        for d in deadlines:
            event = Event()
            event.add("summary", d["summary"])
            event.add("description", d["description"])
            event.add("dtstamp", now)

            # Evento de dia inteiro no dia do vencimento
            due_date = d["due_datetime"].date()
            event.add("dtstart", due_date)
            event.add("dtend", due_date + timedelta(days=1))
            event.add("uid", f"canvas-due-{abs(hash(d['summary'] + str(due_date)))}@academico")
            cal.add_component(event)

        # 2. Adiciona Marcos Avaliativos em Destaque (03/10 e 31/10)
        for m in SPECIAL_MILESTONES:
            event = Event()
            event.add("summary", m["summary"])
            event.add("description", m["description"])
            event.add("dtstamp", now)
            m_date = datetime.strptime(m["date"], "%Y-%m-%d").date()
            event.add("dtstart", m_date)
            event.add("dtend", m_date + timedelta(days=1))
            event.add("uid", f"milestone-{m['date']}@academico")
            cal.add_component(event)

        # 3. Adiciona Blocos Fixos Semanais
        # Data de início da recorrência: próxima segunda-feira ou data base
        base_monday = now.date() - timedelta(days=now.weekday())

        for b in WEEKLY_ROUTINE["weekdays"]:
            start_h, start_m = map(int, b["start_time"].split(":"))
            end_h, end_m = map(int, b["end_time"].split(":"))

            start_dt = self.tz.localize(datetime.combine(base_monday, time(start_h, start_m)))
            end_dt = self.tz.localize(datetime.combine(base_monday, time(end_h, end_m)))

            event = Event()
            event.add("summary", b["summary"])
            event.add("description", b["description"])
            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
            event.add("dtstamp", now)
            event.add("rrule", {"freq": "weekly", "byday": ["MO", "TU", "WE", "TH", "FR"]})
            event.add("uid", f"routine-weekday-{abs(hash(b['summary']))}@academico")
            cal.add_component(event)

        # 4. Bloco de Sábado (MVP Mobile Development)
        base_saturday = base_monday + timedelta(days=5)
        for b in WEEKLY_ROUTINE["saturday"]:
            start_h, start_m = map(int, b["start_time"].split(":"))
            end_h, end_m = map(int, b["end_time"].split(":"))

            start_dt = self.tz.localize(datetime.combine(base_saturday, time(start_h, start_m)))
            end_dt = self.tz.localize(datetime.combine(base_saturday, time(end_h, end_m)))

            event = Event()
            event.add("summary", b["summary"])
            event.add("description", b["description"])
            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
            event.add("dtstamp", now)
            event.add("rrule", {"freq": "weekly", "byday": ["SA"]})
            event.add("uid", f"routine-sat-{abs(hash(b['summary']))}@academico")
            cal.add_component(event)

        # Salva o arquivo .ics
        with open(output_path, "wb") as f:
            f.write(cal.to_ical())

        logger.info(f"Arquivo de integracao (.ics) gerado com sucesso: {output_path}")
        return output_path

    def sync_with_google_calendar_api(self, deadlines: List[Dict[str, Any]]) -> bool:
        """Sincroniza os eventos diretamente via Google Calendar API com OAuth2."""
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Bibliotecas do Google API Client não estão instaladas. Use a importação do arquivo .ics.")
            return False

        if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
            logger.info(
                f"Arquivo '{GOOGLE_CREDENTIALS_FILE}' não encontrado. "
                "Para sincronização direta via API, configure o OAuth no Google Cloud Console. "
                "O arquivo .ics já foi gerado e pode ser importado imediatamente na sua agenda."
            )
            return False

        creds = None
        if os.path.exists(GOOGLE_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(GOOGLE_TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        service = build("calendar", "v3", credentials=creds)
        logger.info(f"Conectado ao Google Calendar API. Inserindo eventos na agenda '{CALENDAR_ID}'...")

        # 1. Inserir Prazos do Canvas
        for d in deadlines:
            due_date = d["due_datetime"].date()
            event_body = {
                "summary": d["summary"],
                "description": d["description"],
                "start": {"date": due_date.isoformat()},
                "end": {"date": (due_date + timedelta(days=1)).isoformat()},
            }
            try:
                service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
                logger.info(f"  [OK] Prazo sincronizado no Google Calendar: {d['summary']}")
            except Exception as e:
                logger.warning(f"  Falha ao inserir prazo '{d['summary']}': {e}")

        # 2. Inserir Marcos Especiais (03/10 e 31/10)
        for m in SPECIAL_MILESTONES:
            m_date = datetime.strptime(m["date"], "%Y-%m-%d").date()
            event_body = {
                "summary": m["summary"],
                "description": m["description"],
                "start": {"date": m_date.isoformat()},
                "end": {"date": (m_date + timedelta(days=1)).isoformat()},
            }
            try:
                service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
                logger.info(f"  [OK] Marco especial inserido: {m['summary']}")
            except Exception as e:
                logger.warning(f"  Falha ao inserir marco '{m['summary']}': {e}")

        # 3. Inserir Blocos Fixos Semanais (Recorrentes)
        now = datetime.now(self.tz)
        base_monday = now.date() - timedelta(days=now.weekday())

        for b in WEEKLY_ROUTINE["weekdays"]:
            start_time = f"{base_monday}T{b['start_time']}:00"
            end_time = f"{base_monday}T{b['end_time']}:00"
            event_body = {
                "summary": b["summary"],
                "description": b["description"],
                "start": {"dateTime": start_time, "timeZone": str(self.tz)},
                "end": {"dateTime": end_time, "timeZone": str(self.tz)},
                "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"],
            }
            try:
                service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
                logger.info(f"  [OK] Bloco fixo semanal inserido: {b['summary']}")
            except Exception as e:
                logger.warning(f"  Falha ao inserir rotina semanal '{b['summary']}': {e}")

        # 4. Inserir Bloco de Sábado
        base_saturday = base_monday + timedelta(days=5)
        for b in WEEKLY_ROUTINE["saturday"]:
            start_time = f"{base_saturday}T{b['start_time']}:00"
            end_time = f"{base_saturday}T{b['end_time']}:00"
            event_body = {
                "summary": b["summary"],
                "description": b["description"],
                "start": {"dateTime": start_time, "timeZone": str(self.tz)},
                "end": {"dateTime": end_time, "timeZone": str(self.tz)},
                "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=SA"],
            }
            try:
                service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
                logger.info(f"  [OK] Bloco de sábado inserido: {b['summary']}")
            except Exception as e:
                logger.warning(f"  Falha ao inserir rotina de sábado '{b['summary']}': {e}")

        logger.info("Sincronização com Google Calendar concluída.")
        return True

