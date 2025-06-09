# pages/dashboard.py
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import json 
import dash_dynamic_grid_layout as dgl
import uuid
from dash.exceptions import PreventUpdate

from utils.logger import log_info, log_error, log_warning, log_debug

# Variável global para a instância do cache
cache = None

# Layout for dashboard page
layout = dbc.Container([
    dcc.Store(id="dashboard-filtered-data", storage_type="session"),
    dcc.Store(id="dashboard-edit-mode", data=False),
    dcc.Store(id="dashboard-modal-feedback", data={}),
    dcc.Store(id="dashboard-elements", data=[]),
    dbc.Row([
        dbc.Col([
            html.H2([html.I(className="fas fa-tachometer-alt me-2"), "Dashboard Executivo"], className="mb-4 text-primary"),
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-filter me-2"),"Configurações e Filtros"], className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Intervalo de Atualização:", html_for="dashboard-refresh-interval"),
                            dcc.Dropdown(
                                id="dashboard-refresh-interval",
                                options=[
                                    {"label": "Manual", "value": 0}, 
                                    {"label": "30 segundos", "value": 30000},
                                    {"label": "1 minuto", "value": 60000},
                                    {"label": "5 minutos", "value": 300000}
                                ], value=0, clearable=False
                            )
                        ], md=3, className="mb-2"),
                        dbc.Col([
                            dbc.Label("Coluna Categórica para Filtro:", html_for="dashboard-filter-column"),
                            dcc.Dropdown(id="dashboard-filter-column", placeholder="Selecione uma coluna...")
                        ], md=3, className="mb-2"),
                        dbc.Col([
                            dbc.Label("Valores para Filtro (da coluna acima):", html_for="dashboard-filter-value"),
                            dcc.Dropdown(id="dashboard-filter-value", placeholder="Selecione valores...", multi=True, disabled=True)
                        ], md=3, className="mb-2"),
                        dbc.Col([
                            dbc.Label("Coluna de Data para Filtro:", html_for="dashboard-date-column-selector"),
                            dcc.Dropdown(id="dashboard-date-column-selector", placeholder="Selecione coluna de data...", disabled=True)
                        ], md=3, className="mb-2"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Intervalo de Datas (da coluna acima):", html_for="dashboard-date-range"),
                            dcc.DatePickerRange(
                                id="dashboard-date-range", display_format="DD/MM/YYYY",
                                clearable=True, disabled=True
                            )
                        ], md=6, className="mb-2"),
                        dbc.Col([
                            html.Br(), 
                            dbc.Button([html.I(className="fas fa-sync-alt me-1"), "Aplicar Filtros e Atualizar"], 
                                       id="refresh-dashboard-btn", color="primary", className="w-100 mt-md-2", n_clicks=0)
                        ], md=3, className="d-flex align-items-md-end"),
                        dbc.Col([
                            html.Br(),
                            dbc.Button([html.I(className="fas fa-edit me-1"), "Modo de Edição"],
                                      id="dashboard-edit-mode-btn", color="secondary", className="w-100 mt-md-2", n_clicks=0)
                        ], md=3, className="d-flex align-items-md-end"),
                    ]),
                ])
            ], className="mb-4 shadow-sm"),
            
            # Botões para adicionar elementos
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-plus-circle me-2"),"Adicionar Elementos"], className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Button([html.I(className="fas fa-chart-bar me-1"), "Adicionar Gráfico"], 
                                     id="add-chart-btn", color="success", className="w-100", n_clicks=0)
                        ], md=4),
                        dbc.Col([
                            dbc.Button([html.I(className="fas fa-table me-1"), "Adicionar Tabela"], 
                                     id="add-table-btn", color="info", className="w-100", n_clicks=0)
                        ], md=4),
                        dbc.Col([
                            dbc.Button([html.I(className="fas fa-calculator me-1"), "Adicionar KPI"], 
                                     id="add-kpi-btn", color="warning", className="w-100", n_clicks=0)
                        ], md=4),
                    ])
                ])
            ], className="mb-4 shadow-sm"),
            
            dcc.Interval(id="dashboard-interval-component", interval=60000, n_intervals=0, disabled=True),
            
            # Modal para configurar gráfico
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Configurar Gráfico")),
                dbc.Alert(id="chart-modal-feedback", children="", color="danger", className="mb-2"),
                dbc.ModalBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Título do Gráfico:"),
                            dbc.Input(id="chart-title-input", type="text", placeholder="Digite um título para o gráfico")
                        ], width=12, className="mb-3"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Selecione a coluna para o eixo X:"),
                            dcc.Dropdown(id="chart-x-axis-selector", placeholder="Selecione coluna para eixo X...")
                        ], width=6, className="mb-3"),
                        dbc.Col([
                            dbc.Label("Selecione a coluna para o eixo Y:"),
                            dcc.Dropdown(id="chart-y-axis-selector", placeholder="Selecione coluna para eixo Y...")
                        ], width=6, className="mb-3"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Tipo de gráfico:"),
                            dcc.Dropdown(
                                id="chart-type-selector",
                                options=[
                                    {"label": "Dispersão", "value": "scatter"},
                                    {"label": "Linha", "value": "line"},
                                    {"label": "Barra", "value": "bar"},
                                    {"label": "Histograma", "value": "histogram"},
                                    {"label": "Box Plot", "value": "box"},
                                    {"label": "Pizza", "value": "pie"}
                                ],
                                value="bar",
                                clearable=False
                            )
                        ], width=6, className="mb-3"),
                        dbc.Col([
                            dbc.Label("Agrupar por (opcional):"),
                            dcc.Dropdown(id="chart-group-by-selector", placeholder="Selecione coluna para agrupar...")
                        ], width=6, className="mb-3"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Operação de agregação:"),
                            dcc.Dropdown(
                                id="chart-agg-operation",
                                options=[
                                    {"label": "Soma", "value": "sum"},
                                    {"label": "Média", "value": "mean"},
                                    {"label": "Contagem", "value": "count"},
                                    {"label": "Mínimo", "value": "min"},
                                    {"label": "Máximo", "value": "max"}
                                ],
                                value="count",
                                clearable=False
                            )
                        ], width=6, className="mb-3"),
                    ])
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="chart-modal-close", className="me-2", color="secondary"),
                    dbc.Button("Adicionar", id="chart-modal-add", color="primary", n_clicks=0)
                ])
            ], id="chart-config-modal", size="lg", is_open=False),
            
            # Modal para configurar tabela
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Configurar Tabela")),
                dbc.Alert(id="table-modal-feedback", children="", color="danger", className="mb-2"),
                dbc.ModalBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Título da Tabela:"),
                            dbc.Input(id="table-title-input", type="text", placeholder="Digite um título para a tabela")
                        ], width=12, className="mb-3"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Selecione as colunas para exibir:"),
                            dcc.Dropdown(id="table-columns-selector", multi=True, placeholder="Selecione as colunas...")
                        ], width=12, className="mb-3"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Número de linhas a exibir:"),
                            dbc.Input(id="table-rows-input", type="number", min=1, max=100, step=1, value=10)
                        ], width=6, className="mb-3"),
                    ])
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="table-modal-close", className="me-2", color="secondary"),
                    dbc.Button("Adicionar", id="table-modal-add", color="primary", n_clicks=0)
                ])
            ], id="table-config-modal", size="lg", is_open=False),
            
            # Modal para configurar KPI
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Configurar KPI")),
                dbc.Alert(id="kpi-modal-feedback", children="", color="danger", className="mb-2"),
                dbc.ModalBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Título do KPI:"),
                            dbc.Input(id="kpi-title-input", type="text", placeholder="Digite um título para o KPI")
                        ], width=12, className="mb-3"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Selecione a coluna para o KPI:"),
                            dcc.Dropdown(id="kpi-column-selector", placeholder="Selecione a coluna...")
                        ], width=6, className="mb-3"),
                        dbc.Col([
                            dbc.Label("Operação:"),
                            dcc.Dropdown(
                                id="kpi-operation-selector",
                                options=[
                                    {"label": "Soma", "value": "sum"},
                                    {"label": "Média", "value": "mean"},
                                    {"label": "Contagem", "value": "count"},
                                    {"label": "Mínimo", "value": "min"},
                                    {"label": "Máximo", "value": "max"}
                                ],
                                value="sum",
                                clearable=False
                            )
                        ], width=6, className="mb-3"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Cor do KPI:"),
                            dcc.Dropdown(
                                id="kpi-color-selector",
                                options=[
                                    {"label": "Azul", "value": "primary"},
                                    {"label": "Verde", "value": "success"},
                                    {"label": "Vermelho", "value": "danger"},
                                    {"label": "Amarelo", "value": "warning"},
                                    {"label": "Roxo", "value": "info"}
                                ],
                                value="primary",
                                clearable=False
                            )
                        ], width=6, className="mb-3"),
                        dbc.Col([
                            dbc.Label("Ícone:"),
                            dcc.Dropdown(
                                id="kpi-icon-selector",
                                options=[
                                    {"label": "Gráfico", "value": "fas fa-chart-bar"},
                                    {"label": "Usuários", "value": "fas fa-users"},
                                    {"label": "Dinheiro", "value": "fas fa-dollar-sign"},
                                    {"label": "Calendário", "value": "fas fa-calendar"},
                                    {"label": "Relógio", "value": "fas fa-clock"}
                                ],
                                value="fas fa-chart-bar",
                                clearable=False
                            )
                        ], width=6, className="mb-3"),
                    ])
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="kpi-modal-close", className="me-2", color="secondary"),
                    dbc.Button("Adicionar", id="kpi-modal-add", color="primary", n_clicks=0)
                ])
            ], id="kpi-config-modal", size="lg", is_open=False),
            
            # Área de conteúdo do dashboard
            dcc.Loading(
                id="loading-dashboard-content",
                type="default",
                children=html.Div(id="dashboard-content-area", className="mt-4")
            ),
        ])
    ])
], fluid=True)

