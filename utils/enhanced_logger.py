import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import json
from pathlib import Path

class ColoredFormatter(logging.Formatter):
    """
    Formatter colorido para logs no console
    """
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """
    Formatter JSON para logs estruturados
    """
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Adicionar informações extras se disponíveis
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'extra'):
            log_entry['extra'] = record.extra
        
        # Adicionar informações de exceção se disponíveis
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class EnhancedLogger:
    """
    Sistema de logging melhorado com rotação automática e múltiplos handlers
    """
    
    def __init__(self, name: str = 'BI-Dashboard', log_dir: str = 'logs'):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Criar logger principal
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """
        Configura os handlers de logging
        """
        # Handler para console com cores
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Handler para arquivo geral com rotação
        general_file = self.log_dir / 'application.log'
        file_handler = logging.handlers.RotatingFileHandler(
            general_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Handler para erros com rotação
        error_file = self.log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)
        
        # Handler para logs JSON estruturados
        json_file = self.log_dir / 'structured.jsonl'
        json_handler = logging.handlers.RotatingFileHandler(
            json_file,
            maxBytes=20*1024*1024,  # 20MB
            backupCount=3,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(json_handler)
        
        # Handler para logs de performance
        perf_file = self.log_dir / 'performance.log'
        perf_handler = logging.handlers.TimedRotatingFileHandler(
            perf_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(file_formatter)
        
        # Criar logger específico para performance
        self.perf_logger = logging.getLogger(f'{self.name}.performance')
        self.perf_logger.setLevel(logging.INFO)
        self.perf_logger.addHandler(perf_handler)
        self.perf_logger.propagate = False
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, extra, **kwargs)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, extra, **kwargs)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, extra, **kwargs)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, extra, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info, **kwargs)
    
    def performance(self, operation: str, duration: float, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Log performance metrics"""
        perf_data = {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'timestamp': datetime.now().isoformat()
        }
        if extra:
            perf_data.update(extra)
        
        message = f"PERFORMANCE: {operation} took {perf_data['duration_ms']}ms"
        self.perf_logger.info(message, extra=perf_data, **kwargs)
    
    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Internal logging method"""
        if extra:
            # Criar um LogRecord customizado com informações extras
            record = self.logger.makeRecord(
                self.logger.name, level, '', 0, message, (), None, **kwargs
            )
            record.extra = extra
            self.logger.handle(record)
        else:
            self.logger.log(level, message, **kwargs)
    
    def log_request(self, method: str, path: str, status_code: int, duration: float, 
                   user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Log HTTP request"""
        extra = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration_ms': round(duration * 1000, 2)
        }
        
        if user_id:
            extra['user_id'] = user_id
        if session_id:
            extra['session_id'] = session_id
        
        message = f"{method} {path} - {status_code} ({extra['duration_ms']}ms)"
        self.info(message, extra=extra)
    
    def log_database_query(self, query: str, duration: float, rows_affected: int = 0, 
                          connection_name: str = None):
        """Log database query"""
        extra = {
            'query_type': 'database',
            'duration_ms': round(duration * 1000, 2),
            'rows_affected': rows_affected,
            'query_preview': query[:100] + '...' if len(query) > 100 else query
        }
        
        if connection_name:
            extra['connection'] = connection_name
        
        message = f"DB Query executed in {extra['duration_ms']}ms, {rows_affected} rows affected"
        self.info(message, extra=extra)
    
    def log_cache_operation(self, operation: str, key: str, hit: bool = None, duration: float = None):
        """Log cache operation"""
        extra = {
            'cache_operation': operation,
            'cache_key': key
        }
        
        if hit is not None:
            extra['cache_hit'] = hit
        if duration is not None:
            extra['duration_ms'] = round(duration * 1000, 2)
        
        message = f"Cache {operation}: {key}"
        if hit is not None:
            message += f" ({'HIT' if hit else 'MISS'})"
        
        self.debug(message, extra=extra)
    
    def log_user_action(self, user_id: str, action: str, resource: str = None, 
                       session_id: str = None, ip_address: str = None):
        """Log user action for audit"""
        extra = {
            'user_id': user_id,
            'action': action,
            'audit': True
        }
        
        if resource:
            extra['resource'] = resource
        if session_id:
            extra['session_id'] = session_id
        if ip_address:
            extra['ip_address'] = ip_address
        
        message = f"User {user_id} performed {action}"
        if resource:
            message += f" on {resource}"
        
        self.info(message, extra=extra)
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """Get the underlying logger instance"""
        if name:
            return logging.getLogger(f'{self.name}.{name}')
        return self.logger

# Instância global do logger
enhanced_logger = EnhancedLogger()

# Funções de conveniência para compatibilidade com o logger existente
def log_info(message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
    enhanced_logger.info(message, extra=extra, **kwargs)

def log_error(message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False, **kwargs):
    enhanced_logger.error(message, extra=extra, exc_info=exc_info, **kwargs)

def log_debug(message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
    enhanced_logger.debug(message, extra=extra, **kwargs)

def log_warning(message: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
    enhanced_logger.warning(message, extra=extra, **kwargs)

def log_performance(operation: str, duration: float, extra: Optional[Dict[str, Any]] = None, **kwargs):
    enhanced_logger.performance(operation, duration, extra=extra, **kwargs)

def log_request(method: str, path: str, status_code: int, duration: float, 
               user_id: Optional[str] = None, session_id: Optional[str] = None):
    enhanced_logger.log_request(method, path, status_code, duration, user_id, session_id)

def log_database_query(query: str, duration: float, rows_affected: int = 0, 
                      connection_name: str = None):
    enhanced_logger.log_database_query(query, duration, rows_affected, connection_name)

def log_cache_operation(operation: str, key: str, hit: bool = None, duration: float = None):
    enhanced_logger.log_cache_operation(operation, key, hit, duration)

def log_user_action(user_id: str, action: str, resource: str = None, 
                   session_id: str = None, ip_address: str = None):
    enhanced_logger.log_user_action(user_id, action, resource, session_id, ip_address)