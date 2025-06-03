# pages/dashboard.py
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import json 

from utils.data_analyzer import DataAnalyzer
# A função load_dataframe_from_store de utils.dataframe_utils não é mais estritamente necessária aqui
# se todos os dados vierem do cache. No entanto, pode ser útil se você tiver
# outros fluxos de dados JSON que precisam ser convertidos em DataFrames.
# from utils.dataframe_utils import load_dataframe_from_store 

# Variável global para a instância do cache
cache = None

# Layout for dashboard page (permanece o mesmo da sua última versão)
layout = dbc.Container([
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
                    ]),
                ])
            ], className="mb-4 shadow-sm"),
            
            dcc.Interval(id="dashboard-interval-component", interval=60000, n_intervals=0, disabled=True),
            dcc.Loading(id="loading-dashboard-content", type="default",
                children=html.Div(id="dashboard-content-area")
            )
        ])
    ])
], fluid=True)

def create_kpi_card(title, value, icon="fas fa-chart-bar", color="primary", note=""):
    return dbc.Col([
        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col(html.I(className=f"{icon} fa-2x text-{color} mb-2 mb-md-0"), width="auto", className="d-none d-md-block"),
                dbc.Col([
                    html.H3(value, className=f"card-title text-{color} mb-1"),
                    html.P(title, className="card-text text-muted mb-0 small text-uppercase fw-bold"),
                    html.P(note, className="card-text text-muted small fst-italic") if note else None
                ])
            ], align="center")
        ]), className="shadow-sm h-100")
    ], md=3, className="mb-3")

def create_chart_card(title, graph_id, icon="fas fa-chart-line"):
    return dbc.Col([
        dbc.Card([
            dbc.CardHeader(html.H5([html.I(className=f"{icon} me-2"), title], className="mb-0")),
            dbc.CardBody(dcc.Loading(dcc.Graph(id=graph_id, style={"height": "350px"})))
        ], className="shadow-sm h-100")
    ], md=6, className="mb-3")

def create_empty_dashboard_layout():
    return dbc.Alert([
        html.H4([html.I(className="fas fa-info-circle me-2"), "Dashboard Vazio"]),
        html.P("Nenhum dado carregado. Por favor, carregue dados para visualizar o dashboard.")
    ], color="info", className="text-center m-3 p-4")