# Função para criar um KPI card moderno
def create_kpi_card(title, value, icon="fas fa-chart-bar", color="primary", note=""):
    return dbc.Card(
        dbc.CardBody([
        dbc.Row([
            dbc.Col([
                    html.Div([
                        html.I(className=f"{icon} fa-lg text-white"),
                    ], className=f"d-flex align-items-center justify-content-center rounded-circle bg-{color}", style={"width": "48px", "height": "48px"})
                ], width="auto", className="me-3"),
                dbc.Col([
                    html.H3(value, className=f"card-title text-{color} mb-1 fw-bold"),
                html.P(title, className="card-text text-muted mb-0 small text-uppercase fw-bold"),
                html.P(note, className="card-text text-muted small fst-italic") if note else None
                ], className="d-flex flex-column justify-content-center")
            ], align="center", className="h-100")
        ]), className="shadow-sm h-100 border-0"
    )

# Função para criar um chart card moderno (agora recebe edit_mode)
def create_chart_card(title, graph_id, edit_mode=False, icon="fas fa-chart-line"):
    delete_btn = html.Button(
                        html.I(className="fas fa-trash"),
                        id={"type": "delete-chart", "index": graph_id},
                        className="btn btn-sm btn-outline-danger ms-2",
        n_clicks=0,
        style={"display": "inline-block" if edit_mode else "none"}
    )
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.H5([
                    html.I(className=f"{icon} me-2 text-info"), title
                ], className="mb-0 d-inline fw-bold"),
                html.Div([delete_btn], className="float-end")
            ], className="d-flex align-items-center justify-content-between")
        ], className="bg-white border-0"),
        dbc.CardBody(dcc.Loading(dcc.Graph(id={"type": "graph", "index": graph_id}, style={"height": "350px"})), className="p-2")
    ], className="shadow-sm h-100 border-0")

