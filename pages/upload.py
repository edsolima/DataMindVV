# pages/upload.py
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import chardet
from utils.data_analyzer import DataAnalyzer
from utils.logger import log_info, log_error, log_warning, log_debug
import json
import uuid # Para gerar chaves de cache
import numpy as np
from datetime import datetime
from dash.dependencies import ALL
from utils.ui_helpers import create_preview_table, show_feedback_alert

# Tentar importar Dask e Arrow
try:
    import dask.dataframe as dd
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False
try:
    import pyarrow as pa
    ARROW_AVAILABLE = True
except ImportError:
    ARROW_AVAILABLE = False

# MODIFICADO PARA CACHE: A função register_callbacks agora aceita 'cache_instance'
def register_callbacks(app, cache_instance): # Mudança aqui
    global cache # Tornar a instância do cache acessível globalmente neste módulo
    cache = cache_instance

    # ... (layout permanece o mesmo da última versão)
    # Copie o layout da sua última versão de upload.py aqui
    global layout # Para que o app.py possa acessá-lo
    layout = dbc.Container([
        dbc.Row(dbc.Col(html.H2([html.I(className="fas fa-upload me-2"), "Upload de Arquivos & Análise Preliminar"], className="mb-4 text-primary"))),
        dbc.Row([
            dbc.Col(
                md=5, sm=12, xs=12,
                children=[
                    dbc.Card([
                        dbc.CardHeader(html.H5([html.I(className="fas fa-file-upload me-2"),"Configurações de Upload"], className="mb-0")),
                        dbc.CardBody([
                            dcc.Upload(
                                id="upload-data-component",
                                children=html.Div([
                                    html.I(className="fas fa-cloud-upload-alt fa-3x mb-2 text-primary"), html.Br(),
                                    "Arraste e solte ou ",
                                    html.A("Selecione Arquivos", className="text-primary", style={"textDecoration": "underline", "cursor": "pointer"})
                                ]),
                                style={
                                    "width": "100%", "height": "150px", "lineHeight": "normal",
                                    "borderWidth": "2px", "borderStyle": "dashed", "borderRadius": "10px",
                                    "textAlign": "center", "padding": "20px", "marginBottom": "20px",
                                    "borderColor": "#adb5bd", "backgroundColor": "#f8f9fa"
                                },
                                multiple=False
                            ),
                            dbc.Label("Delimitador (para CSV):", html_for="csv-delimiter-input", className="fw-bold small"),
                            dbc.InputGroup([
                                dbc.InputGroupText(html.I(className="fas fa-grip-lines me-1"), style={"width": "50px", "justifyContent": "center"}),
                                dbc.Select(
                                    id="csv-delimiter-input",
                                    options=[
                                        {"label": "Vírgula (,)", "value": ","},
                                        {"label": "Ponto e Vírgula (;)", "value": ";"},
                                        {"label": "Tabulação (\\t)", "value": "\t"},
                                        {"label": "Barra Vertical (|)", "value": "|"},
                                    ], value=",",
                                ),
                            ], className="mb-3"),
                            dbc.Label("Linha de Cabeçalho:", html_for="header-row-dropdown", className="fw-bold small"),
                            dbc.InputGroup([
                                dbc.InputGroupText(html.I(className="fas fa-heading me-1"), style={"width": "50px", "justifyContent": "center"}),
                                dbc.Select(id="header-row-dropdown",options=[{"label": "Sim (Primeira linha é cabeçalho)", "value": "0"},{"label": "Não (Sem cabeçalho)", "value": "None"}], value="0"),
                            ], className="mb-3"),
                            dbc.Label("Encoding (para CSV):", html_for="csv-encoding-dropdown", className="fw-bold small"),
                            dbc.InputGroup([
                                dbc.InputGroupText(html.I(className="fas fa-language me-1"), style={"width": "50px", "justifyContent": "center"}),
                                dbc.Select(id="csv-encoding-dropdown", options=[{"label": "Auto-detectar", "value": "auto"},{"label": "UTF-8", "value": "utf-8"},{"label": "ISO-8859-1 (Latin-1)", "value": "iso-8859-1"},{"label": "Windows-1252", "value": "windows-1252"}], value="auto"),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Linhas no Preview:", html_for="preview-n-rows", className="fw-bold small"),
                                    dcc.Dropdown(id="preview-n-rows", options=[{"label": str(n), "value": n} for n in [10, 50, 100, 500, 1000]], value=15, clearable=False, className="mb-2")
                                ], width=12)
                            ]),
                            dbc.Button([html.I(className="fas fa-cogs me-1"), "Processar e Carregar Dados"], id="process-uploaded-file-btn", color="primary", className="w-100", disabled=True, n_clicks=0),
                            html.Div(id="upload-status-message", className="mt-3 text-center small")
                        ])
                    ], className="shadow-sm mb-4 w-100")
                ]
            ),
            dbc.Col(
                md=7, sm=12, xs=12,
                children=[
                    dbc.Card([
                        dbc.CardHeader(html.H5([html.I(className="fas fa-table me-2"), "Preview dos Dados Carregados & Qualidade"], className="mb-0")),
                        dbc.CardBody([
                            dcc.Loading(id="loading-upload-preview",type="default", children=[
                                html.Div(id="uploaded-data-preview-area", className="table-responsive", style={"maxWidth": "100%", "overflowX": "auto", "maxHeight": "300px", "overflowY": "auto"}),
                                html.Hr(id="quality-report-hr", style={'display': 'none'}),
                                html.Div(id="data-quality-report-area")
                            ])
                        ])
                    ], className="shadow-sm w-100")
                ]
            )
        ], className="gy-3")
    ], fluid=True)


    @app.callback(
        Output("upload-status-message", "children"),
        Output("process-uploaded-file-btn", "disabled", allow_duplicate=True),
        Input("upload-data-component", "filename"),
        Input("upload-data-component", "contents"),
        prevent_initial_call='initial_duplicate'
    )
    def update_upload_status_and_button(filename, contents):
        if filename and contents:
            log_info("Arquivo selecionado para upload", extra={"filename": filename, "content_size": len(contents) if contents else 0})
            return html.Div([html.I(className="fas fa-file-alt me-1"), f"Arquivo selecionado: {filename}"], className="text-success"), False
        return "Nenhum arquivo selecionado.", True

    @app.callback(
        Output("process-uploaded-file-btn", "children"),
        Output("process-uploaded-file-btn", "disabled", allow_duplicate=True),
        Input("process-uploaded-file-btn", "n_clicks"),
        State("upload-data-component", "filename"),
        State("upload-data-component", "contents"),
        State("process-uploaded-file-btn", "disabled"),
        prevent_initial_call=True
    )
    def update_button_loading(n_clicks, filename, contents, btn_disabled):
        if n_clicks and filename and contents and not btn_disabled:
            return [dbc.Spinner(size="sm", color="light", children=[" Processando..."])], True
        return [html.I(className="fas fa-cogs me-1"), "Processar e Carregar Dados"], btn_disabled

    @app.callback(
        Output("uploaded-data-preview-area", "children"),
        Output("data-quality-report-area", "children"),
        Output("quality-report-hr", "style"),
        Output('server-side-data-key', 'data', allow_duplicate=True),
        Output('active-connection-name', 'data', allow_duplicate=True),   
        Output('active-table-name', 'data', allow_duplicate=True),         
        Output('data-source-type', 'data', allow_duplicate=True),
        Output("app-toast", "is_open", allow_duplicate=True), 
        Output("app-toast", "children", allow_duplicate=True),
        Output("app-toast", "header", allow_duplicate=True),  
        Output("app-toast", "icon", allow_duplicate=True),    
        Input("process-uploaded-file-btn", "n_clicks"),
        State("upload-data-component", "contents"),
        State("upload-data-component", "filename"),
        State("csv-delimiter-input", "value"),
        State("header-row-dropdown", "value"), 
        State("csv-encoding-dropdown", "value"),
        State("preview-n-rows", "value"),
        prevent_initial_call=True
    )
    def parse_and_display_uploaded_file(n_clicks, contents, filename, delimiter, header_row_str, encoding_choice, preview_n_rows):
        if not n_clicks or n_clicks == 0 or not contents or not filename:
            return ([dash.no_update] * 7) + [False, dash.no_update, dash.no_update, dash.no_update]

        content_type, content_string = contents.split(',')
        decoded_content = base64.b64decode(content_string)
        df = None
        hr_style = {'display': 'none'}
        header_row_val = None
        if header_row_str == "0": header_row_val = 0
        # Se header_row_str for "None" (string), header_row_val permanece None, o que é correto para pd.read_csv

        data_key_to_store = None # Para a chave do cache
        active_conn_name_val = None
        active_table_name_val = None
        data_source_type_val = None
        preview_is_sample = False
        used_dask = False
        dask_rows = None

        try:
            file_extension = filename.split('.')[-1].lower()
            log_info("Iniciando processamento de arquivo", extra={"filename": filename, "file_extension": file_extension, "delimiter": delimiter, "encoding": encoding_choice})
            
            if file_extension == 'csv' and DASK_AVAILABLE:
                # Heurística: se arquivo > 100MB, usar Dask
                if len(decoded_content) > 100*1024*1024:
                    used_dask = True
                    ddf = dd.read_csv(io.BytesIO(decoded_content), delimiter=delimiter, header=header_row_val, encoding=encoding_choice if encoding_choice != 'auto' else 'utf-8', blocksize="16MB")
                    dask_rows = ddf.shape[0].compute()
                    df = ddf.head(preview_n_rows)
                    preview_is_sample = True
                else:
                    enc_to_use = encoding_choice
                    if encoding_choice == 'auto':
                        detected = chardet.detect(decoded_content) 
                        enc_to_use = detected['encoding'] if detected['encoding'] else 'utf-8'
                        log_debug("Encoding detectado automaticamente", extra={"detected_encoding": enc_to_use, "confidence": detected.get('confidence', 0)})
                    df = pd.read_csv(io.BytesIO(decoded_content), delimiter=delimiter, header=header_row_val, encoding=enc_to_use, low_memory=False)
            elif file_extension in ['xls', 'xlsx']:
                df = pd.read_excel(io.BytesIO(decoded_content), header=header_row_val)
            else:
                err_msg = "Tipo de arquivo não suportado."
                log_error("Tipo de arquivo não suportado", extra={"filename": filename, "file_extension": file_extension})
                return dbc.Alert(err_msg,color="danger"),html.Div(),hr_style,None,None,None,None,True,err_msg,"Erro Upload","danger"

            if df is not None and not df.empty:
                log_info("Arquivo carregado com sucesso", extra={"filename": filename, "rows": len(df), "columns": len(df.columns)})
                
                # Inferência aprimorada de tipos de dados
                type_changes = {}
                for col in df.columns:
                    if df[col].isnull().all(): 
                        continue
                    
                    original_type = str(df[col].dtype)
                    
                    if df[col].dtype == 'object':
                        # Tentar converter para numérico primeiro
                        try:
                            numeric_series = pd.to_numeric(df[col], errors='coerce')
                            if not numeric_series.isnull().all():
                                # Verificar se são inteiros ou floats
                                if numeric_series.dropna().apply(lambda x: x.is_integer()).all():
                                    df[col] = numeric_series.astype('Int64')  # Nullable integer
                                    type_changes[col] = f"{original_type} -> Int64"
                                else:
                                    df[col] = numeric_series
                                    type_changes[col] = f"{original_type} -> float64"
                                continue
                        except (ValueError, TypeError):
                            pass
                        
                        # Tentar converter para datetime
                        try:
                            datetime_series = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True)
                            if not datetime_series.isnull().all():
                                # Verificar se pelo menos 50% dos valores são datas válidas
                                valid_dates_ratio = datetime_series.notna().sum() / len(datetime_series.dropna())
                                if valid_dates_ratio > 0.5:
                                    df[col] = datetime_series
                                    type_changes[col] = f"{original_type} -> datetime64[ns]"
                                    continue
                        except (ValueError, TypeError):
                            pass
                        
                        # Verificar se é categórico (menos de 50% de valores únicos)
                        unique_ratio = df[col].nunique() / len(df[col].dropna())
                        if unique_ratio < 0.5 and df[col].nunique() < 100:
                            df[col] = df[col].astype('category')
                            type_changes[col] = f"{original_type} -> category"
                
                if type_changes:
                    log_info("Tipos de dados inferidos e convertidos", extra={"type_changes": type_changes}) 
                
                # Preview aprimorado com informações de tipos
                columns_info = []
                for col in df.columns:
                    col_info = {
                        "name": str(col),
                        "id": str(col),
                        "type": "text"
                    }
                    
                    # Definir tipo de coluna para melhor renderização
                    if pd.api.types.is_numeric_dtype(df[col]):
                        col_info["type"] = "numeric"
                        col_info["format"] = {"specifier": ".2f"} if df[col].dtype == 'float64' else {"specifier": ",d"}
                    elif pd.api.types.is_datetime64_any_dtype(df[col]):
                        col_info["type"] = "datetime"
                    
                    columns_info.append(col_info)
                
                preview_table = create_preview_table(df, max_rows=preview_n_rows, page_size=10)
                
                # Estatísticas básicas por tipo de coluna
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['category']).columns.tolist()
                
                type_summary = html.Div([
                    dbc.Row([
                        dbc.Col(dbc.Badge(f"Numéricas: {len(numeric_cols)}", color="primary", className="me-2"), width="auto"),
                        dbc.Col(dbc.Badge(f"Datas: {len(datetime_cols)}", color="info", className="me-2"), width="auto"),
                        dbc.Col(dbc.Badge(f"Categóricas: {len(categorical_cols)}", color="success", className="me-2"), width="auto"),
                        dbc.Col(dbc.Badge(f"Texto: {len(df.columns) - len(numeric_cols) - len(datetime_cols) - len(categorical_cols)}", color="secondary"), width="auto")
                    ], className="mb-2")
                ])
                
                preview_header = html.Div([
                    html.H5([
                        f"Preview: '{filename}' ({len(df):,} linhas, {len(df.columns)} colunas)",
                        html.Span(" (Amostra)", className="ms-2 text-warning") if preview_is_sample else None,
                        html.Span(" (Dask)", className="ms-2 text-info") if used_dask else None
                    ], className="mb-2"),
                    type_summary
                ])
                preview_output = html.Div([preview_header, preview_table])

                analyzer = DataAnalyzer(df)
                quality_data = analyzer.get_data_quality_report()
                q_cards = dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody([html.H6("Linhas",className="small text-muted text-uppercase"),html.P(f"{quality_data['total_rows']:,}",className="fs-4 fw-bold text-primary")])),width=4,className="mb-2"),
                    dbc.Col(dbc.Card(dbc.CardBody([html.H6("Colunas",className="small text-muted text-uppercase"),html.P(f"{quality_data['total_columns']}",className="fs-4 fw-bold text-primary")])),width=4,className="mb-2"),
                    dbc.Col(dbc.Card(dbc.CardBody([html.H6("Duplicadas",className="small text-muted text-uppercase"),html.P(f"{quality_data['duplicate_rows']}",className="fs-4 fw-bold text-warning" if quality_data['duplicate_rows']>0 else "fs-4 fw-bold text-success")])),width=4,className="mb-2"),
                ])
                missing_data = [{'Col':k,'Ausentes':v['count'],'% Ausente':f"{v['percentage']:.1f}%",'Tipo':str(df[k].dtype)} for k,v in quality_data['missing_data'].items() if v['count']>0]
                missing_tbl = dash_table.DataTable(data=missing_data,columns=[{"name":i,"id":i} for i in ['Col','Ausentes','% Ausente','Tipo']],page_size=5,style_cell={'fontSize':'0.85rem'}) if missing_data else dbc.Alert("Sem dados ausentes significativos!",color="success",className="mt-2")
                quality_output = html.Div([html.H5("Qualidade dos Dados:",className="mt-3 mb-2"),q_cards,html.H6("Dados Ausentes:",className="mt-3"),missing_tbl])
                hr_style = {'display':'block','margin':'20px 0'}
                
                data_key_to_store = str(uuid.uuid4()) # Gerar chave para o cache
                cache.set(data_key_to_store, df, timeout=3600) # Salvar DataFrame no cache

                active_conn_name_val = "Arquivo Carregado"
                active_table_name_val = filename
                data_source_type_val = 'upload'
                
                msg_sucesso = html.Span([
                    html.I(className="fas fa-check-circle me-1 text-success"),
                    f"Arquivo '{filename}' carregado com sucesso: {len(df):,} linhas, {len(df.columns)} colunas.",
                    html.Span(" (Amostra)", className="ms-2 text-warning") if preview_is_sample else None,
                    html.Span(" (Dask)", className="ms-2 text-info") if used_dask else None
                ])
                logger.info("Arquivo processado e armazenado no cache", extra={
                    "filename": filename, 
                    "data_key": data_key_to_store, 
                    "rows": len(df), 
                    "columns": len(df.columns),
                    "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
                })
                return preview_output, quality_output, hr_style, \
                       data_key_to_store, active_conn_name_val, active_table_name_val, data_source_type_val, \
                       True, msg_sucesso, "Upload Sucesso", "success"
            else:
                err_msg = f"Arquivo '{filename}' está vazio."
                logger.warning(err_msg)
                return show_feedback_alert(err_msg, tipo="warning"), html.Div(), hr_style, None, None, None, None, True, err_msg, "Upload Vazio", "warning"
        except Exception as e:
            err_msg = f"Erro ao processar arquivo: {e}"
            logger.error(err_msg, extra={"exception": str(e)})
            return show_feedback_alert(err_msg, tipo="erro"), html.Div(), hr_style, None, None, None, None, True, err_msg, "Erro Upload", "danger"