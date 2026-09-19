import re
from typing import List, Optional, Tuple
import requests
from canvasapi import Canvas
from canvasapi.course import Course
from canvasapi.exceptions import InvalidAccessToken, CanvasException

from src.config import CANVAS_API_URL, CANVAS_API_TOKEN, TARGET_COURSES
from src.utils import logger

class CanvasClient:
    """Gerencia a conexão, autenticação e busca de cursos no Canvas LMS."""

    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None):
        self.api_url = api_url or CANVAS_API_URL
        self.api_token = api_token or CANVAS_API_TOKEN
        self.canvas: Optional[Canvas] = None
        self._initialize()

    def _initialize(self):
        if not self.api_url or not self.api_token:
            logger.warning("CANVAS_API_URL ou CANVAS_API_TOKEN não definidos no .env.")
            return

        try:
            self.canvas = Canvas(self.api_url, self.api_token)
        except Exception as e:
            logger.error(f"Falha ao instanciar cliente Canvas API: {e}")
            self.canvas = None

    def test_connection(self) -> Tuple[bool, str]:
        """Testa se as credenciais e URL do Canvas estão operacionais."""
        if not self.canvas:
            return False, "Cliente Canvas não foi inicializado (verifique o arquivo .env)."
        
        try:
            user = self.canvas.get_current_user()
            user_name = getattr(user, "name", "Usuário")
            return True, f"Conexão bem-sucedida com Canvas LMS. Autenticado como: {user_name}"
        except InvalidAccessToken:
            return False, "Token do Canvas inválido ou expirado. Gere um novo token em sua conta no Canvas."
        except Exception as e:
            return False, f"Erro ao conectar com Canvas API ({self.api_url}): {e}"

    def get_all_courses(self) -> List[Course]:
        """Retorna todos os cursos vinculados ao usuário com paginação automática."""
        if not self.canvas:
            logger.error("Cliente Canvas não está pronto.")
            return []

        try:
            # enrollment_state='active' para filtrar disciplinas atuais
            courses_paginated = self.canvas.get_courses(enrollment_state="active")
            courses_list = list(courses_paginated)
            return courses_list
        except Exception as e:
            logger.error(f"Erro ao listar cursos: {e}")
            return []

    def get_target_courses(self) -> List[Course]:
        """
        Localiza os cursos correspondentes às 5 disciplinas ativas definidas.
        Usa correspondência inteligente por código e nome.
        """
        all_courses = self.get_all_courses()
        if not all_courses:
            logger.warning("Nenhum curso ativo retornado pela API do Canvas.")
            return []

        matched_courses: List[Course] = []
        
        def normalize_str(s: str) -> str:
            return re.sub(r"[^\w\s]", "", s).lower().strip()

        target_normalized = [normalize_str(t) for t in TARGET_COURSES]

        logger.info(f"Analisando {len(all_courses)} cursos encontrados no Canvas...")

        for course in all_courses:
            course_name = getattr(course, "name", "")
            course_code = getattr(course, "course_code", "")
            combined = f"{course_code} - {course_name}"
            combined_norm = normalize_str(combined)
            name_norm = normalize_str(course_name)

            is_match = False
            for target_norm in target_normalized:
                # Correspondência se o alvo estiver contido ou bater com código/nome
                if target_norm in combined_norm or name_norm in target_norm or target_norm in name_norm:
                    is_match = True
                    break

            if is_match and course not in matched_courses:
                matched_courses.append(course)
                logger.info(f"  [OK] Disciplina identificada: {course_name} (ID: {course.id})")


        if not matched_courses:
            logger.warning("Nenhum dos cursos cadastrados em TARGET_COURSES foi identificado com precisão.")
            logger.info("Cursos ativos disponíveis na sua conta Canvas:")
            for c in all_courses:
                logger.info(f"  - ID: {c.id} | Nome: {getattr(c, 'name', 'Sem nome')} | Código: {getattr(c, 'course_code', '')}")

        return matched_courses
