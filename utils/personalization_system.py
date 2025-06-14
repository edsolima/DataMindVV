# -*- coding: utf-8 -*-
"""
Sistema de Personalização Avançada
Implementa personalização de interface, preferências e experiência do usuário
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path
import hashlib

class PersonalizationType(Enum):
    """Tipos de personalização"""
    THEME = "theme"
    LAYOUT = "layout"
    DASHBOARD = "dashboard"
    CHARTS = "charts"
    NAVIGATION = "navigation"
    NOTIFICATIONS = "notifications"
    LANGUAGE = "language"
    TIMEZONE = "timezone"
    ACCESSIBILITY = "accessibility"
    SHORTCUTS = "shortcuts"

class WidgetType(Enum):
    """Tipos de widgets personalizáveis"""
    CHART = "chart"
    KPI = "kpi"
    TABLE = "table"
    TEXT = "text"
    IMAGE = "image"
    IFRAME = "iframe"
    FILTER = "filter"
    CALENDAR = "calendar"
    NEWS = "news"
    WEATHER = "weather"

class LayoutType(Enum):
    """Tipos de layout"""
    GRID = "grid"
    FLEX = "flex"
    MASONRY = "masonry"
    TABS = "tabs"
    ACCORDION = "accordion"
    SIDEBAR = "sidebar"

@dataclass
class UserPreference:
    """Preferência do usuário"""
    id: str
    user_id: str
    preference_type: PersonalizationType
    key: str
    value: Any
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool

@dataclass
class CustomWidget:
    """Widget personalizado"""
    id: str
    user_id: str
    name: str
    widget_type: WidgetType
    config: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height
    dashboard_id: Optional[str]
    is_shared: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class CustomLayout:
    """Layout personalizado"""
    id: str
    user_id: str
    name: str
    layout_type: LayoutType
    config: Dict[str, Any]
    widgets: List[str]  # IDs dos widgets
    is_default: bool
    is_shared: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class UserProfile:
    """Perfil completo do usuário"""
    user_id: str
    display_name: str
    avatar_url: Optional[str]
    theme: str
    language: str
    timezone: str
    date_format: str
    number_format: str
    currency: str
    preferences: Dict[str, Any]
    custom_css: Optional[str]
    shortcuts: Dict[str, str]
    last_updated: datetime

class PersonalizationSystem:
    """Sistema principal de personalização"""
    
    def __init__(self, db_path: str = "personalization.sqlite"):
        self.db_path = db_path
        self._init_database()
        self._load_default_themes()
        self._load_default_layouts()
        
    def _init_database(self):
        """Inicializa o banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            # Tabela de preferências do usuário
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    preference_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    UNIQUE(user_id, preference_type, key)
                )
            """)
            
            # Tabela de widgets personalizados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_widgets (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    widget_type TEXT NOT NULL,
                    config TEXT NOT NULL,
                    position TEXT NOT NULL,
                    dashboard_id TEXT,
                    is_shared BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Tabela de layouts personalizados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_layouts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    layout_type TEXT NOT NULL,
                    config TEXT NOT NULL,
                    widgets TEXT NOT NULL DEFAULT '[]',
                    is_default BOOLEAN DEFAULT FALSE,
                    is_shared BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Tabela de perfis de usuário
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    avatar_url TEXT,
                    theme TEXT DEFAULT 'default',
                    language TEXT DEFAULT 'pt-BR',
                    timezone TEXT DEFAULT 'America/Sao_Paulo',
                    date_format TEXT DEFAULT 'DD/MM/YYYY',
                    number_format TEXT DEFAULT 'pt-BR',
                    currency TEXT DEFAULT 'BRL',
                    preferences TEXT NOT NULL DEFAULT '{}',
                    custom_css TEXT,
                    shortcuts TEXT NOT NULL DEFAULT '{}',
                    last_updated TEXT NOT NULL
                )
            """)
            
            # Tabela de temas personalizados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_themes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    config TEXT NOT NULL,
                    css_variables TEXT NOT NULL,
                    is_public BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Tabela de templates de dashboard
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_templates (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    config TEXT NOT NULL,
                    preview_image TEXT,
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    is_public BOOLEAN DEFAULT FALSE,
                    usage_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Índices para performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_widgets_user ON custom_widgets(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_layouts_user ON custom_layouts(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_templates_public ON dashboard_templates(is_public)")
            
            conn.commit()
    
    def _load_default_themes(self):
        """Carrega temas padrão"""
        default_themes = [
            {
                'id': 'default',
                'name': 'Padrão',
                'config': {
                    'primary_color': '#1976d2',
                    'secondary_color': '#dc004e',
                    'background_color': '#ffffff',
                    'surface_color': '#f5f5f5',
                    'text_color': '#212121',
                    'border_radius': '4px',
                    'font_family': 'Roboto, sans-serif'
                }
            },
            {
                'id': 'dark',
                'name': 'Escuro',
                'config': {
                    'primary_color': '#bb86fc',
                    'secondary_color': '#03dac6',
                    'background_color': '#121212',
                    'surface_color': '#1e1e1e',
                    'text_color': '#ffffff',
                    'border_radius': '4px',
                    'font_family': 'Roboto, sans-serif'
                }
            },
            {
                'id': 'corporate',
                'name': 'Corporativo',
                'config': {
                    'primary_color': '#2c3e50',
                    'secondary_color': '#e74c3c',
                    'background_color': '#ecf0f1',
                    'surface_color': '#ffffff',
                    'text_color': '#2c3e50',
                    'border_radius': '2px',
                    'font_family': 'Arial, sans-serif'
                }
            }
        ]
        
        # Salva no sistema de temas (integração com theme_manager)
        try:
            from .theme_manager import theme_manager
            for theme in default_themes:
                theme_manager.create_theme(
                    theme['id'],
                    theme['name'],
                    theme['config']
                )
        except ImportError:
            pass
    
    def _load_default_layouts(self):
        """Carrega layouts padrão"""
        default_layouts = [
            {
                'id': 'dashboard_grid',
                'name': 'Grade de Dashboard',
                'layout_type': LayoutType.GRID,
                'config': {
                    'columns': 12,
                    'row_height': 60,
                    'margin': [10, 10],
                    'container_padding': [10, 10],
                    'responsive': True,
                    'breakpoints': {
                        'lg': 1200,
                        'md': 996,
                        'sm': 768,
                        'xs': 480
                    }
                }
            },
            {
                'id': 'analytics_flex',
                'name': 'Analytics Flexível',
                'layout_type': LayoutType.FLEX,
                'config': {
                    'direction': 'column',
                    'wrap': True,
                    'justify_content': 'flex-start',
                    'align_items': 'stretch',
                    'gap': '16px'
                }
            },
            {
                'id': 'executive_tabs',
                'name': 'Executivo com Abas',
                'layout_type': LayoutType.TABS,
                'config': {
                    'tab_position': 'top',
                    'tab_style': 'pills',
                    'animated': True,
                    'lazy_load': True
                }
            }
        ]
        
        # Salva layouts padrão no banco
        with sqlite3.connect(self.db_path) as conn:
            for layout in default_layouts:
                conn.execute("""
                    INSERT OR IGNORE INTO custom_layouts (
                        id, user_id, name, layout_type, config, widgets,
                        is_default, is_shared, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    layout['id'], 'system', layout['name'],
                    layout['layout_type'].value, json.dumps(layout['config']),
                    '[]', True, True, datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            conn.commit()
    
    def set_user_preference(self, 
                           user_id: str,
                           preference_type: PersonalizationType,
                           key: str,
                           value: Any,
                           metadata: Dict[str, Any] = None) -> str:
        """Define uma preferência do usuário"""
        
        preference_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences (
                    id, user_id, preference_type, key, value, metadata,
                    created_at, updated_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                preference_id, user_id, preference_type.value, key,
                json.dumps(value), json.dumps(metadata or {}),
                now.isoformat(), now.isoformat(), True
            ))
            conn.commit()
        
        return preference_id
    
    def get_user_preference(self, 
                           user_id: str,
                           preference_type: PersonalizationType,
                           key: str,
                           default_value: Any = None) -> Any:
        """Obtém uma preferência do usuário"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT value FROM user_preferences
                WHERE user_id = ? AND preference_type = ? AND key = ? AND is_active = 1
            """, (user_id, preference_type.value, key))
            
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            
            return default_value
    
    def get_user_preferences(self, 
                            user_id: str,
                            preference_type: PersonalizationType = None) -> Dict[str, Any]:
        """Obtém todas as preferências do usuário"""
        
        query = "SELECT key, value FROM user_preferences WHERE user_id = ? AND is_active = 1"
        params = [user_id]
        
        if preference_type:
            query += " AND preference_type = ?"
            params.append(preference_type.value)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            
            preferences = {}
            for row in cursor.fetchall():
                preferences[row[0]] = json.loads(row[1])
            
            return preferences
    
    def create_custom_widget(self, 
                            user_id: str,
                            name: str,
                            widget_type: WidgetType,
                            config: Dict[str, Any],
                            position: Dict[str, int] = None,
                            dashboard_id: str = None) -> str:
        """Cria um widget personalizado"""
        
        widget_id = str(uuid.uuid4())
        now = datetime.now()
        
        default_position = {'x': 0, 'y': 0, 'width': 4, 'height': 3}
        position = position or default_position
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO custom_widgets (
                    id, user_id, name, widget_type, config, position,
                    dashboard_id, is_shared, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                widget_id, user_id, name, widget_type.value,
                json.dumps(config), json.dumps(position),
                dashboard_id, False, now.isoformat(), now.isoformat()
            ))
            conn.commit()
        
        return widget_id
    
    def update_widget_position(self, 
                              widget_id: str,
                              user_id: str,
                              position: Dict[str, int]) -> bool:
        """Atualiza posição de um widget"""
        
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE custom_widgets
                SET position = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (json.dumps(position), now.isoformat(), widget_id, user_id))
            
            return cursor.rowcount > 0
    
    def create_custom_layout(self, 
                            user_id: str,
                            name: str,
                            layout_type: LayoutType,
                            config: Dict[str, Any],
                            widgets: List[str] = None) -> str:
        """Cria um layout personalizado"""
        
        layout_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO custom_layouts (
                    id, user_id, name, layout_type, config, widgets,
                    is_default, is_shared, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                layout_id, user_id, name, layout_type.value,
                json.dumps(config), json.dumps(widgets or []),
                False, False, now.isoformat(), now.isoformat()
            ))
            conn.commit()
        
        return layout_id
    
    def get_user_widgets(self, 
                        user_id: str,
                        dashboard_id: str = None) -> List[CustomWidget]:
        """Obtém widgets do usuário"""
        
        query = "SELECT * FROM custom_widgets WHERE user_id = ?"
        params = [user_id]
        
        if dashboard_id:
            query += " AND dashboard_id = ?"
            params.append(dashboard_id)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            widgets = []
            for row in cursor.fetchall():
                widgets.append(CustomWidget(
                    id=row['id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    widget_type=WidgetType(row['widget_type']),
                    config=json.loads(row['config']),
                    position=json.loads(row['position']),
                    dashboard_id=row['dashboard_id'],
                    is_shared=row['is_shared'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            
            return widgets
    
    def get_user_layouts(self, user_id: str) -> List[CustomLayout]:
        """Obtém layouts do usuário"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM custom_layouts
                WHERE user_id = ? OR is_shared = 1
                ORDER BY is_default DESC, created_at DESC
            """, (user_id,))
            
            layouts = []
            for row in cursor.fetchall():
                layouts.append(CustomLayout(
                    id=row['id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    layout_type=LayoutType(row['layout_type']),
                    config=json.loads(row['config']),
                    widgets=json.loads(row['widgets']),
                    is_default=row['is_default'],
                    is_shared=row['is_shared'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            
            return layouts
    
    def create_user_profile(self, 
                           user_id: str,
                           display_name: str,
                           **kwargs) -> UserProfile:
        """Cria ou atualiza perfil do usuário"""
        
        now = datetime.now()
        
        profile_data = {
            'display_name': display_name,
            'avatar_url': kwargs.get('avatar_url'),
            'theme': kwargs.get('theme', 'default'),
            'language': kwargs.get('language', 'pt-BR'),
            'timezone': kwargs.get('timezone', 'America/Sao_Paulo'),
            'date_format': kwargs.get('date_format', 'DD/MM/YYYY'),
            'number_format': kwargs.get('number_format', 'pt-BR'),
            'currency': kwargs.get('currency', 'BRL'),
            'preferences': kwargs.get('preferences', {}),
            'custom_css': kwargs.get('custom_css'),
            'shortcuts': kwargs.get('shortcuts', {})
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profiles (
                    user_id, display_name, avatar_url, theme, language, timezone,
                    date_format, number_format, currency, preferences,
                    custom_css, shortcuts, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, profile_data['display_name'], profile_data['avatar_url'],
                profile_data['theme'], profile_data['language'], profile_data['timezone'],
                profile_data['date_format'], profile_data['number_format'],
                profile_data['currency'], json.dumps(profile_data['preferences']),
                profile_data['custom_css'], json.dumps(profile_data['shortcuts']),
                now.isoformat()
            ))
            conn.commit()
        
        return UserProfile(
            user_id=user_id,
            display_name=profile_data['display_name'],
            avatar_url=profile_data['avatar_url'],
            theme=profile_data['theme'],
            language=profile_data['language'],
            timezone=profile_data['timezone'],
            date_format=profile_data['date_format'],
            number_format=profile_data['number_format'],
            currency=profile_data['currency'],
            preferences=profile_data['preferences'],
            custom_css=profile_data['custom_css'],
            shortcuts=profile_data['shortcuts'],
            last_updated=now
        )
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Obtém perfil do usuário"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return UserProfile(
                    user_id=row['user_id'],
                    display_name=row['display_name'],
                    avatar_url=row['avatar_url'],
                    theme=row['theme'],
                    language=row['language'],
                    timezone=row['timezone'],
                    date_format=row['date_format'],
                    number_format=row['number_format'],
                    currency=row['currency'],
                    preferences=json.loads(row['preferences']),
                    custom_css=row['custom_css'],
                    shortcuts=json.loads(row['shortcuts']),
                    last_updated=datetime.fromisoformat(row['last_updated'])
                )
            
            return None
    
    def create_custom_theme(self, 
                           user_id: str,
                           name: str,
                           config: Dict[str, Any],
                           css_variables: Dict[str, str] = None) -> str:
        """Cria um tema personalizado"""
        
        theme_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO custom_themes (
                    id, user_id, name, config, css_variables,
                    is_public, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                theme_id, user_id, name, json.dumps(config),
                json.dumps(css_variables or {}), False,
                now.isoformat(), now.isoformat()
            ))
            conn.commit()
        
        return theme_id
    
    def create_dashboard_template(self, 
                                 user_id: str,
                                 name: str,
                                 description: str,
                                 config: Dict[str, Any],
                                 category: str,
                                 tags: List[str] = None) -> str:
        """Cria um template de dashboard"""
        
        template_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO dashboard_templates (
                    id, user_id, name, description, config, category,
                    tags, is_public, usage_count, rating,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template_id, user_id, name, description,
                json.dumps(config), category, json.dumps(tags or []),
                False, 0, 0, now.isoformat(), now.isoformat()
            ))
            conn.commit()
        
        return template_id
    
    def get_dashboard_templates(self, 
                               user_id: str = None,
                               category: str = None,
                               public_only: bool = False) -> List[Dict[str, Any]]:
        """Obtém templates de dashboard"""
        
        query = "SELECT * FROM dashboard_templates WHERE 1=1"
        params = []
        
        if public_only:
            query += " AND is_public = 1"
        elif user_id:
            query += " AND (user_id = ? OR is_public = 1)"
            params.append(user_id)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY usage_count DESC, rating DESC, created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def apply_user_customizations(self, user_id: str) -> Dict[str, Any]:
        """Aplica todas as personalizações do usuário"""
        
        profile = self.get_user_profile(user_id)
        preferences = self.get_user_preferences(user_id)
        widgets = self.get_user_widgets(user_id)
        layouts = self.get_user_layouts(user_id)
        
        # Gera CSS personalizado
        custom_css = self._generate_custom_css(user_id, profile)
        
        return {
            'profile': asdict(profile) if profile else {},
            'preferences': preferences,
            'widgets': [asdict(w) for w in widgets],
            'layouts': [asdict(l) for l in layouts],
            'custom_css': custom_css,
            'theme_config': self._get_theme_config(profile.theme if profile else 'default')
        }
    
    def _generate_custom_css(self, user_id: str, profile: UserProfile = None) -> str:
        """Gera CSS personalizado baseado nas preferências"""
        
        if not profile:
            profile = self.get_user_profile(user_id)
        
        if not profile:
            return ""
        
        # CSS base do tema
        theme_config = self._get_theme_config(profile.theme)
        
        css_rules = []
        
        # Variáveis CSS do tema
        if theme_config:
            css_rules.append(":root {")
            for key, value in theme_config.items():
                css_var = f"--{key.replace('_', '-')}"
                css_rules.append(f"  {css_var}: {value};")
            css_rules.append("}")
        
        # CSS personalizado do usuário
        if profile.custom_css:
            css_rules.append(profile.custom_css)
        
        # Preferências de acessibilidade
        accessibility_prefs = self.get_user_preferences(user_id, PersonalizationType.ACCESSIBILITY)
        if accessibility_prefs:
            if accessibility_prefs.get('high_contrast'):
                css_rules.append("""
                .high-contrast {
                    filter: contrast(150%);
                }
                """)
            
            if accessibility_prefs.get('large_text'):
                css_rules.append("""
                .large-text {
                    font-size: 1.2em !important;
                }
                """)
        
        return "\n".join(css_rules)
    
    def _get_theme_config(self, theme_name: str) -> Dict[str, Any]:
        """Obtém configuração do tema"""
        try:
            from .theme_manager import theme_manager
            return theme_manager.get_theme(theme_name)
        except ImportError:
            # Fallback para temas padrão
            default_themes = {
                'default': {
                    'primary_color': '#1976d2',
                    'secondary_color': '#dc004e',
                    'background_color': '#ffffff',
                    'surface_color': '#f5f5f5',
                    'text_color': '#212121'
                },
                'dark': {
                    'primary_color': '#bb86fc',
                    'secondary_color': '#03dac6',
                    'background_color': '#121212',
                    'surface_color': '#1e1e1e',
                    'text_color': '#ffffff'
                }
            }
            return default_themes.get(theme_name, default_themes['default'])
    
    def export_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Exporta todas as configurações do usuário"""
        
        profile = self.get_user_profile(user_id)
        preferences = self.get_user_preferences(user_id)
        widgets = self.get_user_widgets(user_id)
        layouts = self.get_user_layouts(user_id)
        
        # Obtém temas personalizados
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM custom_themes WHERE user_id = ?", (user_id,)
            )
            custom_themes = [dict(row) for row in cursor.fetchall()]
        
        return {
            'profile': asdict(profile) if profile else None,
            'preferences': preferences,
            'widgets': [asdict(w) for w in widgets],
            'layouts': [asdict(l) for l in layouts],
            'custom_themes': custom_themes,
            'export_date': datetime.now().isoformat(),
            'version': '1.0'
        }
    
    def import_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Importa configurações do usuário"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Importa perfil
                if settings.get('profile'):
                    profile_data = settings['profile']
                    self.create_user_profile(user_id, **profile_data)
                
                # Importa preferências
                if settings.get('preferences'):
                    for key, value in settings['preferences'].items():
                        # Determina tipo de preferência baseado na chave
                        pref_type = self._determine_preference_type(key)
                        self.set_user_preference(user_id, pref_type, key, value)
                
                # Importa widgets
                if settings.get('widgets'):
                    for widget_data in settings['widgets']:
                        self.create_custom_widget(
                            user_id=user_id,
                            name=widget_data['name'],
                            widget_type=WidgetType(widget_data['widget_type']),
                            config=widget_data['config'],
                            position=widget_data['position'],
                            dashboard_id=widget_data.get('dashboard_id')
                        )
                
                # Importa layouts
                if settings.get('layouts'):
                    for layout_data in settings['layouts']:
                        if layout_data['user_id'] != 'system':  # Não importa layouts do sistema
                            self.create_custom_layout(
                                user_id=user_id,
                                name=layout_data['name'],
                                layout_type=LayoutType(layout_data['layout_type']),
                                config=layout_data['config'],
                                widgets=layout_data['widgets']
                            )
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Erro ao importar configurações: {e}")
            return False
    
    def _determine_preference_type(self, key: str) -> PersonalizationType:
        """Determina o tipo de preferência baseado na chave"""
        
        key_mappings = {
            'theme': PersonalizationType.THEME,
            'layout': PersonalizationType.LAYOUT,
            'language': PersonalizationType.LANGUAGE,
            'timezone': PersonalizationType.TIMEZONE,
            'notifications': PersonalizationType.NOTIFICATIONS,
            'accessibility': PersonalizationType.ACCESSIBILITY,
            'shortcuts': PersonalizationType.SHORTCUTS
        }
        
        for pattern, pref_type in key_mappings.items():
            if pattern in key.lower():
                return pref_type
        
        return PersonalizationType.DASHBOARD  # Padrão
    
    def get_personalization_analytics(self, user_id: str = None) -> Dict[str, Any]:
        """Obtém analytics de personalização"""
        
        with sqlite3.connect(self.db_path) as conn:
            analytics = {}
            
            # Estatísticas gerais
            if user_id:
                # Analytics específicos do usuário
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM user_preferences WHERE user_id = ?", (user_id,)
                )
                analytics['user_preferences_count'] = cursor.fetchone()[0]
                
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM custom_widgets WHERE user_id = ?", (user_id,)
                )
                analytics['user_widgets_count'] = cursor.fetchone()[0]
                
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM custom_layouts WHERE user_id = ?", (user_id,)
                )
                analytics['user_layouts_count'] = cursor.fetchone()[0]
            else:
                # Analytics globais
                cursor = conn.execute("SELECT COUNT(*) FROM user_profiles")
                analytics['total_users'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM custom_widgets")
                analytics['total_widgets'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM custom_layouts")
                analytics['total_layouts'] = cursor.fetchone()[0]
                
                # Temas mais populares
                cursor = conn.execute("""
                    SELECT theme, COUNT(*) as count
                    FROM user_profiles
                    GROUP BY theme
                    ORDER BY count DESC
                    LIMIT 5
                """)
                analytics['popular_themes'] = [{'theme': row[0], 'count': row[1]} for row in cursor.fetchall()]
                
                # Tipos de widget mais usados
                cursor = conn.execute("""
                    SELECT widget_type, COUNT(*) as count
                    FROM custom_widgets
                    GROUP BY widget_type
                    ORDER BY count DESC
                    LIMIT 5
                """)
                analytics['popular_widget_types'] = [{'type': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            return analytics

# Instância global
personalization_system = PersonalizationSystem()