# pages/transform.py
import dash
from dash import dcc, html, Input, Output, State, dash_table, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import json
import uuid # Para gerar chaves de cache únicas
# A função load_dataframe_from_store não será mais usada aqui para carregar o DF principal,
# pois ele virá do cache. Mas pode ser mantida em utils se for usada em outros contextos.
# from utils.dataframe_utils import load_dataframe_from_store 

# Variável global para a instância do cache, será definida em register_callbacks
cache = None

layout = dbc.Container([
    html.Div(id="transform-page-loaded-signal", style={'display': 'none'}), 
    dbc.Row(dbc.Col(html.H2([html.I(className="fas fa-exchange-alt me-2"), "Transformação de Dados"], className="mb-4 text-primary"))),
    
    dbc.Row([
        dbc.Col(md=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-list me-2"), "Colunas Atuais & Tipos"])), # Título ajustado
                dbc.CardBody([
                    dcc.Loading(dbc.ListGroup(id="transform-column-list", flush=True)),
                    html.Hr(),
                    dbc.Button([html.I(className="fas fa-sync-alt me-1"), "Recarregar Lista/Preview"], 
                               id="transform-refresh-cols-btn", color="info", size="sm", className="w-100 mt-2", n_clicks=0)
                ])
            ], className="mb-4 shadow-sm sticky-top", style={"top":"80px"}),
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-eye me-2"), "Preview dos Dados (Top 10 linhas)"])),
                dbc.CardBody([
                    dcc.Loading(html.Div(id="transform-data-preview-area", className="table-responsive", 
                                         style={"maxHeight": "300px", "overflowY": "auto"}))
                ])
            ], className="mb-4 shadow-sm")
        ]),
        
        dbc.Col(md=8, children=[
            dbc.Accordion([
                dbc.AccordionItem(title="Renomear Coluna", children=[
                    dbc.Row([
                        dbc.Col(dcc.Dropdown(id="transform-rename-select-col", placeholder="Selecione a coluna...", className="mb-2"), md=5),
                        dbc.Col(dbc.Input(id="transform-rename-new-name", placeholder="Novo nome da coluna...", className="mb-2"), md=5),
                        dbc.Col(dbc.Button("Renomear", id="transform-rename-btn", color="primary", n_clicks=0), md=2)
                    ], align="center")
                ]),
                dbc.AccordionItem(title="Remover Coluna(s)", children=[
                    dcc.Dropdown(id="transform-remove-select-cols", placeholder="Selecione colunas para remover...", multi=True, className="mb-2"),
                    dbc.Button("Remover Selecionadas", id="transform-remove-btn", color="danger", n_clicks=0, className="w-100")
                ]),
                dbc.AccordionItem(title="Mudar Tipo de Dados", children=[
                    dbc.Row([
                        dbc.Col(dcc.Dropdown(id="transform-changetype-select-col", placeholder="Coluna...", className="mb-2"), md=5),
                        dbc.Col(dcc.Dropdown(id="transform-changetype-new-type", placeholder="Novo tipo...", className="mb-2", options=[
                            {"label": "Numérico (Float)", "value": "float64"},
                            {"label": "Numérico (Inteiro)", "value": "Int64"},
                            {"label": "Texto (String)", "value": "object"},
                            {"label": "Data/Hora", "value": "datetime64[ns]"},
                            {"label": "Booleano", "value": "bool"}
                        ]), md=5),
                        dbc.Col(dbc.Button("Alterar Tipo", id="transform-changetype-btn", color="primary", n_clicks=0), md=2)
                    ], align="center")
                ]),
                dbc.AccordionItem(title="Criar Coluna Calculada (A + B)", children=[
                    dbc.Row([
                        dbc.Col(dcc.Dropdown(id="transform-calc-col-a", placeholder="Coluna A (Numérica)...", className="mb-2"), md=3),
                        dbc.Col(dcc.Dropdown(id="transform-calc-col-b", placeholder="Coluna B (Numérica)...", className="mb-2"), md=3),
                        dbc.Col(dbc.Input(id="transform-calc-new-col-name", placeholder="Nome da Nova Coluna...", className="mb-2"), md=4),
                        dbc.Col(dbc.Button("Criar Soma", id="transform-calc-btn", color="success", n_clicks=0), md=2)
                    ], align="center")
                ]),
                dbc.AccordionItem(title="Tratar Valores Ausentes", children=[
                    dbc.Row([
                        dbc.Col(dcc.Dropdown(id="transform-fillna-select-col", placeholder="Coluna...", className="mb-2"), md=4),
                        dbc.Col(dcc.Dropdown(id="transform-fillna-method", placeholder="Método...", className="mb-2", options=[
                            {"label": "Remover Linhas com NaN nesta coluna", "value": "dropna_col"},
                            {"label": "Preencher com Média (Numérico)", "value": "mean"},
                            {"label": "Preencher com Mediana (Numérico)", "value": "median"},
                            {"label": "Preencher com Moda (Categórico/Numérico)", "value": "mode"},
                            {"label": "Preencher com Valor Constante", "value": "constant"}
                        ]), md=4),
                        dbc.Col(dbc.Input(id="transform-fillna-constant-value", placeholder="Valor constante", className="mb-2"), md=2),
                        dbc.Col(dbc.Button("Aplicar", id="transform-fillna-btn", color="warning", n_clicks=0), md=2)
                    ], align="center"),
                    dbc.Button("Remover TODAS as Linhas com QUALQUER NaN", id="transform-dropna-all-btn", color="danger", outline=True, size="sm", className="mt-3 w-100", n_clicks=0)
                ]),
            ], flush=True, always_open=True, active_item=[]), 
            html.Div(id="transform-feedback-message", className="mt-3")
        ])
    ])
], fluid=True)

