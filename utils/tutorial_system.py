# -*- coding: utf-8 -*-
"""
Sistema de Recursos Educacionais e Tutoriais
Implementa tutoriais interativos, tours guiados e recursos de aprendizado
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path

class TutorialType(Enum):
    """Tipos de tutorial"""
    INTERACTIVE_TOUR = "interactive_tour"
    VIDEO_TUTORIAL = "video_tutorial"
    STEP_BY_STEP = "step_by_step"
    QUICK_TIP = "quick_tip"
    DOCUMENTATION = "documentation"
    EXAMPLE_PROJECT = "example_project"

class DifficultyLevel(Enum):
    """Níveis de dificuldade"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class TutorialStatus(Enum):
    """Status do tutorial para o usuário"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"

@dataclass
class TutorialStep:
    """Passo individual de um tutorial"""
    id: str
    title: str
    description: str
    target_element: Optional[str]  # Seletor CSS do elemento
    position: str  # top, bottom, left, right
    content: str  # HTML content
    action_required: bool
    validation_script: Optional[str]  # JavaScript para validar ação
    order: int

@dataclass
class Tutorial:
    """Tutorial completo"""
    id: str
    title: str
    description: str
    tutorial_type: TutorialType
    difficulty: DifficultyLevel
    category: str
    tags: List[str]
    estimated_duration: int  # em minutos
    prerequisites: List[str]  # IDs de outros tutoriais
    steps: List[TutorialStep]
    resources: List[Dict[str, str]]  # Links, arquivos, etc.
    created_at: datetime
    updated_at: datetime
    is_active: bool
    completion_rate: float
    rating: float
    total_ratings: int

@dataclass
class UserProgress:
    """Progresso do usuário em um tutorial"""
    id: str
    user_id: str
    tutorial_id: str
    status: TutorialStatus
    current_step: int
    completed_steps: List[str]
    started_at: datetime
    completed_at: Optional[datetime]
    time_spent: int  # em segundos
    rating: Optional[int]
    feedback: Optional[str]

class TutorialSystem:
    """Sistema principal de tutoriais"""
    
    def __init__(self, db_path: str = "tutorials.sqlite"):
        self.db_path = db_path
        self._init_database()
        self._load_default_tutorials()
        
    def _init_database(self):
        """Inicializa o banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tutorials (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    tutorial_type TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    estimated_duration INTEGER NOT NULL,
                    prerequisites TEXT NOT NULL DEFAULT '[]',
                    steps TEXT NOT NULL,
                    resources TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    completion_rate REAL DEFAULT 0,
                    rating REAL DEFAULT 0,
                    total_ratings INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    tutorial_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'not_started',
                    current_step INTEGER DEFAULT 0,
                    completed_steps TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    time_spent INTEGER DEFAULT 0,
                    rating INTEGER,
                    feedback TEXT,
                    FOREIGN KEY (tutorial_id) REFERENCES tutorials (id),
                    UNIQUE(user_id, tutorial_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tutorial_analytics (
                    id TEXT PRIMARY KEY,
                    tutorial_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    views INTEGER DEFAULT 0,
                    starts INTEGER DEFAULT 0,
                    completions INTEGER DEFAULT 0,
                    avg_time_spent REAL DEFAULT 0,
                    drop_off_points TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (tutorial_id) REFERENCES tutorials (id)
                )
            """)
            
            conn.commit()
    
    def _load_default_tutorials(self):
        """Carrega tutoriais padrão"""
        default_tutorials = self._get_default_tutorials()
        
        for tutorial_data in default_tutorials:
            if not self.get_tutorial(tutorial_data['id']):
                self.create_tutorial(**tutorial_data)
    
    def _get_default_tutorials(self) -> List[Dict[str, Any]]:
        """Define tutoriais padrão do sistema"""
        return [
            {
                'id': 'getting-started',
                'title': 'Primeiros Passos no DataMindVV',
                'description': 'Aprenda os conceitos básicos e navegue pela plataforma',
                'tutorial_type': TutorialType.INTERACTIVE_TOUR,
                'difficulty': DifficultyLevel.BEGINNER,
                'category': 'Introdução',
                'tags': ['básico', 'navegação', 'interface'],
                'estimated_duration': 10,
                'prerequisites': [],
                'steps': [
                    {
                        'id': 'welcome',
                        'title': 'Bem-vindo ao DataMindVV',
                        'description': 'Conheça a interface principal',
                        'target_element': '.navbar',
                        'position': 'bottom',
                        'content': '<h4>Bem-vindo!</h4><p>Esta é a barra de navegação principal. Aqui você pode acessar todas as funcionalidades da plataforma.</p>',
                        'action_required': False,
                        'validation_script': None,
                        'order': 1
                    },
                    {
                        'id': 'sidebar',
                        'title': 'Menu Lateral',
                        'description': 'Explore as opções do menu',
                        'target_element': '.sidebar',
                        'position': 'right',
                        'content': '<h4>Menu de Navegação</h4><p>Use este menu para navegar entre as diferentes seções: Dados, Visualizações, Dashboards e mais.</p>',
                        'action_required': False,
                        'validation_script': None,
                        'order': 2
                    }
                ],
                'resources': [
                    {'type': 'documentation', 'title': 'Guia Completo', 'url': '/docs/getting-started'},
                    {'type': 'video', 'title': 'Vídeo Introdutório', 'url': '/videos/intro.mp4'}
                ]
            },
            {
                'id': 'data-upload',
                'title': 'Como Fazer Upload de Dados',
                'description': 'Aprenda a importar e configurar seus dados',
                'tutorial_type': TutorialType.STEP_BY_STEP,
                'difficulty': DifficultyLevel.BEGINNER,
                'category': 'Dados',
                'tags': ['upload', 'dados', 'importação'],
                'estimated_duration': 15,
                'prerequisites': ['getting-started'],
                'steps': [
                    {
                        'id': 'navigate-upload',
                        'title': 'Acesse a Página de Upload',
                        'description': 'Clique no menu Upload',
                        'target_element': 'a[href="/upload"]',
                        'position': 'right',
                        'content': '<h4>Upload de Dados</h4><p>Clique aqui para acessar a página de upload de dados.</p>',
                        'action_required': True,
                        'validation_script': 'return window.location.pathname === "/upload"',
                        'order': 1
                    },
                    {
                        'id': 'select-file',
                        'title': 'Selecione um Arquivo',
                        'description': 'Escolha o arquivo para upload',
                        'target_element': '#upload-area',
                        'position': 'top',
                        'content': '<h4>Seleção de Arquivo</h4><p>Arraste e solte seu arquivo aqui ou clique para selecionar. Suportamos CSV, Excel e JSON.</p>',
                        'action_required': True,
                        'validation_script': 'return document.querySelector("#file-input").files.length > 0',
                        'order': 2
                    }
                ],
                'resources': [
                    {'type': 'sample', 'title': 'Arquivo de Exemplo', 'url': '/sample_data.csv'},
                    {'type': 'documentation', 'title': 'Formatos Suportados', 'url': '/docs/file-formats'}
                ]
            },
            {
                'id': 'create-visualization',
                'title': 'Criando Sua Primeira Visualização',
                'description': 'Aprenda a criar gráficos e visualizações',
                'tutorial_type': TutorialType.STEP_BY_STEP,
                'difficulty': DifficultyLevel.INTERMEDIATE,
                'category': 'Visualizações',
                'tags': ['gráficos', 'visualização', 'charts'],
                'estimated_duration': 20,
                'prerequisites': ['data-upload'],
                'steps': [
                    {
                        'id': 'navigate-viz',
                        'title': 'Acesse Visualizações',
                        'description': 'Vá para a página de visualizações',
                        'target_element': 'a[href="/visualizations"]',
                        'position': 'right',
                        'content': '<h4>Visualizações</h4><p>Aqui você pode criar gráficos incríveis com seus dados.</p>',
                        'action_required': True,
                        'validation_script': 'return window.location.pathname === "/visualizations"',
                        'order': 1
                    },
                    {
                        'id': 'select-chart-type',
                        'title': 'Escolha o Tipo de Gráfico',
                        'description': 'Selecione o tipo de visualização',
                        'target_element': '#chart-type-selector',
                        'position': 'bottom',
                        'content': '<h4>Tipos de Gráfico</h4><p>Escolha entre barras, linhas, pizza e muitos outros tipos de gráfico.</p>',
                        'action_required': True,
                        'validation_script': 'return document.querySelector("#chart-type-selector").value !== ""',
                        'order': 2
                    }
                ],
                'resources': [
                    {'type': 'gallery', 'title': 'Galeria de Exemplos', 'url': '/gallery'},
                    {'type': 'documentation', 'title': 'Tipos de Gráfico', 'url': '/docs/chart-types'}
                ]
            },
            {
                'id': 'dashboard-creation',
                'title': 'Construindo Dashboards',
                'description': 'Crie dashboards interativos e informativos',
                'tutorial_type': TutorialType.STEP_BY_STEP,
                'difficulty': DifficultyLevel.ADVANCED,
                'category': 'Dashboards',
                'tags': ['dashboard', 'painel', 'kpi'],
                'estimated_duration': 30,
                'prerequisites': ['create-visualization'],
                'steps': [],
                'resources': []
            }
        ]
    
    def create_tutorial(self, 
                       id: str,
                       title: str,
                       description: str,
                       tutorial_type: TutorialType,
                       difficulty: DifficultyLevel,
                       category: str,
                       tags: List[str],
                       estimated_duration: int,
                       prerequisites: List[str],
                       steps: List[Dict[str, Any]],
                       resources: List[Dict[str, str]]) -> str:
        """Cria um novo tutorial"""
        
        now = datetime.now()
        
        # Converte steps para objetos TutorialStep
        tutorial_steps = []
        for step_data in steps:
            step = TutorialStep(**step_data)
            tutorial_steps.append(step)
        
        tutorial = Tutorial(
            id=id,
            title=title,
            description=description,
            tutorial_type=tutorial_type,
            difficulty=difficulty,
            category=category,
            tags=tags,
            estimated_duration=estimated_duration,
            prerequisites=prerequisites,
            steps=tutorial_steps,
            resources=resources,
            created_at=now,
            updated_at=now,
            is_active=True,
            completion_rate=0.0,
            rating=0.0,
            total_ratings=0
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tutorials (
                    id, title, description, tutorial_type, difficulty, category,
                    tags, estimated_duration, prerequisites, steps, resources,
                    created_at, updated_at, is_active, completion_rate, rating, total_ratings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tutorial.id, tutorial.title, tutorial.description,
                tutorial.tutorial_type.value, tutorial.difficulty.value,
                tutorial.category, json.dumps(tutorial.tags),
                tutorial.estimated_duration, json.dumps(tutorial.prerequisites),
                json.dumps([asdict(step) for step in tutorial.steps]),
                json.dumps(tutorial.resources), tutorial.created_at.isoformat(),
                tutorial.updated_at.isoformat(), tutorial.is_active,
                tutorial.completion_rate, tutorial.rating, tutorial.total_ratings
            ))
            conn.commit()
        
        return id
    
    def get_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """Obtém um tutorial específico"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tutorials WHERE id = ?", (tutorial_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_tutorial(row)
            return None
    
    def get_tutorials_by_category(self, category: str) -> List[Tutorial]:
        """Obtém tutoriais por categoria"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tutorials WHERE category = ? AND is_active = TRUE ORDER BY difficulty, estimated_duration",
                (category,)
            )
            rows = cursor.fetchall()
            
            return [self._row_to_tutorial(row) for row in rows]
    
    def get_recommended_tutorials(self, user_id: str, limit: int = 5) -> List[Tutorial]:
        """Obtém tutoriais recomendados para o usuário"""
        # Lógica de recomendação baseada no progresso do usuário
        completed_tutorials = self.get_user_completed_tutorials(user_id)
        completed_ids = [t.tutorial_id for t in completed_tutorials]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Busca tutoriais que o usuário pode fazer (pré-requisitos atendidos)
            query = """
                SELECT * FROM tutorials 
                WHERE is_active = TRUE 
                AND id NOT IN ({}) 
                ORDER BY rating DESC, completion_rate DESC
                LIMIT ?
            """.format(','.join(['?' for _ in completed_ids]) if completed_ids else "''")
            
            params = completed_ids + [limit] if completed_ids else [limit]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            tutorials = [self._row_to_tutorial(row) for row in rows]
            
            # Filtra por pré-requisitos
            recommended = []
            for tutorial in tutorials:
                if all(prereq in completed_ids for prereq in tutorial.prerequisites):
                    recommended.append(tutorial)
            
            return recommended[:limit]
    
    def start_tutorial(self, user_id: str, tutorial_id: str) -> str:
        """Inicia um tutorial para o usuário"""
        progress_id = str(uuid.uuid4())
        now = datetime.now()
        
        progress = UserProgress(
            id=progress_id,
            user_id=user_id,
            tutorial_id=tutorial_id,
            status=TutorialStatus.IN_PROGRESS,
            current_step=0,
            completed_steps=[],
            started_at=now,
            completed_at=None,
            time_spent=0,
            rating=None,
            feedback=None
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_progress (
                    id, user_id, tutorial_id, status, current_step, completed_steps,
                    started_at, completed_at, time_spent, rating, feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                progress.id, progress.user_id, progress.tutorial_id,
                progress.status.value, progress.current_step,
                json.dumps(progress.completed_steps), progress.started_at.isoformat(),
                None, progress.time_spent, progress.rating, progress.feedback
            ))
            conn.commit()
        
        return progress_id
    
    def update_progress(self, 
                       user_id: str, 
                       tutorial_id: str, 
                       current_step: int,
                       completed_steps: List[str],
                       time_spent: int) -> bool:
        """Atualiza progresso do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE user_progress 
                SET current_step = ?, completed_steps = ?, time_spent = ?
                WHERE user_id = ? AND tutorial_id = ?
            """, (
                current_step, json.dumps(completed_steps), time_spent,
                user_id, tutorial_id
            ))
            
            return cursor.rowcount > 0
    
    def complete_tutorial(self, 
                         user_id: str, 
                         tutorial_id: str,
                         rating: Optional[int] = None,
                         feedback: Optional[str] = None) -> bool:
        """Marca tutorial como completo"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE user_progress 
                SET status = ?, completed_at = ?, rating = ?, feedback = ?
                WHERE user_id = ? AND tutorial_id = ?
            """, (
                TutorialStatus.COMPLETED.value, now.isoformat(),
                rating, feedback, user_id, tutorial_id
            ))
            
            # Atualiza estatísticas do tutorial
            if rating:
                conn.execute("""
                    UPDATE tutorials 
                    SET total_ratings = total_ratings + 1,
                        rating = (rating * total_ratings + ?) / (total_ratings + 1)
                    WHERE id = ?
                """, (rating, tutorial_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_user_progress(self, user_id: str, tutorial_id: str) -> Optional[UserProgress]:
        """Obtém progresso do usuário em um tutorial"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM user_progress WHERE user_id = ? AND tutorial_id = ?",
                (user_id, tutorial_id)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_progress(row)
            return None
    
    def get_user_completed_tutorials(self, user_id: str) -> List[UserProgress]:
        """Obtém tutoriais completados pelo usuário"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM user_progress WHERE user_id = ? AND status = ?",
                (user_id, TutorialStatus.COMPLETED.value)
            )
            rows = cursor.fetchall()
            
            return [self._row_to_progress(row) for row in rows]
    
    def get_tutorial_analytics(self, tutorial_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtém analytics de um tutorial"""
        start_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Estatísticas básicas
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_starts,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completions,
                    AVG(time_spent) as avg_time,
                    AVG(rating) as avg_rating
                FROM user_progress 
                WHERE tutorial_id = ? AND started_at >= ?
            """, (tutorial_id, start_date.isoformat()))
            
            stats = cursor.fetchone()
            
            completion_rate = (stats['completions'] / stats['total_starts'] * 100) if stats['total_starts'] > 0 else 0
            
            return {
                'tutorial_id': tutorial_id,
                'total_starts': stats['total_starts'],
                'completions': stats['completions'],
                'completion_rate': round(completion_rate, 2),
                'avg_time_minutes': round((stats['avg_time'] or 0) / 60, 2),
                'avg_rating': round(stats['avg_rating'] or 0, 2),
                'period_days': days
            }
    
    def _row_to_tutorial(self, row: sqlite3.Row) -> Tutorial:
        """Converte row do banco para objeto Tutorial"""
        steps_data = json.loads(row['steps'])
        steps = [TutorialStep(**step_data) for step_data in steps_data]
        
        return Tutorial(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            tutorial_type=TutorialType(row['tutorial_type']),
            difficulty=DifficultyLevel(row['difficulty']),
            category=row['category'],
            tags=json.loads(row['tags']),
            estimated_duration=row['estimated_duration'],
            prerequisites=json.loads(row['prerequisites']),
            steps=steps,
            resources=json.loads(row['resources']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            is_active=row['is_active'],
            completion_rate=row['completion_rate'],
            rating=row['rating'],
            total_ratings=row['total_ratings']
        )
    
    def _row_to_progress(self, row: sqlite3.Row) -> UserProgress:
        """Converte row do banco para objeto UserProgress"""
        return UserProgress(
            id=row['id'],
            user_id=row['user_id'],
            tutorial_id=row['tutorial_id'],
            status=TutorialStatus(row['status']),
            current_step=row['current_step'],
            completed_steps=json.loads(row['completed_steps']),
            started_at=datetime.fromisoformat(row['started_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            time_spent=row['time_spent'],
            rating=row['rating'],
            feedback=row['feedback']
        )

# Instância global
tutorial_system = TutorialSystem()