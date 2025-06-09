# pages/ai_chat.py
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
import re # For parsing chart JSON
import numpy as np

# Plotly for chart generation
import plotly.express as px
import plotly.graph_objects as go

from utils.rag_module import prepare_dataframe_for_chat, query_data_with_llm # Ensure these are the updated versions
from utils.logger import log_info, log_error, log_warning, log_debug

cache = None

# Helper to parse chart parameters from LLM response
def extract_chart_params_from_response(text_response: str) -> Optional[Dict]:
    # [cite: 15] LLM returns JSON for chart
    
    # Tentar múltiplos padrões de extração para maior robustez
    patterns = [
        r"CHART_PARAMS_JSON:\s*(\{.*?\})",
        r"```json\s*(\{.*?\})\s*```",
        r'\{[^{}]*"chart_type"[^{}]*\}',
        r'chart_params["\"]?\s*[:=]\s*(\{.*?\})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_response, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = match.group(1)
            try:
                params = json.loads(json_str)
                # Validação aprimorada
                if isinstance(params, dict) and "chart_type" in params:
                    # Validar tipos de gráfico suportados
                    supported_charts = ["bar", "line", "scatter", "pie", "histogram", "boxplot", "heatmap", "area", "violin"]
                    if params["chart_type"].lower() in supported_charts:
                        log_info("Parâmetros de gráfico extraídos com sucesso", extra={
                            "chart_type": params.get("chart_type"),
                            "x_column": params.get("x_column"),
                            "y_column": params.get("y_column"),
                            "pattern_used": pattern
                        })
                        return params
                    else:
                        log_warning("Tipo de gráfico não suportado", extra={"chart_type": params.get("chart_type")})
            except json.JSONDecodeError as e:
                log_debug("Erro ao decodificar JSON de gráfico", extra={"error": str(e), "json_string": json_str[:100]})
                continue
    
    log_debug("Nenhum parâmetro de gráfico válido encontrado na resposta")
    return None

# Helper to generate Plotly charts with improved column interpretation
def generate_plotly_chart(chart_params: Dict, df: pd.DataFrame) -> Optional[go.Figure]:
    try:
        chart_type = chart_params.get("chart_type", "").lower()
        x_col = chart_params.get("x_column")
        y_col = chart_params.get("y_column")
        color_col = chart_params.get("color_column")
        title = chart_params.get("title", f"{chart_type.capitalize()} of {x_col}" + (f" by {y_col}" if y_col else ""))
        
        # Verificar se as colunas existem no DataFrame com sugestões inteligentes
        if not x_col or x_col not in df.columns:
            # Tentar encontrar coluna similar
            similar_cols = [col for col in df.columns if x_col.lower() in col.lower() or col.lower() in x_col.lower()]
            if similar_cols:
                x_col = similar_cols[0]
                log_info("Coluna X substituída por similar", extra={"original": chart_params.get("x_column"), "substituted": x_col})
            else:
                log_error("Coluna X não encontrada no DataFrame", extra={"x_column": x_col, "available_columns": list(df.columns)})
                return None
                
        if y_col and y_col not in df.columns:
            # Tentar encontrar coluna similar
            similar_cols = [col for col in df.columns if y_col.lower() in col.lower() or col.lower() in y_col.lower()]
            if similar_cols:
                y_col = similar_cols[0]
                log_info("Coluna Y substituída por similar", extra={"original": chart_params.get("y_column"), "substituted": y_col})
            else:
                log_warning("Coluna Y não encontrada no DataFrame", extra={"y_column": y_col, "available_columns": list(df.columns)})
                y_col = None  # Continuar sem y_col se possível
                
        if color_col and color_col not in df.columns:
            # Tentar encontrar coluna similar
            similar_cols = [col for col in df.columns if color_col.lower() in col.lower() or col.lower() in color_col.lower()]
            if similar_cols:
                color_col = similar_cols[0]
                log_info("Coluna de cor substituída por similar", extra={"original": chart_params.get("color_column"), "substituted": color_col})
            else:
                log_debug("Coluna de cor não encontrada, ignorando", extra={"color_column": color_col})
                color_col = None
            
        # Detectar automaticamente tipos de colunas para melhor visualização
        column_types = {}
        for col in [x_col, y_col, color_col]:
            if col and col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    column_types[col] = 'numeric'
                elif pd.api.types.is_datetime64_any_dtype(df[col]) or pd.api.types.is_period_dtype(df[col]):
                    column_types[col] = 'datetime'
                    # Garantir que a coluna seja datetime
                    if not pd.api.types.is_datetime64_any_dtype(df[col]):
                        try:
                            df[col] = pd.to_datetime(df[col])
                        except:
                            pass
                else:
                    column_types[col] = 'categorical'

        fig = None
        if chart_type == "bar":
            # Se y_col for numérico, é um gráfico de barras direto. Se não, ou se y_col for None, pode ser uma contagem.
            if y_col:
                # Verificar se x_col é categórico ou datetime para ordenação adequada
                if column_types.get(x_col) == 'datetime':
                    df_sorted = df.sort_values(by=x_col)
                    fig = px.bar(df_sorted, x=x_col, y=y_col, color=color_col, title=title)
                else:
                    # Para colunas categóricas, ordenar por valor de y para melhor visualização
                    if column_types.get(y_col) == 'numeric' and column_types.get(x_col) == 'categorical':
                        # Calcular média ou soma por categoria
                        agg_df = df.groupby(x_col)[y_col].agg('mean').reset_index().sort_values(y_col, ascending=False)
                        fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, 
                                     category_orders={x_col: agg_df[x_col].tolist()})
                    else:
                        fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title)
            else: # Contar ocorrências de x_col se y_col não for especificado
                counts = df[x_col].value_counts().reset_index()
                counts.columns = [x_col, 'count']
                counts = counts.sort_values('count', ascending=False)
                fig = px.bar(counts, x=x_col, y='count', color=color_col, 
                             title=title if title else f"Contagem de {x_col}")
                
        elif chart_type == "line":
            # Verificar se x_col é datetime ou numérico para ordenação adequada
            if column_types.get(x_col) in ['datetime', 'numeric']:
                df_sorted = df.sort_values(by=x_col)
                fig = px.line(df_sorted, x=x_col, y=y_col, color=color_col, title=title, markers=True)
            else:
                fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title, markers=True)
                
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title, 
                           hover_data=df.select_dtypes(include=['number', 'object']).columns[:5].tolist())
            
        elif chart_type == "pie":
            # Pie geralmente usa nomes e valores. Se y_col for numérico, x_col são os nomes.
            if y_col: # y_col são valores, x_col são nomes
                # Agregar dados se necessário
                if len(df[x_col].unique()) > 10:  # Muitas categorias
                    log_info("Muitas categorias para gráfico de pizza, limitando a top 10", extra={
                        "total_categories": len(df[x_col].unique()),
                        "chart_type": "pie"
                    })
                    agg_df = df.groupby(x_col)[y_col].sum().reset_index()
                    agg_df = agg_df.sort_values(y_col, ascending=False).head(10)
                    # Adicionar categoria 'Outros' se necessário
                    if len(df[x_col].unique()) > 10:
                        other_sum = df.groupby(x_col)[y_col].sum().reset_index()
                        other_sum = other_sum[~other_sum[x_col].isin(agg_df[x_col])][y_col].sum()
                        if other_sum > 0:
                            agg_df = pd.concat([agg_df, pd.DataFrame({x_col: ['Outros'], y_col: [other_sum]})], ignore_index=True)
                    fig = px.pie(agg_df, names=x_col, values=y_col, title=title)
                else:
                    fig = px.pie(df, names=x_col, values=y_col, title=title)
            else: # Se não houver y_col, contar ocorrências de x_col
                counts = df[x_col].value_counts().reset_index()
                counts.columns = ['category', 'count']
                # Limitar a 10 categorias para legibilidade
                if len(counts) > 10:
                    other_count = counts.iloc[10:]['count'].sum()
                    counts = counts.iloc[:10]
                    if other_count > 0:
                        counts = pd.concat([counts, pd.DataFrame({'category': ['Outros'], 'count': [other_count]})], ignore_index=True)
                fig = px.pie(counts, names='category', values='count', 
                             title=title if title else f"Distribuição de {x_col}")
                
        elif chart_type == "histogram":
            # Verificar se a coluna é numérica
            if column_types.get(x_col) == 'numeric':
                fig = px.histogram(df, x=x_col, color=color_col, title=title, 
                                  marginal="rug" if y_col else None, y=y_col,
                                  histnorm='probability density' if chart_params.get('normalize') else None)
            else:
                # Para colunas não numéricas, usar contagem de valores
                counts = df[x_col].value_counts().reset_index()
                counts.columns = [x_col, 'count']
                fig = px.bar(counts, x=x_col, y='count', title=title if title else f"Distribuição de {x_col}")
                
        elif chart_type == "boxplot":
            # Verificar se y_col é numérico (necessário para boxplot)
            if y_col and column_types.get(y_col) == 'numeric':
                fig = px.box(df, x=x_col, y=y_col, color=color_col, title=title, 
                            points='outliers')  # Mostrar apenas outliers para reduzir ruído visual
            elif x_col and column_types.get(x_col) == 'numeric':
                # Se apenas x_col for numérico, inverter eixos
                fig = px.box(df, y=x_col, x=y_col, color=color_col, title=title, 
                            points='outliers')
            else:
                log_warning("Boxplot requer pelo menos uma coluna numérica", extra={
                    "x_column": x_col,
                    "y_column": y_col,
                    "x_type": column_types.get(x_col),
                    "y_type": column_types.get(y_col)
                })
                return None
                
        elif chart_type == "heatmap":
            # Heatmap geralmente precisa de uma matriz ou x, y, z.
            if x_col and y_col and chart_params.get("z_column") and chart_params.get("z_column") in df.columns:
                z_col = chart_params.get("z_column")
                # Verificar se z_col é numérico
                if pd.api.types.is_numeric_dtype(df[z_col]):
                    pivot_df = df.pivot_table(index=y_col, columns=x_col, values=z_col, aggfunc='mean')
                    fig = px.imshow(pivot_df, title=title, aspect="auto", labels=dict(color=z_col))
                else:
                    log_warning("Coluna Z deve ser numérica para heatmap", extra={"z_column": z_col, "z_type": str(df[z_col].dtype)})
                    return None
            else: # Default para matriz de correlação de colunas numéricas
                numeric_df = df.select_dtypes(include=['number'])
                if not numeric_df.empty and len(numeric_df.columns) > 1:
                    corr_matrix = numeric_df.corr()
                    fig = px.imshow(corr_matrix, title=title if title else "Matriz de Correlação", 
                                   text_auto=True, aspect="auto", color_continuous_scale='RdBu_r',
                                   zmin=-1, zmax=1)
                else:
                    log_warning("Dados numéricos insuficientes para heatmap de correlação", extra={
                        "numeric_columns": len(numeric_df.columns),
                        "total_columns": len(df.columns)
                    })
                    return None
                    
        elif chart_type == "area":
            # Verificar se x_col é datetime ou numérico para ordenação adequada
            if column_types.get(x_col) in ['datetime', 'numeric']:
                df_sorted = df.sort_values(by=x_col)
                if color_col:  # Área empilhada por categoria
                    fig = px.area(df_sorted, x=x_col, y=y_col, color=color_col, title=title)
                else:  # Área simples
                    fig = px.area(df_sorted, x=x_col, y=y_col, title=title)
            else:
                if color_col:  # Área empilhada por categoria
                    fig = px.area(df, x=x_col, y=y_col, color=color_col, title=title)
                else:  # Área simples
                    fig = px.area(df, x=x_col, y=y_col, title=title)
                    
        elif chart_type == "violin":
            # Verificar se y_col é numérico (necessário para violin plot)
            if y_col and column_types.get(y_col) == 'numeric':
                fig = px.violin(df, x=x_col, y=y_col, color=color_col, title=title, 
                               box=True, points="outliers")
            elif x_col and column_types.get(x_col) == 'numeric':
                # Se apenas x_col for numérico, inverter eixos
                fig = px.violin(df, y=x_col, x=y_col, color=color_col, title=title, 
                               box=True, points="outliers")
            else:
                log_warning("Violin plot requer pelo menos uma coluna numérica", extra={
                    "x_column": x_col,
                    "y_column": y_col,
                    "x_type": column_types.get(x_col),
                    "y_type": column_types.get(y_col)
                })
                return None
        else:
            log_warning("Tipo de gráfico não suportado", extra={"chart_type": chart_type})
            return None

        if fig:
            # Melhorar layout do gráfico
            fig.update_layout(
                title_x=0.5,  # Centralizar título
                paper_bgcolor="rgba(0,0,0,0)",  # Fundo transparente
                plot_bgcolor="rgba(0,0,0,0)",  # Fundo do gráfico transparente
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),  # Legenda horizontal no topo
                margin=dict(l=40, r=40, t=50, b=40),  # Margens reduzidas
                xaxis=dict(showgrid=True, gridcolor='rgba(211,211,211,0.3)'),  # Grade leve no eixo x
                yaxis=dict(showgrid=True, gridcolor='rgba(211,211,211,0.3)')   # Grade leve no eixo y
            )
            
            # Adicionar linha de referência zero para gráficos com eixo y numérico
            if chart_type in ["bar", "line", "scatter", "area"] and y_col and column_types.get(y_col) == 'numeric':
                y_min, y_max = df[y_col].min(), df[y_col].max()
                if y_min < 0 < y_max:  # Se o intervalo cruza zero
                    fig.add_shape(type="line", x0=0, x1=1, y0=0, y1=0,
                                 xref="paper", yref="y", line=dict(color="gray", width=1, dash="dot"))
        return fig

    except Exception as e:
        log_error("Erro ao gerar gráfico Plotly", extra={"error": str(e), "chart_params": chart_params})
        import traceback
        traceback.print_exc()
        return None


