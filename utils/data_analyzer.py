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