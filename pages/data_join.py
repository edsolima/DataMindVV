# pages/data_join.py
import dash
from dash import dcc, html, Input, Output, State, dash_table, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import json
import uuid
import base64
from utils.database_manager import DatabaseManager
from utils.config_manager import ConfigManager
from utils.logger import log_error

cache = None
db_manager = None 
config_manager = None 

layout = dbc.Container([
    html.Div(id="join-page-loaded-signal", style={'display': 'none'}),
    dcc.Store(id='temp-join-data-key-store', storage_type='session'),
    dcc.Store(id='second-connection-store', storage_type='session'),
    dbc.Row(dbc.Col(html.H2([html.I(className="fas fa-link me-2"), "Combinar (Join) Dados"], className="mb-4 text-primary"))),

    dbc.Row([
        dbc.Col(md=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-cog me-2"), "Configurar Join"])),
                dbc.CardBody([
                    dbc.Alert("Carregue um DataFrame principal nas páginas 'Dados' ou 'Upload' primeiro.", 
                              color="info", id="join-info-alert-main-df", is_open=True),
                    html.Div(id="join-main-df-info"), 
                    html.Hr(),
                    
                    # Opção para escolher fonte da segunda tabela
                    dbc.Label("Fonte da Segunda Tabela:", className="fw-bold small"),
                    dbc.RadioItems(
                        options=[
                            {"label": "Banco de Dados Ativo", "value": "active_db"},
                            {"label": "Outro Banco de Dados", "value": "other_db"}
                        ],
                        value="active_db",
                        id="join-second-table-source",
                        inline=True,
                        className="mb-2"
                    ),
                    
                    # Conexão ativa
                    html.Div(id="join-active-db-container", children=[
                        dbc.Label("Selecionar Tabela (do BD Ativo):", html_for="join-select-db-table", className="fw-bold small"),
                        dcc.Dropdown(id="join-select-db-table", placeholder="Selecione tabela do BD...", className="mb-2", disabled=True),
                        dbc.Button("Carregar Colunas da Tabela", id="join-load-db-table-cols-btn", color="secondary", size="sm", className="w-100 mb-3", n_clicks=0, disabled=True),
                    ]),
                    
                    # Outra conexão
                    html.Div(id="join-other-db-container", style={"display": "none"}, children=[
                        dbc.Label("Selecionar Conexão:", html_for="join-select-other-connection", className="fw-bold small"),
                        dcc.Dropdown(id="join-select-other-connection", placeholder="Selecione conexão...", className="mb-2"),
                        dbc.Label("Selecionar Tabela:", html_for="join-select-other-db-table", className="fw-bold small"),
                        dcc.Dropdown(id="join-select-other-db-table", placeholder="Selecione tabela...", className="mb-2", disabled=True),
                        dbc.Button("Carregar Colunas da Tabela", id="join-load-other-db-table-cols-btn", color="secondary", size="sm", className="w-100 mb-3", n_clicks=0, disabled=True),
                    ]),
                    
                    html.Hr(),
                    dbc.Label("Tipo de Join:", html_for="join-type-dropdown", className="fw-bold small"),
                    dcc.Dropdown(id="join-type-dropdown", options=[
                        {"label": "Inner Join (Interseção)", "value": "inner"},
                        {"label": "Left Join (Tudo de A, correspondente de B)", "value": "left"},
                        {"label": "Right Join (Tudo de B, correspondente de A)", "value": "right"},
                        {"label": "Outer Join (União Completa)", "value": "outer"},
                    ], value="inner", clearable=False, className="mb-3"),
                    dbc.Label("Chave(s) do DataFrame Principal (A):", html_for="join-keys-main-df", className="fw-bold small"),
                    dcc.Dropdown(id="join-keys-main-df", placeholder="Selecione coluna(s) chave...", multi=True, className="mb-2", disabled=True),
                    dbc.Label("Chave(s) da Segunda Tabela (B):", html_for="join-keys-db-table", className="fw-bold small"),
                    dcc.Dropdown(id="join-keys-db-table", placeholder="Selecione coluna(s) chave...", multi=True, className="mb-2", disabled=True),
                    dbc.Row([
                        dbc.Col(dbc.Button([html.I(className="fas fa-play me-1"), "Executar Join & Preview"], id="join-execute-btn", color="success", className="w-100", n_clicks=0, disabled=True)),
                    ], className="mt-3"),
                ])
            ], className="shadow-sm sticky-top", style={"top":"80px"})
        ]),
        dbc.Col(md=8, children=[
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-table me-2"), "Preview do Resultado do Join"])),
                dbc.CardBody([
                    dcc.Loading(html.Div(id="join-preview-area", className="table-responsive", 
                                         style={"maxHeight": "400px", "overflowY": "auto"}), type="default"),
                    html.Div(id="join-result-info", className="mt-2 small text-muted"),
                    dbc.Button([html.I(className="fas fa-save me-1"), "Salvar e Usar DataFrame Combinado"], 
                               id="join-save-result-btn", color="primary", className="w-100 mt-3", n_clicks=0, disabled=True, style={'display':'none'})
                ])
            ], className="shadow-sm mb-4"),
            html.Div(id="join-feedback-message", className="mt-3")
        ])
    ])
], fluid=True)

