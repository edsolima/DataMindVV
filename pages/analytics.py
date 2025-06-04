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
from utils.advanced_analytics import AdvancedAnalytics
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
                                        {"label": "🧩 Análise de Clusters", "value": "cluster"},
                                        {"label": "🔄 Análise de Componentes Principais (PCA)", "value": "pca"},
                                        {"label": "🚨 Detecção de Anomalias", "value": "anomalies"},
                                        {"label": "📅 Decomposição de Séries Temporais", "value": "time_series"},
                                        {"label": "👥 Análise de Coorte", "value": "cohort"},
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
def create_kpi_card(title, value, icon, color, note=None):
    return dbc.Col(dbc.Card([
        dbc.CardBody([
            html.Div([html.I(className=f"{icon} me-2"), html.Span(title)], className="text-muted small"),
            html.H4(value, className="mt-2 mb-0"),
            html.Small(note, className="text-muted") if note else None
        ])
    ], color=color, outline=True, className="shadow-sm"), md=3, className="mb-3")

# Funções para gerar conteúdo das análises avançadas
def generate_cluster_analysis_content(df, cluster_cols, n_clusters):
    if not cluster_cols or len(cluster_cols) < 2:
        return create_card_layout("🧩 Análise de Clusters", dbc.Alert("Selecione pelo menos duas colunas numéricas para clustering.", color="warning"), icon="fas fa-puzzle-piece")
    
    try:
        df_with_clusters, fig = AdvancedAnalytics.perform_cluster_analysis(df, cluster_cols, n_clusters=n_clusters)
        
        # Estatísticas por cluster
        cluster_stats = df_with_clusters.groupby('Cluster')[cluster_cols].agg(['mean', 'count'])
        cluster_stats_reset = cluster_stats.reset_index()
        
        # Formatar para exibição
        cluster_stats_display = format_datatable(cluster_stats_reset, "cluster-stats-table")
        
        # Amostra de dados com clusters
        sample_with_clusters = df_with_clusters.sample(min(10, len(df_with_clusters))).reset_index(drop=True)
        sample_display = format_datatable(sample_with_clusters, "cluster-sample-table")
        
        content = [
            html.H5(f"Análise de Clusters com {n_clusters} grupos", className="mb-3"),
            dcc.Graph(figure=fig),
            html.H5("Estatísticas por Cluster:", className="mt-4 mb-2"),
            cluster_stats_display,
            html.H5("Amostra de Dados com Clusters:", className="mt-4 mb-2"),
            sample_display
        ]
        
        return create_card_layout("🧩 Análise de Clusters", content, icon="fas fa-puzzle-piece")
    except Exception as e:
        return create_card_layout("🧩 Análise de Clusters", dbc.Alert(f"Erro na análise de clusters: {str(e)}", color="danger"), icon="fas fa-puzzle-piece")

