# pages/upload.py
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import chardet
from utils.data_analyzer import DataAnalyzer
import json
import uuid # Para gerar chaves de cache

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
            dbc.Col(md=5, children=[
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
                        dbc.Button([html.I(className="fas fa-cogs me-1"), "Processar e Carregar Dados"], id="process-uploaded-file-btn", color="primary", className="w-100", disabled=True, n_clicks=0),
                        html.Div(id="upload-status-message", className="mt-3 text-center small")
                    ])
                ], className="shadow-sm mb-4")
            ]),
            dbc.Col(md=7, children=[
                dbc.Card([
                    dbc.CardHeader(html.H5([html.I(className="fas fa-table me-2"), "Preview dos Dados Carregados & Qualidade"], className="mb-0")),
                    dbc.CardBody([
                        dcc.Loading(id="loading-upload-preview",type="default", children=[
                            html.Div(id="uploaded-data-preview-area", className="table-responsive", style={"maxHeight": "300px", "overflowY": "auto"}),
                            html.Hr(id="quality-report-hr", style={'display': 'none'}),
                            html.Div(id="data-quality-report-area")
                        ])
                    ])
                ], className="shadow-sm")
            ])
        ])
    ], fluid=True)


    @app.callback(
        Output("upload-status-message", "children"),
        Output("process-uploaded-file-btn", "disabled"),
        Input("upload-data-component", "filename"),
        Input("upload-data-component", "contents"),
    )
    def update_upload_status_and_button(filename, contents):
        if filename and contents:
            return html.Div([html.I(className="fas fa-file-alt me-1"), f"Arquivo selecionado: {filename}"], className="text-success"), False
        return "Nenhum arquivo selecionado.", True

    @app.callback(
        Output("uploaded-data-preview-area", "children"),
        Output("data-quality-report-area", "children"),
        Output("quality-report-hr", "style"),
        Output('server-side-data-key', 'data', allow_duplicate=True), # MODIFICADO PARA CACHE
        # Output('stored-dataframe-json', 'data', allow_duplicate=True), # REMOVIDO
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
        prevent_initial_call=True
    )
    def parse_and_display_uploaded_file(n_clicks, contents, filename, delimiter, header_row_str, encoding_choice):
        if not n_clicks or n_clicks == 0 or not contents or not filename: # Adicionado n_clicks == 0
            # Ajustar o número de dash.no_update para corresponder aos Outputs (7 antes do toast)
            return ([dash.no_update] * 7) + [False, dash.no_update, dash.no_update, dash.no_update] 

        content_type, content_string = contents.split(',')
        decoded_content = base64.b64decode(content_string)
        df = pd.DataFrame()
        hr_style = {'display': 'none'}
        header_row_val = None
        if header_row_str == "0": header_row_val = 0
        # Se header_row_str for "None" (string), header_row_val permanece None, o que é correto para pd.read_csv

        data_key_to_store = None # Para a chave do cache
        active_conn_name_val = None
        active_table_name_val = None
        data_source_type_val = None

        try:
            file_extension = filename.split('.')[-1].lower()
            if file_extension == 'csv':
                enc_to_use = encoding_choice
                if encoding_choice == 'auto':
                    detected = chardet.detect(decoded_content) 
                    enc_to_use = detected['encoding'] if detected['encoding'] else 'utf-8'
                df = pd.read_csv(io.BytesIO(decoded_content), delimiter=delimiter, header=header_row_val, encoding=enc_to_use, low_memory=False)
            elif file_extension in ['xls', 'xlsx']:
                df = pd.read_excel(io.BytesIO(decoded_content), header=header_row_val)
            else:
                err_msg = "Tipo de arquivo não suportado."
                return dbc.Alert(err_msg,color="danger"),html.Div(),hr_style,None,None,None,None,True,err_msg,"Erro Upload","danger"

            if not df.empty:
                for col in df.columns:
                    if df[col].isnull().all(): continue
                    if df[col].dtype == 'object':
                        try: df[col] = pd.to_numeric(df[col])
                        except ValueError:
                            try: df[col] = pd.to_datetime(df[col], errors='coerce')
                            except Exception: pass 
                
                preview_table = dash_table.DataTable(
                    data=df.head(15).to_dict('records'), columns=[{"name":str(i),"id":str(i)} for i in df.columns],
                    page_size=10,style_table={'overflowX':'auto','minWidth':'100%'},
                    style_cell={'textAlign':'left','padding':'5px','fontSize':'0.85rem'},
                    style_header={'backgroundColor':'#e9ecef','fontWeight':'bold'},fixed_rows={'headers':True}
                )
                preview_header = html.H5(f"Preview: '{filename}' ({len(df):,}l, {len(df.columns)}c)")
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
                
                success_msg = f"Arquivo '{filename}' processado!"
                return preview_output, quality_output, hr_style, \
                       data_key_to_store, active_conn_name_val, active_table_name_val, data_source_type_val, \
                       True, success_msg, "Upload Concluído", "success"
            else:
                warn_msg = "Arquivo vazio ou não pôde ser lido."
                return dbc.Alert(warn_msg,color="warning"),html.Div(),hr_style,None,None,None,None,True,warn_msg,"Upload","warning"
        except Exception as e:
            err_msg_exc = f"Erro: {str(e)}. Verifique formato/delimitador/encoding."
            print(f"Erro upload {filename}: {e}"); import traceback; traceback.print_exc()
            return dbc.Alert(err_msg_exc,color="danger"),html.Div(),hr_style,None,None,None,None,True,err_msg_exc,"Erro Upload","danger"