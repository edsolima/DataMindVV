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

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Plataforma Analítica de BI Avançada"
)
app.server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 

# Configurar Cache com caminho absoluto
project_root = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(project_root, 'cache-directory')

# Tentar criar o diretório de cache se ele não existir
if not os.path.exists(cache_dir):
    try:
        os.makedirs(cache_dir)
        print(f"Diretório de cache criado em: {cache_dir}")
    except OSError as e:
        print(f"ALERTA: Erro ao criar diretório de cache '{cache_dir}': {e}. Verifique as permissões.")
        print("AVISO: O cache em FileSystem pode não funcionar. A aplicação tentará continuar.")
        # Poderia definir um CACHE_TYPE='simple' como fallback aqui se desejado,
        # mas isso mudaria o comportamento esperado de persistência.

CACHE_CONFIG = {
    #'CACHE_TYPE': 'simple', # MANTENHA 'simple' PARA TESTES ATUAIS
    'CACHE_TYPE': 'filesystem', # DESCOMENTE PARA USAR FILESYSTEM
    'CACHE_DIR': cache_dir, 
    'CACHE_THRESHOLD': 500  
}
cache = Cache(app.server, config=CACHE_CONFIG) 
print(f"Cache inicializado. Tipo: {CACHE_CONFIG['CACHE_TYPE']}{', Diretório: ' + cache_dir if CACHE_CONFIG['CACHE_TYPE'] == 'filesystem' else ''}")


config_manager = ConfigManager()
db_manager = DatabaseManager()
query_manager = QueryManager()

navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-database me-1"), "Dados"], href="/database", id="nav-database")),
        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-upload me-1"), "Upload"], href="/upload", id="nav-upload")),
        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-exchange-alt me-1"), "Transformar"], href="/transform", id="nav-transform")),
        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-link me-1"), "Combinar Dados"], href="/data-join", id="nav-join")),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Criar Gráficos", href="/visualizations", id="nav-viz"),
                dbc.DropdownMenuItem("Análises Detalhadas", href="/analytics", id="nav-analytics"),
                dbc.DropdownMenuItem("Previsões (IA)", href="/forecasting", id="nav-forecast"), 
                dbc.DropdownMenuItem("Chat com Dados (IA)", href="/ai-chat", id="nav-ai-chat"),
            ],
            nav=True, in_navbar=True, label=[html.I(className="fas fa-chart-bar me-1"), "Explorar & IA"],
        ),
        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-tachometer-alt me-1"), "Dashboard"], href="/dashboard", id="nav-dashboard")),
        dbc.NavItem(
            dbc.Badge("Nenhum dado carregado", id="data-loaded-status-badge", color="secondary", text_color="white", 
                      className="ms-3 p-2 align-middle", pill=True),
            className="d-flex align-items-center" 
        )
    ],
    brand=[html.I(className="fas fa-brain me-2"),"Plataforma Analítica Integrada"],
    brand_href="/", color="primary", dark=True, fluid=True, sticky="top", className="mb-4 shadow-sm" 
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
    # print(f"APP.PY - DEBUG: server-side-data-key foi ATUALIZADA para: {data_key}") # Log já estava aqui, pode ser útil
    return f"Current data key in dcc.Store: {data_key}"


@app.callback(Output("page-content", "children"), Input("app-url", "pathname"))
def display_page(pathname):
    # print(f"APP.PY - display_page: Navegando para {pathname}") # DEBUG
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
            html.Div([
                html.H1(className="display-3 fw-bold", children=[html.I(className="fas fa-rocket me-2"), " Plataforma Analítica Integrada!"]),
                html.P("Conecte, transforme, analise, visualize e preveja seus dados.", className="lead fs-4"),
                html.Hr(className="my-4"),
                html.P("Comece sua jornada de descoberta de dados:", className="mb-4"),
                html.Div([
                    dbc.Button([html.I(className="fas fa-database me-2"),"Dados & SQL"],color="primary",size="lg",href="/database",className="me-md-3 mb-2 mb-md-0"),
                    dbc.Button([html.I(className="fas fa-upload me-2"),"Upload de Arquivos"],color="success",size="lg",href="/upload",className="me-md-3 mb-2 mb-md-0"),
                    dbc.Button([html.I(className="fas fa-exchange-alt me-2"),"Transformar Dados"],color="info",size="lg",href="/transform",className="me-md-3 mb-2 mb-md-0"),
                    dbc.Button([html.I(className="fas fa-link me-2"),"Combinar Dados"],color="purple",size="lg",href="/data-join",className="me-md-3 mb-2 mb-md-0"), 
                    dbc.Button([html.I(className="fas fa-chart-pie me-2"),"Explorar Dados"],color="warning",size="lg",href="/visualizations"),
                ], className="d-grid gap-2 d-md-flex justify-content-md-start flex-wrap")
            ], className="container-fluid py-5 text-center") 
        ], className="p-5 mb-4 bg-white rounded-3 shadow") 
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
    # print(f"APP.PY - update_data_loaded_status: TRIGGERED. data_key = {data_key}") 
    if data_key:
        # print(f"APP.PY - update_data_loaded_status: Verificando cache.has('{data_key}') = {cache.has(data_key)}")
        df_from_cache = cache.get(data_key) 
        # print(f"APP.PY - update_data_loaded_status: df_from_cache é None? {df_from_cache is None}. Tipo: {type(df_from_cache)}")
        
        if df_from_cache is not None and isinstance(df_from_cache, pd.DataFrame): # pd está definido agora
            try:
                num_rows = len(df_from_cache)
                num_cols = len(df_from_cache.columns)
                status_text = f"{num_rows:,} Linhas, {num_cols:,} Col."
                if source_type == 'database' and conn_name and table_name: status_text += f": {conn_name} ({table_name})"
                elif source_type == 'upload' and table_name: status_text += f": {table_name}"
                elif table_name: status_text += f" (Origem: {table_name})"
                # print(f"APP.PY - update_data_loaded_status: SUCESSO. Status: {status_text}")
                return status_text, "success", "white" 
            except Exception as e:
                print(f"APP.PY - Error updating status badge (processando df do cache): {e}")
                return "Dados Carregados (erro ao processar)", "warning", "dark"
        else: 
            # print(f"APP.PY - Status badge: data_key '{data_key}' ENCONTRADA NO DCC.STORE, mas os dados NÃO ESTÃO NO CACHE DO SERVIDOR ou são inválidos.")
            return "Dados não disponíveis (cache)", "warning", "dark" 
            
    # print(f"APP.PY - update_data_loaded_status: NENHUM data_key no dcc.Store.")
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
        print("AVISO: Usando SimpleCache. Para consistência do cache durante o teste, o reloader será desabilitado.")
        use_reloader_flag = False
    
    app.run(debug=True, host="0.0.0.0", port=8050, use_reloader=use_reloader_flag)