# -*- coding: utf-8 -*-
"""
Theme Manager - Gerenciamento de Temas Personalizáveis
Permite que usuários escolham diferentes temas e esquemas de cores
"""

import json
import os
from typing import Dict, List, Optional, Any

from utils.logger import log_info, log_error
from utils.config_manager import ConfigManager

class ThemeManager:
    """Gerenciador de temas personalizáveis"""
    
    def __init__(self, themes_dir: str = "themes"):
        self.themes_dir = themes_dir
        self.config_manager = ConfigManager()
        self._ensure_themes_dir()
        self._load_default_themes()
    
    def _ensure_themes_dir(self):
        """Garante que o diretório de temas existe"""
        if not os.path.exists(self.themes_dir):
            os.makedirs(self.themes_dir)
            log_info(f"Diretório de temas criado: {self.themes_dir}")
    
    def _load_default_themes(self):
        """Carrega temas padrão se não existirem"""
        default_themes = {
            'default': self._create_default_theme(),
            'dark': self._create_dark_theme(),
            'corporate': self._create_corporate_theme(),
            'modern': self._create_modern_theme(),
            'minimal': self._create_minimal_theme(),
            'colorful': self._create_colorful_theme()
        }
        
        for theme_id, theme_data in default_themes.items():
            theme_file = os.path.join(self.themes_dir, f"{theme_id}.json")
            if not os.path.exists(theme_file):
                self.save_theme(theme_id, theme_data)
                log_info(f"Tema padrão criado: {theme_id}")
    
    def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Obtém um tema pelo ID"""
        try:
            theme_file = os.path.join(self.themes_dir, f"{theme_id}.json")
            if os.path.exists(theme_file):
                with open(theme_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            log_error(f"Erro ao carregar tema {theme_id}", extra={"error": str(e)})
            return None
    
    def save_theme(self, theme_id: str, theme_data: Dict[str, Any]) -> bool:
        """Salva um tema"""
        try:
            theme_file = os.path.join(self.themes_dir, f"{theme_id}.json")
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)
            log_info(f"Tema salvo: {theme_id}")
            return True
        except Exception as e:
            log_error(f"Erro ao salvar tema {theme_id}", extra={"error": str(e)})
            return False
    
    def list_themes(self) -> List[Dict[str, Any]]:
        """Lista todos os temas disponíveis"""
        themes = []
        try:
            for filename in os.listdir(self.themes_dir):
                if filename.endswith('.json'):
                    theme_id = filename[:-5]  # Remove .json
                    theme_data = self.get_theme(theme_id)
                    if theme_data:
                        themes.append({
                            'id': theme_id,
                            'name': theme_data.get('name', theme_id),
                            'description': theme_data.get('description', ''),
                            'preview_colors': theme_data.get('preview_colors', []),
                            'category': theme_data.get('category', 'custom')
                        })
        except Exception as e:
            log_error(f"Erro ao listar temas", extra={"error": str(e)})
        
        return themes
    
    def get_current_theme(self) -> str:
        """Obtém o tema atual do usuário"""
        return self.config_manager.get_config('theme', 'default')
    
    def set_current_theme(self, theme_id: str) -> bool:
        """Define o tema atual do usuário"""
        if self.get_theme(theme_id):
            self.config_manager.set_config('theme', theme_id)
            log_info(f"Tema alterado para: {theme_id}")
            return True
        return False
    
    def generate_css(self, theme_id: str) -> str:
        """Gera CSS personalizado para um tema"""
        theme = self.get_theme(theme_id)
        if not theme:
            return ""
        
        css_vars = []
        colors = theme.get('colors', {})
        
        # Variáveis CSS para cores
        for key, value in colors.items():
            css_vars.append(f"  --{key.replace('_', '-')}: {value};")
        
        # Variáveis CSS para tipografia
        typography = theme.get('typography', {})
        for key, value in typography.items():
            css_vars.append(f"  --font-{key.replace('_', '-')}: {value};")
        
        # Variáveis CSS para espaçamento
        spacing = theme.get('spacing', {})
        for key, value in spacing.items():
            css_vars.append(f"  --spacing-{key}: {value};")
        
        # Variáveis CSS para bordas
        borders = theme.get('borders', {})
        for key, value in borders.items():
            css_vars.append(f"  --border-{key.replace('_', '-')}: {value};")
        
        # Variáveis CSS para sombras
        shadows = theme.get('shadows', {})
        for key, value in shadows.items():
            css_vars.append(f"  --shadow-{key}: {value};")
        
        css = f":root {{\n{chr(10).join(css_vars)}\n}}"
        
        # Adiciona estilos específicos do tema
        custom_css = theme.get('custom_css', '')
        if custom_css:
            css += f"\n\n{custom_css}"
        
        return css
    
    def _create_default_theme(self) -> Dict[str, Any]:
        """Cria tema padrão"""
        return {
            'name': 'Padrão',
            'description': 'Tema padrão do sistema com cores neutras',
            'category': 'built-in',
            'preview_colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
            'colors': {
                'primary': '#1f77b4',
                'secondary': '#ff7f0e',
                'success': '#2ca02c',
                'danger': '#d62728',
                'warning': '#ff7f0e',
                'info': '#17a2b8',
                'light': '#f8f9fa',
                'dark': '#343a40',
                'background': '#ffffff',
                'surface': '#f8f9fa',
                'text_primary': '#212529',
                'text_secondary': '#6c757d',
                'border': '#dee2e6',
                'hover': '#e9ecef'
            },
            'typography': {
                'family_primary': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
                'family_monospace': '"Courier New", Courier, monospace',
                'size_xs': '0.75rem',
                'size_sm': '0.875rem',
                'size_base': '1rem',
                'size_lg': '1.125rem',
                'size_xl': '1.25rem',
                'size_2xl': '1.5rem',
                'weight_normal': '400',
                'weight_medium': '500',
                'weight_bold': '700'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '3rem'
            },
            'borders': {
                'radius_sm': '0.25rem',
                'radius_md': '0.375rem',
                'radius_lg': '0.5rem',
                'width': '1px'
            },
            'shadows': {
                'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
            }
        }
    
    def _create_dark_theme(self) -> Dict[str, Any]:
        """Cria tema escuro"""
        return {
            'name': 'Escuro',
            'description': 'Tema escuro para reduzir fadiga visual',
            'category': 'built-in',
            'preview_colors': ['#bb86fc', '#03dac6', '#cf6679', '#121212'],
            'colors': {
                'primary': '#bb86fc',
                'secondary': '#03dac6',
                'success': '#4caf50',
                'danger': '#cf6679',
                'warning': '#ff9800',
                'info': '#2196f3',
                'light': '#2c2c2c',
                'dark': '#121212',
                'background': '#121212',
                'surface': '#1e1e1e',
                'text_primary': '#ffffff',
                'text_secondary': '#b3b3b3',
                'border': '#333333',
                'hover': '#2c2c2c'
            },
            'typography': {
                'family_primary': '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
                'family_monospace': '"Courier New", Courier, monospace',
                'size_xs': '0.75rem',
                'size_sm': '0.875rem',
                'size_base': '1rem',
                'size_lg': '1.125rem',
                'size_xl': '1.25rem',
                'size_2xl': '1.5rem',
                'weight_normal': '400',
                'weight_medium': '500',
                'weight_bold': '700'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '3rem'
            },
            'borders': {
                'radius_sm': '0.25rem',
                'radius_md': '0.375rem',
                'radius_lg': '0.5rem',
                'width': '1px'
            },
            'shadows': {
                'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
                'md': '0 4px 6px -1px rgba(0, 0, 0, 0.4)',
                'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
            },
            'custom_css': '''
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table {
    background-color: var(--surface) !important;
    color: var(--text-primary) !important;
}

.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: var(--light) !important;
    color: var(--text-primary) !important;
}

.Select-control {
    background-color: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
}
'''
        }
    
    def _create_corporate_theme(self) -> Dict[str, Any]:
        """Cria tema corporativo"""
        return {
            'name': 'Corporativo',
            'description': 'Tema profissional para ambiente corporativo',
            'category': 'business',
            'preview_colors': ['#003366', '#0066cc', '#004d99', '#f5f5f5'],
            'colors': {
                'primary': '#003366',
                'secondary': '#0066cc',
                'success': '#28a745',
                'danger': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8',
                'light': '#f5f5f5',
                'dark': '#003366',
                'background': '#ffffff',
                'surface': '#f8f9fa',
                'text_primary': '#2c3e50',
                'text_secondary': '#7f8c8d',
                'border': '#bdc3c7',
                'hover': '#ecf0f1'
            },
            'typography': {
                'family_primary': '"Arial", "Helvetica Neue", Helvetica, sans-serif',
                'family_monospace': '"Consolas", "Monaco", monospace',
                'size_xs': '0.75rem',
                'size_sm': '0.875rem',
                'size_base': '1rem',
                'size_lg': '1.125rem',
                'size_xl': '1.25rem',
                'size_2xl': '1.5rem',
                'weight_normal': '400',
                'weight_medium': '500',
                'weight_bold': '700'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '3rem'
            },
            'borders': {
                'radius_sm': '0.125rem',
                'radius_md': '0.25rem',
                'radius_lg': '0.375rem',
                'width': '1px'
            },
            'shadows': {
                'sm': '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
            }
        }
    
    def _create_modern_theme(self) -> Dict[str, Any]:
        """Cria tema moderno"""
        return {
            'name': 'Moderno',
            'description': 'Tema moderno com gradientes e cores vibrantes',
            'category': 'modern',
            'preview_colors': ['#667eea', '#764ba2', '#f093fb', '#f5f7fa'],
            'colors': {
                'primary': '#667eea',
                'secondary': '#764ba2',
                'success': '#10ac84',
                'danger': '#ee5a52',
                'warning': '#feca57',
                'info': '#3742fa',
                'light': '#f5f7fa',
                'dark': '#2f3542',
                'background': '#ffffff',
                'surface': '#f5f7fa',
                'text_primary': '#2f3542',
                'text_secondary': '#57606f',
                'border': '#a4b0be',
                'hover': '#dfe4ea'
            },
            'typography': {
                'family_primary': '"Inter", "Segoe UI", sans-serif',
                'family_monospace': '"Fira Code", "Consolas", monospace',
                'size_xs': '0.75rem',
                'size_sm': '0.875rem',
                'size_base': '1rem',
                'size_lg': '1.125rem',
                'size_xl': '1.25rem',
                'size_2xl': '1.5rem',
                'weight_normal': '400',
                'weight_medium': '500',
                'weight_bold': '600'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '3rem'
            },
            'borders': {
                'radius_sm': '0.5rem',
                'radius_md': '0.75rem',
                'radius_lg': '1rem',
                'width': '1px'
            },
            'shadows': {
                'sm': '0 2px 4px 0 rgba(102, 126, 234, 0.1)',
                'md': '0 8px 16px 0 rgba(102, 126, 234, 0.15)',
                'lg': '0 16px 32px 0 rgba(102, 126, 234, 0.2)'
            },
            'custom_css': '''
.card {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
}

.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
}
'''
        }
    
    def _create_minimal_theme(self) -> Dict[str, Any]:
        """Cria tema minimalista"""
        return {
            'name': 'Minimalista',
            'description': 'Tema limpo e minimalista com foco no conteúdo',
            'category': 'minimal',
            'preview_colors': ['#000000', '#ffffff', '#f0f0f0', '#cccccc'],
            'colors': {
                'primary': '#000000',
                'secondary': '#666666',
                'success': '#4caf50',
                'danger': '#f44336',
                'warning': '#ff9800',
                'info': '#2196f3',
                'light': '#f0f0f0',
                'dark': '#000000',
                'background': '#ffffff',
                'surface': '#fafafa',
                'text_primary': '#000000',
                'text_secondary': '#666666',
                'border': '#e0e0e0',
                'hover': '#f5f5f5'
            },
            'typography': {
                'family_primary': '"Helvetica Neue", Helvetica, Arial, sans-serif',
                'family_monospace': '"SF Mono", Monaco, monospace',
                'size_xs': '0.75rem',
                'size_sm': '0.875rem',
                'size_base': '1rem',
                'size_lg': '1.125rem',
                'size_xl': '1.25rem',
                'size_2xl': '1.5rem',
                'weight_normal': '300',
                'weight_medium': '400',
                'weight_bold': '600'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '2rem',
                'xl': '4rem'
            },
            'borders': {
                'radius_sm': '0',
                'radius_md': '0',
                'radius_lg': '0',
                'width': '1px'
            },
            'shadows': {
                'sm': 'none',
                'md': '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                'lg': '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }
        }
    
    def _create_colorful_theme(self) -> Dict[str, Any]:
        """Cria tema colorido"""
        return {
            'name': 'Colorido',
            'description': 'Tema vibrante com cores alegres e energéticas',
            'category': 'creative',
            'preview_colors': ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4'],
            'colors': {
                'primary': '#ff6b6b',
                'secondary': '#4ecdc4',
                'success': '#96ceb4',
                'danger': '#ff7675',
                'warning': '#fdcb6e',
                'info': '#45b7d1',
                'light': '#ffeaa7',
                'dark': '#2d3436',
                'background': '#ffffff',
                'surface': '#f8f9fa',
                'text_primary': '#2d3436',
                'text_secondary': '#636e72',
                'border': '#ddd',
                'hover': '#fab1a0'
            },
            'typography': {
                'family_primary': '"Poppins", "Segoe UI", sans-serif',
                'family_monospace': '"Source Code Pro", monospace',
                'size_xs': '0.75rem',
                'size_sm': '0.875rem',
                'size_base': '1rem',
                'size_lg': '1.125rem',
                'size_xl': '1.25rem',
                'size_2xl': '1.5rem',
                'weight_normal': '400',
                'weight_medium': '500',
                'weight_bold': '600'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '3rem'
            },
            'borders': {
                'radius_sm': '0.5rem',
                'radius_md': '1rem',
                'radius_lg': '1.5rem',
                'width': '2px'
            },
            'shadows': {
                'sm': '0 2px 8px 0 rgba(255, 107, 107, 0.2)',
                'md': '0 8px 16px 0 rgba(255, 107, 107, 0.3)',
                'lg': '0 16px 32px 0 rgba(255, 107, 107, 0.4)'
            },
            'custom_css': '''
.card {
    border: 2px solid var(--primary);
    background: linear-gradient(135deg, rgba(255, 107, 107, 0.1) 0%, rgba(78, 205, 196, 0.1) 100%);
}

.btn {
    border-radius: 25px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
'''
        }