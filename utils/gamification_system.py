# -*- coding: utf-8 -*-
"""
Sistema de Gamificação
Implementa conquistas, pontos, rankings e elementos de gamificação
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path
import math

class AchievementType(Enum):
    """Tipos de conquista"""
    MILESTONE = "milestone"  # Marcos (ex: 100 dashboards criados)
    STREAK = "streak"        # Sequências (ex: 7 dias consecutivos)
    SKILL = "skill"          # Habilidades (ex: usar 10 tipos de gráfico)
    SOCIAL = "social"        # Sociais (ex: compartilhar 5 dashboards)
    EXPLORATION = "exploration"  # Exploração (ex: usar todas as funcionalidades)
    QUALITY = "quality"      # Qualidade (ex: dashboard com alta avaliação)
    SPEED = "speed"          # Velocidade (ex: criar dashboard em < 5 min)
    COLLABORATION = "collaboration"  # Colaboração (ex: trabalhar com 3 pessoas)

class BadgeRarity(Enum):
    """Raridade dos badges"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class ActivityType(Enum):
    """Tipos de atividade que geram pontos"""
    CREATE_DASHBOARD = "create_dashboard"
    SHARE_DASHBOARD = "share_dashboard"
    VIEW_DASHBOARD = "view_dashboard"
    CREATE_CHART = "create_chart"
    UPLOAD_DATA = "upload_data"
    COMMENT = "comment"
    LIKE = "like"
    HELP_USER = "help_user"
    COMPLETE_TUTORIAL = "complete_tutorial"
    LOGIN_DAILY = "login_daily"
    INVITE_USER = "invite_user"
    OPTIMIZE_QUERY = "optimize_query"
    DISCOVER_INSIGHT = "discover_insight"
    EXPORT_REPORT = "export_report"
    USE_ADVANCED_FEATURE = "use_advanced_feature"

@dataclass
class Achievement:
    """Conquista/Badge"""
    id: str
    name: str
    description: str
    icon: str
    achievement_type: AchievementType
    rarity: BadgeRarity
    points: int
    criteria: Dict[str, Any]  # Critérios para desbloquear
    is_hidden: bool  # Se deve ser mostrado antes de ser desbloqueado
    category: str
    unlock_message: str
    prerequisites: List[str]  # IDs de achievements necessários
    is_active: bool

@dataclass
class UserAchievement:
    """Conquista desbloqueada pelo usuário"""
    id: str
    user_id: str
    achievement_id: str
    unlocked_at: datetime
    progress_data: Dict[str, Any]  # Dados do progresso

@dataclass
class UserStats:
    """Estatísticas do usuário"""
    user_id: str
    total_points: int
    level: int
    experience: int
    experience_to_next_level: int
    achievements_count: int
    rank_position: int
    streak_days: int
    last_activity: datetime
    activities_count: Dict[str, int]
    monthly_points: int
    weekly_points: int

@dataclass
class Activity:
    """Atividade do usuário"""
    id: str
    user_id: str
    activity_type: ActivityType
    points_earned: int
    metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class Level:
    """Nível do usuário"""
    level: int
    name: str
    min_experience: int
    max_experience: int
    benefits: List[str]
    icon: str
    color: str

