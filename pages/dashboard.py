# Dashboard Moderno - Refatoração Completa
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table, ALL, MATCH
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import json
import uuid
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate

from utils.logger import log_info, log_error, log_warning, log_debug
from utils.ui_helpers import create_preview_table, show_feedback_alert

# Variável global para a instância do cache
cache = None

# Temas para modo escuro/claro
THEMES = {
    'light': {
        'primary': '#0d6efd',
        'secondary': '#6c757d', 
        'success': '#198754',
        'warning': '#ffc107',
        'danger': '#dc3545',
        'info': '#0dcaf0',
        'background': '#ffffff',
        'surface': '#f8f9fa',
        'text': '#212529',
        'text_secondary': '#6c757d',
        'border': '#dee2e6'
    },
    'dark': {
        'primary': '#0d6efd',
        'secondary': '#6c757d',
        'success': '#198754', 
        'warning': '#ffc107',
        'danger': '#dc3545',
        'info': '#0dcaf0',
        'background': '#212529',
        'surface': '#343a40',
        'text': '#ffffff',
        'text_secondary': '#adb5bd',
        'border': '#495057'
    }
}

def create_header(theme='light'):
    """Cria cabeçalho fixo elegante com logo e opções avançadas"""
    colors = THEMES[theme]
    
    # Definir estilo do logo baseado no tema
    logo_style = {
        'color': colors['primary'],
        'filter': 'drop-shadow(0px 2px 2px rgba(0,0,0,0.2))',
        'transition': 'all 0.3s ease'
    }
    
    # Definir estilo do título baseado no tema
    title_style = {
        'color': colors['text'],
        'transition': 'all 0.3s ease'
    }
    
    # Definir estilo do subtítulo baseado no tema
    subtitle_style = {
        'color': colors['text_secondary'],
        'fontSize': '0.9rem',
        'transition': 'all 0.3s ease'
    }
    
    return dbc.Navbar(
        dbc.Container([
            # Logo e título com animação suave
            dbc.Row([
                dbc.Col([
                    html.Div([
                        # Logo com efeito de sombra
                        html.Div([
                            html.I(className="fas fa-chart-line fa-2x", style=logo_style),
                            html.I(className="fas fa-analytics fa-2x ms-n2", style={**logo_style, 'opacity': '0.7'})
                        ], className="d-flex position-relative me-3"),
                        
                        # Título e subtítulo
                        html.Div([
                            html.H3("DataMindVV", className="mb-0 fw-bold", style=title_style),
                            html.Small("Dashboard Analítico Executivo", style=subtitle_style)
                        ])
                    ], className="d-flex align-items-center")
                ], width="auto"),
                
                # Informações e status do sistema
                dbc.Col([
                    html.Div([
                        html.Span("Última atualização: ", className="me-1", style={'color': colors['text_secondary']}),
                        html.Span(id="last-update-time", children=datetime.now().strftime("%d/%m/%Y %H:%M"), 
                                style={'color': colors['text']})
                    ], className="d-none d-md-block text-center")
                ], width="auto", className="d-none d-md-block"),
                
                # Menu de configurações avançado
                dbc.Col([
                    dbc.ButtonGroup([
                        # Botão de tema com tooltip
                        dbc.Button(
                            html.I(className="fas fa-moon" if theme == 'light' else "fas fa-sun"),
                            id="theme-toggle-btn",
                            color="outline-secondary",
                            size="sm",
                            className="rounded-pill",
                            title="Alternar tema claro/escuro"
                        ),
                        
                        # Botão de atualização com tooltip
                        dbc.Button(
                            html.I(className="fas fa-sync-alt"),
                            id="refresh-header-btn",
                            color="outline-info",
                            size="sm",
                            className="rounded-pill",
                            title="Atualizar dados"
                        ),
                        
                        # Dropdown de configurações
                        dbc.DropdownMenu(
                            [
                                dbc.DropdownMenuItem([html.I(className="fas fa-columns me-2"), "Layout Padrão"], id="layout-default"),
                                dbc.DropdownMenuItem([html.I(className="fas fa-th-large me-2"), "Layout Compacto"], id="layout-compact"),
                                dbc.DropdownMenuItem([html.I(className="fas fa-th me-2"), "Layout Expandido"], id="layout-expanded"),
                                dbc.DropdownMenuItem(divider=True),
                                dbc.DropdownMenuItem([html.I(className="fas fa-file-export me-2"), "Exportar PDF"], id="export-pdf"),
                                dbc.DropdownMenuItem([html.I(className="fas fa-file-image me-2"), "Exportar PNG"], id="export-png"),
                                dbc.DropdownMenuItem([html.I(className="fas fa-file-csv me-2"), "Exportar Dados CSV"], id="export-csv"),
                                dbc.DropdownMenuItem(divider=True),
                                dbc.DropdownMenuItem([html.I(className="fas fa-bookmark me-2"), "Salvar Visualização"], id="save-view"),
                                dbc.DropdownMenuItem([html.I(className="fas fa-share-alt me-2"), "Compartilhar"], id="share-dashboard"),
                            ],
                            label=html.I(className="fas fa-cog"),
                            color="outline-secondary",
                            size="sm",
                            className="rounded-pill",
                            toggle_style={"fontSize": "0.875rem"},
                        ),
                    ], className="ms-auto")
                ], width="auto", className="ms-auto")
            ], className="w-100 justify-content-between align-items-center")
        ], fluid=True),
        color=colors['surface'],
        dark=theme=='dark',
        sticky="top",
        className="shadow-sm border-bottom",
        style={'borderColor': colors['border']}
    )

