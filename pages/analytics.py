# pages/analytics.py
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import json 

from utils.data_analyzer import DataAnalyzer
# A função load_dataframe_from_store não será mais usada aqui para o DF principal.
# from utils.dataframe_utils import load_dataframe_from_store 

# Variável global para a instância do cache
cache = None

# Layout for analytics page (permanece o mesmo da última versão)
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2([html.I(className="fas fa-magnifying-glass-chart me-2"), "Análises Detalhadas"], className="mb-4 text-primary"),
            dbc.Card([
                dbc.CardHeader(html.H5([html.I(className="fas fa-cogs me-2"), "Configurar Análise"], className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Tipo de Análise:", html_for="analytics-type-dropdown"),
                            dcc.Dropdown(
                                id="analytics-type-dropdown", 
                                options=[
                                    {"label": "📋 Relatório de Qualidade dos Dados", "value": "quality"},
                                    {"label": "📊 Estatísticas Descritivas", "value": "descriptive"},
                                    {"label": "🔗 Análise de Correlação", "value": "correlation"},
                                    {"label": "📈 Análise de Distribuição", "value": "distribution"},
                                    {"label": "⚠️ Detecção de Outliers", "value": "outliers"},
                                    {"label": "🔍 Análise Comparativa (Agrupada)", "value": "comparative"},
                                    {"label": "📊 Teste t (2 Grupos)", "value": "ttest"},
                                    {"label": "📈 ANOVA (>2 Grupos)", "value": "anova"},
                                    {"label": "🔗 Teste Qui-Quadrado", "value": "chi_square"},
                                ],
                                value="quality", clearable=False
                            )
                        ], md=4, className="mb-2"),
                        dbc.Col([
                            dbc.Label("Agrupar Por (Descritiva/Comparativa/Testes):", html_for="analytics-group-by-column"),
                            dcc.Dropdown(
                                id="analytics-group-by-column", 
                                placeholder="Selecione coluna de agrupamento...",
                                disabled=True 
                            )
                        ], md=4, className="mb-2"),
                        dbc.Col([ 
                            html.Br(), 
                             dbc.Button([html.I(className="fas fa-play-circle me-1"), "Executar Análise"], 
                                       id="analytics-run-btn", color="primary", className="w-100 mt-md-2", n_clicks=0)
                        ], md=4, className="d-flex align-items-md-end") 
                    ]),
                    html.Div(id="analytics-specific-test-options-area", className="mt-3 border-top pt-3")
                ])
            ], className="mb-4 shadow-sm"),
            dcc.Loading(
                id="loading-analytics-results", type="default",
                children=html.Div(id="analytics-results-area", children=[
                    dbc.Alert("Selecione um tipo de análise e clique em 'Executar Análise'.", color="info", className="mt-3 text-center")
                ])
            )
        ])
    ])
], fluid=True)

# ----- Funções de Criação de Conteúdo de Análise (permanecem as mesmas) -----
# (Copie suas funções generate_descriptive_stats_content, generate_correlation_analysis_content, etc., daqui da última resposta)
def create_card_layout(title, children, icon="fas fa-info-circle"):
    return dbc.Card(
        [
            dbc.CardHeader(html.H5([html.I(className=f"{icon} me-2"), title], className="mb-0")),
            dbc.CardBody(children)
        ], className="mb-3 shadow-sm"
    )