layout = dbc.Container([
    dcc.Store(id="ai-chat-index-status-store", storage_type="session", data={"summary_cache_key": None, "status_message": "Nenhum dado preparado.", "original_data_key": None}),
    dcc.Store(id="ai-chat-history-store", storage_type="session", data=[]),
    dcc.Store(id="ai-chat-pending-suggestion-store", storage_type="session", data=None), # For chart suggestions
    dcc.Store(id="ai-chat-generated-charts-store", storage_type="session", data=[]), # [cite: 33, 35] For chart gallery

    dbc.Row(dbc.Col(html.H2([html.I(className="fas fa-comments me-2"), "Assistente de Análise (Chat com Dados)"], className="mb-4 text-primary"))),

    dbc.Row([
        dbc.Col(md=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-cogs me-2"), "Configurações e Ações"])),
                dbc.CardBody([
                    dbc.Alert("Carregue dados (BD/Upload) e depois prepare-os para o chat abaixo.", color="info", id="ai-chat-initial-info", is_open=True, className="small"),
                    html.Div(id="ai-chat-current-data-info", className="mb-3 small text-muted"),

                    dbc.Button([html.I(className="fas fa-brain me-1"), "Preparar Dados Atuais para Chat"],
                               id="ai-chat-prepare-data-btn", color="success", className="w-100 mb-1", n_clicks=0, disabled=True),
                    dcc.Loading(html.Div(id="ai-chat-prepare-status", className="small mt-1 text-center")),

                    html.Hr(),
                    dbc.Button([html.I(className="fas fa-chart-bar me-2"), "Ver Gráficos Gerados"], # [cite: 32]
                               id="ai-chat-view-gallery-btn", color="info", outline=True, className="w-100 mb-3", n_clicks=0),
                    html.Hr(),

                    dbc.Label("Provedor LLM:", html_for="ai-chat-llm-provider", className="fw-bold small"),
                    dcc.Dropdown(id="ai-chat-llm-provider", options=[
                        {"label": "Ollama (Local)", "value": "llama3.2:latest"},
                        {"label": "Groq API", "value": "groq"},
                    ], value="llama3.2:latest", clearable=False, className="mb-2"),

                    html.Div(id="ai-chat-ollama-options", children=[
                        dbc.Label("Modelo Ollama:", html_for="ai-chat-ollama-model", className="fw-bold small"),
                        dbc.Input(id="ai-chat-ollama-model", placeholder="Ex: llama3.2:latest, mistral", value="llama3.2:latest", className="mb-2"),
                    ]),

                    html.Div(id="ai-chat-groq-options", style={'display':'none'}, children=[
                        dbc.Label("Chave API Groq:", html_for="ai-chat-groq-api-key", className="fw-bold small"),
                        dbc.Input(id="ai-chat-groq-api-key", type="password", placeholder="Sua chave API Groq...", className="mb-2"),
                        dbc.Label("Modelo Groq:", html_for="ai-chat-groq-model", className="fw-bold small"),
                        dcc.Dropdown(id="ai-chat-groq-model",
                                     options=[
                                         {"label": "Llama3 8B", "value": "llama3-8b-8192"},
                                         {"label": "Llama3 70B", "value": "llama3-70b-8192"},
                                         {"label": "Mixtral 8x7B", "value": "mixtral-8x7b-32768"},
                                         {"label": "Gemma 7B", "value": "gemma-7b-it"},
                                     ],
                                     value="llama3-8b-8192", className="mb-2"),
                    ]),
                ])
            ], className="shadow-sm sticky-top", style={"top":"80px"})
        ]),

        dbc.Col(md=8, children=[
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-comment-dots me-2"), "Conversa"])),
                dbc.CardBody([
                    dcc.Loading(id="ai-chat-loading-conversation", type="default", children=[
                        html.Div(id="ai-chat-conversation-area", style={
                            "height": "calc(100vh - 380px)", "minHeight": "400px",
                            "overflowY": "auto", "border": "1px solid #dee2e6",
                            "padding": "15px", "borderRadius":"5px", "backgroundColor":"#f8f9fa" # Light background
                        }, children=[dbc.Alert("Configure e prepare os dados para iniciar o chat.", color="light", className="text-center")])
                    ]),
                    dbc.InputGroup([
                        dcc.Textarea(id="ai-chat-user-question", placeholder="Faça uma pergunta sobre seus dados ou peça um gráfico...", className="mt-3", style={"height": "80px", "resize":"none"}),
                        dbc.Button(html.I(className="fas fa-paper-plane fs-5"), id="ai-chat-send-question-btn", color="primary", className="mt-3", n_clicks=0, disabled=True)
                    ], className="mt-2")
                ])
            ], className="shadow-sm")
        ])
    ]),
    # Offcanvas for Chart Gallery [cite: 33]
    dbc.Offcanvas(
        id="ai-chat-charts-gallery-offcanvas",
        title="Galeria de Gráficos Gerados",
        is_open=False,
        placement="end", # Or "start", "top", "bottom"
        backdrop=True,
        scrollable=True,
        style={"width": "60%"} # Adjust width as needed
    )
], fluid=True)