# Função para criar um table card moderno (agora recebe edit_mode)
def create_table_card(title, table_id, edit_mode=False):
    delete_btn = html.Button(
                        html.I(className="fas fa-trash"),
                        id={"type": "delete-table", "index": table_id},
                        className="btn btn-sm btn-outline-danger ms-2",
        n_clicks=0,
        style={"display": "inline-block" if edit_mode else "none"}
    )
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.H5([
                    html.I(className="fas fa-table me-2 text-info"), title
                ], className="mb-0 d-inline fw-bold"),
                html.Div([delete_btn], className="float-end")
            ], className="d-flex align-items-center justify-content-between")
        ], className="bg-white border-0"),
        dbc.CardBody(dcc.Loading(html.Div(id={"type": "table", "index": table_id})), className="p-2")
    ], className="shadow-sm h-100 border-0")

# Função para criar um layout vazio
def create_empty_dashboard_layout():
    return dbc.Alert([
        html.H4([html.I(className="fas fa-info-circle me-2"), "Dashboard Vazio"]),
        html.P("Nenhum dado carregado. Por favor, carregue dados para visualizar o dashboard.")
    ], color="info", className="text-center m-3 p-4")

# Função para criar o layout do dashboard com grid dinâmico (recebe edit_mode)
def create_dashboard_layout(df_exists, data_source_name, data_source_type, elements=None, edit_mode=False):
    if not df_exists:
        return create_empty_dashboard_layout()
    
    if not elements:
        elements = []
    
    grid_items = []
    item_layouts = []

    for i, elem in enumerate(elements):
        # Definir tamanho base do elemento
        w = 6  # Largura padrão (metade da tela)
        h = 4  # Altura padrão
        
        # Ajustar tamanho baseado no tipo de elemento
        if elem['type'] == 'kpi':
            w = 3  # KPIs são menores
            h = 2
        elif elem['type'] == 'table':
            w = 12 # Tabelas ocupam toda a largura
            h = 6
        
        # ID único para o item no layout do grid
        item_id = str(elem.get('id', i)) # Usar o ID do elemento se disponível

        # Adicionar posição e tamanho ao layout do item
        item_layouts.append({
            'i': item_id,
            'x': (i * w) % 12,  # Posição X baseada no índice
            'y': (i * h) // 12, # Posição Y baseada no índice
            'w': w,
            'h': h,
            'minW': 3,  # Largura mínima
            'minH': 2,  # Altura mínima
            'maxW': 12, # Largura máxima
            'maxH': 12, # Altura máxima
            'isDraggable': edit_mode, # Parâmetros para cada item
            'isResizable': edit_mode  # Parâmetros para cada item
        })

        # Criar o componente real envolto em DraggableWrapper
        component_to_add = create_element_component(elem, edit_mode)
        
        grid_items.append(
            dgl.DraggableWrapper(
                children=[component_to_add],
                handleText="Mover", # Texto genérico da alça de arrasto
                handleBackground="#f8f9fa", # Cor de fundo da alça
                handleColor="#495057" # Cor do texto da alça
            )
        )
    
    # Criar grid container com configurações responsivas
    grid_container = dgl.DashGridLayout(
        id="dashboard-grid-layout",
        items=grid_items, # Passa a lista de componentes envoltos
        itemLayout=item_layouts, # Passa as definições de layout para cada item
        className="dashboard-grid",
        style={
            'background': '#f8f9fa',
            'padding': '10px',
            'borderRadius': '5px',
            'minHeight': '500px'
        },
        verticalCompact=True,
        preventCollision=False,
        useCSSTransforms=True,
        margin=[10, 10],
        containerPadding=[10, 10],
        rowHeight=100,
        breakpoints={'lg': 1200, 'md': 996, 'sm': 768, 'xs': 480, 'xxs': 0},
        cols={'lg': 12, 'md': 10, 'sm': 6, 'xs': 4, 'xxs': 2}
    )
    
    # Adicionar CSS personalizado para melhorar a responsividade
    custom_css = html.Style('''
        .dashboard-grid {
            transition: all 0.3s ease;
        }
        .dashboard-grid .react-grid-item {
            transition: all 0.3s ease;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .dashboard-grid .react-grid-item:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .dashboard-grid .react-grid-item.react-grid-placeholder {
            background: #e9ecef;
            border: 2px dashed #6c757d;
            border-radius: 5px;
        }
        /* A classe drag-handle deve ser aplicada ao elemento dentro do componente que atua como a alça */
        .drag-handle {
            cursor: grab; /* Alterado para grab para melhor UX */
            padding: 5px;
            background: #f8f9fa; /* Consistente com o fundo do cabeçalho do cartão */
            border-radius: 3px;
        }
        .dashboard-grid .react-grid-item.react-draggable-dragging {
            transition: none;
            z-index: 3;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }
        @media (max-width: 768px) {
            .dashboard-grid {
                margin: 0;
                padding: 5px;
            }
            .dashboard-grid .react-grid-item {
                margin: 5px;
            }
        }
    ''')
    
    return html.Div([
        custom_css,
        grid_container
    ], className="dashboard-container")

