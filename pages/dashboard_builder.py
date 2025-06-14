# -*- coding: utf-8 -*-
"""
Dashboard Builder - Interface Drag & Drop
Permite aos usuários construir dashboards arrastando e soltando componentes
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import uuid
from datetime import datetime

from utils.logger import log_info, log_error, log_warning
from utils.sqlite_cache import SQLiteCache
from utils.template_manager import TemplateManager
from utils.theme_manager import ThemeManager

# Componentes disponíveis para arrastar
AVAILABLE_COMPONENTS = {
    'chart': {
        'name': 'Gráfico',
        'icon': 'fas fa-chart-bar',
        'description': 'Gráfico de barras, linhas, pizza, etc.',
        'category': 'visualização'
    },
    'kpi': {
        'name': 'KPI Card',
        'icon': 'fas fa-tachometer-alt',
        'description': 'Cartão de indicador chave',
        'category': 'métricas'
    },
    'table': {
        'name': 'Tabela',
        'icon': 'fas fa-table',
        'description': 'Tabela de dados',
        'category': 'dados'
    },
    'filter': {
        'name': 'Filtro',
        'icon': 'fas fa-filter',
        'description': 'Componente de filtro',
        'category': 'controles'
    },
    'text': {
        'name': 'Texto',
        'icon': 'fas fa-font',
        'description': 'Bloco de texto ou título',
        'category': 'conteúdo'
    },
    'image': {
        'name': 'Imagem',
        'icon': 'fas fa-image',
        'description': 'Imagem ou logo',
        'category': 'conteúdo'
    },
    'spacer': {
        'name': 'Espaçador',
        'icon': 'fas fa-arrows-alt-v',
        'description': 'Espaço em branco',
        'category': 'layout'
    }
}

# Layout padrão do grid
DEFAULT_LAYOUT = {
    'lg': [],
    'md': [],
    'sm': [],
    'xs': [],
    'xxs': []
}

def create_component_palette():
    """Cria a paleta de componentes disponíveis"""
    categories = {}
    for comp_id, comp_info in AVAILABLE_COMPONENTS.items():
        category = comp_info['category']
        if category not in categories:
            categories[category] = []
        categories[category].append((comp_id, comp_info))
    
    palette_items = []
    for category, components in categories.items():
        # Cabeçalho da categoria
        palette_items.append(
            html.Div([
                html.H6(category.title(), className="text-muted mb-2 mt-3")
            ])
        )
        
        # Componentes da categoria
        for comp_id, comp_info in components:
            palette_items.append(
                html.Div([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className=f"{comp_info['icon']} fa-2x mb-2 text-primary"),
                                html.H6(comp_info['name'], className="card-title mb-1"),
                                html.P(comp_info['description'], className="card-text small text-muted")
                            ], className="text-center")
                        ], className="p-2")
                    ], className="draggable-component mb-2 cursor-pointer")
                ], 
                id={'type': 'component-palette-item', 'id': comp_id},
                style={'cursor': 'grab'},
                n_clicks=0
                )
            )
    
    return palette_items

def create_dashboard_canvas():
    """Cria a área de canvas para construção do dashboard"""
    return html.Div([
        # Toolbar do canvas
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-save me-1"),
                        "Salvar"
                    ], id="save-dashboard-btn", color="primary", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-eye me-1"),
                        "Visualizar"
                    ], id="preview-dashboard-btn", color="secondary", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-undo me-1"),
                        "Desfazer"
                    ], id="undo-btn", color="outline-secondary", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-redo me-1"),
                        "Refazer"
                    ], id="redo-btn", color="outline-secondary", size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-trash me-1"),
                        "Limpar"
                    ], id="clear-canvas-btn", color="danger", size="sm")
                ])
            ], width="auto"),
            dbc.Col([
                dbc.InputGroup([
                    dbc.Input(
                        id="dashboard-name-input",
                        placeholder="Nome do Dashboard",
                        value="Novo Dashboard",
                        size="sm"
                    ),
                    dbc.Button([
                        html.I(className="fas fa-edit")
                    ], color="outline-secondary", size="sm")
                ], size="sm")
            ], width=4),
            dbc.Col([
                dbc.Select(
                    id="grid-size-select",
                    options=[
                        {'label': 'Grade Pequena (12 cols)', 'value': 12},
                        {'label': 'Grade Média (16 cols)', 'value': 16},
                        {'label': 'Grade Grande (24 cols)', 'value': 24}
                    ],
                    value=12,
                    size="sm"
                )
            ], width="auto")
        ], className="mb-3 p-2 bg-light rounded"),
        
        # Canvas principal
        html.Div([
            # Área de drop
            html.Div([
                html.Div([
                    html.I(className="fas fa-plus-circle fa-3x text-muted mb-3"),
                    html.H4("Arraste componentes aqui", className="text-muted"),
                    html.P("Comece arrastando componentes da paleta para criar seu dashboard", 
                           className="text-muted")
                ], className="text-center py-5", id="empty-canvas-message")
            ], 
            id="dashboard-canvas",
            className="dashboard-canvas border-2 border-dashed border-secondary rounded p-3",
            style={'min-height': '500px', 'background': 'rgba(248, 249, 250, 0.5)'}
            )
        ])
    ])

def create_component_properties_panel():
    """Cria o painel de propriedades do componente selecionado"""
    return dbc.Card([
        dbc.CardHeader([
            html.H6("Propriedades", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div([
                html.P("Selecione um componente para editar suas propriedades", 
                       className="text-muted text-center")
            ], id="properties-content")
        ])
    ])

def create_dashboard_builder_layout():
    """Layout principal do construtor de dashboards"""
    return dbc.Container([
        # Cabeçalho
        dbc.Row([
            dbc.Col([
                html.H2([
                    html.I(className="fas fa-drafting-compass me-2"),
                    "Dashboard Builder"
                ], className="mb-0"),
                html.P("Construa dashboards interativos arrastando e soltando componentes", 
                       className="text-muted")
            ])
        ], className="mb-4"),
        
        # Layout principal
        dbc.Row([
            # Paleta de componentes (esquerda)
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Componentes", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div(
                            create_component_palette(),
                            id="component-palette",
                            style={'max-height': '600px', 'overflow-y': 'auto'}
                        )
                    ])
                ])
            ], width=3),
            
            # Canvas central
            dbc.Col([
                create_dashboard_canvas()
            ], width=6),
            
            # Painel de propriedades (direita)
            dbc.Col([
                create_component_properties_panel(),
                
                # Painel de templates
                dbc.Card([
                    dbc.CardHeader([
                        html.H6("Templates", className="mb-0")
                    ]),
                    dbc.CardBody([
                        dbc.Button("Análise de Vendas", color="outline-primary", size="sm", className="w-100 mb-2"),
                        dbc.Button("Dashboard Executivo", color="outline-primary", size="sm", className="w-100 mb-2"),
                        dbc.Button("Relatório Financeiro", color="outline-primary", size="sm", className="w-100 mb-2"),
                        dbc.Button("Monitoramento KPI", color="outline-primary", size="sm", className="w-100")
                    ])
                ], className="mt-3")
            ], width=3)
        ]),
        
        # Modais
        dbc.Modal([
            dbc.ModalHeader("Salvar Dashboard"),
            dbc.ModalBody([
                dbc.Input(
                    id="save-dashboard-name",
                    placeholder="Nome do dashboard",
                    className="mb-3"
                ),
                dbc.Textarea(
                    id="save-dashboard-description",
                    placeholder="Descrição (opcional)",
                    rows=3
                )
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="cancel-save-btn", color="secondary"),
                dbc.Button("Salvar", id="confirm-save-btn", color="primary")
            ])
        ], id="save-modal", is_open=False),
        
        # Toast para mensagens
        dbc.Toast(
            id="save-dashboard-toast",
            header="Dashboard Builder",
            is_open=False,
            dismissable=True,
            duration=4000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "z-index": 9999}
        ),
        
        # Modal de Preview
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Preview do Dashboard")),
            dbc.ModalBody(id="preview-dashboard-content"),
            dbc.ModalFooter([
                dbc.Button("Fechar", id="close-preview-modal", className="ms-auto")
            ])
        ], id="preview-dashboard-modal", size="xl", is_open=False),
        
        # Armazenamento de estado
        dcc.Store(id="dashboard-layout-store", data=DEFAULT_LAYOUT),
        dcc.Store(id="dashboard-components-store", data={}),
        dcc.Store(id="selected-component-store", data=None),
        dcc.Store(id="undo-redo-store", data={'history': [], 'current_index': -1})
        
    ], fluid=True, className="py-4")

def register_callbacks(app, cache):
    """Registra todos os callbacks do Dashboard Builder"""
    
    # Callback para alternar modal de salvar
    @app.callback(
        Output('save-modal', 'is_open'),
        [Input('save-dashboard-btn', 'n_clicks'),
         Input('cancel-save-btn', 'n_clicks'),
         Input('confirm-save-btn', 'n_clicks')],
        [State('save-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_save_modal(save_clicks, cancel_clicks, confirm_clicks, is_open):
        """Controla abertura/fechamento do modal de salvar"""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id in ['save-dashboard-btn']:
            return not is_open
        elif button_id in ['cancel-save-btn', 'confirm-save-btn']:
            return False
        
        return is_open
    
    # Callback para salvar dashboard
    @app.callback(
        [Output('save-dashboard-toast', 'is_open', allow_duplicate=True),
         Output('save-dashboard-toast', 'children', allow_duplicate=True),
         Output('save-dashboard-name', 'value'),
         Output('save-dashboard-description', 'value')],
        [Input('confirm-save-btn', 'n_clicks')],
        [State('save-dashboard-name', 'value'),
         State('save-dashboard-description', 'value'),
         State('dashboard-canvas', 'children'),
         State('dashboard-layout-store', 'data')],
        prevent_initial_call=True
    )
    def save_dashboard(n_clicks, name, description, components_data, layout_data):
        """Processa salvamento do dashboard"""
        if not n_clicks:
            raise PreventUpdate
            
        try:
            if not name or not name.strip():
                return True, dbc.Alert("Por favor, insira um nome para o dashboard.", color="warning"), name, description
            
            # Criar dados do dashboard
            dashboard_data = {
                'id': str(uuid.uuid4()),
                'name': name,
                'description': description or '',
                'components': components_data or {},
                'layout': layout_data or DEFAULT_LAYOUT,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Salvar no cache/banco de dados
            cache_key = f"dashboard_{dashboard_data['id']}"
            cache.set(cache_key, json.dumps(dashboard_data))
            
            # Adicionar à lista de dashboards salvos
            saved_dashboards = cache.get('saved_dashboards')
            if saved_dashboards:
                saved_dashboards = json.loads(saved_dashboards)
            else:
                saved_dashboards = []
            
            # Adicionar novo dashboard à lista
            dashboard_summary = {
                'id': dashboard_data['id'],
                'name': name,
                'description': description,
                'created_at': dashboard_data['created_at'],
                'component_count': len(components_data or {})
            }
            saved_dashboards.append(dashboard_summary)
            
            # Salvar lista atualizada
            cache.set('saved_dashboards', json.dumps(saved_dashboards))
            
            log_info(f"Dashboard salvo com sucesso: {name} (ID: {dashboard_data['id']})")
            
            return (
                True, 
                dbc.Alert(f"Dashboard '{name}' salvo com sucesso!", color="success"),
                "",  # Limpar nome
                ""   # Limpar descrição
            )
            
        except Exception as e:
            log_error(f"Erro ao salvar dashboard: {e}")
            return (
                True,
                dbc.Alert("Erro ao salvar dashboard. Tente novamente.", color="danger"),
                name,
                description
            )
    
    # Callback para adicionar componentes ao canvas via drag and drop
    @app.callback(
        [Output('dashboard-canvas', 'children', allow_duplicate=True),
         Output('dashboard-layout-store', 'data', allow_duplicate=True)],
        [Input({'type': 'component-palette-item', 'id': ALL}, 'n_clicks')],
        [State('dashboard-canvas', 'children'),
         State('dashboard-layout-store', 'data')],
        prevent_initial_call=True
    )
    def add_component_to_canvas(n_clicks_list, current_components, current_layout):
        """Adiciona componente ao canvas quando clicado na paleta"""
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            raise PreventUpdate
        
        # Identificar qual componente foi clicado
        triggered_id = ctx.triggered[0]['prop_id']
        component_type = None
        
        for i, n_clicks in enumerate(n_clicks_list):
            if n_clicks and n_clicks > 0:
                # Extrair tipo do componente baseado no índice
                component_types = ['chart', 'kpi', 'table', 'filter', 'text', 'image', 'spacer']
                if i < len(component_types):
                    component_type = component_types[i]
                    break
        
        if not component_type:
            raise PreventUpdate
        
        # Gerar ID único para o novo componente
        comp_id = f"{component_type}_{uuid.uuid4().hex[:8]}"
        
        # Configuração padrão do componente
        comp_config = get_default_component_config(component_type)
        comp_data = {
            'type': component_type,
            'title': AVAILABLE_COMPONENTS[component_type]['name'],
            'config': comp_config
        }
        
        # Criar novo componente
        new_component = create_dashboard_component(comp_id, comp_data)
        
        # Adicionar ao canvas
        updated_components = (current_components or []) + [new_component]
        
        # Atualizar layout
        updated_layout = current_layout or DEFAULT_LAYOUT.copy()
        updated_layout['components'] = updated_layout.get('components', {}) 
        updated_layout['components'][comp_id] = comp_data
        
        return updated_components, updated_layout
    
    # Callback para preview do dashboard
    @app.callback(
        Output('preview-dashboard-modal', 'is_open'),
        [Input('preview-dashboard-btn', 'n_clicks'),
         Input('close-preview-modal', 'n_clicks')],
        [State('preview-dashboard-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_preview_modal(preview_clicks, close_clicks, is_open):
        """Controla abertura/fechamento do modal de preview"""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        return not is_open
    
    # Callback para atualizar conteúdo do preview
    @app.callback(
        Output('preview-dashboard-content', 'children'),
        [Input('preview-dashboard-modal', 'is_open')],
        [State('dashboard-canvas', 'children'),
         State('dashboard-layout-store', 'data')],
        prevent_initial_call=True
    )
    def update_preview_content(is_open, canvas_components, layout_data):
        """Atualiza o conteúdo do preview quando o modal é aberto"""
        if not is_open:
            raise PreventUpdate
        
        if not canvas_components:
            return html.Div("Dashboard vazio", className="text-center text-muted p-5")
        
        # Criar versão de preview dos componentes (sem botões de edição)
        preview_components = []
        for component in canvas_components:
            if hasattr(component, 'children') and len(component.children) > 1:
                # Pegar apenas o conteúdo, sem o cabeçalho com botões
                content = component.children[1]  # CardBody
                preview_components.append(
                    dbc.Card(content, className="mb-3 shadow-sm")
                )
        
        return html.Div(preview_components, className="preview-container")
    
    # Callback para deletar componentes
    @app.callback(
        [Output('dashboard-canvas', 'children', allow_duplicate=True),
         Output('dashboard-layout-store', 'data', allow_duplicate=True)],
        [Input({'type': 'delete-component', 'id': ALL}, 'n_clicks')],
        [State('dashboard-canvas', 'children'),
         State('dashboard-layout-store', 'data')],
        prevent_initial_call=True
    )
    def delete_component(n_clicks_list, current_components, current_layout):
        """Remove componente do canvas"""
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            raise PreventUpdate
        
        # Identificar qual componente foi deletado
        triggered_prop = ctx.triggered[0]['prop_id']
        import json
        component_id = json.loads(triggered_prop.split('.')[0])['id']
        
        # Remover componente da lista
        updated_components = []
        for component in (current_components or []):
            if hasattr(component, 'id') and component.id != {'type': 'dashboard-component', 'id': component_id}:
                updated_components.append(component)
        
        # Atualizar layout
        updated_layout = current_layout or DEFAULT_LAYOUT.copy()
        if 'components' in updated_layout and component_id in updated_layout['components']:
            del updated_layout['components'][component_id]
        
        return updated_components, updated_layout
    
    # Callback para funcionalidade de undo/redo (básica)
    @app.callback(
        Output('undo-redo-store', 'data'),
        [Input('dashboard-layout-store', 'data')],
        [State('undo-redo-store', 'data')],
        prevent_initial_call=True
    )
    def update_history(current_layout, history_data):
        """Mantém histórico para undo/redo"""
        if not history_data:
            history_data = {'history': [], 'current_index': -1}
        
        # Adicionar estado atual ao histórico
        history_data['history'].append(current_layout)
        history_data['current_index'] = len(history_data['history']) - 1
        
        # Manter apenas os últimos 10 estados
        if len(history_data['history']) > 10:
            history_data['history'] = history_data['history'][-10:]
            history_data['current_index'] = 9
        
        return history_data
    
    # Callback para botão de undo
    @app.callback(
        [Output('dashboard-layout-store', 'data', allow_duplicate=True),
         Output('undo-btn', 'disabled'),
         Output('redo-btn', 'disabled')],
        [Input('undo-btn', 'n_clicks'),
         Input('redo-btn', 'n_clicks')],
        [State('undo-redo-store', 'data')],
        prevent_initial_call=True
    )
    def handle_undo_redo(undo_clicks, redo_clicks, history_data):
        """Gerencia funcionalidade de undo/redo"""
        ctx = callback_context
        if not ctx.triggered or not history_data:
            raise PreventUpdate
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        history = history_data.get('history', [])
        current_index = history_data.get('current_index', -1)
        
        if button_id == 'undo-btn' and current_index > 0:
            new_index = current_index - 1
            layout = history[new_index]
            undo_disabled = new_index <= 0
            redo_disabled = False
        elif button_id == 'redo-btn' and current_index < len(history) - 1:
            new_index = current_index + 1
            layout = history[new_index]
            undo_disabled = False
            redo_disabled = new_index >= len(history) - 1
        else:
            raise PreventUpdate
        
        # Atualizar índice no histórico
        history_data['current_index'] = new_index
        
        return layout, undo_disabled, redo_disabled
    
    # Callback para limpar canvas
    @app.callback(
        [Output('dashboard-canvas', 'children', allow_duplicate=True),
         Output('dashboard-layout-store', 'data', allow_duplicate=True)],
        [Input('clear-canvas-btn', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_canvas(n_clicks):
        """Limpa todo o canvas"""
        if not n_clicks:
            raise PreventUpdate
        
        return [], DEFAULT_LAYOUT.copy()
    
    log_info("Callbacks do Dashboard Builder registrados com sucesso")

def create_dashboard_component(comp_id, comp_data):
    """Cria um componente do dashboard baseado nos dados"""
    comp_type = comp_data['type']
    comp_config = comp_data.get('config', {})
    
    # Cabeçalho do componente
    header = html.Div([
        html.Span(comp_data['title'], className="component-title"),
        html.Div([
            dbc.Button(
                html.I(className="fas fa-cog"),
                size="sm",
                color="link",
                className="p-1",
                id={'type': 'config-component', 'id': comp_id}
            ),
            dbc.Button(
                html.I(className="fas fa-trash"),
                size="sm",
                color="link",
                className="p-1 text-danger",
                id={'type': 'delete-component', 'id': comp_id}
            )
        ], className="component-actions")
    ], className="component-header d-flex justify-content-between align-items-center p-2 bg-light")
    
    # Conteúdo do componente
    if comp_type == 'chart':
        content = create_chart_component(comp_config)
    elif comp_type == 'kpi':
        content = create_kpi_component(comp_config)
    elif comp_type == 'table':
        content = create_table_component(comp_config)
    elif comp_type == 'filter':
        content = create_filter_component(comp_config)
    elif comp_type == 'text':
        content = create_text_component(comp_config)
    elif comp_type == 'image':
        content = create_image_component(comp_config)
    elif comp_type == 'spacer':
        content = create_spacer_component(comp_config)
    else:
        content = html.Div("Componente não implementado", className="p-3 text-center text-muted")
    
    return dbc.Card([
        header,
        dbc.CardBody(content, className="p-2")
    ], 
    className="dashboard-component mb-2",
    id={'type': 'dashboard-component', 'id': comp_id},
    style={'cursor': 'move'}
    )

def create_chart_component(config):
    """Cria componente de gráfico"""
    # Gráfico de exemplo
    fig = go.Figure(data=[
        go.Bar(x=['A', 'B', 'C'], y=[1, 3, 2])
    ])
    fig.update_layout(
        title=config.get('title', 'Gráfico de Exemplo'),
        height=200,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

def create_kpi_component(config):
    """Cria componente de KPI"""
    return html.Div([
        html.H3(config.get('value', '1,234'), className="text-primary mb-0"),
        html.P(config.get('label', 'Vendas Totais'), className="text-muted mb-0"),
        html.Small([
            html.I(className="fas fa-arrow-up text-success me-1"),
            "+12.5%"
        ], className="text-success")
    ], className="text-center p-3")

def create_table_component(config):
    """Cria componente de tabela"""
    return html.Div([
        html.Table([
            html.Thead([
                html.Tr([html.Th("Produto"), html.Th("Vendas"), html.Th("Status")])
            ]),
            html.Tbody([
                html.Tr([html.Td("Produto A"), html.Td("R$ 1.000"), html.Td("Ativo")]),
                html.Tr([html.Td("Produto B"), html.Td("R$ 2.500"), html.Td("Ativo")]),
                html.Tr([html.Td("Produto C"), html.Td("R$ 800"), html.Td("Inativo")])
            ])
        ], className="table table-sm")
    ])

def create_filter_component(config):
    """Cria componente de filtro"""
    return html.Div([
        html.Label("Filtrar por:", className="form-label small"),
        dbc.Select(
            options=[
                {'label': 'Todos', 'value': 'all'},
                {'label': 'Ativos', 'value': 'active'},
                {'label': 'Inativos', 'value': 'inactive'}
            ],
            value='all',
            size="sm"
        )
    ])

def create_text_component(config):
    """Cria componente de texto"""
    return html.Div([
        html.H5(config.get('title', 'Título'), className="mb-2"),
        html.P(config.get('content', 'Conteúdo do texto aqui...'), className="mb-0")
    ], className="p-2")

def create_image_component(config):
    """Cria componente de imagem"""
    return html.Div([
        html.Img(
            src=config.get('src', '/assets/placeholder-image.png'),
            className="img-fluid",
            style={'max-height': '150px'}
        )
    ], className="text-center p-2")

def create_spacer_component(config):
    """Cria componente espaçador"""
    height = config.get('height', 50)
    return html.Div(
        style={'height': f'{height}px', 'background': 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,.1) 10px, rgba(0,0,0,.1) 20px)'}
    )

def get_default_component_config(component_type):
    """Retorna configuração padrão para um tipo de componente"""
    defaults = {
        'chart': {
            'chart_type': 'bar',
            'title': 'Novo Gráfico',
            'x_axis': '',
            'y_axis': '',
            'color_scheme': 'plotly'
        },
        'kpi': {
            'value': '0',
            'label': 'Novo KPI',
            'format': 'number',
            'trend': 'up',
            'trend_value': '0%'
        },
        'table': {
            'columns': [],
            'max_rows': 10,
            'sortable': True,
            'filterable': True
        },
        'filter': {
            'filter_type': 'dropdown',
            'label': 'Filtro',
            'options': []
        },
        'text': {
            'title': 'Título',
            'content': 'Conteúdo do texto',
            'alignment': 'left',
            'font_size': 'medium'
        },
        'image': {
            'src': '',
            'alt': 'Imagem',
            'width': '100%',
            'height': 'auto'
        },
        'spacer': {
            'height': 50
        }
    }
    
    return defaults.get(component_type, {})

# Layout principal do módulo
layout = create_dashboard_builder_layout()