def chat_history_to_html(chat_history_list: List[Dict]) -> List:
    if not chat_history_list:
        return [dbc.Alert("Faça sua primeira pergunta sobre os dados preparados!", color="light", className="text-center p-3")]
    components = []
    for entry in chat_history_list:
        timestamp = entry.get("timestamp", datetime.now().strftime("%H:%M:%S"))
        role = entry.get("role")
        content_type = entry.get("type", "text") # Default to text
        message_content = entry.get("content")

        card_props = {"className": "mb-2 shadow-sm"}
        header_props = {"className": "small text-muted"}
        body_props = {"className": "p-2"}

        if role == "user":
            card_props.update({"color": "primary", "outline": True, "style": {'maxWidth':'80%', "marginLeft": "auto"}})
            header_props["className"] += " text-end pe-2"
            header_text = f"Você ({timestamp})"
            body_content_processed = dcc.Markdown(message_content, className="mb-0")
        elif role == "assistant":
            card_props.update({"style": {'maxWidth':'80%', "marginRight": "auto"}})
            header_props["className"] += " ps-2"
            header_text = f"Assistente IA ({timestamp})"

            if content_type == "error":
                card_props.update({"color": "danger", "outline": False})
                body_content_processed = html.Pre(message_content) if isinstance(message_content, str) else message_content
            elif content_type == "loading":
                card_props.update({"color": "light", "outline": True})
                body_content_processed = html.Div([dbc.Spinner(size="sm", className="me-2"), message_content])
            elif content_type == "chart": # [cite: 5, 27, 29] Inline chart rendering in a card
                card_props.update({"color": "light", "outline": True})
                if isinstance(message_content, go.Figure):
                    body_content_processed = dcc.Graph(figure=message_content, config={'displayModeBar': True, 'scrollZoom': True})
                else: # Should not happen if figure is passed correctly
                    body_content_processed = html.P("Erro ao renderizar gráfico.")
            else: # Default AI text response
                card_props.update({"color": "light", "outline": True})
                body_content_processed = dcc.Markdown(message_content, dangerously_allow_html=False, className="mb-0") # Main AI response
                # Check for chart suggestion in the text itself (the CHART_PARAMS_JSON is for direct generation)
                # For now, chart suggestions are part of the main text from LLM.

        else: # Should not happen
            continue

        components.append(
            dbc.Row(dbc.Col(
                dbc.Card([
                    dbc.CardHeader(header_text, **header_props),
                    dbc.CardBody(body_content_processed, **body_props)
                ], **card_props),
            width=12 )) # Full width for the inner card, outer row controls offset if needed
        )
    return components


