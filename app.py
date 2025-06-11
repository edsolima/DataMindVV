# app.py
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from flask_caching import Cache 
import uuid 
import pandas as pd # <--- IMPORTAÇÃO DO PANDAS CORRIGIDA/GARANTIDA
import json 
import os # Para criar o caminho absoluto do cache

# Import page modules
from pages import database, upload, transform, visualizations, analytics, dashboard, forecasting, data_join, ai_chat

# Import utility managers
from utils.config_manager import ConfigManager
from utils.database_manager import DatabaseManager
from utils.query_manager import QueryManager
from utils.logger import log_info, log_error, log_warning, log_debug

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.LUX, 
        dbc.icons.FONT_AWESOME,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
    ],
    external_scripts=[
        "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"
    ],
    suppress_callback_exceptions=True,
    title="DataMindVV - Plataforma Analítica Integrada",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"},
        {"name": "description", "content": "Plataforma analítica integrada com IA para visualização e análise de dados"},
        {"name": "keywords", "content": "analytics, BI, dashboard, data visualization, AI, machine learning"}
    ]
)
app.server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 

# Importar o backend SQLite personalizado
from utils.sqlite_cache import SQLiteCache

# Configurar caminho para o banco de dados SQLite do cache
project_root = os.path.dirname(os.path.abspath(__file__))
sqlite_cache_path = os.path.join(project_root, 'cache.sqlite')

# Configuração do cache usando SQLiteCache como padrão
CACHE_CONFIG = {
    'CACHE_TYPE': 'null',  # Usar tipo nulo, pois o backend real é injetado manualmente
    'CACHE_DEFAULT_TIMEOUT': 3600,
    'CACHE_SQLITE_PATH': sqlite_cache_path
}

# Inicializar o cache com SQLiteCache
cache = Cache()
cache._cache = SQLiteCache({
    'CACHE_DEFAULT_TIMEOUT': 3600,
    'CACHE_SQLITE_PATH': sqlite_cache_path
})
# Redirecionar métodos principais para o backend customizado
cache.set = cache._cache.set
cache.get = cache._cache.get
cache.has = cache._cache.has
cache.delete = cache._cache.delete
cache.clear = cache._cache.clear
cache.get_active_data_key = cache._cache.get_active_data_key
cache.set_active_data_key = cache._cache.set_active_data_key
cache.init_app(app.server, config=CACHE_CONFIG)
log_info("Cache SQLiteCache inicializado", extra={"cache_type": "SQLiteCache", "sqlite_path": sqlite_cache_path})


config_manager = ConfigManager()
db_manager = DatabaseManager()
query_manager = QueryManager()

