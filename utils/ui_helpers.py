"""
Helpers de UI para Dash/Plotly.

Exemplo de uso:
    from utils.ui_helpers import create_preview_table, show_feedback_alert
    preview = create_preview_table(df)
    alert = show_feedback_alert("Arquivo carregado com sucesso!", tipo="success")
"""

from dash import dash_table
import dash_bootstrap_components as dbc
from dash import html
import pandas as pd

def create_preview_table(df: pd.DataFrame, max_rows: int = 15, page_size: int = 10) -> dash_table.DataTable:
    """
    Gera um dash_table.DataTable estilizado para preview de DataFrame.
    Parâmetros:
        df (pd.DataFrame): DataFrame a ser exibido.
        max_rows (int): Número máximo de linhas a mostrar.
        page_size (int): Tamanho da paginação.
    Retorna:
        dash_table.DataTable: Tabela Dash estilizada para preview.
    """
    columns_info = []
    for col in df.columns:
        col_info = {"name": str(col), "id": str(col), "type": "text"}
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["type"] = "numeric"
            col_info["format"] = {"specifier": ".2f"} if df[col].dtype == 'float64' else {"specifier": ",d"}
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            col_info["type"] = "datetime"
        columns_info.append(col_info)
    return dash_table.DataTable(
        data=df.head(max_rows).to_dict('records'),
        columns=columns_info,
        page_size=page_size,
        style_table={'overflowX':'auto','minWidth':'100%'},
        style_cell={'textAlign':'left','padding':'8px','fontSize':'0.85rem'},
        style_header={'backgroundColor':'#e9ecef','fontWeight':'bold','textAlign':'center'},
        style_data_conditional=[
            {'if': {'column_type': 'numeric'},'textAlign': 'right'},
            {'if': {'column_type': 'datetime'},'textAlign': 'center'}
        ],
        fixed_rows={'headers':True},
        tooltip_data=[
            {col: {'value': f'Tipo: {df[col].dtype}', 'type': 'markdown'} for col in df.columns}
            for _ in range(min(max_rows, len(df)))
        ],
        tooltip_duration=None
    )

def show_feedback_alert(msg: str, tipo: str = "info", duration: int = 4000):
    """
    Gera um dbc.Alert padronizado para feedback visual.
    Parâmetros:
        msg (str): Mensagem a ser exibida.
        tipo (str): Tipo do alerta ('success', 'erro', 'warning', 'info').
        duration (int): Duração do alerta em ms.
    Retorna:
        dbc.Alert: Componente visual de alerta.
    """
    color_map = {"success": "success", "erro": "danger", "warning": "warning", "info": "info"}
    color = color_map.get(tipo.lower(), "info")
    return dbc.Alert(msg, color=color, duration=duration, className="mt-2 small") 