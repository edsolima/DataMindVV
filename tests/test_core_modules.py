import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path
import sqlite3
import time

# Importações dos módulos a serem testados
from utils.config_manager import ConfigManager
from utils.database_manager import DatabaseManager
from utils.query_manager import QueryManager
from utils.sqlite_cache import SQLiteCache
from utils.dependency_container import DIContainer, setup_dependencies

class TestConfigManager:
    """Testes para o ConfigManager"""
    
    def test_config_manager_initialization(self, test_data_dir):
        """Testa inicialização do ConfigManager"""
        config_file = test_data_dir / 'test_connections.yml'
        config_manager = ConfigManager(str(config_file))
        assert config_manager.config_file == str(config_file)
    
    def test_save_and_load_connection(self, test_data_dir):
        """Testa salvamento e carregamento de conexão"""
        config_file = test_data_dir / 'test_connections.yml'
        config_manager = ConfigManager(str(config_file))
        
        connection_data = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password',
            'db_type': 'postgresql'
        }
        
        # Salvar conexão
        result = config_manager.save_connection('test_conn', connection_data)
        assert result is True
        
        # Carregar conexões
        connections = config_manager.load_connections(decrypt_passwords=False)
        assert 'test_conn' in connections
        assert connections['test_conn']['host'] == 'localhost'
        assert connections['test_conn']['port'] == 5432
    
    def test_delete_connection(self, test_data_dir):
        """Testa exclusão de conexão"""
        config_file = test_data_dir / 'test_connections.yml'
        config_manager = ConfigManager(str(config_file))
        
        # Primeiro salvar uma conexão
        connection_data = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password',
            'db_type': 'postgresql'
        }
        config_manager.save_connection('test_conn', connection_data)
        
        # Depois deletar
        result = config_manager.delete_connection('test_conn')
        assert result is True
        
        # Verificar que foi deletada
        connections = config_manager.load_connections()
        assert 'test_conn' not in connections
    
    def test_password_encryption_decryption(self, test_data_dir):
        """Testa criptografia e descriptografia de senhas"""
        config_file = test_data_dir / 'test_connections.yml'
        config_manager = ConfigManager(str(config_file))
        
        original_password = 'my_secret_password'
        
        # Criptografar
        encrypted = config_manager._encrypt_password(original_password)
        assert encrypted != original_password
        assert len(encrypted) > len(original_password)
        
        # Descriptografar
        decrypted = config_manager._decrypt_password(encrypted)
        assert decrypted == original_password
    
    def test_invalid_connection_data(self, test_data_dir):
        """Testa tratamento de dados de conexão inválidos"""
        config_file = test_data_dir / 'test_connections.yml'
        config_manager = ConfigManager(str(config_file))
        
        # Dados incompletos
        invalid_data = {
            'host': 'localhost'
            # Faltando campos obrigatórios
        }
        
        result = config_manager.save_connection('invalid_conn', invalid_data)
        assert result is False