def generate_pca_analysis_content(df, pca_cols, n_components):
    if not pca_cols or len(pca_cols) < 2:
        return create_card_layout("🔄 Análise de Componentes Principais", dbc.Alert("Selecione pelo menos duas colunas numéricas para PCA.", color="warning"), icon="fas fa-sync-alt")
    
    try:
        df_pca, fig, explained_variance = AdvancedAnalytics.perform_pca_analysis(df, pca_cols, n_components=n_components)
        
        # Criar tabela de variância explicada
        variance_df = pd.DataFrame({
            'Componente': [f'PC{i+1}' for i in range(len(explained_variance))],
            'Variância Explicada (%)': [f"{var:.2f}%" for var in explained_variance],
            'Variância Acumulada (%)': [f"{sum(explained_variance[:i+1]):.2f}%" for i in range(len(explained_variance))]
        })
        variance_table = format_datatable(variance_df, "pca-variance-table")
        
        # Amostra de dados com componentes principais
        pc_cols = [col for col in df_pca.columns if col.startswith('PC')]
        if pc_cols:
            sample_with_pca = df_pca[pc_cols].head(10).reset_index(drop=True)
            sample_display = format_datatable(sample_with_pca, "pca-sample-table")
        else:
            sample_display = dbc.Alert("Nenhum componente principal gerado.", color="warning")
        
        content = [
            html.H5(f"Análise de Componentes Principais com {n_components} componentes", className="mb-3"),
            dcc.Graph(figure=fig),
            html.H5("Variância Explicada:", className="mt-4 mb-2"),
            variance_table,
            html.H5("Amostra de Componentes Principais:", className="mt-4 mb-2"),
            sample_display,
            html.Hr(),
            html.P("Interpretação: Os componentes principais são combinações lineares das variáveis originais que capturam a maior variância possível nos dados. PC1 é o componente que explica a maior parte da variância, seguido por PC2, e assim por diante.", className="text-muted")
        ]
        
        return create_card_layout("🔄 Análise de Componentes Principais", content, icon="fas fa-sync-alt")
    except Exception as e:
        return create_card_layout("🔄 Análise de Componentes Principais", dbc.Alert(f"Erro na análise PCA: {str(e)}", color="danger"), icon="fas fa-sync-alt")

def generate_anomaly_detection_content(df, anomaly_cols, contamination):
    if not anomaly_cols or len(anomaly_cols) < 1:
        return create_card_layout("🚨 Detecção de Anomalias", dbc.Alert("Selecione pelo menos uma coluna numérica para detecção de anomalias.", color="warning"), icon="fas fa-exclamation-triangle")
    
    try:
        df_anomaly, fig = AdvancedAnalytics.detect_anomalies(df, anomaly_cols, contamination=contamination)
        
        # Estatísticas de anomalias
        anomaly_count = (df_anomaly['Anomalia'] == 'Sim').sum()
        anomaly_percent = (anomaly_count / len(df_anomaly)) * 100
        
        # Amostra de anomalias
        anomalies_sample = df_anomaly[df_anomaly['Anomalia'] == 'Sim'].sample(min(10, anomaly_count)).reset_index(drop=True) if anomaly_count > 0 else pd.DataFrame()
        
        content = [
            html.H5(f"Detecção de Anomalias (Proporção esperada: {contamination:.1%})", className="mb-3"),
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.P("Anomalias Detectadas:", className="text-muted mb-0"),
                    html.H3(f"{anomaly_count}", className="mt-2")
                ])), width=6),
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.P("Percentual de Anomalias:", className="text-muted mb-0"),
                    html.H3(f"{anomaly_percent:.2f}%", className="mt-2")
                ])), width=6)
            ], className="mb-4"),
            dcc.Graph(figure=fig),
            html.H5("Amostra de Anomalias Detectadas:", className="mt-4 mb-2"),
            format_datatable(anomalies_sample, "anomaly-sample-table") if not anomalies_sample.empty else dbc.Alert("Nenhuma anomalia detectada na amostra.", color="info"),
            html.Hr(),
            html.P("Interpretação: As anomalias são pontos de dados que se desviam significativamente do padrão normal. Esses pontos podem representar erros, fraudes, comportamentos incomuns ou eventos raros que merecem atenção especial.", className="text-muted")
        ]
        
        return create_card_layout("🚨 Detecção de Anomalias", content, icon="fas fa-exclamation-triangle")
    except Exception as e:
        return create_card_layout("🚨 Detecção de Anomalias", dbc.Alert(f"Erro na detecção de anomalias: {str(e)}", color="danger"), icon="fas fa-exclamation-triangle")

