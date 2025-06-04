# utils/advanced_analytics.py
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

class AdvancedAnalytics:
    """
    Classe para análises avançadas de BI.
    Fornece métodos para análises estatísticas, segmentação, detecção de anomalias
    e outras técnicas avançadas de análise de dados.
    """
    
    @staticmethod
    def perform_cluster_analysis(df, numeric_columns, n_clusters=3, method='kmeans'):
        """
        Realiza análise de clustering nos dados.
        
        Args:
            df: DataFrame com os dados
            numeric_columns: Lista de colunas numéricas para usar na análise
            n_clusters: Número de clusters a serem criados
            method: Método de clustering ('kmeans' por enquanto)
            
        Returns:
            Tuple contendo (DataFrame com clusters, figura Plotly)
        """
        if not numeric_columns or len(numeric_columns) < 2:
            raise ValueError("Pelo menos duas colunas numéricas são necessárias para clustering")
        
        # Preparar os dados
        df_cluster = df.copy()
        X = df_cluster[numeric_columns].dropna()
        
        if X.shape[0] < n_clusters:
            raise ValueError(f"Número de amostras válidas ({X.shape[0]}) é menor que o número de clusters ({n_clusters})")
        
        # Normalizar os dados
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Aplicar K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        
        # Adicionar clusters ao DataFrame original
        df_with_clusters = df_cluster.copy()
        df_with_clusters.loc[X.index, 'Cluster'] = clusters.astype(int)
        
        # Criar visualização
        if len(numeric_columns) >= 2:
            fig = px.scatter(
                df_with_clusters.dropna(subset=['Cluster']),
                x=numeric_columns[0],
                y=numeric_columns[1],
                color='Cluster',
                color_discrete_sequence=px.colors.qualitative.G10,
                title=f'Análise de Clusters: {numeric_columns[0]} vs {numeric_columns[1]}',
                hover_data=numeric_columns
            )
            
            # Adicionar centróides
            centroids = scaler.inverse_transform(kmeans.cluster_centers_)
            for i in range(n_clusters):
                fig.add_trace(go.Scatter(
                    x=[centroids[i, 0]],
                    y=[centroids[i, 1]],
                    mode='markers',
                    marker=dict(symbol='x', size=15, color='black', line=dict(width=2)),
                    name=f'Centróide {i}'
                ))
            
            fig.update_layout(
                template='plotly_white',
                legend_title_text='Cluster',
                title_x=0.5
            )
        else:
            fig = go.Figure()
            fig.update_layout(
                title="Visualização requer pelo menos 2 colunas numéricas",
                title_x=0.5
            )
        
        return df_with_clusters, fig
    
    @staticmethod
    def perform_pca_analysis(df, numeric_columns, n_components=2):
        """
        Realiza análise de componentes principais (PCA).
        
        Args:
            df: DataFrame com os dados
            numeric_columns: Lista de colunas numéricas para usar na análise
            n_components: Número de componentes principais a serem extraídos
            
        Returns:
            Tuple contendo (DataFrame com componentes principais, figura Plotly)
        """
        if not numeric_columns or len(numeric_columns) < 2:
            raise ValueError("Pelo menos duas colunas numéricas são necessárias para PCA")
        
        # Preparar os dados
        df_pca = df.copy()
        X = df_pca[numeric_columns].dropna()
        
        if X.shape[0] < 3:
            raise ValueError(f"Número de amostras válidas ({X.shape[0]}) é muito pequeno para PCA")
        
        # Normalizar os dados
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Aplicar PCA
        pca = PCA(n_components=min(n_components, len(numeric_columns)))
        principal_components = pca.fit_transform(X_scaled)
        
        # Criar DataFrame com componentes principais
        pc_columns = [f'PC{i+1}' for i in range(principal_components.shape[1])]
        df_principal = pd.DataFrame(data=principal_components, columns=pc_columns, index=X.index)
        
        # Adicionar componentes ao DataFrame original
        for col in pc_columns:
            df_pca.loc[X.index, col] = df_principal[col]
        
        # Calcular variância explicada
        explained_variance = pca.explained_variance_ratio_ * 100
        
        # Criar visualização
        if principal_components.shape[1] >= 2:
            fig = px.scatter(
                df_principal,
                x='PC1',
                y='PC2',
                title=f'Análise PCA: PC1 ({explained_variance[0]:.2f}%) vs PC2 ({explained_variance[1]:.2f}%)',
                opacity=0.7
            )
            
            # Adicionar vetores de carga (loadings)
            loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
            for i, feature in enumerate(numeric_columns):
                fig.add_shape(
                    type='line',
                    x0=0, y0=0,
                    x1=loadings[i, 0],
                    y1=loadings[i, 1],
                    line=dict(color='red', width=1, dash='dash'),
                )
                fig.add_annotation(
                    x=loadings[i, 0],
                    y=loadings[i, 1],
                    ax=0, ay=0,
                    xanchor="center",
                    yanchor="bottom",
                    text=feature,
                    font=dict(size=10)
                )
            
            fig.update_layout(
                template='plotly_white',
                title_x=0.5,
                xaxis_title=f'PC1 ({explained_variance[0]:.2f}%)',
                yaxis_title=f'PC2 ({explained_variance[1]:.2f}%)',
                xaxis=dict(zeroline=True, zerolinewidth=1, zerolinecolor='gray'),
                yaxis=dict(zeroline=True, zerolinewidth=1, zerolinecolor='gray')
            )
        else:
            fig = go.Figure()
            fig.update_layout(
                title="Visualização requer pelo menos 2 componentes principais",
                title_x=0.5
            )
        
        return df_pca, fig, explained_variance
    
    @staticmethod
    def detect_anomalies(df, numeric_columns, contamination=0.05, method='isolation_forest'):
        """
        Detecta anomalias nos dados usando Isolation Forest.
        
        Args:
            df: DataFrame com os dados
            numeric_columns: Lista de colunas numéricas para usar na detecção
            contamination: Proporção esperada de anomalias nos dados
            method: Método de detecção ('isolation_forest' por enquanto)
            
        Returns:
            Tuple contendo (DataFrame com anomalias marcadas, figura Plotly)
        """
        if not numeric_columns or len(numeric_columns) < 1:
            raise ValueError("Pelo menos uma coluna numérica é necessária para detecção de anomalias")
        
        # Preparar os dados
        df_anomaly = df.copy()
        X = df_anomaly[numeric_columns].dropna()
        
        if X.shape[0] < 10:
            raise ValueError(f"Número de amostras válidas ({X.shape[0]}) é muito pequeno para detecção de anomalias")
        
        # Normalizar os dados
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Aplicar Isolation Forest
        model = IsolationForest(contamination=contamination, random_state=42)
        anomalies = model.fit_predict(X_scaled)
        
        # Converter para formato mais intuitivo: 1 para normal, -1 para anomalia
        df_anomaly.loc[X.index, 'Anomalia'] = np.where(anomalies == -1, 'Sim', 'Não')
        
        # Adicionar score de anomalia (quanto menor, mais anômalo)
        anomaly_score = model.decision_function(X_scaled)
        df_anomaly.loc[X.index, 'Score_Anomalia'] = anomaly_score
        
        # Criar visualização
        if len(numeric_columns) >= 2:
            fig = px.scatter(
                df_anomaly.dropna(subset=['Anomalia']),
                x=numeric_columns[0],
                y=numeric_columns[1],
                color='Anomalia',
                color_discrete_map={'Sim': 'red', 'Não': 'blue'},
                title=f'Detecção de Anomalias: {numeric_columns[0]} vs {numeric_columns[1]}',
                hover_data=['Score_Anomalia'] + numeric_columns,
                size_max=10,
                opacity=0.7
            )
            
            fig.update_layout(
                template='plotly_white',
                title_x=0.5,
                legend_title_text='Anomalia'
            )
        else:
            # Para uma única coluna, criar histograma
            fig = px.histogram(
                df_anomaly.dropna(subset=['Anomalia']),
                x=numeric_columns[0],
                color='Anomalia',
                color_discrete_map={'Sim': 'red', 'Não': 'blue'},
                title=f'Detecção de Anomalias: Distribuição de {numeric_columns[0]}',
                barmode='overlay',
                opacity=0.7
            )
            
            fig.update_layout(
                template='plotly_white',
                title_x=0.5,
                legend_title_text='Anomalia'
            )
        
        return df_anomaly, fig
    
    @staticmethod
    def perform_time_series_decomposition(df, date_column, value_column, period=None):
        """
        Decompõe uma série temporal em tendência, sazonalidade e resíduo.
        
        Args:
            df: DataFrame com os dados
            date_column: Coluna com as datas
            value_column: Coluna com os valores da série temporal
            period: Período de sazonalidade (None para detecção automática)
            
        Returns:
            Figura Plotly com a decomposição
        """
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Preparar os dados
        df_ts = df.copy()
        df_ts[date_column] = pd.to_datetime(df_ts[date_column])
        df_ts = df_ts.sort_values(by=date_column)
        
        # Verificar se há valores ausentes
        if df_ts[value_column].isnull().any():
            df_ts[value_column] = df_ts[value_column].interpolate(method='linear')
        
        # Definir o índice como a coluna de data
        df_ts = df_ts.set_index(date_column)
        
        # Detectar período automaticamente se não fornecido
        if period is None:
            # Tentar detectar frequência diária, semanal, mensal ou anual
            freq_map = {
                'D': 7,       # Diário -> semanal
                'W': 52,      # Semanal -> anual
                'M': 12,      # Mensal -> anual
                'Q': 4,       # Trimestral -> anual
                'A': 1        # Anual
            }
            inferred_freq = pd.infer_freq(df_ts.index)
            if inferred_freq:
                for freq_key, freq_period in freq_map.items():
                    if freq_key in inferred_freq:
                        period = freq_period
                        break
            
            # Se não conseguir detectar, usar um valor padrão
            if period is None:
                if len(df_ts) >= 365:
                    period = 365  # Diário por um ano
                elif len(df_ts) >= 52:
                    period = 52   # Semanal por um ano
                elif len(df_ts) >= 12:
                    period = 12   # Mensal por um ano
                else:
                    period = len(df_ts) // 2  # Metade do tamanho da série
        
        # Garantir que o período não seja maior que metade do tamanho da série
        period = min(period, len(df_ts) // 2)
        period = max(period, 2)  # Garantir que o período seja pelo menos 2
        
        # Realizar a decomposição
        try:
            result = seasonal_decompose(
                df_ts[value_column],
                model='additive',
                period=period
            )
            
            # Criar figura com subplots
            fig = make_subplots(
                rows=4, cols=1,
                subplot_titles=('Série Original', 'Tendência', 'Sazonalidade', 'Resíduo'),
                shared_xaxes=True,
                vertical_spacing=0.05
            )
            
            # Adicionar série original
            fig.add_trace(
                go.Scatter(x=df_ts.index, y=df_ts[value_column], mode='lines', name='Original'),
                row=1, col=1
            )
            
            # Adicionar tendência
            fig.add_trace(
                go.Scatter(x=df_ts.index, y=result.trend, mode='lines', name='Tendência', line=dict(color='red')),
                row=2, col=1
            )
            
            # Adicionar sazonalidade
            fig.add_trace(
                go.Scatter(x=df_ts.index, y=result.seasonal, mode='lines', name='Sazonalidade', line=dict(color='green')),
                row=3, col=1
            )
            
            # Adicionar resíduo
            fig.add_trace(
                go.Scatter(x=df_ts.index, y=result.resid, mode='lines', name='Resíduo', line=dict(color='purple')),
                row=4, col=1
            )
            
            fig.update_layout(
                height=800,
                title=f'Decomposição da Série Temporal: {value_column} (Período: {period})',
                title_x=0.5,
                template='plotly_white',
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            # Em caso de erro, retornar uma figura com mensagem de erro
            fig = go.Figure()
            fig.update_layout(
                title=f"Erro na decomposição: {str(e)}",
                title_x=0.5
            )
            return fig
    
    @staticmethod
    def create_cohort_analysis(df, date_column, id_column, value_column=None, time_unit='M'):
        """
        Realiza análise de coorte baseada em data.
        
        Args:
            df: DataFrame com os dados
            date_column: Coluna com as datas
            id_column: Coluna com os IDs dos usuários/clientes
            value_column: Coluna com os valores (opcional, se None usa contagem)
            time_unit: Unidade de tempo para agrupar ('D', 'W', 'M', 'Q', 'Y')
            
        Returns:
            Tuple contendo (DataFrame da análise de coorte, figura Plotly)
        """
        # Preparar os dados
        df_cohort = df.copy()
        df_cohort[date_column] = pd.to_datetime(df_cohort[date_column])
        
        # Extrair o período de coorte (primeira data para cada ID)
        cohort_data = df_cohort.groupby(id_column)[date_column].min().reset_index()
        cohort_data.columns = [id_column, 'Cohort_Date']
        
        # Adicionar o período de coorte ao DataFrame original
        df_cohort = df_cohort.merge(cohort_data, on=id_column, how='left')
        
        # Criar período para data original e data de coorte
        df_cohort['Period'] = df_cohort[date_column].dt.to_period(time_unit)
        df_cohort['Cohort_Period'] = df_cohort['Cohort_Date'].dt.to_period(time_unit)
        
        # Calcular o período de diferença (em meses, semanas, etc.)
        df_cohort['Period_Diff'] = (df_cohort['Period'] - df_cohort['Cohort_Period']).apply(lambda x: x.n)
        
        # Agrupar por período de coorte e período de diferença
        if value_column:
            # Se um valor for fornecido, usar soma ou média
            cohort_table = df_cohort.groupby(['Cohort_Period', 'Period_Diff'])[value_column].sum().unstack()
        else:
            # Caso contrário, contar IDs únicos
            cohort_table = df_cohort.groupby(['Cohort_Period', 'Period_Diff'])[id_column].nunique().unstack()
        
        # Calcular taxas de retenção
        cohort_sizes = cohort_table[0].copy()
        retention_table = cohort_table.divide(cohort_sizes, axis=0)
        
        # Criar heatmap
        fig = go.Figure(data=go.Heatmap(
            z=retention_table.values,
            x=retention_table.columns,
            y=[str(period) for period in retention_table.index],
            colorscale='RdBu_r',
            text=np.round(retention_table.values * 100, 1),
            texttemplate='%{text}%',
            colorbar=dict(title='Taxa de Retenção %')
        ))
        
        time_unit_names = {
            'D': 'Dia',
            'W': 'Semana',
            'M': 'Mês',
            'Q': 'Trimestre',
            'Y': 'Ano'
        }
        
        time_unit_name = time_unit_names.get(time_unit, time_unit)
        
        fig.update_layout(
            title=f'Análise de Coorte por {time_unit_name}',
            title_x=0.5,
            xaxis_title=f'{time_unit_name}s desde a primeira atividade',
            yaxis_title=f'Coorte ({time_unit_name} de entrada)',
            xaxis=dict(tickmode='array', tickvals=list(retention_table.columns)),
            template='plotly_white'
        )
        
        return retention_table, fig