class TestDatabaseManager:
    """Testes para o DatabaseManager"""
    
    def test_database_manager_initialization(self):
        """Testa inicialização do DatabaseManager"""
        db_manager = DatabaseManager()
        assert db_manager.connection is None
        assert db_manager.engine is None
    
    def test_sqlite_connection_string(self):
        """Testa criação de string de conexão SQLite"""
        db_manager = DatabaseManager()
        
        connection_data = {
            'database': '/path/to/database.db',
            'db_type': 'sqlite'
        }
        
        conn_string = db_manager._create_connection_string(connection_data)
        assert conn_string == 'sqlite:////path/to/database.db'
    
    def test_postgresql_connection_string(self):
        """Testa criação de string de conexão PostgreSQL"""
        db_manager = DatabaseManager()
        
        connection_data = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'user',
            'password': 'pass',
            'db_type': 'postgresql'
        }
        
        conn_string = db_manager._create_connection_string(connection_data)
        expected = 'postgresql://user:pass@localhost:5432/test_db'
        assert conn_string == expected
    
    def test_mysql_connection_string(self):
        """Testa criação de string de conexão MySQL"""
        db_manager = DatabaseManager()
        
        connection_data = {
            'host': 'localhost',
            'port': 3306,
            'database': 'test_db',
            'username': 'user',
            'password': 'pass',
            'db_type': 'mysql'
        }
        
        conn_string = db_manager._create_connection_string(connection_data)
        expected = 'mysql+pymysql://user:pass@localhost:3306/test_db'
        assert conn_string == expected
    
    @patch('sqlalchemy.create_engine')
    def test_connect_success(self, mock_create_engine):
        """Testa conexão bem-sucedida"""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        db_manager = DatabaseManager()
        connection_string = 'sqlite:///test.db'
        
        result = db_manager.connect(connection_string)
        assert result is True
        assert db_manager.engine == mock_engine
        mock_create_engine.assert_called_once()
    
    @patch('sqlalchemy.create_engine')
    def test_connect_failure(self, mock_create_engine):
        """Testa falha na conexão"""
        mock_create_engine.side_effect = Exception("Connection failed")
        
        db_manager = DatabaseManager()
        connection_string = 'invalid://connection'
        
        result = db_manager.connect(connection_string)
        assert result is False
        assert db_manager.engine is None
    
    def test_execute_query_with_sqlite(self, test_sqlite_db):
        """Testa execução de query com SQLite real"""
        db_manager = DatabaseManager()
        
        # Conectar ao banco de teste
        db_path = test_sqlite_db.execute("PRAGMA database_list").fetchone()[2]
        connection_string = f'sqlite:///{db_path}'
        
        result = db_manager.connect(connection_string)
        assert result is True
        
        # Executar query
        df = db_manager.execute_query("SELECT * FROM sales LIMIT 3")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert 'product_name' in df.columns
    
    def test_get_tables_with_sqlite(self, test_sqlite_db):
        """Testa obtenção de tabelas com SQLite real"""
        db_manager = DatabaseManager()
        
        # Conectar ao banco de teste
        db_path = test_sqlite_db.execute("PRAGMA database_list").fetchone()[2]
        connection_string = f'sqlite:///{db_path}'
        
        db_manager.connect(connection_string)
        tables = db_manager.get_tables()
        
        assert isinstance(tables, list)
        assert 'sales' in tables
        assert 'customers' in tables
    
    def test_get_columns_with_sqlite(self, test_sqlite_db):
        """Testa obtenção de colunas com SQLite real"""
        db_manager = DatabaseManager()
        
        # Conectar ao banco de teste
        db_path = test_sqlite_db.execute("PRAGMA database_list").fetchone()[2]
        connection_string = f'sqlite:///{db_path}'
        
        db_manager.connect(connection_string)
        columns = db_manager.get_columns('sales')
        
        assert isinstance(columns, list)
        expected_columns = ['id', 'product_name', 'quantity', 'price', 'sale_date', 'region']
        for col in expected_columns:
            assert col in columns

