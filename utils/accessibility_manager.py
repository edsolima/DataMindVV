# -*- coding: utf-8 -*-
"""
Accessibility Manager - Gerenciador de Acessibilidade
Garante conformidade com padrões WCAG e melhora a acessibilidade da plataforma
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import colorsys
import math

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager

class WCAGLevel(Enum):
    """Níveis de conformidade WCAG"""
    A = "A"
    AA = "AA"
    AAA = "AAA"

class AccessibilityFeature(Enum):
    """Recursos de acessibilidade"""
    HIGH_CONTRAST = "high_contrast"
    LARGE_TEXT = "large_text"
    KEYBOARD_NAVIGATION = "keyboard_navigation"
    SCREEN_READER = "screen_reader"
    REDUCED_MOTION = "reduced_motion"
    FOCUS_INDICATORS = "focus_indicators"
    ALT_TEXT = "alt_text"
    ARIA_LABELS = "aria_labels"
    COLOR_BLIND_FRIENDLY = "color_blind_friendly"

class ColorBlindnessType(Enum):
    """Tipos de daltonismo"""
    PROTANOPIA = "protanopia"      # Dificuldade com vermelho
    DEUTERANOPIA = "deuteranopia"  # Dificuldade com verde
    TRITANOPIA = "tritanopia"      # Dificuldade com azul
    ACHROMATOPSIA = "achromatopsia" # Monocromático

@dataclass
class ColorInfo:
    """Informações sobre cor"""
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]
    luminance: float
    name: Optional[str] = None

@dataclass
class ContrastResult:
    """Resultado de análise de contraste"""
    ratio: float
    passes_aa: bool
    passes_aaa: bool
    foreground: ColorInfo
    background: ColorInfo
    recommendation: Optional[str] = None

@dataclass
class AccessibilityIssue:
    """Problema de acessibilidade"""
    id: str
    type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    element: str
    description: str
    recommendation: str
    wcag_guideline: str
    auto_fixable: bool = False
    detected_at: datetime = None

@dataclass
class AccessibilityProfile:
    """Perfil de acessibilidade do usuário"""
    user_id: str
    enabled_features: List[AccessibilityFeature]
    font_size_multiplier: float = 1.0
    high_contrast_enabled: bool = False
    reduced_motion_enabled: bool = False
    screen_reader_enabled: bool = False
    color_blindness_type: Optional[ColorBlindnessType] = None
    custom_colors: Dict[str, str] = None
    created_at: datetime = None
    updated_at: datetime = None

class ColorAnalyzer:
    """Analisador de cores e contraste"""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Converte hex para RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hsl(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Converte RGB para HSL"""
        r, g, b = [x / 255.0 for x in rgb]
        return colorsys.rgb_to_hls(r, g, b)
    
    @staticmethod
    def calculate_luminance(rgb: Tuple[int, int, int]) -> float:
        """Calcula luminância relativa"""
        def gamma_correct(value):
            value = value / 255.0
            if value <= 0.03928:
                return value / 12.92
            else:
                return pow((value + 0.055) / 1.055, 2.4)
        
        r, g, b = rgb
        r_linear = gamma_correct(r)
        g_linear = gamma_correct(g)
        b_linear = gamma_correct(b)
        
        return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear
    
    @staticmethod
    def calculate_contrast_ratio(color1: str, color2: str) -> float:
        """Calcula razão de contraste entre duas cores"""
        rgb1 = ColorAnalyzer.hex_to_rgb(color1)
        rgb2 = ColorAnalyzer.hex_to_rgb(color2)
        
        lum1 = ColorAnalyzer.calculate_luminance(rgb1)
        lum2 = ColorAnalyzer.calculate_luminance(rgb2)
        
        # Garante que a luminância maior seja o numerador
        if lum1 > lum2:
            return (lum1 + 0.05) / (lum2 + 0.05)
        else:
            return (lum2 + 0.05) / (lum1 + 0.05)
    
    @staticmethod
    def analyze_contrast(foreground: str, background: str) -> ContrastResult:
        """Analisa contraste entre cores"""
        ratio = ColorAnalyzer.calculate_contrast_ratio(foreground, background)
        
        # WCAG 2.1 guidelines
        passes_aa = ratio >= 4.5  # AA para texto normal
        passes_aaa = ratio >= 7.0  # AAA para texto normal
        
        fg_rgb = ColorAnalyzer.hex_to_rgb(foreground)
        bg_rgb = ColorAnalyzer.hex_to_rgb(background)
        
        fg_info = ColorInfo(
            hex=foreground,
            rgb=fg_rgb,
            hsl=ColorAnalyzer.rgb_to_hsl(fg_rgb),
            luminance=ColorAnalyzer.calculate_luminance(fg_rgb)
        )
        
        bg_info = ColorInfo(
            hex=background,
            rgb=bg_rgb,
            hsl=ColorAnalyzer.rgb_to_hsl(bg_rgb),
            luminance=ColorAnalyzer.calculate_luminance(bg_rgb)
        )
        
        recommendation = None
        if not passes_aa:
            if fg_info.luminance > bg_info.luminance:
                recommendation = "Considere usar uma cor de fundo mais escura ou texto mais claro"
            else:
                recommendation = "Considere usar uma cor de fundo mais clara ou texto mais escuro"
        
        return ContrastResult(
            ratio=ratio,
            passes_aa=passes_aa,
            passes_aaa=passes_aaa,
            foreground=fg_info,
            background=bg_info,
            recommendation=recommendation
        )
    
    @staticmethod
    def simulate_color_blindness(hex_color: str, 
                               blindness_type: ColorBlindnessType) -> str:
        """Simula como uma cor aparece para diferentes tipos de daltonismo"""
        rgb = ColorAnalyzer.hex_to_rgb(hex_color)
        r, g, b = [x / 255.0 for x in rgb]
        
        if blindness_type == ColorBlindnessType.PROTANOPIA:
            # Protanopia (sem cones vermelhos)
            new_r = 0.567 * r + 0.433 * g
            new_g = 0.558 * r + 0.442 * g
            new_b = 0.242 * g + 0.758 * b
        elif blindness_type == ColorBlindnessType.DEUTERANOPIA:
            # Deuteranopia (sem cones verdes)
            new_r = 0.625 * r + 0.375 * g
            new_g = 0.7 * r + 0.3 * g
            new_b = 0.3 * g + 0.7 * b
        elif blindness_type == ColorBlindnessType.TRITANOPIA:
            # Tritanopia (sem cones azuis)
            new_r = 0.95 * r + 0.05 * g
            new_g = 0.433 * g + 0.567 * b
            new_b = 0.475 * g + 0.525 * b
        elif blindness_type == ColorBlindnessType.ACHROMATOPSIA:
            # Achromatopsia (monocromático)
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            new_r = new_g = new_b = gray
        else:
            return hex_color
        
        # Converte de volta para hex
        new_rgb = (
            max(0, min(255, int(new_r * 255))),
            max(0, min(255, int(new_g * 255))),
            max(0, min(255, int(new_b * 255)))
        )
        
        return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"
    
    @staticmethod
    def get_accessible_color_palette() -> Dict[str, str]:
        """Retorna paleta de cores acessível"""
        return {
            # Cores primárias com bom contraste
            'primary': '#0066cc',      # Azul acessível
            'secondary': '#6c757d',    # Cinza médio
            'success': '#28a745',      # Verde acessível
            'warning': '#ffc107',      # Amarelo com contraste
            'danger': '#dc3545',       # Vermelho acessível
            'info': '#17a2b8',        # Ciano acessível
            
            # Cores de fundo
            'light': '#f8f9fa',       # Fundo claro
            'dark': '#343a40',        # Fundo escuro
            
            # Cores de texto
            'text-primary': '#212529', # Texto principal
            'text-secondary': '#6c757d', # Texto secundário
            'text-light': '#ffffff',   # Texto claro
            
            # Cores para daltonismo
            'colorblind-safe-1': '#1f77b4',  # Azul
            'colorblind-safe-2': '#ff7f0e',  # Laranja
            'colorblind-safe-3': '#2ca02c',  # Verde
            'colorblind-safe-4': '#d62728',  # Vermelho
            'colorblind-safe-5': '#9467bd',  # Roxo
            'colorblind-safe-6': '#8c564b',  # Marrom
        }