def format_datatable(df_to_display, table_id, page_size=10):
    if df_to_display is None or df_to_display.empty:
        return dbc.Alert("Nenhum dado para exibir na tabela.", color="light", className="text-center")
    return dash_table.DataTable(
        id=table_id, data=df_to_display.to_dict('records'),
        columns=[{"name": str(i), "id": str(i)} for i in df_to_display.columns],
        page_size=page_size, style_table={'overflowX': 'auto', 'minWidth': '100%'},
        style_cell={'textAlign': 'left', 'padding': '8px', 'minWidth': '100px', 'maxWidth': '250px', 'whiteSpace': 'normal', 'fontSize': '0.9rem'},
        style_header={'backgroundColor': '#e9ecef', 'fontWeight': 'bold', 'borderBottom': '2px solid black'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
        sort_action="native", filter_action="native", export_format="csv", fixed_rows={'headers': True}
    )

def generate_descriptive_stats_content(analyzer, group_by_col=None):
    content = []
    desc_stats_df = analyzer.get_descriptive_statistics(group_by=group_by_col) 
    if desc_stats_df.empty:
        content.append(dbc.Alert("Nenhuma coluna numérica ou dados para estatísticas.", color="warning"))
    else:
        title = f"Estatísticas Descritivas{' Agrupadas por ' + group_by_col if group_by_col else ' Gerais'}"
        content.append(html.H5(title, className="mb-2"))
        # Ajuste para o reset_index dependendo se é agrupado ou não (MultiIndex)
        if group_by_col and isinstance(desc_stats_df.index, pd.MultiIndex):
             content.append(format_datatable(desc_stats_df.round(3).reset_index(), "desc-stats-table", page_size=15))
        elif not group_by_col: # Estatísticas gerais, o índice é o nome da estatística
            content.append(format_datatable(desc_stats_df.round(3).reset_index().rename(columns={'index':'Estatística'}), "desc-stats-table", page_size=15))
        else: # Agrupado mas não MultiIndex (caso de uma única coluna numérica agrupada)
            content.append(format_datatable(desc_stats_df.round(3).reset_index(), "desc-stats-table", page_size=15))

    cat_stats_dict = analyzer.get_categorical_statistics() 
    if cat_stats_dict:
        content.append(html.Hr())
        content.append(html.H5("Estatísticas de Colunas Categóricas:", className="mt-3 mb-2"))
        for col, stats_df in cat_stats_dict.items():
            content.append(html.H6(f"Coluna: {col}", className="mt-2"))
            content.append(format_datatable(stats_df.reset_index(), f"cat-stats-{col}-table", page_size=5))
            content.append(html.Br())
    return create_card_layout("📊 Estatísticas Descritivas", content if content else dbc.Alert("Nenhuma estatística.", color="info"), icon="fas fa-calculator")

def generate_correlation_analysis_content(analyzer):
    if len(analyzer.numeric_columns) < 2:
        return create_card_layout("🔗 Análise de Correlação", dbc.Alert("São necessárias >= 2 colunas numéricas.", color="warning"), icon="fas fa-link")
    heatmap_fig = analyzer.create_correlation_heatmap() 
    corr_matrix = analyzer.calculate_correlation_matrix() 
    strong_corrs_data = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            val = corr_matrix.iloc[i, j]
            if abs(val) >= 0.7: 
                strong_corrs_data.append({'Coluna 1': corr_matrix.columns[i], 'Coluna 2': corr_matrix.columns[j], 'Correlação': f"{val:.2f}", 'Força': "Forte Positiva" if val > 0 else "Forte Negativa"})
    strong_corrs_table = format_datatable(pd.DataFrame(strong_corrs_data), "strong-corrs-table", page_size=5) if strong_corrs_data else dbc.Alert("Nenhuma correlação forte (|r| >= 0.7) encontrada.", color="info")
    return create_card_layout("🔗 Análise de Correlação", [dcc.Graph(figure=heatmap_fig), html.H6("Correlações Fortes:", className="mt-3"), strong_corrs_table], icon="fas fa-link")

def generate_distribution_analysis_content(analyzer):
    if not analyzer.numeric_columns:
         return create_card_layout("📈 Análise de Distribuição", dbc.Alert("Nenhuma coluna numérica.", color="warning"), icon="fas fa-chart-area")
    dist_fig = analyzer.create_distribution_plots() 
    return create_card_layout("📈 Análise de Distribuição", [dcc.Graph(figure=dist_fig)], icon="fas fa-chart-area")

def generate_outlier_analysis_content(analyzer):
    if not analyzer.numeric_columns:
        return create_card_layout("⚠️ Detecção de Outliers", dbc.Alert("Nenhuma coluna numérica.", color="warning"), icon="fas fa-search-location")
    summary_data, box_plots_components = [], [] 
    for col in analyzer.numeric_columns:
        iqr_info = analyzer.detect_outliers(col, method='iqr') 
        zscore_info = analyzer.detect_outliers(col, method='zscore') 
        summary_data.append({"Coluna": col, "Outliers (IQR)": iqr_info['outlier_count'], "% (IQR)": f"{iqr_info['outlier_percentage']:.2f}%", "Outliers (Z-Score)": zscore_info['outlier_count'], "% (Z-Score)": f"{zscore_info['outlier_percentage']:.2f}%"})
        if (iqr_info['outlier_count'] > 0 or zscore_info['outlier_count'] > 0) and len(box_plots_components) < 3:
            box_fig = analyzer.create_boxplot_analysis(col) 
            box_plots_components.append(html.Div([html.H6(f"Box Plot de '{col}'"), dcc.Graph(figure=box_fig)], className="mb-2"))
    summary_table = format_datatable(pd.DataFrame(summary_data), "outlier-summary-table")
    return create_card_layout("⚠️ Detecção de Outliers", [html.H5("Resumo:"), summary_table, html.Hr(className="my-3") if box_plots_components else html.Div(), html.H5("Detalhes (Box Plots):", className="mb-2") if box_plots_components else html.Div(), html.Div(box_plots_components if box_plots_components else dbc.Alert("Sem outliers para detalhar.", color="info"))], icon="fas fa-search-location")

def generate_quality_report_content(analyzer):
    report_data = analyzer.get_data_quality_report() 
    kpi_cards_content = dbc.Row([
        create_kpi_card("Linhas Totais", f"{report_data['total_rows']:,}", "fas fa-stream", "primary", note=f"{report_data['total_columns']} Colunas"),
        create_kpi_card("Duplicadas", report_data['duplicate_rows'], "fas fa-copy", "warning" if report_data['duplicate_rows'] > 0 else "success"),
        create_kpi_card("Memória (MB)", f"{report_data['memory_usage']:.2f}", "fas fa-memory", "secondary"),
        create_kpi_card("Células Ausentes (%)", f"{(sum(info['count'] for info in report_data['missing_data'].values()) / (report_data['total_rows'] * report_data['total_columns']) * 100 if (report_data['total_rows'] * report_data['total_columns']) > 0 else 0):.2f}%", "fas fa-eraser", "danger" if sum(info['count'] for info in report_data['missing_data'].values()) > 0 else "success")
    ])
    missing_df_data = []
    for col, info in report_data['missing_data'].items():
        if info['count'] > 0:
             missing_df_data.append({'Coluna': col, 'Ausentes': info['count'], '% Ausente': f"{info['percentage']:.2f}%", 'Tipo de Dado': str(analyzer.data[col].dtype)}) # Acessar analyzer.data
    missing_table = format_datatable(pd.DataFrame(missing_df_data), "quality-missing-table") if missing_df_data else dbc.Alert("Nenhum dado ausente.", color="success")
    recommendations = []
    if report_data['duplicate_rows'] > 0: recommendations.append(dbc.ListGroupItem(f"Remover {report_data['duplicate_rows']} linhas duplicadas.", color="warning"))
    high_missing_cols = [col for col, info in report_data['missing_data'].items() if info['percentage'] > 20]
    if high_missing_cols: recommendations.append(dbc.ListGroupItem(f"Colunas com >20% de dados ausentes: {', '.join(high_missing_cols)}. Avalie.", color="danger"))
    if not recommendations: recommendations.append(dbc.ListGroupItem("Boa qualidade de dados (sem recomendações críticas).", color="success"))
    return create_card_layout("📋 Relatório de Qualidade dos Dados", [kpi_cards_content, html.H5("Dados Ausentes:", className="mt-4 mb-2"), missing_table, html.H5("Recomendações:", className="mt-4 mb-2"), dbc.ListGroup(recommendations, flush=True)], icon="fas fa-check-double")

def generate_comparative_analysis_content(analyzer, group_by_col):
    if not group_by_col: return create_card_layout("🔍 Análise Comparativa", dbc.Alert("Selecione 'Agrupar Por'.", color="warning"), icon="fas fa-balance-scale")
    if group_by_col not in analyzer.categorical_columns: return create_card_layout("🔍 Análise Comparativa", dbc.Alert(f"'{group_by_col}' não é categórica.", color="danger"), icon="fas fa-balance-scale")
    if analyzer.data[group_by_col].nunique() > 20: return create_card_layout("🔍 Análise Comparativa", dbc.Alert(f"Muitos grupos em '{group_by_col}' (>20).", color="warning"), icon="fas fa-balance-scale")
    
    grouped_stats_df = analyzer.get_descriptive_statistics(group_by=group_by_col) 
    # Ajuste para reset_index quando o índice é MultiIndex (comum em groupby com múltiplas agregações)
    # ou quando é um índice simples (groupby com uma única agregação ou sem agregação)
    stats_table_df_to_format = grouped_stats_df
    if isinstance(grouped_stats_df.index, pd.MultiIndex) or group_by_col: # Se agrupado, sempre resetar
        stats_table_df_to_format = grouped_stats_df.reset_index()

    stats_table = format_datatable(stats_table_df_to_format, "comparative-stats-table")
    
    graphs = []
    for num_col in analyzer.numeric_columns[:min(len(analyzer.numeric_columns), 2)]:
        fig_box_comp = analyzer.create_boxplot_analysis(numeric_col=num_col, category_col=group_by_col) 
        graphs.append(dcc.Graph(figure=fig_box_comp, className="mb-2"))
        fig_bar_comp = analyzer.create_comparison_chart(metric_col=num_col, category_col=group_by_col, aggregation='mean', chart_type='bar') 
        graphs.append(dcc.Graph(figure=fig_bar_comp, className="mb-2"))
    return create_card_layout(f"🔍 Análise Comparativa por '{group_by_col}'", [html.H5("Estatísticas Agrupadas:"), stats_table, html.Hr(className="my-3") if graphs else "", html.H5("Visualizações Comparativas:", className="mb-2") if graphs else "", html.Div(graphs)], icon="fas fa-balance-scale")

def generate_ttest_content(analyzer, data_col, group_col_selected):
    if not data_col or not group_col_selected:
        return create_card_layout("📊 Teste t", dbc.Alert("Selecione coluna de dados e de grupo.", color="warning"))
    results = analyzer.perform_ttest_ind(data_col, group_col_selected) 
    if results is None:
        return create_card_layout(f"📊 Teste t: {data_col} por {group_col_selected}", dbc.Alert("Não foi possível realizar o Teste t.", color="danger"))
    insights = analyzer.generate_textual_insights(results, "ttest") 
    content = [
        html.H6(f"Comparando '{data_col}' entre '{results.get('group1','G1')}' vs '{results.get('group2','G2')}'"),
        dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.P("Estatística t:"), html.H4(f"{results['t_statistic']:.3f}")]))),
                 dbc.Col(dbc.Card(dbc.CardBody([html.P("Valor-p:"), html.H4(f"{results['p_value']:.3f}")]))),], className="mb-3"),
        html.H6("Interpretação:"),
    ]
    for insight in insights: content.append(dbc.Alert(insight, color="success" if "significativa" in insight and "não" not in insight.lower() else "warning" if "significativa" in insight else "light"))
    return create_card_layout(f"📊 Teste t: {data_col} por {group_col_selected}", content)

