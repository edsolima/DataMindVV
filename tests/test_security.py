import pytest
import os
from unittest.mock import patch, Mock
from utils.security_config import SecurityConfig
from utils.validators import (
    DatabaseConnectionValidator, SQLQueryValidator, ChartConfigValidator,
    FileUploadValidator, UserInputValidator, DashboardConfigValidator,
    validate_sql_injection, sanitize_input
)
from pydantic import ValidationError

class TestSecurityConfig:
    """Testes para configuração de segurança"""
    
    def test_jwt_secret_from_env(self):
        """Testa carregamento do JWT secret do ambiente"""
        with patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-secret-123'}):
            config = SecurityConfig()
            assert config.get_jwt_secret() == 'test-secret-123'
    
    def test_jwt_secret_generation_when_missing(self):
        """Testa geração automática do JWT secret quando não está no ambiente"""
        with patch.dict(os.environ, {}, clear=True):
            config = SecurityConfig()
            secret = config.get_jwt_secret()
            assert len(secret) >= 32
            assert isinstance(secret, str)
    
    def test_encryption_key_from_env(self):
        """Testa carregamento da chave de criptografia do ambiente"""
        with patch.dict(os.environ, {'ENCRYPTION_KEY': 'test-encryption-key'}):
            config = SecurityConfig()
            assert config.get_encryption_key() == 'test-encryption-key'
    
    def test_encryption_key_generation_when_missing(self):
        """Testa geração automática da chave de criptografia"""
        with patch.dict(os.environ, {}, clear=True):
            config = SecurityConfig()
            key = config.get_encryption_key()
            assert len(key) >= 32
            assert isinstance(key, str)
    
    def test_is_production_detection(self):
        """Testa detecção do ambiente de produção"""
        with patch.dict(os.environ, {'APP_ENV': 'production'}):
            config = SecurityConfig()
            assert config.is_production() is True
        
        with patch.dict(os.environ, {'APP_ENV': 'development'}):
            config = SecurityConfig()
            assert config.is_production() is False
    
    @pytest.mark.security
    def test_secrets_not_logged(self, caplog):
        """Testa que secrets não são logados"""
        config = SecurityConfig()
        secret = config.get_jwt_secret()
        
        # Verifica que o secret não aparece nos logs
        for record in caplog.records:
            assert secret not in record.message

class TestDatabaseConnectionValidator:
    """Testes para validação de conexões de banco"""
    
    def test_valid_postgresql_connection(self):
        """Testa validação de conexão PostgreSQL válida"""
        data = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'user',
            'password': 'pass',
            'db_type': 'postgresql'
        }
        validator = DatabaseConnectionValidator(**data)
        assert validator.host == 'localhost'
        assert validator.port == 5432
        assert validator.db_type == 'postgresql'
    
    def test_invalid_port_range(self):
        """Testa validação de porta inválida"""
        data = {
            'host': 'localhost',
            'port': 70000,  # Porta inválida
            'database': 'test_db',
            'username': 'user',
            'password': 'pass',
            'db_type': 'postgresql'
        }
        with pytest.raises(ValidationError):
            DatabaseConnectionValidator(**data)
    
    def test_invalid_db_type(self):
        """Testa validação de tipo de banco inválido"""
        data = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'user',
            'password': 'pass',
            'db_type': 'invalid_db'  # Tipo inválido
        }
        with pytest.raises(ValidationError):
            DatabaseConnectionValidator(**data)
    
    def test_missing_required_fields(self):
        """Testa validação com campos obrigatórios faltando"""
        data = {
            'host': 'localhost',
            # port, database, username, password faltando
            'db_type': 'postgresql'
        }
        with pytest.raises(ValidationError):
            DatabaseConnectionValidator(**data)