def create_element_component(elem, edit_mode):
    """Cria um componente para o elemento do dashboard com controles de edição"""
    if elem['type'] == 'chart':
        return create_chart_card(elem['title'], elem['id'], edit_mode)
    elif elem['type'] == 'table':
        return create_table_card(elem['title'], elem['id'], edit_mode)
    elif elem['type'] == 'kpi':
        return create_kpi_card(
            elem['title'],
            elem.get('value', '0'),
            elem.get('icon', 'fas fa-chart-bar'),
            elem.get('color', 'primary'),
            elem.get('note', '')
        )
    return None

def create_chart_card(title, graph_id, edit_mode=False, icon="fas fa-chart-line"):
    """Cria um card para um gráfico com controles de edição"""
    card = dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className=f"{icon} me-2"),
                html.Span(title, className="card-title")
            ], className="d-flex align-items-center drag-handle"),
            html.Div([
                dbc.Button(
                    html.I(className="fas fa-expand"),
                    color="link",
                    className="btn-sm me-2",
                    id={"type": "expand-chart", "index": graph_id}
                ),
                dbc.Button(
                    html.I(className="fas fa-trash-alt"),
                    color="link",
                    className="btn-sm text-danger",
                    id={"type": "delete-chart", "index": graph_id}
                ) if edit_mode else None
            ], className="ms-auto") if edit_mode else None
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            dcc.Graph(
                id={"type": "graph", "index": graph_id},
                config={'displayModeBar': True, 'responsive': True},
                style={'height': '100%', 'width': '100%'}
            )
        ], className="p-0")
    ], className="h-100")
    
    return card

def create_table_card(title, table_id, edit_mode=False):
    """Cria um card para uma tabela com controles de edição"""
    card = dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.I(className="fas fa-table me-2"),
                html.Span(title, className="card-title")
            ], className="d-flex align-items-center drag-handle"),
            html.Div([
                dbc.Button(
                    html.I(className="fas fa-expand"),
                    color="link",
                    className="btn-sm me-2",
                    id={"type": "expand-table", "index": table_id}
                ),
                dbc.Button(
                    html.I(className="fas fa-trash-alt"),
                    color="link",
                    className="btn-sm text-danger",
                    id={"type": "delete-table", "index": table_id}
                ) if edit_mode else None
            ], className="ms-auto") if edit_mode else None
        ], className="d-flex align-items-center"),
        dbc.CardBody([
            html.Div(
                id={"type": "table", "index": table_id},
                className="table-responsive"
            )
        ], className="p-0")
    ], className="h-100")
    
    return card

def create_kpi_card(title, value, icon="fas fa-chart-bar", color="primary", note=""):
    """Cria um card para um KPI"""
    card = dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.I(className=f"{icon} fa-2x mb-2"),
                    html.H4(value, className="mb-0"),
                    html.Small(title, className="text-muted")
                ], className="text-center")
            ], className="drag-handle")
        ], className="p-3")
    ], className=f"bg-{color} text-white h-100")
    
    return card

def create_empty_dashboard_layout():
    """Cria um layout vazio para quando não há dados"""
    return dbc.Alert(
        "Nenhum dado disponível para exibir no dashboard. Por favor, carregue dados primeiro.",
        color="info",
        className="text-center"
    )

