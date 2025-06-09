# pages/database.py
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table, ALL 
import dash_bootstrap_components as dbc
import pandas as pd
import json
from datetime import datetime 
import uuid
from utils.logger import log_info, log_error, log_warning, log_debug

cache = None # Será definido em register_callbacks
db_manager = None
config_manager = None
query_manager = None

# Layout (mesmo da última versão, com "database-page-loaded-signal")
layout = dbc.Container([
    html.Div(id="database-page-loaded-signal", style={'display': 'none'}), 
    dbc.Row([
        dbc.Col([
            html.H2([html.I(className="fas fa-database me-2"), "Conexões de Banco de Dados & Editor SQL"], className="mb-4 text-primary"),
            dbc.Tabs([
                dbc.Tab(label="Gerenciar Conexões", tab_id="tab-connections", children=[
                    dbc.Row([
                        dbc.Col(md=5, children=[
                            dbc.Card([
                                dbc.CardHeader(html.H5([html.I(className="fas fa-plug me-2"), "Nova Conexão / Editar"], className="mb-0")),
                                dbc.CardBody([
                                    dbc.Input(id="db-original-connection-name", type="hidden"), 
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Nome da Conexão*", html_for="db-connection-name", className="fw-bold small"),
                                            dbc.Input(id="db-connection-name", placeholder="Ex: Meu PostgreSQL Local", required=True)
                                        ], md=12, className="mb-2"),
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Label("Tipo de Banco*", html_for="db-type", className="fw-bold small"),
                                            dcc.Dropdown(
                                                id="db-type",
                                                options=[
                                                    {"label": "PostgreSQL", "value": "postgresql"},
                                                    {"label": "SQL Server", "value": "sqlserver"},
                                                    {"label": "MySQL", "value": "mysql"},
                                                    {"label": "SQLite (caminho do arquivo)", "value": "sqlite"},
                                                ],
                                                value="postgresql", clearable=False
                                            )
                                        ], md=12, className="mb-2"),
                                    ]),
                                    dbc.Row([
                                        dbc.Col(md=8, children=[dbc.Label("Host*", html_for="db-host", className="fw-bold small"), dbc.Input(id="db-host", placeholder="localhost ou /path/to/db.sqlite")]),
                                        dbc.Col(md=4, children=[dbc.Label("Porta", html_for="db-port", className="fw-bold small"), dbc.Input(id="db-port", type="number", placeholder="5432")]),
                                    ], className="mb-2"),
                                    dbc.Row([
                                        dbc.Col(md=6, children=[dbc.Label("Nome do Banco*", html_for="db-database", className="fw-bold small"), dbc.Input(id="db-database", placeholder="mydatabase")]),
                                        dbc.Col(md=6, children=[dbc.Label("Usuário*", html_for="db-username", className="fw-bold small"), dbc.Input(id="db-username", placeholder="user")]),
                                    ], className="mb-2"),
                                    dbc.Row([
                                        dbc.Col(md=6, children=[dbc.Label("Senha*", html_for="db-password", className="fw-bold small"), dbc.Input(id="db-password", type="password", placeholder="••••••••")]),
                                        dbc.Col(md=6, children=[dbc.Label("Schema (Opcional)", html_for="db-schema", className="fw-bold small"), dbc.Input(id="db-schema", placeholder="public (PostgreSQL), dbo (SQL Server)")]),
                                    ], className="mb-2"),
                                    html.Div(id='sqlserver-specific-options', children=[
                                        dbc.Row([
                                            dbc.Col(md=8, children=[dbc.Label("Driver ODBC (SQL Server)", html_for="db-driver-sqlserver", className="fw-bold small"), dbc.Input(id="db-driver-sqlserver", value="ODBC Driver 17 for SQL Server")]),
                                            dbc.Col(md=4, className="d-flex align-items-end pb-2", children=[dbc.Checkbox(id="db-trust-cert-sqlserver", label="Trust Cert?")]),
                                        ], className="mb-2")
                                    ], style={'display': 'none'}),
                                    html.Hr(),
                                    dbc.Row([
                                        dbc.Col(dbc.Button([html.I(className="fas fa-network-wired me-1"),"Testar Conexão"], id="test-connection-btn", color="info", className="w-100 mb-2", n_clicks=0), width=12),
                                        dbc.Col(dbc.Button([html.I(className="fas fa-save me-1"),"Salvar Conexão"], id="save-connection-btn", color="primary", className="w-100", n_clicks=0), width=12),
                                    ]),
                                    html.Div(id="connection-feedback-output", className="mt-3"),
                                ])
                            ], className="mb-4 shadow-sm"),
                        ]),
                        dbc.Col(md=7, children=[
                            dbc.Card([
                                dbc.CardHeader(html.H5([html.I(className="fas fa-list-ul me-2"), "Conexões Salvas"], className="mb-0")),
                                dbc.CardBody(
                                    dcc.Loading(
                                        id="loading-saved-connections", type="default",
                                        children=html.Div(id="saved-connections-list-display-area") 
                                    )
                                ),
                            ], className="shadow-sm"),
                        ]),
                    ]),
                ]), 
                dbc.Tab(label="Explorar Dados & SQL", tab_id="tab-explore", children=[
                    dbc.Row([
                        dbc.Col(md=4, children=[
                            dbc.Card([
                                dbc.CardHeader(html.H5([html.I(className="fas fa-search-location me-2"),"Selecionar Dados"], className="mb-0")),
                                dbc.CardBody([
                                    dbc.Label("Conexão Ativa:", html_for="active-connection-dropdown", className="fw-bold small"),
                                    dcc.Dropdown(id="active-connection-dropdown", placeholder="Selecione uma conexão salva...", className="mb-2"),
                                    dbc.Button([html.I(className="fas fa-plug me-1"), "Conectar & Listar Tabelas"], id="connect-db-btn", color="success", className="w-100 mb-3", disabled=True, n_clicks=0),
                                    html.Div(id="connect-db-feedback", className="mt-2 small"),
                                    html.Hr(),
                                    dbc.Label("Selecionar Tabela:", html_for="db-table-dropdown", className="fw-bold small"),
                                    dcc.Dropdown(id="db-table-dropdown", placeholder="Selecione uma tabela...", className="mb-2", disabled=True),
                                    dbc.Label("Tamanho da Amostra:", html_for="db-sample-size", className="fw-bold small"),
                                    dbc.Input(id="db-sample-size", type="number", value=100, min=1, step=10, className="mb-3"),
                                    dbc.Row([
                                        dbc.Col(dbc.Button([html.I(className="fas fa-table me-1"), "Carregar Amostra"], id="load-table-sample-btn", color="primary", className="w-100 mb-2", disabled=True, n_clicks=0)),
                                        dbc.Col(dbc.Button([html.I(className="fas fa-eye me-1"), "Ver Schema"], id="show-table-schema-btn", color="secondary", className="w-100 mb-2", disabled=True, n_clicks=0)),
                                    ]),
                                ])
                            ], className="mb-4 shadow-sm sticky-top", style={"top": "80px"}),
                        ]),
                        dbc.Col(md=8, children=[
                            dbc.Card([
                                dbc.CardHeader(html.H5([html.I(className="fas fa-code me-2"),"Editor SQL"], className="mb-0")),
                                dbc.CardBody([
                                    dbc.Row([
                                        dbc.Col(md=6, children=[
                                            dbc.Label("Queries Padrão:", html_for="standard-query-dropdown", className="fw-bold small"),
                                            dcc.Dropdown(id="standard-query-dropdown", placeholder="Carregar query padrão...", clearable=True, className="mb-2")
                                        ]),
                                        dbc.Col(md=6, children=[
                                            dbc.Label("Queries Salvas:", html_for="saved-query-dropdown", className="fw-bold small"),
                                            dcc.Dropdown(id="saved-query-dropdown", placeholder="Carregar query salva...", clearable=True, className="mb-2")
                                        ]),
                                    ]),
                                    html.Div([
                                        dbc.Row([
                                            dbc.Col([
                                                dbc.Button([html.I(className="fas fa-expand me-1"), "Expandir Editor"], id="expand-sql-editor-btn", color="outline-secondary", size="sm", className="mb-2")
                                            ], width="auto"),
                                            dbc.Col([
                                                dbc.Button([html.I(className="fas fa-magic me-1"), "Formatar SQL"], id="format-sql-btn", color="outline-info", size="sm", className="mb-2")
                                            ], width="auto"),
                                            dbc.Col([
                                                dbc.Button([html.I(className="fas fa-history me-1"), "Histórico"], id="sql-history-btn", color="outline-warning", size="sm", className="mb-2")
                                            ], width="auto")
                                        ], className="mb-2")
                                    ]),
                                    dbc.Textarea(id="sql-query-input", placeholder="SELECT * FROM sua_tabela WHERE condicao = 'valor';\n-- Lembre-se de usar LIMIT para queries em tabelas grandes!\n-- Use Ctrl+Enter para executar rapidamente", rows=8, className="mb-2 form-control-sm", style={'fontFamily': 'Consolas, Monaco, monospace', 'fontSize':'0.9em', 'lineHeight': '1.4'}),
                                    dbc.Row([
                                        dbc.Col(md=7, children=[dbc.Input(id="save-query-name", placeholder="Nome para salvar a query (ex: Vendas Trimestrais)")]),
                                        dbc.Col(md=5, children=[dbc.Button([html.I(className="fas fa-save me-1"), "Salvar Query"], id="save-query-btn", color="info", className="w-100", n_clicks=0)]),
                                    ], className="mb-2"),
                                    dbc.Input(id="save-query-description", placeholder="Descrição (opcional)", className="mb-2 form-control-sm"),
                                    dbc.Button([html.I(className="fas fa-play me-1"), "Executar Query"], id="execute-query-btn", color="success", className="w-100 mb-2", disabled=True, n_clicks=0),
                                    html.Div(id="sql-editor-feedback", className="mt-2 small"),
                                    html.Div(id="saved-queries-management-area", className="mt-3") 
                                ])
                            ], className="mb-4 shadow-sm"),
                            dbc.Card([
                                dbc.CardHeader(html.H5([html.I(className="fas fa-border-all me-2"), "Preview dos Dados / Resultados da Query"], className="mb-0")),
                                dbc.CardBody([
                                    dbc.Row([
                                        dbc.Col(html.Div(id="data-preview-header"), width=9),
                                        dbc.Col(html.Button([html.I(className="fas fa-download me-1"), "Download CSV"], id="download-data-btn", className="btn btn-warning float-end", style={'display': 'none'}, n_clicks=0), width=3, className="d-flex justify-content-end")
                                    ], align="center", className="mb-2"),
                                    dcc.Download(id="download-dataframe-csv"),
                                    dcc.Loading(type="default", children=html.Div(id="data-preview-area", className="mt-2 table-responsive", style={"maxHeight": "400px", "overflowY": "auto"})),
                                    dcc.Loading(type="default", children=html.Div(id="table-schema-area", className="mt-3 table-responsive"))
                                ])
                            ], className="shadow-sm"),
                        ]),
                    ]),
                ]), 
            ]) 
        ])
    ])
], fluid=True)