def create_kpi_cards(data=None, theme='light'):
    """Cria cards de KPI interativos com animações e indicadores de tendência"""
    colors = THEMES[theme]
    
    # Estilos base para os cards
    card_style = {
        'transition': 'all 0.3s ease',
        'borderRadius': '12px',
        'overflow': 'hidden',
        'border': f"1px solid {colors['border']}"
    }
    
    # Estilos para os valores dos KPIs
    kpi_value_style = {
        'fontSize': '2rem',
        'fontWeight': '700',
        'color': colors['text'],
        'transition': 'all 0.3s ease'
    }
    
    # Estilos para os títulos dos KPIs
    kpi_title_style = {
        'fontSize': '0.9rem',
        'color': colors['text_secondary'],
        'fontWeight': '600',
        'textTransform': 'uppercase',
        'letterSpacing': '0.5px'
    }
    
    if data is None or not isinstance(data, pd.DataFrame) or data.empty:
        # Retorna cards vazios com estilo moderno se não houver dados
        return dbc.Row([
            dbc.Col(dbc.Card(
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-exclamation-circle fa-2x mb-3", 
                               style={'color': colors['warning']}),
                        html.H5("Sem dados disponíveis", className="mb-2", 
                                style={'color': colors['text']}),
                        html.P("Carregue dados para visualizar os KPIs", 
                               style={'color': colors['text_secondary']})
                    ], className="text-center py-4")
                ]), 
                color=colors['surface'], 
                className="shadow-sm",
                style=card_style), 
                width=12)
        ], className="mb-4")
    
    # Calcula KPIs básicos
    total_rows = len(data)
    
    # Identifica colunas numéricas para cálculos
    numeric_cols = data.select_dtypes(include=['number']).columns
    
    # Simula dados históricos para mostrar tendências (em um app real, isso viria do banco de dados)
    # Aqui estamos simulando uma variação de -10% a +15%
    def get_trend_data(value):
        # Simula dados históricos (em um app real, isso viria do banco de dados)
        np.random.seed(int(abs(value)) % 100 if value else 42)  # Seed para consistência
        change_pct = np.random.uniform(-10, 15)  # Variação percentual entre -10% e +15%
        previous_value = value / (1 + change_pct/100)
        
        # Determina cor e ícone com base na tendência
        if change_pct > 5:
            trend_color = colors['success']
            trend_icon = "fas fa-arrow-up"
            trend_text = f"+{change_pct:.1f}%"
        elif change_pct < -5:
            trend_color = colors['danger']
            trend_icon = "fas fa-arrow-down"
            trend_text = f"{change_pct:.1f}%"
        else:
            trend_color = colors['warning']
            trend_icon = "fas fa-arrows-alt-h"
            trend_text = f"{change_pct:.1f}%"
            
        return {
            'previous_value': previous_value,
            'change_pct': change_pct,
            'trend_color': trend_color,
            'trend_icon': trend_icon,
            'trend_text': trend_text
        }
    
    kpi_cards = []
    
    # KPI 1: Total de registros com indicador de tendência
    trend_data = get_trend_data(total_rows)
    
    kpi_cards.append(
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    # Ícone e título
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-database", 
                                  style={'color': colors['primary'], 'fontSize': '1.2rem'})
                        ], className="p-2 rounded-circle", 
                           style={'backgroundColor': f"{colors['primary']}20"}),
                        html.Div([
                            html.H6("TOTAL DE REGISTROS", 
                                  style=kpi_title_style, 
                                  className="mb-0")
                        ], className="ms-2")
                    ], className="d-flex align-items-center mb-3"),
                    
                    # Valor principal e tendência
                    html.Div([
                        html.Div([
                            html.H3(f"{total_rows:,}".replace(',', '.'), 
                                   style=kpi_value_style, 
                                   className="mb-0"),
                        ]),
                        html.Div([
                            html.Span([
                                html.I(className=f"{trend_data['trend_icon']} me-1"),
                                trend_data['trend_text']
                            ], style={'color': trend_data['trend_color'], 'fontWeight': '500'})
                        ], className="ms-auto")
                    ], className="d-flex align-items-baseline justify-content-between"),
                    
                    # Barra de progresso
                    html.Div([
                        dbc.Progress(value=min(100, abs(trend_data['change_pct']) * 5), 
                                    color="success" if trend_data['change_pct'] > 0 else "danger",
                                    className="mt-2", 
                                    style={'height': '4px'})
                    ]),
                    
                    # Texto de comparação
                    html.Div([
                        html.Small(f"vs {int(trend_data['previous_value']):,}".replace(',', '.') + " anteriores", 
                                 style={'color': colors['text_secondary']})
                    ], className="mt-2")
                ]),
                color=colors['surface'],
                className="shadow-sm h-100",
                style=card_style
            ),
            width=12, sm=6, md=4, lg=3,
            className="mb-4"
        )
    )
    
    # Adiciona KPIs para colunas numéricas (até 3 colunas)
    for i, col in enumerate(numeric_cols[:3]):
        try:
            col_mean = data[col].mean()
            col_sum = data[col].sum()
            col_max = data[col].max()
            col_min = data[col].min()
            
            # Determina qual valor mostrar como principal (soma ou média)
            # Para valores muito grandes, a média pode ser mais informativa
            if abs(col_sum) > 1_000_000 and abs(col_mean) < 10_000:
                primary_value = col_mean
                primary_label = "MÉDIA"
                secondary_value = col_sum
                secondary_label = "Total"
            else:
                primary_value = col_sum
                primary_label = "TOTAL"
                secondary_value = col_mean
                secondary_label = "Média"
            
            # Formata valores com base na magnitude
            def format_value(val):
                if abs(val) >= 1_000_000:
                    return f"{val/1_000_000:.2f}M"
                elif abs(val) >= 1_000:
                    return f"{val/1_000:.1f}K"
                else:
                    return f"{val:.2f}"
                
            formatted_primary = format_value(primary_value)
            formatted_secondary = format_value(secondary_value)
            
            # Escolhe ícone com base no nome da coluna
            icon_class = "fas fa-chart-line"
            if any(term in col.lower() for term in ["valor", "preco", "price", "custo", "cost"]):
                icon_class = "fas fa-dollar-sign"
                card_accent_color = colors['success']
            elif any(term in col.lower() for term in ["quantidade", "qtd", "qty", "count", "total"]):
                icon_class = "fas fa-cubes"
                card_accent_color = colors['info']
            elif any(term in col.lower() for term in ["tempo", "time", "duration", "period"]):
                icon_class = "fas fa-clock"
                card_accent_color = colors['warning']
            else:
                card_accent_color = colors['primary']
                
            # Obtém dados de tendência
            trend_data = get_trend_data(primary_value)
            
            # Formata o título da coluna para exibição
            display_title = col.replace('_', ' ').title()
            if len(display_title) > 20:
                display_title = display_title[:18] + '...'
                
            kpi_cards.append(
                dbc.Col(
                    dbc.Card(
                        [
                            # Barra de acento colorida no topo do card
                            html.Div(className="w-100", style={
                                'height': '4px', 
                                'backgroundColor': card_accent_color,
                                'borderTopLeftRadius': '12px',
                                'borderTopRightRadius': '12px'
                            }),
                            
                            dbc.CardBody([
                                # Ícone e título
                                html.Div([
                                    html.Div([
                                        html.I(className=icon_class, 
                                              style={'color': card_accent_color, 'fontSize': '1.2rem'})
                                    ], className="p-2 rounded-circle", 
                                       style={'backgroundColor': f"{card_accent_color}20"}),
                                    html.Div([
                                        html.H6(display_title.upper(), 
                                              style=kpi_title_style, 
                                              className="mb-0",
                                              title=col)  # Tooltip com nome completo
                                    ], className="ms-2")
                                ], className="d-flex align-items-center mb-3"),
                                
                                # Valor principal e tendência
                                html.Div([
                                    html.Div([
                                        html.H3(formatted_primary, 
                                               style=kpi_value_style, 
                                               className="mb-0"),
                                        html.Small(primary_label, 
                                                  style={'color': colors['text_secondary']})
                                    ]),
                                    html.Div([
                                        html.Span([
                                            html.I(className=f"{trend_data['trend_icon']} me-1"),
                                            trend_data['trend_text']
                                        ], style={'color': trend_data['trend_color'], 'fontWeight': '500'})
                                    ], className="ms-auto d-flex align-items-center")
                                ], className="d-flex align-items-start justify-content-between"),
                                
                                # Barra de progresso
                                html.Div([
                                    dbc.Progress(value=min(100, abs(trend_data['change_pct']) * 5), 
                                                color="success" if trend_data['change_pct'] > 0 else "danger",
                                                className="mt-2", 
                                                style={'height': '4px'})
                                ]),
                                
                                # Informações adicionais
                                html.Div([
                                    html.Div([
                                        html.Small(secondary_label, className="d-block text-muted"),
                                        html.Span(formatted_secondary, style={'fontWeight': '600'})
                                    ], className="me-3"),
                                    html.Div([
                                        html.Small("Máx", className="d-block text-muted"),
                                        html.Span(format_value(col_max), style={'fontWeight': '600'})
                                    ], className="me-3"),
                                    html.Div([
                                        html.Small("Mín", className="d-block text-muted"),
                                        html.Span(format_value(col_min), style={'fontWeight': '600'})
                                    ])
                                ], className="d-flex justify-content-between mt-3 pt-2", 
                                   style={'borderTop': f"1px solid {colors['border']}"})
                            ])
                        ],
                        color=colors['surface'],
                        className="shadow-sm h-100",
                        style=card_style
                    ),
                    width=12, sm=6, md=4, lg=3,
                    className="mb-4"
                )
            )
        except Exception as e:
            print(f"Erro ao calcular KPI para coluna {col}: {e}")
    
    # Preenche com cards vazios se necessário para completar a linha
    while len(kpi_cards) < 4:
        kpi_cards.append(
            dbc.Col(width=12, sm=6, md=4, lg=3, className="mb-4 d-none d-lg-block")
        )
    
    return dbc.Row(kpi_cards, className="mb-4")