def generate_anova_content(analyzer, value_col, group_by_col): # Nova função
    if not value_col or not group_by_col:
        return create_card_layout("📈 ANOVA", dbc.Alert("Selecione coluna de valor (numérica) e coluna de agrupamento (categórica).", color="warning"))
    results = analyzer.perform_anova_oneway(value_col, group_by_col)
    if results is None:
        return create_card_layout(f"📈 ANOVA: {value_col} por {group_by_col}", dbc.Alert("Não foi possível realizar ANOVA. Verifique se há >=2 grupos com dados suficientes.", color="danger"))
    insights = analyzer.generate_textual_insights(results, "anova")
    content = [
        html.H6(f"Comparando médias de '{value_col}' entre grupos de '{group_by_col}' ({results.get('groups_compared', 'N/A')} grupos)"),
        dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.P("Estatística F:"), html.H4(f"{results['f_statistic']:.3f}")]))),
                 dbc.Col(dbc.Card(dbc.CardBody([html.P("Valor-p:"), html.H4(f"{results['p_value']:.3f}")]))),], className="mb-3"),
        html.H6("Interpretação:"),
    ]
    for insight in insights: content.append(dbc.Alert(insight, color="success" if "significativa" in insight and "não" not in insight.lower() else "warning" if "significativa" in insight else "light"))
    return create_card_layout(f"📈 ANOVA: {value_col} por {group_by_col}", content)