class TestQueryManager:
    """Testes para o QueryManager"""
    
    def test_query_manager_initialization(self, test_data_dir):
        """Testa inicialização do QueryManager"""
        queries_file = test_data_dir / 'test_queries.json'
        query_manager = QueryManager(str(queries_file))
        assert query_manager.queries_file == str(queries_file)
    
    def test_save_and_load_query(self, test_data_dir):
        """Testa salvamento e carregamento de query"""
        queries_file = test_data_dir / 'test_queries.json'
        query_manager = QueryManager(str(queries_file))
        
        query_name = 'test_query'
        query_sql = 'SELECT * FROM sales WHERE region = "Norte"'
        query_description = 'Query de teste para região Norte'
        
        # Salvar query
        result = query_manager.save_query(query_name, query_sql, query_description)
        assert result is True
        
        # Carregar queries
        queries = query_manager.load_queries()
        assert query_name in queries
        assert queries[query_name]['query'] == query_sql
        assert queries[query_name]['description'] == query_description
    
    def test_delete_query(self, test_data_dir):
        """Testa exclusão de query"""
        queries_file = test_data_dir / 'test_queries.json'
        query_manager = QueryManager(str(queries_file))
        
        # Primeiro salvar uma query
        query_manager.save_query('test_query', 'SELECT 1', 'Teste')
        
        # Depois deletar
        result = query_manager.delete_query('test_query')
        assert result is True
        
        # Verificar que foi deletada
        queries = query_manager.load_queries()
        assert 'test_query' not in queries
    
    def test_update_query(self, test_data_dir):
        """Testa atualização de query existente"""
        queries_file = test_data_dir / 'test_queries.json'
        query_manager = QueryManager(str(queries_file))
        
        # Salvar query inicial
        query_manager.save_query('test_query', 'SELECT 1', 'Descrição inicial')
        
        # Atualizar query
        new_sql = 'SELECT * FROM customers'
        new_description = 'Nova descrição'
        result = query_manager.save_query('test_query', new_sql, new_description)
        assert result is True
        
        # Verificar atualização
        queries = query_manager.load_queries()
        assert queries['test_query']['query'] == new_sql
        assert queries['test_query']['description'] == new_description
    
    def test_get_query_history(self, test_data_dir):
        """Testa obtenção do histórico de queries"""
        queries_file = test_data_dir / 'test_queries.json'
        query_manager = QueryManager(str(queries_file))
        
        # Salvar algumas queries
        query_manager.save_query('query1', 'SELECT 1', 'Primeira query')
        query_manager.save_query('query2', 'SELECT 2', 'Segunda query')
        query_manager.save_query('query3', 'SELECT 3', 'Terceira query')
        
        # Obter histórico
        history = query_manager.get_query_history(limit=2)
        assert len(history) == 2
        
        # Verificar ordem (mais recentes primeiro)
        assert history[0]['name'] == 'query3'
        assert history[1]['name'] == 'query2'

class TestSQLiteCache:
    """Testes para o SQLiteCache"""
    
    def test_cache_initialization(self, test_data_dir):
        """Testa inicialização do cache"""
        cache_file = test_data_dir / 'test_cache.db'
        cache = SQLiteCache(str(cache_file))
        assert cache.db_path == str(cache_file)
    
    def test_set_and_get_cache(self, test_data_dir):
        """Testa definição e obtenção de cache"""
        cache_file = test_data_dir / 'test_cache.db'
        cache = SQLiteCache(str(cache_file))
        
        key = 'test_key'
        value = {'data': 'test_value', 'number': 42}
        
        # Definir cache
        result = cache.set(key, value)
        assert result is True
        
        # Obter cache
        cached_value = cache.get(key)
        assert cached_value == value
    
    def test_cache_expiration(self, test_data_dir):
        """Testa expiração do cache"""
        cache_file = test_data_dir / 'test_cache.db'
        cache = SQLiteCache(str(cache_file))
        
        key = 'expiring_key'
        value = 'expiring_value'
        
        # Definir cache com timeout muito baixo
        cache.set(key, value, timeout=1)
        
        # Verificar que existe imediatamente
        assert cache.get(key) == value
        
        # Aguardar expiração
        time.sleep(1.1)
        
        # Verificar que expirou
        assert cache.get(key) is None
    
    def test_cache_delete(self, test_data_dir):
        """Testa exclusão de cache"""
        cache_file = test_data_dir / 'test_cache.db'
        cache = SQLiteCache(str(cache_file))
        
        key = 'delete_key'
        value = 'delete_value'
        
        # Definir e verificar
        cache.set(key, value)
        assert cache.get(key) == value
        
        # Deletar
        result = cache.delete(key)
        assert result is True
        
        # Verificar que foi deletado
        assert cache.get(key) is None
    
    def test_cache_clear(self, test_data_dir):
        """Testa limpeza completa do cache"""
        cache_file = test_data_dir / 'test_cache.db'
        cache = SQLiteCache(str(cache_file))
        
        # Definir múltiplos itens
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')
        
        # Verificar que existem
        assert cache.get('key1') == 'value1'
        assert cache.get('key2') == 'value2'
        
        # Limpar cache
        result = cache.clear()
        assert result is True
        
        # Verificar que foram removidos
        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert cache.get('key3') is None
    
    def test_cache_with_dataframe(self, test_data_dir, sample_dataframe):
        """Testa cache com DataFrame"""
        cache_file = test_data_dir / 'test_cache.db'
        cache = SQLiteCache(str(cache_file))
        
        key = 'dataframe_key'
        
        # Definir DataFrame no cache
        result = cache.set(key, sample_dataframe)
        assert result is True
        
        # Obter DataFrame do cache
        cached_df = cache.get(key)
        assert isinstance(cached_df, pd.DataFrame)
        pd.testing.assert_frame_equal(cached_df, sample_dataframe)

