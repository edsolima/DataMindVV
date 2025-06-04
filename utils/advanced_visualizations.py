# utils/advanced_visualizations.py
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
from scipy import stats

class AdvancedVisualizations:
    """
    Classe para criar visualizações avançadas de BI com Plotly.
    Fornece métodos para gerar gráficos complexos e interativos
    que vão além das visualizações básicas.
    """
    
    @staticmethod
    def create_treemap(df, path_columns, values_column=None, color_column=None, title="Treemap"):
        """
        Cria um gráfico treemap hierárquico.
        
        Args:
            df: DataFrame com os dados
            path_columns: Lista de colunas para criar a hierarquia do treemap
            values_column: Coluna com os valores para dimensionar os blocos
            color_column: Coluna para colorir os blocos
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        fig = px.treemap(
            df,
            path=path_columns,
            values=values_column,
            color=color_column,
            title=title,
            color_continuous_scale='RdBu',
            color_continuous_midpoint=np.average(df[color_column]) if color_column else None
        )
        
        fig.update_layout(
            margin=dict(t=50, l=25, r=25, b=25),
            font=dict(size=12)
        )
        
        return fig
    
    @staticmethod
    def create_sunburst(df, path_columns, values_column=None, color_column=None, title="Sunburst"):
        """
        Cria um gráfico sunburst (gráfico solar) hierárquico.
        
        Args:
            df: DataFrame com os dados
            path_columns: Lista de colunas para criar a hierarquia do sunburst
            values_column: Coluna com os valores para dimensionar os segmentos
            color_column: Coluna para colorir os segmentos
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        fig = px.sunburst(
            df,
            path=path_columns,
            values=values_column,
            color=color_column,
            title=title,
            color_continuous_scale='RdBu',
            color_continuous_midpoint=np.average(df[color_column]) if color_column else None
        )
        
        fig.update_layout(
            margin=dict(t=50, l=0, r=0, b=0),
            font=dict(size=12)
        )
        
        return fig
    
    @staticmethod
    def create_funnel(df, x_column, y_column, title="Funil de Conversão"):
        """
        Cria um gráfico de funil para análise de conversão.
        
        Args:
            df: DataFrame com os dados
            x_column: Coluna com os nomes das etapas
            y_column: Coluna com os valores de cada etapa
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        # Ordenar os dados do maior para o menor valor
        df_sorted = df.sort_values(by=y_column, ascending=False)
        
        fig = go.Figure(go.Funnel(
            y=df_sorted[x_column],
            x=df_sorted[y_column],
            textposition="inside",
            textinfo="value+percent initial",
            opacity=0.8,
            marker={"line": {"width": [2, 2, 2, 2, 2], "color": ["white", "white", "white", "white", "white"]}},
            connector={"line": {"color": "royalblue", "dash": "solid", "width": 3}}
        ))
        
        fig.update_layout(
            title=title,
            margin=dict(t=50, l=25, r=25, b=25),
            font=dict(size=12)
        )
        
        return fig
    
    @staticmethod
    def create_waterfall(df, x_column, y_column, title="Gráfico de Cascata"):
        """
        Cria um gráfico de cascata (waterfall) para análise de contribuições.
        
        Args:
            df: DataFrame com os dados
            x_column: Coluna com os nomes das categorias
            y_column: Coluna com os valores de cada categoria
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        # Calcular os valores cumulativos
        measure = ['relative'] * len(df)
        measure[0] = 'absolute'  # Primeiro valor é absoluto
        measure[-1] = 'total'    # Último valor é o total
        
        fig = go.Figure(go.Waterfall(
            name="Cascata",
            orientation="v",
            measure=measure,
            x=df[x_column],
            y=df[y_column],
            textposition="outside",
            text=df[y_column].apply(lambda x: f"{x:,.2f}"),
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        
        fig.update_layout(
            title=title,
            showlegend=False,
            margin=dict(t=50, l=25, r=25, b=25),
            font=dict(size=12)
        )
        
        return fig
    
    @staticmethod
    def create_radar(df, category_column, value_columns, title="Gráfico Radar"):
        """
        Cria um gráfico radar (ou teia de aranha) para comparação multidimensional.
        
        Args:
            df: DataFrame com os dados
            category_column: Coluna com as categorias a serem comparadas
            value_columns: Lista de colunas com os valores para cada dimensão
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        fig = go.Figure()
        
        categories = df[value_columns].columns.tolist()
        
        for i, category in enumerate(df[category_column].unique()):
            values = df[df[category_column] == category][value_columns].iloc[0].tolist()
            # Fechar o polígono repetindo o primeiro valor
            values.append(values[0])
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],  # Repetir a primeira categoria para fechar o polígono
                fill='toself',
                name=str(category)
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                )
            ),
            title=title,
            margin=dict(t=50, l=50, r=50, b=50),
            font=dict(size=12)
        )
        
        return fig
    
    @staticmethod
    def create_sankey(df, source_column, target_column, value_column=None, title="Diagrama de Sankey"):
        """
        Cria um diagrama de Sankey para visualizar fluxos entre nós.
        
        Args:
            df: DataFrame com os dados
            source_column: Coluna com os nós de origem
            target_column: Coluna com os nós de destino
            value_column: Coluna com os valores dos fluxos
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        # Criar mapeamento de nomes para índices
        all_nodes = pd.concat([df[source_column], df[target_column]]).unique()
        node_indices = {node: i for i, node in enumerate(all_nodes)}
        
        # Criar listas para o diagrama Sankey
        sources = [node_indices[source] for source in df[source_column]]
        targets = [node_indices[target] for target in df[target_column]]
        values = df[value_column] if value_column else [1] * len(sources)
        
        # Criar o gráfico
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=list(all_nodes),
                color="blue"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                hoverlabel=dict(bgcolor="white", font_size=12),
                hovertemplate="%{source.label} → %{target.label}<br>Valor: %{value}<extra></extra>"
            )
        )])
        
        fig.update_layout(
            title=title,
            font=dict(size=12),
            margin=dict(t=50, l=25, r=25, b=25)
        )
        
        return fig
    
    @staticmethod
    def create_bullet_chart(df, title="Gráfico de Bala", actual_column="Atual", target_column="Meta", 
                           category_column="Categoria", ranges_columns=None):
        """
        Cria um gráfico de bala (bullet chart) para comparar valores atuais com metas.
        
        Args:
            df: DataFrame com os dados
            title: Título do gráfico
            actual_column: Coluna com os valores atuais
            target_column: Coluna com os valores de meta
            category_column: Coluna com os nomes das categorias
            ranges_columns: Lista de colunas com os intervalos de referência (opcional)
        
        Returns:
            Figura Plotly
        """
        fig = go.Figure()
        
        # Definir intervalos padrão se não fornecidos
        if ranges_columns is None:
            for i, row in df.iterrows():
                target = row[target_column]
                ranges = [target * 0.6, target * 0.8, target]  # Intervalos padrão baseados na meta
                
                fig.add_trace(go.Indicator(
                    mode="number+gauge",
                    value=row[actual_column],
                    domain={'x': [0, 1], 'y': [i/len(df), (i+0.8)/len(df)]},
                    title={'text': row[category_column]},
                    gauge={
                        'shape': "bullet",
                        'axis': {'range': [0, max(target * 1.2, row[actual_column] * 1.2)]},
                        'threshold': {
                            'line': {'color': "red", 'width': 2},
                            'thickness': 0.75,
                            'value': target
                        },
                        'steps': [
                            {'range': [0, ranges[0]], 'color': "lightgray"},
                            {'range': [ranges[0], ranges[1]], 'color': "gray"},
                            {'range': [ranges[1], ranges[2]], 'color': "darkgray"}
                        ],
                        'bar': {'color': "black"}
                    }
                ))
        else:
            # Usar intervalos fornecidos
            for i, row in df.iterrows():
                ranges = [row[col] for col in ranges_columns]
                
                fig.add_trace(go.Indicator(
                    mode="number+gauge",
                    value=row[actual_column],
                    domain={'x': [0, 1], 'y': [i/len(df), (i+0.8)/len(df)]},
                    title={'text': row[category_column]},
                    gauge={
                        'shape': "bullet",
                        'axis': {'range': [0, max(ranges[-1] * 1.2, row[actual_column] * 1.2)]},
                        'threshold': {
                            'line': {'color': "red", 'width': 2},
                            'thickness': 0.75,
                            'value': row[target_column]
                        },
                        'steps': [
                            {'range': [0, ranges[0]], 'color': "lightgray"},
                            {'range': [ranges[0], ranges[1]], 'color': "gray"},
                            {'range': [ranges[1], ranges[2]], 'color': "darkgray"}
                        ],
                        'bar': {'color': "black"}
                    }
                ))
        
        fig.update_layout(
            title=title,
            height=100 + (100 * len(df)),  # Ajustar altura com base no número de categorias
            margin=dict(t=50, l=120, r=25, b=25),
            font=dict(size=12)
        )
        
        return fig
    
    @staticmethod
    def create_pareto_chart(df, category_column, value_column, title="Análise de Pareto"):
        """
        Cria um gráfico de Pareto (80/20) para análise de prioridades.
        
        Args:
            df: DataFrame com os dados
            category_column: Coluna com as categorias
            value_column: Coluna com os valores
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        # Ordenar os dados pelo valor em ordem decrescente
        df_sorted = df.sort_values(by=value_column, ascending=False).reset_index(drop=True)
        
        # Calcular o percentual cumulativo
        df_sorted['cumulative_percentage'] = df_sorted[value_column].cumsum() / df_sorted[value_column].sum() * 100
        
        # Criar o gráfico
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Adicionar barras para os valores
        fig.add_trace(
            go.Bar(
                x=df_sorted[category_column],
                y=df_sorted[value_column],
                name=value_column,
                marker_color='blue'
            ),
            secondary_y=False,
        )
        
        # Adicionar linha para o percentual cumulativo
        fig.add_trace(
            go.Scatter(
                x=df_sorted[category_column],
                y=df_sorted['cumulative_percentage'],
                name="% Cumulativo",
                marker_color='red',
                mode='lines+markers'
            ),
            secondary_y=True,
        )
        
        # Adicionar linha de referência em 80%
        fig.add_shape(
            type="line",
            x0=-0.5,
            y0=80,
            x1=len(df_sorted)-0.5,
            y1=80,
            line=dict(color="green", width=2, dash="dash"),
            xref="x",
            yref="y2"
        )
        
        # Configurar os eixos
        fig.update_layout(
            title=title,
            xaxis_title=category_column,
            margin=dict(t=50, l=25, r=25, b=100),
            font=dict(size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_yaxes(
            title_text=value_column,
            secondary_y=False
        )
        
        fig.update_yaxes(
            title_text="Percentual Cumulativo",
            secondary_y=True,
            range=[0, 105],
            ticksuffix="%"
        )
        
        return fig
    
    @staticmethod
    def create_calendar_heatmap(df, date_column, value_column, title="Mapa de Calor por Calendário"):
        """
        Cria um mapa de calor em formato de calendário.
        
        Args:
            df: DataFrame com os dados
            date_column: Coluna com as datas (deve ser datetime)
            value_column: Coluna com os valores
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        # Garantir que a coluna de data seja datetime
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        
        # Extrair componentes da data
        df['year'] = df[date_column].dt.year
        df['month'] = df[date_column].dt.month
        df['day'] = df[date_column].dt.day
        df['weekday'] = df[date_column].dt.weekday
        
        # Criar o gráfico
        fig = px.density_heatmap(
            df,
            x='day',
            y='weekday',
            z=value_column,
            facet_row='month',
            facet_col='year',
            category_orders={
                'weekday': [0, 1, 2, 3, 4, 5, 6],  # Segunda a Domingo
                'month': list(range(1, 13))  # Janeiro a Dezembro
            },
            labels={
                'weekday': 'Dia da Semana',
                'day': 'Dia do Mês',
                'month': 'Mês',
                'year': 'Ano',
                value_column: 'Valor'
            },
            color_continuous_scale='RdBu_r'
        )
        
        # Configurar nomes dos dias da semana
        weekday_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        fig.update_yaxes(tickvals=list(range(7)), ticktext=weekday_names)
        
        # Configurar nomes dos meses
        month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        for annotation in fig.layout.annotations:
            if 'month=' in annotation.text:
                month_num = int(annotation.text.split('=')[1])
                annotation.text = month_names[month_num-1]
        
        fig.update_layout(
            title=title,
            margin=dict(t=50, l=25, r=25, b=25),
            font=dict(size=12)
        )
        
        return fig
    
    @staticmethod
    def create_gauge_chart(value, min_value=0, max_value=100, threshold_values=None, title="Medidor"):
        """
        Cria um gráfico de medidor (gauge).
        
        Args:
            value: Valor atual do medidor
            min_value: Valor mínimo da escala
            max_value: Valor máximo da escala
            threshold_values: Lista de valores de limite para as cores [baixo, médio, alto]
            title: Título do gráfico
        
        Returns:
            Figura Plotly
        """
        if threshold_values is None:
            # Valores padrão de limite baseados no máximo
            threshold_values = [max_value * 0.33, max_value * 0.66, max_value]
        
        # Determinar a cor com base nos limites
        if value <= threshold_values[0]:
            color = "red"
        elif value <= threshold_values[1]:
            color = "yellow"
        else:
            color = "green"
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            gauge={
                'axis': {'range': [min_value, max_value]},
                'bar': {'color': color},
                'steps': [
                    {'range': [min_value, threshold_values[0]], 'color': "lightgray"},
                    {'range': [threshold_values[0], threshold_values[1]], 'color': "gray"},
                    {'range': [threshold_values[1], max_value], 'color': "darkgray"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': value
                }
            }
        ))
        
        fig.update_layout(
            margin=dict(t=50, l=25, r=25, b=25),
            font=dict(size=12)
        )
        
        return fig