def generate_chisquare_content(analyzer, col1, col2): # Nova função
    if not col1 or not col2:
        return create_card_layout("🔗 Teste Qui-Quadrado", dbc.Alert("Selecione duas colunas categóricas.", color="warning"))
    results = analyzer.perform_chi_square_test(col1, col2)
    if results is None:
        return create_card_layout(f"🔗 Teste Qui-Quadrado: {col1} vs {col2}", dbc.Alert("Não foi possível realizar o Teste Qui-Quadrado. Verifique as colunas.", color="danger"))
    insights = analyzer.generate_textual_insights(results, "chi_square")
    content = [
        html.H6(f"Testando associação entre '{col1}' e '{col2}'"),
        dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([html.P("Estatística χ²:"), html.H4(f"{results['chi2_statistic']:.3f}")]))),
                 dbc.Col(dbc.Card(dbc.CardBody([html.P("Valor-p:"), html.H4(f"{results['p_value']:.3f}")]))),
                 dbc.Col(dbc.Card(dbc.CardBody([html.P("Graus de Liberdade:"), html.H4(f"{results['degrees_of_freedom']}")]))), # Adicionado Graus de Liberdade
                ], className="mb-3"),
        html.H6("Interpretação:"),
    ]
    for insight in insights: content.append(dbc.Alert(insight, color="success" if "significativa" in insight and "não" not in insight.lower() else "warning" if "significativa" in insight else "light"))
    return create_card_layout(f"🔗 Teste Qui-Quadrado: {col1} vs {col2}", content)