class TestSQLQueryValidator:
    """Testes para validação de queries SQL"""
    
    def test_valid_select_query(self):
        """Testa validação de query SELECT válida"""
        data = {
            'query': 'SELECT * FROM users WHERE age > 18',
            'query_type': 'read'
        }
        validator = SQLQueryValidator(**data)
        assert validator.query_type == 'read'
    
    def test_dangerous_drop_query(self):
        """Testa detecção de query DROP perigosa"""
        data = {
            'query': 'DROP TABLE users',
            'query_type': 'write'
        }
        with pytest.raises(ValidationError) as exc_info:
            SQLQueryValidator(**data)
        assert 'comandos perigosos' in str(exc_info.value)
    
    def test_dangerous_delete_all_query(self):
        """Testa detecção de DELETE sem WHERE"""
        data = {
            'query': 'DELETE FROM users',
            'query_type': 'write'
        }
        with pytest.raises(ValidationError) as exc_info:
            SQLQueryValidator(**data)
        assert 'comandos perigosos' in str(exc_info.value)
    
    def test_sql_injection_detection(self):
        """Testa detecção de SQL injection"""
        dangerous_queries = [
            "SELECT * FROM users WHERE id = '1; DROP TABLE users; --'",
            "SELECT * FROM users WHERE name = 'admin' OR '1'='1'",
            "SELECT * FROM users; DELETE FROM users WHERE 1=1"
        ]
        
        for query in dangerous_queries:
            data = {'query': query, 'query_type': 'read'}
            with pytest.raises(ValidationError):
                SQLQueryValidator(**data)
    
    def test_query_length_limit(self):
        """Testa limite de tamanho da query"""
        long_query = 'SELECT * FROM users WHERE ' + 'x' * 10000
        data = {
            'query': long_query,
            'query_type': 'read'
        }
        with pytest.raises(ValidationError):
            SQLQueryValidator(**data)