def create_filters_sidebar(data=None, theme='light'):
    """Cria barra lateral de filtros moderna e interativa"""
    colors = THEMES[theme]
    
    # Estilos para os componentes do sidebar
    sidebar_style = {
        'backgroundColor': colors['surface'],
        'borderRadius': '12px',
        'border': f"1px solid {colors['border']}",
        'transition': 'all 0.3s ease',
        'overflow': 'hidden'
    }
    
    # Estilos para os títulos dos filtros
    filter_title_style = {
        'fontSize': '0.9rem',
        'fontWeight': '600',
        'color': colors['text'],
        'textTransform': 'uppercase',
        'letterSpacing': '0.5px'
    }
    
    # Estilos para os grupos de filtros
    filter_group_style = {
        'padding': '15px',
        'marginBottom': '15px',
        'borderRadius': '8px',
        'backgroundColor': f"{colors['background']}50",
        'border': f"1px solid {colors['border']}"
    }
    
    if data is None or not isinstance(data, pd.DataFrame) or data.empty:
        return dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className="fas fa-filter me-2", style={'color': colors['primary']}),
                    html.Span("Filtros Avançados", style={'fontWeight': '600'})
                ], className="d-flex align-items-center"),
                dbc.Button(
                    html.I(className="fas fa-chevron-down"),
                    id="filters-collapse-btn",
                    color="link",
                    size="sm",
                    className="ms-auto p-0"
                )
            ], className="d-flex align-items-center", 
               style={'borderBottom': f"1px solid {colors['border']}"}),
            dbc.Collapse([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-info-circle fa-2x mb-3", 
                               style={'color': colors['info']}),
                        html.P("Carregue dados para visualizar os filtros disponíveis", 
                              className="mb-0",
                              style={'color': colors['text_secondary']})
                    ], className="text-center py-4")
                ])
            ], id="filters-collapse", is_open=True)
        ], className="mb-4 shadow-sm", style=sidebar_style)
    
    # Detectar colunas para filtros
    categorical_cols = data.select_dtypes(include=['object', 'category']).columns.tolist()
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    date_cols = data.select_dtypes(include=['datetime64']).columns.tolist()
    
    filters_content = []
    
    # Contador de filtros disponíveis
    total_filters = len(date_cols[:1]) + len(categorical_cols[:3]) + len(numeric_cols[:3])
    
    filters_content.append(
        html.Div([
            html.Span(f"{total_filters}", 
                     className="badge rounded-pill bg-primary me-2"),
            html.Span("filtros disponíveis", style={'color': colors['text_secondary']})
        ], className="mb-3 mt-2")
    )
    
    # Filtro de data
    if date_cols:
        date_filters = []
        for i, col in enumerate(date_cols[:1]):  # Limita a 1 filtro de data
            try:
                min_date = data[col].min()
                max_date = data[col].max()
                
                if isinstance(min_date, pd.Timestamp) and isinstance(max_date, pd.Timestamp):
                    date_filter = html.Div([
                        html.Label(col.replace('_', ' ').title(), 
                                 className="d-block mb-2",
                                 style={'fontWeight': '500', 'color': colors['text']}),
                        dcc.DatePickerRange(
                            id=f"date-filter-{i}",
                            min_date_allowed=min_date.date(),
                            max_date_allowed=max_date.date(),
                            start_date=min_date.date(),
                            end_date=max_date.date(),
                            display_format="DD/MM/YYYY",
                            className="w-100 mb-2",
                            style={'zIndex': '1001'}
                        )
                    ], className="mb-3")
                    date_filters.append(date_filter)
            except Exception as e:
                print(f"Erro ao criar filtro de data para {col}: {e}")
        
        if date_filters:
            filters_content.append(html.Div([
                html.Div([
                    html.I(className="fas fa-calendar-alt me-2", 
                          style={'color': colors['primary']}),
                    html.Span("PERÍODO", style=filter_title_style)
                ], className="d-flex align-items-center mb-3"),
                html.Div(date_filters)
            ], style=filter_group_style))
    
    # Filtros categóricos
    if categorical_cols:
        cat_filters = []
        for i, col in enumerate(categorical_cols[:3]):  # Máximo 3 filtros categóricos
            try:
                unique_values = data[col].dropna().unique()[:20]  # Máximo 20 valores
                options = [{'label': str(val), 'value': str(val)} for val in sorted(unique_values)]
                
                cat_filter = html.Div([
                    html.Label(col.replace('_', ' ').title(), 
                             className="d-block mb-2",
                             style={'fontWeight': '500', 'color': colors['text']}),
                    dcc.Dropdown(
                        id=f"categorical-filter-{i}",
                        options=options,
                        multi=True,
                        placeholder=f"Selecione valores...",
                        className="mb-2",
                        style={
                            'borderRadius': '6px',
                            'border': f"1px solid {colors['border']}"
                        }
                    )
                ], className="mb-3")
                cat_filters.append(cat_filter)
            except Exception as e:
                print(f"Erro ao criar filtro categórico para {col}: {e}")
        
        if cat_filters:
            filters_content.append(html.Div([
                html.Div([
                    html.I(className="fas fa-tags me-2", 
                          style={'color': colors['info']}),
                    html.Span("CATEGORIAS", style=filter_title_style)
                ], className="d-flex align-items-center mb-3"),
                html.Div(cat_filters)
            ], style=filter_group_style))
    
    # Filtros numéricos (range sliders)
    if numeric_cols:
        num_filters = []
        for i, col in enumerate(numeric_cols[:3]):  # Máximo 3 filtros numéricos
            try:
                min_val = float(data[col].min())
                max_val = float(data[col].max())
                step = (max_val - min_val) / 100
                
                # Formata os valores para exibição
                def format_number(val):
                    if abs(val) >= 1_000_000:
                        return f"{val/1_000_000:.1f}M"
                    elif abs(val) >= 1_000:
                        return f"{val/1_000:.1f}K"
                    else:
                        return f"{val:.1f}"
                
                # Cria marcas para o slider
                marks = {
                    min_val: {'label': format_number(min_val), 'style': {'color': colors['text_secondary']}},
                    max_val: {'label': format_number(max_val), 'style': {'color': colors['text_secondary']}}
                }
                
                # Adiciona marca intermediária
                mid_val = min_val + (max_val - min_val) / 2
                marks[mid_val] = {'label': format_number(mid_val), 'style': {'color': colors['text_secondary']}}
                
                num_filter = html.Div([
                    html.Label(col.replace('_', ' ').title(), 
                             className="d-block mb-2",
                             style={'fontWeight': '500', 'color': colors['text']}),
                    html.Div([
                        html.Div(id=f"num-filter-{i}-display", 
                               children=f"{format_number(min_val)} - {format_number(max_val)}",
                               className="text-center mb-2",
                               style={'color': colors['primary'], 'fontWeight': '600'})
                    ]),
                    dcc.RangeSlider(
                        id=f"numeric-filter-{i}",
                        min=min_val,
                        max=max_val,
                        step=step,
                        marks=marks,
                        value=[min_val, max_val],
                        className="mb-3",
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], className="mb-3")
                num_filters.append(num_filter)
            except Exception as e:
                print(f"Erro ao criar filtro numérico para {col}: {e}")
        
        if num_filters:
            filters_content.append(html.Div([
                html.Div([
                    html.I(className="fas fa-sliders-h me-2", 
                          style={'color': colors['warning']}),
                    html.Span("VALORES", style=filter_title_style)
                ], className="d-flex align-items-center mb-3"),
                html.Div(num_filters)
            ], style=filter_group_style))
    
    # Botões de ação com ícones e efeitos visuais
    filters_content.append(
        html.Div([
            dbc.Button([
                html.I(className="fas fa-filter me-2"),
                "Aplicar Filtros"
            ], id="apply-filters-btn", color="primary", className="w-100 mb-2"),
            dbc.Button([
                html.I(className="fas fa-undo me-2"),
                "Limpar Filtros"
            ], id="clear-filters-btn", color="outline-secondary", className="w-100")
        ], className="mt-3 mb-2")
    )
    
    # Adiciona dica de uso
    filters_content.append(
        html.Div([
            html.I(className="fas fa-lightbulb me-2", style={'color': colors['warning']}),
            html.Small("Dica: Combine múltiplos filtros para análises mais precisas", 
                     style={'color': colors['text_secondary']})
        ], className="mt-3 small")
    )
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-filter me-2", style={'color': colors['primary']}),
                html.Span("Filtros Avançados", style={'fontWeight': '600'})
            ], className="d-flex align-items-center"),
            dbc.Button(
                html.I(className="fas fa-chevron-down", id="filters-chevron"),
                id="filters-collapse-btn",
                color="link",
                size="sm",
                className="ms-auto p-0"
            )
        ], className="d-flex align-items-center", 
           style={'borderBottom': f"1px solid {colors['border']}"}),
        dbc.Collapse([
            dbc.CardBody(filters_content)
        ], id="filters-collapse", is_open=True)
    ], className="mb-4 shadow-sm", style=sidebar_style)

