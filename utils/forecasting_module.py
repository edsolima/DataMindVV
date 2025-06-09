# utils/forecasting_module.py
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple 
import plotly.graph_objects as go # <--- IMPORTADO AQUI
from utils.logger import log_info, log_warning, log_error

# Modelos Locais
from statsmodels.tsa.holtwinters import ExponentialSmoothing
# Para AutoARIMA, você precisará instalar: pip install pmdarima
# import pmdarima as pm 
# Modelos API (Exemplo Groq)
# from groq import Groq # Para API Groq: pip install groq
# import os

def run_local_exponential_smoothing(series: pd.Series, horizon: int) -> Tuple[pd.DataFrame, str]:
    """
    Executa previsão usando Suavização Exponencial (Holt-Winters) localmente.
    Tenta inferir frequência, ajustar sazonalidade e retorna DataFrame com previsões e intervalos de confiança.
    Parâmetros:
        series (pd.Series): Série temporal indexada por datas.
        horizon (int): Número de períodos a prever.
    Retorna:
        Tuple[pd.DataFrame, str]: DataFrame com previsões e mensagem de feedback.
    """
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors='coerce')
        if series.index.isnull().any():
            return pd.DataFrame(), "Coluna de data inválida para Suavização Exponencial."
    
    inferred_freq = pd.infer_freq(series.index)
    if inferred_freq:
        series = series.asfreq(inferred_freq)
    else: 
        log_warning(f"Aviso: Não foi possível inferir frequência para a série temporal '{series.name}'. Resultados podem variar.")

    series = series.dropna()
    if len(series) < 3: 
        return pd.DataFrame(), "Série temporal muito curta para Suavização Exponencial após limpeza."

    seasonal_periods, trend_param, seasonal_param = None, "add", None
    if inferred_freq:
        if 'M' in inferred_freq.upper() and len(series) >= 24: seasonal_periods, seasonal_param = 12, "add"
        elif 'Q' in inferred_freq.upper() and len(series) >= 8: seasonal_periods, seasonal_param = 4, "add"
        elif 'D' in inferred_freq.upper() and len(series) >= 14: seasonal_periods, seasonal_param = 7, "add" 

    try:
        model = ExponentialSmoothing(
            series, trend=trend_param, seasonal=seasonal_param, 
            seasonal_periods=seasonal_periods, initialization_method="estimated"
        ).fit()
        forecast_values = model.forecast(horizon)
        
        forecast_df = pd.DataFrame({'ds': forecast_values.index, 'yhat': forecast_values.values})
        try: 
            if hasattr(model, 'get_prediction'):
                pred_intervals = model.get_prediction(start=len(series), end=len(series)+horizon-1)
                summary_frame = pred_intervals.summary_frame(alpha=0.05) 
                if 'mean_ci_lower' in summary_frame.columns and 'mean_ci_upper' in summary_frame.columns:
                    forecast_df['yhat_lower'] = summary_frame['mean_ci_lower']
                    forecast_df['yhat_upper'] = summary_frame['mean_ci_upper']
                elif 'pi_lower' in summary_frame.columns and 'pi_upper' in summary_frame.columns: 
                    forecast_df['yhat_lower'] = summary_frame['pi_lower']
                    forecast_df['yhat_upper'] = summary_frame['pi_upper']
        except Exception as e_ci:
            log_warning(f"Não foi possível gerar intervalo de confiança para ExpSmoothing:", exception=e_ci)

        return forecast_df, f"Previsão com Suavização Exponencial (Trend: {trend_param}, Sazonal: {seasonal_param or 'Nenhum'})."
    except Exception as e:
        log_error(f"Erro no Exponential Smoothing:", exception=e)
        try: 
            model_simple = ExponentialSmoothing(series, trend="add", initialization_method="estimated").fit()
            forecast_values = model_simple.forecast(horizon)
            forecast_df = pd.DataFrame({'ds': forecast_values.index, 'yhat': forecast_values.values})
            return forecast_df, "Previsão com Suavização Exponencial (Trend Aditivo, Sazonalidade Nenhuma - fallback)."
        except Exception as e_simple:
            return pd.DataFrame(), f"Falha na Suavização Exponencial: {e_simple}"