def register_callbacks(app, cache_instance, db_manager_instance, config_manager_instance):
    global cache, db_manager, config_manager
    cache = cache_instance
    db_manager = db_manager_instance
    config_manager = config_manager_instance
    
    # Callback para alternar entre fontes de segunda tabela
    @app.callback(
        [Output("join-active-db-container", "style"),
         Output("join-other-db-container", "style")],
        [Input("join-second-table-source", "value")]
    )
    def toggle_second_table_source(source_value):
        if source_value == "active_db":
            return {"display": "block"}, {"display": "none"}
        else:
            return {"display": "none"}, {"display": "block"}
    
    # Callback para carregar as conexões disponíveis no dropdown de outras conexões
    @app.callback(
        Output("join-select-other-connection", "options"),
        [Input("join-page-loaded-signal", "children")]
    )
    def load_available_connections(_):
        connections = config_manager.list_connections()
        return [{"label": conn, "value": conn} for conn in connections]
    
    # Callback para carregar tabelas da outra conexão selecionada
    @app.callback(
        [Output("join-select-other-db-table", "options"),
         Output("join-select-other-db-table", "disabled"),
         Output("join-load-other-db-table-cols-btn", "disabled"),
         Output("second-connection-store", "data")],
        [Input("join-select-other-connection", "value")]
    )
    def update_other_db_tables(selected_connection):
        if not selected_connection:
            return [], True, True, None
        
        conn_data = config_manager.get_connection(selected_connection)
        if not conn_data:
            return [], True, True, None
        
        # Criar uma instância temporária do DatabaseManager para a segunda conexão
        temp_db_manager = DatabaseManager()
        conn_string = temp_db_manager.create_connection_string(conn_data)
        if not temp_db_manager.connect(conn_string):
            return [], True, True, None
        
        tables = temp_db_manager.get_tables(schema=conn_data.get('schema'))
        table_options = [{"label": str(t), "value": str(t)} for t in tables]
        
        # Armazenar informações da conexão para uso posterior
        connection_info = {
            "name": selected_connection,
            "conn_string": conn_string,
            "conn_data": conn_data
        }
        
        return table_options, False, False if table_options else True, connection_info

    @app.callback(
        [Output("join-main-df-info", "children"), Output("join-select-db-table", "options"),
         Output("join-select-db-table", "disabled"), Output("join-load-db-table-cols-btn", "disabled"),
         Output("join-info-alert-main-df", "is_open")],
        [Input("join-page-loaded-signal", "children"), Input("server-side-data-key", "data"),
         Input("active-connection-name", "data")]
    )
    def update_main_df_info_and_db_tables(_, data_key, active_conn_name):
        main_df_info_children = dbc.Alert("Nenhum DataFrame principal carregado. Carregue dados nas páginas 'Dados' ou 'Upload' primeiro.", color="info", className="text-center p-3")
        db_table_options = []
        db_table_disabled = True
        load_cols_btn_disabled = True
        alert_open = True

        if data_key:
            df_main = cache.get(data_key)
            if df_main is not None and not df_main.empty:
                main_df_info_children = dbc.Card(dbc.CardBody([
                    html.H6("DataFrame Principal (A):", className="mb-1"),
                    html.P(f"Linhas: {len(df_main):,}, Colunas: {len(df_main.columns)}", className="small text-muted mb-0")
                ]), className="mb-2 bg-light border")
                alert_open = False 
            elif df_main is None: # Chave existe mas dados não estão no cache
                 main_df_info_children = dbc.Alert("Dados do DataFrame principal não encontrados no cache (sessão pode ter expirado). Recarregue os dados.", color="danger", className="text-center p-3")


        if active_conn_name:
            conn_data = config_manager.get_connection(active_conn_name)
            if conn_data:
                current_conn_string = db_manager.create_connection_string(conn_data)
                if not db_manager.engine or db_manager.connection_string != current_conn_string:
                    db_manager.connect(current_conn_string)
                if db_manager.engine:
                    tables = db_manager.get_tables(schema=conn_data.get('schema'))
                    db_table_options = [{"label": str(t), "value": str(t)} for t in tables]
                    if db_table_options:
                         db_table_disabled = False
        
        return main_df_info_children, db_table_options, db_table_disabled, load_cols_btn_disabled, alert_open

    # Habilitar botão "Carregar Colunas da Tabela do BD" quando uma tabela é selecionada
    @app.callback(
        Output("join-load-db-table-cols-btn", "disabled", allow_duplicate=True),
        Input("join-select-db-table", "value"),
        prevent_initial_call=True
    )
    def toggle_load_db_cols_button(selected_db_table):
        return not bool(selected_db_table)
        
    # Habilitar botão "Carregar Colunas da Outra Tabela do BD" quando uma tabela é selecionada
    @app.callback(
        Output("join-load-other-db-table-cols-btn", "disabled", allow_duplicate=True),
        Input("join-select-other-db-table", "value"),
        prevent_initial_call=True
    )
    def toggle_load_other_db_cols_button(selected_other_db_table):
        return not bool(selected_other_db_table)


    @app.callback(
        [Output("join-keys-main-df", "options"), Output("join-keys-main-df", "disabled"),
         Output("join-keys-db-table", "options"), Output("join-keys-db-table", "disabled"),
         Output("join-execute-btn", "disabled")],
        [Input("server-side-data-key", "data"), 
         Input("join-load-db-table-cols-btn", "n_clicks"),
         Input("join-load-other-db-table-cols-btn", "n_clicks")],
        [State("join-select-db-table", "value"), 
         State("active-connection-string", "data"),
         State("join-select-other-db-table", "value"),
         State("second-connection-store", "data"),
         State("join-second-table-source", "value")],
        prevent_initial_call=True
    )
    def update_join_key_options(data_key_main, n_clicks_load_cols, n_clicks_load_other_cols, 
                               selected_db_table, active_conn_str, selected_other_db_table, 
                               second_connection_data, second_table_source):
        ctx = dash.callback_context
        triggered_id = ctx.triggered_id if ctx.triggered else None
        
        main_df_cols_opts, main_df_disabled = [], True
        db_table_cols_opts, db_table_disabled = [], True
        execute_join_disabled = True

        # Carregar colunas do DataFrame principal
        df_main = None
        if data_key_main:
            df_main = cache.get(data_key_main)
            if df_main is not None and not df_main.empty:
                main_df_cols_opts = [{"label": col, "value": col} for col in df_main.columns]
                main_df_disabled = False
        
        # Determinar qual fonte de segunda tabela está sendo usada
        using_active_db = second_table_source == "active_db"
        triggered_by_active_db = triggered_id == "join-load-db-table-cols-btn"
        triggered_by_other_db = triggered_id == "join-load-other-db-table-cols-btn"
        
        # Carregar colunas da tabela do banco de dados ativo
        if using_active_db and triggered_by_active_db and selected_db_table and active_conn_str:
            if not db_manager.engine or db_manager.connection_string != active_conn_str:
                if not db_manager.connect(active_conn_str):
                    return main_df_cols_opts, main_df_disabled, [], True, True

            if db_manager.engine:
                schema_part, table_part = (selected_db_table.split('.',1)+[None])[:2] if '.' in selected_db_table else (None, selected_db_table)
                df_db_table_sample = db_manager.get_table_sample(table_part, schema=schema_part, sample_size=1) 
                if df_db_table_sample is not None and not df_db_table_sample.empty:
                    db_table_cols_opts = [{"label": col, "value": col} for col in df_db_table_sample.columns]
                    db_table_disabled = False
        
        # Carregar colunas da tabela do outro banco de dados
        elif not using_active_db and triggered_by_other_db and selected_other_db_table and second_connection_data:
            # Criar uma instância temporária do DatabaseManager para a segunda conexão
            temp_db_manager = DatabaseManager()
            conn_string = second_connection_data.get("conn_string")
            if not temp_db_manager.connect(conn_string):
                return main_df_cols_opts, main_df_disabled, [], True, True
            
            schema_part, table_part = (selected_other_db_table.split('.',1)+[None])[:2] if '.' in selected_other_db_table else (None, selected_other_db_table)
            df_db_table_sample = temp_db_manager.get_table_sample(table_part, schema=schema_part, sample_size=1)
            if df_db_table_sample is not None and not df_db_table_sample.empty:
                db_table_cols_opts = [{"label": col, "value": col} for col in df_db_table_sample.columns]
                db_table_disabled = False
        
        # Se não foi acionado por nenhum dos botões de carregar colunas, manter o estado atual
        elif not triggered_by_active_db and not triggered_by_other_db:
            # Manter o estado atual, não fazer nada
            pass
        
        if not main_df_disabled and not db_table_disabled:
            execute_join_disabled = False
            
        return main_df_cols_opts, main_df_disabled, db_table_cols_opts, db_table_disabled, execute_join_disabled

    @app.callback(
        [Output("join-preview-area", "children"), Output("join-result-info", "children"),
         Output("join-save-result-btn", "style"), Output("join-save-result-btn", "disabled"),
         Output("join-feedback-message", "children"),
         Output('temp-join-data-key-store', 'data')], # <--- NOVO OUTPUT para a chave temporária
        [Input("join-execute-btn", "n_clicks")],
        [State("server-side-data-key", "data"), 
         State("join-select-db-table", "value"),
         State("join-select-other-db-table", "value"),
         State("active-connection-string", "data"), 
         State("second-connection-store", "data"),
         State("join-type-dropdown", "value"),
         State("join-keys-main-df", "value"), 
         State("join-keys-db-table", "value"),
         State("join-second-table-source", "value")],
        prevent_initial_call=True
    )
    def execute_and_preview_join(n_clicks, data_key_main, active_db_table_name, other_db_table_name,
                                active_conn_str, second_connection_data, join_type, 
                                main_df_keys, db_table_keys, second_table_source):
        if not n_clicks or n_clicks == 0 or not data_key_main or not join_type or not main_df_keys or not db_table_keys:
            return dbc.Alert("Preencha todas as configurações do Join.", color="warning"), "", {'display':'none'}, True, "", None

        # Verificar qual fonte de segunda tabela está sendo usada
        using_active_db = second_table_source == "active_db"
        db_table_name = active_db_table_name if using_active_db else other_db_table_name
        
        if not db_table_name:
            return dbc.Alert("Selecione uma tabela de banco de dados.", color="warning"), "", {'display':'none'}, True, "", None

        # Carregar o DataFrame principal
        df_main = cache.get(data_key_main)
        if df_main is None: 
            return dbc.Alert("DataFrame principal não encontrado no cache.", color="danger"), "", {'display':'none'}, True, "", None

        # Obter o DataFrame da segunda tabela
        df_db_table = None
        
        if using_active_db:
            # Usar o banco de dados ativo
            if not active_conn_str:
                return dbc.Alert("Conexão ativa não encontrada.", color="danger"), "", {'display':'none'}, True, "", None
                
            if not db_manager.engine or db_manager.connection_string != active_conn_str:
                if not db_manager.connect(active_conn_str):
                    return dbc.Alert("Falha ao conectar ao banco de dados ativo.", color="danger"), "", {'display':'none'}, True, "", None
            
            schema_part, table_part = (db_table_name.split('.',1)+[None])[:2] if '.' in db_table_name else (None, db_table_name)
            
            # Construir a query de forma segura
            id_prep = db_manager.engine.dialect.identifier_preparer if hasattr(db_manager.engine.dialect, 'identifier_preparer') else None
            quoted_table = id_prep.quote_identifier(table_part) if id_prep else f'"{table_part}"'
            query = f"SELECT * FROM {id_prep.quote_identifier(schema_part)}.{quoted_table}" if schema_part and id_prep else f"SELECT * FROM {quoted_table}"
            
            try:
                df_db_table = db_manager.execute_query(query)
            except Exception as e:
                err_msg = f"Erro ao carregar '{db_table_name}' do banco de dados ativo: {e}"; log_error(err_msg, exception=e); import traceback; traceback.print_exc()
                return dbc.Alert(err_msg, color="danger"), "", {'display':'none'}, True, "", None
        else:
            # Usar outro banco de dados
            if not second_connection_data or not second_connection_data.get("conn_string"):
                return dbc.Alert("Informações da segunda conexão não encontradas.", color="danger"), "", {'display':'none'}, True, "", None
            
            # Criar uma instância temporária do DatabaseManager para a segunda conexão
            temp_db_manager = DatabaseManager()
            conn_string = second_connection_data.get("conn_string")
            if not temp_db_manager.connect(conn_string):
                return dbc.Alert("Falha ao conectar ao segundo banco de dados.", color="danger"), "", {'display':'none'}, True, "", None
            
            schema_part, table_part = (db_table_name.split('.',1)+[None])[:2] if '.' in db_table_name else (None, db_table_name)
            
            # Construir a query de forma segura
            id_prep = temp_db_manager.engine.dialect.identifier_preparer if hasattr(temp_db_manager.engine.dialect, 'identifier_preparer') else None
            quoted_table = id_prep.quote_identifier(table_part) if id_prep else f'"{table_part}"'
            query = f"SELECT * FROM {id_prep.quote_identifier(schema_part)}.{quoted_table}" if schema_part and id_prep else f"SELECT * FROM {quoted_table}"
            
            try:
                df_db_table = temp_db_manager.execute_query(query)
            except Exception as e:
                err_msg = f"Erro ao carregar '{db_table_name}' do segundo banco de dados: {e}"; log_error(err_msg, exception=e); import traceback; traceback.print_exc()
                return dbc.Alert(err_msg, color="danger"), "", {'display':'none'}, True, "", None

        if df_db_table is None or df_db_table.empty:
            return dbc.Alert(f"Tabela '{db_table_name}' vazia ou erro.", color="warning"), "", {'display':'none'}, True, "", None

        try:
            main_keys = [main_df_keys] if isinstance(main_df_keys, str) else main_df_keys
            db_keys = [db_table_keys] if isinstance(db_table_keys, str) else db_table_keys
            if len(main_keys) != len(db_keys):
                return dbc.Alert("Número de chaves deve ser igual.", color="danger"), "", {'display':'none'}, True, "", None

            df_joined = pd.merge(df_main, df_db_table, how=join_type, left_on=main_keys, right_on=db_keys, suffixes=('_A', '_B'))
            if df_joined.empty:
                return dbc.Alert("Join resultou em DataFrame vazio. Verifique as chaves e o tipo de join.", color="warning"), "Resultado Vazio", {'display':'none'}, True, "", None

            # Criar o preview da tabela
            preview = dash_table.DataTable(
                data=df_joined.head(20).to_dict('records'), 
                columns=[{"name":str(i),"id":str(i)} for i in df_joined.columns],
                page_size=10, style_table={'overflowX':'auto'}, style_cell={'fontSize':'0.8rem'}
            )
            
            # Adicionar botão de download
            download_button = html.Div([
                html.A(
                    dbc.Button([html.I(className="fas fa-download me-1"), "Baixar CSV"], 
                              color="secondary", size="sm", className="mt-2"),
                    id="join-download-link",
                    download=f"join_result_{join_type}.csv",
                    href="",
                    target="_blank"
                )
            ], className="mt-2 mb-2")
            
            # Combinar o preview e o botão de download
            preview_with_download = html.Div([
                preview,
                download_button
            ])
            
            info = f"Join '{join_type}'. Resultado: {len(df_joined):,} linhas, {len(df_joined.columns)} colunas."
            
            temp_join_key = f"temp_join_{str(uuid.uuid4())}"
            cache.set(temp_join_key, df_joined, timeout=600) # Cache por 10 min
            
            # Gerar o link de download
            csv_string = df_joined.to_csv(index=False, encoding='utf-8')
            csv_bytes = csv_string.encode('utf-8')
            b64 = base64.b64encode(csv_bytes).decode('utf-8')
            href = f"data:text/csv;charset=utf-8;base64,{b64}"
            
            # Atualizar o link de download
            app.clientside_callback(
                """
                function(href) {
                    document.getElementById('join-download-link').href = href;
                    return '';
                }
                """,
                Output("join-download-link", "children"),
                [Input("join-download-link", "href")]
            )
            
            # Definir o link de download
            app.clientside_callback(
                """
                function(temp_join_key) {
                    return temp_join_key ? true : false;
                }
                """,
                Output("join-download-link", "href"),
                [Input("temp-join-data-key-store", "data")]
            )

            return preview_with_download, info, {'display':'block'}, False, dbc.Alert("Preview gerado. Você pode baixar os dados ou salvá-los como DataFrame principal.", color="success", duration=5000), temp_join_key
        except Exception as e:
            err_msg = f"Erro ao executar Join: {e}"; log_error(err_msg, exception=e); import traceback; traceback.print_exc()
            return dbc.Alert(err_msg, color="danger"), "", {'display':'none'}, True, "", None

    @app.callback(
        [Output("server-side-data-key", "data", allow_duplicate=True),
         Output("join-feedback-message", "children", allow_duplicate=True),
         Output("app-toast", "is_open", allow_duplicate=True), Output("app-toast", "children", allow_duplicate=True),
         Output("app-toast", "header", allow_duplicate=True), Output("app-toast", "icon", allow_duplicate=True),
         Output("join-save-result-btn", "style", allow_duplicate=True)],
        [Input("join-save-result-btn", "n_clicks")],
        [State('temp-join-data-key-store', 'data')], # <--- LER DO NOVO STORE
        prevent_initial_call=True
    )
    def save_joined_dataframe(n_clicks, temp_join_key): # <--- USA A CHAVE DO STORE
        if not n_clicks or n_clicks == 0 or not temp_join_key:
            raise dash.exceptions.PreventUpdate

        df_joined = cache.get(temp_join_key)
        
        if df_joined is not None and not df_joined.empty:
            cache.delete(temp_join_key) # Remove a chave temporária
            new_main_data_key = str(uuid.uuid4())
            cache.set(new_main_data_key, df_joined, timeout=3600) 
            msg = "DataFrame combinado salvo e definido como principal!"
            return new_main_data_key, dbc.Alert(msg, color="success", duration=4000, className="small"), \
                   True, msg, "Join Salvo", "success", {'display':'none'}
        else:
            msg = "Erro: DataFrame do preview não encontrado no cache. Execute o join novamente."
            return dash.no_update, dbc.Alert(msg, color="danger", className="small"), \
                   True, msg, "Erro ao Salvar Join", "danger", {'display':'block'}