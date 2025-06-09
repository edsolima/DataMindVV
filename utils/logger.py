"""
Módulo de logging estruturado para a aplicação BI.

Exemplo de uso:
    from utils.logger import log_info, log_error
    log_info("Mensagem informativa")
    log_error("Mensagem de erro", exception=Exception("Erro!"))

Utilize as funções de conveniência para logs padronizados em toda a aplicação.
"""

import logging
import os
from datetime import datetime
from typing import Optional
import sys

class StructuredLogger:
    """
    Sistema de logging estruturado para a aplicação BI.
    Substitui print statements por logging robusto com diferentes níveis.
    Oferece métodos para logs de operação, performance, banco de dados, ações de usuário e processamento de dados.
    """
    
    def __init__(self, name: str = "BI_APP", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura os handlers de logging para console e arquivos."""
        # Formatter estruturado
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Handler para arquivo
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Handler para erros críticos
        error_handler = logging.FileHandler(
            os.path.join(log_dir, "errors.log"),
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def info(self, message: str, extra: Optional[dict] = None):
        """Log de informação."""
        self.logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[dict] = None):
        """Log de aviso."""
        self.logger.warning(message, extra=extra or {})
    
    def error(self, message: str, exception: Optional[Exception] = None, extra: Optional[dict] = None):
        """Log de erro. Se exception for fornecida, inclui traceback."""
        if exception:
            self.logger.error(f"{message} | Exception: {str(exception)}", exc_info=True, extra=extra or {})
        else:
            self.logger.error(message, extra=extra or {})
    
    def debug(self, message: str, extra: Optional[dict] = None):
        """Log de debug."""
        self.logger.debug(message, extra=extra or {})
    
    def critical(self, message: str, exception: Optional[Exception] = None, extra: Optional[dict] = None):
        """Log crítico. Se exception for fornecida, inclui traceback."""
        if exception:
            self.logger.critical(f"{message} | Exception: {str(exception)}", exc_info=True, extra=extra or {})
        else:
            self.logger.critical(message, extra=extra or {})
    
    def log_operation(self, operation: str, details: dict = None, level: str = "INFO"):
        """Log estruturado para operações específicas."""
        details = details or {}
        message = f"Operation: {operation}"
        if details:
            message += f" | Details: {details}"
        
        getattr(self.logger, level.lower())(message)
    
    def log_performance(self, operation: str, duration: float, details: dict = None):
        """Log de performance para operações."""
        details = details or {}
        message = f"Performance: {operation} | Duration: {duration:.4f}s"
        if details:
            message += f" | Details: {details}"
        
        self.logger.info(message)
    
    def log_database_operation(self, operation: str, query: str = None, duration: float = None, 
                              rows_affected: int = None, error: Exception = None):
        """Log específico para operações de banco de dados."""
        details = {
            "operation": operation,
            "query": query[:100] + "..." if query and len(query) > 100 else query,
            "duration": f"{duration:.4f}s" if duration else None,
            "rows_affected": rows_affected
        }
        
        # Remove valores None
        details = {k: v for k, v in details.items() if v is not None}
        
        if error:
            self.error(f"Database operation failed: {operation}", exception=error, extra=details)
        else:
            self.info(f"Database operation successful: {operation}", extra=details)
    
    def log_user_action(self, user_id: str, action: str, details: dict = None):
        """Log de ações do usuário."""
        details = details or {}
        details.update({"user_id": user_id, "action": action})
        self.info(f"User action: {action}", extra=details)
    
    def log_data_processing(self, operation: str, input_shape: tuple = None, 
                           output_shape: tuple = None, duration: float = None, error: Exception = None):
        """Log específico para processamento de dados."""
        details = {
            "operation": operation,
            "input_shape": input_shape,
            "output_shape": output_shape,
            "duration": f"{duration:.4f}s" if duration else None
        }
        
        # Remove valores None
        details = {k: v for k, v in details.items() if v is not None}
        
        if error:
            self.error(f"Data processing failed: {operation}", exception=error, extra=details)
        else:
            self.info(f"Data processing successful: {operation}", extra=details)

# Instância global do logger
app_logger = StructuredLogger()

# Funções de conveniência para uso direto
def log_info(message: str, extra: dict = None):
    """Função de conveniência para log de informação."""
    app_logger.info(message, extra)

def log_warning(message: str, extra: dict = None):
    """Função de conveniência para log de aviso."""
    app_logger.warning(message, extra)

def log_error(message: str, exception: Exception = None, extra: dict = None):
    """Função de conveniência para log de erro."""
    app_logger.error(message, exception, extra)

def log_debug(message: str, extra: dict = None):
    """Função de conveniência para log de debug."""
    app_logger.debug(message, extra)

def log_critical(message: str, exception: Exception = None, extra: dict = None):
    """Função de conveniência para log crítico."""
    app_logger.critical(message, exception, extra)

def log_operation(operation: str, details: dict = None, level: str = "INFO"):
    """Função de conveniência para log de operação."""
    app_logger.log_operation(operation, details, level)

def log_performance(operation: str, duration: float, details: dict = None):
    """Função de conveniência para log de performance."""
    app_logger.log_performance(operation, duration, details)

def log_database_operation(operation: str, query: str = None, duration: float = None, 
                          rows_affected: int = None, error: Exception = None):
    """Função de conveniência para log de operação de banco."""
    app_logger.log_database_operation(operation, query, duration, rows_affected, error)

def log_user_action(user_id: str, action: str, details: dict = None):
    """Função de conveniência para log de ação do usuário."""
    app_logger.log_user_action(user_id, action, details)

def log_data_processing(operation: str, input_shape: tuple = None, 
                       output_shape: tuple = None, duration: float = None, error: Exception = None):
    """Função de conveniência para log de processamento de dados."""
    app_logger.log_data_processing(operation, input_shape, output_shape, duration, error)