# -*- coding: utf-8 -*-
"""
Performance Monitor - Monitor de Performance
Sistema de monitoramento de performance em tempo real
"""

import time
import psutil
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
from enum import Enum
import sqlite3
import weakref
import functools
import traceback
import gc

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager

class MetricType(Enum):
    """Tipos de métricas"""
    COUNTER = "counter"          # Contador incremental
    GAUGE = "gauge"              # Valor atual
    HISTOGRAM = "histogram"      # Distribuição de valores
    TIMER = "timer"              # Tempo de execução
    MEMORY = "memory"            # Uso de memória
    CPU = "cpu"                  # Uso de CPU
    DISK = "disk"                # Uso de disco
    NETWORK = "network"          # Uso de rede
    CUSTOM = "custom"            # Métrica customizada

class AlertLevel(Enum):
    """Níveis de alerta"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Metric:
    """Métrica de performance"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None
    unit: str = ""
    description: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass
class Alert:
    """Alerta de performance"""
    id: str
    metric_name: str
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

@dataclass
class PerformanceSnapshot:
    """Snapshot de performance do sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    process_count: int
    thread_count: int
    load_average: float = 0.0

class MetricCollector:
    """Coletor de métricas"""
    
    def __init__(self, max_history: int = 1000):
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.counters = defaultdict(float)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.timers = defaultdict(list)
        self.lock = threading.RLock()
    
    def record_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Registra contador"""
        with self.lock:
            self.counters[name] += value
            metric = Metric(
                name=name,
                type=MetricType.COUNTER,
                value=self.counters[name],
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[name].append(metric)
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Registra gauge"""
        with self.lock:
            self.gauges[name] = value
            metric = Metric(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[name].append(metric)
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Registra valor no histograma"""
        with self.lock:
            self.histograms[name].append(value)
            # Mantém apenas últimos 1000 valores
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            
            metric = Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[name].append(metric)
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Registra tempo de execução"""
        with self.lock:
            self.timers[name].append(duration)
            # Mantém apenas últimos 1000 valores
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
            
            metric = Metric(
                name=name,
                type=MetricType.TIMER,
                value=duration,
                timestamp=datetime.now(),
                tags=tags or {},
                unit="ms"
            )
            self.metrics[name].append(metric)
    
    def get_metrics(self, name: str = None) -> Dict[str, List[Metric]]:
        """Retorna métricas"""
        with self.lock:
            if name:
                return {name: list(self.metrics.get(name, []))}
            return {k: list(v) for k, v in self.metrics.items()}
    
    def get_latest_value(self, name: str) -> Optional[float]:
        """Retorna último valor de uma métrica"""
        with self.lock:
            if name in self.metrics and self.metrics[name]:
                return self.metrics[name][-1].value
            return None
    
    def get_statistics(self, name: str) -> Dict[str, float]:
        """Retorna estatísticas de uma métrica"""
        with self.lock:
            if name not in self.metrics or not self.metrics[name]:
                return {}
            
            values = [m.value for m in self.metrics[name]]
            
            if not values:
                return {}
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1]
            }
    
    def clear_metrics(self, name: str = None):
        """Limpa métricas"""
        with self.lock:
            if name:
                if name in self.metrics:
                    self.metrics[name].clear()
                if name in self.counters:
                    del self.counters[name]
                if name in self.gauges:
                    del self.gauges[name]
                if name in self.histograms:
                    del self.histograms[name]
                if name in self.timers:
                    del self.timers[name]
            else:
                self.metrics.clear()
                self.counters.clear()
                self.gauges.clear()
                self.histograms.clear()
                self.timers.clear()

class SystemMonitor:
    """Monitor de sistema"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.process = psutil.Process()
        self.last_network_stats = None
        self.start_time = time.time()
    
    def collect_system_metrics(self) -> PerformanceSnapshot:
        """Coleta métricas do sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.collector.record_gauge('system.cpu.percent', cpu_percent)
            
            # Memória
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / 1024 / 1024
            memory_available_mb = memory.available / 1024 / 1024
            
            self.collector.record_gauge('system.memory.percent', memory_percent)
            self.collector.record_gauge('system.memory.used_mb', memory_used_mb)
            self.collector.record_gauge('system.memory.available_mb', memory_available_mb)
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            
            self.collector.record_gauge('system.disk.percent', disk_percent)
            self.collector.record_gauge('system.disk.free_gb', disk_free_gb)
            
            # Rede
            network = psutil.net_io_counters()
            if self.last_network_stats:
                bytes_sent_delta = network.bytes_sent - self.last_network_stats.bytes_sent
                bytes_recv_delta = network.bytes_recv - self.last_network_stats.bytes_recv
                
                self.collector.record_gauge('system.network.bytes_sent_rate', bytes_sent_delta)
                self.collector.record_gauge('system.network.bytes_recv_rate', bytes_recv_delta)
            
            self.last_network_stats = network
            
            # Processos e threads
            process_count = len(psutil.pids())
            thread_count = threading.active_count()
            
            self.collector.record_gauge('system.process.count', process_count)
            self.collector.record_gauge('system.thread.count', thread_count)
            
            # Conexões ativas
            try:
                connections = len(psutil.net_connections())
                self.collector.record_gauge('system.network.connections', connections)
            except:
                connections = 0
            
            # Load average (apenas em sistemas Unix)
            load_avg = 0.0
            try:
                if hasattr(psutil, 'getloadavg'):
                    load_avg = psutil.getloadavg()[0]
                    self.collector.record_gauge('system.load.avg1', load_avg)
            except:
                pass
            
            return PerformanceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                active_connections=connections,
                process_count=process_count,
                thread_count=thread_count,
                load_average=load_avg
            )
            
        except Exception as e:
            log_error(f"Erro ao coletar métricas do sistema: {e}")
            return None
    
    def collect_process_metrics(self):
        """Coleta métricas do processo atual"""
        try:
            # CPU do processo
            cpu_percent = self.process.cpu_percent()
            self.collector.record_gauge('process.cpu.percent', cpu_percent)
            
            # Memória do processo
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self.collector.record_gauge('process.memory.rss_mb', memory_mb)
            
            # Threads do processo
            thread_count = self.process.num_threads()
            self.collector.record_gauge('process.thread.count', thread_count)
            
            # Arquivos abertos
            try:
                open_files = len(self.process.open_files())
                self.collector.record_gauge('process.files.open', open_files)
            except:
                pass
            
            # Tempo de execução
            uptime = time.time() - self.start_time
            self.collector.record_gauge('process.uptime.seconds', uptime)
            
        except Exception as e:
            log_error(f"Erro ao coletar métricas do processo: {e}")

class AlertManager:
    """Gerenciador de alertas"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.alerts = {}
        self.thresholds = {}
        self.callbacks = defaultdict(list)
        self.lock = threading.RLock()
    
    def set_threshold(self, metric_name: str, threshold: float, 
                     level: AlertLevel = AlertLevel.WARNING,
                     operator: str = ">"):
        """Define threshold para métrica"""
        with self.lock:
            self.thresholds[metric_name] = {
                'threshold': threshold,
                'level': level,
                'operator': operator
            }
    
    def add_alert_callback(self, level: AlertLevel, callback: Callable[[Alert], None]):
        """Adiciona callback para alertas"""
        self.callbacks[level].append(callback)
    
    def check_thresholds(self):
        """Verifica thresholds e gera alertas"""
        with self.lock:
            for metric_name, config in self.thresholds.items():
                current_value = self.collector.get_latest_value(metric_name)
                
                if current_value is None:
                    continue
                
                threshold = config['threshold']
                level = config['level']
                operator = config['operator']
                
                # Verifica condição
                triggered = False
                if operator == ">" and current_value > threshold:
                    triggered = True
                elif operator == "<" and current_value < threshold:
                    triggered = True
                elif operator == ">=" and current_value >= threshold:
                    triggered = True
                elif operator == "<=" and current_value <= threshold:
                    triggered = True
                elif operator == "==" and current_value == threshold:
                    triggered = True
                
                alert_id = f"{metric_name}_{operator}_{threshold}"
                
                if triggered:
                    # Cria ou atualiza alerta
                    if alert_id not in self.alerts or self.alerts[alert_id].resolved:
                        alert = Alert(
                            id=alert_id,
                            metric_name=metric_name,
                            level=level,
                            message=f"{metric_name} {operator} {threshold} (atual: {current_value})",
                            value=current_value,
                            threshold=threshold,
                            timestamp=datetime.now()
                        )
                        
                        self.alerts[alert_id] = alert
                        self._trigger_callbacks(alert)
                        
                        log_warning(f"Alerta {level.value}: {alert.message}")
                
                else:
                    # Resolve alerta se existir
                    if alert_id in self.alerts and not self.alerts[alert_id].resolved:
                        self.alerts[alert_id].resolved = True
                        self.alerts[alert_id].resolved_at = datetime.now()
                        
                        log_info(f"Alerta resolvido: {metric_name}")
    
    def _trigger_callbacks(self, alert: Alert):
        """Dispara callbacks para alerta"""
        try:
            for callback in self.callbacks[alert.level]:
                try:
                    callback(alert)
                except Exception as e:
                    log_error(f"Erro em callback de alerta: {e}")
        except Exception as e:
            log_error(f"Erro ao disparar callbacks: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Retorna alertas ativos"""
        with self.lock:
            return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_all_alerts(self) -> List[Alert]:
        """Retorna todos os alertas"""
        with self.lock:
            return list(self.alerts.values())
    
    def clear_alerts(self):
        """Limpa alertas"""
        with self.lock:
            self.alerts.clear()

class PerformanceMonitor:
    """Monitor principal de performance"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Componentes
        self.collector = MetricCollector(
            max_history=self.config.get('max_history', 1000)
        )
        self.system_monitor = SystemMonitor(self.collector)
        self.alert_manager = AlertManager(self.collector)
        
        # Configurações
        self.collection_interval = self.config.get('collection_interval', 5)  # segundos
        self.alert_check_interval = self.config.get('alert_check_interval', 10)  # segundos
        
        # Threads
        self.running = True
        self.collection_thread = None
        self.alert_thread = None
        
        # Banco de dados para persistência
        self.db_path = self.config.get('db_path', 'performance.db')
        self._init_db()
        
        # Configurações padrão de alertas
        self._setup_default_alerts()
        
        log_info("Monitor de performance inicializado")
    
    def _init_db(self):
        """Inicializa banco de dados"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        value REAL NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        tags TEXT,
                        unit TEXT,
                        description TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id TEXT PRIMARY KEY,
                        metric_name TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        value REAL NOT NULL,
                        threshold REAL NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolved_at TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp 
                    ON metrics(name, timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                    ON alerts(timestamp)
                """)
        except Exception as e:
            log_error(f"Erro ao inicializar banco de dados: {e}")
    
    def _setup_default_alerts(self):
        """Configura alertas padrão"""
        try:
            # CPU
            self.alert_manager.set_threshold(
                'system.cpu.percent', 80, AlertLevel.WARNING
            )
            self.alert_manager.set_threshold(
                'system.cpu.percent', 95, AlertLevel.CRITICAL
            )
            
            # Memória
            self.alert_manager.set_threshold(
                'system.memory.percent', 85, AlertLevel.WARNING
            )
            self.alert_manager.set_threshold(
                'system.memory.percent', 95, AlertLevel.CRITICAL
            )
            
            # Disco
            self.alert_manager.set_threshold(
                'system.disk.percent', 90, AlertLevel.WARNING
            )
            self.alert_manager.set_threshold(
                'system.disk.percent', 95, AlertLevel.CRITICAL
            )
            
            # Espaço livre em disco
            self.alert_manager.set_threshold(
                'system.disk.free_gb', 1, AlertLevel.CRITICAL, "<"
            )
            
        except Exception as e:
            log_error(f"Erro ao configurar alertas padrão: {e}")
    
    def start(self):
        """Inicia monitoramento"""
        try:
            if self.collection_thread and self.collection_thread.is_alive():
                return
            
            self.running = True
            
            # Thread de coleta
            self.collection_thread = threading.Thread(
                target=self._collection_worker, daemon=True
            )
            self.collection_thread.start()
            
            # Thread de alertas
            self.alert_thread = threading.Thread(
                target=self._alert_worker, daemon=True
            )
            self.alert_thread.start()
            
            log_info("Monitoramento de performance iniciado")
            
        except Exception as e:
            log_error(f"Erro ao iniciar monitoramento: {e}")
    
    def stop(self):
        """Para monitoramento"""
        try:
            self.running = False
            
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=5)
            
            if self.alert_thread and self.alert_thread.is_alive():
                self.alert_thread.join(timeout=5)
            
            log_info("Monitoramento de performance parado")
            
        except Exception as e:
            log_error(f"Erro ao parar monitoramento: {e}")
    
    def _collection_worker(self):
        """Worker de coleta de métricas"""
        while self.running:
            try:
                # Coleta métricas do sistema
                snapshot = self.system_monitor.collect_system_metrics()
                if snapshot:
                    self._save_snapshot(snapshot)
                
                # Coleta métricas do processo
                self.system_monitor.collect_process_metrics()
                
                # Persiste métricas
                self._persist_metrics()
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                log_error(f"Erro no worker de coleta: {e}")
                time.sleep(self.collection_interval)
    
    def _alert_worker(self):
        """Worker de verificação de alertas"""
        while self.running:
            try:
                self.alert_manager.check_thresholds()
                time.sleep(self.alert_check_interval)
                
            except Exception as e:
                log_error(f"Erro no worker de alertas: {e}")
                time.sleep(self.alert_check_interval)
    
    def _save_snapshot(self, snapshot: PerformanceSnapshot):
        """Salva snapshot no banco"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO metrics 
                    (name, type, value, timestamp, unit, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    'system.snapshot',
                    'custom',
                    0,  # valor dummy
                    snapshot.timestamp.isoformat(),
                    'snapshot',
                    json.dumps(asdict(snapshot), default=str)
                ))
        except Exception as e:
            log_error(f"Erro ao salvar snapshot: {e}")
    
    def _persist_metrics(self):
        """Persiste métricas no banco"""
        try:
            metrics_to_save = []
            
            for name, metric_list in self.collector.get_metrics().items():
                # Salva apenas métricas recentes
                recent_metrics = [
                    m for m in metric_list 
                    if (datetime.now() - m.timestamp).total_seconds() < 60
                ]
                
                for metric in recent_metrics:
                    metrics_to_save.append((
                        metric.name,
                        metric.type.value,
                        metric.value,
                        metric.timestamp.isoformat(),
                        json.dumps(metric.tags),
                        metric.unit,
                        metric.description
                    ))
            
            if metrics_to_save:
                with sqlite3.connect(self.db_path) as conn:
                    conn.executemany("""
                        INSERT INTO metrics 
                        (name, type, value, timestamp, tags, unit, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, metrics_to_save)
                    
        except Exception as e:
            log_error(f"Erro ao persistir métricas: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Retorna resumo das métricas"""
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'system': {},
                'process': {},
                'alerts': {
                    'active': len(self.alert_manager.get_active_alerts()),
                    'total': len(self.alert_manager.get_all_alerts())
                }
            }
            
            # Métricas do sistema
            system_metrics = [
                'system.cpu.percent',
                'system.memory.percent',
                'system.disk.percent',
                'system.network.connections'
            ]
            
            for metric in system_metrics:
                value = self.collector.get_latest_value(metric)
                if value is not None:
                    key = metric.replace('system.', '').replace('.', '_')
                    summary['system'][key] = round(value, 2)
            
            # Métricas do processo
            process_metrics = [
                'process.cpu.percent',
                'process.memory.rss_mb',
                'process.thread.count',
                'process.uptime.seconds'
            ]
            
            for metric in process_metrics:
                value = self.collector.get_latest_value(metric)
                if value is not None:
                    key = metric.replace('process.', '').replace('.', '_')
                    summary['process'][key] = round(value, 2)
            
            return summary
            
        except Exception as e:
            log_error(f"Erro ao gerar resumo: {e}")
            return {'error': str(e)}
    
    def get_historical_data(self, metric_name: str, 
                           hours: int = 24) -> List[Dict[str, Any]]:
        """Retorna dados históricos de uma métrica"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM metrics 
                    WHERE name = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                """, (metric_name, since.isoformat()))
                
                return [
                    {
                        'timestamp': row['timestamp'],
                        'value': row['value'],
                        'tags': json.loads(row['tags']) if row['tags'] else {}
                    }
                    for row in cursor.fetchall()
                ]
                
        except Exception as e:
            log_error(f"Erro ao obter dados históricos: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 7):
        """Remove dados antigos"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM metrics WHERE timestamp < ?",
                    (cutoff.isoformat(),)
                )
                
                deleted_metrics = cursor.rowcount
                
                cursor = conn.execute(
                    "DELETE FROM alerts WHERE timestamp < ? AND resolved = TRUE",
                    (cutoff.isoformat(),)
                )
                
                deleted_alerts = cursor.rowcount
                
                log_info(f"Limpeza: {deleted_metrics} métricas e {deleted_alerts} alertas removidos")
                
        except Exception as e:
            log_error(f"Erro na limpeza de dados: {e}")
    
    def export_metrics(self, filename: str, hours: int = 24):
        """Exporta métricas para arquivo JSON"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM metrics 
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (since.isoformat(),))
                
                metrics = [
                    {
                        'name': row['name'],
                        'type': row['type'],
                        'value': row['value'],
                        'timestamp': row['timestamp'],
                        'tags': json.loads(row['tags']) if row['tags'] else {},
                        'unit': row['unit'],
                        'description': row['description']
                    }
                    for row in cursor.fetchall()
                ]
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        'export_timestamp': datetime.now().isoformat(),
                        'period_hours': hours,
                        'metrics_count': len(metrics),
                        'metrics': metrics
                    }, f, indent=2, ensure_ascii=False)
                
                log_info(f"Métricas exportadas para {filename}")
                
        except Exception as e:
            log_error(f"Erro ao exportar métricas: {e}")
    
    def __del__(self):
        """Destrutor"""
        self.stop()