def render_saved_connections(config_mngr): # Renomeado para clareza
    connections = config_mngr.list_connections()
    if not connections:
        return dbc.Alert("Nenhuma conexão salva ainda. Crie uma no formulário ao lado.", color="info", className="mt-2 text-center") 
    items = []
    for conn_name in connections:
        conn_details = config_mngr.get_connection(conn_name) 
        db_type = conn_details.get('type', 'N/A') if conn_details else 'N/A'
        host = conn_details.get('host', 'N/A') if conn_details else 'N/A'
        database_name = conn_details.get('database', 'N/A') if conn_details else 'N/A'
        items.append(dbc.ListGroupItem([
            dbc.Row([
                dbc.Col([
                    html.Strong(conn_name), html.Br(),
                    html.Small(f"Tipo: {db_type}, Host: {host}, DB: {database_name}", className="text-muted")
                ], width=7, md=8, style={"overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"}),
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button(html.I(className="fas fa-edit"), id={"type": "edit-connection-btn", "index": conn_name}, size="sm", color="light", title="Editar", className="me-1", n_clicks=0),
                        dbc.Button(html.I(className="fas fa-trash-alt"), id={"type": "delete-connection-btn", "index": conn_name}, size="sm", color="danger", title="Deletar", className="me-1", n_clicks=0),
                        dbc.Button(html.I(className="fas fa-plug"), id={"type": "select-as-active-conn-btn", "index": conn_name}, size="sm", color="success", title="Selecionar como ativa", n_clicks=0),
                    ], className="float-end")
                ], width=5, md=4)
            ], align="center")
        ], action=True, id={"type": "list-group-item-conn", "index": conn_name}))
    return dbc.ListGroup(items, flush=True)

