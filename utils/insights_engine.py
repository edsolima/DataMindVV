# -*- coding: utf-8 -*-
"""
Insights Engine - Motor de Insights Automatizados e Alertas Inteligentes
Detecta automaticamente anomalias, padrões e gera insights dos dados
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest

from utils.logger import log_info, log_error, log_warning
from utils.database_manager import DatabaseManager
from utils.config_manager import ConfigManager

@dataclass
class Insight:
    """Representa um insight descoberto"""
    id: str
    title: str
    description: str
    type: str  # 'anomaly', 'trend', 'pattern', 'correlation', 'forecast'
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence: float
    data_source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    recommendations: List[str]

@dataclass
class Anomaly:
    """Representa uma anomalia detectada"""
    timestamp: datetime
    value: float
    expected_value: float
    deviation: float
    severity: str
    context: Dict[str, Any]

@dataclass
class Trend:
    """Representa uma tendência identificada"""
    direction: str  # 'up', 'down', 'stable'
    strength: float  # 0-1
    duration: int  # dias
    start_date: datetime
    end_date: datetime
    slope: float
    r_squared: float

class InsightsEngine:
    """Motor de insights automatizados"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.insights_cache: List[Insight] = []
        
        # Configurações de detecção
        self.anomaly_threshold = 2.5  # desvios padrão
        self.trend_min_points = 7  # mínimo de pontos para detectar tendência
        self.correlation_threshold = 0.7  # correlação mínima
        
        # Modelos de ML para detecção
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        
    def analyze_data(self, data: pd.DataFrame, data_source: str = "unknown") -> List[Insight]:
        """Analisa dados e gera insights automaticamente"""
        insights = []
        
        try:
            if data.empty:
                return insights
            
            # Detecta anomalias
            anomaly_insights = self._detect_anomalies(data, data_source)
            insights.extend(anomaly_insights)
            
            # Detecta tendências
            trend_insights = self._detect_trends(data, data_source)
            insights.extend(trend_insights)
            
            # Detecta padrões
            pattern_insights = self._detect_patterns(data, data_source)
            insights.extend(pattern_insights)
            
            # Detecta correlações
            correlation_insights = self._detect_correlations(data, data_source)
            insights.extend(correlation_insights)
            
            # Gera previsões
            forecast_insights = self._generate_forecasts(data, data_source)
            insights.extend(forecast_insights)
            
            # Atualiza cache
            self.insights_cache.extend(insights)
            
            log_info(f"Análise concluída: {len(insights)} insights gerados para {data_source}")
            
        except Exception as e:
            log_error(f"Erro na análise de dados", extra={"error": str(e), "source": data_source})
        
        return insights
    
    def _detect_anomalies(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Detecta anomalias nos dados"""
        insights = []
        
        try:
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for column in numeric_columns:
                if data[column].isna().all():
                    continue
                
                # Método 1: Z-Score
                z_scores = np.abs(stats.zscore(data[column].dropna()))
                anomalies_zscore = data[z_scores > self.anomaly_threshold]
                
                if not anomalies_zscore.empty:
                    insight = self._create_anomaly_insight(
                        anomalies_zscore, column, "z-score", data_source
                    )
                    insights.append(insight)
                
                # Método 2: IQR
                Q1 = data[column].quantile(0.25)
                Q3 = data[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                anomalies_iqr = data[
                    (data[column] < lower_bound) | (data[column] > upper_bound)
                ]
                
                if not anomalies_iqr.empty:
                    insight = self._create_anomaly_insight(
                        anomalies_iqr, column, "iqr", data_source
                    )
                    insights.append(insight)
                
                # Método 3: Isolation Forest (para dados multivariados)
                if len(numeric_columns) > 1:
                    features = data[numeric_columns].fillna(data[numeric_columns].mean())
                    if len(features) > 10:  # mínimo de pontos
                        scaler = StandardScaler()
                        features_scaled = scaler.fit_transform(features)
                        
                        outliers = self.isolation_forest.fit_predict(features_scaled)
                        anomalies_ml = data[outliers == -1]
                        
                        if not anomalies_ml.empty:
                            insight = self._create_anomaly_insight(
                                anomalies_ml, "multivariate", "isolation_forest", data_source
                            )
                            insights.append(insight)
        
        except Exception as e:
            log_error(f"Erro na detecção de anomalias", extra={"error": str(e)})
        
        return insights
    
    def _detect_trends(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Detecta tendências temporais nos dados"""
        insights = []
        
        try:
            # Procura por colunas de data
            date_columns = []
            for col in data.columns:
                if data[col].dtype == 'datetime64[ns]' or 'data' in col.lower():
                    date_columns.append(col)
            
            if not date_columns:
                return insights
            
            date_col = date_columns[0]
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for num_col in numeric_columns:
                if data[num_col].isna().all():
                    continue
                
                # Ordena por data
                sorted_data = data.sort_values(date_col)
                
                if len(sorted_data) < self.trend_min_points:
                    continue
                
                # Calcula tendência usando regressão linear
                x = np.arange(len(sorted_data))
                y = sorted_data[num_col].fillna(method='ffill')
                
                if len(y.dropna()) < self.trend_min_points:
                    continue
                
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                
                # Determina direção e força da tendência
                if abs(r_value) > 0.5 and p_value < 0.05:  # correlação significativa
                    direction = 'up' if slope > 0 else 'down' if slope < 0 else 'stable'
                    strength = abs(r_value)
                    
                    trend = Trend(
                        direction=direction,
                        strength=strength,
                        duration=(sorted_data[date_col].max() - sorted_data[date_col].min()).days,
                        start_date=sorted_data[date_col].min(),
                        end_date=sorted_data[date_col].max(),
                        slope=slope,
                        r_squared=r_value**2
                    )
                    
                    insight = self._create_trend_insight(trend, num_col, data_source)
                    insights.append(insight)
        
        except Exception as e:
            log_error(f"Erro na detecção de tendências", extra={"error": str(e)})
        
        return insights
    
    def _detect_patterns(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Detecta padrões nos dados"""
        insights = []
        
        try:
            # Padrão 1: Sazonalidade
            insights.extend(self._detect_seasonality(data, data_source))
            
            # Padrão 2: Clusters
            insights.extend(self._detect_clusters(data, data_source))
            
            # Padrão 3: Distribuições incomuns
            insights.extend(self._detect_distribution_patterns(data, data_source))
            
        except Exception as e:
            log_error(f"Erro na detecção de padrões", extra={"error": str(e)})
        
        return insights
    
    def _detect_correlations(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Detecta correlações interessantes entre variáveis"""
        insights = []
        
        try:
            numeric_data = data.select_dtypes(include=[np.number])
            
            if len(numeric_data.columns) < 2:
                return insights
            
            # Calcula matriz de correlação
            corr_matrix = numeric_data.corr()
            
            # Encontra correlações fortes
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    
                    if abs(corr_value) > self.correlation_threshold:
                        col1 = corr_matrix.columns[i]
                        col2 = corr_matrix.columns[j]
                        
                        insight = self._create_correlation_insight(
                            col1, col2, corr_value, data_source
                        )
                        insights.append(insight)
        
        except Exception as e:
            log_error(f"Erro na detecção de correlações", extra={"error": str(e)})
        
        return insights
    
    def _generate_forecasts(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Gera previsões simples baseadas em tendências"""
        insights = []
        
        try:
            # Procura por colunas de data
            date_columns = [col for col in data.columns 
                          if data[col].dtype == 'datetime64[ns]' or 'data' in col.lower()]
            
            if not date_columns:
                return insights
            
            date_col = date_columns[0]
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for num_col in numeric_columns:
                if data[num_col].isna().all():
                    continue
                
                # Ordena por data
                sorted_data = data.sort_values(date_col).tail(30)  # últimos 30 pontos
                
                if len(sorted_data) < 7:
                    continue
                
                # Previsão simples usando média móvel
                values = sorted_data[num_col].fillna(method='ffill')
                
                # Média móvel de 7 dias
                ma_7 = values.rolling(window=7).mean().iloc[-1]
                
                # Tendência recente
                recent_trend = values.iloc[-7:].mean() - values.iloc[-14:-7].mean()
                
                # Previsão para próximo período
                forecast = ma_7 + recent_trend
                
                insight = self._create_forecast_insight(
                    num_col, forecast, ma_7, recent_trend, data_source
                )
                insights.append(insight)
        
        except Exception as e:
            log_error(f"Erro na geração de previsões", extra={"error": str(e)})
        
        return insights
    
    def _detect_seasonality(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Detecta padrões sazonais"""
        insights = []
        
        try:
            # Procura por colunas de data
            date_columns = [col for col in data.columns 
                          if data[col].dtype == 'datetime64[ns]' or 'data' in col.lower()]
            
            if not date_columns:
                return insights
            
            date_col = date_columns[0]
            
            # Adiciona colunas temporais
            data_copy = data.copy()
            data_copy['day_of_week'] = pd.to_datetime(data_copy[date_col]).dt.dayofweek
            data_copy['month'] = pd.to_datetime(data_copy[date_col]).dt.month
            data_copy['hour'] = pd.to_datetime(data_copy[date_col]).dt.hour
            
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for num_col in numeric_columns:
                # Analisa padrão por dia da semana
                weekly_pattern = data_copy.groupby('day_of_week')[num_col].mean()
                weekly_std = weekly_pattern.std()
                weekly_mean = weekly_pattern.mean()
                
                if weekly_std / weekly_mean > 0.3:  # variação significativa
                    insight = self._create_seasonality_insight(
                        num_col, 'weekly', weekly_pattern, data_source
                    )
                    insights.append(insight)
                
                # Analisa padrão por mês
                if len(data_copy['month'].unique()) > 3:
                    monthly_pattern = data_copy.groupby('month')[num_col].mean()
                    monthly_std = monthly_pattern.std()
                    monthly_mean = monthly_pattern.mean()
                    
                    if monthly_std / monthly_mean > 0.2:
                        insight = self._create_seasonality_insight(
                            num_col, 'monthly', monthly_pattern, data_source
                        )
                        insights.append(insight)
        
        except Exception as e:
            log_error(f"Erro na detecção de sazonalidade", extra={"error": str(e)})
        
        return insights
    
    def _detect_clusters(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Detecta clusters nos dados"""
        insights = []
        
        try:
            numeric_data = data.select_dtypes(include=[np.number])
            
            if len(numeric_data.columns) < 2 or len(numeric_data) < 10:
                return insights
            
            # Prepara dados
            features = numeric_data.fillna(numeric_data.mean())
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Aplica DBSCAN
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            clusters = dbscan.fit_predict(features_scaled)
            
            n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)
            n_noise = list(clusters).count(-1)
            
            if n_clusters > 1:
                insight = self._create_cluster_insight(
                    n_clusters, n_noise, len(data), data_source
                )
                insights.append(insight)
        
        except Exception as e:
            log_error(f"Erro na detecção de clusters", extra={"error": str(e)})
        
        return insights
    
    def _detect_distribution_patterns(self, data: pd.DataFrame, data_source: str) -> List[Insight]:
        """Detecta padrões de distribuição incomuns"""
        insights = []
        
        try:
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for column in numeric_columns:
                if data[column].isna().all():
                    continue
                
                values = data[column].dropna()
                
                if len(values) < 10:
                    continue
                
                # Testa normalidade
                _, p_value = stats.normaltest(values)
                
                # Calcula assimetria e curtose
                skewness = stats.skew(values)
                kurtosis = stats.kurtosis(values)
                
                # Detecta distribuições incomuns
                if p_value < 0.05:  # não normal
                    if abs(skewness) > 1:
                        insight = self._create_distribution_insight(
                            column, 'skewed', skewness, data_source
                        )
                        insights.append(insight)
                    
                    if abs(kurtosis) > 3:
                        insight = self._create_distribution_insight(
                            column, 'heavy_tailed', kurtosis, data_source
                        )
                        insights.append(insight)
        
        except Exception as e:
            log_error(f"Erro na detecção de padrões de distribuição", extra={"error": str(e)})
        
        return insights
    
    def _create_anomaly_insight(self, anomalies: pd.DataFrame, column: str, 
                               method: str, data_source: str) -> Insight:
        """Cria insight de anomalia"""
        severity = 'high' if len(anomalies) > 5 else 'medium'
        
        return Insight(
            id=f"anomaly_{column}_{method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Anomalias detectadas em {column}",
            description=f"Foram encontradas {len(anomalies)} anomalias na variável {column} usando o método {method}.",
            type="anomaly",
            severity=severity,
            confidence=0.8,
            data_source=data_source,
            timestamp=datetime.now(),
            metadata={
                'column': column,
                'method': method,
                'count': len(anomalies),
                'values': anomalies[column].tolist() if column in anomalies.columns else []
            },
            recommendations=[
                f"Investigar as causas das anomalias em {column}",
                "Verificar se os valores anômalos são erros de dados",
                "Considerar filtrar ou tratar os valores extremos"
            ]
        )
    
    def _create_trend_insight(self, trend: Trend, column: str, data_source: str) -> Insight:
        """Cria insight de tendência"""
        direction_text = {
            'up': 'crescimento',
            'down': 'declínio',
            'stable': 'estabilidade'
        }
        
        severity = 'high' if trend.strength > 0.8 else 'medium' if trend.strength > 0.6 else 'low'
        
        return Insight(
            id=f"trend_{column}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Tendência de {direction_text[trend.direction]} em {column}",
            description=f"Detectada tendência de {direction_text[trend.direction]} em {column} com força {trend.strength:.2f} ao longo de {trend.duration} dias.",
            type="trend",
            severity=severity,
            confidence=trend.strength,
            data_source=data_source,
            timestamp=datetime.now(),
            metadata={
                'column': column,
                'direction': trend.direction,
                'strength': trend.strength,
                'duration': trend.duration,
                'slope': trend.slope,
                'r_squared': trend.r_squared
            },
            recommendations=[
                f"Monitorar continuamente a tendência em {column}",
                "Investigar fatores que podem estar influenciando a tendência",
                "Considerar ajustar estratégias baseadas na tendência identificada"
            ]
        )
    
    def _create_correlation_insight(self, col1: str, col2: str, 
                                   correlation: float, data_source: str) -> Insight:
        """Cria insight de correlação"""
        correlation_type = 'positiva' if correlation > 0 else 'negativa'
        strength = 'forte' if abs(correlation) > 0.8 else 'moderada'
        
        return Insight(
            id=f"correlation_{col1}_{col2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Correlação {strength} {correlation_type} entre {col1} e {col2}",
            description=f"Identificada correlação {correlation_type} {strength} ({correlation:.3f}) entre {col1} e {col2}.",
            type="correlation",
            severity='medium',
            confidence=abs(correlation),
            data_source=data_source,
            timestamp=datetime.now(),
            metadata={
                'variable1': col1,
                'variable2': col2,
                'correlation': correlation,
                'type': correlation_type,
                'strength': strength
            },
            recommendations=[
                f"Explorar a relação causal entre {col1} e {col2}",
                "Considerar usar uma variável para prever a outra",
                "Investigar fatores comuns que podem influenciar ambas as variáveis"
            ]
        )
    
    def _create_forecast_insight(self, column: str, forecast: float, 
                                current: float, trend: float, data_source: str) -> Insight:
        """Cria insight de previsão"""
        change_pct = ((forecast - current) / current * 100) if current != 0 else 0
        direction = 'aumento' if change_pct > 0 else 'diminuição'
        
        return Insight(
            id=f"forecast_{column}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Previsão para {column}",
            description=f"Baseado na tendência recente, prevê-se {direction} de {abs(change_pct):.1f}% em {column}.",
            type="forecast",
            severity='low',
            confidence=0.6,
            data_source=data_source,
            timestamp=datetime.now(),
            metadata={
                'column': column,
                'forecast_value': forecast,
                'current_value': current,
                'trend': trend,
                'change_percent': change_pct
            },
            recommendations=[
                f"Monitorar {column} para validar a previsão",
                "Considerar fatores externos que podem afetar a previsão",
                "Ajustar estratégias baseadas na previsão"
            ]
        )
    
    def _create_seasonality_insight(self, column: str, pattern_type: str, 
                                   pattern: pd.Series, data_source: str) -> Insight:
        """Cria insight de sazonalidade"""
        peak_period = pattern.idxmax()
        low_period = pattern.idxmin()
        
        period_names = {
            'weekly': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'],
            'monthly': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        }
        
        if pattern_type in period_names:
            peak_name = period_names[pattern_type][peak_period] if peak_period < len(period_names[pattern_type]) else str(peak_period)
            low_name = period_names[pattern_type][low_period] if low_period < len(period_names[pattern_type]) else str(low_period)
        else:
            peak_name = str(peak_period)
            low_name = str(low_period)
        
        return Insight(
            id=f"seasonality_{column}_{pattern_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Padrão sazonal {pattern_type} em {column}",
            description=f"Identificado padrão sazonal {pattern_type} em {column}. Pico em {peak_name}, menor valor em {low_name}.",
            type="pattern",
            severity='medium',
            confidence=0.7,
            data_source=data_source,
            timestamp=datetime.now(),
            metadata={
                'column': column,
                'pattern_type': pattern_type,
                'peak_period': peak_period,
                'low_period': low_period,
                'pattern_values': pattern.to_dict()
            },
            recommendations=[
                f"Ajustar estratégias baseadas no padrão sazonal de {column}",
                f"Preparar recursos para o período de pico ({peak_name})",
                f"Investigar causas da baixa no período {low_name}"
            ]
        )
    
    def _create_cluster_insight(self, n_clusters: int, n_noise: int, 
                               total_points: int, data_source: str) -> Insight:
        """Cria insight de clusters"""
        return Insight(
            id=f"clusters_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Segmentação em {n_clusters} grupos",
            description=f"Os dados podem ser segmentados em {n_clusters} grupos distintos, com {n_noise} pontos atípicos.",
            type="pattern",
            severity='medium',
            confidence=0.7,
            data_source=data_source,
            timestamp=datetime.now(),
            metadata={
                'n_clusters': n_clusters,
                'n_noise': n_noise,
                'total_points': total_points,
                'noise_percentage': (n_noise / total_points * 100) if total_points > 0 else 0
            },
            recommendations=[
                "Analisar as características de cada grupo identificado",
                "Desenvolver estratégias específicas para cada segmento",
                "Investigar os pontos atípicos identificados"
            ]
        )
    
    def _create_distribution_insight(self, column: str, pattern_type: str, 
                                    value: float, data_source: str) -> Insight:
        """Cria insight de distribuição"""
        descriptions = {
            'skewed': f"A distribuição de {column} é assimétrica (assimetria: {value:.2f})",
            'heavy_tailed': f"A distribuição de {column} tem caudas pesadas (curtose: {value:.2f})"
        }
        
        return Insight(
            id=f"distribution_{column}_{pattern_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=f"Distribuição incomum em {column}",
            description=descriptions.get(pattern_type, f"Padrão {pattern_type} detectado em {column}"),
            type="pattern",
            severity='low',
            confidence=0.6,
            data_source=data_source,
            timestamp=datetime.now(),
            metadata={
                'column': column,
                'pattern_type': pattern_type,
                'value': value
            },
            recommendations=[
                f"Investigar as causas da distribuição incomum em {column}",
                "Considerar transformações nos dados se necessário",
                "Verificar se a distribuição afeta análises estatísticas"
            ]
        )
    
    def get_insights_summary(self) -> Dict[str, Any]:
        """Retorna resumo dos insights gerados"""
        if not self.insights_cache:
            return {'total': 0, 'by_type': {}, 'by_severity': {}}
        
        by_type = {}
        by_severity = {}
        
        for insight in self.insights_cache:
            by_type[insight.type] = by_type.get(insight.type, 0) + 1
            by_severity[insight.severity] = by_severity.get(insight.severity, 0) + 1
        
        return {
            'total': len(self.insights_cache),
            'by_type': by_type,
            'by_severity': by_severity,
            'latest': self.insights_cache[-5:] if len(self.insights_cache) > 5 else self.insights_cache
        }
    
    def clear_insights_cache(self):
        """Limpa o cache de insights"""
        self.insights_cache.clear()
        log_info("Cache de insights limpo")