class TestFileUploadValidator:
    """Testes para validação de upload de arquivos"""
    
    def test_valid_csv_upload(self):
        """Testa upload de CSV válido"""
        data = {
            'filename': 'data.csv',
            'content_type': 'text/csv',
            'file_size': 1024
        }
        validator = FileUploadValidator(**data)
        assert validator.filename == 'data.csv'
    
    def test_invalid_file_extension(self):
        """Testa rejeição de extensão inválida"""
        data = {
            'filename': 'malware.exe',
            'content_type': 'application/octet-stream',
            'file_size': 1024
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadValidator(**data)
        assert 'extensão não permitida' in str(exc_info.value)
    
    def test_file_size_limit(self):
        """Testa limite de tamanho de arquivo"""
        data = {
            'filename': 'large_file.csv',
            'content_type': 'text/csv',
            'file_size': 11 * 1024 * 1024  # 11MB
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadValidator(**data)
        assert 'muito grande' in str(exc_info.value)
    
    def test_content_type_mismatch(self):
        """Testa incompatibilidade entre extensão e content-type"""
        data = {
            'filename': 'data.csv',
            'content_type': 'application/pdf',  # Não combina com .csv
            'file_size': 1024
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadValidator(**data)
        assert 'não corresponde' in str(exc_info.value)

class TestUserInputValidator:
    """Testes para validação de entrada do usuário"""
    
    def test_valid_user_input(self):
        """Testa entrada de usuário válida"""
        data = {
            'content': 'Este é um texto normal e seguro',
            'input_type': 'text'
        }
        validator = UserInputValidator(**data)
        assert validator.content == 'Este é um texto normal e seguro'
    
    def test_script_injection_detection(self):
        """Testa detecção de injeção de script"""
        dangerous_inputs = [
            '<script>alert("XSS")</script>',
            'javascript:alert("XSS")',
            '<img src=x onerror=alert("XSS")>',
            'onload="alert(\"XSS\")"'
        ]
        
        for dangerous_input in dangerous_inputs:
            data = {
                'content': dangerous_input,
                'input_type': 'text'
            }
            with pytest.raises(ValidationError) as exc_info:
                UserInputValidator(**data)
            assert 'scripts potencialmente perigosos' in str(exc_info.value)
    
    def test_input_length_limit(self):
        """Testa limite de tamanho da entrada"""
        long_input = 'x' * 10001  # Excede o limite de 10000
        data = {
            'content': long_input,
            'input_type': 'text'
        }
        with pytest.raises(ValidationError) as exc_info:
            UserInputValidator(**data)
        assert 'muito longo' in str(exc_info.value)

class TestChartConfigValidator:
    """Testes para validação de configuração de gráficos"""
    
    def test_valid_chart_config(self):
        """Testa configuração de gráfico válida"""
        data = {
            'chart_type': 'bar',
            'x_column': 'produto',
            'y_column': 'vendas',
            'title': 'Vendas por Produto'
        }
        validator = ChartConfigValidator(**data)
        assert validator.chart_type == 'bar'
    
    def test_invalid_chart_type(self):
        """Testa tipo de gráfico inválido"""
        data = {
            'chart_type': 'invalid_type',
            'x_column': 'produto',
            'y_column': 'vendas',
            'title': 'Teste'
        }
        with pytest.raises(ValidationError):
            ChartConfigValidator(**data)
    
    def test_missing_required_columns(self):
        """Testa configuração com colunas obrigatórias faltando"""
        data = {
            'chart_type': 'bar',
            'title': 'Teste'
            # x_column e y_column faltando
        }
        with pytest.raises(ValidationError):
            ChartConfigValidator(**data)

class TestSecurityFunctions:
    """Testes para funções de segurança"""
    
    def test_sql_injection_validation(self):
        """Testa função de validação de SQL injection"""
        safe_query = "SELECT * FROM users WHERE age > 18"
        dangerous_query = "SELECT * FROM users WHERE id = '1; DROP TABLE users; --'"
        
        assert validate_sql_injection(safe_query) is True
        assert validate_sql_injection(dangerous_query) is False
    
    def test_input_sanitization(self):
        """Testa sanitização de entrada"""
        dangerous_input = '<script>alert("XSS")</script>Hello World'
        sanitized = sanitize_input(dangerous_input)
        
        assert '<script>' not in sanitized
        assert 'Hello World' in sanitized
    
    def test_sanitization_preserves_safe_content(self):
        """Testa que sanitização preserva conteúdo seguro"""
        safe_input = "Este é um texto normal com números 123 e símbolos @#$"
        sanitized = sanitize_input(safe_input)
        
        assert sanitized == safe_input
    
    @pytest.mark.parametrize("dangerous_pattern", [
        '<script>',
        'javascript:',
        'onload=',
        'onerror=',
        '<iframe>',
        'eval(',
        'document.cookie'
    ])
    def test_dangerous_patterns_removed(self, dangerous_pattern):
        """Testa remoção de padrões perigosos"""
        input_text = f"Texto normal {dangerous_pattern} mais texto"
        sanitized = sanitize_input(input_text)
        
        assert dangerous_pattern.lower() not in sanitized.lower()

class TestDashboardConfigValidator:
    """Testes para validação de configuração de dashboard"""
    
    def test_valid_dashboard_config(self):
        """Testa configuração de dashboard válida"""
        data = {
            'name': 'Dashboard de Vendas',
            'description': 'Dashboard para análise de vendas',
            'components': [
                {
                    'id': 'chart1',
                    'type': 'bar_chart',
                    'position': {'x': 0, 'y': 0, 'w': 6, 'h': 4}
                }
            ]
        }
        validator = DashboardConfigValidator(**data)
        assert validator.name == 'Dashboard de Vendas'
        assert len(validator.components) == 1
    
    def test_invalid_component_position(self):
        """Testa posição de componente inválida"""
        data = {
            'name': 'Dashboard Teste',
            'description': 'Teste',
            'components': [
                {
                    'id': 'chart1',
                    'type': 'bar_chart',
                    'position': {'x': -1, 'y': 0, 'w': 6, 'h': 4}  # x negativo
                }
            ]
        }
        with pytest.raises(ValidationError):
            DashboardConfigValidator(**data)
    
    def test_duplicate_component_ids(self):
        """Testa IDs de componentes duplicados"""
        data = {
            'name': 'Dashboard Teste',
            'description': 'Teste',
            'components': [
                {
                    'id': 'chart1',
                    'type': 'bar_chart',
                    'position': {'x': 0, 'y': 0, 'w': 6, 'h': 4}
                },
                {
                    'id': 'chart1',  # ID duplicado
                    'type': 'line_chart',
                    'position': {'x': 6, 'y': 0, 'w': 6, 'h': 4}
                }
            ]
        }
        with pytest.raises(ValidationError) as exc_info:
            DashboardConfigValidator(**data)
        assert 'IDs de componentes duplicados' in str(exc_info.value)

@pytest.mark.security
class TestSecurityIntegration:
    """Testes de integração de segurança"""
    
    def test_end_to_end_input_validation(self):
        """Testa validação de entrada de ponta a ponta"""
        # Simula entrada do usuário passando por todas as validações
        user_input = "SELECT name, age FROM users WHERE city = 'São Paulo'"
        
        # Validação de entrada do usuário
        input_validator = UserInputValidator(
            content=user_input,
            input_type='sql'
        )
        
        # Validação de query SQL
        sql_validator = SQLQueryValidator(
            query=input_validator.content,
            query_type='read'
        )
        
        assert sql_validator.query == user_input
        assert sql_validator.query_type == 'read'
    
    def test_security_headers_configuration(self):
        """Testa configuração de cabeçalhos de segurança"""
        # Este teste seria expandido para verificar cabeçalhos HTTP de segurança
        # como CSP, HSTS, X-Frame-Options, etc.
        pass