def create_chart_card(chart_id, title, chart_type='bar', theme='light', data=None):
    """Cria card de gráfico moderno com controles avançados e interatividade"""
    colors = THEMES[theme]
    
    # Estilos para o card
    card_style = {
        'backgroundColor': colors['surface'],
        'borderRadius': '12px',
        'overflow': 'hidden',
        'border': f"1px solid {colors['border']}",
        'transition': 'all 0.3s ease',
        'height': '100%'
    }
    
    # Estilos para o cabeçalho
    header_style = {
        'borderBottom': f"1px solid {colors['border']}",
        'padding': '12px 16px'
    }
    
    # Determinar ícone baseado no tipo de gráfico
    chart_icon = {
        'bar': 'fas fa-chart-bar',
        'line': 'fas fa-chart-line',
        'pie': 'fas fa-chart-pie',
        'scatter': 'fas fa-braille',
        'area': 'fas fa-chart-area',
        'heatmap': 'fas fa-th',
        'histogram': 'fas fa-stream'
    }.get(chart_type, 'fas fa-chart-bar')
    
    # Determinar cor de acento baseada no tipo de gráfico
    chart_color = {
        'bar': colors['primary'],
        'line': colors['info'],
        'pie': colors['success'],
        'scatter': colors['warning'],
        'area': colors['info'],
        'heatmap': colors['danger'],
        'histogram': colors['secondary']
    }.get(chart_type, colors['primary'])
    
    # Criar gráfico baseado nos dados
    fig = create_sample_chart(chart_type, data, theme)
    
    return dbc.Col([
        dbc.Card([
            # Barra de acento colorida no topo do card
            html.Div(className="w-100", style={
                'height': '4px', 
                'backgroundColor': chart_color,
                'borderTopLeftRadius': '12px',
                'borderTopRightRadius': '12px'
            }),
            
            # Cabeçalho com título e controles
            dbc.CardHeader([
                html.Div([
                    html.Div([
                        html.I(className=f"{chart_icon} me-2", 
                              style={'color': chart_color}),
                        html.Span(title, className="fw-bold", style={'color': colors['text']})
                    ], className="d-flex align-items-center"),
                    
                    # Indicador de atualização
                    html.Div([
                        html.Small("Atualizado: ", className="me-1", 
                                 style={'color': colors['text_secondary']}),
                        html.Small(datetime.now().strftime("%H:%M"), 
                                 style={'color': colors['text']})
                    ], className="d-none d-md-block ms-3 small")
                ], className="d-flex align-items-center"),
                
                # Botões de controle
                dbc.ButtonGroup([
                    # Botão de tela cheia
                    dbc.Button(
                        html.I(className="fas fa-expand"),
                        id=f"fullscreen-{chart_id}",
                        color="outline-secondary",
                        size="sm",
                        className="rounded-pill",
                        title="Expandir para tela cheia"
                    ),
                    
                    # Botão de download
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-image me-2"), "PNG"], id=f"download-png-{chart_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-pdf me-2"), "PDF"], id=f"download-pdf-{chart_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-csv me-2"), "CSV"], id=f"download-csv-{chart_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-excel me-2"), "Excel"], id=f"download-excel-{chart_id}"),
                        ],
                        label=html.I(className="fas fa-download"),
                        color="outline-primary",
                        size="sm",
                        className="rounded-pill",
                        toggle_style={"fontSize": "0.875rem"},
                    ),
                    
                    # Botão de configuração
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem([html.I(className="fas fa-chart-bar me-2"), "Gráfico de Barras"], id=f"chart-type-bar-{chart_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-chart-line me-2"), "Gráfico de Linha"], id=f"chart-type-line-{chart_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-chart-pie me-2"), "Gráfico de Pizza"], id=f"chart-type-pie-{chart_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-braille me-2"), "Gráfico de Dispersão"], id=f"chart-type-scatter-{chart_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-chart-area me-2"), "Gráfico de Área"], id=f"chart-type-area-{chart_id}"),
                            dbc.DropdownMenuItem(divider=True),
                            dbc.DropdownMenuItem([html.I(className="fas fa-cog me-2"), "Configurações Avançadas"], id=f"chart-config-{chart_id}"),
                        ],
                        label=html.I(className="fas fa-cog"),
                        color="outline-secondary",
                        size="sm",
                        className="rounded-pill",
                        toggle_style={"fontSize": "0.875rem"},
                    )
                ], size="sm", className="ms-auto")
            ], className="d-flex justify-content-between align-items-center", style=header_style),
            
            # Corpo do card com o gráfico
            dbc.CardBody([
                # Área de loading para o gráfico
                dbc.Spinner(
                    dcc.Graph(
                        id=f"chart-{chart_id}",
                        figure=fig,
                        config={
                            'displayModeBar': 'hover',
                            'responsive': True,
                            'toImageButtonOptions': {
                                'format': 'png',
                                'filename': f'{title}_{chart_type}',
                                'height': 800,
                                'width': 1200,
                                'scale': 2
                            },
                            'modeBarButtonsToRemove': ['select2d', 'lasso2d']
                        },
                        className="h-100 w-100",
                        style={
                            'minHeight': '300px',
                            'transition': 'all 0.3s ease'
                        }
                    ),
                    color=chart_color,
                    type="border",
                    fullscreen=False,
                ),
                
                # Rodapé com informações adicionais
                html.Div([
                    html.Small([
                        html.I(className="fas fa-info-circle me-1", style={'color': colors['info']}),
                        "Clique e arraste para zoom. Clique duplo para resetar."
                    ], style={'color': colors['text_secondary']})
                ], className="mt-3 text-center small d-none d-md-block")
            ], className="p-3")
        ], className="shadow-sm", style=card_style)
    ], lg=6, md=12, className="mb-4")

def create_data_table_card(table_id, title, theme='light', data=None):
    """Cria card de tabela moderna com pesquisa avançada, paginação e exportação"""
    colors = THEMES[theme]
    
    # Estilos para o card
    card_style = {
        'backgroundColor': colors['surface'],
        'borderRadius': '12px',
        'overflow': 'hidden',
        'border': f"1px solid {colors['border']}",
        'transition': 'all 0.3s ease',
        'height': '100%'
    }
    
    # Estilos para o cabeçalho
    header_style = {
        'borderBottom': f"1px solid {colors['border']}",
        'padding': '12px 16px'
    }
    
    # Preparar dados da tabela
    if data is not None and not data.empty:
        # Formatar dados para exibição mais amigável
        formatted_data = data.copy()
        
        # Detectar e formatar colunas numéricas
        for col in formatted_data.select_dtypes(include=['float64', 'int64']).columns:
            # Verificar se parece com valores monetários (grandes números)
            if formatted_data[col].abs().mean() > 1000:
                formatted_data[col] = formatted_data[col].apply(
                    lambda x: f"R$ {x:,.2f}" if pd.notna(x) else ""
                )
            # Números decimais comuns
            elif formatted_data[col].dtype == 'float64':
                formatted_data[col] = formatted_data[col].apply(
                    lambda x: f"{x:,.2f}" if pd.notna(x) else ""
                )
        
        # Detectar e formatar colunas de data
        for col in formatted_data.select_dtypes(include=['datetime64']).columns:
            formatted_data[col] = formatted_data[col].dt.strftime('%d/%m/%Y')
        
        # Definir colunas e tipos para a tabela
        table_columns = []
        for i in formatted_data.columns:
            col_type = str(data[i].dtype)
            if 'int' in col_type or 'float' in col_type:
                table_columns.append({"name": i, "id": i, "type": "numeric"})
            elif 'datetime' in col_type or 'date' in col_type:
                table_columns.append({"name": i, "id": i, "type": "datetime"})
            else:
                table_columns.append({"name": i, "id": i, "type": "text"})
        
        # Limitar a 100 linhas para performance
        table_data = formatted_data.head(100).to_dict('records')
        total_rows = len(data)
        display_rows = min(100, total_rows)
    else:
        table_columns = []
        table_data = []
        total_rows = 0
        display_rows = 0
    
    return dbc.Col([
        dbc.Card([
            # Barra de acento colorida no topo do card
            html.Div(className="w-100", style={
                'height': '4px', 
                'backgroundColor': colors['info'],
                'borderTopLeftRadius': '12px',
                'borderTopRightRadius': '12px'
            }),
            
            # Cabeçalho com título e controles
            dbc.CardHeader([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-table me-2", style={'color': colors['info']}),
                        html.Span(title, className="fw-bold", style={'color': colors['text']})
                    ], className="d-flex align-items-center"),
                    
                    # Contador de registros
                    html.Div([
                        html.Small("Registros: ", className="me-1", style={'color': colors['text_secondary']}),
                        html.Small(f"{display_rows} de {total_rows}", 
                                  className="badge rounded-pill", 
                                  style={
                                      'backgroundColor': f"{colors['info']}20",
                                      'color': colors['info'],
                                      'fontWeight': 'normal'
                                  })
                    ], className="d-none d-md-flex ms-3 align-items-center" if total_rows > 0 else "d-none")
                ], className="d-flex align-items-center"),
                
                # Botões de controle
                dbc.ButtonGroup([
                    # Campo de pesquisa
                    dbc.Input(
                        id=f"search-input-{table_id}",
                        placeholder="Pesquisar...",
                        size="sm",
                        className="me-2 rounded-pill",
                        style={
                            'width': '150px',
                            'transition': 'width 0.3s',
                            'backgroundColor': colors['surface'],
                            'border': f"1px solid {colors['border']}",
                            'color': colors['text']
                        }
                    ),
                    
                    # Botão de pesquisa
                    dbc.Button(
                        html.I(className="fas fa-search"),
                        id=f"search-{table_id}",
                        color="outline-secondary",
                        size="sm",
                        className="rounded-pill",
                        title="Pesquisar"
                    ),
                    
                    # Menu de exportação
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-csv me-2"), "CSV"], id=f"export-csv-{table_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-excel me-2"), "Excel"], id=f"export-excel-{table_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-file-pdf me-2"), "PDF"], id=f"export-pdf-{table_id}"),
                            dbc.DropdownMenuItem(divider=True),
                            dbc.DropdownMenuItem([html.I(className="fas fa-print me-2"), "Imprimir"], id=f"print-{table_id}"),
                        ],
                        label=html.I(className="fas fa-download"),
                        color="outline-primary",
                        size="sm",
                        className="rounded-pill ms-2",
                        toggle_style={"fontSize": "0.875rem"},
                    ),
                    # Botão de configuração
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem([html.I(className="fas fa-sort-alpha-down me-2"), "Ordenar A-Z"], id=f"sort-asc-{table_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-sort-alpha-up me-2"), "Ordenar Z-A"], id=f"sort-desc-{table_id}"),
                            dbc.DropdownMenuItem(divider=True),
                            dbc.DropdownMenuItem([html.I(className="fas fa-filter me-2"), "Mostrar Filtros"], id=f"toggle-filters-{table_id}"),
                            dbc.DropdownMenuItem([html.I(className="fas fa-cog me-2"), "Configurações"], id=f"table-config-{table_id}"),
                        ],
                        label=html.I(className="fas fa-cog"),
                        color="outline-secondary",
                        size="sm",
                        className="rounded-pill ms-2",
                        toggle_style={"fontSize": "0.875rem"},
                    )
                ], size="sm", className="ms-auto")
            ], className="d-flex justify-content-between align-items-center", style=header_style),
            
            # Corpo do card com a tabela
            dbc.CardBody([
                # Área de loading para a tabela
                dbc.Spinner(
                    html.Div([
                        dash_table.DataTable(
                            id=f"table-{table_id}",
                            columns=table_columns,
                            data=table_data,
                            page_size=15,
                            style_table={
                                'overflowX': 'auto',
                                'minWidth': '100%',
                                'borderRadius': '8px',
                                'overflow': 'hidden',
                                'border': f"1px solid {colors['border']}",
                            },
                            style_cell={
                                'textAlign': 'left',
                                'padding': '12px 15px',
                                'backgroundColor': colors['surface'],
                                'color': colors['text'],
                                'fontFamily': '"Segoe UI", Arial, sans-serif',
                                'fontSize': '14px',
                                'overflow': 'hidden',
                                'textOverflow': 'ellipsis',
                                'maxWidth': 0,
                                'height': 'auto',
                                'whiteSpace': 'normal',
                                'lineHeight': '1.5',
                            },
                            style_header={
                                'backgroundColor': colors['surface'],
                                'color': colors['text'],
                                'fontWeight': 'bold',
                                'textAlign': 'left',
                                'padding': '15px',
                                'borderBottom': f"2px solid {colors['info']}",
                            },
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': colors['surface'],
                                    'opacity': '0.8'
                                },
                                {
                                    'if': {'state': 'selected'},
                                    'backgroundColor': f"{colors['info']}20",
                                    'border': f"1px solid {colors['info']}",
                                },
                                # Estilo para colunas numéricas
                                *[{
                                    'if': {'column_type': 'numeric'},
                                    'textAlign': 'right'
                                }],
                                # Estilo para valores negativos
                                *([{                                    'if': {
                                        'filter_query': f'{{{col}}} < 0',
                                        'column_id': col
                                    },
                                    'color': colors['danger'],
                                    'fontWeight': 'bold'
                                } for col in ([] if data is None or data.empty else data.select_dtypes(include=['float64', 'int64']).columns)])
                            ],
                            page_action='native',
                            sort_action='native',
                            filter_action='native',
                            export_format='xlsx',
                            export_headers='display',
                            row_selectable='multi',
                            selected_rows=[],
                            style_as_list_view=True,
                            style_filter={
                                'backgroundColor': colors['surface'],
                                'color': colors['text'],
                                'padding': '8px',
                                'borderRadius': '4px',
                            },
                            style_pagination={
                                'borderTop': f"1px solid {colors['border']}",
                                'padding': '10px 0',
                            },
                            page_current=0,
                            css=[
                                {
                                    'selector': '.dash-spreadsheet-menu',
                                    'rule': f'background-color: {colors["surface"]} !important; color: {colors["text"]} !important;'
                                },
                                {
                                    'selector': '.dash-spreadsheet-menu .bp3-button',
                                    'rule': f'background-color: {colors["surface"]} !important; color: {colors["text"]} !important;'
                                },
                                {
                                    'selector': '.dash-filter--case',
                                    'rule': f'display: none !important;'
                                }
                            ]
                        )
                    ], style={'overflowX': 'auto'}),
                    color=colors['info'],
                    type="border",
                    fullscreen=False,
                ),
                
                # Rodapé com informações adicionais
                html.Div([
                    html.Div([
                        html.Small([
                            html.I(className="fas fa-info-circle me-1", style={'color': colors['info']}),
                            "Clique nos cabeçalhos para ordenar. Use os filtros para refinar os dados."
                        ], style={'color': colors['text_secondary']})
                    ], className="col-12 col-md-8"),
                    html.Div([
                        html.Small([
                            html.Span("Página: ", style={'color': colors['text_secondary']}),
                            html.Span("1", id=f"table-current-page-{table_id}", style={'fontWeight': 'bold', 'color': colors['text']}),
                            html.Span(" de ", style={'color': colors['text_secondary']}),
                            html.Span(str(max(1, (total_rows // 15) + (1 if total_rows % 15 > 0 else 0))), 
                                     id=f"table-total-pages-{table_id}", 
                                     style={'color': colors['text']})
                        ])
                    ], className="col-12 col-md-4 text-md-end mt-2 mt-md-0")
                ], className="d-flex flex-wrap justify-content-between align-items-center mt-3 small")
            ], className="p-3")
        ], className="shadow-sm mb-4", style=card_style)
    ], lg=12, className="mb-4")