class AccessibilityChecker:
    """Verificador de acessibilidade"""
    
    def __init__(self):
        self.issues: List[AccessibilityIssue] = []
    
    def check_color_contrast(self, elements: List[Dict[str, str]]) -> List[AccessibilityIssue]:
        """Verifica contraste de cores"""
        issues = []
        
        for element in elements:
            fg_color = element.get('color', '#000000')
            bg_color = element.get('background-color', '#ffffff')
            element_id = element.get('id', 'unknown')
            
            contrast = ColorAnalyzer.analyze_contrast(fg_color, bg_color)
            
            if not contrast.passes_aa:
                severity = 'high' if contrast.ratio < 3.0 else 'medium'
                
                issue = AccessibilityIssue(
                    id=f"contrast_{element_id}_{datetime.now().timestamp()}",
                    type="color_contrast",
                    severity=severity,
                    element=element_id,
                    description=f"Contraste insuficiente: {contrast.ratio:.2f}:1 (mínimo 4.5:1)",
                    recommendation=contrast.recommendation or "Ajuste as cores para melhor contraste",
                    wcag_guideline="1.4.3 Contrast (Minimum)",
                    auto_fixable=True,
                    detected_at=datetime.now()
                )
                
                issues.append(issue)
        
        return issues
    
    def check_alt_text(self, images: List[Dict[str, str]]) -> List[AccessibilityIssue]:
        """Verifica texto alternativo em imagens"""
        issues = []
        
        for image in images:
            alt_text = image.get('alt', '')
            src = image.get('src', '')
            element_id = image.get('id', src)
            
            if not alt_text or alt_text.strip() == '':
                issue = AccessibilityIssue(
                    id=f"alt_text_{element_id}_{datetime.now().timestamp()}",
                    type="missing_alt_text",
                    severity="high",
                    element=element_id,
                    description="Imagem sem texto alternativo",
                    recommendation="Adicione texto alternativo descritivo para a imagem",
                    wcag_guideline="1.1.1 Non-text Content",
                    auto_fixable=False,
                    detected_at=datetime.now()
                )
                
                issues.append(issue)
            elif len(alt_text) > 125:
                issue = AccessibilityIssue(
                    id=f"alt_text_long_{element_id}_{datetime.now().timestamp()}",
                    type="alt_text_too_long",
                    severity="low",
                    element=element_id,
                    description="Texto alternativo muito longo",
                    recommendation="Mantenha o texto alternativo conciso (máximo 125 caracteres)",
                    wcag_guideline="1.1.1 Non-text Content",
                    auto_fixable=False,
                    detected_at=datetime.now()
                )
                
                issues.append(issue)
        
        return issues
    
    def check_heading_structure(self, headings: List[Dict[str, str]]) -> List[AccessibilityIssue]:
        """Verifica estrutura de cabeçalhos"""
        issues = []
        
        if not headings:
            return issues
        
        # Ordena por ordem de aparição
        headings.sort(key=lambda h: int(h.get('order', 0)))
        
        prev_level = 0
        
        for heading in headings:
            level = int(heading.get('level', 1))
            element_id = heading.get('id', f'heading_{level}')
            
            # Verifica se pula níveis
            if level > prev_level + 1 and prev_level > 0:
                issue = AccessibilityIssue(
                    id=f"heading_skip_{element_id}_{datetime.now().timestamp()}",
                    type="heading_structure",
                    severity="medium",
                    element=element_id,
                    description=f"Cabeçalho h{level} pula do nível h{prev_level}",
                    recommendation="Use níveis de cabeçalho sequenciais (h1, h2, h3...)",
                    wcag_guideline="1.3.1 Info and Relationships",
                    auto_fixable=True,
                    detected_at=datetime.now()
                )
                
                issues.append(issue)
            
            prev_level = level
        
        return issues
    
    def check_form_labels(self, form_elements: List[Dict[str, str]]) -> List[AccessibilityIssue]:
        """Verifica rótulos de formulários"""
        issues = []
        
        for element in form_elements:
            element_type = element.get('type', '')
            element_id = element.get('id', 'unknown')
            label = element.get('label', '')
            aria_label = element.get('aria-label', '')
            aria_labelledby = element.get('aria-labelledby', '')
            
            # Elementos que precisam de rótulo
            if element_type in ['text', 'email', 'password', 'number', 'tel', 'url', 'search', 'textarea', 'select']:
                if not any([label, aria_label, aria_labelledby]):
                    issue = AccessibilityIssue(
                        id=f"form_label_{element_id}_{datetime.now().timestamp()}",
                        type="missing_form_label",
                        severity="high",
                        element=element_id,
                        description="Campo de formulário sem rótulo",
                        recommendation="Adicione um rótulo, aria-label ou aria-labelledby",
                        wcag_guideline="1.3.1 Info and Relationships",
                        auto_fixable=False,
                        detected_at=datetime.now()
                    )
                    
                    issues.append(issue)
        
        return issues

