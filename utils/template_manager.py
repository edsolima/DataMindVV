# -*- coding: utf-8 -*-
"""
Template Manager - Gerenciamento de Templates de Dashboard
Fornece templates pré-construídos para casos de uso comuns
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager

class TemplateManager:
    """Gerenciador de templates de dashboard"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = templates_dir
        self.config_manager = ConfigManager()
        self._ensure_templates_dir()
        self._load_default_templates()
    
    def _ensure_templates_dir(self):
        """Garante que o diretório de templates existe"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            log_info(f"Diretório de templates criado: {self.templates_dir}")
    
    def _load_default_templates(self):
        """Carrega templates padrão se não existirem"""
        default_templates = {
            'sales_analysis': self._create_sales_analysis_template(),
            'executive_dashboard': self._create_executive_dashboard_template(),
            'financial_report': self._create_financial_report_template(),
            'kpi_monitoring': self._create_kpi_monitoring_template(),
            'marketing_analytics': self._create_marketing_analytics_template()
        }
        
        for template_id, template_data in default_templates.items():
            template_file = os.path.join(self.templates_dir, f"{template_id}.json")
            if not os.path.exists(template_file):
                self.save_template(template_id, template_data)
                log_info(f"Template padrão criado: {template_id}")
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Obtém um template pelo ID"""
        try:
            template_file = os.path.join(self.templates_dir, f"{template_id}.json")
            if os.path.exists(template_file):
                with open(template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            log_error(f"Erro ao carregar template {template_id}", extra={"error": str(e)})
            return None
    
    def save_template(self, template_id: str, template_data: Dict[str, Any]) -> bool:
        """Salva um template"""
        try:
            template_file = os.path.join(self.templates_dir, f"{template_id}.json")
            
            # Adiciona metadados
            template_data['metadata'] = {
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
            
            log_info(f"Template salvo: {template_id}")
            return True
        except Exception as e:
            log_error(f"Erro ao salvar template {template_id}", extra={"error": str(e)})
            return False
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """Lista todos os templates disponíveis"""
        templates = []
        try:
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.json'):
                    template_id = filename[:-5]  # Remove .json
                    template_data = self.get_template(template_id)
                    if template_data:
                        templates.append({
                            'id': template_id,
                            'name': template_data.get('name', template_id),
                            'description': template_data.get('description', ''),
                            'category': template_data.get('category', 'general'),
                            'preview_image': template_data.get('preview_image', ''),
                            'metadata': template_data.get('metadata', {})
                        })
        except Exception as e:
            log_error(f"Erro ao listar templates", extra={"error": str(e)})
        
        return templates
    
    def delete_template(self, template_id: str) -> bool:
        """Deleta um template"""
        try:
            template_file = os.path.join(self.templates_dir, f"{template_id}.json")
            if os.path.exists(template_file):
                os.remove(template_file)
                log_info(f"Template deletado: {template_id}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao deletar template {template_id}", extra={"error": str(e)})
            return False
    
    def _create_sales_analysis_template(self) -> Dict[str, Any]:
        """Cria template de análise de vendas"""
        return {
            'name': 'Análise de Vendas',
            'description': 'Dashboard completo para análise de vendas e performance comercial',
            'category': 'vendas',
            'preview_image': '/assets/templates/sales_analysis.png',
            'layout': {
                'lg': [
                    {'i': 'title_1', 'x': 0, 'y': 0, 'w': 12, 'h': 1},
                    {'i': 'kpi_1', 'x': 0, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'kpi_2', 'x': 3, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'kpi_3', 'x': 6, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'kpi_4', 'x': 9, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'chart_1', 'x': 0, 'y': 3, 'w': 8, 'h': 4},
                    {'i': 'chart_2', 'x': 8, 'y': 3, 'w': 4, 'h': 4},
                    {'i': 'table_1', 'x': 0, 'y': 7, 'w': 12, 'h': 4}
                ]
            },
            'components': {
                'title_1': {
                    'type': 'text',
                    'title': 'Dashboard de Vendas',
                    'config': {
                        'title': 'Dashboard de Vendas',
                        'content': 'Análise completa de performance comercial',
                        'alignment': 'center',
                        'font_size': 'large'
                    }
                },
                'kpi_1': {
                    'type': 'kpi',
                    'title': 'Vendas Totais',
                    'config': {
                        'value': 'R$ 1.250.000',
                        'label': 'Vendas Totais',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+15.2%'
                    }
                },
                'kpi_2': {
                    'type': 'kpi',
                    'title': 'Novos Clientes',
                    'config': {
                        'value': '342',
                        'label': 'Novos Clientes',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+8.7%'
                    }
                },
                'kpi_3': {
                    'type': 'kpi',
                    'title': 'Ticket Médio',
                    'config': {
                        'value': 'R$ 3.654',
                        'label': 'Ticket Médio',
                        'format': 'currency',
                        'trend': 'down',
                        'trend_value': '-2.1%'
                    }
                },
                'kpi_4': {
                    'type': 'kpi',
                    'title': 'Taxa Conversão',
                    'config': {
                        'value': '12.8%',
                        'label': 'Taxa de Conversão',
                        'format': 'percentage',
                        'trend': 'up',
                        'trend_value': '+1.3%'
                    }
                },
                'chart_1': {
                    'type': 'chart',
                    'title': 'Vendas por Mês',
                    'config': {
                        'chart_type': 'line',
                        'title': 'Evolução das Vendas',
                        'x_axis': 'mes',
                        'y_axis': 'vendas',
                        'color_scheme': 'plotly'
                    }
                },
                'chart_2': {
                    'type': 'chart',
                    'title': 'Vendas por Região',
                    'config': {
                        'chart_type': 'pie',
                        'title': 'Distribuição por Região',
                        'x_axis': 'regiao',
                        'y_axis': 'vendas',
                        'color_scheme': 'viridis'
                    }
                },
                'table_1': {
                    'type': 'table',
                    'title': 'Top Produtos',
                    'config': {
                        'columns': ['produto', 'vendas', 'margem', 'status'],
                        'max_rows': 10,
                        'sortable': True,
                        'filterable': True
                    }
                }
            }
        }
    
    def _create_executive_dashboard_template(self) -> Dict[str, Any]:
        """Cria template de dashboard executivo"""
        return {
            'name': 'Dashboard Executivo',
            'description': 'Visão executiva com KPIs principais e métricas estratégicas',
            'category': 'executivo',
            'preview_image': '/assets/templates/executive_dashboard.png',
            'layout': {
                'lg': [
                    {'i': 'title_1', 'x': 0, 'y': 0, 'w': 12, 'h': 1},
                    {'i': 'kpi_1', 'x': 0, 'y': 1, 'w': 2, 'h': 2},
                    {'i': 'kpi_2', 'x': 2, 'y': 1, 'w': 2, 'h': 2},
                    {'i': 'kpi_3', 'x': 4, 'y': 1, 'w': 2, 'h': 2},
                    {'i': 'kpi_4', 'x': 6, 'y': 1, 'w': 2, 'h': 2},
                    {'i': 'kpi_5', 'x': 8, 'y': 1, 'w': 2, 'h': 2},
                    {'i': 'kpi_6', 'x': 10, 'y': 1, 'w': 2, 'h': 2},
                    {'i': 'chart_1', 'x': 0, 'y': 3, 'w': 6, 'h': 4},
                    {'i': 'chart_2', 'x': 6, 'y': 3, 'w': 6, 'h': 4}
                ]
            },
            'components': {
                'title_1': {
                    'type': 'text',
                    'title': 'Dashboard Executivo',
                    'config': {
                        'title': 'Dashboard Executivo',
                        'content': 'Visão estratégica dos principais indicadores',
                        'alignment': 'center',
                        'font_size': 'large'
                    }
                },
                'kpi_1': {
                    'type': 'kpi',
                    'title': 'Receita',
                    'config': {
                        'value': 'R$ 5.2M',
                        'label': 'Receita Total',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+12%'
                    }
                },
                'kpi_2': {
                    'type': 'kpi',
                    'title': 'Lucro',
                    'config': {
                        'value': 'R$ 890K',
                        'label': 'Lucro Líquido',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+8%'
                    }
                },
                'kpi_3': {
                    'type': 'kpi',
                    'title': 'Margem',
                    'config': {
                        'value': '17.1%',
                        'label': 'Margem Líquida',
                        'format': 'percentage',
                        'trend': 'down',
                        'trend_value': '-1.2%'
                    }
                },
                'kpi_4': {
                    'type': 'kpi',
                    'title': 'Clientes',
                    'config': {
                        'value': '12.5K',
                        'label': 'Clientes Ativos',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+5%'
                    }
                },
                'kpi_5': {
                    'type': 'kpi',
                    'title': 'NPS',
                    'config': {
                        'value': '72',
                        'label': 'Net Promoter Score',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+3'
                    }
                },
                'kpi_6': {
                    'type': 'kpi',
                    'title': 'Funcionários',
                    'config': {
                        'value': '245',
                        'label': 'Total Funcionários',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+12'
                    }
                },
                'chart_1': {
                    'type': 'chart',
                    'title': 'Performance Financeira',
                    'config': {
                        'chart_type': 'line',
                        'title': 'Receita vs Lucro (12 meses)',
                        'x_axis': 'mes',
                        'y_axis': 'valor',
                        'color_scheme': 'plotly'
                    }
                },
                'chart_2': {
                    'type': 'chart',
                    'title': 'Distribuição de Receita',
                    'config': {
                        'chart_type': 'treemap',
                        'title': 'Receita por Unidade de Negócio',
                        'x_axis': 'unidade',
                        'y_axis': 'receita',
                        'color_scheme': 'viridis'
                    }
                }
            }
        }
    
    def _create_financial_report_template(self) -> Dict[str, Any]:
        """Cria template de relatório financeiro"""
        return {
            'name': 'Relatório Financeiro',
            'description': 'Relatório completo com análises financeiras e contábeis',
            'category': 'financeiro',
            'preview_image': '/assets/templates/financial_report.png',
            'layout': {
                'lg': [
                    {'i': 'title_1', 'x': 0, 'y': 0, 'w': 12, 'h': 1},
                    {'i': 'kpi_1', 'x': 0, 'y': 1, 'w': 4, 'h': 2},
                    {'i': 'kpi_2', 'x': 4, 'y': 1, 'w': 4, 'h': 2},
                    {'i': 'kpi_3', 'x': 8, 'y': 1, 'w': 4, 'h': 2},
                    {'i': 'chart_1', 'x': 0, 'y': 3, 'w': 12, 'h': 4},
                    {'i': 'chart_2', 'x': 0, 'y': 7, 'w': 6, 'h': 4},
                    {'i': 'chart_3', 'x': 6, 'y': 7, 'w': 6, 'h': 4},
                    {'i': 'table_1', 'x': 0, 'y': 11, 'w': 12, 'h': 4}
                ]
            },
            'components': {
                'title_1': {
                    'type': 'text',
                    'title': 'Relatório Financeiro',
                    'config': {
                        'title': 'Relatório Financeiro Mensal',
                        'content': 'Análise detalhada da situação financeira',
                        'alignment': 'center',
                        'font_size': 'large'
                    }
                },
                'kpi_1': {
                    'type': 'kpi',
                    'title': 'Receita Bruta',
                    'config': {
                        'value': 'R$ 2.8M',
                        'label': 'Receita Bruta',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+18%'
                    }
                },
                'kpi_2': {
                    'type': 'kpi',
                    'title': 'Custos Operacionais',
                    'config': {
                        'value': 'R$ 1.9M',
                        'label': 'Custos Operacionais',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+12%'
                    }
                },
                'kpi_3': {
                    'type': 'kpi',
                    'title': 'EBITDA',
                    'config': {
                        'value': 'R$ 650K',
                        'label': 'EBITDA',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+25%'
                    }
                },
                'chart_1': {
                    'type': 'chart',
                    'title': 'Fluxo de Caixa',
                    'config': {
                        'chart_type': 'waterfall',
                        'title': 'Fluxo de Caixa Mensal',
                        'x_axis': 'categoria',
                        'y_axis': 'valor',
                        'color_scheme': 'RdYlGn'
                    }
                },
                'chart_2': {
                    'type': 'chart',
                    'title': 'Receita vs Despesas',
                    'config': {
                        'chart_type': 'bar',
                        'title': 'Comparativo Mensal',
                        'x_axis': 'mes',
                        'y_axis': 'valor',
                        'color_scheme': 'plotly'
                    }
                },
                'chart_3': {
                    'type': 'chart',
                    'title': 'Composição de Custos',
                    'config': {
                        'chart_type': 'pie',
                        'title': 'Distribuição de Custos',
                        'x_axis': 'categoria',
                        'y_axis': 'valor',
                        'color_scheme': 'Set3'
                    }
                },
                'table_1': {
                    'type': 'table',
                    'title': 'Demonstrativo Detalhado',
                    'config': {
                        'columns': ['conta', 'valor_atual', 'valor_anterior', 'variacao'],
                        'max_rows': 15,
                        'sortable': True,
                        'filterable': True
                    }
                }
            }
        }
    
    def _create_kpi_monitoring_template(self) -> Dict[str, Any]:
        """Cria template de monitoramento de KPIs"""
        return {
            'name': 'Monitoramento de KPIs',
            'description': 'Dashboard focado no acompanhamento de indicadores chave',
            'category': 'kpi',
            'preview_image': '/assets/templates/kpi_monitoring.png',
            'layout': {
                'lg': [
                    {'i': 'title_1', 'x': 0, 'y': 0, 'w': 12, 'h': 1},
                    {'i': 'kpi_1', 'x': 0, 'y': 1, 'w': 3, 'h': 3},
                    {'i': 'kpi_2', 'x': 3, 'y': 1, 'w': 3, 'h': 3},
                    {'i': 'kpi_3', 'x': 6, 'y': 1, 'w': 3, 'h': 3},
                    {'i': 'kpi_4', 'x': 9, 'y': 1, 'w': 3, 'h': 3},
                    {'i': 'kpi_5', 'x': 0, 'y': 4, 'w': 3, 'h': 3},
                    {'i': 'kpi_6', 'x': 3, 'y': 4, 'w': 3, 'h': 3},
                    {'i': 'kpi_7', 'x': 6, 'y': 4, 'w': 3, 'h': 3},
                    {'i': 'kpi_8', 'x': 9, 'y': 4, 'w': 3, 'h': 3}
                ]
            },
            'components': {
                'title_1': {
                    'type': 'text',
                    'title': 'Monitoramento de KPIs',
                    'config': {
                        'title': 'Dashboard de KPIs',
                        'content': 'Acompanhamento em tempo real dos principais indicadores',
                        'alignment': 'center',
                        'font_size': 'large'
                    }
                },
                'kpi_1': {
                    'type': 'kpi',
                    'title': 'Vendas',
                    'config': {
                        'value': 'R$ 125K',
                        'label': 'Vendas do Mês',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+15%'
                    }
                },
                'kpi_2': {
                    'type': 'kpi',
                    'title': 'Leads',
                    'config': {
                        'value': '1,234',
                        'label': 'Novos Leads',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+8%'
                    }
                },
                'kpi_3': {
                    'type': 'kpi',
                    'title': 'Conversão',
                    'config': {
                        'value': '12.5%',
                        'label': 'Taxa Conversão',
                        'format': 'percentage',
                        'trend': 'down',
                        'trend_value': '-2%'
                    }
                },
                'kpi_4': {
                    'type': 'kpi',
                    'title': 'CAC',
                    'config': {
                        'value': 'R$ 245',
                        'label': 'Custo Aquisição',
                        'format': 'currency',
                        'trend': 'down',
                        'trend_value': '-5%'
                    }
                },
                'kpi_5': {
                    'type': 'kpi',
                    'title': 'LTV',
                    'config': {
                        'value': 'R$ 2.8K',
                        'label': 'Lifetime Value',
                        'format': 'currency',
                        'trend': 'up',
                        'trend_value': '+12%'
                    }
                },
                'kpi_6': {
                    'type': 'kpi',
                    'title': 'Churn',
                    'config': {
                        'value': '3.2%',
                        'label': 'Taxa de Churn',
                        'format': 'percentage',
                        'trend': 'down',
                        'trend_value': '-0.8%'
                    }
                },
                'kpi_7': {
                    'type': 'kpi',
                    'title': 'NPS',
                    'config': {
                        'value': '68',
                        'label': 'Net Promoter Score',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+5'
                    }
                },
                'kpi_8': {
                    'type': 'kpi',
                    'title': 'ROI',
                    'config': {
                        'value': '245%',
                        'label': 'Return on Investment',
                        'format': 'percentage',
                        'trend': 'up',
                        'trend_value': '+18%'
                    }
                }
            }
        }
    
    def _create_marketing_analytics_template(self) -> Dict[str, Any]:
        """Cria template de analytics de marketing"""
        return {
            'name': 'Analytics de Marketing',
            'description': 'Dashboard para análise de campanhas e performance de marketing',
            'category': 'marketing',
            'preview_image': '/assets/templates/marketing_analytics.png',
            'layout': {
                'lg': [
                    {'i': 'title_1', 'x': 0, 'y': 0, 'w': 12, 'h': 1},
                    {'i': 'kpi_1', 'x': 0, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'kpi_2', 'x': 3, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'kpi_3', 'x': 6, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'kpi_4', 'x': 9, 'y': 1, 'w': 3, 'h': 2},
                    {'i': 'chart_1', 'x': 0, 'y': 3, 'w': 8, 'h': 4},
                    {'i': 'chart_2', 'x': 8, 'y': 3, 'w': 4, 'h': 4},
                    {'i': 'chart_3', 'x': 0, 'y': 7, 'w': 6, 'h': 4},
                    {'i': 'chart_4', 'x': 6, 'y': 7, 'w': 6, 'h': 4}
                ]
            },
            'components': {
                'title_1': {
                    'type': 'text',
                    'title': 'Marketing Analytics',
                    'config': {
                        'title': 'Dashboard de Marketing',
                        'content': 'Análise de performance de campanhas e canais',
                        'alignment': 'center',
                        'font_size': 'large'
                    }
                },
                'kpi_1': {
                    'type': 'kpi',
                    'title': 'Impressões',
                    'config': {
                        'value': '2.5M',
                        'label': 'Total Impressões',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+22%'
                    }
                },
                'kpi_2': {
                    'type': 'kpi',
                    'title': 'Cliques',
                    'config': {
                        'value': '125K',
                        'label': 'Total Cliques',
                        'format': 'number',
                        'trend': 'up',
                        'trend_value': '+18%'
                    }
                },
                'kpi_3': {
                    'type': 'kpi',
                    'title': 'CTR',
                    'config': {
                        'value': '5.2%',
                        'label': 'Click Through Rate',
                        'format': 'percentage',
                        'trend': 'down',
                        'trend_value': '-0.3%'
                    }
                },
                'kpi_4': {
                    'type': 'kpi',
                    'title': 'CPC',
                    'config': {
                        'value': 'R$ 1.25',
                        'label': 'Custo por Clique',
                        'format': 'currency',
                        'trend': 'down',
                        'trend_value': '-8%'
                    }
                },
                'chart_1': {
                    'type': 'chart',
                    'title': 'Performance por Canal',
                    'config': {
                        'chart_type': 'line',
                        'title': 'Evolução por Canal de Marketing',
                        'x_axis': 'data',
                        'y_axis': 'conversoes',
                        'color_scheme': 'plotly'
                    }
                },
                'chart_2': {
                    'type': 'chart',
                    'title': 'Distribuição de Budget',
                    'config': {
                        'chart_type': 'pie',
                        'title': 'Investimento por Canal',
                        'x_axis': 'canal',
                        'y_axis': 'investimento',
                        'color_scheme': 'Set2'
                    }
                },
                'chart_3': {
                    'type': 'chart',
                    'title': 'Funil de Conversão',
                    'config': {
                        'chart_type': 'funnel',
                        'title': 'Funil de Marketing',
                        'x_axis': 'etapa',
                        'y_axis': 'usuarios',
                        'color_scheme': 'Blues'
                    }
                },
                'chart_4': {
                    'type': 'chart',
                    'title': 'ROI por Campanha',
                    'config': {
                        'chart_type': 'bar',
                        'title': 'Retorno sobre Investimento',
                        'x_axis': 'campanha',
                        'y_axis': 'roi',
                        'color_scheme': 'viridis'
                    }
                }
            }
        }