def create_sample_chart(chart_type, data=None, theme='light', animation=True, advanced_options=None):
    """Cria gráficos modernos e interativos baseados nos dados disponíveis
    
    Parâmetros:
    - chart_type: Tipo de gráfico (line, bar, area, scatter, heatmap, histogram, pie, box, violin)
    - data: DataFrame com os dados para visualização
    - theme: Tema de cores (light, dark)
    - animation: Se True, adiciona animações aos gráficos
    - advanced_options: Dicionário com opções avançadas de configuração
    """
    colors = THEMES[theme]
    
    # Configurações padrão
    default_options = {
        'show_grid': True,
        'show_legend': True,
        'template': 'plotly_white' if theme == 'light' else 'plotly_dark',
        'colorscale': 'Viridis',
        'marker_size': 8,
        'line_width': 2,
        'opacity': 0.8,
        'title_font_size': 18,
        'axis_font_size': 14,
        'legend_font_size': 12,
        'show_trend': True,
        'smooth_line': True,
        'bar_mode': 'group',
        'show_values': False
    }
    
    # Mesclar com opções avançadas, se fornecidas
    options = default_options.copy()
    if advanced_options:
        options.update(advanced_options)
    
    # Definir paleta de cores personalizada baseada no tema
    custom_colors = [
        colors['primary'], colors['secondary'], colors['success'], 
        colors['info'], colors['warning'], colors['danger']
    ]
    
    # Gerar dados de exemplo se não houver dados reais
    if data is None or data.empty:
        # Dados de exemplo mais interessantes
        if chart_type in ['line', 'area']:
            # Gerar série temporal com tendência e sazonalidade
            dates = pd.date_range('2024-01-01', periods=90, freq='D')
            trend = np.linspace(0, 15, 90)  # Tendência crescente
            seasonality = 5 * np.sin(np.linspace(0, 6*np.pi, 90))  # Padrão sazonal
            noise = np.random.normal(0, 1, 90)  # Ruído aleatório
            values = trend + seasonality + noise
            
            # Criar DataFrame com múltiplas séries
            df = pd.DataFrame({
                'Data': dates,
                'Série A': values,
                'Série B': values * 0.7 + np.random.normal(0, 1, 90) + 5,
                'Série C': values * 0.5 + np.random.normal(0, 1, 90) + 10
            })
            
            if chart_type == 'line':
                fig = px.line(df, x='Data', y=['Série A', 'Série B', 'Série C'], 
                              title="Tendência Temporal com Sazonalidade",
                              color_discrete_sequence=custom_colors,
                              line_shape='spline' if options['smooth_line'] else 'linear')
                
                # Adicionar linha de tendência
                if options['show_trend']:
                    for col in ['Série A', 'Série B', 'Série C']:
                        fig.add_traces(
                            px.scatter(x=df['Data'], y=df[col], trendline="lowess").data[1]
                        )
            else:  # area
                fig = px.area(df, x='Data', y=['Série A', 'Série B', 'Série C'], 
                              title="Performance ao Longo do Tempo",
                              color_discrete_sequence=custom_colors)
                
        elif chart_type == 'bar':
            # Dados de barras mais interessantes com categorias significativas
            categories = ['Vendas', 'Marketing', 'Operações', 'Financeiro', 'RH', 'TI']
            values_2023 = np.random.randint(50, 150, 6)
            values_2024 = values_2023 * (1 + np.random.uniform(-0.3, 0.5, 6))  # Variação ano a ano
            
            df = pd.DataFrame({
                'Departamento': categories * 2,
                'Valor': np.concatenate([values_2023, values_2024]),
                'Ano': ['2023'] * 6 + ['2024'] * 6
            })
            
            fig = px.bar(df, x='Departamento', y='Valor', color='Ano', 
                         title="Comparativo por Departamento",
                         barmode=options['bar_mode'],
                         color_discrete_sequence=custom_colors)
            
            # Adicionar valores nas barras
            if options['show_values']:
                fig.update_traces(texttemplate='%{y:.0f}', textposition='outside')
                
        elif chart_type == 'heatmap':
            # Matriz de correlação mais interessante
            labels = ['Vendas', 'Lucro', 'Custo', 'Volume', 'Satisfação', 'Retenção']
            n = len(labels)
            
            # Criar matriz de correlação com padrões realistas
            base = np.eye(n)  # Diagonal principal = 1
            for i in range(n):
                for j in range(i+1, n):
                    # Correlações mais realistas entre -0.8 e 0.9
                    val = np.random.uniform(-0.8, 0.9)
                    base[i, j] = val
                    base[j, i] = val  # Matriz simétrica
            
            fig = px.imshow(base, x=labels, y=labels, 
                             title="Matriz de Correlação entre Métricas",
                             color_continuous_scale=options['colorscale'],
                             zmin=-1, zmax=1)
            
            # Adicionar valores na matriz
            if options['show_values']:
                fig.update_traces(text=[[f"{val:.2f}" for val in row] for row in base],
                                 texttemplate="%{text}")
                
        elif chart_type == 'scatter':
            # Dados de dispersão com clusters
            n_points = 100
            
            # Criar três clusters distintos
            cluster1_x = np.random.normal(5, 1, n_points // 3)
            cluster1_y = np.random.normal(5, 1, n_points // 3)
            
            cluster2_x = np.random.normal(10, 1.2, n_points // 3)
            cluster2_y = np.random.normal(10, 1.2, n_points // 3)
            
            cluster3_x = np.random.normal(7.5, 1.5, n_points // 3)
            cluster3_y = np.random.normal(15, 1.5, n_points // 3)
            
            df = pd.DataFrame({
                'x': np.concatenate([cluster1_x, cluster2_x, cluster3_x]),
                'y': np.concatenate([cluster1_y, cluster2_y, cluster3_y]),
                'cluster': ['Grupo A'] * (n_points // 3) + ['Grupo B'] * (n_points // 3) + ['Grupo C'] * (n_points // 3),
                'tamanho': np.random.randint(10, 50, n_points)
            })
            
            fig = px.scatter(df, x='x', y='y', color='cluster', size='tamanho',
                             title="Análise de Clusters",
                             color_discrete_sequence=custom_colors,
                             opacity=options['opacity'])
            
        elif chart_type == 'histogram':
            # Histograma com distribuição interessante
            # Mistura de duas distribuições normais
            data1 = np.random.normal(20, 5, 300)  # Média 20, desvio 5
            data2 = np.random.normal(35, 8, 200)  # Média 35, desvio 8
            all_data = np.concatenate([data1, data2])
            
            fig = px.histogram(all_data, title="Distribuição Bimodal",
                               color_discrete_sequence=[colors['primary']],
                               opacity=options['opacity'],
                               nbins=30)
            
        elif chart_type == 'pie':
            # Gráfico de pizza com dados de mercado
            labels = ['Produto A', 'Produto B', 'Produto C', 'Produto D', 'Outros']
            values = [38, 27, 18, 10, 7]  # Porcentagens
            
            fig = px.pie(values=values, names=labels, 
                         title="Participação de Mercado",
                         color_discrete_sequence=custom_colors,
                         hole=0.4)  # Transformar em donut chart
            
            # Adicionar valores percentuais
            if options['show_values']:
                fig.update_traces(textinfo='percent+label')
                
        elif chart_type == 'box':
            # Box plot com múltiplas categorias
            categories = ['Grupo A', 'Grupo B', 'Grupo C', 'Grupo D']
            data_points = []
            cat_labels = []
            
            # Gerar dados com diferentes distribuições para cada categoria
            for i, cat in enumerate(categories):
                # Cada categoria tem uma distribuição diferente
                mean_val = 50 + i * 10
                std_val = 5 + i * 2
                points = np.random.normal(mean_val, std_val, 50)
                data_points.extend(points)
                cat_labels.extend([cat] * 50)
            
            df = pd.DataFrame({
                'Categoria': cat_labels,
                'Valor': data_points
            })
            
            fig = px.box(df, x='Categoria', y='Valor', 
                         title="Distribuição por Grupos",
                         color='Categoria',
                         color_discrete_sequence=custom_colors)
            
        else:  # Fallback para outros tipos não especificados
            # Gráfico de linha como padrão
            dates = pd.date_range('2024-01-01', periods=60, freq='D')
            values = np.random.randn(60).cumsum() + 100
            df = pd.DataFrame({'date': dates, 'value': values})
            fig = px.line(df, x='date', y='value', 
                          title="Visualização de Dados",
                          color_discrete_sequence=[colors['primary']])
    else:
        # Usar dados reais
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        date_cols = [col for col in data.columns if pd.api.types.is_datetime64_any_dtype(data[col]) or 
                    ('date' in col.lower() or 'data' in col.lower() or 'dia' in col.lower())]  # Detectar colunas de data
        
        # Selecionar a primeira coluna de data, se existir
        date_col = date_cols[0] if date_cols else None
        
        # Selecionar x_col baseado na disponibilidade de colunas de data
        if date_col:
            x_col = date_col
        elif len(data.columns) > 0:
            x_col = data.columns[0]  # Usar primeira coluna como fallback
        else:
            # Caso extremo: não há colunas
            return px.scatter(title="Sem dados disponíveis")
        
        if len(numeric_cols) >= 1:
            # Selecionar até 3 colunas numéricas para visualização
            y_cols = numeric_cols[:3]
            
            if chart_type == 'line':
                # Gráfico de linha com múltiplas séries
                fig = px.line(data, x=x_col, y=y_cols, 
                              title="Tendência dos Dados",
                              color_discrete_sequence=custom_colors,
                              line_shape='spline' if options['smooth_line'] else 'linear')
                
                # Adicionar linha de tendência
                if options['show_trend'] and len(data) > 5:
                    for col in y_cols:
                        try:
                            fig.add_traces(
                                px.scatter(x=data[x_col], y=data[col], trendline="lowess").data[1]
                            )
                        except Exception:
                            # Fallback se a linha de tendência falhar
                            pass
                            
            elif chart_type == 'bar':
                # Limitar a 15 registros para melhor visualização
                sample_data = data.head(15) if len(data) > 15 else data
                
                # Verificar se há uma coluna categórica para agrupar
                cat_cols = data.select_dtypes(include=['object', 'category']).columns
                if len(cat_cols) > 0 and len(y_cols) > 0:
                    # Usar a primeira coluna categórica para agrupar
                    color_col = cat_cols[0]
                    fig = px.bar(sample_data, x=x_col, y=y_cols[0], color=color_col,
                                title="Distribuição por Categoria",
                                barmode=options['bar_mode'],
                                color_discrete_sequence=custom_colors)
                else:
                    # Sem coluna categórica, usar apenas barras simples
                    fig = px.bar(sample_data, x=x_col, y=y_cols[0],
                                title="Top 15 Registros",
                                color_discrete_sequence=[colors['primary']])
                
                # Adicionar valores nas barras
                if options['show_values']:
                    fig.update_traces(texttemplate='%{y:.1f}', textposition='outside')
                    
            elif chart_type == 'heatmap':
                # Matriz de correlação entre variáveis numéricas
                if len(numeric_cols) >= 2:
                    # Calcular correlação apenas para colunas numéricas
                    corr_matrix = data[numeric_cols].corr().round(2)
                    
                    # Limitar a 10x10 para melhor visualização
                    if len(corr_matrix) > 10:
                        corr_matrix = corr_matrix.iloc[:10, :10]
                    
                    fig = px.imshow(corr_matrix,
                                  title="Matriz de Correlação",
                                  color_continuous_scale=options['colorscale'],
                                  zmin=-1, zmax=1)
                    
                    # Adicionar valores na matriz
                    if options['show_values']:
                        fig.update_traces(text=[[f"{val:.2f}" for val in row] for row in corr_matrix.values],
                                         texttemplate="%{text}")
                else:
                    # Fallback se não houver colunas numéricas suficientes
                    fig = px.scatter(title="Dados insuficientes para matriz de correlação")
                    
            elif chart_type == 'scatter':
                # Gráfico de dispersão entre duas variáveis numéricas
                if len(numeric_cols) >= 2:
                    # Limitar a 200 pontos para performance
                    sample_data = data.sample(min(200, len(data))) if len(data) > 200 else data
                    
                    # Verificar se há uma coluna categórica para colorir
                    cat_cols = data.select_dtypes(include=['object', 'category']).columns
                    if len(cat_cols) > 0:
                        color_col = cat_cols[0]
                        fig = px.scatter(sample_data, x=numeric_cols[0], y=numeric_cols[1],
                                       color=color_col, size=numeric_cols[0] if len(numeric_cols) > 0 else None,
                                       title="Correlação entre Variáveis",
                                       color_discrete_sequence=custom_colors,
                                       opacity=options['opacity'])
                    else:
                        # Sem coluna categórica
                        fig = px.scatter(sample_data, x=numeric_cols[0], y=numeric_cols[1],
                                       title="Correlação entre Variáveis",
                                       color_discrete_sequence=[colors['primary']],
                                       opacity=options['opacity'])
                    
                    # Adicionar linha de tendência
                    if options['show_trend']:
                        fig.update_layout(showlegend=True)
                        fig.add_traces(
                            px.scatter(x=sample_data[numeric_cols[0]], 
                                      y=sample_data[numeric_cols[1]], 
                                      trendline="ols").data[1]
                        )
                else:
                    # Fallback se não houver colunas numéricas suficientes
                    fig = px.scatter(title="Dados insuficientes para gráfico de dispersão")
                    
            elif chart_type == 'histogram':
                # Histograma da primeira coluna numérica
                if len(numeric_cols) > 0:
                    # Verificar se há uma coluna categórica para colorir
                    cat_cols = data.select_dtypes(include=['object', 'category']).columns
                    if len(cat_cols) > 0:
                        color_col = cat_cols[0]
                        fig = px.histogram(data, x=numeric_cols[0], color=color_col,
                                         title=f"Distribuição de {numeric_cols[0]}",
                                         color_discrete_sequence=custom_colors,
                                         opacity=options['opacity'],
                                         nbins=30)
                    else:
                        # Sem coluna categórica
                        fig = px.histogram(data, x=numeric_cols[0],
                                         title=f"Distribuição de {numeric_cols[0]}",
                                         color_discrete_sequence=[colors['primary']],
                                         opacity=options['opacity'],
                                         nbins=30)
                else:
                    # Fallback para primeira coluna se não houver numéricas
                    fig = px.histogram(data, x=data.columns[0],
                                     title=f"Distribuição de {data.columns[0]}",
                                     color_discrete_sequence=[colors['primary']])
                    
            elif chart_type == 'pie':
                # Gráfico de pizza para distribuição de categorias
                cat_cols = data.select_dtypes(include=['object', 'category']).columns
                if len(cat_cols) > 0 and len(numeric_cols) > 0:
                    # Agrupar por categoria e somar valores
                    cat_col = cat_cols[0]
                    value_col = numeric_cols[0]
                    
                    # Limitar a 8 categorias para melhor visualização
                    grouped_data = data.groupby(cat_col)[value_col].sum().reset_index()
                    if len(grouped_data) > 8:
                        # Manter as 7 maiores categorias e agrupar o resto como "Outros"
                        top_cats = grouped_data.nlargest(7, value_col)
                        others_sum = grouped_data[~grouped_data[cat_col].isin(top_cats[cat_col])][value_col].sum()
                        
                        # Adicionar categoria "Outros"
                        others_row = pd.DataFrame({cat_col: ['Outros'], value_col: [others_sum]})
                        grouped_data = pd.concat([top_cats, others_row])
                    
                    fig = px.pie(grouped_data, values=value_col, names=cat_col,
                                title=f"Distribuição por {cat_col}",
                                color_discrete_sequence=custom_colors,
                                hole=0.4)  # Donut chart
                    
                    # Adicionar valores percentuais
                    if options['show_values']:
                        fig.update_traces(textinfo='percent+label')
                else:
                    # Fallback se não houver categorias ou valores numéricos
                    fig = px.pie(title="Dados insuficientes para gráfico de pizza")
                    
            elif chart_type == 'box':
                # Box plot para distribuição de valores numéricos por categoria
                cat_cols = data.select_dtypes(include=['object', 'category']).columns
                if len(cat_cols) > 0 and len(numeric_cols) > 0:
                    cat_col = cat_cols[0]
                    value_col = numeric_cols[0]
                    
                    # Limitar a 10 categorias para melhor visualização
                    top_cats = data[cat_col].value_counts().nlargest(10).index
                    filtered_data = data[data[cat_col].isin(top_cats)]
                    
                    fig = px.box(filtered_data, x=cat_col, y=value_col,
                                title=f"Distribuição de {value_col} por {cat_col}",
                                color=cat_col,
                                color_discrete_sequence=custom_colors)
                else:
                    # Fallback se não houver categorias ou valores numéricos
                    if len(numeric_cols) > 0:
                        # Box plot simples para valores numéricos
                        fig = px.box(data, y=numeric_cols[0],
                                    title=f"Distribuição de {numeric_cols[0]}",
                                    color_discrete_sequence=[colors['primary']])
                    else:
                        fig = px.box(title="Dados insuficientes para box plot")
            else:
                # Fallback para outros tipos não implementados
                fig = px.line(data, x=x_col, y=numeric_cols[0] if len(numeric_cols) > 0 else None,
                             title="Visualização de Dados",
                             color_discrete_sequence=[colors['primary']])
        else:
            # Fallback para dados sem colunas numéricas
            fig = px.bar(data.head(15), x=data.columns[0], title="Visualização de Dados",
                        color_discrete_sequence=[colors['primary']])
    
    # Aplicar tema e configurações avançadas
    fig.update_layout(
        template=options['template'],
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['surface'],
        font_color=colors['text'],
        title_font_color=colors['text'],
        title_font_size=options['title_font_size'],
        legend_title_font_size=options['legend_font_size'],
        legend_font_size=options['legend_font_size'],
        showlegend=options['show_legend'],
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode='closest',
        xaxis=dict(
            showgrid=options['show_grid'],
            gridcolor=colors['border'],
            title_font_size=options['axis_font_size'],
            tickfont_size=options['axis_font_size'] - 2,
        ),
        yaxis=dict(
            showgrid=options['show_grid'],
            gridcolor=colors['border'],
            title_font_size=options['axis_font_size'],
            tickfont_size=options['axis_font_size'] - 2,
        ),
        # Adicionar marca d'água sutil
        annotations=[
            dict(
                text="DataMindVV",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(
                    size=50,
                    color=colors['border'],
                ),
                opacity=0.07,
                textangle=0
            )
        ]
    )
    
    # Configurar linhas e marcadores
    if chart_type == 'line' or chart_type == 'scatter':
        # Aplicar configurações específicas para gráficos de linha e dispersão
        for trace in fig.data:
            if hasattr(trace, 'type') and trace.type in ['scatter', 'scattergl']:
                # Configurar marcadores para todos os tipos de scatter
                if hasattr(trace, 'marker'):
                    trace.marker.size = options['marker_size']
                # Configurar linhas apenas para traces que suportam essa propriedade
                if hasattr(trace, 'line'):
                    trace.line.width = options['line_width']
    
    # Adicionar animações se solicitado
    if animation:
        # Configurar animações para transições suaves
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    showactive=False,
                    buttons=[
                        dict(
                            label="Animar",
                            method="animate",
                            args=[
                                None,
                                dict(
                                    frame=dict(duration=500, redraw=True),
                                    fromcurrent=True,
                                    transition=dict(duration=300, easing="quadratic-in-out")
                                )
                            ]
                        )
                    ],
                    x=0.05,
                    y=1.15,
                )
            ]
        )
    
    # Adicionar marca d'água com a data de atualização
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    fig.add_annotation(
        text=f"Atualizado em: {current_time}",
        x=1,
        y=-0.15,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=10, color=colors['text_secondary']),
        align="right"
    )
    
    return fig

def create_empty_dashboard_layout():
    """Layout para dashboard vazio"""
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-chart-line fa-3x text-primary mb-3"),
                        html.H3("Dashboard Vazio", className="mb-3"),
                        html.P(
                            "Nenhum dado carregado. Para começar a criar visualizações, você precisa carregar dados.",
                            className="text-muted mb-4"
                        ),
                        html.Div([
                            dbc.Button([
                                html.I(className="fas fa-upload me-2"),
                                "Carregar Arquivo"
                            ], color="primary", className="me-3 mb-2", href="/upload"),
                            dbc.Button([
                                html.I(className="fas fa-database me-2"),
                                "Conectar a Fonte de Dados"
                            ], color="outline-primary", className="mb-2", href="/database")
                        ], className="d-flex flex-wrap justify-content-center")
                    ], className="text-center py-5")
                ], className="d-flex justify-content-center align-items-center")
            ])
        ], className="shadow-sm border-0 my-5")
    ], className="container py-5")