def generate_time_series_decomposition_content(df, date_col, value_col):
    if not date_col or not value_col:
        return create_card_layout("📅 Decomposição de Séries Temporais", dbc.Alert("Selecione uma coluna de data e uma coluna de valor.", color="warning"), icon="fas fa-chart-line")
    
    try:
        fig = AdvancedAnalytics.perform_time_series_decomposition(df, date_col, value_col)
        
        content = [
            html.H5(f"Decomposição da Série Temporal: {value_col} por {date_col}", className="mb-3"),
            dcc.Graph(figure=fig, style={'height': '800px'}),
            html.Hr(),
            html.P("Interpretação:", className="fw-bold mt-3"),
            html.Ul([
                html.Li("Série Original: Os dados brutos ao longo do tempo."),
                html.Li("Tendência: O componente de longo prazo que indica a direção geral da série."),
                html.Li("Sazonalidade: Padrões cíclicos que se repetem em intervalos regulares."),
                html.Li("Resíduo: O que resta após remover tendência e sazonalidade, representando ruído ou eventos irregulares.")
            ], className="text-muted")
        ]
        
        return create_card_layout("📅 Decomposição de Séries Temporais", content, icon="fas fa-chart-line")
    except Exception as e:
        return create_card_layout("📅 Decomposição de Séries Temporais", dbc.Alert(f"Erro na decomposição da série temporal: {str(e)}", color="danger"), icon="fas fa-chart-line")

