# -*- coding: utf-8 -*-
"""
NLP Query Processor - Processamento de Consultas em Linguagem Natural
Permite que usuários façam consultas em português natural e obtenham visualizações
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd

from utils.logger import log_info, log_error, log_warning
from utils.database_manager import DatabaseManager
from utils.config_manager import ConfigManager

@dataclass
class QueryIntent:
    """Representa a intenção de uma consulta"""
    action: str  # 'show', 'compare', 'analyze', 'filter', 'aggregate'
    entity: str  # 'vendas', 'clientes', 'produtos', etc.
    attributes: List[str]  # colunas específicas
    filters: Dict[str, Any]  # filtros aplicados
    time_period: Optional[str] = None  # período temporal
    aggregation: Optional[str] = None  # tipo de agregação
    chart_type: Optional[str] = None  # tipo de gráfico sugerido
    confidence: float = 0.0  # confiança na interpretação

@dataclass
class ChartSuggestion:
    """Sugestão de gráfico baseada na consulta"""
    chart_type: str
    x_axis: str
    y_axis: str
    title: str
    description: str
    confidence: float

class NLPQueryProcessor:
    """Processador de consultas em linguagem natural"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        
        # Dicionários de mapeamento
        self.action_patterns = {
            'mostrar': ['mostrar', 'exibir', 'ver', 'visualizar', 'apresentar'],
            'comparar': ['comparar', 'contrastar', 'versus', 'vs', 'diferença'],
            'analisar': ['analisar', 'análise', 'estudar', 'examinar', 'investigar'],
            'filtrar': ['filtrar', 'onde', 'com', 'que', 'apenas'],
            'agregar': ['total', 'soma', 'média', 'máximo', 'mínimo', 'contar']
        }
        
        self.entity_patterns = {
            'vendas': ['vendas', 'venda', 'receita', 'faturamento', 'comercial'],
            'clientes': ['clientes', 'cliente', 'consumidores', 'compradores'],
            'produtos': ['produtos', 'produto', 'itens', 'mercadorias'],
            'funcionarios': ['funcionários', 'funcionario', 'colaboradores', 'equipe'],
            'pedidos': ['pedidos', 'pedido', 'ordens', 'solicitações'],
            'categorias': ['categorias', 'categoria', 'tipos', 'grupos']
        }
        
        self.time_patterns = {
            'hoje': ['hoje', 'hoje mesmo', 'dia atual'],
            'ontem': ['ontem', 'dia anterior'],
            'semana': ['semana', 'esta semana', 'semana atual', 'últimos 7 dias'],
            'mes': ['mês', 'este mês', 'mês atual', 'últimos 30 dias'],
            'ano': ['ano', 'este ano', 'ano atual', 'últimos 12 meses'],
            'ultimo_mes': ['mês passado', 'último mês', 'mês anterior'],
            'ultimo_ano': ['ano passado', 'último ano', 'ano anterior']
        }
        
        self.aggregation_patterns = {
            'sum': ['total', 'soma', 'somar', 'totalizar'],
            'avg': ['média', 'médio', 'promedio'],
            'max': ['máximo', 'maior', 'mais alto', 'pico'],
            'min': ['mínimo', 'menor', 'mais baixo'],
            'count': ['quantidade', 'número', 'contar', 'quantos']
        }
        
        self.chart_suggestions = {
            'temporal': 'line',
            'categorical': 'bar',
            'comparison': 'bar',
            'distribution': 'pie',
            'correlation': 'scatter',
            'trend': 'line'
        }
    
    def process_query(self, query: str) -> Tuple[QueryIntent, Optional[ChartSuggestion]]:
        """Processa uma consulta em linguagem natural"""
        try:
            # Normaliza a consulta
            normalized_query = self._normalize_query(query)
            
            # Extrai intenção
            intent = self._extract_intent(normalized_query)
            
            # Sugere gráfico
            chart_suggestion = self._suggest_chart(intent)
            
            log_info(f"Consulta processada: {query} -> {intent.action} {intent.entity}")
            
            return intent, chart_suggestion
            
        except Exception as e:
            log_error(f"Erro ao processar consulta: {query}", extra={"error": str(e)})
            return self._create_default_intent(), None
    
    def _normalize_query(self, query: str) -> str:
        """Normaliza a consulta removendo acentos e convertendo para minúsculas"""
        # Remove acentos
        replacements = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
            'é': 'e', 'ê': 'e',
            'í': 'i', 'î': 'i',
            'ó': 'o', 'ô': 'o', 'õ': 'o',
            'ú': 'u', 'û': 'u',
            'ç': 'c'
        }
        
        normalized = query.lower()
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _extract_intent(self, query: str) -> QueryIntent:
        """Extrai a intenção da consulta"""
        # Detecta ação
        action = self._detect_action(query)
        
        # Detecta entidade
        entity = self._detect_entity(query)
        
        # Detecta atributos
        attributes = self._detect_attributes(query, entity)
        
        # Detecta filtros
        filters = self._detect_filters(query)
        
        # Detecta período temporal
        time_period = self._detect_time_period(query)
        
        # Detecta agregação
        aggregation = self._detect_aggregation(query)
        
        # Calcula confiança
        confidence = self._calculate_confidence(action, entity, attributes)
        
        return QueryIntent(
            action=action,
            entity=entity,
            attributes=attributes,
            filters=filters,
            time_period=time_period,
            aggregation=aggregation,
            confidence=confidence
        )
    
    def _detect_action(self, query: str) -> str:
        """Detecta a ação na consulta"""
        for action, patterns in self.action_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    return action
        return 'mostrar'  # ação padrão
    
    def _detect_entity(self, query: str) -> str:
        """Detecta a entidade principal na consulta"""
        for entity, patterns in self.entity_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    return entity
        return 'vendas'  # entidade padrão
    
    def _detect_attributes(self, query: str, entity: str) -> List[str]:
        """Detecta atributos específicos na consulta"""
        attributes = []
        
        # Mapeamento de atributos por entidade
        entity_attributes = {
            'vendas': ['valor', 'quantidade', 'data', 'produto', 'cliente', 'vendedor'],
            'clientes': ['nome', 'email', 'telefone', 'cidade', 'estado', 'idade'],
            'produtos': ['nome', 'preco', 'categoria', 'estoque', 'fornecedor'],
            'funcionarios': ['nome', 'cargo', 'salario', 'departamento', 'data_admissao'],
            'pedidos': ['numero', 'data', 'status', 'valor_total', 'cliente']
        }
        
        possible_attributes = entity_attributes.get(entity, [])
        
        for attr in possible_attributes:
            if attr in query or attr.replace('_', ' ') in query:
                attributes.append(attr)
        
        # Se não encontrou atributos específicos, usa padrões
        if not attributes:
            if entity == 'vendas':
                attributes = ['valor', 'data']
            elif entity == 'clientes':
                attributes = ['nome', 'cidade']
            else:
                attributes = ['nome']
        
        return attributes
    
    def _detect_filters(self, query: str) -> Dict[str, Any]:
        """Detecta filtros na consulta"""
        filters = {}
        
        # Detecta filtros de valor
        value_patterns = [
            r'maior que (\d+)',
            r'menor que (\d+)',
            r'igual a (\d+)',
            r'acima de (\d+)',
            r'abaixo de (\d+)'
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, query)
            if match:
                value = int(match.group(1))
                if 'maior' in pattern or 'acima' in pattern:
                    filters['valor_min'] = value
                elif 'menor' in pattern or 'abaixo' in pattern:
                    filters['valor_max'] = value
                else:
                    filters['valor'] = value
        
        # Detecta filtros de categoria
        if 'categoria' in query:
            # Extrai categoria específica se mencionada
            category_match = re.search(r'categoria ([\w\s]+)', query)
            if category_match:
                filters['categoria'] = category_match.group(1).strip()
        
        return filters
    
    def _detect_time_period(self, query: str) -> Optional[str]:
        """Detecta período temporal na consulta"""
        for period, patterns in self.time_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    return period
        
        # Detecta datas específicas
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, query):
                return 'data_especifica'
        
        return None
    
    def _detect_aggregation(self, query: str) -> Optional[str]:
        """Detecta tipo de agregação na consulta"""
        for agg_type, patterns in self.aggregation_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    return agg_type
        return None
    
    def _calculate_confidence(self, action: str, entity: str, attributes: List[str]) -> float:
        """Calcula confiança na interpretação"""
        confidence = 0.5  # base
        
        # Aumenta confiança se encontrou ação específica
        if action != 'mostrar':
            confidence += 0.2
        
        # Aumenta confiança se encontrou entidade específica
        if entity != 'vendas':
            confidence += 0.2
        
        # Aumenta confiança se encontrou atributos específicos
        if len(attributes) > 1:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _suggest_chart(self, intent: QueryIntent) -> Optional[ChartSuggestion]:
        """Sugere tipo de gráfico baseado na intenção"""
        try:
            chart_type = 'bar'  # padrão
            x_axis = intent.attributes[0] if intent.attributes else 'categoria'
            y_axis = 'valor'
            
            # Determina tipo de gráfico baseado na intenção
            if intent.time_period:
                chart_type = 'line'
                x_axis = 'data'
            elif intent.action == 'comparar':
                chart_type = 'bar'
            elif intent.aggregation == 'count':
                chart_type = 'pie'
            elif len(intent.attributes) > 2:
                chart_type = 'scatter'
            
            # Ajusta eixos baseado na entidade
            if intent.entity == 'vendas':
                y_axis = 'valor' if 'valor' in intent.attributes else 'quantidade'
            elif intent.entity == 'clientes':
                y_axis = 'quantidade'
                x_axis = 'cidade' if 'cidade' in intent.attributes else 'mes'
            
            # Gera título
            title = self._generate_chart_title(intent)
            
            # Gera descrição
            description = self._generate_chart_description(intent, chart_type)
            
            return ChartSuggestion(
                chart_type=chart_type,
                x_axis=x_axis,
                y_axis=y_axis,
                title=title,
                description=description,
                confidence=intent.confidence
            )
            
        except Exception as e:
            log_error(f"Erro ao sugerir gráfico", extra={"error": str(e)})
            return None
    
    def _generate_chart_title(self, intent: QueryIntent) -> str:
        """Gera título para o gráfico"""
        entity_names = {
            'vendas': 'Vendas',
            'clientes': 'Clientes',
            'produtos': 'Produtos',
            'funcionarios': 'Funcionários',
            'pedidos': 'Pedidos'
        }
        
        entity_name = entity_names.get(intent.entity, intent.entity.title())
        
        if intent.time_period:
            time_names = {
                'hoje': 'Hoje',
                'semana': 'Esta Semana',
                'mes': 'Este Mês',
                'ano': 'Este Ano'
            }
            time_name = time_names.get(intent.time_period, intent.time_period.title())
            return f"{entity_name} - {time_name}"
        
        if intent.aggregation:
            agg_names = {
                'sum': 'Total de',
                'avg': 'Média de',
                'max': 'Máximo de',
                'min': 'Mínimo de',
                'count': 'Quantidade de'
            }
            agg_name = agg_names.get(intent.aggregation, '')
            return f"{agg_name} {entity_name}"
        
        return f"Análise de {entity_name}"
    
    def _generate_chart_description(self, intent: QueryIntent, chart_type: str) -> str:
        """Gera descrição para o gráfico"""
        chart_names = {
            'line': 'gráfico de linha',
            'bar': 'gráfico de barras',
            'pie': 'gráfico de pizza',
            'scatter': 'gráfico de dispersão'
        }
        
        chart_name = chart_names.get(chart_type, 'gráfico')
        entity_name = intent.entity
        
        return f"Este {chart_name} mostra a análise de {entity_name} baseada na sua consulta."
    
    def _create_default_intent(self) -> QueryIntent:
        """Cria intenção padrão em caso de erro"""
        return QueryIntent(
            action='mostrar',
            entity='vendas',
            attributes=['valor', 'data'],
            filters={},
            confidence=0.1
        )
    
    def generate_sql_query(self, intent: QueryIntent) -> str:
        """Gera consulta SQL baseada na intenção"""
        try:
            # Mapeia entidades para tabelas
            table_mapping = {
                'vendas': 'vendas',
                'clientes': 'clientes',
                'produtos': 'produtos',
                'funcionarios': 'funcionarios',
                'pedidos': 'pedidos'
            }
            
            table = table_mapping.get(intent.entity, 'vendas')
            
            # Constrói SELECT
            if intent.aggregation:
                if intent.aggregation == 'count':
                    select_clause = f"COUNT(*) as quantidade"
                else:
                    agg_func = intent.aggregation.upper()
                    value_col = 'valor' if 'valor' in intent.attributes else intent.attributes[0]
                    select_clause = f"{agg_func}({value_col}) as {intent.aggregation}_{value_col}"
                
                # Adiciona GROUP BY se necessário
                if len(intent.attributes) > 1:
                    group_col = [attr for attr in intent.attributes if attr != 'valor'][0]
                    select_clause += f", {group_col}"
                    group_clause = f" GROUP BY {group_col}"
                else:
                    group_clause = ""
            else:
                select_clause = ", ".join(intent.attributes) if intent.attributes else "*"
                group_clause = ""
            
            # Constrói WHERE
            where_conditions = []
            
            # Adiciona filtros de valor
            for key, value in intent.filters.items():
                if key == 'valor_min':
                    where_conditions.append(f"valor >= {value}")
                elif key == 'valor_max':
                    where_conditions.append(f"valor <= {value}")
                elif key == 'valor':
                    where_conditions.append(f"valor = {value}")
                else:
                    where_conditions.append(f"{key} = '{value}'")
            
            # Adiciona filtros temporais
            if intent.time_period:
                time_condition = self._generate_time_condition(intent.time_period)
                if time_condition:
                    where_conditions.append(time_condition)
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Constrói consulta final
            query = f"SELECT {select_clause} FROM {table}{where_clause}{group_clause}"
            
            # Adiciona ORDER BY
            if 'data' in intent.attributes:
                query += " ORDER BY data DESC"
            elif intent.aggregation:
                query += f" ORDER BY {intent.aggregation}_{intent.attributes[0] if intent.attributes else 'valor'} DESC"
            
            # Adiciona LIMIT
            query += " LIMIT 100"
            
            log_info(f"SQL gerado: {query}")
            return query
            
        except Exception as e:
            log_error(f"Erro ao gerar SQL", extra={"error": str(e)})
            return "SELECT * FROM vendas LIMIT 10"
    
    def _generate_time_condition(self, time_period: str) -> Optional[str]:
        """Gera condição temporal para SQL"""
        conditions = {
            'hoje': "date(data) = date('now')",
            'ontem': "date(data) = date('now', '-1 day')",
            'semana': "date(data) >= date('now', '-7 days')",
            'mes': "date(data) >= date('now', '-1 month')",
            'ano': "date(data) >= date('now', '-1 year')",
            'ultimo_mes': "date(data) >= date('now', '-2 months') AND date(data) < date('now', '-1 month')",
            'ultimo_ano': "date(data) >= date('now', '-2 years') AND date(data) < date('now', '-1 year')"
        }
        
        return conditions.get(time_period)
    
    def get_example_queries(self) -> List[str]:
        """Retorna exemplos de consultas que podem ser processadas"""
        return [
            "Mostre as vendas deste mês",
            "Compare vendas por região",
            "Qual o total de vendas hoje?",
            "Analise clientes por cidade",
            "Produtos com maior faturamento",
            "Vendas acima de 1000 reais",
            "Média de vendas por vendedor",
            "Quantidade de pedidos esta semana",
            "Clientes que compraram mais de 5 produtos",
            "Evolução das vendas no último ano"
        ]