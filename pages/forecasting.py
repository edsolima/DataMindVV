# pages/forecasting.py
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go 
import json
import numpy as np # Necessário para np.number

# A função load_dataframe_from_store não será mais usada aqui para o DF principal.
# from utils.dataframe_utils import load_dataframe_from_store 
from utils.forecasting_module import run_forecast 

# Variável global para a instância do cache
cache = None

layout = dbc.Container([
    html.Div(id="forecast-page-loaded-signal", style={'display':'none'}),
    dbc.Row(dbc.Col(html.H2([html.I(className="fas fa-chart-line me-2"), "Previsão de Séries Temporais"], className="mb-4 text-primary"))),
    
    dbc.Row([
        dbc.Col(md=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-sliders-h me-2"), "Configurar Previsão"])),
                dbc.CardBody([
                    dbc.Label("Coluna de Data/Período:", html_for="forecast-date-col", className="fw-bold small"),
                    dcc.Dropdown(id="forecast-date-col", placeholder="Selecione coluna de data...", className="mb-3"),
                    
                    dbc.Label("Coluna de Valor a Prever (Numérica):", html_for="forecast-value-col", className="fw-bold small"),
                    dcc.Dropdown(id="forecast-value-col", placeholder="Selecione coluna de valor...", className="mb-3"),
                    
                    dbc.Label("Número de Períodos Futuros para Previsão:", html_for="forecast-horizon", className="fw-bold small"),
                    dbc.Input(id="forecast-horizon", type="number", value=12, min=1, step=1, className="mb-3"),
                    
                    dbc.Label("Modelo de Previsão:", html_for="forecast-model-choice", className="fw-bold small"),
                    dcc.Dropdown(id="forecast-model-choice", options=[
                        {"label": "Auto ARIMA (Local)", "value": "auto_arima_local"},
                        {"label": "Suavização Exponencial (Local)", "value": "exponential_smoothing_local"},
                        # {"label": "Groq API Llama (Requer Chave)", "value": "groq_llama"}, 
                    ], value="auto_arima_local", clearable=False, className="mb-3"),
                                        
                    dbc.Button([html.I(className="fas fa-cogs me-1"), "Gerar Previsão"], id="forecast-run-btn", color="primary", className="w-100", n_clicks=0)
                ])
            ], className="shadow-sm sticky-top", style={"top":"80px"})
        ]),
        dbc.Col(md=8, children=[
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-bullseye me-2"), "Resultados da Previsão"])),
                dbc.CardBody([
                    dcc.Loading(id="loading-forecast-results", type="default", children=[
                        html.Div(id="forecast-results-area", children=[
                            dbc.Alert("Configure os parâmetros e clique em 'Gerar Previsão' para ver os resultados.", color="info", className="text-center m-3 p-3")
                        ])
                    ])
                ])
            ], className="shadow-sm")
        ])
    ])
], fluid=True)

# MODIFICADO PARA CACHE: Aceita cache_instance
def register_callbacks(app, cache_instance):
    global cache 
    cache = cache_instance

    @app.callback(
        [Output("forecast-date-col", "options"), Output("forecast-value-col", "options")],
        [Input("forecast-page-loaded-signal", "children"), 
         Input("server-side-data-key", "data")] # MODIFICADO PARA CACHE
    )
    def update_forecast_column_selectors(_, data_key): # MODIFICADO PARA CACHE
        if not data_key: return [], []
        df = cache.get(data_key) # MODIFICADO PARA CACHE
        if df is None or df.empty: return [], []
        
        date_cols = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]): 
                date_cols.append(col)
            elif df[col].dtype == 'object':
                try:
                    # Verifica se pelo menos metade dos valores não nulos podem ser convertidos para data
                    temp_series = pd.to_datetime(df[col], errors='coerce')
                    if temp_series.notna().sum() > 0.5 * len(df[col].dropna()): 
                        date_cols.append(col)
                except: pass

        num_cols = df.select_dtypes(include=np.number).columns.tolist()
        date_options = [{"label":col, "value":col} for col in date_cols]
        value_options = [{"label":col, "value":col} for col in num_cols]
        return date_options, value_options

    @app.callback(
        Output("forecast-results-area", "children"),
        Input("forecast-run-btn", "n_clicks"),
        [State("server-side-data-key", "data"), # MODIFICADO PARA CACHE
         State("forecast-date-col", "value"),
         State("forecast-value-col", "value"), 
         State("forecast-horizon", "value"),
         State("forecast-model-choice", "value")],
        prevent_initial_call=True
    )
    def display_forecast_results(n_clicks, data_key, date_col, value_col, horizon, model_choice): # MODIFICADO PARA CACHE
        if not data_key or not date_col or not value_col or not horizon or horizon <=0 :
            return dbc.Alert("Por favor, preencha todos os campos de configuração corretamente.", color="warning", duration=4000)
        
        df = cache.get(data_key) # MODIFICADO PARA CACHE
        if df is None or df.empty:
            return dbc.Alert("Dados não encontrados no cache, vazios ou expirados. Recarregue os dados.", color="danger", duration=4000)
        
        try:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            if df[date_col].isnull().all():
                raise ValueError(f"A coluna de data '{date_col}' não pôde ser convertida para um formato de data válido ou está toda vazia.")
        except Exception as e_date:
            return dbc.Alert(f"Erro ao processar coluna de data '{date_col}': {e_date}", color="danger")
            
        forecast_df_final, fig, feedback_msg = run_forecast(df, date_col, value_col, model_choice, int(horizon))
        
        alert_color = "success"
        if "erro" in feedback_msg.lower() or "falha" in feedback_msg.lower() or forecast_df_final.empty:
            alert_color = "danger"
        elif "não instalada" in feedback_msg.lower() or "não implementada" in feedback_msg.lower():
            alert_color = "warning"
            if forecast_df_final.empty and fig is None: 
                 fig = go.Figure().update_layout(title_text=f"Previsão para '{value_col}'", annotations=[{'text':feedback_msg,'showarrow':False}])

        output_content = [dbc.Alert(feedback_msg, color=alert_color, duration=None if alert_color != "success" else 8000)]
        if fig: 
            output_content.append(dcc.Graph(figure=fig))
        
        if not forecast_df_final.empty:
            df_display = forecast_df_final.copy()
            for col_name_display in df_display.select_dtypes(include=np.number).columns: # Renomeado para evitar conflito
                df_display[col_name_display] = df_display[col_name_display].round(2)
            if 'ds' in df_display.columns and pd.api.types.is_datetime64_any_dtype(df_display['ds']):
                 df_display['ds'] = df_display['ds'].dt.strftime('%Y-%m-%d %H:%M:%S') if any(t.hour or t.minute or t.second for t in df_display['ds'] if pd.notna(t)) else df_display['ds'].dt.strftime('%Y-%m-%d')


            output_content.extend([
                html.H6("Dados Previstos (Amostra):", className="mt-3"),
                dash_table.DataTable(
                    data=df_display.head().to_dict('records'), 
                    columns=[{'name': i, 'id': i} for i in df_display.columns],
                    page_size=5, style_header={'fontWeight': 'bold'}, style_table={'overflowX': 'auto'}
                )
            ])
        elif not fig : 
            pass
            
        return html.Div(output_content)