# -*- coding: utf-8 -*-
"""
Sistema de Feedback do Usuário
Implementa coleta, análise e gestão de feedback dos usuários
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path

class FeedbackType(Enum):
    """Tipos de feedback"""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    GENERAL = "general"
    RATING = "rating"
    USABILITY = "usability"

class FeedbackStatus(Enum):
    """Status do feedback"""
    NEW = "new"
    IN_REVIEW = "in_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"

class Priority(Enum):
    """Prioridade do feedback"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Feedback:
    """Classe para representar um feedback"""
    id: str
    user_id: str
    user_email: str
    feedback_type: FeedbackType
    title: str
    description: str
    rating: Optional[int]  # 1-5 para ratings
    page_url: str
    browser_info: Dict[str, Any]
    screenshot_path: Optional[str]
    status: FeedbackStatus
    priority: Priority
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    admin_notes: str
    votes: int  # Votos de outros usuários
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        data = asdict(self)
        data['feedback_type'] = self.feedback_type.value
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data

class FeedbackSystem:
    """Sistema principal de feedback"""
    
    def __init__(self, db_path: str = "feedback.sqlite"):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Inicializa o banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rating INTEGER,
                    page_url TEXT NOT NULL,
                    browser_info TEXT NOT NULL,
                    screenshot_path TEXT,
                    status TEXT NOT NULL DEFAULT 'new',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT,
                    admin_notes TEXT DEFAULT '',
                    votes INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_votes (
                    id TEXT PRIMARY KEY,
                    feedback_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    vote_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (feedback_id) REFERENCES feedback (id),
                    UNIQUE(feedback_id, user_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_comments (
                    id TEXT PRIMARY KEY,
                    feedback_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (feedback_id) REFERENCES feedback (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_analytics (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    total_feedback INTEGER DEFAULT 0,
                    by_type TEXT NOT NULL DEFAULT '{}',
                    by_status TEXT NOT NULL DEFAULT '{}',
                    avg_rating REAL DEFAULT 0,
                    resolution_time_avg REAL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def submit_feedback(self, 
                       user_id: str,
                       user_email: str,
                       feedback_type: FeedbackType,
                       title: str,
                       description: str,
                       page_url: str,
                       browser_info: Dict[str, Any],
                       rating: Optional[int] = None,
                       screenshot_path: Optional[str] = None,
                       tags: List[str] = None) -> str:
        """Submete um novo feedback"""
        
        feedback_id = str(uuid.uuid4())
        now = datetime.now()
        
        feedback = Feedback(
            id=feedback_id,
            user_id=user_id,
            user_email=user_email,
            feedback_type=feedback_type,
            title=title,
            description=description,
            rating=rating,
            page_url=page_url,
            browser_info=browser_info,
            screenshot_path=screenshot_path,
            status=FeedbackStatus.NEW,
            priority=self._calculate_priority(feedback_type, rating),
            tags=tags or [],
            created_at=now,
            updated_at=now,
            resolved_at=None,
            admin_notes="",
            votes=0
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO feedback (
                    id, user_id, user_email, feedback_type, title, description,
                    rating, page_url, browser_info, screenshot_path, status,
                    priority, tags, created_at, updated_at, resolved_at,
                    admin_notes, votes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.id, feedback.user_id, feedback.user_email,
                feedback.feedback_type.value, feedback.title, feedback.description,
                feedback.rating, feedback.page_url, json.dumps(feedback.browser_info),
                feedback.screenshot_path, feedback.status.value, feedback.priority.value,
                json.dumps(feedback.tags), feedback.created_at.isoformat(),
                feedback.updated_at.isoformat(), None, feedback.admin_notes,
                feedback.votes
            ))
            conn.commit()
        
        return feedback_id
    
    def _calculate_priority(self, feedback_type: FeedbackType, rating: Optional[int]) -> Priority:
        """Calcula prioridade baseada no tipo e rating"""
        if feedback_type == FeedbackType.BUG_REPORT:
            return Priority.HIGH
        elif feedback_type == FeedbackType.RATING and rating and rating <= 2:
            return Priority.HIGH
        elif feedback_type == FeedbackType.FEATURE_REQUEST:
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """Obtém um feedback específico"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_feedback(row)
            return None
    
    def get_all_feedback(self, 
                        status: Optional[FeedbackStatus] = None,
                        feedback_type: Optional[FeedbackType] = None,
                        priority: Optional[Priority] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[Feedback]:
        """Obtém lista de feedback com filtros"""
        
        query = "SELECT * FROM feedback WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if feedback_type:
            query += " AND feedback_type = ?"
            params.append(feedback_type.value)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority.value)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_feedback(row) for row in rows]
    
    def update_feedback_status(self, 
                              feedback_id: str, 
                              status: FeedbackStatus,
                              admin_notes: str = "") -> bool:
        """Atualiza status do feedback"""
        now = datetime.now()
        resolved_at = now if status == FeedbackStatus.RESOLVED else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE feedback 
                SET status = ?, updated_at = ?, resolved_at = ?, admin_notes = ?
                WHERE id = ?
            """, (
                status.value, now.isoformat(), 
                resolved_at.isoformat() if resolved_at else None,
                admin_notes, feedback_id
            ))
            
            return cursor.rowcount > 0
    
    def vote_feedback(self, feedback_id: str, user_id: str, vote_type: str) -> bool:
        """Adiciona voto ao feedback"""
        vote_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                # Adiciona voto
                conn.execute("""
                    INSERT INTO feedback_votes (id, feedback_id, user_id, vote_type, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (vote_id, feedback_id, user_id, vote_type, now.isoformat()))
                
                # Atualiza contador
                if vote_type == "up":
                    conn.execute(
                        "UPDATE feedback SET votes = votes + 1 WHERE id = ?",
                        (feedback_id,)
                    )
                elif vote_type == "down":
                    conn.execute(
                        "UPDATE feedback SET votes = votes - 1 WHERE id = ?",
                        (feedback_id,)
                    )
                
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Usuário já votou
                return False
    
    def add_comment(self, 
                   feedback_id: str,
                   user_id: str,
                   user_email: str,
                   comment: str,
                   is_admin: bool = False) -> str:
        """Adiciona comentário ao feedback"""
        comment_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO feedback_comments 
                (id, feedback_id, user_id, user_email, comment, is_admin, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                comment_id, feedback_id, user_id, user_email, 
                comment, is_admin, now.isoformat()
            ))
            conn.commit()
        
        return comment_id
    
    def get_comments(self, feedback_id: str) -> List[Dict[str, Any]]:
        """Obtém comentários do feedback"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM feedback_comments 
                WHERE feedback_id = ? 
                ORDER BY created_at ASC
            """, (feedback_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Obtém analytics do feedback"""
        start_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total de feedback
            cursor = conn.execute("""
                SELECT COUNT(*) as total FROM feedback 
                WHERE created_at >= ?
            """, (start_date.isoformat(),))
            total = cursor.fetchone()['total']
            
            # Por tipo
            cursor = conn.execute("""
                SELECT feedback_type, COUNT(*) as count 
                FROM feedback 
                WHERE created_at >= ?
                GROUP BY feedback_type
            """, (start_date.isoformat(),))
            by_type = {row['feedback_type']: row['count'] for row in cursor.fetchall()}
            
            # Por status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM feedback 
                WHERE created_at >= ?
                GROUP BY status
            """, (start_date.isoformat(),))
            by_status = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Rating médio
            cursor = conn.execute("""
                SELECT AVG(rating) as avg_rating 
                FROM feedback 
                WHERE rating IS NOT NULL AND created_at >= ?
            """, (start_date.isoformat(),))
            avg_rating = cursor.fetchone()['avg_rating'] or 0
            
            # Tempo médio de resolução
            cursor = conn.execute("""
                SELECT AVG(
                    (julianday(resolved_at) - julianday(created_at)) * 24
                ) as avg_resolution_hours
                FROM feedback 
                WHERE resolved_at IS NOT NULL AND created_at >= ?
            """, (start_date.isoformat(),))
            avg_resolution = cursor.fetchone()['avg_resolution_hours'] or 0
            
            return {
                'total_feedback': total,
                'by_type': by_type,
                'by_status': by_status,
                'avg_rating': round(avg_rating, 2),
                'avg_resolution_hours': round(avg_resolution, 2),
                'period_days': days
            }
    
    def _row_to_feedback(self, row: sqlite3.Row) -> Feedback:
        """Converte row do banco para objeto Feedback"""
        return Feedback(
            id=row['id'],
            user_id=row['user_id'],
            user_email=row['user_email'],
            feedback_type=FeedbackType(row['feedback_type']),
            title=row['title'],
            description=row['description'],
            rating=row['rating'],
            page_url=row['page_url'],
            browser_info=json.loads(row['browser_info']),
            screenshot_path=row['screenshot_path'],
            status=FeedbackStatus(row['status']),
            priority=Priority(row['priority']),
            tags=json.loads(row['tags']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None,
            admin_notes=row['admin_notes'],
            votes=row['votes']
        )
    
    def export_feedback(self, format: str = "json") -> str:
        """Exporta feedback para arquivo"""
        feedback_list = self.get_all_feedback(limit=10000)
        
        if format == "json":
            data = [feedback.to_dict() for feedback in feedback_list]
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        # Adicionar outros formatos conforme necessário
        return ""

# Instância global
feedback_system = FeedbackSystem()