# MODIFICADO PARA CACHE: Aceita cache_instance
def register_callbacks(app, cache_instance):
    global cache 
    cache = cache_instance

    @app.callback(
        [Output("dashboard-interval-component", "disabled"), Output("dashboard-interval-component", "interval")],
        [Input("dashboard-refresh-interval", "value")]
    )
    def update_dashboard_interval_settings(val):
        return (False, val) if val and val > 0 else (True, 60000)

    @app.callback(
        [Output("dashboard-filter-column", "options"), Output("dashboard-filter-column", "disabled"),
         Output("dashboard-date-column-selector", "options"), Output("dashboard-date-column-selector", "disabled"),
         Output("chart-x-axis-selector", "options"), Output("chart-y-axis-selector", "options"),
         Output("chart-group-by-selector", "options"), Output("table-columns-selector", "options"),
         Output("kpi-column-selector", "options")],
        [Input("server-side-data-key", "data")] 
    )
    def populate_filter_dropdowns(data_key): 
        if not data_key: 
            empty_opts = []
            return empty_opts, True, empty_opts, True, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts
        
        df = cache.get(data_key) 
        if df is None or df.empty: 
            empty_opts = []
            return empty_opts, True, empty_opts, True, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts
        
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        date_cols = df.select_dtypes(include=[np.datetime64]).columns.tolist() 
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Opções para os diferentes dropdowns
        cat_opts = [{"label":c,"value":c} for c in cat_cols]
        date_opts = [{"label":c,"value":c} for c in date_cols]
        
        # Para eixos X e Y, podemos usar colunas numéricas e categóricas
        all_cols = num_cols + cat_cols + date_cols
        all_cols_opts = [{"label":c,"value":c} for c in all_cols]
        
        # Para agrupar, usamos apenas colunas categóricas
        group_opts = cat_opts
        
        return (
            cat_opts, not bool(cat_opts),  # Filtro categórico
            date_opts, not bool(date_opts),  # Filtro de data
            all_cols_opts,  # Eixo X
            all_cols_opts,  # Eixo Y
            group_opts,  # Agrupar por
            all_cols_opts,  # Colunas da tabela
            all_cols_opts   # Coluna do KPI
        )

    @app.callback(
        [Output("dashboard-filter-value", "options"), Output("dashboard-filter-value", "disabled")],
        [Input("dashboard-filter-column", "value")], [State("server-side-data-key", "data")] 
    )
    def populate_categorical_value_filter(col, data_key): 
        if not col or not data_key: return [], True
        df = cache.get(data_key) 
        if df is None or df.empty or col not in df.columns: return [], True
        
        vals = df[col].dropna().unique()
        options = [{"label":str(v),"value":v} for v in sorted(vals)[:500 if len(vals)>500 else len(vals)]] 
        return options, False

    @app.callback(Output("dashboard-date-range", "disabled"), [Input("dashboard-date-column-selector", "value")])
    def toggle_date_picker_range(col): return not bool(col)
    
    @app.callback(
        Output("dashboard-edit-mode", "data"),
        Output("dashboard-edit-mode-btn", "children"),
        Output("dashboard-edit-mode-btn", "color"),
        Input("dashboard-edit-mode-btn", "n_clicks"),
        State("dashboard-edit-mode", "data")
    )
    def toggle_edit_mode(n_clicks, edit_mode):
        if n_clicks is None:
            return False, [html.I(className="fas fa-edit me-1"), "Modo de Edição"], "secondary"
        new_mode = not edit_mode if edit_mode is not None else True
        btn_text = [html.I(className="fas fa-check me-1"), "Modo de Edição Ativo"] if new_mode else [html.I(className="fas fa-edit me-1"), "Modo de Edição"]
        btn_color = "danger" if new_mode else "secondary"
        return new_mode, btn_text, btn_color
    
    # Callbacks para abrir/fechar modais
    @app.callback(
        Output("chart-config-modal", "is_open"),
        [Input("add-chart-btn", "n_clicks"), Input("chart-modal-add", "n_clicks")],
        [State("chart-config-modal", "is_open")]
    )
    def toggle_chart_modal(n_add, n_confirm, is_open):
        if n_add or n_confirm:
            return not is_open
        return is_open
    
    @app.callback(
        Output("table-config-modal", "is_open"),
        [Input("add-table-btn", "n_clicks"), Input("table-modal-close", "n_clicks"), Input("table-modal-add", "n_clicks")],
        [State("table-config-modal", "is_open")]
    )
    def toggle_table_modal(n_add, n_close, n_confirm, is_open):
        if n_add or n_close or n_confirm:
            return not is_open
        return is_open
    
    @app.callback(
        Output("kpi-config-modal", "is_open"),
        [Input("add-kpi-btn", "n_clicks"), Input("kpi-modal-close", "n_clicks"), Input("kpi-modal-add", "n_clicks")],
        [State("kpi-config-modal", "is_open")]
    )
    def toggle_kpi_modal(n_add, n_close, n_confirm, is_open):
        if n_add or n_close or n_confirm:
            return not is_open
        return is_open
    
    # Callback para adicionar elementos ao dashboard, agora com validação
    @app.callback(
        Output("dashboard-elements", "data"),
        Output("dashboard-modal-feedback", "data"),
        [Input("chart-modal-add", "n_clicks"),
            Input("table-modal-add", "n_clicks"),
         Input("kpi-modal-add", "n_clicks")],
        [State("dashboard-elements", "data"),
            # Estados para gráfico
            State("chart-title-input", "value"),
            State("chart-x-axis-selector", "value"),
            State("chart-y-axis-selector", "value"),
            State("chart-type-selector", "value"),
            State("chart-group-by-selector", "value"),
            State("chart-agg-operation", "value"),
            # Estados para tabela
            State("table-title-input", "value"),
            State("table-columns-selector", "value"),
            State("table-rows-input", "value"),
            # Estados para KPI
            State("kpi-title-input", "value"),
            State("kpi-column-selector", "value"),
            State("kpi-operation-selector", "value"),
            State("kpi-color-selector", "value"),
            State("kpi-icon-selector", "value")
        ]
    )
    def add_dashboard_element(chart_clicks, table_clicks, kpi_clicks, 
                             elements, 
                             chart_title, chart_x, chart_y, chart_type, chart_group, chart_agg,
                             table_title, table_columns, table_rows,
                             kpi_title, kpi_column, kpi_operation, kpi_color, kpi_icon):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        elements = elements or []
        feedback = {}
        # Prevenir duplicidade (mesmo título e tipo)
        def is_duplicate(title, tipo):
            return any(e.get('title') == title and e.get('type') == tipo for e in elements)
        if trigger_id == "chart-modal-add":
            if not chart_x or not chart_title:
                feedback = {"modal": "chart", "msg": "Preencha o título e selecione a coluna do eixo X."}
                return elements, feedback
            if is_duplicate(chart_title, 'chart'):
                feedback = {"modal": "chart", "msg": "Já existe um gráfico com esse título."}
                return elements, feedback
            element_id = f"chart-{str(uuid.uuid4())[:8]}"
            elements.append({
                'id': element_id,
                'type': 'chart',
                'title': chart_title,
                'config': {
                    'x': chart_x,
                    'y': chart_y,
                    'type': chart_type,
                    'group_by': chart_group,
                    'agg_operation': chart_agg
                }
            })
            return elements, {}
        elif trigger_id == "table-modal-add":
            if not table_columns or not table_title:
                feedback = {"modal": "table", "msg": "Preencha o título e selecione as colunas."}
                return elements, feedback
            if is_duplicate(table_title, 'table'):
                feedback = {"modal": "table", "msg": "Já existe uma tabela com esse título."}
                return elements, feedback
            element_id = f"table-{str(uuid.uuid4())[:8]}"
            elements.append({
                'id': element_id,
                'type': 'table',
                'title': table_title,
                'config': {
                    'columns': table_columns,
                    'rows': table_rows
                }
            })
            return elements, {}
        elif trigger_id == "kpi-modal-add":
            if not kpi_column or not kpi_title:
                feedback = {"modal": "kpi", "msg": "Preencha o título e selecione a coluna."}
                return elements, feedback
            if is_duplicate(kpi_title, 'kpi'):
                feedback = {"modal": "kpi", "msg": "Já existe um KPI com esse título."}
                return elements, feedback
            element_id = f"kpi-{str(uuid.uuid4())[:8]}"
            elements.append({
                'id': element_id,
                'type': 'kpi',
                'title': kpi_title,
                'config': {
                    'column': kpi_column,
                    'operation': kpi_operation,
                    'color': kpi_color,
                    'icon': kpi_icon
                }
            })
            return elements, {}
        return elements, {}
        
    # Callback para remover elementos (só no modo edição)
    @app.callback(
        Output("dashboard-elements", "data", allow_duplicate=True),
        [Input({"type": "delete-chart", "index": dash.ALL}, "n_clicks"),
         Input({"type": "delete-table", "index": dash.ALL}, "n_clicks")],
        [State("dashboard-elements", "data"),
         State({"type": "delete-chart", "index": dash.ALL}, "id"),
         State({"type": "delete-table", "index": dash.ALL}, "id"),
         State("dashboard-edit-mode", "data")],
        prevent_initial_call=True
    )
    def remove_dashboard_element(chart_clicks, table_clicks, elements, chart_ids, table_ids, edit_mode):
        ctx = callback_context
        if not ctx.triggered or not elements or not edit_mode:
            return elements
        triggered_id = ctx.triggered[0]["prop_id"]
        elements_list = elements.copy()
        if ".n_clicks" in triggered_id:
            element_id = json.loads(triggered_id.split(".")[0])["index"]
            elements_list = [e for e in elements_list if e.get('id') != element_id]
        return elements_list
        
    @app.callback(
        Output("dashboard-content-area", "children"),
        [Input("refresh-dashboard-btn", "n_clicks"),
         Input("dashboard-interval-component", "n_intervals"),
         Input("dashboard-elements", "data"),
         Input("dashboard-edit-mode", "data")],
        [State("server-side-data-key", "data"),
         State("active-connection-name", "data"),
         State("active-table-name", "data"),
         State("data-source-type", "data")]
    )
    def update_dashboard_layout(n_clicks, n_intervals, elements, edit_mode, data_key, conn, table, src_type):
        if not data_key: return create_empty_dashboard_layout()
        df_check = cache.get(data_key)
        data_exists = df_check is not None and not df_check.empty
        name = f"{conn} - {table}" if src_type=='database' else table if src_type=='upload' else "N/A"
        return create_dashboard_layout(data_exists, name, src_type, elements, edit_mode=edit_mode)

    # Callback para renderizar gráficos
    @app.callback(
        Output({"type": "graph", "index": dash.ALL}, "figure"),
        [Input("refresh-dashboard-btn", "n_clicks"),
         Input("dashboard-interval-component", "n_intervals")],
        [State("dashboard-filtered-data", "data"),
         State("dashboard-elements", "data"),
         State({"type": "graph", "index": dash.ALL}, "id")]
    )
    def update_charts(n_clicks, n_intervals, filtered_data_json, elements, graph_ids):
        if not filtered_data_json or not elements or not graph_ids:
            return [go.Figure() for _ in graph_ids]
        try:
            df = pd.read_json(filtered_data_json, orient='split')
        except Exception:
            return [go.Figure() for _ in graph_ids]
        if df is None or df.empty:
            return [go.Figure() for _ in graph_ids]
        figures = []
        for graph_id in graph_ids:
            element_id = graph_id["index"]
            element = next((e for e in elements if e.get('id') == element_id and e.get('type') == 'chart'), None)
            if not element:
                figures.append(go.Figure())
                continue
            config = element.get('config', {})
            x_col = config.get('x')
            y_col = config.get('y')
            chart_type = config.get('type', 'bar')
            group_by = config.get('group_by')
            agg_operation = config.get('agg_operation', 'count')
            title = element.get('title', 'Gráfico')
            fig = go.Figure()
            try:
                if x_col and x_col in df.columns:
                    if chart_type == "scatter":
                        if y_col and y_col in df.columns:
                            if group_by and group_by in df.columns:
                                fig = px.scatter(df, x=x_col, y=y_col, color=group_by, title=title, template="plotly_white")
                            else:
                                fig = px.scatter(df, x=x_col, y=y_col, title=title, template="plotly_white")
                    elif chart_type == "line":
                        if y_col and y_col in df.columns:
                            if group_by and group_by in df.columns:
                                fig = px.line(df, x=x_col, y=y_col, color=group_by, title=title, template="plotly_white")
                            else:
                                fig = px.line(df, x=x_col, y=y_col, title=title, template="plotly_white")
                    elif chart_type == "bar":
                        if y_col and y_col in df.columns:
                            if group_by and group_by in df.columns:
                                agg_df = df.groupby([x_col, group_by]).agg({y_col: agg_operation}).reset_index()
                                fig = px.bar(agg_df, x=x_col, y=y_col, color=group_by, title=title, template="plotly_white")
                            else:
                                agg_df = df.groupby(x_col).agg({y_col: agg_operation}).reset_index()
                                fig = px.bar(agg_df, x=x_col, y=y_col, title=title, template="plotly_white")
                    elif chart_type == "histogram":
                        fig = px.histogram(df, x=x_col, title=title, template="plotly_white")
                    elif chart_type == "box":
                        if y_col and y_col in df.columns:
                            if group_by and group_by in df.columns:
                                fig = px.box(df, x=group_by, y=y_col, title=title, template="plotly_white")
                            else:
                                fig = px.box(df, y=y_col, title=title, template="plotly_white")
                    elif chart_type == "pie":
                        if y_col and y_col in df.columns:
                            agg_df = df.groupby(x_col).agg({y_col: agg_operation}).reset_index()
                            fig = px.pie(agg_df, names=x_col, values=y_col, title=title, template="plotly_white")
                    fig.update_layout(title_x=0.5, margin=dict(t=50,b=20,l=20,r=20))
            except Exception as e:
                log_error("Erro ao criar gráfico", extra={
                    "element_id": element_id,
                    "error": str(e),
                    "chart_type": chart_type if 'chart_type' in locals() else None,
                    "df_shape": df.shape if 'df' in locals() else None
                })
                fig.update_layout(annotations=[{'text':f'Erro ao criar gráfico: {str(e)}','showarrow':False, 'font_size':10}])
            figures.append(fig)
        return figures
    
    # Callback para renderizar tabelas
    @app.callback(
        Output({"type": "table", "index": dash.ALL}, "children"),
        [Input("refresh-dashboard-btn", "n_clicks"),
         Input("dashboard-interval-component", "n_intervals")],
        [State("dashboard-filtered-data", "data"),
         State("dashboard-elements", "data"),
         State({"type": "table", "index": dash.ALL}, "id")]
    )
    def update_tables(n_clicks, n_intervals, filtered_data_json, elements, table_ids):
        if not filtered_data_json or not elements or not table_ids:
            return [html.Div("Sem dados") for _ in table_ids]
        try:
            df = pd.read_json(filtered_data_json, orient='split')
        except Exception:
            return [html.Div("Sem dados") for _ in table_ids]
        if df is None or df.empty:
            return [html.Div("Nenhum dado corresponde aos filtros") for _ in table_ids]
        tables = []
        for table_id in table_ids:
            element_id = table_id["index"]
            element = next((e for e in elements if e.get('id') == element_id and e.get('type') == 'table'), None)
            if not element:
                tables.append(html.Div("Configuração de tabela não encontrada"))
                continue
            config = element.get('config', {})
            columns = config.get('columns', [])
            rows = config.get('rows', 10)
            try:
                if columns and all(col in df.columns for col in columns):
                    table_df = df[columns].head(rows)
                else:
                    table_df = df.head(rows)
                table = dash_table.DataTable(
                    data=table_df.to_dict('records'), 
                    columns=[{"name":str(i),"id":str(i)} for i in table_df.columns],
                    page_size=rows, 
                    style_table={'overflowX':'auto','minHeight':'300px'},
                    style_cell={'textAlign':'left','padding':'8px','fontSize':'0.9em'},
                    style_header={'backgroundColor':'#e9ecef','fontWeight':'bold'}, 
                    fixed_rows={'headers':True}
                )
                tables.append(table)
            except Exception as e:
                log_error("Erro ao criar tabela", extra={
                    "element_id": element_id,
                    "error": str(e),
                    "df_shape": df.shape if 'df' in locals() else None
                })
                tables.append(html.Div(f"Erro ao criar tabela: {str(e)}"))
        return tables
    
    # Callback para renderizar KPIs
    @app.callback(
        Output({"type": "kpi", "index": dash.ALL}, "children"),
        [Input("refresh-dashboard-btn", "n_clicks"),
         Input("dashboard-interval-component", "n_intervals")],
        [State("dashboard-filtered-data", "data"),
         State("dashboard-elements", "data"),
         State({"type": "kpi", "index": dash.ALL}, "id")]
    )
    def update_kpis(n_clicks, n_intervals, filtered_data_json, elements, kpi_ids):
        if not filtered_data_json or not elements or not kpi_ids:
            return [create_kpi_card("N/D", "-", "fas fa-ban", "light") for _ in kpi_ids]
        try:
            df = pd.read_json(filtered_data_json, orient='split')
        except Exception:
            return [create_kpi_card("N/D", "-", "fas fa-ban", "light") for _ in kpi_ids]
        if df is None or df.empty:
            return [create_kpi_card("Sem dados nos filtros", "0", "fas fa-filter", "light") for _ in kpi_ids]
        kpis = []
        for kpi_id in kpi_ids:
            element_id = kpi_id["index"]
            element = next((e for e in elements if e.get('id') == element_id and e.get('type') == 'kpi'), None)
            if not element:
                kpis.append(create_kpi_card("Configuração não encontrada", "-", "fas fa-question", "light"))
                continue
            config = element.get('config', {})
            column = config.get('column')
            operation = config.get('operation', 'count')
            color = config.get('color', 'primary')
            icon = config.get('icon', 'fas fa-chart-bar')
            title = element.get('title', 'KPI')
            try:
                if column and column in df.columns:
                    if operation == 'count':
                        value = len(df)
                        formatted_value = f"{value:,}"
                    elif operation == 'sum' and pd.api.types.is_numeric_dtype(df[column]):
                        value = df[column].sum()
                        formatted_value = f"{value:,.2f}"
                    elif operation == 'mean' and pd.api.types.is_numeric_dtype(df[column]):
                        value = df[column].mean()
                        formatted_value = f"{value:,.2f}"
                    elif operation == 'min' and pd.api.types.is_numeric_dtype(df[column]):
                        value = df[column].min()
                        formatted_value = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
                    elif operation == 'max' and pd.api.types.is_numeric_dtype(df[column]):
                        value = df[column].max()
                        formatted_value = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
                    elif operation == 'nunique':
                        value = df[column].nunique()
                        formatted_value = f"{value:,}"
                    else:
                        formatted_value = "N/A"
                else:
                    formatted_value = "N/A"
                kpis.append(create_kpi_card(title, formatted_value, icon, color))
            except Exception as e:
                log_error("Erro ao criar KPI", extra={
                    "element_id": element_id,
                    "error": str(e),
                    "kpi_type": operation if 'operation' in locals() else None,
                    "df_shape": df.shape if 'df' in locals() else None
                })
                kpis.append(create_kpi_card(title, "Erro", "fas fa-exclamation-circle", "danger"))
        return kpis

    @app.callback(
        Output("dashboard-filtered-data", "data"),
        Input("server-side-data-key", "data"),
        Input("dashboard-filter-column", "value"),
        Input("dashboard-filter-value", "value"),
        Input("dashboard-date-column-selector", "value"),
        Input("dashboard-date-range", "start_date"),
        Input("dashboard-date-range", "end_date"),
    )
    def filter_dashboard_data(data_key, filter_col, filter_vals, date_col, start_dt, end_dt):
        if not data_key:
            return {}
        
        df = cache.get(data_key)
        if df is None or df.empty:
            return {}
        
        # Aplicar filtros
        df_filtered = df.copy()
        if filter_col and filter_vals and filter_col in df.columns:
            df_filtered = df_filtered[df_filtered[filter_col].isin(filter_vals)]
        if date_col and start_dt and end_dt and date_col in df.columns:
            try:
                df_filtered[date_col] = pd.to_datetime(df_filtered[date_col], errors='coerce')
                df_filtered.dropna(subset=[date_col], inplace=True)
                start_dt_obj = pd.to_datetime(start_dt, errors='coerce')
                end_dt_obj = pd.to_datetime(end_dt, errors='coerce')
                if pd.NaT not in [start_dt_obj, end_dt_obj]:
                    df_filtered = df_filtered[(df_filtered[date_col] >= start_dt_obj) & (df_filtered[date_col] <= end_dt_obj)]
            except Exception as e:
                log_error("Erro ao aplicar filtro de data em KPIs", extra={
                    "error": str(e),
                    "date_col": date_col if 'date_col' in locals() else None,
                    "start_date": start_dt if 'start_dt' in locals() else None,
                    "end_date": end_dt if 'end_dt' in locals() else None,
                    "df_shape": df.shape if 'df' in locals() else None
                })
        
        # Salvar o DataFrame filtrado como JSON (usando df.to_json) para o dcc.Store
        return df_filtered.to_json(orient='split')

    # Exibir feedback visual nos modais
    @app.callback(
        Output("chart-config-modal", "children", allow_duplicate=True),
        Input("dashboard-modal-feedback", "data"),
        prevent_initial_call=True
    )
    def show_chart_modal_feedback(feedback):
        if feedback and feedback.get("modal") == "chart":
            return [
                dbc.ModalHeader(dbc.ModalTitle("Configurar Gráfico")),
                dbc.Alert(feedback["msg"], color="danger", className="mb-2"),
                dash.no_update
            ]
        return dash.no_update
    @app.callback(
        Output("table-config-modal", "children", allow_duplicate=True),
        Input("dashboard-modal-feedback", "data"),
        prevent_initial_call=True
    )
    def show_table_modal_feedback(feedback):
        if feedback and feedback.get("modal") == "table":
            return [
                dbc.ModalHeader(dbc.ModalTitle("Configurar Tabela")),
                dbc.Alert(feedback["msg"], color="danger", className="mb-2"),
                dash.no_update
            ]
        return dash.no_update
    @app.callback(
        Output("kpi-config-modal", "children", allow_duplicate=True),
        Input("dashboard-modal-feedback", "data"),
        prevent_initial_call=True
    )
    def show_kpi_modal_feedback(feedback):
        if feedback and feedback.get("modal") == "kpi":
            return [
                dbc.ModalHeader(dbc.ModalTitle("Configurar KPI")),
                dbc.Alert(feedback["msg"], color="danger", className="mb-2"),
                dash.no_update
            ]
        return dash.no_update