class AccessibilityManager:
    """Gerenciador de acessibilidade"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.color_analyzer = ColorAnalyzer()
        self.checker = AccessibilityChecker()
        
        # Perfis de usuário
        self.user_profiles: Dict[str, AccessibilityProfile] = {}
        
        # Configurações globais
        self.global_settings = {
            'wcag_level': WCAGLevel.AA,
            'auto_fix_enabled': True,
            'check_interval': 3600,  # segundos
            'default_font_size': 16,
            'min_contrast_ratio': 4.5
        }
        
        # Carrega configurações
        self._load_settings()
        
        log_info("Gerenciador de acessibilidade inicializado")
    
    def _load_settings(self):
        """Carrega configurações de acessibilidade"""
        try:
            settings = self.config_manager.get_config('accessibility', {})
            self.global_settings.update(settings)
            
            log_info("Configurações de acessibilidade carregadas")
        except Exception as e:
            log_error(f"Erro ao carregar configurações de acessibilidade: {e}")
    
    def create_user_profile(self, user_id: str, 
                          features: List[AccessibilityFeature] = None) -> AccessibilityProfile:
        """Cria perfil de acessibilidade para usuário"""
        try:
            profile = AccessibilityProfile(
                user_id=user_id,
                enabled_features=features or [],
                created_at=datetime.now()
            )
            
            self.user_profiles[user_id] = profile
            
            log_info(f"Perfil de acessibilidade criado para usuário {user_id}")
            return profile
            
        except Exception as e:
            log_error(f"Erro ao criar perfil de acessibilidade: {e}")
            return None
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza perfil de acessibilidade"""
        try:
            if user_id not in self.user_profiles:
                return False
            
            profile = self.user_profiles[user_id]
            
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.now()
            
            log_info(f"Perfil de acessibilidade atualizado para usuário {user_id}")
            return True
            
        except Exception as e:
            log_error(f"Erro ao atualizar perfil: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[AccessibilityProfile]:
        """Retorna perfil de acessibilidade do usuário"""
        return self.user_profiles.get(user_id)
    
    def generate_accessible_css(self, user_id: str = None) -> str:
        """Gera CSS personalizado para acessibilidade"""
        try:
            profile = self.user_profiles.get(user_id) if user_id else None
            css_rules = []
            
            # CSS base para acessibilidade
            css_rules.extend([
                "/* Acessibilidade - CSS Gerado */",
                "",
                "/* Foco visível */",
                "*:focus {",
                "    outline: 2px solid #0066cc !important;",
                "    outline-offset: 2px !important;",
                "}",
                "",
                "/* Skip links */",
                ".skip-link {",
                "    position: absolute;",
                "    top: -40px;",
                "    left: 6px;",
                "    background: #000;",
                "    color: #fff;",
                "    padding: 8px;",
                "    text-decoration: none;",
                "    z-index: 9999;",
                "}",
                "",
                ".skip-link:focus {",
                "    top: 6px;",
                "}",
                ""
            ])
            
            # Personalizações baseadas no perfil
            if profile:
                # Tamanho da fonte
                if profile.font_size_multiplier != 1.0:
                    css_rules.extend([
                        "/* Tamanho de fonte personalizado */",
                        "html {",
                        f"    font-size: {16 * profile.font_size_multiplier}px !important;",
                        "}",
                        ""
                    ])
                
                # Alto contraste
                if profile.high_contrast_enabled:
                    css_rules.extend([
                        "/* Alto contraste */",
                        "body {",
                        "    background: #000000 !important;",
                        "    color: #ffffff !important;",
                        "}",
                        "",
                        ".card, .modal-content, .dropdown-menu {",
                        "    background: #1a1a1a !important;",
                        "    color: #ffffff !important;",
                        "    border: 2px solid #ffffff !important;",
                        "}",
                        "",
                        "a {",
                        "    color: #00ffff !important;",
                        "}",
                        "",
                        "button, .btn {",
                        "    background: #ffffff !important;",
                        "    color: #000000 !important;",
                        "    border: 2px solid #ffffff !important;",
                        "}",
                        ""
                    ])
                
                # Movimento reduzido
                if profile.reduced_motion_enabled:
                    css_rules.extend([
                        "/* Movimento reduzido */",
                        "@media (prefers-reduced-motion: reduce) {",
                        "    *, *::before, *::after {",
                        "        animation-duration: 0.01ms !important;",
                        "        animation-iteration-count: 1 !important;",
                        "        transition-duration: 0.01ms !important;",
                        "    }",
                        "}",
                        "",
                        ".no-motion * {",
                        "    animation: none !important;",
                        "    transition: none !important;",
                        "}",
                        ""
                    ])
                
                # Cores personalizadas para daltonismo
                if profile.color_blindness_type:
                    accessible_palette = self.color_analyzer.get_accessible_color_palette()
                    css_rules.extend([
                        "/* Paleta para daltonismo */",
                        ":root {"
                    ])
                    
                    for name, color in accessible_palette.items():
                        if 'colorblind-safe' in name:
                            css_rules.append(f"    --{name}: {color};")
                    
                    css_rules.extend([
                        "}",
                        ""
                    ])
            
            return "\n".join(css_rules)
            
        except Exception as e:
            log_error(f"Erro ao gerar CSS de acessibilidade: {e}")
            return ""
    
    def run_accessibility_audit(self, page_elements: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Executa auditoria de acessibilidade"""
        try:
            all_issues = []
            
            # Verifica contraste de cores
            if 'text_elements' in page_elements:
                contrast_issues = self.checker.check_color_contrast(page_elements['text_elements'])
                all_issues.extend(contrast_issues)
            
            # Verifica texto alternativo
            if 'images' in page_elements:
                alt_issues = self.checker.check_alt_text(page_elements['images'])
                all_issues.extend(alt_issues)
            
            # Verifica estrutura de cabeçalhos
            if 'headings' in page_elements:
                heading_issues = self.checker.check_heading_structure(page_elements['headings'])
                all_issues.extend(heading_issues)
            
            # Verifica rótulos de formulário
            if 'form_elements' in page_elements:
                form_issues = self.checker.check_form_labels(page_elements['form_elements'])
                all_issues.extend(form_issues)
            
            # Calcula pontuação
            total_elements = sum(len(elements) for elements in page_elements.values())
            critical_issues = len([i for i in all_issues if i.severity == 'critical'])
            high_issues = len([i for i in all_issues if i.severity == 'high'])
            medium_issues = len([i for i in all_issues if i.severity == 'medium'])
            low_issues = len([i for i in all_issues if i.severity == 'low'])
            
            # Pontuação baseada na severidade (0-100)
            penalty = (critical_issues * 25) + (high_issues * 15) + (medium_issues * 8) + (low_issues * 3)
            score = max(0, 100 - penalty)
            
            # Determina nível WCAG
            wcag_level = WCAGLevel.AAA
            if critical_issues > 0 or high_issues > 0:
                wcag_level = None  # Não atende nenhum nível
            elif medium_issues > 0:
                wcag_level = WCAGLevel.A
            elif low_issues > 2:
                wcag_level = WCAGLevel.AA
            
            return {
                'score': score,
                'wcag_level': wcag_level.value if wcag_level else None,
                'total_issues': len(all_issues),
                'issues_by_severity': {
                    'critical': critical_issues,
                    'high': high_issues,
                    'medium': medium_issues,
                    'low': low_issues
                },
                'issues': [asdict(issue) for issue in all_issues],
                'recommendations': self._generate_recommendations(all_issues),
                'audit_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(f"Erro na auditoria de acessibilidade: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, issues: List[AccessibilityIssue]) -> List[str]:
        """Gera recomendações baseadas nos problemas encontrados"""
        recommendations = []
        
        issue_types = {}
        for issue in issues:
            if issue.type not in issue_types:
                issue_types[issue.type] = 0
            issue_types[issue.type] += 1
        
        if 'color_contrast' in issue_types:
            recommendations.append(
                f"Corrija {issue_types['color_contrast']} problemas de contraste de cores para melhorar a legibilidade"
            )
        
        if 'missing_alt_text' in issue_types:
            recommendations.append(
                f"Adicione texto alternativo a {issue_types['missing_alt_text']} imagens para usuários de leitores de tela"
            )
        
        if 'heading_structure' in issue_types:
            recommendations.append(
                "Organize os cabeçalhos em uma hierarquia lógica (h1, h2, h3...)"
            )
        
        if 'missing_form_label' in issue_types:
            recommendations.append(
                f"Adicione rótulos a {issue_types['missing_form_label']} campos de formulário"
            )
        
        if not recommendations:
            recommendations.append("Parabéns! Nenhum problema crítico de acessibilidade foi encontrado.")
        
        return recommendations
    
    def get_accessibility_report(self) -> Dict[str, Any]:
        """Gera relatório de acessibilidade"""
        try:
            return {
                'total_users_with_profiles': len(self.user_profiles),
                'enabled_features': self._get_feature_usage_stats(),
                'global_settings': self.global_settings,
                'color_palette': self.color_analyzer.get_accessible_color_palette(),
                'wcag_guidelines': {
                    'level': self.global_settings['wcag_level'].value,
                    'min_contrast_ratio': self.global_settings['min_contrast_ratio']
                },
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            log_error(f"Erro ao gerar relatório de acessibilidade: {e}")
            return {'error': str(e)}
    
    def _get_feature_usage_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de uso de recursos"""
        stats = {}
        
        for feature in AccessibilityFeature:
            stats[feature.value] = 0
        
        for profile in self.user_profiles.values():
            for feature in profile.enabled_features:
                if feature.value in stats:
                    stats[feature.value] += 1
        
        return stats