def render_saved_queries(query_mngr): # Renomeado para clareza
    queries = query_mngr.load_queries()
    if not queries: return dbc.Alert("Nenhuma query SQL salva.", color="info", className="mt-2")
    items = []
    for q_name, q_data in queries.items():
        items.append(dbc.ListGroupItem([
            dbc.Row([
                dbc.Col([
                    html.Strong(q_name), html.Br(),
                    html.Small(q_data.get('description', "Sem descrição."), className="text-muted")
                ], width=7, md=8, style={"overflow":"hidden", "textOverflow":"ellipsis", "whiteSpace":"nowrap"}),
                dbc.Col(dbc.ButtonGroup([
                    dbc.Button(html.I(className="fas fa-upload"), id={"type":"load-saved-query-from-list-btn","index":q_name},color="light",size="sm",title="Carregar",className="me-1", n_clicks=0),
                    dbc.Button(html.I(className="fas fa-trash-alt"),id={"type":"delete-saved-query-from-list-btn","index":q_name},color="danger",size="sm",title="Deletar", n_clicks=0)
                ],className="float-end"),width=5, md=4)
            ], align="center")
        ]))
    return dbc.ListGroup(items, flush=True, className="mt-2")

def register_callbacks(app, db_manager_instance, config_manager_instance, query_manager_instance, cache_instance): # Nomes completos para clareza
    global cache, db_manager, config_manager, query_manager
    cache = cache_instance
    db_manager = db_manager_instance
    config_manager = config_manager_instance
    query_manager = query_manager_instance

    @app.callback(
        Output("saved-connections-list-display-area", "children"),
        Output("active-connection-dropdown", "options"), 
        Input("database-page-loaded-signal", "children") 
    )
    def load_initial_connections_list(_): 
        connections = config_manager.list_connections()
        dropdown_options = [{"label": c, "value": c} for c in connections]
        return render_saved_connections(config_manager), dropdown_options

    @app.callback(Output("sqlserver-specific-options", "style"), Input("db-type", "value"))
    def toggle_sqlserver_options(db_type):
        return {'display': 'block'} if db_type == 'sqlserver' else {'display': 'none'}

    @app.callback(
        Output("connection-feedback-output", "children"),
        Input("test-connection-btn", "n_clicks"),
        State("db-type", "value"), State("db-host", "value"), State("db-port", "value"), 
        State("db-database", "value"), State("db-username", "value"), State("db-password", "value"),
        State("db-driver-sqlserver", "value"), State("db-trust-cert-sqlserver", "checked"),
        prevent_initial_call=True
    )
    def test_connection_callback(n_clicks, db_type, host, port, db, user, pwd, driver, trust_cert):
        if not n_clicks or n_clicks == 0: return dash.no_update
        
        log_info("Testando conexão de banco de dados", extra={
            "db_type": db_type, 
            "host": host, 
            "port": port, 
            "database": db,
            "username": user
        })
        
        data = {'type':db_type,'host':host,'port':port,'database':db,'username':user,'password':pwd}
        if db_type == 'sqlserver': data.update({'driver':driver,'trust_server_certificate':trust_cert})
        
        ok, msg = config_manager.test_connection_config(data)
        
        if ok:
            log_info("Teste de conexão bem-sucedido", extra={"connection_name": f"{db_type}://{host}:{port}/{db}"})
        else:
            log_warning("Teste de conexão falhou", extra={"error_message": msg, "db_type": db_type})
        
        color, icon = ("success","check-circle") if ok else ("danger","times-circle")
        return dbc.Alert([html.I(className=f"fas fa-{icon} me-1"),msg],color=color,dismissable=True, duration=4000)

    @app.callback(
        Output("connection-feedback-output", "children", allow_duplicate=True),      
        Output("saved-connections-list-display-area", "children", allow_duplicate=True), 
        Output("active-connection-dropdown", "options", allow_duplicate=True),      
        Output("db-connection-name", "value"), Output("db-type", "value"), Output("db-host", "value"), 
        Output("db-port", "value"), Output("db-database", "value"), Output("db-username", "value"),
        Output("db-password", "value"), Output("db-schema", "value"), Output("db-driver-sqlserver", "value"), 
        Output("db-trust-cert-sqlserver", "checked"), Output("db-original-connection-name", "value"), 
        Output("app-toast", "is_open", allow_duplicate=True), Output("app-toast", "children", allow_duplicate=True),
        Output("app-toast", "header", allow_duplicate=True), Output("app-toast", "icon", allow_duplicate=True),                          
        Input("save-connection-btn", "n_clicks"),
        State("db-original-connection-name","value"), State("db-connection-name","value"), 
        State("db-type","value"), State("db-host","value"), State("db-port","value"), 
        State("db-database","value"), State("db-username","value"), State("db-password","value"), 
        State("db-schema","value"), State("db-driver-sqlserver","value"), 
        State("db-trust-cert-sqlserver","checked"),
        prevent_initial_call=True
    )
    def save_connection_callback(n_clicks, og_name, name, db_type, host, port, db, user, pwd, schema, driver, trust_cert):
        if not n_clicks or n_clicks == 0 or not name: 
            num_outputs_before_toast = 14 
            return ([dash.no_update] * num_outputs_before_toast) + [False, "", "", ""]
        
        log_info("Salvando configuração de conexão", extra={
            "connection_name": name,
            "db_type": db_type,
            "host": host,
            "database": db,
            "is_edit": bool(og_name and og_name != name)
        })
            
        data = {'type':db_type,'host':host,'port':port,'database':db,'username':user,'password':pwd,'schema':schema or None}
        if db_type == 'sqlserver': data.update({'driver':driver,'trust_server_certificate':trust_cert})
        if og_name and og_name != name: 
            config_manager.delete_connection(og_name)
            log_info("Conexão anterior removida durante edição", extra={"old_name": og_name, "new_name": name})
        
        ok = config_manager.save_connection(name, data)
        
        if ok:
            log_info("Conexão salva com sucesso", extra={"connection_name": name})
        else:
            log_error("Falha ao salvar conexão", extra={"connection_name": name})
        
        msg,color,icon = (f"Conexão '{name}' salva!", "success", "check-circle") if ok else (f"Falha ao salvar '{name}'.", "danger", "times-circle")
        form_reset_values = ("", "postgresql","",None,"","","","","ODBC Driver 17 for SQL Server",False,"")
        connections_list = config_manager.list_connections()
        dropdown_opts_updated = [{"label": c, "value": c} for c in connections_list]
        return dbc.Alert([html.I(className=f"fas fa-{icon} me-1"),msg],color=color,dismissable=True, duration=4000), \
               render_saved_connections(config_manager), dropdown_opts_updated, *form_reset_values, \
               True, msg, "Salvar Conexão", color

    @app.callback(
        Output("saved-connections-list-display-area", "children", allow_duplicate=True),
        Output("active-connection-dropdown", "options", allow_duplicate=True), 
        Output("active-connection-dropdown", "value", allow_duplicate=True),   
        Output("db-connection-name", "value", allow_duplicate=True), Output("db-type", "value", allow_duplicate=True),
        Output("db-host", "value", allow_duplicate=True), Output("db-port", "value", allow_duplicate=True),
        Output("db-database", "value", allow_duplicate=True), Output("db-username", "value", allow_duplicate=True),
        Output("db-password", "value", allow_duplicate=True), Output("db-schema", "value", allow_duplicate=True),
        Output("db-driver-sqlserver", "value", allow_duplicate=True),
        Output("db-trust-cert-sqlserver", "checked", allow_duplicate=True),
        Output("db-original-connection-name", "value", allow_duplicate=True), 
        Output("app-toast", "is_open", allow_duplicate=True), Output("app-toast", "children", allow_duplicate=True),
        Output("app-toast", "header", allow_duplicate=True), Output("app-toast", "icon", allow_duplicate=True),
        Input({'type': 'delete-connection-btn', 'index': ALL}, 'n_clicks'),
        Input({'type': 'edit-connection-btn', 'index': ALL}, 'n_clicks'),
        Input({'type': 'select-as-active-conn-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_saved_connections_actions_buttons(del_clicks_list, edit_clicks_list, select_clicks_list):
        ctx = dash.callback_context
        if not ctx.triggered or not ctx.triggered_id: 
            raise dash.exceptions.PreventUpdate
        triggered_id_dict = ctx.triggered_id 
        toast_open, toast_msg, toast_hdr, toast_icon = False, "", "", ""
        form_vals_list = [dash.no_update] * 11 
        selected_active_conn_val = dash.no_update
        action_taken = False 
        if isinstance(triggered_id_dict, dict):
            action_type, conn_name = triggered_id_dict.get('type'), triggered_id_dict.get('index')
            # A lógica para determinar o botão clicado precisa ser robusta se várias listas de n_clicks são None
            # Vamos assumir que ctx.triggered_id é suficiente para identificar o botão único que foi clicado
            if action_type == 'delete-connection-btn':
                # Checar se o n_clicks correspondente é > 0 (ou não None se começando de 0)
                idx = next((i for i, item_id_dict in enumerate(ctx.inputs_list[0]) if item_id_dict['id'] == triggered_id_dict), -1)
                if idx != -1 and del_clicks_list and del_clicks_list[idx] is not None and del_clicks_list[idx] > 0 : # Verifica se o clique específico é válido
                    log_info("Deletando conexão", extra={"connection_name": conn_name})
                    success = config_manager.delete_connection(conn_name)
                    
                    if success:
                        log_info("Conexão deletada com sucesso", extra={"connection_name": conn_name})
                    else:
                        log_error("Falha ao deletar conexão", extra={"connection_name": conn_name})
                    
                    toast_msg,toast_hdr,toast_icon = (f"'{conn_name}' deletada.","Deletar","success") if success else (f"Falha deletar '{conn_name}'.","Deletar","danger")
                    toast_open=True; action_taken=True
            elif action_type == 'edit-connection-btn':
                idx = next((i for i, item_id_dict in enumerate(ctx.inputs_list[1]) if item_id_dict['id'] == triggered_id_dict), -1)
                if idx != -1 and edit_clicks_list and edit_clicks_list[idx] is not None and edit_clicks_list[idx] > 0:
                    log_info("Carregando conexão para edição", extra={"connection_name": conn_name})
                    data = config_manager.get_connection(conn_name)
                    if data:
                        form_vals_list = [conn_name,data.get('type','postgresql'),data.get('host',''),data.get('port',''),data.get('database',''),data.get('username',''),data.get('password',''),data.get('schema',''),data.get('driver','ODBC Driver 17 for SQL Server'),data.get('trust_server_certificate',False),conn_name]
                        toast_msg,toast_hdr,toast_icon = f"Editando '{conn_name}'.","Editar","info"; toast_open=True; action_taken=True
            elif action_type == 'select-as-active-conn-btn':
                idx = next((i for i, item_id_dict in enumerate(ctx.inputs_list[2]) if item_id_dict['id'] == triggered_id_dict), -1)
                if idx != -1 and select_clicks_list and select_clicks_list[idx] is not None and select_clicks_list[idx] > 0 :
                    log_info("Selecionando conexão como ativa", extra={"connection_name": conn_name})
                    selected_active_conn_val = conn_name
                    toast_msg,toast_hdr,toast_icon = f"'{conn_name}' selecionada.","Ativa","info"; toast_open=True; action_taken=True
        if not action_taken: raise dash.exceptions.PreventUpdate
        conns = config_manager.list_connections()
        dd_opts = [{"label":c,"value":c} for c in conns]
        return render_saved_connections(config_manager), dd_opts, selected_active_conn_val, *form_vals_list, toast_open, toast_msg, toast_hdr, toast_icon

    @app.callback(
        Output("connect-db-feedback", "children"),
        Output("db-table-dropdown", "options"), Output("db-table-dropdown", "value"), 
        Output("db-table-dropdown", "disabled"), Output("load-table-sample-btn", "disabled"),
        Output("show-table-schema-btn", "disabled"), Output("execute-query-btn", "disabled"), 
        Output('active-connection-string', 'data'), 
        Output('active-connection-name', 'data', allow_duplicate=True), 
        Output('data-source-type', 'data', allow_duplicate=True),
        Output('server-side-data-key', 'data', allow_duplicate=True), 
        Output('active-table-name', 'data', allow_duplicate=True), 
        Output("app-toast", "is_open", allow_duplicate=True), Output("app-toast", "children", allow_duplicate=True),
        Output("app-toast", "header", allow_duplicate=True), Output("app-toast", "icon", allow_duplicate=True),
        Input("connect-db-btn", "n_clicks"), State("active-connection-dropdown", "value"),
        prevent_initial_call=True
    )
    def connect_to_db_and_list_tables(n_clicks, selected_conn_name):
        # Retorno para o caso de saída antecipada (16 elementos)
        early_exit_return = ([dash.no_update]*7) + [None, None, None, None, None] + ([False] + [""]*3)
        
        if not n_clicks or n_clicks == 0 or not selected_conn_name:
            return early_exit_return
            
        conn_data = config_manager.get_connection(selected_conn_name)
        if not conn_data:
            msg = f"Detalhes da conexão '{selected_conn_name}' não encontrados."
            return dbc.Alert(msg, color="danger", duration=4000), [], None, True, True, True, True, None, None, None, None, None, True, msg, "Erro", "danger"

        # Valores padrão para retorno em caso de erro
        error_feedback = dbc.Alert(f"Falha ao conectar a '{selected_conn_name}'. Verifique.", color="danger", className="mt-2 small", duration=4000)
        error_toast_msg = f"Falha ao conectar a '{selected_conn_name}'."
        error_return_tuple = (error_feedback, [], None, True, True, True, True, None, None, None, None, None, True, error_toast_msg, "Erro Conexão BD", "danger")

        try:
            conn_string = db_manager.create_connection_string(conn_data) # Pode levantar ValueError
            success_connect = db_manager.connect(conn_string) # Pode levantar exceção ou retornar False
            
            if success_connect:
                tables = db_manager.get_tables(schema=conn_data.get('schema')) # Pode levantar exceção
                table_options = [{"label": str(t), "value": str(t)} for t in tables]
                msg = f"Conectado a '{selected_conn_name}'. {len(tables)} tabelas encontradas."
                return dbc.Alert(msg, color="success", className="mt-2 small", duration=4000), table_options, None, \
                       False, False, False, False, \
                       conn_string, selected_conn_name, 'database', \
                       None, None, True, msg, "Conexão BD", "success"
            else: # db_manager.connect() retornou False
                return error_return_tuple
        except ValueError as ve: # Erro ao criar connection string
            log_error(f"ValueError em connect_to_db_and_list_tables (create_connection_string):", exception=ve)
            msg = f"Erro na configuração da conexão: {str(ve)}"
            return dbc.Alert(msg, color="danger", duration=4000), [], None, True, True, True, True, None, None, None, None, None, True, msg, "Erro de Configuração", "danger"
        except Exception as e: # Outras exceções de db_manager.connect() ou db_manager.get_tables()
            log_error(f"Erro inesperado em connect_to_db_and_list_tables:", exception=e)
            import traceback; traceback.print_exc()
            msg = f"Erro inesperado: {str(e)}"
            return dbc.Alert(msg, color="danger", duration=4000), [], None, True, True, True, True, None, None, None, None, None, True, msg, "Erro Crítico", "danger"


    @app.callback(Output("connect-db-btn", "disabled"), Input("active-connection-dropdown", "value"))
    def toggle_connect_db_btn(val): return not bool(val)

    @app.callback(
        Output("data-preview-area", "children"), Output("data-preview-header", "children"),
        Output("download-data-btn", "style"), 
        Output('server-side-data-key', 'data', allow_duplicate=True), 
        Output('active-table-name', 'data', allow_duplicate=True), 
        Output("app-toast", "is_open", allow_duplicate=True), Output("app-toast", "children", allow_duplicate=True),
        Output("app-toast", "header", allow_duplicate=True), Output("app-toast", "icon", allow_duplicate=True),
        Input("load-table-sample-btn", "n_clicks"),
        State("db-table-dropdown", "value"), State("db-sample-size", "value"),
        State('active-connection-string', 'data'), State('active-connection-name', 'data'), 
        prevent_initial_call=True
    )
    def load_table_sample_callback(n_clicks, table_name, size, conn_str, conn_name):
        if not n_clicks or n_clicks == 0 or not table_name or not conn_str:
            return dash.no_update, dash.no_update, {'display':'none'}, dash.no_update, dash.no_update, False,"","",""
        if not db_manager.engine or db_manager.connection_string != conn_str:
            if not db_manager.connect(conn_str): 
                msg="Falha reconectar"; return dbc.Alert(msg,color="danger",duration=4000),html.H5("Erro"),{'display':'none'},None,None,True,msg,"Erro","danger"
        schema, table = (table_name.split('.',1)+[None])[:2] if '.' in table_name else (None,table_name)
        df = db_manager.get_table_sample(table, schema=schema, sample_size=int(size))
        data_key_to_store = None
        if not df.empty:
            data_key_to_store = str(uuid.uuid4())
            cache.set(data_key_to_store, df, timeout=3600)
            log_info(f"DATABASE_PAGE - Dados salvos no cache com chave: {data_key_to_store}. Cache.has('{data_key_to_store}') = {cache.has(data_key_to_store)}")
            retrieved_df_check = cache.get(data_key_to_store)
            if retrieved_df_check is not None:
                log_info(f"DATABASE_PAGE - Verificação IMEDIATA: DataFrame recuperado do cache. Linhas: {len(retrieved_df_check)}")
            else:
                log_error(f"DATABASE_PAGE - ERRO IMEDIATO: Chave {data_key_to_store} existe no cache ({cache.has(data_key_to_store)}), mas get() retornou None!")
            dt=dash_table.DataTable(data=df.to_dict('records'),columns=[{"name":str(i),"id":str(i)} for i in df.columns],page_size=10,style_table={'overflowX':'auto','maxHeight':'350px','overflowY':'auto','minWidth':'100%'},style_cell={'textAlign':'left','padding':'5px','minWidth':'100px','maxWidth':'200px','whiteSpace':'normal','fontSize':'0.85rem'},style_header={'backgroundColor':'#e9ecef','fontWeight':'bold','borderBottom':'1px solid #dee2e6'},fixed_rows={'headers':True})
            msg=f"{len(df)} linhas de '{table_name}'."; 
            return dt,html.H5(f"Amostra de '{table_name}' ({len(df)} l.):"),{'display':'inline-block'},data_key_to_store,table_name,True,msg,"Amostra","success"
        msg=f"Sem dados em '{table_name}'."; 
        return dbc.Alert(msg,color="warning",duration=4000),html.H5("Sem Dados"),{'display':'none'},None,None,True,msg,"Amostra","warning"

    @app.callback(Output("table-schema-area","children"),Input("show-table-schema-btn","n_clicks"),State("db-table-dropdown","value"),State('active-connection-string','data'),prevent_initial_call=True)
    def show_table_schema_callback(n,tbl,conn_str):
        if not n or n == 0 or not tbl or not conn_str: return dash.no_update
        if not db_manager.engine or db_manager.connection_string!=conn_str:
            if not db_manager.connect(conn_str): return dbc.Alert("Falha reconectar.",color="danger",duration=4000)
        s,t = (tbl.split('.',1)+[None])[:2] if '.' in tbl else (None,tbl)
        df_s = db_manager.get_table_schema(t,schema=s)
        if not df_s.empty: return [html.H5(f"Schema '{tbl}':"),dash_table.DataTable(data=df_s.to_dict('records'),columns=[{"name":str(i),"id":str(i)} for i in df_s.columns],style_cell={'textAlign':'left','fontSize':'0.85rem'},style_header={'backgroundColor':'#e9ecef','fontWeight':'bold'})]
        return dbc.Alert(f"Não foi possível obter schema para '{tbl}'.",color="warning",duration=4000)

    @app.callback(Output("standard-query-dropdown","options"),Output("saved-query-dropdown","options"),Output("saved-queries-management-area","children"),Input("app-url","pathname"),Input("save-query-btn","n_clicks"),Input({"type":"delete-saved-query-from-list-btn","index":ALL},"n_clicks"))
    def update_query_dropdowns_and_list(path,save_n,del_n_list):
        ctx = dash.callback_context
        triggered_by_save = ctx.triggered_id == "save-query-btn"
        triggered_by_delete = isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "delete-saved-query-from-list-btn" and any(c is not None and c > 0 for c in del_n_list)
        if path=="/database" or triggered_by_save or triggered_by_delete:
            std_q,saved_q=query_manager.get_standard_queries(),query_manager.load_queries() or {}
            std_opts=[{"label":f"{n} - {d.get('description', '')[:50] if d.get('description') else ''}","value":n} for n,d in std_q.items()]
            saved_opts=[{"label":f"{n} - {d.get('description', '')[:50] if d.get('description') else ''}","value":n} for n,d in saved_q.items()]
            return std_opts,saved_opts,render_saved_queries(query_manager)
        return dash.no_update,dash.no_update,dash.no_update

    @app.callback(Output("sql-query-input","value"),Output("save-query-name","value",allow_duplicate=True),Output("save-query-description","value",allow_duplicate=True),Input("standard-query-dropdown","value"),Input("saved-query-dropdown","value"),Input({"type":"load-saved-query-from-list-btn","index":ALL},"n_clicks"),State("db-table-dropdown","value"),prevent_initial_call=True)
    def load_query_into_editor(std_q,saved_q,list_load_clicks,sel_tbl):
        ctx=dash.callback_context;
        if not ctx.triggered: return dash.no_update
        triggered_prop_id = ctx.triggered[0]['prop_id']
        q_txt,q_name_save,q_desc_save = "",dash.no_update,dash.no_update
        if isinstance(triggered_prop_id, str): 
            if triggered_prop_id.startswith("standard-query-dropdown.") and std_q:
                data=query_manager.get_standard_queries().get(std_q)
                if data:
                    q_txt=data['query']
                    if sel_tbl and "{table_name}" in q_txt:
                        s,t=(sel_tbl.split('.',1)+[None])[:2] if '.' in sel_tbl else (None,sel_tbl)
                        db_type=db_manager.engine.url.drivername if db_manager.engine else None
                        ref=f'"{s}"."{t}"' if db_type=='postgresql' and s else f'"{t}"' if db_type=='postgresql' else f'[{s}].[{t}]' if db_type=='mssql' and s else f'[{t}]' if db_type=='mssql' else f'`{s}`.`{t}`' if db_type=='mysql' and s else f'`{t}`' if db_type=='mysql' else sel_tbl
                        q_txt=q_txt.replace("{table_name}",ref)
                    for ph in ["{column_name}","{category_column}","{numeric_column}"]:
                        if ph in q_txt:q_txt+=f"\n-- ATENÇÃO: Substitua {ph}."
            elif triggered_prop_id.startswith("saved-query-dropdown.") and saved_q:
                data=query_manager.get_query(saved_q)
                if data:q_txt,q_name_save,q_desc_save=data['query'],saved_q,data.get('description','')
        elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type")=="load-saved-query-from-list-btn":
            idx = next((i for i, item_id_dict in enumerate(ctx.inputs_list[2]) if item_id_dict['id'] == ctx.triggered_id), -1)
            if idx != -1 and list_load_clicks and list_load_clicks[idx] is not None and list_load_clicks[idx] > 0:
                q_list_name = ctx.triggered_id.get("index")
                if q_list_name:
                    data = query_manager.get_query(q_list_name)
                    if data: q_txt,q_name_save,q_desc_save = data['query'],q_list_name,data.get('description','')
        return q_txt,q_name_save,q_desc_save

    @app.callback(Output("sql-editor-feedback","children"),Output("save-query-name","value",allow_duplicate=True),Output("save-query-description","value",allow_duplicate=True),Output("app-toast","is_open",allow_duplicate=True),Output("app-toast","children",allow_duplicate=True),Output("app-toast","header",allow_duplicate=True),Output("app-toast","icon",allow_duplicate=True),Input("save-query-btn","n_clicks"),State("save-query-name","value"),State("sql-query-input","value"),State("save-query-description","value"),prevent_initial_call=True)
    def save_sql_query(n,name,query,desc):
        if not n or n == 0 or not name or not query: 
            if n and n > 0 :return dbc.Alert("Nome e query obrigatórios.",color="warning", duration=4000),dash.no_update,dash.no_update,True,"Preencha nome e query.","Salvar Query","warning"
            return dash.no_update,dash.no_update,dash.no_update,False,"","",""
        ok=query_manager.save_query(name,query,desc);msg,clr=(f"Query '{name}' salva!", "success") if ok else (f"Erro ao salvar '{name}'.","danger")
        return dbc.Alert(msg,color=clr,className="mt-2 small", duration=4000),"" if ok else name,"" if ok else desc,True,msg,"Salvar Query",clr

    @app.callback(Output("app-toast","is_open",allow_duplicate=True),Output("app-toast","children",allow_duplicate=True),Output("app-toast","header",allow_duplicate=True),Output("app-toast","icon",allow_duplicate=True),Output("sql-editor-feedback","children",allow_duplicate=True),Input({"type":"delete-saved-query-from-list-btn","index":ALL},"n_clicks"),prevent_initial_call=True)
    def delete_saved_query_from_list(clicks): 
        ctx=dash.callback_context
        if not ctx.triggered or not any(c is not None and c > 0 for c in clicks): return False,"","",dash.no_update,""
        name_del = ctx.triggered_id.get("index") if isinstance(ctx.triggered_id, dict) else None
        if not name_del:return True,"Nada para deletar.","Erro","warning",dbc.Alert("Nada selecionado.",color="warning",className="mt-2 small", duration=4000)
        ok=query_manager.delete_query(name_del);msg,clr=(f"Query '{name_del}' deletada.","success") if ok else (f"Erro ao deletar '{name_del}'.","danger")
        return True,msg,"Deletar Query",clr,dbc.Alert(msg,color=clr,className="mt-2 small", duration=4000)

    @app.callback(
        Output("data-preview-area","children",allow_duplicate=True),Output("data-preview-header","children",allow_duplicate=True),
        Output("download-data-btn","style",allow_duplicate=True),
        Output('server-side-data-key','data',allow_duplicate=True), 
        Output('active-table-name','data',allow_duplicate=True), Output("app-toast","is_open",allow_duplicate=True),
        Output("app-toast","children",allow_duplicate=True),Output("app-toast","header",allow_duplicate=True),
        Output("app-toast","icon",allow_duplicate=True),Output("sql-editor-feedback","children",allow_duplicate=True),
        Input("execute-query-btn","n_clicks"),State("sql-query-input","value"),State('active-connection-string','data'),
        prevent_initial_call=True
    )
    def execute_sql_query(n,query,conn_str):
        if not n or n == 0 or not query:return dash.no_update,dash.no_update,{'display':'none'},dash.no_update,dash.no_update,False,"","","",dash.no_update
        if not conn_str:msg="Nenhuma conexão ativa.";return dash.no_update,dash.no_update,{'display':'none'},None,"Custom Query",True,msg,"Executar Query","danger",dbc.Alert(msg,color="danger",className="mt-2 small", duration=4000)
        if not db_manager.engine or db_manager.connection_string!=conn_str:
            if not db_manager.connect(conn_str):msg="Falha reconectar.";return dash.no_update,dash.no_update,{'display':'none'},None,"Custom Query",True,msg,"Erro","danger",dbc.Alert(msg,color="danger",className="mt-2 small", duration=4000)
        df=db_manager.execute_query(query)
        data_key_to_store = None
        if df is not None and not df.empty:
            data_key_to_store = str(uuid.uuid4())
            cache.set(data_key_to_store, df, timeout=3600)
            log_info(f"DATABASE_PAGE - Dados salvos no cache com chave: {data_key_to_store}. Cache.has('{data_key_to_store}') = {cache.has(data_key_to_store)}")
            retrieved_df_check = cache.get(data_key_to_store)
            if retrieved_df_check is not None:
                log_info(f"DATABASE_PAGE - Verificação IMEDIATA: DataFrame recuperado do cache. Linhas: {len(retrieved_df_check)}")
            else:
                log_error(f"DATABASE_PAGE - ERRO IMEDIATO: Chave {data_key_to_store} existe no cache ({cache.has(data_key_to_store)}), mas get() retornou None!")
            dt=dash_table.DataTable(data=df.to_dict('records'),columns=[{"name":str(i),"id":str(i)} for i in df.columns],page_size=10,style_table={'overflowX':'auto','maxHeight':'350px','overflowY':'auto','minWidth':'100%'},style_cell={'textAlign':'left','padding':'5px','minWidth':'100px','maxWidth':'200px','whiteSpace':'normal','fontSize':'0.85rem'},style_header={'backgroundColor':'#e9ecef','fontWeight':'bold','borderBottom':'1px solid #dee2e6'},fixed_rows={'headers':True},export_format="csv")
            msg=f"Query executada, {len(df)} linhas."
            return dt,html.H5(f"Resultado ({len(df)} l.):"),{'display':'inline-block'},data_key_to_store,"Custom Query",True,msg,"Query","success",dbc.Alert(msg,color="success",className="mt-2 small", duration=4000)
        elif df is not None and df.empty:
            msg ="Query executada, sem dados."
            return dbc.Alert(msg,color="info",className="text-center"),html.H5("Resultado Vazio"),{'display':'none'},None,"Custom Query",True,msg,"Query","info",dbc.Alert(msg,color="info",className="mt-2 small", duration=4000)
        else:
            msg="Erro ao executar query."
            return dbc.Alert(msg,color="danger",className="text-center"),html.H5("Erro Query"),{'display':'none'},None,"Custom Query",True,msg,"Erro Query","danger",dbc.Alert(msg,color="danger",className="mt-2 small", duration=4000)

    @app.callback(Output("download-dataframe-csv","data"),Input("download-data-btn","n_clicks"),State("server-side-data-key","data"),State("active-table-name","data"),prevent_initial_call=True)
    def download_csv_callback(n,data_key,tbl_name):
        if not n or n == 0 or not data_key:raise dash.exceptions.PreventUpdate
        try:
            df = cache.get(data_key)
            if df is None: return None 
            ts=datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix=str(tbl_name).replace(" ","_").replace(".","_").replace("/","_") if tbl_name else "dados"
            return dcc.send_data_frame(df.to_csv,f"{prefix}_{ts}.csv",index=False)
        except Exception as e:
            log_error(f"Erro download:", exception=e)
        return None