def create_dashboard_layout(df_exists, data_source_name, data_source_type):
    if not df_exists: return create_empty_dashboard_layout()
    kpi_row_1 = dbc.Row(id="kpi-row-1-content", className="mb-3") 
    chart_row_1 = dbc.Row([
        create_chart_card("Distribuição de Coluna Numérica", "dashboard-dist-plot"),
        create_chart_card("Contagem de Categoria", "dashboard-cat-plot"),
    ], className="mb-3")
    chart_row_2 = dbc.Row([
        create_chart_card("Série Temporal (se aplicável)", "dashboard-time-series-plot"),
        create_chart_card("Correlação entre Colunas", "dashboard-corr-plot"),
    ], className="mb-3")
    detail_table_row = dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader(html.H5([html.I(className="fas fa-table me-2"), "Amostra dos Dados Filtrados"])),
            dbc.CardBody(dcc.Loading(html.Div(id="dashboard-detail-table")))
        ], className="shadow-sm"), md=12)
    ], className="mb-3")
    return dbc.Container([
        dbc.Alert(f"Exibindo dados de: {data_source_type} - {data_source_name}", color="primary", className="mb-3 fs-6"),
        kpi_row_1, chart_row_1, chart_row_2, detail_table_row,
    ], fluid=True)

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
         Output("dashboard-date-column-selector", "options"), Output("dashboard-date-column-selector", "disabled")],
        [Input("server-side-data-key", "data")] 
    )
    def populate_filter_dropdowns(data_key): 
        if not data_key: return [], True, [], True
        df = cache.get(data_key) 
        if df is None or df.empty: return [], True, [], True
        
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        date_cols = df.select_dtypes(include=[np.datetime64]).columns.tolist() 
        cat_opts = [{"label":c,"value":c} for c in cat_cols]
        date_opts = [{"label":c,"value":c} for c in date_cols]
        return cat_opts, not bool(cat_opts), date_opts, not bool(date_opts)

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
        Output("dashboard-content-area", "children"),
        [Input("refresh-dashboard-btn", "n_clicks"), Input("dashboard-interval-component", "n_intervals")],
        [State("server-side-data-key", "data"), State("active-connection-name", "data"), 
         State("active-table-name", "data"), State("data-source-type", "data")]
    )
    def generate_initial_dashboard_layout(n_clicks, n_intervals, data_key, conn, table, src_type): 
        if not data_key: return create_empty_dashboard_layout()
        df_check = cache.get(data_key) 
        data_exists = df_check is not None and not df_check.empty
        name = f"{conn} - {table}" if src_type=='database' else table if src_type=='upload' else "N/A"
        return create_dashboard_layout(data_exists, name, src_type)

    @app.callback(
        [Output("kpi-row-1-content", "children"), 
         Output("dashboard-dist-plot", "figure"), Output("dashboard-cat-plot", "figure"),
         Output("dashboard-time-series-plot", "figure"), Output("dashboard-corr-plot", "figure"),
         Output("dashboard-detail-table", "children")],
        [Input("refresh-dashboard-btn", "n_clicks"), Input("dashboard-interval-component", "n_intervals")],
        [State("server-side-data-key", "data"), State("dashboard-filter-column", "value"), 
         State("dashboard-filter-value", "value"), State("dashboard-date-column-selector", "value"),
         State("dashboard-date-range", "start_date"), State("dashboard-date-range", "end_date")]
    )
    def update_dashboard_elements(n_refresh_clicks, n_intervals, data_key, 
                                 filter_col, filter_vals, date_col, start_dt, end_dt):
        ctx = callback_context
        if not ctx.triggered and (n_refresh_clicks == 0 and n_intervals == 0):
             raise dash.exceptions.PreventUpdate

        kpi_placeholder_list = [create_kpi_card("N/D", "-", icon="fas fa-ban", color="light")] * 4
        fig_placeholder = go.Figure().update_layout(annotations=[{'text':'Sem Dados','showarrow':False, 'font_size':12}])
        table_placeholder = dbc.Alert("Sem dados para tabela.", color="info", className="text-center")

        if not data_key: 
            return kpi_placeholder_list, fig_placeholder, fig_placeholder, fig_placeholder, fig_placeholder, table_placeholder

        df_original = cache.get(data_key) 
        if df_original is None or df_original.empty:
            kpi_empty_list = [create_kpi_card("Vazio", "0", icon="fas fa-folder-open", color="light")]*4
            fig_empty = go.Figure().update_layout(annotations=[{'text':'Dados Vazios ou Expirados do Cache','showarrow':False, 'font_size':12}])
            return kpi_empty_list, fig_empty, fig_empty, fig_empty, fig_empty, dbc.Alert("Dados não encontrados no cache ou vazios.", color="warning", className="text-center")

        df = df_original.copy()
        if filter_col and filter_vals and filter_col in df.columns:
            df = df[df[filter_col].isin(filter_vals)]
        if date_col and start_dt and end_dt and date_col in df.columns:
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df.dropna(subset=[date_col], inplace=True)
                start_dt_obj = pd.to_datetime(start_dt, errors='coerce')
                end_dt_obj = pd.to_datetime(end_dt, errors='coerce')
                if pd.NaT not in [start_dt_obj, end_dt_obj]:
                    df = df[(df[date_col] >= start_dt_obj) & (df[date_col] <= end_dt_obj)]
            except Exception as e_date_filter:
                print(f"Erro ao aplicar filtro de data no dashboard: {e_date_filter}")
        
        if df.empty: 
            kpi_filtered_list = [create_kpi_card("Filtrado", "0", icon="fas fa-filter", color="light")]*4
            fig_filtered = go.Figure().update_layout(annotations=[{'text':'Nenhum dado com filtros','showarrow':False, 'font_size':12}])
            return kpi_filtered_list, fig_filtered, fig_filtered, fig_filtered, fig_filtered, dbc.Alert("Nenhum dado corresponde aos filtros aplicados.", color="warning", className="text-center")

        analyzer = DataAnalyzer(df)
        
        kpi_components = [
            create_kpi_card("Linhas Filtradas", f"{len(df):,}", "fas fa-stream", "primary"),
            create_kpi_card("Colunas", f"{len(df.columns)}", "fas fa-columns", "info"),
        ]
        if analyzer.numeric_columns:
             kpi_components.append(create_kpi_card(f"Média de '{analyzer.numeric_columns[0]}'", f"{df[analyzer.numeric_columns[0]].mean():.2f}", "fas fa-calculator", "success"))
        else: kpi_components.append(create_kpi_card("Média Numérica", "N/A", "fas fa-calculator", "light"))
        if analyzer.categorical_columns:
             kpi_components.append(create_kpi_card(f"Únicos em '{analyzer.categorical_columns[0]}'", f"{df[analyzer.categorical_columns[0]].nunique()}", "fas fa-tags", "secondary"))
        else: kpi_components.append(create_kpi_card("Categorias Únicas", "N/A", "fas fa-tags", "light"))

        fig_dist, fig_cat, fig_ts, fig_corr = go.Figure(), go.Figure(), go.Figure(), go.Figure()
        # Colocar placeholders mais informativos
        for fig_empty_pl in [fig_dist, fig_cat, fig_ts, fig_corr]:
            fig_empty_pl.update_layout(annotations=[{'text':'Aguardando dados/configuração','showarrow':False, 'font_size':10}])

        if analyzer.numeric_columns:
            fig_dist = px.histogram(df, x=analyzer.numeric_columns[0], title=f"Dist. de {analyzer.numeric_columns[0]}", marginal="box", template="plotly_white")
            fig_dist.update_layout(bargap=0.1, title_x=0.5, margin=dict(t=50,b=20,l=20,r=20))
        if analyzer.categorical_columns:
            top_n = df[analyzer.categorical_columns[0]].value_counts().nlargest(10)
            fig_cat = px.bar(top_n, x=top_n.index, y=top_n.values, title=f"Top 10 - {analyzer.categorical_columns[0]}", template="plotly_white")
            fig_cat.update_layout(title_x=0.5, margin=dict(t=50,b=20,l=20,r=20))
        if analyzer.datetime_columns and analyzer.numeric_columns:
            try:
                # Certificar que a coluna de data está como datetime
                df[analyzer.datetime_columns[0]] = pd.to_datetime(df[analyzer.datetime_columns[0]], errors='coerce')
                df_ts_resample = df.dropna(subset=[analyzer.datetime_columns[0]]) # Remover NaT antes de resample
                if not df_ts_resample.empty:
                    # Tentar inferir frequência para resample ou usar uma genérica como 'D' ou 'M'
                    inferred_freq = pd.infer_freq(df_ts_resample.set_index(analyzer.datetime_columns[0]).index)
                    resample_freq = inferred_freq if inferred_freq else 'M' # Default para Mensal se não puder inferir
                    
                    df_ts = df_ts_resample.set_index(analyzer.datetime_columns[0]).resample(resample_freq)[analyzer.numeric_columns[0]].sum().reset_index()
                    fig_ts = px.line(df_ts, x=analyzer.datetime_columns[0], y=analyzer.numeric_columns[0], title=f"Série Temporal de {analyzer.numeric_columns[0]} (Soma por {resample_freq})", markers=True, template="plotly_white")
                    fig_ts.update_layout(title_x=0.5, margin=dict(t=50,b=20,l=20,r=20))
            except Exception as e_ts: print(f"Erro TS no dashboard: {e_ts}")
        if len(analyzer.numeric_columns) >= 2:
            corr_m = df[analyzer.numeric_columns].corr()
            fig_corr = px.imshow(corr_m, text_auto=".2f", aspect="auto", title="Correlação", color_continuous_scale='RdBu_r', template="plotly_white", color_continuous_midpoint=0) 
            fig_corr.update_layout(title_x=0.5, margin=dict(t=50,b=20,l=20,r=20))
        
        detail_table_df = df.head(15)
        detail_table = dash_table.DataTable(
            data=detail_table_df.to_dict('records'), columns=[{"name":str(i),"id":str(i)} for i in detail_table_df.columns],
            page_size=10, style_table={'overflowX':'auto','minHeight':'300px'},
            style_cell={'textAlign':'left','padding':'8px','fontSize':'0.9em'},
            style_header={'backgroundColor':'#e9ecef','fontWeight':'bold'}, fixed_rows={'headers':True}
        )
        return kpi_components, fig_dist, fig_cat, fig_ts, fig_corr, detail_table