# Decorador para monitoramento de funções
def monitor_performance(metric_name: str = None, tags: Dict[str, str] = None):
    """Decorator para monitorar performance de funções"""
    def decorator(func: Callable) -> Callable:
        name = metric_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            
            start_time = time.time()
            
            try:
                # Conta execução
                monitor.collector.record_counter(f"{name}.calls", tags=tags)
                
                # Executa função
                result = func(*args, **kwargs)
                
                # Registra sucesso
                monitor.collector.record_counter(f"{name}.success", tags=tags)
                
                return result
                
            except Exception as e:
                # Registra erro
                monitor.collector.record_counter(f"{name}.errors", tags=tags)
                raise
                
            finally:
                # Registra tempo de execução
                duration = (time.time() - start_time) * 1000  # ms
                monitor.collector.record_timer(f"{name}.duration", duration, tags=tags)
        
        return wrapper
    return decorator

# Instância global
_global_monitor = None

def get_monitor(config: Dict[str, Any] = None) -> PerformanceMonitor:
    """Retorna instância global do monitor"""
    global _global_monitor
    
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor(config)
    
    return _global_monitor

def start_monitoring(config: Dict[str, Any] = None):
    """Inicia monitoramento global"""
    monitor = get_monitor(config)
    monitor.start()
    return monitor

def stop_monitoring():
    """Para monitoramento global"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop()