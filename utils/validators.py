from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
import re
from enum import Enum

class DatabaseType(str, Enum):
    """Tipos de banco de dados suportados"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"

class DatabaseConnectionModel(BaseModel):
    """Modelo de validação para conexões de banco de dados"""
    type: DatabaseType
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., gt=0, le=65535)
    database: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    schema: Optional[str] = Field(None, max_length=255)
    driver: Optional[str] = Field(None, max_length=255)
    trust_server_certificate: Optional[bool] = False
    windows_auth: Optional[bool] = False
    
    @validator('host')
    def validate_host(cls, v):
        # Para SQLite, host é o caminho do arquivo
        if not v or len(v.strip()) == 0:
            raise ValueError('Host não pode estar vazio')
        return v.strip()
    
    @validator('database')
    def validate_database(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Nome do banco de dados não pode estar vazio')
        # Validar caracteres permitidos
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Nome do banco contém caracteres inválidos')
        return v.strip()
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Username não pode estar vazio')
        return v.strip()

class QueryModel(BaseModel):
    """Modelo de validação para queries SQL"""
    query: str = Field(..., min_length=1, max_length=10000)
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Query não pode estar vazia')
        
        # Verificar comandos perigosos
        dangerous_commands = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE'
        ]
        
        query_upper = v.upper()
        for cmd in dangerous_commands:
            if cmd in query_upper:
                raise ValueError(f'Comando {cmd} não é permitido')
        
        return v.strip()

class ChartConfigModel(BaseModel):
    """Modelo de validação para configuração de gráficos"""
    chart_type: str = Field(..., min_length=1)
    x_column: str = Field(..., min_length=1)
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    title: Optional[str] = Field(None, max_length=255)
    
    @validator('chart_type')
    def validate_chart_type(cls, v):
        allowed_types = [
            'bar', 'line', 'scatter', 'pie', 'histogram', 
            'boxplot', 'heatmap', 'area', 'violin'
        ]
        if v.lower() not in allowed_types:
            raise ValueError(f'Tipo de gráfico deve ser um de: {allowed_types}')
        return v.lower()

class FileUploadModel(BaseModel):
    """Modelo de validação para upload de arquivos"""
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)
    content_type: str = Field(..., min_length=1)
    
    @validator('filename')
    def validate_filename(cls, v):
        # Verificar extensões permitidas
        allowed_extensions = ['.csv', '.xlsx', '.xls', '.json']
        if not any(v.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError(f'Extensão de arquivo deve ser uma de: {allowed_extensions}')
        
        # Verificar caracteres perigosos
        if any(char in v for char in ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']):
            raise ValueError('Nome do arquivo contém caracteres inválidos')
        
        return v
    
    @validator('file_size')
    def validate_file_size(cls, v):
        max_size = 100 * 1024 * 1024  # 100MB
        if v > max_size:
            raise ValueError(f'Arquivo muito grande. Máximo permitido: {max_size} bytes')
        return v
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'text/csv', 'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/json'
        ]
        if v not in allowed_types:
            raise ValueError(f'Tipo de conteúdo deve ser um de: {allowed_types}')
        return v

class UserInputModel(BaseModel):
    """Modelo de validação para entrada de usuário genérica"""
    text: str = Field(..., min_length=1, max_length=5000)
    
    @validator('text')
    def validate_text(cls, v):
        # Remover scripts maliciosos
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>.*?</iframe>'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE | re.DOTALL):
                raise ValueError('Conteúdo contém código potencialmente perigoso')
        
        return v.strip()

class DashboardConfigModel(BaseModel):
    """Modelo de validação para configuração de dashboard"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    layout: Dict[str, Any] = Field(...)
    components: List[Dict[str, Any]] = Field(default_factory=list)
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s_-]+$', v):
            raise ValueError('Nome contém caracteres inválidos')
        return v.strip()
    
    @validator('layout')
    def validate_layout(cls, v):
        required_keys = ['lg', 'md', 'sm', 'xs', 'xxs']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'Layout deve conter a chave: {key}')
        return v

def validate_sql_injection(query: str) -> bool:
    """
    Validação adicional para prevenir SQL injection
    """
    # Padrões suspeitos de SQL injection
    suspicious_patterns = [
        r"('|(\-\-)|(;)|(\||\|)|(\*|\*))",
        r"(union|select|insert|delete|update|drop|create|alter|exec|execute)",
        r"(script|javascript|vbscript|onload|onerror|onclick)"
    ]
    
    query_lower = query.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, query_lower):
            return False
    
    return True

def sanitize_input(text: str) -> str:
    """
    Sanitiza entrada de texto removendo caracteres perigosos
    """
    # Remove tags HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove caracteres de controle
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()