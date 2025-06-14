from typing import Dict, Any, Callable, TypeVar, Type, Optional
from abc import ABC, abstractmethod
import inspect
from utils.logger import log_info, log_error, log_debug

T = TypeVar('T')

class DIContainer:
    """
    Container de Dependency Injection para gerenciar dependências da aplicação
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._interfaces: Dict[Type, str] = {}
        
    def register_singleton(self, interface: Type[T], implementation: T, name: Optional[str] = None) -> 'DIContainer':
        """
        Registra um serviço como singleton
        """
        service_name = name or interface.__name__
        self._singletons[service_name] = implementation
        self._interfaces[interface] = service_name
        log_debug(f"Singleton registrado: {service_name}")
        return self
    
    def register_transient(self, interface: Type[T], factory: Callable[[], T], name: Optional[str] = None) -> 'DIContainer':
        """
        Registra um serviço como transient (nova instância a cada chamada)
        """
        service_name = name or interface.__name__
        self._factories[service_name] = factory
        self._interfaces[interface] = service_name
        log_debug(f"Transient registrado: {service_name}")
        return self
    
    def register_instance(self, interface: Type[T], instance: T, name: Optional[str] = None) -> 'DIContainer':
        """
        Registra uma instância específica
        """
        service_name = name or interface.__name__
        self._services[service_name] = instance
        self._interfaces[interface] = service_name
        log_debug(f"Instância registrada: {service_name}")
        return self
    
    def get(self, interface: Type[T], name: Optional[str] = None) -> T:
        """
        Obtém uma instância do serviço
        """
        service_name = name or self._interfaces.get(interface) or interface.__name__
        
        # Verifica singletons primeiro
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # Verifica instâncias registradas
        if service_name in self._services:
            return self._services[service_name]
        
        # Verifica factories
        if service_name in self._factories:
            return self._factories[service_name]()
        
        # Tenta criar automaticamente se for uma classe
        if inspect.isclass(interface):
            try:
                instance = self._auto_wire(interface)
                log_debug(f"Instância criada automaticamente: {service_name}")
                return instance
            except Exception as e:
                log_error(f"Erro ao criar instância automaticamente: {service_name}", extra={"error": str(e)})
        
        raise ValueError(f"Serviço não encontrado: {service_name}")
    
    def _auto_wire(self, cls: Type[T]) -> T:
        """
        Cria uma instância automaticamente resolvendo dependências
        """
        signature = inspect.signature(cls.__init__)
        kwargs = {}
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
                
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = self.get(param.annotation)
                except ValueError:
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        raise ValueError(f"Não foi possível resolver dependência: {param_name} ({param.annotation})")
        
        return cls(**kwargs)
    
    def has(self, interface: Type, name: Optional[str] = None) -> bool:
        """
        Verifica se um serviço está registrado
        """
        service_name = name or self._interfaces.get(interface) or interface.__name__
        return (service_name in self._singletons or 
                service_name in self._services or 
                service_name in self._factories)
    
    def clear(self):
        """
        Limpa todos os serviços registrados
        """
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        self._interfaces.clear()
        log_info("Container DI limpo")

# Interfaces para os principais serviços
class IConfigManager(ABC):
    @abstractmethod
    def load_connections(self, decrypt_passwords: bool = True) -> Dict:
        pass
    
    @abstractmethod
    def save_connection(self, name: str, connection_data: Dict) -> bool:
        pass

class IDatabaseManager(ABC):
    @abstractmethod
    def connect(self, connection_string: str) -> bool:
        pass
    
    @abstractmethod
    def execute_query(self, query: str) -> Any:
        pass

class IQueryManager(ABC):
    @abstractmethod
    def save_query(self, name: str, query: str, description: str = "") -> bool:
        pass
    
    @abstractmethod
    def load_queries(self) -> Dict:
        pass

class ICacheManager(ABC):
    @abstractmethod
    def get(self, key: str) -> Any:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        pass

# Container global da aplicação
app_container = DIContainer()

def setup_dependencies():
    """
    Configura as dependências principais da aplicação
    """
    try:
        # Importações locais para evitar dependências circulares
        from utils.config_manager import ConfigManager
        from utils.database_manager import DatabaseManager
        from utils.query_manager import QueryManager
        from utils.sqlite_cache import SQLiteCache
        from utils.security_config import security_config
        
        # Registrar singletons
        app_container.register_singleton(IConfigManager, ConfigManager())
        app_container.register_singleton(IDatabaseManager, DatabaseManager())
        app_container.register_singleton(IQueryManager, QueryManager())
        cache_config = {'CACHE_DEFAULT_TIMEOUT': 300, 'CACHE_SQLITE_PATH': None}
        app_container.register_singleton(ICacheManager, SQLiteCache(cache_config))
        
        # Registrar configuração de segurança
        app_container.register_instance(type(security_config), security_config, "security_config")
        
        log_info("Dependências configuradas com sucesso")
        
    except Exception as e:
        log_error("Erro ao configurar dependências", exception=e, extra={"error": str(e)})
        raise

def get_service(interface: Type[T], name: Optional[str] = None) -> T:
    """
    Função helper para obter serviços do container
    """
    return app_container.get(interface, name)

def inject(interface: Type[T], name: Optional[str] = None):
    """
    Decorator para injeção de dependência em funções
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            service = get_service(interface, name)
            return func(service, *args, **kwargs)
        return wrapper
    return decorator

class ServiceLocator:
    """
    Service Locator pattern como alternativa ao DI
    """
    
    @staticmethod
    def get_config_manager() -> IConfigManager:
        return get_service(IConfigManager)
    
    @staticmethod
    def get_database_manager() -> IDatabaseManager:
        return get_service(IDatabaseManager)
    
    @staticmethod
    def get_query_manager() -> IQueryManager:
        return get_service(IQueryManager)
    
    @staticmethod
    def get_cache_manager() -> ICacheManager:
        return get_service(ICacheManager)
    
    @staticmethod
    def get_security_config():
        return get_service(type(app_container._services.get("security_config")), "security_config")