# MODIFICADO PARA CACHE: Aceita cache_instance
def register_callbacks(app, cache_instance):
    global cache 
    cache = cache_instance

    @app.callback(
        [Output("transform-column-list", "children"),
         Output("transform-rename-select-col", "options"),
         Output("transform-remove-select-cols", "options"),
         Output("transform-changetype-select-col", "options"),
         Output("transform-calc-col-a", "options"),
         Output("transform-calc-col-b", "options"),
         Output("transform-fillna-select-col", "options"),
         Output("transform-data-preview-area", "children")],
        [Input("transform-page-loaded-signal", "children"), 
         Input("server-side-data-key", "data"), # MODIFICADO PARA CACHE: Observa a chave
         Input("transform-refresh-cols-btn", "n_clicks")],
        # Não precisa mais do State aqui se o Input server-side-data-key já traz a chave atualizada
    )
    def update_transform_page_inputs(_, data_key, refresh_clicks): 
        ctx = dash.callback_context
        
        # Se o refresh foi clicado, a data_key já deve estar atualizada pelo Input.
        # Se a data_key mudou, esse é o trigger principal.
        # Se for a carga da página, data_key pode ser None ou uma chave válida.

        if not data_key:
            no_data_alert = dbc.Alert("Nenhum dado carregado para transformar. Carregue dados nas páginas 'Dados' ou 'Upload'.", color="warning", className="text-center p-4")
            empty_opts = []
            return no_data_alert, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts, no_data_alert
        
        df = cache.get(data_key) # MODIFICADO PARA CACHE: Lê do cache
        if df is None: # Chave existe mas dados não estão no cache (expirou, etc.)
             expired_alert = dbc.Alert("Dados não encontrados no cache (sessão pode ter expirado). Recarregue os dados.", color="danger", className="text-center p-4")
             empty_opts = []
             return expired_alert, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts, expired_alert
        if df.empty:
            empty_data_alert = dbc.Alert("Os dados carregados estão vazios.", color="info", className="text-center p-4")
            empty_opts = []
            return empty_data_alert, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts, empty_opts, empty_data_alert

        col_options = [{"label": col, "value": col} for col in df.columns]
        num_col_options = [{"label":col,"value":col} for col in df.select_dtypes(include=np.number).columns]

        list_group_items = [dbc.ListGroupItem(f"{col} ({str(df[col].dtype)})") for col in df.columns]
        
        preview_table = dash_table.DataTable(
            data=df.head(10).to_dict('records'), columns=[{"name": str(i), "id": str(i)} for i in df.columns],
            page_size=5, style_table={'overflowX': 'auto', 'minWidth':'100%'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'fontSize': '0.8rem'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'borderBottom':'1px solid #dee2e6'}
        )
        return list_group_items, col_options, col_options, col_options, num_col_options, num_col_options, col_options, preview_table

    @app.callback(
        Output('server-side-data-key', 'data', allow_duplicate=True), # MODIFICADO PARA CACHE: Atualiza a chave
        Output('transform-feedback-message', 'children'),
        Output("app-toast", "is_open", allow_duplicate=True), Output("app-toast", "children", allow_duplicate=True),
        Output("app-toast", "header", allow_duplicate=True), Output("app-toast", "icon", allow_duplicate=True),
        Input("transform-rename-btn", "n_clicks"), Input("transform-remove-btn", "n_clicks"),
        Input("transform-changetype-btn", "n_clicks"), Input("transform-calc-btn", "n_clicks"),
        Input("transform-fillna-btn", "n_clicks"), Input("transform-dropna-all-btn", "n_clicks"),
        State("server-side-data-key", "data"), # MODIFICADO PARA CACHE: Lê a chave atual
        State("transform-rename-select-col", "value"), State("transform-rename-new-name", "value"),
        State("transform-remove-select-cols", "value"),
        State("transform-changetype-select-col", "value"), State("transform-changetype-new-type", "value"),
        State("transform-calc-col-a", "value"), State("transform-calc-col-b", "value"), State("transform-calc-new-col-name", "value"),
        State("transform-fillna-select-col", "value"), State("transform-fillna-method", "value"), State("transform-fillna-constant-value", "value"),
        prevent_initial_call=True
    )
    def apply_transformation(
        r_n, rm_n, ct_n, calc_n, fn_n, da_n, 
        current_data_key, # MODIFICADO PARA CACHE
        r_col, r_new, rm_cols, ct_col, ct_new_type, 
        calc_a, calc_b, calc_new, fn_col, fn_method, fn_const):

        ctx = dash.callback_context
        if not ctx.triggered_id or not current_data_key: 
            # print("Transformação: Sem trigger ou sem data key.")
            raise dash.exceptions.PreventUpdate

        df = cache.get(current_data_key) # MODIFICADO PARA CACHE: Lê do cache
        if df is None:
            return dash.no_update, dbc.Alert("Dados não encontrados no cache para transformar. Recarregue.", color="danger"), True, "Dados expirados", "Erro", "danger"
        
        # É crucial trabalhar com uma cópia para não modificar o DataFrame no cache diretamente
        # a menos que a transformação seja bem sucedida e uma NOVA chave seja gerada.
        df_copy = df.copy()

        original_cols_set = set(df_copy.columns)
        original_shape = df_copy.shape
        feedback_msg, df_transformed_flag = "", False
        toast_open, toast_children, toast_header, toast_icon = False, "", "", ""
        new_data_key_to_store = dash.no_update # Por padrão, não atualiza a chave

        try:
            button_id = ctx.triggered_id # Este é o ID do botão que disparou
            
            if button_id == "transform-rename-btn" and r_col and r_new:
                if r_col in df_copy.columns: 
                    df_copy.rename(columns={r_col: r_new}, inplace=True)
                    feedback_msg = f"Coluna '{r_col}' renomeada para '{r_new}'."
                    df_transformed_flag = True
                else: feedback_msg = f"Coluna '{r_col}' não encontrada."
            
            elif button_id == "transform-remove-btn" and rm_cols:
                cols_to_drop = [col for col in rm_cols if col in df_copy.columns]
                if cols_to_drop:
                    df_copy.drop(columns=cols_to_drop, inplace=True)
                    feedback_msg = f"Coluna(s) removida(s): {', '.join(cols_to_drop)}."
                    df_transformed_flag = True
                else: feedback_msg = "Nenhuma coluna válida selecionada para remoção."

            elif button_id == "transform-changetype-btn" and ct_col and ct_new_type:
                if ct_col in df_copy.columns:
                    original_dtype = df_copy[ct_col].dtype
                    try:
                        if ct_new_type == "datetime64[ns]": df_copy[ct_col] = pd.to_datetime(df_copy[ct_col], errors='coerce')
                        else: df_copy[ct_col] = df_copy[ct_col].astype(ct_new_type)
                        feedback_msg = f"Tipo de '{ct_col}' (era {original_dtype}) tentou mudar para {ct_new_type} -> resultado {df_copy[ct_col].dtype}."
                    except Exception as e_type: feedback_msg = f"Erro ao alterar tipo de '{ct_col}' para {ct_new_type}: {e_type}"
                    df_transformed_flag = True 
                else: feedback_msg = f"Coluna '{ct_col}' não encontrada."

            elif button_id == "transform-calc-btn" and calc_a and calc_b and calc_new:
                if calc_a in df_copy.columns and calc_b in df_copy.columns and \
                   pd.api.types.is_numeric_dtype(df_copy[calc_a]) and pd.api.types.is_numeric_dtype(df_copy[calc_b]):
                    if calc_new in df_copy.columns: calc_new = f"{calc_new}_soma" # Evitar sobrescrever
                    df_copy[calc_new] = df_copy[calc_a] + df_copy[calc_b]
                    feedback_msg = f"Nova coluna '{calc_new}' ({calc_a}+{calc_b})."
                    df_transformed_flag = True
                else: feedback_msg = "Colunas A e B devem existir e ser numéricas."
            
            elif button_id == "transform-fillna-btn" and fn_col and fn_method:
                if fn_col in df_copy.columns:
                    if fn_method=="dropna_col": df_copy.dropna(subset=[fn_col],inplace=True); feedback_msg=f"Linhas com NaN em '{fn_col}' removidas."
                    elif fn_method=="mean" and pd.api.types.is_numeric_dtype(df_copy[fn_col]): df_copy[fn_col].fillna(df_copy[fn_col].mean(),inplace=True); feedback_msg=f"NaNs em '{fn_col}' preenchidos com média."
                    elif fn_method=="median" and pd.api.types.is_numeric_dtype(df_copy[fn_col]): df_copy[fn_col].fillna(df_copy[fn_col].median(),inplace=True); feedback_msg=f"NaNs em '{fn_col}' preenchidos com mediana."
                    elif fn_method=="mode": df_copy[fn_col].fillna(df_copy[fn_col].mode()[0] if not df_copy[fn_col].mode().empty else np.nan,inplace=True); feedback_msg=f"NaNs em '{fn_col}' preenchidos com moda."
                    elif fn_method=="constant" and fn_const is not None and fn_const != "":
                        try: 
                            # Tentar converter o valor constante para o tipo da coluna antes de preencher
                            target_dtype = df_copy[fn_col].dtype
                            if pd.isna(df_copy[fn_col]).all(): # Se a coluna for toda NaN, não tem dtype base útil
                                 converted_const = fn_const # Usa o valor como string
                            elif pd.api.types.is_numeric_dtype(target_dtype):
                                converted_const = pd.to_numeric(fn_const, errors='raise')
                            elif pd.api.types.is_datetime64_any_dtype(target_dtype):
                                 converted_const = pd.to_datetime(fn_const, errors='raise')
                            elif pd.api.types.is_bool_dtype(target_dtype):
                                 converted_const = bool(str(fn_const).lower() in ['true', '1', 't', 'sim', 's'])
                            else: # object/string
                                 converted_const = str(fn_const)
                            df_copy[fn_col].fillna(converted_const,inplace=True)
                            feedback_msg=f"NaNs em '{fn_col}' preenchidos com '{converted_const}'."
                        except Exception as e_const: feedback_msg = f"Valor '{fn_const}' incompatível com '{fn_col}'. Erro: {e_const}"
                    else: feedback_msg = f"Método '{fn_method}' inválido ou valor constante não fornecido."
                    df_transformed_flag = True
                else: feedback_msg = f"Coluna '{fn_col}' não encontrada."

            elif button_id == "transform-dropna-all-btn":
                df_copy.dropna(inplace=True); feedback_msg=f"Linhas com qualquer NaN removidas."; df_transformed_flag=True
            
            if df_transformed_flag:
                final_cols_set = set(df_copy.columns)
                final_shape = df_copy.shape
                cols_added = len(final_cols_set - original_cols_set)
                cols_removed = len(original_cols_set - final_cols_set)
                rows_change = final_shape[0] - original_shape[0]

                if feedback_msg: feedback_msg += " "
                if cols_added > 0: feedback_msg += f"({cols_added} col. adicionada(s))."
                if cols_removed > 0: feedback_msg += f"({cols_removed} col. removida(s))."
                if rows_change != 0: feedback_msg += f"({abs(rows_change)} linha(s) {'adicionada(s)' if rows_change > 0 else 'removida(s)'})."

                new_data_key_to_store = str(uuid.uuid4()) # Gerar NOVA chave para o DF transformado
                cache.set(new_data_key_to_store, df_copy, timeout=3600) # Salvar DF transformado no cache

                toast_open,toast_children,toast_header,toast_icon = True,feedback_msg,"Transformação","success"
                return new_data_key_to_store, dbc.Alert(feedback_msg,color="success",duration=4000, className="small"),toast_open,toast_children,toast_header,toast_icon
            else:
                alert_color = "warning" if feedback_msg else "secondary" # Se houve mensagem mas não transformou, é warning
                final_feedback = feedback_msg if feedback_msg else "Nenhuma operação realizada ou parâmetros inválidos."
                return dash.no_update, dbc.Alert(final_feedback,color=alert_color,duration=4000, className="small"),False,"","","" # Não mostrar toast se nada aconteceu
        
        except Exception as e:
            err_msg=f"Erro: {e}"; print(f"Erro transformação: {e}"); import traceback; traceback.print_exc()
            return dash.no_update,dbc.Alert(err_msg,color="danger"),True,err_msg,"Erro Transformação","danger"