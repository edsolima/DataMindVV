import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class DataAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        self.datetime_columns = data.select_dtypes(include=['datetime64']).columns.tolist()
    
    def get_descriptive_statistics(self, group_by: Optional[str] = None) -> pd.DataFrame:
        """Calculate descriptive statistics for numeric columns"""
        if group_by and group_by in self.categorical_columns:
            # Group statistics
            stats_df = self.data.groupby(group_by)[self.numeric_columns].agg([
                'count', 'mean', 'median', 'std', 'min', 'max',
                lambda x: x.quantile(0.25),  # Q1
                lambda x: x.quantile(0.75),  # Q3
            ])
            stats_df.columns = ['_'.join(col).strip() for col in stats_df.columns]
            return stats_df.reset_index()
        else:
            # Overall statistics
            stats_dict = {}
            for col in self.numeric_columns:
                series = self.data[col].dropna()
                stats_dict[col] = {
                    'count': len(series),
                    'mean': series.mean(),
                    'median': series.median(),
                    'std': series.std(),
                    'min': series.min(),
                    'max': series.max(),
                    'q25': series.quantile(0.25),
                    'q75': series.quantile(0.75),
                    'skewness': stats.skew(series),
                    'kurtosis': stats.kurtosis(series)
                }
            return pd.DataFrame(stats_dict).T
    
    def get_categorical_statistics(self) -> Dict[str, pd.DataFrame]:
        """Get value counts for categorical columns"""
        cat_stats = {}
        for col in self.categorical_columns:
            value_counts = self.data[col].value_counts()
            percentages = self.data[col].value_counts(normalize=True) * 100
            
            cat_stats[col] = pd.DataFrame({
                'count': value_counts,
                'percentage': percentages
            })
        return cat_stats
    
    def calculate_correlation_matrix(self, method: str = 'pearson') -> pd.DataFrame:
        """Calculate correlation matrix for numeric columns"""
        if len(self.numeric_columns) < 2:
            return pd.DataFrame()
        
        return self.data[self.numeric_columns].corr(method=method)
    
    def create_correlation_heatmap(self, method: str = 'pearson', threshold: float = None) -> go.Figure:
        """Create interactive correlation heatmap"""
        corr_matrix = self.calculate_correlation_matrix(method)
        
        if corr_matrix.empty:
            return go.Figure().add_annotation(
                text="Not enough numeric columns for correlation analysis",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font_size=16
            )
        
        # Apply threshold filter if specified
        if threshold is not None:
            mask = np.abs(corr_matrix) >= threshold
            corr_matrix = corr_matrix.where(mask, np.nan)
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0,
            text=np.round(corr_matrix.values, 3),
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False,
            hovertemplate='<b>%{x}</b> vs <b>%{y}</b><br>Correlation: %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=f'{method.capitalize()} Correlation Matrix',
            xaxis_title='Variables',
            yaxis_title='Variables',
            height=600
        )
        
        return fig
    
    def detect_outliers(self, column: str, method: str = 'iqr') -> Dict:
        """Detect outliers in a numeric column"""
        if column not in self.numeric_columns:
            return {'outliers': [], 'method': method, 'bounds': None}
        
        series = self.data[column].dropna()
        
        if method == 'iqr':
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = series[(series < lower_bound) | (series > upper_bound)]
            bounds = (lower_bound, upper_bound)
        
        elif method == 'zscore':
            z_scores = np.abs(stats.zscore(series))
            threshold = 3
            outliers = series[z_scores > threshold]
            bounds = (-threshold, threshold)
        
        else:
            return {'outliers': [], 'method': method, 'bounds': None}
        
        return {
            'outliers': outliers.tolist(),
            'outlier_indices': outliers.index.tolist(),
            'method': method,
            'bounds': bounds,
            'outlier_count': len(outliers),
            'total_count': len(series),
            'outlier_percentage': (len(outliers) / len(series)) * 100
        }
    
    def create_distribution_plots(self, columns: List[str] = None) -> go.Figure:
        """Create distribution plots for numeric columns"""
        if columns is None:
            columns = self.numeric_columns[:4]  # Limit to first 4 columns
        
        if not columns:
            return go.Figure().add_annotation(
                text="No numeric columns available for distribution analysis",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font_size=16
            )
        
        n_cols = min(2, len(columns))
        n_rows = (len(columns) + 1) // 2
        
        fig = make_subplots(
            rows=n_rows, cols=n_cols,
            subplot_titles=columns,
            specs=[[{"secondary_y": False} for _ in range(n_cols)] for _ in range(n_rows)]
        )
        
        for i, col in enumerate(columns):
            row = (i // n_cols) + 1
            col_pos = (i % n_cols) + 1
            
            # Histogram
            fig.add_trace(
                go.Histogram(
                    x=self.data[col].dropna(),
                    name=f'{col} Distribution',
                    opacity=0.7,
                    nbinsx=30
                ),
                row=row, col=col_pos
            )
        
        fig.update_layout(
            title="Distribution Analysis",
            height=300 * n_rows,
            showlegend=False
        )
        
        return fig
    
    def create_boxplot_analysis(self, numeric_col: str, category_col: str = None) -> go.Figure:
        """Create boxplot for outlier detection and comparison"""
        if numeric_col not in self.numeric_columns:
            return go.Figure().add_annotation(
                text=f"Column '{numeric_col}' is not numeric",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font_size=16
            )
        
        fig = go.Figure()
        
        if category_col and category_col in self.categorical_columns:
            # Grouped boxplot
            for category in self.data[category_col].unique():
                if pd.notna(category):
                    subset = self.data[self.data[category_col] == category][numeric_col].dropna()
                    fig.add_trace(go.Box(
                        y=subset,
                        name=str(category),
                        boxpoints='outliers'
                    ))
            fig.update_layout(
                title=f'{numeric_col} Distribution by {category_col}',
                xaxis_title=category_col,
                yaxis_title=numeric_col
            )
        else:
            # Single boxplot
            fig.add_trace(go.Box(
                y=self.data[numeric_col].dropna(),
                name=numeric_col,
                boxpoints='outliers'
            ))
            fig.update_layout(
                title=f'{numeric_col} Distribution and Outliers',
                yaxis_title=numeric_col
            )
        
        return fig
    
    def create_comparison_chart(self, metric_col: str, category_col: str, 
                              aggregation: str = 'mean', chart_type: str = 'bar') -> go.Figure:
        """Create comparison charts by category"""
        if metric_col not in self.numeric_columns or category_col not in self.categorical_columns:
            return go.Figure().add_annotation(
                text="Invalid column selection for comparison",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font_size=16
            )
        
        # Aggregate data
        agg_funcs = {
            'mean': 'mean',
            'sum': 'sum',
            'count': 'count',
            'median': 'median',
            'std': 'std'
        }
        
        if aggregation not in agg_funcs:
            aggregation = 'mean'
        
        grouped_data = self.data.groupby(category_col)[metric_col].agg(agg_funcs[aggregation]).reset_index()
        grouped_data = grouped_data.sort_values(metric_col, ascending=False)
        
        fig = go.Figure()
        
        if chart_type == 'bar':
            fig.add_trace(go.Bar(
                x=grouped_data[category_col],
                y=grouped_data[metric_col],
                text=grouped_data[metric_col].round(2),
                textposition='auto',
                hovertemplate=f'<b>%{{x}}</b><br>{aggregation.capitalize()}: %{{y:.2f}}<extra></extra>'
            ))
        elif chart_type == 'pie':
            fig.add_trace(go.Pie(
                labels=grouped_data[category_col],
                values=grouped_data[metric_col],
                hovertemplate='<b>%{label}</b><br>Value: %{value:.2f}<br>Percentage: %{percent}<extra></extra>'
            ))
        
        fig.update_layout(
            title=f'{aggregation.capitalize()} of {metric_col} by {category_col}',
            xaxis_title=category_col if chart_type == 'bar' else None,
            yaxis_title=f'{aggregation.capitalize()} {metric_col}' if chart_type == 'bar' else None
        )
        
        return fig
    
    def get_data_quality_report(self) -> Dict:
        """Generate a comprehensive data quality report"""
        report = {
            'total_rows': len(self.data),
            'total_columns': len(self.data.columns),
            'numeric_columns': len(self.numeric_columns),
            'categorical_columns': len(self.categorical_columns),
            'datetime_columns': len(self.datetime_columns),
            'missing_data': {},
            'duplicate_rows': self.data.duplicated().sum(),
            'memory_usage': self.data.memory_usage(deep=True).sum() / 1024**2  # MB
        }
        
        # Missing data analysis
        for col in self.data.columns:
            missing_count = self.data[col].isnull().sum()
            missing_percentage = (missing_count / len(self.data)) * 100
            report['missing_data'][col] = {
                'count': missing_count,
                'percentage': missing_percentage
            }
        
        return report
        
    def perform_ttest_ind(self, data_col: str, group_col: str) -> Dict:
        """Perform independent t-test between two groups"""
        if data_col not in self.numeric_columns:
            return None
        if group_col not in self.categorical_columns:
            return None
            
        # Get unique groups
        groups = self.data[group_col].unique()
        if len(groups) != 2:
            return None
            
        # Extract data for each group
        group1_data = self.data[self.data[group_col] == groups[0]][data_col].dropna()
        group2_data = self.data[self.data[group_col] == groups[1]][data_col].dropna()
        
        if len(group1_data) < 2 or len(group2_data) < 2:
            return None
            
        # Perform t-test
        t_stat, p_value = stats.ttest_ind(group1_data, group2_data, equal_var=False)
        
        # Calculate effect size (Cohen's d)
        mean1, mean2 = group1_data.mean(), group2_data.mean()
        std1, std2 = group1_data.std(), group2_data.std()
        pooled_std = np.sqrt(((len(group1_data) - 1) * std1**2 + (len(group2_data) - 1) * std2**2) / 
                             (len(group1_data) + len(group2_data) - 2))
        effect_size = abs(mean1 - mean2) / pooled_std if pooled_std > 0 else 0
        
        return {
            'group1': str(groups[0]),
            'group2': str(groups[1]),
            'group1_mean': float(mean1),
            'group2_mean': float(mean2),
            'group1_std': float(std1),
            'group2_std': float(std2),
            'group1_count': int(len(group1_data)),
            'group2_count': int(len(group2_data)),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'effect_size': float(effect_size)
        }
        
    def perform_anova_oneway(self, value_col: str, group_col: str) -> Dict:
        """Perform one-way ANOVA test"""
        if value_col not in self.numeric_columns:
            return None
        if group_col not in self.categorical_columns:
            return None
            
        # Get groups
        groups = self.data[group_col].unique()
        if len(groups) < 2:
            return None
            
        # Extract data for each group
        group_data = []
        group_stats = []
        
        for group in groups:
            group_values = self.data[self.data[group_col] == group][value_col].dropna()
            if len(group_values) > 0:
                group_data.append(group_values)
                group_stats.append({
                    'group': str(group),
                    'mean': float(group_values.mean()),
                    'std': float(group_values.std() if len(group_values) > 1 else 0),
                    'count': int(len(group_values))
                })
        
        if len(group_data) < 2 or any(len(gd) < 2 for gd in group_data):
            return None
            
        # Perform ANOVA
        f_stat, p_value = stats.f_oneway(*group_data)
        
        return {
            'f_statistic': float(f_stat),
            'p_value': float(p_value),
            'group_stats': group_stats,
            'num_groups': len(group_data)
        }
        
    def perform_chi_square_test(self, col1: str, col2: str) -> Dict:
        """Perform chi-square test of independence"""
        if col1 not in self.categorical_columns or col2 not in self.categorical_columns:
            return None
            
        # Create contingency table
        contingency_table = pd.crosstab(self.data[col1], self.data[col2])
        
        if contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
            return None
            
        # Perform chi-square test
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
        
        # Calculate Cramer's V (effect size)
        n = contingency_table.sum().sum()
        phi2 = chi2 / n
        r, k = contingency_table.shape
        cramer_v = np.sqrt(phi2 / min(k-1, r-1)) if min(k-1, r-1) > 0 else 0
        
        return {
            'chi2_statistic': float(chi2),
            'p_value': float(p_value),
            'degrees_of_freedom': int(dof),
            'cramer_v': float(cramer_v),
            'contingency_table': contingency_table.to_dict()
        }
        
    def generate_textual_insights(self, results: Dict, test_type: str) -> List[str]:
        """Generate textual insights based on statistical test results"""
        insights = []
        
        if not results:
            return ["Não foi possível gerar insights com os dados fornecidos."]
        
        if test_type == "ttest":
            p_value = results.get('p_value', 1.0)
            effect_size = results.get('effect_size', 0.0)
            group1 = results.get('group1', 'Grupo 1')
            group2 = results.get('group2', 'Grupo 2')
            mean1 = results.get('group1_mean', 0)
            mean2 = results.get('group2_mean', 0)
            
            # Significance interpretation
            if p_value < 0.001:
                insights.append(f"Há uma diferença estatisticamente muito significativa (p < 0.001) entre '{group1}' e '{group2}'.")
            elif p_value < 0.01:
                insights.append(f"Há uma diferença estatisticamente significativa (p < 0.01) entre '{group1}' e '{group2}'.")
            elif p_value < 0.05:
                insights.append(f"Há uma diferença estatisticamente significativa (p < 0.05) entre '{group1}' e '{group2}'.")
            else:
                insights.append(f"Não há diferença estatisticamente significativa (p = {p_value:.3f}) entre '{group1}' e '{group2}'.")
            
            # Effect size interpretation
            if effect_size < 0.2:
                effect_text = "negligível"
            elif effect_size < 0.5:
                effect_text = "pequeno"
            elif effect_size < 0.8:
                effect_text = "médio"
            else:
                effect_text = "grande"
                
            insights.append(f"O tamanho do efeito é {effect_text} (d = {effect_size:.2f}).")
            
            # Mean comparison
            insights.append(f"Média para '{group1}': {mean1:.2f}, Média para '{group2}': {mean2:.2f}.")
            
        elif test_type == "anova":
            p_value = results.get('p_value', 1.0)
            f_stat = results.get('f_statistic', 0.0)
            num_groups = results.get('num_groups', 0)
            
            # Significance interpretation
            if p_value < 0.001:
                insights.append(f"Há diferenças estatisticamente muito significativas (p < 0.001) entre os {num_groups} grupos.")
            elif p_value < 0.01:
                insights.append(f"Há diferenças estatisticamente significativas (p < 0.01) entre os {num_groups} grupos.")
            elif p_value < 0.05:
                insights.append(f"Há diferenças estatisticamente significativas (p < 0.05) entre os {num_groups} grupos.")
            else:
                insights.append(f"Não há diferenças estatisticamente significativas (p = {p_value:.3f}) entre os {num_groups} grupos.")
            
            # Group means
            if 'group_stats' in results:
                means_text = "Médias por grupo: " + ", ".join([f"{stat['group']}: {stat['mean']:.2f}" for stat in results['group_stats']])
                insights.append(means_text)
                
        elif test_type == "chi_square":
            p_value = results.get('p_value', 1.0)
            cramer_v = results.get('cramer_v', 0.0)
            dof = results.get('degrees_of_freedom', 0)
            
            # Significance interpretation
            if p_value < 0.001:
                insights.append(f"Há uma associação estatisticamente muito significativa (p < 0.001) entre as variáveis.")
            elif p_value < 0.01:
                insights.append(f"Há uma associação estatisticamente significativa (p < 0.01) entre as variáveis.")
            elif p_value < 0.05:
                insights.append(f"Há uma associação estatisticamente significativa (p < 0.05) entre as variáveis.")
            else:
                insights.append(f"Não há associação estatisticamente significativa (p = {p_value:.3f}) entre as variáveis.")
            
            # Effect size interpretation
            if cramer_v < 0.1:
                effect_text = "negligível"
            elif cramer_v < 0.3:
                effect_text = "fraca"
            elif cramer_v < 0.5:
                effect_text = "moderada"
            else:
                effect_text = "forte"
                
            insights.append(f"A força da associação é {effect_text} (V de Cramer = {cramer_v:.2f}).")
            
        return insights