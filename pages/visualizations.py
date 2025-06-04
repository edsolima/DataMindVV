# pages/visualizations.py
import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL 
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import json 

# Importar classes de visualizações e análises avançadas
from utils.advanced_visualizations import AdvancedVisualizations

# A função load_dataframe_from_store de utils.dataframe_utils não será mais usada aqui
# para carregar o DataFrame principal, pois ele virá do cache do servidor.
# from utils.dataframe_utils import load_dataframe_from_store 

# Variável global para a instância do cache, será definida em register_callbacks
cache = None

layout = dbc.Container([
    # html.Div(id="viz-page-loaded-signal", style={'display':'none'}), # Pode ser útil para triggers de carga inicial específicos da página
    dbc.Row([
        dbc.Col([
            html.H2([html.I(className="fas fa-paint-brush me-2"), "Visualizações Interativas"], className="mb-4 text-primary"),
            
            dbc.Row([
                dbc.Col(md=4, children=[ 
                    dbc.Card([
                        dbc.CardHeader(html.H5([html.I(className="fas fa-tools me-2"), "Configurar Gráfico"], className="mb-0")),
                        dbc.CardBody([
                            dbc.Label("Tipo de Gráfico:", html_for="viz-chart-type-dropdown"),
                            dcc.Dropdown(
                                id="viz-chart-type-dropdown",
                                options=[
                                    # Gráficos Básicos
                                    {"label": "📊 Gráfico de Barras", "value": "bar"},
                                    {"label": "📈 Gráfico de Linha", "value": "line"},
                                    {"label": "↔️ Gráfico de Dispersão", "value": "scatter"},
                                    {"label": "🥧 Gráfico de Pizza", "value": "pie"},
                                    {"label": "🔥 Heatmap (Correlação/Pivot)", "value": "heatmap"},
                                    {"label": "📦 Box Plot", "value": "box"},
                                    {"label": "📊 Histograma", "value": "histogram"},
                                    {"label": "🎻 Violin Plot", "value": "violin"},
                                    # Gráficos Avançados
                                    {"label": "🌳 Treemap (Hierárquico)", "value": "treemap"},
                                    {"label": "☀️ Sunburst (Gráfico Solar)", "value": "sunburst"},
                                    {"label": "⏬ Funil de Conversão", "value": "funnel"},
                                    {"label": "🌊 Gráfico de Cascata", "value": "waterfall"},
                                    {"label": "🕸️ Gráfico Radar", "value": "radar"},
                                    {"label": "🔀 Diagrama de Sankey", "value": "sankey"},
                                    {"label": "🎯 Gráfico de Bala", "value": "bullet"},
                                    {"label": "📊 Análise de Pareto", "value": "pareto"},
                                    {"label": "📅 Mapa de Calor Calendário", "value": "calendar"}
                                ],
                                value="bar", clearable=False, className="mb-3"
                            ),
                            dcc.Loading(type="default", children=html.Div(id="viz-chart-specific-options-area", className="mb-3")),
                            dbc.Button([html.I(className="fas fa-check-circle me-1"), "Gerar Gráfico"], id="viz-create-chart-btn", color="primary", className="w-100 mb-2", n_clicks=0),
                            dbc.Button([html.I(className="fas fa-eraser me-1"), "Limpar Gráfico"], id="viz-clear-chart-btn", color="secondary", className="w-100", n_clicks=0)
                        ])
                    ], className="shadow-sm sticky-top", style={"top": "80px", "zIndex": "1000"}),
                ]),
                
                dbc.Col(md=8, children=[ 
                    dbc.Card([
                        dbc.CardHeader(html.H5([html.I(className="fas fa-chart-area me-2"), "Visualização Principal"], className="mb-0")),
                        dbc.CardBody([
                            dcc.Loading(id="viz-loading-main-chart", children=[
                                dcc.Graph(id="viz-main-chart", style={"height": "500px"}),
                                html.Div(id="viz-chart-feedback-message")
                            ], type="default")
                        ])
                    ], className="shadow-sm mb-4"),
                    html.Div(id="viz-filters-panel-area", className="mb-4"),
                    dcc.Loading(type="default", children=html.Div(id="viz-drill-down-area", className="mb-4")) # Adicionado Loading ao drilldown
                ])
            ])
        ])
    ])
], fluid=True)