navbar = dbc.Navbar(
    dbc.Container([
        # Brand/Logo
        dbc.Row([
            dbc.Col([
                dbc.NavbarBrand([
                    html.Div([
                        html.I(className="fas fa-brain me-2 text-gradient", style={"fontSize": "1.5rem"}),
                        html.Span("DataMindVV", className="fw-bold"),
                        html.Small(" Analytics", className="text-muted ms-1")
                    ], className="d-flex align-items-center")
                ], href="/", className="text-decoration-none")
            ], width="auto"),
            
            # Navigation Items
            dbc.Col([
                dbc.Nav([
                    # Dados
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-database me-1"), 
                        html.Span("Dados", className="d-none d-lg-inline")
                    ], href="/database", id="nav-database", className="nav-link-modern")),
                    
                    # Upload
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-upload me-1"), 
                        html.Span("Upload", className="d-none d-lg-inline")
                    ], href="/upload", id="nav-upload", className="nav-link-modern")),
                    
                    # Transformar
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-exchange-alt me-1"), 
                        html.Span("Transformar", className="d-none d-lg-inline")
                    ], href="/transform", id="nav-transform", className="nav-link-modern")),
                    
                    # Combinar
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-link me-1"), 
                        html.Span("Combinar", className="d-none d-lg-inline")
                    ], href="/data-join", id="nav-join", className="nav-link-modern")),
                    
                    # Dropdown Explorar & IA
                    dbc.DropdownMenu([
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-chart-pie me-2"), "Visualizações"
                        ], href="/visualizations", id="nav-viz"),
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-chart-line me-2"), "Analytics"
                        ], href="/analytics", id="nav-analytics"),
                        dbc.DropdownMenuItem(divider=True),
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-crystal-ball me-2"), "Previsões (IA)"
                        ], href="/forecasting", id="nav-forecast"),
                        dbc.DropdownMenuItem([
                            html.I(className="fas fa-robot me-2"), "Chat com IA"
                        ], href="/ai-chat", id="nav-ai-chat"),
                    ], nav=True, in_navbar=True, 
                    label=[
                        html.I(className="fas fa-chart-bar me-1"), 
                        html.Span("Explorar & IA", className="d-none d-lg-inline")
                    ], className="nav-dropdown-modern"),
                    
                    # Dashboard
                    dbc.NavItem(dbc.NavLink([
                        html.I(className="fas fa-tachometer-alt me-1"), 
                        html.Span("Dashboard", className="d-none d-lg-inline")
                    ], href="/dashboard", id="nav-dashboard", className="nav-link-modern")),
                    
                ], navbar=True, className="me-auto flex-wrap"),
            ], className="d-flex justify-content-center flex-grow-1"),
            
            # Status Badge e Controles
            dbc.Col([
                html.Div([
                    dbc.Badge(
                        "Nenhum dado carregado", 
                        id="data-loaded-status-badge", 
                        color="secondary", 
                        text_color="white",
                        className="me-2 px-3 py-2 hover-lift", 
                        pill=True,
                        style={"fontSize": "0.75rem"}
                    ),
                    # Botão de notificações (futuro)
                    html.Button([
                        html.I(className="fas fa-bell")
                    ], className="btn btn-outline-light btn-sm me-2 d-none d-md-inline-block", 
                    style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                    
                    # Botão de configurações (futuro)
                    html.Button([
                        html.I(className="fas fa-cog")
                    ], className="btn btn-outline-light btn-sm d-none d-md-inline-block", 
                    style={"borderRadius": "50%", "width": "35px", "height": "35px"})
                ], className="d-flex align-items-center")
            ], width="auto")
        ], className="w-100 align-items-center justify-content-between g-0")
    ], fluid=True),
    color="primary", 
    dark=True, 
    sticky="top", 
    className="navbar-modern shadow-sm mb-4",
    style={"backdropFilter": "blur(10px)", "backgroundColor": "rgba(13, 110, 253, 0.95)"}
)

app.layout = dbc.Container([
    dcc.Location(id="app-url", refresh=False), 
    dcc.Store(id='server-side-data-key', storage_type='session'), 
    dcc.Store(id='active-connection-string', storage_type='session'),
    dcc.Store(id='active-connection-name', storage_type='session'),
    dcc.Store(id='active-table-name', storage_type='session'), 
    dcc.Store(id='data-source-type', storage_type='session'), 
    
    html.Div(id="debug-data-key-display", style={'display':'none'}), # Para depurar a chave
    
    navbar,
    dbc.Container(id="page-content", fluid=True, className="flex-grow-1 pb-4"), 
    dbc.Toast(
        id="app-toast", header="Notificação", is_open=False, dismissable=True, icon="info", duration=5000, 
        style={"position": "fixed", "bottom": "20px", "right": "20px", "width": "350px", "zIndex": "9999" },
    ),
    html.Footer(
        dbc.Container(html.P("© 2025 DataMindVV- Plataforma Analítica Integrada", className="text-center text-muted small py-3"), fluid=True),
        className="mt-auto bg-light border-top" 
    )
], fluid=True, className="d-flex flex-column min-vh-100 bg-light")

@app.callback(
    Output("debug-data-key-display", "children"),
    Input("server-side-data-key", "data")
)
def display_current_data_key_for_debug(data_key):
    log_debug("Server-side data key atualizada", extra={"data_key": data_key})
    return f"Current data key in dcc.Store: {data_key}"