class GamificationSystem:
    """Sistema principal de gamificação"""
    
    def __init__(self, db_path: str = "gamification.sqlite"):
        self.db_path = db_path
        self._init_database()
        self._load_default_achievements()
        self._load_default_levels()
        
    def _init_database(self):
        """Inicializa o banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            # Tabela de conquistas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    icon TEXT NOT NULL,
                    achievement_type TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    criteria TEXT NOT NULL,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    category TEXT NOT NULL,
                    unlock_message TEXT NOT NULL,
                    prerequisites TEXT NOT NULL DEFAULT '[]',
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Tabela de conquistas dos usuários
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    achievement_id TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    progress_data TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (achievement_id) REFERENCES achievements (id),
                    UNIQUE(user_id, achievement_id)
                )
            """)
            
            # Tabela de estatísticas dos usuários
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY,
                    total_points INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    achievements_count INTEGER DEFAULT 0,
                    streak_days INTEGER DEFAULT 0,
                    last_activity TEXT,
                    activities_count TEXT NOT NULL DEFAULT '{}',
                    monthly_points INTEGER DEFAULT 0,
                    weekly_points INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de atividades
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    points_earned INTEGER NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            
            # Tabela de níveis
            conn.execute("""
                CREATE TABLE IF NOT EXISTS levels (
                    level INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    min_experience INTEGER NOT NULL,
                    max_experience INTEGER NOT NULL,
                    benefits TEXT NOT NULL DEFAULT '[]',
                    icon TEXT NOT NULL,
                    color TEXT NOT NULL
                )
            """)
            
            # Tabela de progresso das conquistas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS achievement_progress (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    achievement_id TEXT NOT NULL,
                    current_value INTEGER DEFAULT 0,
                    target_value INTEGER NOT NULL,
                    progress_data TEXT NOT NULL DEFAULT '{}',
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (achievement_id) REFERENCES achievements (id),
                    UNIQUE(user_id, achievement_id)
                )
            """)
            
            # Índices para performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_user ON activities(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_achievement_progress_user ON achievement_progress(user_id)")
            
            conn.commit()
    
    def _load_default_achievements(self):
        """Carrega conquistas padrão"""
        default_achievements = [
            # Marcos de criação
            {
                'id': 'first_dashboard',
                'name': 'Primeiro Passo',
                'description': 'Crie seu primeiro dashboard',
                'icon': '🎯',
                'achievement_type': AchievementType.MILESTONE,
                'rarity': BadgeRarity.COMMON,
                'points': 50,
                'criteria': {'activity_type': 'create_dashboard', 'count': 1},
                'category': 'Criação',
                'unlock_message': 'Parabéns! Você criou seu primeiro dashboard!'
            },
            {
                'id': 'dashboard_creator',
                'name': 'Criador de Dashboards',
                'description': 'Crie 10 dashboards',
                'icon': '📊',
                'achievement_type': AchievementType.MILESTONE,
                'rarity': BadgeRarity.UNCOMMON,
                'points': 200,
                'criteria': {'activity_type': 'create_dashboard', 'count': 10},
                'category': 'Criação',
                'unlock_message': 'Você está se tornando um expert em dashboards!'
            },
            {
                'id': 'dashboard_master',
                'name': 'Mestre dos Dashboards',
                'description': 'Crie 50 dashboards',
                'icon': '👑',
                'achievement_type': AchievementType.MILESTONE,
                'rarity': BadgeRarity.EPIC,
                'points': 1000,
                'criteria': {'activity_type': 'create_dashboard', 'count': 50},
                'category': 'Criação',
                'unlock_message': 'Você é um verdadeiro mestre dos dashboards!'
            },
            
            # Sequências
            {
                'id': 'week_streak',
                'name': 'Semana Dedicada',
                'description': 'Acesse a plataforma por 7 dias consecutivos',
                'icon': '🔥',
                'achievement_type': AchievementType.STREAK,
                'rarity': BadgeRarity.UNCOMMON,
                'points': 150,
                'criteria': {'streak_type': 'daily_login', 'days': 7},
                'category': 'Dedicação',
                'unlock_message': 'Sua dedicação está em chamas!'
            },
            {
                'id': 'month_streak',
                'name': 'Mês Consistente',
                'description': 'Acesse a plataforma por 30 dias consecutivos',
                'icon': '🌟',
                'achievement_type': AchievementType.STREAK,
                'rarity': BadgeRarity.RARE,
                'points': 500,
                'criteria': {'streak_type': 'daily_login', 'days': 30},
                'category': 'Dedicação',
                'unlock_message': 'Sua consistência é impressionante!'
            },
            
            # Habilidades
            {
                'id': 'chart_explorer',
                'name': 'Explorador de Gráficos',
                'description': 'Use 5 tipos diferentes de gráficos',
                'icon': '📈',
                'achievement_type': AchievementType.SKILL,
                'rarity': BadgeRarity.UNCOMMON,
                'points': 100,
                'criteria': {'unique_chart_types': 5},
                'category': 'Habilidade',
                'unlock_message': 'Você domina diversos tipos de visualização!'
            },
            {
                'id': 'data_scientist',
                'name': 'Cientista de Dados',
                'description': 'Use funcionalidades avançadas de análise',
                'icon': '🔬',
                'achievement_type': AchievementType.SKILL,
                'rarity': BadgeRarity.RARE,
                'points': 300,
                'criteria': {'advanced_features_used': 3},
                'category': 'Habilidade',
                'unlock_message': 'Você está dominando a ciência de dados!'
            },
            
            # Sociais
            {
                'id': 'first_share',
                'name': 'Compartilhador',
                'description': 'Compartilhe seu primeiro dashboard',
                'icon': '🤝',
                'achievement_type': AchievementType.SOCIAL,
                'rarity': BadgeRarity.COMMON,
                'points': 75,
                'criteria': {'activity_type': 'share_dashboard', 'count': 1},
                'category': 'Social',
                'unlock_message': 'Compartilhar conhecimento é poder!'
            },
            {
                'id': 'community_helper',
                'name': 'Ajudante da Comunidade',
                'description': 'Ajude 10 usuários com comentários úteis',
                'icon': '💡',
                'achievement_type': AchievementType.SOCIAL,
                'rarity': BadgeRarity.RARE,
                'points': 400,
                'criteria': {'helpful_comments': 10},
                'category': 'Social',
                'unlock_message': 'Você é um pilar da nossa comunidade!'
            },
            
            # Exploração
            {
                'id': 'feature_explorer',
                'name': 'Explorador de Funcionalidades',
                'description': 'Use pelo menos uma vez cada funcionalidade principal',
                'icon': '🗺️',
                'achievement_type': AchievementType.EXPLORATION,
                'rarity': BadgeRarity.UNCOMMON,
                'points': 250,
                'criteria': {'features_explored': ['dashboard', 'charts', 'data_upload', 'sharing', 'export']},
                'category': 'Exploração',
                'unlock_message': 'Você conhece todos os cantos da plataforma!'
            },
            
            # Qualidade
            {
                'id': 'quality_creator',
                'name': 'Criador de Qualidade',
                'description': 'Tenha um dashboard com mais de 100 visualizações',
                'icon': '⭐',
                'achievement_type': AchievementType.QUALITY,
                'rarity': BadgeRarity.RARE,
                'points': 350,
                'criteria': {'dashboard_views': 100},
                'category': 'Qualidade',
                'unlock_message': 'Seu trabalho é reconhecido pela comunidade!'
            },
            
            # Velocidade
            {
                'id': 'speed_creator',
                'name': 'Criador Veloz',
                'description': 'Crie um dashboard em menos de 5 minutos',
                'icon': '⚡',
                'achievement_type': AchievementType.SPEED,
                'rarity': BadgeRarity.UNCOMMON,
                'points': 150,
                'criteria': {'creation_time_seconds': 300},
                'category': 'Velocidade',
                'unlock_message': 'Velocidade e eficiência em perfeita harmonia!'
            },
            
            # Legendárias
            {
                'id': 'platform_legend',
                'name': 'Lenda da Plataforma',
                'description': 'Alcance 10.000 pontos totais',
                'icon': '🏆',
                'achievement_type': AchievementType.MILESTONE,
                'rarity': BadgeRarity.LEGENDARY,
                'points': 2000,
                'criteria': {'total_points': 10000},
                'category': 'Lendário',
                'unlock_message': 'Você se tornou uma lenda! Parabéns!'
            }
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for achievement in default_achievements:
                conn.execute("""
                    INSERT OR IGNORE INTO achievements (
                        id, name, description, icon, achievement_type, rarity,
                        points, criteria, is_hidden, category, unlock_message,
                        prerequisites, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    achievement['id'], achievement['name'], achievement['description'],
                    achievement['icon'], achievement['achievement_type'].value,
                    achievement['rarity'].value, achievement['points'],
                    json.dumps(achievement['criteria']), achievement.get('is_hidden', False),
                    achievement['category'], achievement['unlock_message'],
                    json.dumps(achievement.get('prerequisites', [])), True
                ))
            conn.commit()
    
    def _load_default_levels(self):
        """Carrega níveis padrão"""
        levels = [
            {'level': 1, 'name': 'Iniciante', 'min_exp': 0, 'max_exp': 100, 'icon': '🌱', 'color': '#4CAF50'},
            {'level': 2, 'name': 'Aprendiz', 'min_exp': 100, 'max_exp': 250, 'icon': '📚', 'color': '#2196F3'},
            {'level': 3, 'name': 'Praticante', 'min_exp': 250, 'max_exp': 500, 'icon': '🔧', 'color': '#FF9800'},
            {'level': 4, 'name': 'Competente', 'min_exp': 500, 'max_exp': 1000, 'icon': '⚡', 'color': '#9C27B0'},
            {'level': 5, 'name': 'Proficiente', 'min_exp': 1000, 'max_exp': 2000, 'icon': '🎯', 'color': '#E91E63'},
            {'level': 6, 'name': 'Expert', 'min_exp': 2000, 'max_exp': 4000, 'icon': '🏅', 'color': '#FF5722'},
            {'level': 7, 'name': 'Mestre', 'min_exp': 4000, 'max_exp': 8000, 'icon': '👑', 'color': '#795548'},
            {'level': 8, 'name': 'Guru', 'min_exp': 8000, 'max_exp': 15000, 'icon': '🧙', 'color': '#607D8B'},
            {'level': 9, 'name': 'Lenda', 'min_exp': 15000, 'max_exp': 30000, 'icon': '🏆', 'color': '#FFD700'},
            {'level': 10, 'name': 'Imortal', 'min_exp': 30000, 'max_exp': 999999, 'icon': '💎', 'color': '#00BCD4'}
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for level in levels:
                benefits = [
                    f"Acesso a funcionalidades de nível {level['level']}",
                    f"Título exclusivo: {level['name']}",
                    f"Ícone especial: {level['icon']}"
                ]
                
                conn.execute("""
                    INSERT OR IGNORE INTO levels (
                        level, name, min_experience, max_experience, benefits, icon, color
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    level['level'], level['name'], level['min_exp'], level['max_exp'],
                    json.dumps(benefits), level['icon'], level['color']
                ))
            conn.commit()
    
    def record_activity(self, 
                       user_id: str,
                       activity_type: ActivityType,
                       metadata: Dict[str, Any] = None) -> int:
        """Registra uma atividade e retorna pontos ganhos"""
        
        # Calcula pontos baseado no tipo de atividade
        points_map = {
            ActivityType.CREATE_DASHBOARD: 50,
            ActivityType.SHARE_DASHBOARD: 25,
            ActivityType.VIEW_DASHBOARD: 2,
            ActivityType.CREATE_CHART: 10,
            ActivityType.UPLOAD_DATA: 15,
            ActivityType.COMMENT: 5,
            ActivityType.LIKE: 1,
            ActivityType.HELP_USER: 20,
            ActivityType.COMPLETE_TUTORIAL: 30,
            ActivityType.LOGIN_DAILY: 10,
            ActivityType.INVITE_USER: 100,
            ActivityType.OPTIMIZE_QUERY: 40,
            ActivityType.DISCOVER_INSIGHT: 60,
            ActivityType.EXPORT_REPORT: 15,
            ActivityType.USE_ADVANCED_FEATURE: 35
        }
        
        points = points_map.get(activity_type, 5)
        
        # Aplica multiplicadores baseado em metadata
        if metadata:
            # Bônus por qualidade
            if metadata.get('quality_score', 0) > 0.8:
                points = int(points * 1.5)
            
            # Bônus por complexidade
            if metadata.get('complexity', 'simple') == 'advanced':
                points = int(points * 1.3)
        
        # Registra atividade
        activity_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # Insere atividade
            conn.execute("""
                INSERT INTO activities (id, user_id, activity_type, points_earned, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                activity_id, user_id, activity_type.value, points,
                json.dumps(metadata or {}), now.isoformat()
            ))
            
            # Atualiza estatísticas do usuário
            self._update_user_stats(conn, user_id, points, activity_type, now)
            
            conn.commit()
        
        # Verifica conquistas
        self._check_achievements(user_id, activity_type, metadata)
        
        return points
    
    def _update_user_stats(self, conn, user_id: str, points: int, activity_type: ActivityType, timestamp: datetime):
        """Atualiza estatísticas do usuário"""
        
        # Obtém estatísticas atuais
        cursor = conn.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            # Atualiza existente
            current_points = row[1] + points
            current_exp = row[3] + points
            activities_count = json.loads(row[7])
            activities_count[activity_type.value] = activities_count.get(activity_type.value, 0) + 1
            
            # Calcula novo nível
            new_level = self._calculate_level(current_exp)
            
            # Atualiza streak se for login diário
            streak_days = row[5]
            if activity_type == ActivityType.LOGIN_DAILY:
                last_activity = datetime.fromisoformat(row[6]) if row[6] else None
                if last_activity and (timestamp.date() - last_activity.date()).days == 1:
                    streak_days += 1
                elif not last_activity or (timestamp.date() - last_activity.date()).days > 1:
                    streak_days = 1
            
            conn.execute("""
                UPDATE user_stats SET
                    total_points = ?, level = ?, experience = ?,
                    streak_days = ?, last_activity = ?, activities_count = ?
                WHERE user_id = ?
            """, (
                current_points, new_level, current_exp, streak_days,
                timestamp.isoformat(), json.dumps(activities_count), user_id
            ))
        else:
            # Cria novo
            activities_count = {activity_type.value: 1}
            level = self._calculate_level(points)
            
            conn.execute("""
                INSERT INTO user_stats (
                    user_id, total_points, level, experience, achievements_count,
                    streak_days, last_activity, activities_count, monthly_points,
                    weekly_points, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, points, level, points, 0, 1, timestamp.isoformat(),
                json.dumps(activities_count), points, points, timestamp.isoformat()
            ))
    
    def _calculate_level(self, experience: int) -> int:
        """Calcula nível baseado na experiência"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT level FROM levels WHERE min_experience <= ? ORDER BY level DESC LIMIT 1",
                (experience,)
            )
            row = cursor.fetchone()
            return row[0] if row else 1
    
    def _check_achievements(self, user_id: str, activity_type: ActivityType, metadata: Dict[str, Any] = None):
        """Verifica se o usuário desbloqueou novas conquistas"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Obtém conquistas não desbloqueadas
            cursor = conn.execute("""
                SELECT a.* FROM achievements a
                WHERE a.is_active = 1
                AND a.id NOT IN (
                    SELECT achievement_id FROM user_achievements WHERE user_id = ?
                )
            """, (user_id,))
            
            achievements = cursor.fetchall()
            
            for achievement in achievements:
                if self._check_achievement_criteria(user_id, achievement, activity_type, metadata):
                    self._unlock_achievement(user_id, achievement[0])  # achievement[0] é o ID
    
    def _check_achievement_criteria(self, 
                                   user_id: str,
                                   achievement: tuple,
                                   activity_type: ActivityType,
                                   metadata: Dict[str, Any] = None) -> bool:
        """Verifica se os critérios da conquista foram atendidos"""
        
        criteria = json.loads(achievement[7])  # achievement[7] é criteria
        
        with sqlite3.connect(self.db_path) as conn:
            # Verifica diferentes tipos de critérios
            if 'activity_type' in criteria:
                # Critério baseado em contagem de atividades
                if criteria['activity_type'] == activity_type.value:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM activities WHERE user_id = ? AND activity_type = ?",
                        (user_id, activity_type.value)
                    )
                    count = cursor.fetchone()[0]
                    return count >= criteria.get('count', 1)
            
            elif 'streak_type' in criteria:
                # Critério baseado em streak
                if criteria['streak_type'] == 'daily_login' and activity_type == ActivityType.LOGIN_DAILY:
                    cursor = conn.execute("SELECT streak_days FROM user_stats WHERE user_id = ?", (user_id,))
                    row = cursor.fetchone()
                    if row:
                        return row[0] >= criteria.get('days', 1)
            
            elif 'total_points' in criteria:
                # Critério baseado em pontos totais
                cursor = conn.execute("SELECT total_points FROM user_stats WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    return row[0] >= criteria['total_points']
            
            elif 'unique_chart_types' in criteria:
                # Critério baseado em tipos únicos de gráfico
                cursor = conn.execute("""
                    SELECT COUNT(DISTINCT JSON_EXTRACT(metadata, '$.chart_type'))
                    FROM activities
                    WHERE user_id = ? AND activity_type = 'create_chart'
                    AND JSON_EXTRACT(metadata, '$.chart_type') IS NOT NULL
                """, (user_id,))
                row = cursor.fetchone()
                if row:
                    return row[0] >= criteria['unique_chart_types']
        
        return False
    
    def _unlock_achievement(self, user_id: str, achievement_id: str):
        """Desbloqueia uma conquista para o usuário"""
        
        unlock_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # Registra conquista desbloqueada
            conn.execute("""
                INSERT INTO user_achievements (id, user_id, achievement_id, unlocked_at, progress_data)
                VALUES (?, ?, ?, ?, ?)
            """, (unlock_id, user_id, achievement_id, now.isoformat(), '{}'))
            
            # Obtém pontos da conquista
            cursor = conn.execute("SELECT points FROM achievements WHERE id = ?", (achievement_id,))
            points = cursor.fetchone()[0]
            
            # Adiciona pontos bônus
            conn.execute(
                "UPDATE user_stats SET total_points = total_points + ?, achievements_count = achievements_count + 1 WHERE user_id = ?",
                (points, user_id)
            )
            
            conn.commit()
        
        # Notifica usuário (integração com sistema de notificações)
        try:
            from .notification_system import notification_system, NotificationType, NotificationPriority
            
            achievement = self.get_achievement(achievement_id)
            if achievement:
                notification_system.create_from_template(
                    template_id='achievement_unlocked',
                    user_id=user_id,
                    variables={
                        'achievement_name': achievement.name,
                        'achievement_icon': achievement.icon,
                        'points': str(achievement.points)
                    }
                )
        except ImportError:
            pass
    
    def get_user_stats(self, user_id: str) -> Optional[UserStats]:
        """Obtém estatísticas do usuário"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                # Calcula posição no ranking
                rank_cursor = conn.execute(
                    "SELECT COUNT(*) + 1 FROM user_stats WHERE total_points > ?",
                    (row['total_points'],)
                )
                rank_position = rank_cursor.fetchone()[0]
                
                # Calcula experiência para próximo nível
                level_cursor = conn.execute(
                    "SELECT max_experience FROM levels WHERE level = ?",
                    (row['level'],)
                )
                level_row = level_cursor.fetchone()
                exp_to_next = level_row[0] - row['experience'] if level_row else 0
                
                return UserStats(
                    user_id=row['user_id'],
                    total_points=row['total_points'],
                    level=row['level'],
                    experience=row['experience'],
                    experience_to_next_level=max(0, exp_to_next),
                    achievements_count=row['achievements_count'],
                    rank_position=rank_position,
                    streak_days=row['streak_days'],
                    last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None,
                    activities_count=json.loads(row['activities_count']),
                    monthly_points=row['monthly_points'],
                    weekly_points=row['weekly_points']
                )
            
            return None
    
    def get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Obtém conquistas do usuário"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT a.*, ua.unlocked_at
                FROM achievements a
                JOIN user_achievements ua ON a.id = ua.achievement_id
                WHERE ua.user_id = ?
                ORDER BY ua.unlocked_at DESC
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_available_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Obtém conquistas disponíveis (não desbloqueadas)"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM achievements
                WHERE is_active = 1 AND is_hidden = 0
                AND id NOT IN (
                    SELECT achievement_id FROM user_achievements WHERE user_id = ?
                )
                ORDER BY points ASC
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_leaderboard(self, limit: int = 10, period: str = 'all_time') -> List[Dict[str, Any]]:
        """Obtém ranking de usuários"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if period == 'monthly':
                cursor = conn.execute(
                    "SELECT user_id, monthly_points as points, level FROM user_stats ORDER BY monthly_points DESC LIMIT ?",
                    (limit,)
                )
            elif period == 'weekly':
                cursor = conn.execute(
                    "SELECT user_id, weekly_points as points, level FROM user_stats ORDER BY weekly_points DESC LIMIT ?",
                    (limit,)
                )
            else:  # all_time
                cursor = conn.execute(
                    "SELECT user_id, total_points as points, level FROM user_stats ORDER BY total_points DESC LIMIT ?",
                    (limit,)
                )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """Obtém uma conquista específica"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM achievements WHERE id = ?", (achievement_id,))
            row = cursor.fetchone()
            
            if row:
                return Achievement(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    icon=row['icon'],
                    achievement_type=AchievementType(row['achievement_type']),
                    rarity=BadgeRarity(row['rarity']),
                    points=row['points'],
                    criteria=json.loads(row['criteria']),
                    is_hidden=row['is_hidden'],
                    category=row['category'],
                    unlock_message=row['unlock_message'],
                    prerequisites=json.loads(row['prerequisites']),
                    is_active=row['is_active']
                )
            
            return None
    
    def get_level_info(self, level: int) -> Optional[Level]:
        """Obtém informações de um nível"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM levels WHERE level = ?", (level,))
            row = cursor.fetchone()
            
            if row:
                return Level(
                    level=row['level'],
                    name=row['name'],
                    min_experience=row['min_experience'],
                    max_experience=row['max_experience'],
                    benefits=json.loads(row['benefits']),
                    icon=row['icon'],
                    color=row['color']
                )
            
            return None
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Obtém progresso geral do usuário"""
        
        stats = self.get_user_stats(user_id)
        if not stats:
            return {}
        
        achievements = self.get_user_achievements(user_id)
        available = self.get_available_achievements(user_id)
        level_info = self.get_level_info(stats.level)
        
        # Calcula progresso por categoria
        category_progress = {}
        for achievement in available:
            category = achievement['category']
            if category not in category_progress:
                category_progress[category] = {'total': 0, 'completed': 0}
            category_progress[category]['total'] += 1
        
        for achievement in achievements:
            category = achievement['category']
            if category in category_progress:
                category_progress[category]['completed'] += 1
        
        return {
            'stats': asdict(stats) if stats else {},
            'level_info': asdict(level_info) if level_info else {},
            'achievements': {
                'unlocked': achievements,
                'available': available,
                'total_unlocked': len(achievements),
                'total_available': len(available)
            },
            'category_progress': category_progress,
            'recent_activities': self._get_recent_activities(user_id, 10)
        }
    
    def _get_recent_activities(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém atividades recentes do usuário"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM activities
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def reset_weekly_points(self):
        """Reseta pontos semanais (executar semanalmente)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE user_stats SET weekly_points = 0")
            conn.commit()
    
    def reset_monthly_points(self):
        """Reseta pontos mensais (executar mensalmente)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE user_stats SET monthly_points = 0")
            conn.commit()

# Instância global
gamification_system = GamificationSystem()