# Layout principal moderno e responsivo
layout = html.Div([
    # Stores para gerenciar estado
    dcc.Store(id="dashboard-data", storage_type="session"),
    dcc.Store(id="dashboard-theme", data="light"),
    dcc.Store(id="dashboard-filters", data={}),
    dcc.Store(id="dashboard-config", data={}),
    dcc.Store(id="dashboard-layout-mode", data="default"),
    
    # Script para aplicar tema inicial
    html.Script("""
        // Aplicar tema inicial
        document.addEventListener('DOMContentLoaded', function() {
            const theme = localStorage.getItem('app-theme') || 'light';
            document.documentElement.setAttribute('data-theme', theme);
            document.body.setAttribute('data-theme', theme);
        });
    """),
    
    # Cabeçalho fixo moderno
    html.Div(id="dashboard-header"),
    
    # Container principal com design aprimorado
    dbc.Container([
        # Hero Section com KPIs
        html.Div([
            # Título da seção
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H2([
                            html.I(className="fas fa-chart-line me-3 text-primary"),
                            "Indicadores Principais"
                        ], className="display-6 fw-bold mb-2"),
                        html.P("Acompanhe os principais métricas em tempo real", 
                              className="lead text-muted mb-4")
                    ], className="text-center py-3")
                ])
            ]),
            
            # KPIs Cards
            html.Div(id="kpi-section", className="mb-5")
        ], className="mb-4"),
        
        # Layout principal responsivo
        dbc.Row([
            # Sidebar de filtros e controles
            dbc.Col([
                # Card de filtros
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H5([
                                    html.I(className="fas fa-filter me-2"),
                                    "Filtros e Controles"
                                ], className="mb-0 text-primary")
                            ], md=8),
                            dbc.Col([
                                dbc.Button(
                                    html.I(id="filters-chevron", className="fas fa-chevron-down"),
                                    id="filters-collapse-btn",
                                    color="outline-primary",
                                    size="sm",
                                    className="float-end"
                                )
                            ], md=4, className="text-end")
                        ])
                    ]),
                    dbc.Collapse(
                        dbc.CardBody([
                            html.Div(id="filters-sidebar")
                        ]),
                        id="filters-collapse",
                        is_open=True
                    )
                ], className="mb-4 shadow-sm border-0"),
                
                # Card de ações rápidas
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-bolt me-2"),
                            "Ações Rápidas"
                        ], className="mb-0 text-info")
                    ]),
                    dbc.CardBody([
                        dbc.ButtonGroup([
                            dbc.Button(
                                [html.I(className="fas fa-plus me-2"), "Gráfico"],
                                id="add-chart-btn",
                                color="primary",
                                size="sm",
                                className="mb-2 w-100"
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-table me-2"), "Tabela"],
                                id="add-table-btn",
                                color="success",
                                size="sm",
                                className="mb-2 w-100"
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-sync-alt me-2"), "Atualizar"],
                                id="refresh-btn",
                                color="info",
                                size="sm",
                                className="mb-2 w-100"
                            )
                        ], vertical=True, className="w-100"),
                        
                        html.Hr(),
                        
                        # Controles de layout
                        html.Div([
                            html.Label("Layout do Dashboard:", className="fw-bold mb-2"),
                            dbc.RadioItems(
                                id="layout-mode-selector",
                                options=[
                                    {"label": "Padrão", "value": "default"},
                                    {"label": "Compacto", "value": "compact"},
                                    {"label": "Expandido", "value": "expanded"}
                                ],
                                value="default",
                                className="mb-3"
                            ),
                            
                            html.Label("Atualização Automática:", className="fw-bold mb-2"),
                            dbc.Switch(
                                id="auto-refresh-switch",
                                label="Ativar",
                                value=False,
                                className="mb-3"
                            )
                        ])
                    ])
                ], className="mb-4 shadow-sm border-0")
            ], lg=3, md=12, className="mb-4"),
            
            # Área principal de visualizações
            dbc.Col([
                # Barra de ferramentas superior
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H5([
                                    html.I(className="fas fa-chart-area me-2"),
                                    "Visualizações"
                                ], className="mb-0 text-secondary")
                            ], md=6),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button(
                                        html.I(className="fas fa-th-large"),
                                        id="grid-view-btn",
                                        color="outline-secondary",
                                        size="sm",
                                        title="Visualização em Grade"
                                    ),
                                    dbc.Button(
                                        html.I(className="fas fa-list"),
                                        id="list-view-btn",
                                        color="outline-secondary",
                                        size="sm",
                                        title="Visualização em Lista"
                                    ),
                                    dbc.Button(
                                        html.I(className="fas fa-expand-arrows-alt"),
                                        id="fullscreen-btn",
                                        color="outline-secondary",
                                        size="sm",
                                        title="Tela Cheia"
                                    )
                                ], className="float-end")
                            ], md=6, className="text-end")
                        ])
                    ])
                ], className="mb-4 shadow-sm border-0"),
                
                # Grid de visualizações responsivo
                html.Div([
                    dcc.Loading(
                        id="loading-charts",
                        type="default",
                        children=html.Div(id="charts-grid")
                    )
                ], className="mb-4"),
                
                # Seção de tabelas de dados
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.H5([
                                    html.I(className="fas fa-table me-2"),
                                    "Dados Detalhados"
                                ], className="mb-0 text-secondary")
                            ], md=8),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button(
                                        html.I(className="fas fa-download"),
                                        id="export-data-btn",
                                        color="outline-success",
                                        size="sm",
                                        title="Exportar Dados"
                                    ),
                                    dbc.Button(
                                        html.I(className="fas fa-search"),
                                        id="search-data-btn",
                                        color="outline-info",
                                        size="sm",
                                        title="Pesquisar"
                                    )
                                ], className="float-end")
                            ], md=4, className="text-end")
                        ])
                    ]),
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading-tables",
                            type="default",
                            children=html.Div(id="tables-section")
                        )
                    ])
                ], className="shadow-sm border-0")
            ], lg=9, md=12)
        ])
    ], fluid=True, className="py-4"),
    
    # Footer com informações do sistema
    html.Footer([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.I(className="fas fa-info-circle me-2"),
                        "Dashboard atualizado automaticamente a cada minuto"
                    ], className="text-muted small mb-0")
                ], md=6),
                dbc.Col([
                    html.P([
                        html.I(className="fas fa-clock me-2"),
                        "Última atualização: ",
                        html.Span(id="last-update-footer", children=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    ], className="text-muted small mb-0 text-end")
                ], md=6)
            ])
        ], fluid=True)
    ], className="bg-light py-3 mt-5"),
    
    # Interval para atualizações automáticas
    dcc.Interval(id="auto-refresh", interval=60000, n_intervals=0, disabled=True)
], style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh'}, className="dashboard-container")