@app.callback(Output("page-content", "children"), Input("app-url", "pathname"))
def display_page(pathname):
    log_info("Navegação de página", extra={"page_path": pathname})
    if pathname == "/database": return database.layout
    elif pathname == "/upload": return upload.layout
    elif pathname == "/transform": return transform.layout 
    elif pathname == "/data-join": return data_join.layout 
    elif pathname == "/visualizations": return visualizations.layout
    elif pathname == "/analytics": return analytics.layout
    elif pathname == "/forecasting": return forecasting.layout 
    elif pathname == "/ai-chat": return ai_chat.layout
    elif pathname == "/dashboard": return dashboard.layout
    elif pathname == "/": 
        home_content = html.Div([
            # Hero Section
            html.Div([
                dbc.Container([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H1([
                                    html.Span("DataMindVV", className="text-gradient fw-bold"),
                                    html.Br(),
                                    html.Small("Plataforma Analítica Integrada", className="text-muted")
                                ], className="display-3 mb-4 fade-in"),
                                html.P(
                                    "Transforme seus dados em insights poderosos com nossa plataforma completa de analytics e IA.",
                                    className="lead fs-4 mb-4 fade-in"
                                ),
                                html.Div([
                                    dbc.Button([
                                        html.I(className="fas fa-play me-2"),
                                        "Começar Agora"
                                    ], color="primary", size="lg", href="/upload", 
                                    className="me-3 mb-2 hover-lift"),
                                    dbc.Button([
                                        html.I(className="fas fa-tachometer-alt me-2"),
                                        "Ver Dashboard"
                                    ], color="outline-primary", size="lg", href="/dashboard",
                                    className="mb-2 hover-lift")
                                ], className="mb-4 fade-in")
                            ], className="text-center py-5")
                        ], md=8, className="mx-auto")
                    ])
                ], fluid=True)
            ], className="bg-gradient-primary text-white py-5 mb-5", 
            style={"background": "linear-gradient(135deg, #0d6efd 0%, #6610f2 100%)"}),
            
            # Features Section
            dbc.Container([
                html.H2("Recursos Principais", className="text-center mb-5 text-gradient"),
                dbc.Row([
                    # Conectar Dados
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-database fa-3x text-primary mb-3"),
                                    html.H4("Conectar Dados", className="card-title"),
                                    html.P("Conecte-se a bancos de dados ou faça upload de arquivos CSV, Excel e mais.", 
                                          className="card-text"),
                                    dbc.Button("Explorar", color="primary", href="/database", className="hover-lift")
                                ], className="text-center")
                            ])
                        ], className="h-100 hover-lift shadow-sm")
                    ], md=4, className="mb-4"),
                    
                    # Transformar
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-exchange-alt fa-3x text-success mb-3"),
                                    html.H4("Transformar", className="card-title"),
                                    html.P("Limpe, transforme e prepare seus dados para análise com ferramentas intuitivas.", 
                                          className="card-text"),
                                    dbc.Button("Transformar", color="success", href="/transform", className="hover-lift")
                                ], className="text-center")
                            ])
                        ], className="h-100 hover-lift shadow-sm")
                    ], md=4, className="mb-4"),
                    
                    # Visualizar
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-chart-pie fa-3x text-warning mb-3"),
                                    html.H4("Visualizar", className="card-title"),
                                    html.P("Crie gráficos interativos e dashboards profissionais para seus dados.", 
                                          className="card-text"),
                                    dbc.Button("Visualizar", color="warning", href="/visualizations", className="hover-lift")
                                ], className="text-center")
                            ])
                        ], className="h-100 hover-lift shadow-sm")
                    ], md=4, className="mb-4")
                ]),
                
                # AI Features
                html.Hr(className="my-5"),
                html.H2("Recursos de Inteligência Artificial", className="text-center mb-5 text-gradient"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-robot fa-3x text-info mb-3"),
                                    html.H4("Chat com IA", className="card-title"),
                                    html.P("Converse com seus dados usando linguagem natural e obtenha insights instantâneos.", 
                                          className="card-text"),
                                    dbc.Button("Conversar", color="info", href="/ai-chat", className="hover-lift")
                                ], className="text-center")
                            ])
                        ], className="h-100 hover-lift shadow-sm")
                    ], md=6, className="mb-4"),
                    
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-crystal-ball fa-3x text-purple mb-3"),
                                    html.H4("Previsões", className="card-title"),
                                    html.P("Use machine learning para prever tendências e padrões futuros em seus dados.", 
                                          className="card-text"),
                                    dbc.Button("Prever", color="secondary", href="/forecasting", className="hover-lift")
                                ], className="text-center")
                            ])
                        ], className="h-100 hover-lift shadow-sm")
                    ], md=6, className="mb-4")
                ])
            ], className="mb-5"),
            
            # Quick Start Section
            html.Div([
                dbc.Container([
                    dbc.Row([
                        dbc.Col([
                            html.H3("Comece em 3 Passos Simples", className="text-center mb-4 text-white"),
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.Div("1", className="badge bg-white text-primary fs-3 rounded-circle p-3 mb-3"),
                                        html.H5("Conecte", className="text-white"),
                                        html.P("Carregue seus dados", className="text-white-50")
                                    ], className="text-center")
                                ], md=4),
                                dbc.Col([
                                    html.Div([
                                        html.Div("2", className="badge bg-white text-primary fs-3 rounded-circle p-3 mb-3"),
                                        html.H5("Explore", className="text-white"),
                                        html.P("Analise e visualize", className="text-white-50")
                                    ], className="text-center")
                                ], md=4),
                                dbc.Col([
                                    html.Div([
                                        html.Div("3", className="badge bg-white text-primary fs-3 rounded-circle p-3 mb-3"),
                                        html.H5("Insights", className="text-white"),
                                        html.P("Tome decisões", className="text-white-50")
                                    ], className="text-center")
                                ], md=4)
                            ])
                        ], md=10, className="mx-auto")
                    ])
                ])
            ], className="bg-dark py-5")
        ], className="fade-in") 
        return home_content
    else:
        return dbc.Alert([
            html.H4("Erro 404: Página Não Encontrada!", className="alert-heading"),
            html.P(f"O caminho '{pathname}' não foi encontrado."), html.Hr(),
            html.P(dbc.Button("Voltar para Home", href="/", color="primary", outline=True), className="mb-0")
        ], color="danger", className="m-5 text-center p-4")