def generate_cohort_analysis_content(df, date_col, id_col, value_col, time_unit):
    if not date_col or not id_col:
        return create_card_layout("👥 Análise de Coorte", dbc.Alert("Selecione uma coluna de data e uma coluna de ID.", color="warning"), icon="fas fa-users")
    
    try:
        retention_table, fig = AdvancedAnalytics.create_cohort_analysis(df, date_col, id_col, value_col, time_unit)
        
        # Formatar tabela de retenção para exibição
        retention_display = retention_table.copy() * 100  # Converter para percentual
        retention_display = retention_display.round(1).reset_index()
        retention_display.columns = [str(col) for col in retention_display.columns]  # Converter todos os nomes de colunas para string
        
        content = [
            html.H5(f"Análise de Coorte: {id_col} por {date_col}", className="mb-3"),
            dcc.Graph(figure=fig),
            html.H5("Tabela de Retenção (%):", className="mt-4 mb-2"),
            format_datatable(retention_display, "cohort-table"),
            html.Hr(),
            html.P("Interpretação: A análise de coorte agrupa usuários/clientes que iniciaram no mesmo período e acompanha seu comportamento ao longo do tempo. Cada linha representa uma coorte, e cada coluna representa um período após a entrada. Os valores mostram a taxa de retenção (percentual de usuários que continuam ativos em cada período).", className="text-muted")
        ]
        
        return create_card_layout("👥 Análise de Coorte", content, icon="fas fa-users")
    except Exception as e:
        return create_card_layout("👥 Análise de Coorte", dbc.Alert(f"Erro na análise de coorte: {str(e)}", color="danger"), icon="fas fa-users")
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
        date_opts = [{"label": col, "value": col} for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col]) or 
                     (isinstance(df[col].dtype, object) and pd.to_datetime(df[col], errors='coerce').notna().any())]

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
        elif analysis_type == "cluster":
            specific_options_children = html.Div([
                dbc.Label("Colunas Numéricas para Clustering:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-cluster-cols", options=num_opts, placeholder="Selecione...", multi=True, className="mb-2"),
                dbc.Label("Número de Clusters:", className="mt-2 fw-bold small"),
                dcc.Slider(id="analytics-cluster-number", min=2, max=10, step=1, value=3, marks={i: str(i) for i in range(2, 11)}),
            ])
        elif analysis_type == "pca":
            specific_options_children = html.Div([
                dbc.Label("Colunas Numéricas para PCA:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-pca-cols", options=num_opts, placeholder="Selecione...", multi=True, className="mb-2"),
                dbc.Label("Número de Componentes:", className="mt-2 fw-bold small"),
                dcc.Slider(id="analytics-pca-components", min=2, max=5, step=1, value=2, marks={i: str(i) for i in range(2, 6)}),
            ])
        elif analysis_type == "anomalies":
            specific_options_children = html.Div([
                dbc.Label("Colunas Numéricas para Detecção:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-anomaly-cols", options=num_opts, placeholder="Selecione...", multi=True, className="mb-2"),
                dbc.Label("Proporção Esperada de Anomalias (%):", className="mt-2 fw-bold small"),
                dcc.Slider(id="analytics-anomaly-contamination", min=1, max=10, step=1, value=5, 
                            marks={i: f"{i}%" for i in range(1, 11)}),
            ])
        elif analysis_type == "time_series":
            specific_options_children = html.Div([
                dbc.Label("Coluna de Data:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-ts-date-col", options=date_opts, placeholder="Selecione...", className="mb-2"),
                dbc.Label("Coluna de Valor:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-ts-value-col", options=num_opts, placeholder="Selecione...", className="mb-2"),
            ])
        elif analysis_type == "cohort":
            specific_options_children = html.Div([
                dbc.Label("Coluna de Data:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-cohort-date-col", options=date_opts, placeholder="Selecione...", className="mb-2"),
                dbc.Label("Coluna de ID (Cliente/Usuário):", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-cohort-id-col", options=[{"label": col, "value": col} for col in df.columns], 
                              placeholder="Selecione...", className="mb-2"),
                dbc.Label("Coluna de Valor (opcional):", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-cohort-value-col", options=num_opts, placeholder="Selecione...", className="mb-2", clearable=True),
                dbc.Label("Unidade de Tempo:", className="mt-2 fw-bold small"),
                dcc.Dropdown(id="analytics-cohort-time-unit", options=[
                    {"label": "Dia", "value": "D"},
                    {"label": "Semana", "value": "W"},
                    {"label": "Mês", "value": "M"},
                    {"label": "Trimestre", "value": "Q"},
                    {"label": "Ano", "value": "Y"},
                ], value="M", className="mb-2"),
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
         State("analytics-chisq-col1", "value"), State("analytics-chisq-col2", "value"),
         State("analytics-cluster-cols", "value"), State("analytics-cluster-number", "value"),
         State("analytics-pca-cols", "value"), State("analytics-pca-components", "value"),
         State("analytics-anomaly-cols", "value"), State("analytics-anomaly-contamination", "value"),
         State("analytics-ts-date-col", "value"), State("analytics-ts-value-col", "value"),
         State("analytics-cohort-date-col", "value"), State("analytics-cohort-id-col", "value"),
         State("analytics-cohort-value-col", "value"), State("analytics-cohort-time-unit", "value")],
        prevent_initial_call=True
    )
    def run_selected_analysis(n_clicks, data_key, analysis_type, group_by_col, # MODIFICADO PARA CACHE
                              ttest_data_col, anova_value_col, chisq_col1, chisq_col2,
                              cluster_cols, cluster_number, pca_cols, pca_components,
                              anomaly_cols, anomaly_contamination, ts_date_col, ts_value_col,
                              cohort_date_col, cohort_id_col, cohort_value_col, cohort_time_unit):
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
            elif analysis_type == "cluster":
                return generate_cluster_analysis_content(df, cluster_cols, cluster_number)
            elif analysis_type == "pca":
                return generate_pca_analysis_content(df, pca_cols, pca_components)
            elif analysis_type == "anomalies":
                return generate_anomaly_detection_content(df, anomaly_cols, anomaly_contamination/100)
            elif analysis_type == "time_series":
                return generate_time_series_decomposition_content(df, ts_date_col, ts_value_col)
            elif analysis_type == "cohort":
                return generate_cohort_analysis_content(df, cohort_date_col, cohort_id_col, cohort_value_col, cohort_time_unit)
            else: return dbc.Alert("Tipo de análise inválido.", color="warning", className="mt-3")
        except Exception as e:
            print(f"Erro na análise '{analysis_type}': {e}"); import traceback; traceback.print_exc()
            return dbc.Alert(f"Erro em '{analysis_type}': {str(e)}", color="danger", className="mt-3")