class TestDependencyContainer:
    """Testes para o container de dependências"""
    
    def test_container_initialization(self):
        """Testa inicialização do container"""
        container = DIContainer()
        assert len(container._services) == 0
        assert len(container._singletons) == 0
        assert len(container._factories) == 0
    
    def test_register_and_get_singleton(self):
        """Testa registro e obtenção de singleton"""
        container = DIContainer()
        
        # Criar um mock service
        mock_service = Mock()
        
        # Registrar como singleton
        container.register_singleton(type(mock_service), mock_service)
        
        # Obter serviço
        retrieved_service = container.get(type(mock_service))
        assert retrieved_service is mock_service
    
    def test_register_and_get_transient(self):
        """Testa registro e obtenção de transient"""
        container = DIContainer()
        
        # Factory que cria novos mocks
        def mock_factory():
            return Mock()
        
        # Registrar como transient
        container.register_transient(Mock, mock_factory)
        
        # Obter serviços (devem ser instâncias diferentes)
        service1 = container.get(Mock)
        service2 = container.get(Mock)
        
        assert service1 is not service2
        assert isinstance(service1, Mock)
        assert isinstance(service2, Mock)
    
    def test_register_instance(self):
        """Testa registro de instância específica"""
        container = DIContainer()
        
        instance = {'test': 'value'}
        container.register_instance(dict, instance)
        
        retrieved = container.get(dict)
        assert retrieved is instance
    
    def test_service_not_found(self):
        """Testa erro quando serviço não é encontrado"""
        container = DIContainer()
        
        with pytest.raises(ValueError, match="Serviço não encontrado"):
            container.get(str)
    
    def test_has_service(self):
        """Testa verificação de existência de serviço"""
        container = DIContainer()
        
        # Inicialmente não tem
        assert container.has(str) is False
        
        # Registrar e verificar
        container.register_instance(str, "test")
        assert container.has(str) is True
    
    def test_clear_container(self):
        """Testa limpeza do container"""
        container = DIContainer()
        
        # Registrar alguns serviços
        container.register_instance(str, "test")
        container.register_singleton(int, 42)
        
        # Verificar que existem
        assert container.has(str) is True
        assert container.has(int) is True
        
        # Limpar
        container.clear()
        
        # Verificar que foram removidos
        assert container.has(str) is False
        assert container.has(int) is False