def register_callbacks(app, cache_instance):
    global cache
    cache = cache_instance

    @app.callback(
        [Output("ai-chat-groq-options", "style"), Output("ai-chat-ollama-options", "style")],
        Input("ai-chat-llm-provider", "value")
    )
    def toggle_llm_provider_options(provider):
        return ({'display':'block'},{'display':'none'}) if provider=="groq" else ({'display':'none'},{'display':'block'})

    @app.callback(
        [Output("ai-chat-current-data-info", "children"),
         Output("ai-chat-prepare-data-btn", "disabled"),
         Output("ai-chat-initial-info", "is_open"),
         Output("ai-chat-send-question-btn", "disabled"), # Initial state based on data prep
         Output("ai-chat-index-status-store", "data", allow_duplicate=True)],
        [Input("app-url", "pathname"),
         Input("server-side-data-key", "data")], # Main trigger for data change
        [State("active-table-name", "data"),
         State("data-source-type", "data"),
         State("ai-chat-index-status-store", "data")],
        prevent_initial_call='initial_duplicate' # Crucial to prevent issues on load
    )
    def update_current_data_status(pathname, data_key, table_name, source_type, current_index_status):
        if pathname != "/ai-chat":
            log_debug("Não está na página AI Chat, prevenindo atualização")
            raise dash.exceptions.PreventUpdate

        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else "None"
        log_debug("Atualizando status dos dados atuais", extra={
            "triggered_by": triggered_id,
            "data_key": data_key,
            "table_name": table_name,
            "source_type": source_type
        })


        data_info_children = dbc.Alert("Nenhum dado carregado. Vá para 'Dados' ou 'Upload'.",color="info",className="small")
        prepare_btn_disabled = True; initial_info_open = True; send_btn_disabled = True
        index_status_to_set = current_index_status
        if index_status_to_set is None:
            index_status_to_set = {"summary_cache_key": None, "status_message": "Nenhum dado preparado.", "original_data_key": None}

        if not data_key:
            index_status_to_set.update({"summary_cache_key":None,"status_message":"Nenhum dado para preparar.","original_data_key":None})
            return data_info_children, prepare_btn_disabled, initial_info_open, send_btn_disabled, index_status_to_set

        df = cache.get(data_key)
        df_is_valid = df is not None and isinstance(df, pd.DataFrame) and not df.empty

        if df_is_valid:
            info_text = f"Dados atuais: '{table_name or 'DataFrame'}' ({len(df):,}l, {len(df.columns)}c) de '{source_type or 'N/A'}'."
            initial_info_open = False; prepare_btn_disabled = False
            is_prepared = False

            log_info("Dados válidos carregados para AI Chat", extra={
                "table_name": table_name,
                "rows": len(df),
                "columns": len(df.columns),
                "source_type": source_type,
                "data_key": data_key
            })

            # Check if the current data_key matches the one in store and if summary_cache_key is valid
            if current_index_status and \
               current_index_status.get("original_data_key") == data_key and \
               current_index_status.get("summary_cache_key") and \
               cache.has(current_index_status.get("summary_cache_key")): # check if cache still has the RAG index
                is_prepared = True
                log_debug("Dados já preparados para RAG", extra={"summary_cache_key": current_index_status.get("summary_cache_key")})

            if is_prepared:
                status_msg_display = current_index_status.get('status_message', 'Dados preparados e prontos para chat!')
                data_info_children = dbc.Alert(f"{info_text} {status_msg_display}", color="success", className="small")
                send_btn_disabled = False # Enable send if prepared
                index_status_to_set = current_index_status # Keep current status
            else:
                status_msg_display = "Clique em 'Preparar Dados Atuais para Chat' para começar."
                data_info_children = dbc.Alert(info_text + " " + status_msg_display, color="info", className="small")
                send_btn_disabled = True # Disable send if not prepared
                # Reset summary_cache_key if data_key has changed or data is not prepared
                index_status_to_set = {"summary_cache_key":None,"status_message":status_msg_display,"original_data_key":data_key}
        else:
            msg = "Dados não encontrados no cache, vazios ou inválidos. Recarregue.";
            data_info_children = dbc.Alert(msg,color="warning",className="small")
            index_status_to_set.update({"summary_cache_key":None,"status_message":msg,"original_data_key":data_key}) # Update status for this data_key
            send_btn_disabled = True
            log_warning("Dados inválidos ou não encontrados", extra={"data_key": data_key, "df_valid": df_is_valid})

        return data_info_children, prepare_btn_disabled, initial_info_open, send_btn_disabled, index_status_to_set


    @app.callback(
        [Output("ai-chat-prepare-status", "children"),
         Output("ai-chat-index-status-store", "data", allow_duplicate=True),
         Output("ai-chat-send-question-btn", "disabled", allow_duplicate=True)], # Controls send button after prep
        [Input("ai-chat-prepare-data-btn", "n_clicks")],
        [State("server-side-data-key", "data"),
         State("ai-chat-index-status-store", "data")], # Pass current store to preserve original_data_key if needed
        prevent_initial_call=True
    )
    def handle_prepare_data_for_chat(n_clicks, data_key, current_index_status):
        if not data_key:
            log_warning("Tentativa de preparar dados sem data_key válido")
            return dbc.Alert("Nenhum dado principal para preparar.", color="warning"), dash.no_update, True
        df = cache.get(data_key)
        if df is None or df.empty:
            log_error("Dados do cache inválidos para preparação RAG", extra={"data_key": data_key})
            return dbc.Alert("Dados do cache inválidos ou não encontrados. Recarregue.", color="danger"), \
                   {"summary_cache_key":None,"status_message":"Falha ao carregar do cache.","original_data_key":data_key}, True

        log_info("Iniciando preparação de dados para RAG", extra={
            "data_key": data_key,
            "rows": len(df),
            "columns": len(df.columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
        })

        # Call RAG module's prepare function
        # Using force_complete_processing=True as per rag_module.py's updated prepare_dataframe_for_chat default
        success, message, summary_key = prepare_dataframe_for_chat(data_key, df, cache, force_complete_processing=True)

        if success and summary_key:
            log_info("Dados preparados com sucesso para RAG", extra={
                "summary_key": summary_key,
                "data_key": data_key,
                "message": message
            })
            alert_msg = dbc.Alert(message, color="success", duration=4000, className="small")
            # Update store with new summary_key and original_data_key
            new_index_status = {"summary_cache_key": summary_key, "status_message": "Dados preparados!", "original_data_key": data_key}
            return alert_msg, new_index_status, False # Enable send button
        else:
            log_error("Falha ao preparar dados para RAG", extra={
                "data_key": data_key,
                "error_message": message
            })
            alert_msg = dbc.Alert(f"Falha ao preparar dados: {message}", color="danger", className="small")
            # Keep original_data_key, but clear summary_key
            failed_index_status = {"summary_cache_key": None, "status_message": f"Falha: {message}", "original_data_key": data_key}
            return alert_msg, failed_index_status, True # Keep send button disabled


    @app.callback(
        [Output("ai-chat-conversation-area", "children"),
         Output("ai-chat-user-question", "value"),
         Output("ai-chat-history-store", "data"),
         Output("ai-chat-pending-suggestion-store", "data", allow_duplicate=True), # Store LLM's chart suggestions
         Output("ai-chat-generated-charts-store", "data", allow_duplicate=True)], # Add generated charts
        [Input("ai-chat-send-question-btn", "n_clicks")],
        [State("ai-chat-user-question", "value"),
         State("ai-chat-index-status-store", "data"),
         State("ai-chat-llm-provider", "value"),
         State("ai-chat-ollama-model", "value"),
         State("ai-chat-groq-api-key", "value"),
         State("ai-chat-groq-model", "value"),
         State("ai-chat-history-store", "data"),
         State("ai-chat-pending-suggestion-store", "data"), # Get pending suggestions
         State("ai-chat-generated-charts-store", "data"), # Get current list of charts
         State("server-side-data-key", "data")], # For chart generation
        prevent_initial_call=True
    )
    def handle_chat_interaction(n_clicks, user_question, index_status,
                                llm_provider, ollama_model, groq_api_key, groq_model,
                                chat_history_list, pending_suggestion, generated_charts_list,
                                data_key_for_charting): # data_key from server_side_data_store

        if not user_question or not user_question.strip():
            log_debug("Pergunta vazia recebida no chat")
            # If empty, just return current history, don't add new entries
            return chat_history_to_html(chat_history_list), "", chat_history_list, pending_suggestion, generated_charts_list

        summary_key = index_status.get("summary_cache_key") if isinstance(index_status, dict) else None
        original_data_key = index_status.get("original_data_key") if isinstance(index_status, dict) else None
        current_timestamp = datetime.now().strftime("%H:%M:%S")

        log_info("Nova interação de chat iniciada", extra={
            "user_question": user_question[:100] + "..." if len(user_question) > 100 else user_question,
            "llm_provider": llm_provider,
            "model": groq_model if llm_provider == "groq" else ollama_model,
            "summary_key": summary_key,
            "original_data_key": original_data_key
        })

        # Ensure data is prepared before proceeding
        if not summary_key or not cache.has(summary_key) or \
           not original_data_key or not cache.has(original_data_key): # Also check original_data_key in cache
            error_msg = "Dados não preparados ou sumário expirado. Clique em 'Preparar Dados Atuais para Chat'."
            log_warning("Tentativa de chat sem dados preparados", extra={
                "summary_key_exists": bool(summary_key and cache.has(summary_key)),
                "original_data_key_exists": bool(original_data_key and cache.has(original_data_key))
            })
            chat_history_list.append({"role": "user", "content": user_question, "timestamp": current_timestamp})
            chat_history_list.append({"role": "assistant", "content": error_msg, "type": "error", "timestamp": current_timestamp})
            return chat_history_to_html(chat_history_list), "", chat_history_list, None, generated_charts_list # Clear pending suggestion

        # Add user question to history
        chat_history_list.append({"role": "user", "content": user_question, "timestamp": current_timestamp})
        # Add loading message for assistant
        chat_history_list.append({"role": "assistant", "content": "Analisando e respondendo...", "type": "loading", "timestamp": current_timestamp})

        # Determine if this is a chart confirmation (enhanced)
        confirmation_keywords = ["sim", "yes", "ok", "gerar gráfico", "pode gerar", "confirmo", "aceito", "vamos", "faça"]
        is_chart_confirmation = any(keyword in user_question.strip().lower() for keyword in confirmation_keywords) and pending_suggestion

        log_debug("Análise de confirmação de gráfico", extra={
            "is_chart_confirmation": is_chart_confirmation,
            "has_pending_suggestion": bool(pending_suggestion),
            "user_question_lower": user_question.strip().lower()
        })

        new_pending_suggestion = None # Reset for this turn unless a new one is made

        try:
            if is_chart_confirmation:
                chart_params = pending_suggestion # Use the stored suggestion
                ai_response_text = f"Ok, tentando gerar o gráfico sugerido: {chart_params.get('title', 'gráfico')}"
                error_msg_llm = None
                log_info("Confirmação de gráfico recebida", extra={"chart_params": chart_params})
            else:
                # Regular query or new chart request
                log_debug("Enviando pergunta para LLM", extra={
                    "provider": llm_provider,
                    "model": groq_model if llm_provider == "groq" else ollama_model
                })
                ai_response_text, error_msg_llm = query_data_with_llm(
                    summary_key, cache, user_question, llm_provider,
                    ollama_model_name=ollama_model,
                    groq_api_key=groq_api_key, groq_model_name=groq_model
                )
                # Try to extract chart params from this new response
                chart_params = extract_chart_params_from_response(ai_response_text) if not error_msg_llm else None
                
                if chart_params:
                    log_info("Parâmetros de gráfico detectados na resposta LLM", extra={"chart_params": chart_params})


            # Remove loading message
            chat_history_list.pop()
            response_timestamp = datetime.now().strftime("%H:%M:%S")

            if error_msg_llm:
                log_error("Erro na resposta do LLM", extra={"error": error_msg_llm})
                chat_history_list.append({"role":"assistant","content":error_msg_llm,"type":"error","timestamp":response_timestamp})
            else:
                log_info("Resposta do LLM recebida com sucesso", extra={
                    "response_length": len(ai_response_text),
                    "has_chart_params": bool(chart_params)
                })
                chat_history_list.append({"role":"assistant","content":ai_response_text,"type":"ai","timestamp":response_timestamp})
                if chart_params and not is_chart_confirmation : # If LLM suggested & parsed a new chart, store it as pending
                    new_pending_suggestion = chart_params
                    log_debug("Nova sugestão de gráfico armazenada", extra={"suggestion": chart_params})
                    # Optionally, add a small text like "I can generate this chart for you. Say 'yes' or similar."
                    # For now, the main text might contain the suggestion phrase.

            # If chart_params are available (either from new extraction or confirmed suggestion)
            # And we have a valid data_key_for_charting
            if chart_params and data_key_for_charting:
                log_info("Tentando gerar gráfico", extra={
                    "chart_type": chart_params.get("chart_type"),
                    "x_column": chart_params.get("x_column"),
                    "y_column": chart_params.get("y_column"),
                    "data_key": data_key_for_charting
                })
                
                df_for_chart = cache.get(data_key_for_charting)
                if df_for_chart is not None and not df_for_chart.empty:
                    plotly_fig = generate_plotly_chart(chart_params, df_for_chart)
                    if plotly_fig:
                        # Add chart to conversation
                        chart_entry_ts = datetime.now().strftime("%H:%M:%S")
                        chart_title = chart_params.get("title", "Gráfico Gerado")
                        
                        log_info("Gráfico gerado com sucesso", extra={
                            "chart_title": chart_title,
                            "chart_type": chart_params.get("chart_type"),
                            "data_points": len(df_for_chart)
                        })
                        
                        chat_history_list.append({
                            "role": "assistant",
                            "content": plotly_fig, # The actual Plotly Figure object
                            "type": "chart", # Special type for rendering
                            "timestamp": chart_entry_ts,
                            "chart_title": chart_title # Store title for gallery
                        })
                        # Add chart to gallery store [cite: 33]
                        # Storing as JSON for dcc.Store if Figure object is too large or complex
                        generated_charts_list.append({"title": chart_title, "figure_json": plotly_fig.to_json()})
                        new_pending_suggestion = None # Clear suggestion once plotted
                    else:
                        err_msg_chart = f"Desculpe, não consegui gerar o gráfico com os parâmetros: {chart_params}"
                        log_warning("Falha ao gerar gráfico", extra={"chart_params": chart_params})
                        chat_history_list.append({"role":"assistant","content":err_msg_chart,"type":"error","timestamp":datetime.now().strftime("%H:%M:%S")})

                else:
                    err_msg_df = "Não foi possível carregar os dados para gerar o gráfico."
                    log_error("Dados não encontrados para geração de gráfico", extra={"data_key": data_key_for_charting})
                    chat_history_list.append({"role":"assistant","content":err_msg_df,"type":"error","timestamp":datetime.now().strftime("%H:%M:%S")})


        except Exception as e:
            if chat_history_list and chat_history_list[-1].get("type") == "loading": # Ensure loading is popped
                chat_history_list.pop()
            err_str=f"Erro durante o processamento do chat: {e}"
            response_timestamp=datetime.now().strftime("%H:%M:%S")
            chat_history_list.append({"role":"assistant","content":err_str,"type":"error","timestamp":response_timestamp})
            
            log_error("Erro crítico durante processamento do chat", extra={
                "error": str(e),
                "user_question": user_question,
                "llm_provider": llm_provider,
                "summary_key": summary_key,
                "traceback": __import__('traceback').format_exc()
            })

        return chat_history_to_html(chat_history_list), "", chat_history_list, new_pending_suggestion, generated_charts_list

    # Callback for chart gallery [cite: 32, 34]
    @app.callback(
        [Output("ai-chat-charts-gallery-offcanvas", "is_open"),
         Output("ai-chat-charts-gallery-offcanvas", "children")],
        [Input("ai-chat-view-gallery-btn", "n_clicks"),
         Input("ai-chat-generated-charts-store", "data")], # Update when new charts are added
        [State("ai-chat-charts-gallery-offcanvas", "is_open")],
        prevent_initial_call=True
    )
    def toggle_and_populate_charts_gallery(n_clicks_btn, generated_charts_data, is_open_state):
        log_debug("Callback da galeria de gráficos acionado", extra={
            "n_clicks": n_clicks_btn,
            "charts_count": len(generated_charts_data) if generated_charts_data else 0,
            "is_open": is_open_state
        })
        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        new_is_open_state = is_open_state
        if triggered_id == "ai-chat-view-gallery-btn" and n_clicks_btn:
            new_is_open_state = not is_open_state

        if not generated_charts_data:
            gallery_content = [dbc.Alert("Nenhum gráfico foi gerado nesta sessão ainda.", color="info")]
        else:
            gallery_content = [html.H5("Gráficos Gerados na Sessão")]
            for idx, chart_data in enumerate(reversed(generated_charts_data)): # Show newest first
                try:
                    fig = go.Figure(json.loads(chart_data["figure_json"]))
                    title = chart_data.get("title", f"Gráfico {len(generated_charts_data) - idx}")
                    gallery_content.append(
                        dbc.Card([
                            dbc.CardHeader(title),
                            dbc.CardBody(dcc.Graph(figure=fig, style={"height": "300px"})) # Smaller height for gallery view
                        ], className="mb-3")
                    )
                except Exception as e_fig:
                    gallery_content.append(dbc.Alert(f"Erro ao carregar gráfico: {e_fig}", color="danger"))
        
        # Only update if the button was clicked or if the charts data changed while gallery is open
        if triggered_id == "ai-chat-view-gallery-btn" or (triggered_id == "ai-chat-generated-charts-store" and new_is_open_state) or (not triggered_id and new_is_open_state): # last for initial open if any charts
             return new_is_open_state, gallery_content
        
        return dash.no_update, dash.no_update # Default: no change