# MODIFICADO PARA CACHE: Aceita cache_instance
def register_callbacks(app, cache_instance):
    global cache 
    cache = cache_instance

    @app.callback(
        [Output("analytics-group-by-column", "options"), Output("analytics-group-by-column", "disabled"),
         Output("analytics-specific-test-options-area", "children")],
        [Input("server-side-data-key", "data"), Input("analytics-type-dropdown", "value")] # MODIFICADO PARA CACHE
    )
    def update_analysis_options(data_key, analysis_type): # MODIFICADO PARA CACHE
        disable_group_by = analysis_type not in ["descriptive", "comparative", "ttest", "anova"]
        specific_options_children = []
        
        if not data_key: return [], True, None
        df = cache.get(data_key) # MODIFICADO PARA CACHE
        if df is None or df.empty: return [], True, None

        analyzer = DataAnalyzer(df)
        cat_opts = [{"label": col, "value": col} for col in analyzer.categorical_columns]
        num_opts = [{"label": col, "value": col} for col in analyzer.numeric_columns]

        if analysis_type == "ttest":
            specific_options_children = html.Div([
                dbc.Label("Coluna de Dados (Numérica):", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-ttest-data-col", options=num_opts, placeholder="Selecione...", className="mb-2"),
                html.Small("A 'Coluna de Grupo' será a selecionada em 'Agrupar Por' (deve ter 2 categorias).", className="text-muted")
            ])
        elif analysis_type == "anova":
             specific_options_children = html.Div([
                dbc.Label("Coluna de Valor (Numérica):", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-anova-value-col", options=num_opts, placeholder="Selecione...", className="mb-2"),
                html.Small("A 'Coluna de Grupo' será a selecionada em 'Agrupar Por'.", className="text-muted")
            ])
        elif analysis_type == "chi_square":
            specific_options_children = html.Div([
                dbc.Label("Variável Categórica 1:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-chisq-col1", options=cat_opts, placeholder="Selecione...", className="mb-2"),
                dbc.Label("Variável Categórica 2:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-chisq-col2", options=cat_opts, placeholder="Selecione..."),
            ])
        return cat_opts, disable_group_by, specific_options_children

    @app.callback(
        Output("analytics-results-area", "children"),
        [Input("analytics-run-btn", "n_clicks")],
        [State("server-side-data-key", "data"), # MODIFICADO PARA CACHE
         State("analytics-type-dropdown", "value"),
         State("analytics-group-by-column", "value"),
         State("analytics-ttest-data-col", "value"),
         State("analytics-anova-value-col", "value"),
         State("analytics-chisq-col1", "value"), State("analytics-chisq-col2", "value")],
        prevent_initial_call=True
    )
    def run_selected_analysis(n_clicks, data_key, analysis_type, group_by_col, # MODIFICADO PARA CACHE
                              ttest_data_col, anova_value_col, chisq_col1, chisq_col2):
        if not data_key:
            return dbc.Alert("Nenhum dado carregado. Por favor, carregue dados primeiro.", color="warning", className="mt-3")
        
        df = cache.get(data_key) # MODIFICADO PARA CACHE
        if df is None:
             return dbc.Alert("Dados não encontrados no cache ou expirados. Recarregue.", color="danger", className="mt-3")
        if df.empty:
            return dbc.Alert("Os dados carregados estão vazios.", color="info", className="mt-3")

        analyzer = DataAnalyzer(df) 
        try:
            if analysis_type == "quality": return generate_quality_report_content(analyzer)
            elif analysis_type == "descriptive": return generate_descriptive_stats_content(analyzer, group_by_col)
            elif analysis_type == "correlation": return generate_correlation_analysis_content(analyzer)
            elif analysis_type == "distribution": return generate_distribution_analysis_content(analyzer)
            elif analysis_type == "outliers": return generate_outlier_analysis_content(analyzer)
            elif analysis_type == "comparative": return generate_comparative_analysis_content(analyzer, group_by_col)
            elif analysis_type == "ttest":
                return generate_ttest_content(analyzer, ttest_data_col, group_by_col) # group_by_col é a coluna de grupo
            elif analysis_type == "anova":
                return generate_anova_content(analyzer, anova_value_col, group_by_col)
            elif analysis_type == "chi_square":
                return generate_chisquare_content(analyzer, chisq_col1, chisq_col2)
            else: return dbc.Alert("Tipo de análise inválido.", color="warning", className="mt-3")
        except Exception as e:
            print(f"Erro na análise '{analysis_type}': {e}"); import traceback; traceback.print_exc()
            return dbc.Alert(f"Erro em '{analysis_type}': {str(e)}", color="danger", className="mt-3")