def run_local_auto_arima(series: pd.Series, horizon: int) -> Tuple[pd.DataFrame, str]:
    """
    Executa previsão usando AutoARIMA localmente (pmdarima).
    Tenta inferir frequência, ajustar sazonalidade e retorna DataFrame com previsões e intervalos de confiança.
    Parâmetros:
        series (pd.Series): Série temporal indexada por datas.
        horizon (int): Número de períodos a prever.
    Retorna:
        Tuple[pd.DataFrame, str]: DataFrame com previsões e mensagem de feedback.
    """
    try: import pmdarima as pm
    except ImportError: return pd.DataFrame(), "Biblioteca 'pmdarima' não instalada (pip install pmdarima)."

    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors='coerce')
        if series.index.isnull().any(): return pd.DataFrame(), "Coluna de data inválida para AutoARIMA."
    
    inferred_freq = pd.infer_freq(series.index)
    if inferred_freq: series = series.asfreq(inferred_freq)
    else: log_warning(f"Aviso: Não foi possível inferir frequência para AutoARIMA da série '{series.name}'.")
    
    series = series.dropna()
    if len(series) < 10: 
        return pd.DataFrame(), "Série temporal muito curta para AutoARIMA."

    m = 1 
    if inferred_freq:
        if 'M' in inferred_freq.upper(): m = 12
        elif 'Q' in inferred_freq.upper(): m = 4
        elif 'W' in inferred_freq.upper(): m = 52 
        elif 'D' in inferred_freq.upper(): m = 7  
            
    try:
        model = pm.auto_arima(
            series, seasonal=(m > 1), m=m, stepwise=True, 
            suppress_warnings=True, error_action='ignore', trace=False,
        )
        forecast_values, conf_int = model.predict(n_periods=horizon, return_conf_int=True)
        
        last_date = series.index[-1]
        future_index = None
        if inferred_freq:
            future_index = pd.date_range(start=last_date, periods=horizon + 1, freq=inferred_freq, inclusive="right")
            if future_index is not None and len(future_index) > 0: 
                 future_index = future_index[1:] if len(future_index) > 1 else future_index 
        
        if future_index is None or len(future_index) != horizon: 
            log_info("Fallback para índice de previsão numérico ou baseado em timedelta.")
            try:
                time_diff = series.index[-1] - series.index[-2] if len(series.index) >=2 else pd.Timedelta(days=1)
                future_index = pd.date_range(start=last_date + time_diff, periods=horizon, freq=time_diff)
            except: 
                future_index = pd.RangeIndex(start=len(series), stop=len(series) + horizon)

        forecast_df = pd.DataFrame({'ds': future_index, 'yhat': forecast_values, 'yhat_lower': conf_int[:, 0], 'yhat_upper': conf_int[:, 1]})
        return forecast_df, f"AutoARIMA: Ordem {model.order}, Sazonal {model.seasonal_order if hasattr(model, 'seasonal_order') and model.seasonal_order else 'N/A'}."
    except Exception as e:
        return pd.DataFrame(), f"Erro no AutoARIMA: {e}"