@pytest.mark.integration
class TestModuleIntegration:
    """Testes de integração entre módulos"""
    
    def test_config_and_database_integration(self, test_data_dir, test_sqlite_db):
        """Testa integração entre ConfigManager e DatabaseManager"""
        # Configurar ConfigManager
        config_file = test_data_dir / 'integration_test.yml'
        config_manager = ConfigManager(str(config_file))
        
        # Obter caminho do banco de teste
        db_path = test_sqlite_db.execute("PRAGMA database_list").fetchone()[2]
        
        # Salvar conexão
        connection_data = {
            'database': db_path,
            'db_type': 'sqlite'
        }
        config_manager.save_connection('test_integration', connection_data)
        
        # Carregar conexão e usar no DatabaseManager
        connections = config_manager.load_connections()
        db_manager = DatabaseManager()
        
        conn_string = db_manager._create_connection_string(
            connections['test_integration']
        )
        
        result = db_manager.connect(conn_string)
        assert result is True
        
        # Executar query
        df = db_manager.execute_query("SELECT COUNT(*) as total FROM sales")
        assert len(df) == 1
        assert df.iloc[0]['total'] == 5  # 5 registros de teste
    
    def test_query_manager_and_cache_integration(self, test_data_dir):
        """Testa integração entre QueryManager e Cache"""
        # Configurar managers
        queries_file = test_data_dir / 'integration_queries.json'
        cache_file = test_data_dir / 'integration_cache.db'
        
        query_manager = QueryManager(str(queries_file))
        cache = SQLiteCache(str(cache_file))
        
        # Salvar query
        query_sql = 'SELECT * FROM sales WHERE region = "Norte"'
        query_manager.save_query('north_sales', query_sql, 'Vendas do Norte')
        
        # Simular resultado da query no cache
        cache_key = f"query_result_{hash(query_sql)}"
        mock_result = pd.DataFrame({
            'product_name': ['Produto A', 'Produto C'],
            'quantity': [10, 8],
            'region': ['Norte', 'Norte']
        })
        
        cache.set(cache_key, mock_result)
        
        # Verificar que o resultado está no cache
        cached_result = cache.get(cache_key)
        assert isinstance(cached_result, pd.DataFrame)
        assert len(cached_result) == 2
        assert all(cached_result['region'] == 'Norte')

@pytest.mark.performance
class TestPerformance:
    """Testes de performance"""
    
    def test_cache_performance(self, test_data_dir, performance_monitor):
        """Testa performance do cache"""
        cache_file = test_data_dir / 'performance_cache.db'
        cache = SQLiteCache(str(cache_file))
        
        # Teste de escrita
        performance_monitor.start()
        for i in range(100):
            cache.set(f'key_{i}', f'value_{i}')
        write_duration = performance_monitor.stop('cache_write_100_items')
        
        # Teste de leitura
        performance_monitor.start()
        for i in range(100):
            cache.get(f'key_{i}')
        read_duration = performance_monitor.stop('cache_read_100_items')
        
        # Verificar performance (ajustar limites conforme necessário)
        performance_monitor.assert_performance('cache_write_100_items', 2.0)  # 2 segundos
        performance_monitor.assert_performance('cache_read_100_items', 1.0)   # 1 segundo
    
    def test_query_manager_performance(self, test_data_dir, performance_monitor):
        """Testa performance do QueryManager"""
        queries_file = test_data_dir / 'performance_queries.json'
        query_manager = QueryManager(str(queries_file))
        
        # Teste de salvamento de múltiplas queries
        performance_monitor.start()
        for i in range(50):
            query_manager.save_query(
                f'query_{i}',
                f'SELECT * FROM table_{i}',
                f'Descrição da query {i}'
            )
        save_duration = performance_monitor.stop('query_save_50_items')
        
        # Teste de carregamento
        performance_monitor.start()
        queries = query_manager.load_queries()
        load_duration = performance_monitor.stop('query_load_all')
        
        # Verificar que todas as queries foram salvas
        assert len(queries) == 50
        
        # Verificar performance
        performance_monitor.assert_performance('query_save_50_items', 1.0)
        performance_monitor.assert_performance('query_load_all', 0.5)