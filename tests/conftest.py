import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd
import sqlite3
from typing import Dict, Any

# Configurar variáveis de ambiente para testes
os.environ['TESTING'] = 'true'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['ENCRYPTION_KEY'] = 'test-encryption-key-for-testing'
os.environ['APP_ENV'] = 'test'

@pytest.fixture(scope="session")
def test_data_dir():
    """Diretório temporário para dados de teste"""
    temp_dir = tempfile.mkdtemp(prefix="bi_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture(scope="session")
def test_db_path(test_data_dir):
    """Caminho para banco de dados de teste"""
    return test_data_dir / "test_database.db"

@pytest.fixture
def test_sqlite_db(test_db_path):
    """Banco de dados SQLite para testes"""
    conn = sqlite3.connect(str(test_db_path))
    
    # Criar tabelas de teste
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            product_name TEXT,
            quantity INTEGER,
            price REAL,
            sale_date DATE,
            region TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            age INTEGER,
            city TEXT
        )
    """)
    
    # Inserir dados de teste
    sales_data = [
        (1, 'Produto A', 10, 25.50, '2024-01-15', 'Norte'),
        (2, 'Produto B', 5, 45.00, '2024-01-16', 'Sul'),
        (3, 'Produto C', 8, 30.75, '2024-01-17', 'Norte'),
        (4, 'Produto A', 12, 25.50, '2024-01-18', 'Centro'),
        (5, 'Produto D', 3, 80.00, '2024-01-19', 'Sul')
    ]
    
    customers_data = [
        (1, 'João Silva', 'joao@email.com', 35, 'São Paulo'),
        (2, 'Maria Santos', 'maria@email.com', 28, 'Rio de Janeiro'),
        (3, 'Pedro Costa', 'pedro@email.com', 42, 'Belo Horizonte'),
        (4, 'Ana Oliveira', 'ana@email.com', 31, 'Salvador'),
        (5, 'Carlos Lima', 'carlos@email.com', 39, 'Brasília')
    ]
    
    conn.executemany("INSERT OR REPLACE INTO sales VALUES (?, ?, ?, ?, ?, ?)", sales_data)
    conn.executemany("INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?, ?)", customers_data)
    conn.commit()
    
    yield conn
    conn.close()

@pytest.fixture
def sample_dataframe():
    """DataFrame de exemplo para testes"""
    return pd.DataFrame({
        'produto': ['A', 'B', 'C', 'A', 'B'],
        'vendas': [100, 150, 200, 120, 180],
        'regiao': ['Norte', 'Sul', 'Centro', 'Norte', 'Sul'],
        'data': pd.date_range('2024-01-01', periods=5)
    })

@pytest.fixture
def mock_config_manager():
    """Mock do ConfigManager para testes"""
    mock = Mock()
    mock.load_connections.return_value = {
        'test_connection': {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass',
            'db_type': 'postgresql'
        }
    }
    mock.save_connection.return_value = True
    mock.delete_connection.return_value = True
    return mock

@pytest.fixture
def mock_database_manager():
    """Mock do DatabaseManager para testes"""
    mock = Mock()
    mock.connect.return_value = True
    mock.test_connection.return_value = True
    mock.execute_query.return_value = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Test 1', 'Test 2', 'Test 3']
    })
    mock.get_tables.return_value = ['table1', 'table2', 'table3']
    mock.get_columns.return_value = ['id', 'name', 'value']
    return mock

@pytest.fixture
def mock_query_manager():
    """Mock do QueryManager para testes"""
    mock = Mock()
    mock.save_query.return_value = True
    mock.load_queries.return_value = {
        'test_query': {
            'query': 'SELECT * FROM test_table',
            'description': 'Query de teste',
            'created_at': '2024-01-01 10:00:00'
        }
    }
    mock.delete_query.return_value = True
    return mock

@pytest.fixture
def mock_cache_manager():
    """Mock do CacheManager para testes"""
    mock = Mock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.clear.return_value = True
    return mock

@pytest.fixture
def test_config_data():
    """Dados de configuração para testes"""
    return {
        'database': {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password'
        },
        'cache': {
            'type': 'sqlite',
            'timeout': 300
        },
        'logging': {
            'level': 'DEBUG',
            'file': 'test.log'
        }
    }

@pytest.fixture
def test_chart_config():
    """Configuração de gráfico para testes"""
    return {
        'type': 'bar',
        'x_column': 'produto',
        'y_column': 'vendas',
        'title': 'Vendas por Produto',
        'color_column': 'regiao'
    }

@pytest.fixture
def test_dashboard_config():
    """Configuração de dashboard para testes"""
    return {
        'name': 'Dashboard de Teste',
        'description': 'Dashboard para testes automatizados',
        'components': [
            {
                'id': 'chart1',
                'type': 'bar_chart',
                'position': {'x': 0, 'y': 0, 'w': 6, 'h': 4},
                'config': {
                    'title': 'Vendas por Produto',
                    'x_column': 'produto',
                    'y_column': 'vendas'
                }
            },
            {
                'id': 'table1',
                'type': 'data_table',
                'position': {'x': 6, 'y': 0, 'w': 6, 'h': 4},
                'config': {
                    'title': 'Dados de Vendas',
                    'columns': ['produto', 'vendas', 'regiao']
                }
            }
        ]
    }

@pytest.fixture
def mock_dash_app():
    """Mock da aplicação Dash para testes"""
    with patch('dash.Dash') as mock_dash:
        app = Mock()
        mock_dash.return_value = app
        app.callback = Mock()
        app.run_server = Mock()
        yield app

@pytest.fixture
def test_sql_queries():
    """Queries SQL para testes"""
    return {
        'valid_select': 'SELECT * FROM sales WHERE region = "Norte"',
        'valid_insert': 'INSERT INTO customers (name, email) VALUES ("Test", "test@email.com")',
        'valid_update': 'UPDATE sales SET price = 30.00 WHERE id = 1',
        'invalid_drop': 'DROP TABLE sales',
        'invalid_delete_all': 'DELETE FROM customers',
        'sql_injection': "SELECT * FROM users WHERE id = '1; DROP TABLE users; --'"
    }

@pytest.fixture
def test_file_uploads():
    """Dados para teste de upload de arquivos"""
    return {
        'valid_csv': {
            'filename': 'test.csv',
            'content': 'name,age,city\nJoão,30,SP\nMaria,25,RJ',
            'content_type': 'text/csv'
        },
        'valid_excel': {
            'filename': 'test.xlsx',
            'content': b'fake_excel_content',
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        },
        'invalid_extension': {
            'filename': 'test.exe',
            'content': b'fake_executable',
            'content_type': 'application/octet-stream'
        },
        'oversized_file': {
            'filename': 'large.csv',
            'content': 'x' * (11 * 1024 * 1024),  # 11MB
            'content_type': 'text/csv'
        }
    }

@pytest.fixture(autouse=True)
def setup_test_environment(test_data_dir):
    """Configuração automática do ambiente de teste"""
    # Configurar diretórios de teste
    logs_dir = test_data_dir / 'logs'
    config_dir = test_data_dir / 'config'
    cache_dir = test_data_dir / 'cache'
    
    logs_dir.mkdir(exist_ok=True)
    config_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)
    
    # Configurar variáveis de ambiente específicas para teste
    test_env = {
        'LOGS_DIR': str(logs_dir),
        'CONFIG_DIR': str(config_dir),
        'CACHE_DIR': str(cache_dir),
        'DATABASE_URL': f'sqlite:///{test_data_dir}/test.db'
    }
    
    with patch.dict(os.environ, test_env):
        yield

@pytest.fixture
def performance_monitor():
    """Monitor de performance para testes"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.measurements = []
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self, operation_name: str):
            if self.start_time:
                duration = time.time() - self.start_time
                self.measurements.append({
                    'operation': operation_name,
                    'duration': duration
                })
                self.start_time = None
                return duration
            return 0
        
        def get_measurements(self):
            return self.measurements.copy()
        
        def assert_performance(self, operation_name: str, max_duration: float):
            measurement = next(
                (m for m in self.measurements if m['operation'] == operation_name),
                None
            )
            if measurement:
                assert measurement['duration'] <= max_duration, \
                    f"Operation {operation_name} took {measurement['duration']:.3f}s, expected <= {max_duration}s"
    
    return PerformanceMonitor()

# Configurações globais do pytest
def pytest_configure(config):
    """Configuração global do pytest"""
    # Adicionar marcadores customizados
    config.addinivalue_line(
        "markers", "slow: marca testes que demoram para executar"
    )
    config.addinivalue_line(
        "markers", "integration: marca testes de integração"
    )
    config.addinivalue_line(
        "markers", "unit: marca testes unitários"
    )
    config.addinivalue_line(
        "markers", "performance: marca testes de performance"
    )
    config.addinivalue_line(
        "markers", "security: marca testes de segurança"
    )

def pytest_collection_modifyitems(config, items):
    """Modifica a coleta de testes"""
    # Adicionar marcador 'slow' para testes que demoram
    for item in items:
        if "slow" in item.nodeid or "integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)