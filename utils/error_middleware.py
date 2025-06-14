import traceback
import json
from typing import Dict, Any, Optional
from datetime import datetime
from dash import html
import dash_bootstrap_components as dbc
from utils.logger import log_error, log_warning, log_info
from pydantic import ValidationError

class ErrorMiddleware:
    """
    Middleware para tratamento centralizado de erros na aplicação Dash
    """
    
    def __init__(self, app):
        self.app = app
        self.setup_error_handlers()
    
    def setup_error_handlers(self):
        """Configura handlers de erro para o Flask subjacente"""
        
        @self.app.server.errorhandler(400)
        def handle_bad_request(e):
            log_warning("Bad Request", extra={"error": str(e)})
            return self._create_error_response("Requisição inválida", 400)
        
        @self.app.server.errorhandler(401)
        def handle_unauthorized(e):
            log_warning("Unauthorized access", extra={"error": str(e)})
            return self._create_error_response("Acesso não autorizado", 401)
        
        @self.app.server.errorhandler(403)
        def handle_forbidden(e):
            log_warning("Forbidden access", extra={"error": str(e)})
            return self._create_error_response("Acesso proibido", 403)
        
        @self.app.server.errorhandler(404)
        def handle_not_found(e):
            log_warning("Resource not found", extra={"error": str(e)})
            return self._create_error_response("Recurso não encontrado", 404)
        
        @self.app.server.errorhandler(500)
        def handle_internal_error(e):
            log_error("Internal server error", exc_info=True)
            return self._create_error_response("Erro interno do servidor", 500)
        
        @self.app.server.errorhandler(ValidationError)
        def handle_validation_error(e):
            log_warning("Validation error", extra={"errors": e.errors()})
            return self._create_validation_error_response(e)
    
    def _create_error_response(self, message: str, status_code: int) -> tuple:
        """Cria resposta de erro padronizada"""
        return {
            "error": {
                "message": message,
                "status_code": status_code,
                "timestamp": datetime.now().isoformat()
            }
        }, status_code
    
    def _create_validation_error_response(self, validation_error: ValidationError) -> tuple:
        """Cria resposta específica para erros de validação"""
        errors = []
        for error in validation_error.errors():
            field = '.'.join(str(loc) for loc in error['loc'])
            errors.append({
                "field": field,
                "message": error['msg'],
                "type": error['type']
            })
        
        return {
            "error": {
                "message": "Dados de entrada inválidos",
                "status_code": 422,
                "timestamp": datetime.now().isoformat(),
                "validation_errors": errors
            }
        }, 422

class DashErrorHandler:
    """
    Handler específico para erros em callbacks do Dash
    """
    
    @staticmethod
    def handle_callback_error(func):
        """Decorator para tratar erros em callbacks"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                log_warning(f"Validation error in callback {func.__name__}", extra={"errors": e.errors()})
                return DashErrorHandler.create_validation_error_component(e)
            except Exception as e:
                log_error(f"Error in callback {func.__name__}", exc_info=True)
                return DashErrorHandler.create_generic_error_component(str(e))
        return wrapper
    
    @staticmethod
    def create_validation_error_component(validation_error: ValidationError):
        """Cria componente Dash para exibir erros de validação"""
        error_items = []
        for error in validation_error.errors():
            field = '.'.join(str(loc) for loc in error['loc'])
            error_items.append(
                html.Li(f"{field}: {error['msg']}", className="text-danger")
            )
        
        return dbc.Alert([
            html.H5("Dados inválidos", className="alert-heading"),
            html.P("Por favor, corrija os seguintes erros:"),
            html.Ul(error_items)
        ], color="danger", dismissable=True)
    
    @staticmethod
    def create_generic_error_component(error_message: str):
        """Cria componente Dash para exibir erros genéricos"""
        return dbc.Alert([
            html.H5("Erro", className="alert-heading"),
            html.P(f"Ocorreu um erro: {error_message}"),
            html.Hr(),
            html.P("Se o problema persistir, entre em contato com o suporte.", className="mb-0")
        ], color="danger", dismissable=True)
    
    @staticmethod
    def create_loading_error_component():
        """Cria componente para erros de carregamento"""
        return dbc.Alert([
            html.H5("Erro de Carregamento", className="alert-heading"),
            html.P("Não foi possível carregar os dados. Tente novamente."),
        ], color="warning", dismissable=True)
    
    @staticmethod
    def create_connection_error_component():
        """Cria componente para erros de conexão"""
        return dbc.Alert([
            html.H5("Erro de Conexão", className="alert-heading"),
            html.P("Não foi possível conectar ao banco de dados. Verifique as configurações."),
        ], color="danger", dismissable=True)

class ErrorBoundary:
    """
    Boundary para capturar erros em componentes específicos
    """
    
    @staticmethod
    def wrap_component(component, error_fallback=None):
        """Envolve um componente com tratamento de erro"""
        try:
            return component
        except Exception as e:
            log_error("Error in component", exc_info=True)
            if error_fallback:
                return error_fallback
            return DashErrorHandler.create_generic_error_component(str(e))

def safe_callback(func):
    """
    Decorator para tornar callbacks seguros contra erros
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            log_warning(f"Validation error in {func.__name__}", extra={"errors": e.errors()})
            return DashErrorHandler.create_validation_error_component(e)
        except ConnectionError as e:
            log_error(f"Connection error in {func.__name__}", extra={"error": str(e)})
            return DashErrorHandler.create_connection_error_component()
        except Exception as e:
            log_error(f"Unexpected error in {func.__name__}", exc_info=True)
            return DashErrorHandler.create_generic_error_component("Erro inesperado. Tente novamente.")
    return wrapper

def log_performance(func):
    """
    Decorator para monitorar performance de callbacks
    """
    import time
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 2.0:  # Log se demorar mais que 2 segundos
                log_warning(f"Slow callback execution: {func.__name__}", extra={
                    "execution_time": execution_time,
                    "function": func.__name__
                })
            else:
                log_info(f"Callback executed: {func.__name__}", extra={
                    "execution_time": execution_time
                })
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            log_error(f"Callback failed: {func.__name__}", extra={
                "execution_time": execution_time,
                "error": str(e)
            }, exc_info=True)
            raise
    
    return wrapper