@app.callback(
    Output("data-loaded-status-badge", "children"), Output("data-loaded-status-badge", "color"),
    Output("data-loaded-status-badge", "text_color"), 
    Input("server-side-data-key", "data"), 
    State("active-connection-name", "data"), State("active-table-name", "data"), 
    State("data-source-type", "data")
)
def update_data_loaded_status(data_key, conn_name, table_name, source_type):
    log_debug("Atualizando status de dados carregados", extra={"data_key": data_key, "conn_name": conn_name, "table_name": table_name, "source_type": source_type})
    if data_key:
        # Definir a chave de dados ativa no cache
        cache._cache.set_active_data_key(data_key)
        
        df_from_cache = cache.get(data_key)
        
        if df_from_cache is not None and isinstance(df_from_cache, pd.DataFrame): # pd está definido agora
            try:
                num_rows = len(df_from_cache)
                num_cols = len(df_from_cache.columns)
                status_text = f"{num_rows:,} Linhas, {num_cols:,} Col."
                if source_type == 'database' and conn_name and table_name: status_text += f": {conn_name} ({table_name})"
                elif source_type == 'upload' and table_name: status_text += f": {table_name}"
                elif table_name: status_text += f" (Origem: {table_name})"
                log_info("Status de dados atualizado com sucesso", extra={"status_text": status_text, "num_rows": num_rows, "num_cols": num_cols})
                return status_text, "success", "white" 
            except Exception as e:
                log_error("Erro ao atualizar badge de status", extra={"error": str(e), "data_key": data_key}, exc_info=True)
                return "Dados Carregados (erro ao processar)", "warning", "dark"
        else: 
            log_warning("Dados não encontrados no cache", extra={"data_key": data_key})
            return "Dados não disponíveis (cache)", "warning", "dark" 
    else:
        # Limpar a chave de dados ativa quando não há dados
        cache._cache.set_active_data_key(None)
            
    log_debug("Nenhuma chave de dados no store")
    return "Nenhum Dado Carregado", "secondary", "white"

# Registrar Callbacks 
# Assegurar que todos os módulos de página tenham suas funções register_callbacks aceitando os argumentos corretos
database.register_callbacks(app, db_manager, config_manager, query_manager, cache)
upload.register_callbacks(app, cache) 
transform.register_callbacks(app, cache) 
visualizations.register_callbacks(app, cache) 
analytics.register_callbacks(app, cache)   
forecasting.register_callbacks(app, cache) 
dashboard.register_callbacks(app, cache)   
data_join.register_callbacks(app, cache, db_manager, config_manager) 
ai_chat.register_callbacks(app, cache)

if __name__ == "__main__":
    use_reloader_flag = True # Padrão para desenvolvimento
    if CACHE_CONFIG['CACHE_TYPE'] == 'simple':
        log_warning("Usando SimpleCache - reloader desabilitado para consistência do cache")
        use_reloader_flag = False
    
    log_info("Iniciando aplicação Dash", extra={"host": "0.0.0.0", "port": 8050, "debug": True, "use_reloader": use_reloader_flag})
    app.run(debug=True, host="0.0.0.0", port=8050, use_reloader=use_reloader_flag)