# Função para carregar dados do cache
def get_cached_data():
    """Recupera dados do cache"""
    global cache
    if cache is None:
        return None
    
    try:
        data_key = cache.get_active_data_key()
        if data_key:
            return cache.get(data_key)
    except Exception as e:
        log_error(f"Erro ao recuperar dados do cache: {str(e)}")
    
    return None

# Registrar callbacks
def register_callbacks(app, cache_instance):
    """Registra todos os callbacks do dashboard"""
    global cache
    cache = cache_instance
    
    # Callback para inicialização do layout
    @app.callback(
        [Output('dashboard-header', 'children'),
         Output('kpi-section', 'children'),
         Output('filters-sidebar', 'children'),
         Output('charts-grid', 'children'),
         Output('tables-section', 'children')],
        [Input('dashboard-theme', 'data'),
         Input('dashboard-data', 'data'),
         Input('server-side-data-key', 'data')]
    )
    def update_dashboard_layout(theme, dashboard_data, data_key):
        """Atualiza layout do dashboard baseado no tema e dados"""
        try:
            # Tentar obter dados do cache primeiro
            df = None
            if data_key:
                df = get_cached_data()
            elif dashboard_data:
                df = pd.DataFrame(dashboard_data)
            
            # Criar componentes
            header = create_header(theme)
            kpis = create_kpi_cards(df, theme)
            filters = create_filters_sidebar(df, theme)
            
            if df is not None and not df.empty:
                # Criar gráficos com dados reais
                charts = dbc.Row([
                    create_chart_card('sales-trend', 'Tendência de Vendas', 'line', theme, df),
                    create_chart_card('category-dist', 'Distribuição por Categoria', 'bar', theme, df),
                    create_chart_card('performance', 'Performance Mensal', 'area', theme, df),
                    create_chart_card('correlation', 'Matriz de Correlação', 'heatmap', theme, df)
                ])
                
                # Criar tabela com dados reais
                tables = create_data_table_card('main-data', 'Dados Principais', theme, df)
            else:
                # Layout vazio
                charts = create_empty_dashboard_layout()
                tables = html.Div()
            
            return header, kpis, filters, charts, tables
            
        except Exception as e:
            log_error(f"Erro ao atualizar layout do dashboard: {str(e)}")
            return html.Div(), html.Div(), html.Div(), create_empty_dashboard_layout(), html.Div()
    
    # Callback para alternar tema
    @app.callback(
        [Output('dashboard-theme', 'data'),
         Output('theme-toggle-btn', 'children')],
        Input('theme-toggle-btn', 'n_clicks'),
        State('dashboard-theme', 'data'),
        prevent_initial_call=True
    )
    def toggle_theme(n_clicks, current_theme):
        """Alterna entre tema claro e escuro"""
        if n_clicks:
            new_theme = 'dark' if current_theme == 'light' else 'light'
            icon_class = 'fas fa-sun' if new_theme == 'dark' else 'fas fa-moon'
            return new_theme, html.I(className=icon_class)
        
        # Estado inicial
        icon_class = 'fas fa-sun' if current_theme == 'dark' else 'fas fa-moon'
        return current_theme, html.I(className=icon_class)
    
    # Callback para colapsar filtros
    @app.callback(
        [Output('filters-collapse', 'is_open'),
         Output('filters-chevron', 'className')],
        Input('filters-collapse-btn', 'n_clicks'),
        State('filters-collapse', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_filters_collapse(n_clicks, is_open):
        """Colapsa/expande painel de filtros"""
        if n_clicks:
            new_state = not is_open
            chevron_class = "fas fa-chevron-up" if new_state else "fas fa-chevron-down"
            return new_state, chevron_class
        return is_open, "fas fa-chevron-down"
    
    # Callback para carregar dados iniciais
    @app.callback(
        Output('dashboard-data', 'data'),
        Input('refresh-btn', 'n_clicks'),
        State('server-side-data-key', 'data'),
        prevent_initial_call=True
    )
    def load_dashboard_data(n_clicks, data_key):
        """Carrega dados para o dashboard"""
        try:
            if data_key:
                data = get_cached_data()
                if data is not None:
                    # Limitar dados para performance
                    if len(data) > 10000:
                        data = data.sample(n=10000)
                    return data.to_dict('records')
            return []
        except Exception as e:
            log_error(f"Erro ao carregar dados do dashboard: {str(e)}")
            return []
    
    # Callback para atualização automática
    @app.callback(
        Output('auto-refresh', 'disabled'),
        Input('dashboard-theme', 'data')
    )
    def setup_auto_refresh(theme):
        """Configura atualização automática"""
        return False  # Habilita atualização automática

print("Dashboard moderno carregado com sucesso!")