# ----- Funções Auxiliares (permanecem as mesmas da última versão) -----
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

def create_card_layout(title, children, icon="fas fa-info-circle"):
    return dbc.Card([
        dbc.CardHeader(html.H5([html.I(className=f"{icon} me-2"), title], className="mb-0")),
        dbc.CardBody(children)
    ], className="mb-3 shadow-sm")
    
def create_dynamic_filter_components(df):
    if df is None or df.empty: return [], [] # Adicionada checagem de df is None
    filters_layout = []
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    cols_for_filtering = [col for col in categorical_cols if 1 < df[col].nunique() < 25][:4] 
    for i, col_name in enumerate(cols_for_filtering):
        unique_vals = sorted(df[col_name].dropna().unique())
        options = [{"label": str(val), "value": val} for val in unique_vals]
        filters_layout.append(
            dbc.Col([
                dbc.Label(f"Filtrar por {col_name}:", html_for={"type": "dynamic-filter-dropdown", "index": col_name}),
                dcc.Dropdown(id={"type": "dynamic-filter-dropdown", "index": col_name}, options=options, multi=True, placeholder=f"Selecionar {col_name}...")
            ], md=3, className="mb-2")
        )
    if not filters_layout: return [dbc.Alert("Nenhuma coluna para filtros rápidos.", color="info", className="text-center")], []
    return [dbc.Card([dbc.CardHeader(html.H6([html.I(className="fas fa-filter me-2"), "Filtros Rápidos"], className="mb-0")), dbc.CardBody(dbc.Row(filters_layout))], className="shadow-sm")], cols_for_filtering

