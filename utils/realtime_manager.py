# -*- coding: utf-8 -*-
"""
Realtime Manager - Gerenciamento de Dados em Tempo Real
Permite streaming de dados e atualizações periódicas
"""

import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from queue import Queue
import pandas as pd

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager
from utils.database_manager import DatabaseManager

@dataclass
class DataStream:
    """Representa um stream de dados"""
    id: str
    name: str
    source_type: str  # 'database', 'api', 'file', 'websocket'
    source_config: Dict[str, Any]
    update_interval: int  # segundos
    last_update: Optional[datetime] = None
    is_active: bool = True
    callback: Optional[Callable] = None

@dataclass
class RealtimeAlert:
    """Representa um alerta em tempo real"""
    id: str
    name: str
    condition: str  # expressão Python para avaliar
    message: str
    severity: str  # 'info', 'warning', 'error', 'critical'
    channels: List[str]  # canais de notificação
    is_active: bool = True
    last_triggered: Optional[datetime] = None

class RealtimeManager:
    """Gerenciador de dados em tempo real"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager()
        self.streams: Dict[str, DataStream] = {}
        self.alerts: Dict[str, RealtimeAlert] = {}
        self.data_queue = Queue()
        self.is_running = False
        self.update_thread = None
        self.websocket_clients = set()
        
        # Cache para dados em tempo real
        self.realtime_cache: Dict[str, pd.DataFrame] = {}
        
        # Configurações padrão
        self.default_config = {
            'max_cache_size': 1000,
            'cleanup_interval': 300,  # 5 minutos
            'max_alert_frequency': 60  # 1 minuto
        }
    
    def start(self):
        """Inicia o gerenciador de tempo real"""
        if not self.is_running:
            self.is_running = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            log_info("Gerenciador de tempo real iniciado")
    
    def stop(self):
        """Para o gerenciador de tempo real"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        log_info("Gerenciador de tempo real parado")
    
    def add_stream(self, stream: DataStream) -> bool:
        """Adiciona um novo stream de dados"""
        try:
            self.streams[stream.id] = stream
            log_info(f"Stream adicionado: {stream.name} ({stream.id})")
            return True
        except Exception as e:
            log_error(f"Erro ao adicionar stream {stream.id}", extra={"error": str(e)})
            return False
    
    def remove_stream(self, stream_id: str) -> bool:
        """Remove um stream de dados"""
        try:
            if stream_id in self.streams:
                del self.streams[stream_id]
                if stream_id in self.realtime_cache:
                    del self.realtime_cache[stream_id]
                log_info(f"Stream removido: {stream_id}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao remover stream {stream_id}", extra={"error": str(e)})
            return False
    
    def add_alert(self, alert: RealtimeAlert) -> bool:
        """Adiciona um novo alerta"""
        try:
            self.alerts[alert.id] = alert
            log_info(f"Alerta adicionado: {alert.name} ({alert.id})")
            return True
        except Exception as e:
            log_error(f"Erro ao adicionar alerta {alert.id}", extra={"error": str(e)})
            return False
    
    def remove_alert(self, alert_id: str) -> bool:
        """Remove um alerta"""
        try:
            if alert_id in self.alerts:
                del self.alerts[alert_id]
                log_info(f"Alerta removido: {alert_id}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao remover alerta {alert_id}", extra={"error": str(e)})
            return False
    
    def get_realtime_data(self, stream_id: str) -> Optional[pd.DataFrame]:
        """Obtém dados em tempo real de um stream"""
        return self.realtime_cache.get(stream_id)
    
    def _update_loop(self):
        """Loop principal de atualização"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Atualiza streams
                for stream in self.streams.values():
                    if self._should_update_stream(stream, current_time):
                        self._update_stream(stream)
                
                # Verifica alertas
                self._check_alerts()
                
                # Limpa cache antigo
                self._cleanup_cache()
                
                time.sleep(1)  # Verifica a cada segundo
                
            except Exception as e:
                log_error("Erro no loop de atualização em tempo real", extra={"error": str(e)})
                time.sleep(5)
    
    def _should_update_stream(self, stream: DataStream, current_time: datetime) -> bool:
        """Verifica se um stream deve ser atualizado"""
        if not stream.is_active:
            return False
        
        if stream.last_update is None:
            return True
        
        time_diff = (current_time - stream.last_update).total_seconds()
        return time_diff >= stream.update_interval
    
    def _update_stream(self, stream: DataStream):
        """Atualiza dados de um stream"""
        try:
            data = None
            
            if stream.source_type == 'database':
                data = self._fetch_database_data(stream)
            elif stream.source_type == 'api':
                data = self._fetch_api_data(stream)
            elif stream.source_type == 'file':
                data = self._fetch_file_data(stream)
            elif stream.source_type == 'websocket':
                data = self._fetch_websocket_data(stream)
            
            if data is not None:
                # Atualiza cache
                self.realtime_cache[stream.id] = data
                stream.last_update = datetime.now()
                
                # Chama callback se definido
                if stream.callback:
                    stream.callback(stream.id, data)
                
                # Notifica clientes WebSocket
                self._notify_websocket_clients(stream.id, data)
                
                log_info(f"Stream atualizado: {stream.name} ({len(data)} registros)")
            
        except Exception as e:
            log_error(f"Erro ao atualizar stream {stream.id}", extra={"error": str(e)})
    
    def _fetch_database_data(self, stream: DataStream) -> Optional[pd.DataFrame]:
        """Busca dados do banco de dados"""
        try:
            config = stream.source_config
            query = config.get('query', '')
            
            if query:
                return self.db_manager.execute_query(query)
            
        except Exception as e:
            log_error(f"Erro ao buscar dados do banco para stream {stream.id}", extra={"error": str(e)})
        
        return None
    
    def _fetch_api_data(self, stream: DataStream) -> Optional[pd.DataFrame]:
        """Busca dados de uma API"""
        try:
            import requests
            
            config = stream.source_config
            url = config.get('url', '')
            method = config.get('method', 'GET')
            headers = config.get('headers', {})
            params = config.get('params', {})
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Converte para DataFrame
                if isinstance(data, list):
                    return pd.DataFrame(data)
                elif isinstance(data, dict) and 'data' in data:
                    return pd.DataFrame(data['data'])
                else:
                    return pd.DataFrame([data])
            
        except Exception as e:
            log_error(f"Erro ao buscar dados da API para stream {stream.id}", extra={"error": str(e)})
        
        return None
    
    def _fetch_file_data(self, stream: DataStream) -> Optional[pd.DataFrame]:
        """Busca dados de um arquivo"""
        try:
            config = stream.source_config
            file_path = config.get('path', '')
            file_type = config.get('type', 'csv')
            
            if file_type.lower() == 'csv':
                return pd.read_csv(file_path)
            elif file_type.lower() == 'excel':
                return pd.read_excel(file_path)
            elif file_type.lower() == 'json':
                return pd.read_json(file_path)
            
        except Exception as e:
            log_error(f"Erro ao buscar dados do arquivo para stream {stream.id}", extra={"error": str(e)})
        
        return None
    
    def _fetch_websocket_data(self, stream: DataStream) -> Optional[pd.DataFrame]:
        """Busca dados de WebSocket (placeholder)"""
        # Implementação futura para WebSocket
        return None
    
    def _check_alerts(self):
        """Verifica alertas em tempo real"""
        current_time = datetime.now()
        
        for alert in self.alerts.values():
            if not alert.is_active:
                continue
            
            # Verifica frequência mínima
            if alert.last_triggered:
                time_diff = (current_time - alert.last_triggered).total_seconds()
                if time_diff < self.default_config['max_alert_frequency']:
                    continue
            
            try:
                # Avalia condição do alerta
                if self._evaluate_alert_condition(alert):
                    self._trigger_alert(alert)
                    alert.last_triggered = current_time
                    
            except Exception as e:
                log_error(f"Erro ao verificar alerta {alert.id}", extra={"error": str(e)})
    
    def _evaluate_alert_condition(self, alert: RealtimeAlert) -> bool:
        """Avalia a condição de um alerta"""
        try:
            # Cria contexto com dados em tempo real
            context = {
                'data': self.realtime_cache,
                'datetime': datetime,
                'pd': pd
            }
            
            # Adiciona funções auxiliares
            context.update({
                'len': len,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs
            })
            
            # Avalia expressão
            return eval(alert.condition, {"__builtins__": {}}, context)
            
        except Exception as e:
            log_error(f"Erro ao avaliar condição do alerta {alert.id}", extra={"error": str(e)})
            return False
    
    def _trigger_alert(self, alert: RealtimeAlert):
        """Dispara um alerta"""
        try:
            alert_data = {
                'id': alert.id,
                'name': alert.name,
                'message': alert.message,
                'severity': alert.severity,
                'timestamp': datetime.now().isoformat()
            }
            
            # Envia para canais configurados
            for channel in alert.channels:
                self._send_alert_to_channel(channel, alert_data)
            
            log_warning(f"Alerta disparado: {alert.name} - {alert.message}")
            
        except Exception as e:
            log_error(f"Erro ao disparar alerta {alert.id}", extra={"error": str(e)})
    
    def _send_alert_to_channel(self, channel: str, alert_data: Dict[str, Any]):
        """Envia alerta para um canal específico"""
        try:
            if channel == 'websocket':
                self._notify_websocket_clients('alert', alert_data)
            elif channel == 'email':
                self._send_email_alert(alert_data)
            elif channel == 'slack':
                self._send_slack_alert(alert_data)
            elif channel == 'webhook':
                self._send_webhook_alert(alert_data)
                
        except Exception as e:
            log_error(f"Erro ao enviar alerta para canal {channel}", extra={"error": str(e)})
    
    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Envia alerta por email (placeholder)"""
        # Implementação futura para email
        pass
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Envia alerta para Slack (placeholder)"""
        # Implementação futura para Slack
        pass
    
    def _send_webhook_alert(self, alert_data: Dict[str, Any]):
        """Envia alerta via webhook (placeholder)"""
        # Implementação futura para webhook
        pass
    
    def _notify_websocket_clients(self, event_type: str, data: Any):
        """Notifica clientes WebSocket"""
        try:
            message = {
                'type': event_type,
                'data': data if isinstance(data, dict) else data.to_dict('records') if hasattr(data, 'to_dict') else str(data),
                'timestamp': datetime.now().isoformat()
            }
            
            # Aqui seria implementada a notificação WebSocket real
            # Por enquanto, apenas registra no log
            log_info(f"Notificação WebSocket: {event_type}")
            
        except Exception as e:
            log_error(f"Erro ao notificar clientes WebSocket", extra={"error": str(e)})
    
    def _cleanup_cache(self):
        """Limpa cache antigo"""
        try:
            max_size = self.default_config['max_cache_size']
            
            for stream_id, data in list(self.realtime_cache.items()):
                if len(data) > max_size:
                    # Mantém apenas os registros mais recentes
                    self.realtime_cache[stream_id] = data.tail(max_size)
                    
        except Exception as e:
            log_error("Erro ao limpar cache", extra={"error": str(e)})
    
    def get_stream_status(self) -> Dict[str, Any]:
        """Obtém status dos streams"""
        status = {
            'is_running': self.is_running,
            'total_streams': len(self.streams),
            'active_streams': len([s for s in self.streams.values() if s.is_active]),
            'total_alerts': len(self.alerts),
            'active_alerts': len([a for a in self.alerts.values() if a.is_active]),
            'cache_size': sum(len(data) for data in self.realtime_cache.values()),
            'streams': []
        }
        
        for stream in self.streams.values():
            stream_info = {
                'id': stream.id,
                'name': stream.name,
                'source_type': stream.source_type,
                'update_interval': stream.update_interval,
                'is_active': stream.is_active,
                'last_update': stream.last_update.isoformat() if stream.last_update else None,
                'data_count': len(self.realtime_cache.get(stream.id, []))
            }
            status['streams'].append(stream_info)
        
        return status
    
    def create_sample_streams(self):
        """Cria streams de exemplo para demonstração"""
        # Stream de vendas simulado
        sales_stream = DataStream(
            id='sales_realtime',
            name='Vendas em Tempo Real',
            source_type='database',
            source_config={
                'query': 'SELECT * FROM vendas WHERE data >= date("now", "-1 day") ORDER BY data DESC LIMIT 100'
            },
            update_interval=30  # 30 segundos
        )
        
        # Stream de KPIs simulado
        kpi_stream = DataStream(
            id='kpi_realtime',
            name='KPIs em Tempo Real',
            source_type='database',
            source_config={
                'query': 'SELECT COUNT(*) as total_vendas, SUM(valor) as receita_total FROM vendas WHERE data >= date("now")'
            },
            update_interval=60  # 1 minuto
        )
        
        self.add_stream(sales_stream)
        self.add_stream(kpi_stream)
        
        # Alerta de exemplo
        sales_alert = RealtimeAlert(
            id='high_sales_alert',
            name='Vendas Altas',
            condition='len(data.get("sales_realtime", [])) > 50',
            message='Volume de vendas acima do normal detectado!',
            severity='warning',
            channels=['websocket']
        )
        
        self.add_alert(sales_alert)
        
        log_info("Streams e alertas de exemplo criados")