def run_forecast(df_original: pd.DataFrame, date_col: str, value_col: str, model_choice: str, horizon: int, api_key: Optional[str] = None) -> Tuple[pd.DataFrame, go.Figure, str]:
    """
    Função principal para rodar previsão de séries temporais a partir de um DataFrame.
    Faz limpeza, validação, escolhe modelo e retorna DataFrame de previsão, figura Plotly e feedback.
    Parâmetros:
        df_original (pd.DataFrame): DataFrame original com dados.
        date_col (str): Nome da coluna de datas.
        value_col (str): Nome da coluna de valores.
        model_choice (str): Modelo a ser utilizado ('auto_arima_local', 'exponential_smoothing_local').
        horizon (int): Número de períodos a prever.
        api_key (str, opcional): Chave de API para modelos externos.
    Retorna:
        Tuple[pd.DataFrame, go.Figure, str]: Previsão, gráfico e mensagem de feedback.
    """
    df = df_original.copy(); fig = go.Figure(); feedback = ""; forecast_df_final = pd.DataFrame()
    series_for_plot = pd.Series(dtype='float64') 

    try:
        if date_col not in df.columns or value_col not in df.columns: raise ValueError("Colunas não encontradas.")
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df.dropna(subset=[date_col], inplace=True)
        df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
        df.dropna(subset=[value_col], inplace=True)
        if df.empty: raise ValueError("Dados insuficientes após limpeza (data/valor).")
        
        series = df.set_index(date_col)[value_col].sort_index()
        series_for_plot = series.copy() 

        if not isinstance(series.index, pd.DatetimeIndex): raise ValueError("Índice de data inválido.")
        
        inferred_freq = pd.infer_freq(series.index)
        if inferred_freq:
            series = series.asfreq(inferred_freq)
        else: 
            log_warning(f"Aviso: Não foi possível inferir frequência para '{series.name}'. Alguns modelos podem ter problemas.")

        if model_choice == "auto_arima_local": forecast_df_final, feedback = run_local_auto_arima(series, horizon)
        elif model_choice == "exponential_smoothing_local": forecast_df_final, feedback = run_local_exponential_smoothing(series, horizon)
        else: raise ValueError(f"Modelo '{model_choice}' não reconhecido.")
        
        if forecast_df_final.empty and "Falha" not in feedback and "não instalada" not in feedback :
            feedback = f"Modelo {model_choice} não produziu uma previsão. {feedback}" if feedback else f"Modelo {model_choice} não produziu uma previsão."
    
    except Exception as e:
        log_error(f"Erro em run_forecast:", exception=e)
        import traceback; traceback.print_exc()
        feedback = f"Erro ao gerar previsão: {str(e)}"
    
    if not series_for_plot.empty:
        fig.add_trace(go.Scatter(x=series_for_plot.index, y=series_for_plot.values, mode='lines+markers', name='Histórico', line=dict(color='royalblue'), marker=dict(size=5)))
    elif not df[value_col].empty: 
        fig.add_trace(go.Scatter(x=df[date_col], y=df[value_col], mode='lines+markers', name='Histórico (dados brutos)', line=dict(color='royalblue'), marker=dict(size=5)))

    if not forecast_df_final.empty and 'ds' in forecast_df_final.columns and 'yhat' in forecast_df_final.columns:
        fig.add_trace(go.Scatter(x=forecast_df_final['ds'], y=forecast_df_final['yhat'], mode='lines+markers', name='Previsão', line={'dash': 'dash', 'color': 'darkorange'}, marker=dict(size=5, symbol='x')))
        if 'yhat_lower' in forecast_df_final.columns and 'yhat_upper' in forecast_df_final.columns:
            fig.add_trace(go.Scatter(x=forecast_df_final['ds'],y=forecast_df_final['yhat_upper'],mode='lines',line={'width':0},name='Limite Sup.',showlegend=False))
            fig.add_trace(go.Scatter(x=forecast_df_final['ds'],y=forecast_df_final['yhat_lower'],mode='lines',line={'width':0},fill='tonexty',name='Int. Confiança',fillcolor='rgba(255,165,0,0.2)',showlegend=False))
    
    title_text = f"Previsão para '{value_col}'"
    if not series_for_plot.empty: 
        title_text += f" (Série: {series_for_plot.name or value_col})"
    if model_choice:
        title_text += f" - Modelo: {model_choice.replace('_local','').replace('_',' ').title()}"

    fig.update_layout(title=title_text, xaxis_title="Data", yaxis_title=value_col, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return forecast_df_final, fig, feedback