# MODIFICADO PARA CACHE: Aceita cache_instance
def register_callbacks(app, cache_instance):
    global cache 
    cache = cache_instance

    @app.callback(
        Output("viz-chart-specific-options-area", "children"),
        [Input("viz-chart-type-dropdown", "value"), 
         Input("server-side-data-key", "data")] # MODIFICADO PARA CACHE
    )
    def render_chart_specific_options(chart_type, data_key): # MODIFICADO PARA CACHE
        if not data_key: return dbc.Alert("Carregue dados para ver as opções.", color="warning", className="text-center p-3")
        df = cache.get(data_key) # MODIFICADO PARA CACHE
        if df is None: return dbc.Alert("Dados não encontrados no cache. Recarregue.", color="danger", className="text-center p-3")
        if df.empty: return dbc.Alert("Os dados carregados estão vazios.", color="info", className="text-center p-3")

        all_c = [{"label": col, "value": col} for col in df.columns]
        num_c = [{"label": col, "value": col} for col in df.select_dtypes(include=np.number).columns]
        cat_c = [{"label": col, "value": col} for col in df.select_dtypes(include=['object', 'category']).columns]
        layout_opts = []
        def create_opt_dropdown(label, opt_name, options, placeholder=None, value=None, multi=False, clearable=True):
            return [dbc.Label(label, html_for={"type": "viz-opt", "index": opt_name}), 
                    dcc.Dropdown(id={"type": "viz-opt", "index": opt_name}, options=options, placeholder=placeholder, value=value, multi=multi, clearable=clearable, className="mb-2")]
        # Opções para gráficos básicos
        if chart_type in ["bar", "line", "scatter", "box", "violin", "histogram", "heatmap", "funnel", "waterfall", "pareto", "calendar"]:
            layout_opts.extend(create_opt_dropdown("Eixo X / Categoria:", "x", all_c, "Obrigatório"))
        
        if chart_type in ["bar", "line", "scatter", "box", "violin", "heatmap", "funnel", "waterfall", "radar", "bullet", "pareto", "calendar"]:
            layout_opts.extend(create_opt_dropdown("Eixo Y / Valor:", "y", num_c if chart_type not in ["bar", "funnel"] else all_c, "Opcional para Contagem (Barra) / Obrigatório para outros"))
        
        # Opções para gráficos de pizza, treemap e sunburst
        if chart_type in ["pie", "treemap", "sunburst"]:
            layout_opts.extend(create_opt_dropdown("Nomes (Categorias):", "names", cat_c, "Obrigatório"))
            layout_opts.extend(create_opt_dropdown("Valores:", "values", num_c, "Obrigatório"))
        
        # Opções de agregação
        if chart_type in ["bar", "line", "heatmap", "pie", "treemap", "sunburst", "pareto"]:
             layout_opts.append(dbc.Label("Função de Agregação:", html_for={"type": "viz-opt", "index": "agg"}))
             layout_opts.append(dcc.Dropdown(id={"type": "viz-opt", "index": "agg"}, options=[{"label": L, "value": V} for L,V in [("Soma","sum"),("Média","mean"),("Contagem","count"),("Mediana","median"),("Mínimo","min"),("Máximo","max"), ("Nenhum (usar valores diretos)","none")]], value="sum" if chart_type not in ["pie", "treemap", "sunburst"] else "none", clearable=False, className="mb-2"))
        
        # Opções de cor
        if chart_type not in ["heatmap"]:
            if chart_type == "radar":
                layout_opts.extend(create_opt_dropdown("Categoria para Comparação:", "color", cat_c, "Obrigatório para Radar", clearable=False))
            elif chart_type == "bullet":
                layout_opts.extend(create_opt_dropdown("Categoria:", "color", cat_c, "Obrigatório para Bullet", clearable=False))
            elif chart_type == "sankey":
                layout_opts.extend(create_opt_dropdown("Categoria (Opcional):", "color", cat_c, clearable=True))
            else:
                layout_opts.extend(create_opt_dropdown("Agrupar por Cor (Opcional):", "color", all_c, clearable=True))
        
        # Opções específicas para scatter
        if chart_type == "scatter":
            layout_opts.extend(create_opt_dropdown("Variar Tamanho por (Opcional, Numérico):", "size", num_c, clearable=True))
        
        # Opções específicas para sankey
        if chart_type == "sankey":
            layout_opts.extend(create_opt_dropdown("Valores de Fluxo (Opcional, Numérico):", "size", num_c, "Se não especificado, todos os fluxos terão o mesmo valor", clearable=True))
        
        # Opções específicas para heatmap
        if chart_type == "heatmap":
             layout_opts.extend(create_opt_dropdown("Valores (Z - para Pivot):", "z", num_c, "Usar correlação se X,Y,Z não para pivot", clearable=True))
             layout_opts.append(html.Small("Se X, Y, Z preenchidos e 'Agregação' != 'Nenhum', cria Pivot. Senão, Heatmap de Correlação (ignora X,Y,Z).", className="text-muted d-block mb-2"))
        
        # Instruções específicas para tipos de gráficos avançados
        if chart_type == "treemap" or chart_type == "sunburst":
            layout_opts.append(html.Small("Selecione 'Nomes' para o primeiro nível hierárquico e 'Agrupar por Cor' para o segundo nível (opcional).", className="text-muted d-block mb-2"))
        elif chart_type == "funnel":
            layout_opts.append(html.Small("Selecione 'Eixo X' para as etapas do funil e 'Eixo Y' para os valores em cada etapa.", className="text-muted d-block mb-2"))
        elif chart_type == "waterfall":
            layout_opts.append(html.Small("Selecione 'Eixo X' para as categorias e 'Eixo Y' para os valores. O primeiro valor é o inicial, os intermediários são incrementos/decrementos, e o último é o total.", className="text-muted d-block mb-2"))
        elif chart_type == "radar":
            layout_opts.append(html.Small("Selecione 'Categoria para Comparação' para agrupar e 'Eixo Y' como uma das métricas. Até 5 métricas numéricas serão incluídas automaticamente.", className="text-muted d-block mb-2"))
        elif chart_type == "sankey":
            layout_opts.append(html.Small("Selecione 'Eixo X' para origem, 'Eixo Y' para destino e opcionalmente 'Valores de Fluxo' para a intensidade das conexões.", className="text-muted d-block mb-2"))
        elif chart_type == "bullet":
            layout_opts.append(html.Small("Selecione 'Eixo Y' para valores atuais, 'Eixo X' para metas e 'Categoria' para agrupar os medidores.", className="text-muted d-block mb-2"))
        elif chart_type == "pareto":
            layout_opts.append(html.Small("Selecione 'Eixo X' para categorias e 'Eixo Y' para valores. O gráfico mostrará a distribuição e o percentual cumulativo.", className="text-muted d-block mb-2"))
        elif chart_type == "calendar":
            layout_opts.append(html.Small("Selecione 'Eixo X' para a coluna de data e 'Eixo Y' para os valores a serem exibidos no calendário.", className="text-muted d-block mb-2"))
        return html.Div(layout_opts) if layout_opts else dbc.Alert("Selecione tipo.", color="light")

    @app.callback(
        [Output("viz-main-chart", "figure"), Output("viz-chart-feedback-message", "children")],
        [Input("viz-create-chart-btn", "n_clicks"), Input("viz-clear-chart-btn", "n_clicks")],
        [State("server-side-data-key", "data"), State("viz-chart-type-dropdown", "value"), # MODIFICADO PARA CACHE
         State({"type": "viz-opt", "index": ALL}, "id"), State({"type": "viz-opt", "index": ALL}, "value"), 
         State({"type": "dynamic-filter-dropdown", "index": ALL}, "id"),
         State({"type": "dynamic-filter-dropdown", "index": ALL}, "value")],
        prevent_initial_call=True 
    )
    def create_main_visualization(create_clicks, clear_clicks, data_key, chart_type, # MODIFICADO PARA CACHE
                                  opt_ids, opt_values, filter_ids, filter_values):
        ctx = dash.callback_context
        if not ctx.triggered: return go.Figure().update_layout(annotations=[{'text':'Aguardando.','showarrow':False}]),""
        
        triggered_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        if triggered_id_str == "viz-clear-chart-btn":
            return go.Figure().update_layout(annotations=[{'text':'Gráfico Limpo.','showarrow':False}]), dbc.Alert("Gráfico limpo.",color="info",duration=2000)
            
        if not data_key: # MODIFICADO PARA CACHE
            return go.Figure().update_layout(annotations=[{'text':'Sem dados.','showarrow':False}]), dbc.Alert("Nenhum dado carregado.",color="warning", duration=3000)

        df_original = cache.get(data_key) # MODIFICADO PARA CACHE
        if df_original is None:
            return go.Figure().update_layout(annotations=[{'text':'Dados expirados.','showarrow':False}]), dbc.Alert("Dados não encontrados no cache/expirados. Recarregue.",color="danger", duration=4000)
        if df_original.empty:
             return go.Figure().update_layout(annotations=[{'text':'Dados vazios.','showarrow':False}]), dbc.Alert("Dados carregados estão vazios.",color="info", duration=3000)

        df = df_original.copy()
        if filter_ids and filter_values:
            for i, f_id_dict in enumerate(filter_ids):
                col_to_filter = f_id_dict.get("index")
                selected_vals = filter_values[i]
                if col_to_filter and selected_vals and col_to_filter in df.columns:
                    df = df[df[col_to_filter].isin(selected_vals)]
        if df.empty:
            return go.Figure().update_layout(annotations=[{'text':'Nenhum dado com filtros.','showarrow':False}]), dbc.Alert("Nenhum dado corresponde aos filtros.",color="warning", duration=4000)

        opts = {opt_id['index']: opt_val for opt_id, opt_val in zip(opt_ids, opt_values) if opt_id and 'index' in opt_id}
        opt_x, opt_y, opt_names, opt_values_pie, opt_color, opt_size, opt_agg, opt_z = \
            opts.get("x"), opts.get("y"), opts.get("names"), opts.get("values"), \
            opts.get("color"), opts.get("size"), opts.get("agg"), opts.get("z")
        
        fig = go.Figure(); feedback_msg_content = ""
        try:
            plot_args = {'data_frame': df.copy()}; title = f"{chart_type.capitalize()}"
            if chart_type == "pie":
                if not opt_names or not opt_values_pie: raise ValueError("'Nomes' e 'Valores' para Pizza.")
                plot_args.update({'names': opt_names, 'values': opt_values_pie})
                if opt_color: plot_args['color'] = opt_color
                title = f"Distribuição de {opt_values_pie} por {opt_names}"
                if opt_agg and opt_agg!="none" and opt_values_pie in df.select_dtypes(include=np.number).columns:
                    grp_cols_pie=[opt_names];
                    if opt_color and opt_color!=opt_names:grp_cols_pie.append(opt_color)
                    plot_args['data_frame']=df.groupby(list(set(grp_cols_pie)),as_index=False).agg({opt_values_pie:opt_agg})
                fig = px.pie(**plot_args)
            else:
                if not opt_x: raise ValueError("Eixo X obrigatório.")
                plot_args['x'] = opt_x
                if chart_type in ["bar","line"]:
                    is_y_num = opt_y and opt_y in df.select_dtypes(include=np.number).columns
                    if is_y_num and opt_agg and opt_agg!="none":
                        grp_cols=[opt_x];
                        if opt_color and opt_color!=opt_y:grp_cols.append(opt_color)
                        plot_args['data_frame']=df.groupby(list(set(grp_cols)),as_index=False).agg({opt_y:opt_agg})
                        plot_args['y']=opt_y;title=f"{opt_agg.capitalize()} de {opt_y} por {opt_x}"
                    elif not is_y_num and chart_type=="bar":
                        cnt_col='Contagem';grp_cols=[opt_x];
                        if opt_color:grp_cols.append(opt_color)
                        plot_args['data_frame']=df.groupby(list(set(grp_cols)),as_index=False).size().rename(columns={'size':cnt_col})
                        plot_args['y']=cnt_col;title=f"Contagem por {opt_x}"
                    elif opt_y:plot_args['y']=opt_y;title=f"{opt_y} por {opt_x}"
                    elif chart_type=="bar": # Contagem simples se Y não for fornecido para barra
                        cnt_col='Contagem'; plot_args['data_frame']=df.groupby(opt_x,as_index=False).size().rename(columns={'size':cnt_col})
                        plot_args['y']=cnt_col; title=f"Contagem de {opt_x}"
                elif opt_y:plot_args['y']=opt_y;title=f"{opt_y} vs {opt_x}" if chart_type=="scatter" else f"Dist. {opt_y} por {opt_x}"
                if opt_color:plot_args['color']=opt_color
                if opt_size and chart_type=="scatter":plot_args['size']=opt_size
                if opt_z and chart_type=="heatmap":plot_args['z']=opt_z
                if chart_type in ["line","scatter","box","violin"] and not plot_args.get('y') and not (chart_type=="heatmap" and not (opt_x and opt_y and opt_z)):
                    raise ValueError(f"Eixo Y obrigatório para {chart_type}.")
                
                chart_map={"bar":px.bar,"line":px.line,"scatter":px.scatter,"box":px.box,"histogram":px.histogram,"violin":px.violin}
                final_kwargs={**plot_args}
                if chart_type=="line":final_kwargs['markers']=True
                if chart_type in chart_map:
                    if chart_type=="histogram" and 'y' in final_kwargs and not final_kwargs.get('y'):del final_kwargs['y']
                    fig=chart_map[chart_type](**final_kwargs)
                elif chart_type=="heatmap":
                    if opt_x and opt_y and opt_z and opt_agg and opt_agg != "none": # Pivot
                        if not(opt_x in df.columns and opt_y in df.columns and opt_z in df.select_dtypes(include=np.number).columns):raise ValueError("Pivot: X,Y válidos e Z numérico.")
                        pivot=pd.pivot_table(plot_args['data_frame'],values=opt_z,index=opt_y,columns=opt_x,aggfunc=opt_agg)
                        fig=px.imshow(pivot,text_auto=".2f",aspect="auto",color_continuous_scale='Viridis');title=f"Heatmap: {opt_z} ({opt_agg}) por {opt_y} vs {opt_x}"
                    else: # Correlação
                        num_df_h=plot_args['data_frame'].select_dtypes(include=np.number)
                        if len(num_df_h.columns)<2:raise ValueError("Heatmap (correlação) requer >=2 colunas numéricas.")
                        fig=px.imshow(num_df_h.corr(),text_auto=".2f",aspect="auto",color_continuous_scale='RdBu_r',color_continuous_midpoint=0);title="Heatmap de Correlação"
                elif chart_type == "treemap":
                    if not opt_names or not opt_values_pie: raise ValueError("'Nomes' e 'Valores' para Treemap são obrigatórios.")
                    path_cols = [opt_names]
                    if opt_color and opt_color != opt_names: path_cols.append(opt_color)
                    fig = AdvancedVisualizations.create_treemap(
                        df=plot_args['data_frame'],
                        path_columns=path_cols,
                        values_column=opt_values_pie,
                        color_column=opt_values_pie,
                        title=f"Treemap de {opt_values_pie} por {' > '.join(path_cols)}"
                    )
                elif chart_type == "sunburst":
                    if not opt_names or not opt_values_pie: raise ValueError("'Nomes' e 'Valores' para Sunburst são obrigatórios.")
                    path_cols = [opt_names]
                    if opt_color and opt_color != opt_names: path_cols.append(opt_color)
                    fig = AdvancedVisualizations.create_sunburst(
                        df=plot_args['data_frame'],
                        path_columns=path_cols,
                        values_column=opt_values_pie,
                        color_column=opt_values_pie,
                        title=f"Sunburst de {opt_values_pie} por {' > '.join(path_cols)}"
                    )
                elif chart_type == "funnel":
                    if not opt_x or not opt_y: raise ValueError("Eixos X e Y são obrigatórios para Funil.")
                    fig = AdvancedVisualizations.create_funnel(
                        df=plot_args['data_frame'],
                        x_column=opt_x,
                        y_column=opt_y,
                        title=f"Funil de Conversão: {opt_y} por {opt_x}"
                    )
                elif chart_type == "waterfall":
                    if not opt_x or not opt_y: raise ValueError("Eixos X e Y são obrigatórios para Cascata.")
                    fig = AdvancedVisualizations.create_waterfall(
                        df=plot_args['data_frame'],
                        x_column=opt_x,
                        y_column=opt_y,
                        title=f"Gráfico de Cascata: {opt_y} por {opt_x}"
                    )
                elif chart_type == "radar":
                    if not opt_color or not opt_y: raise ValueError("'Agrupar por Cor' e 'Eixo Y' são obrigatórios para Radar.")
                    # Para radar, precisamos de múltiplas colunas numéricas
                    # Usamos opt_color como categoria e opt_y como uma das colunas de valor
                    num_cols = df.select_dtypes(include=np.number).columns.tolist()
                    if opt_y not in num_cols: raise ValueError(f"'{opt_y}' deve ser numérico para Radar.")
                    # Usar até 5 colunas numéricas incluindo opt_y
                    value_cols = [opt_y]
                    for col in num_cols:
                        if col != opt_y and len(value_cols) < 5:
                            value_cols.append(col)
                    fig = AdvancedVisualizations.create_radar(
                        df=plot_args['data_frame'],
                        category_column=opt_color,
                        value_columns=value_cols,
                        title=f"Gráfico Radar por {opt_color}"
                    )
                elif chart_type == "sankey":
                    if not opt_x or not opt_y: raise ValueError("'Origem' (X) e 'Destino' (Y) são obrigatórios para Sankey.")
                    fig = AdvancedVisualizations.create_sankey(
                        df=plot_args['data_frame'],
                        source_column=opt_x,
                        target_column=opt_y,
                        value_column=opt_size,  # Opcional
                        title=f"Diagrama de Sankey: {opt_x} → {opt_y}"
                    )
                elif chart_type == "bullet":
                    if not opt_y or not opt_x: raise ValueError("'Valor Atual' (Y) e 'Meta' (X) são obrigatórios para Bullet.")
                    if not opt_color: raise ValueError("'Categoria' (Cor) é obrigatório para Bullet.")
                    fig = AdvancedVisualizations.create_bullet_chart(
                        df=plot_args['data_frame'],
                        actual_column=opt_y,
                        target_column=opt_x,
                        category_column=opt_color,
                        title=f"Gráfico de Bala: {opt_y} vs Meta ({opt_x})"
                    )
                elif chart_type == "pareto":
                    if not opt_x or not opt_y: raise ValueError("Eixos X e Y são obrigatórios para Pareto.")
                    fig = AdvancedVisualizations.create_pareto_chart(
                        df=plot_args['data_frame'],
                        category_column=opt_x,
                        value_column=opt_y,
                        title=f"Análise de Pareto: {opt_y} por {opt_x}"
                    )
                elif chart_type == "calendar":
                    if not opt_x: raise ValueError("'Data' (X) é obrigatório para Calendário.")
                    if not opt_y: raise ValueError("'Valor' (Y) é obrigatório para Calendário.")
                    # Verificar se opt_x é uma coluna de data
                    try:
                        pd.to_datetime(df[opt_x])
                        fig = AdvancedVisualizations.create_calendar_heatmap(
                            df=plot_args['data_frame'],
                            date_column=opt_x,
                            value_column=opt_y,
                            title=f"Mapa de Calor Calendário: {opt_y} por {opt_x}"
                        )
                    except:
                        raise ValueError(f"'{opt_x}' deve ser uma coluna de data válida para Calendário.")
                else:
                    raise ValueError("Tipo de gráfico não suportado.")
            fig.update_layout(title_text=title,title_x=0.5,template="plotly_white",paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',clickmode='event+select')
            feedback_msg_content = dbc.Alert("Gráfico gerado!",color="success",duration=3000)
        except Exception as e:
            fig = go.Figure().update_layout(annotations=[{'text':f'Erro: {str(e)}','showarrow':False,'font_size':12}])
            feedback_msg_content = dbc.Alert(f"Erro ao gerar gráfico: {e}",color="danger",duration=10000)
            print(f"Erro viz: {e}");import traceback;traceback.print_exc()
        return fig, feedback_msg_content

    @app.callback(Output("viz-filters-panel-area","children"),[Input("server-side-data-key","data")]) # MODIFICADO PARA CACHE
    def render_dynamic_filters_panel(data_key): # MODIFICADO PARA CACHE
        if not data_key: return dbc.Alert("Carregue dados para filtros.",color="light",className="text-center")
        df = cache.get(data_key) # MODIFICADO PARA CACHE
        if df is None: return dbc.Alert("Dados não encontrados no cache.",color="danger")
        if df.empty: return dbc.Alert("Dados vazios.", color="info")
        layout_filters, _ = create_dynamic_filter_components(df)
        return layout_filters

    @app.callback(
        Output("viz-drill-down-area","children"), [Input("viz-main-chart","clickData")],
        [State("server-side-data-key","data"), State("viz-chart-type-dropdown","value"), # MODIFICADO PARA CACHE
         State({"type":"viz-opt","index":ALL},"id"), State({"type":"viz-opt","index":ALL},"value"),
         State({"type":"dynamic-filter-dropdown","index":ALL},"id"), State({"type":"dynamic-filter-dropdown","index":ALL},"value")],
        prevent_initial_call=True
    )
    def handle_chart_click_for_drilldown(click_data,data_key,chart_type,opt_ids,opt_values,filter_ids,filter_values): # MODIFICADO PARA CACHE
        if not click_data or not data_key: return ""
        df_original = cache.get(data_key) # MODIFICADO PARA CACHE
        if df_original is None: return dbc.Alert("Dados para drill-down não encontrados no cache.",color="danger")
        if df_original.empty: return dbc.Alert("Dados para drill-down estão vazios.",color="info")
        
        df = df_original.copy()
        if filter_ids and filter_values:
            for i,f_id_dict in enumerate(filter_ids):
                col_filter = f_id_dict.get("index"); sel_vals = filter_values[i]
                if col_filter and sel_vals and col_filter in df.columns: df=df[df[col_filter].isin(sel_vals)]
        if df.empty: return dbc.Alert("Nenhum dado após filtros para drill-down.",color="info")
        
        point_info = click_data['points'][0]
        opts = {opt_id['index']:opt_val for opt_id,opt_val in zip(opt_ids,opt_values) if opt_id and 'index' in opt_id}
        clicked_val, filter_col = None,None
        
        if chart_type=="pie" and 'label' in point_info: clicked_val,filter_col = point_info['label'],opts.get("names")
        elif 'x' in point_info and opts.get("x"): clicked_val,filter_col = point_info['x'],opts.get("x")
        elif chart_type=="heatmap" and 'x' in point_info and 'y' in point_info:
            col_x_h,col_y_h = point_info.get('x'),point_info.get('y')
            if col_x_h in df.columns and col_y_h in df.columns and pd.api.types.is_numeric_dtype(df[col_x_h]) and pd.api.types.is_numeric_dtype(df[col_y_h]):
                s_fig=px.scatter(df,x=col_x_h,y=col_y_h,title=f"Scatter: {col_y_h} vs {col_x_h}",marginal_x="box",marginal_y="violin",template="plotly_white")
                s_fig.update_layout(title_x=0.5); return create_card_layout(f"Relação: {col_x_h} & {col_y_h}",[dcc.Graph(figure=s_fig)],icon="fas fa-project-diagram")
            return dbc.Alert(f"Drill-down em heatmap para '{col_x_h}' e '{col_y_h}' não implementado.",color="info")
        if clicked_val is None or filter_col is None or filter_col not in df.columns:
            if not (chart_type=="heatmap" and 'x' in point_info and 'y' in point_info): return dbc.Alert("Não foi possível determinar ponto de drill-down.",color="warning")
            else: return ""
        
        df_drill = df[df[filter_col]==clicked_val]
        if df_drill.empty: return dbc.Alert(f"Sem dados detalhados para '{filter_col} = {clicked_val}'.",color="info")
        stats_drill = df_drill.describe(include='all').transpose().round(2).reset_index().rename(columns={'index':'Métrica'})
        drill_graph = None; num_cols_drill = df_drill.select_dtypes(include=np.number).columns
        if len(num_cols_drill)>0: 
            hist_drill=px.histogram(df_drill,x=num_cols_drill[0],title=f"Dist. de {num_cols_drill[0]} para Seleção",nbins=15,template="plotly_white")
            hist_drill.update_layout(title_x=0.5,bargap=0.1); drill_graph=dcc.Graph(figure=hist_drill)
        content = [html.H5(f"Detalhes: {filter_col} = {str(clicked_val)} ({len(df_drill):,} linhas)"),
                   dbc.Row([dbc.Col(format_datatable(stats_drill,"drill-stats",8),md=7), dbc.Col(drill_graph if drill_graph else "",md=5)]),
                   html.Hr(), html.H6("Amostra Detalhada:"), format_datatable(df_drill.head(10),"drill-sample",5)]
        return create_card_layout(f"Drill-Down: {str(clicked_val)}", content, icon="fas fa-search-plus")