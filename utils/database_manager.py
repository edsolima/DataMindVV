# utils/database_manager.py
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import QueuePool
from typing import Dict, List, Tuple, Optional
import psycopg2 # Certifique-se de ter psycopg2-binary instalado: pip install psycopg2-binary
import pyodbc    # Certifique-se de ter pyodbc instalado e o driver ODBC para SQL Server: pip install pyodbc
from utils.logger import log_info, log_error, log_warning, log_debug
import re

class DatabaseManager:
    """
    Gerencia conexões com bancos de dados relacionais, provendo métodos para conectar, listar tabelas,
    obter schemas, executar queries seguras e amostrar dados, com foco em segurança e logging estruturado.
    """
    def __init__(self):
        """
        Inicializa o DatabaseManager, preparando o logger e variáveis de conexão.
        """
        self.engine = None
        self.connection_string = None
        log_info("DatabaseManager inicializado")

    def create_connection_string(self, connection_data: Dict) -> str:
        """
        Cria uma string de conexão SQLAlchemy a partir de um dicionário de dados de conexão.
        Suporta PostgreSQL, SQL Server, MySQL e SQLite.
        """
        db_type = connection_data.get('type', 'postgresql')
        host = connection_data.get('host', 'localhost')
        port = connection_data.get('port')
        database = connection_data.get('database')
        username = connection_data.get('username')
        password = connection_data.get('password')
        if db_type == 'postgresql':
            port = port or 5432
            # Montar parâmetros SSL se fornecidos
            ssl_params = []
            for param in ['sslmode', 'sslcert', 'sslkey', 'sslrootcert']:
                val = connection_data.get(param)
                if val:
                    ssl_params.append(f"{param}={val}")
            ssl_query = ('&' + '&'.join(ssl_params)) if ssl_params else ''
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}?client_encoding=utf8{ssl_query}"
        elif db_type == 'sqlserver':
            port = port or 1433
            driver = connection_data.get('driver', 'ODBC Driver 17 for SQL Server').replace(' ', '+')
            windows_auth = connection_data.get('windows_auth', False)
            if windows_auth:
                # Autenticação do Windows: sem usuário/senha, Trusted_Connection=yes
                conn_str = f"mssql+pyodbc://@{host}:{port}/{database}?driver={driver};Trusted_Connection=yes"
            else:
                conn_str = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver={driver}&charset=utf8"
            if connection_data.get('trust_server_certificate', False):
                conn_str += "&TrustServerCertificate=yes"
            return conn_str
        elif db_type == 'mysql':
            port = port or 3306
            # Certifique-se de ter mysqlclient ou mysql-connector-python instalado
            return f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'sqlite':
            # Para SQLite, 'host' é o caminho do arquivo. Ex: /path/to/your/database.db
            # Se o caminho for relativo, será relativo à raiz do projeto.
            return f"sqlite:///{host}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def test_connection(self, connection_data: Dict) -> Tuple[bool, str]:
        """
        Testa uma configuração de conexão com banco de dados, retornando (True, msg) se bem-sucedido.
        """
        try:
            conn_string = self.create_connection_string(connection_data)
            engine = create_engine(conn_string, connect_args={'connect_timeout': 5})
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            log_info("Teste de conexão bem-sucedido", extra={"database": connection_data.get('database'), "db_type": connection_data.get('type')})
            return True, "Connection successful!"
        except Exception as e:
            log_error("Teste de conexão falhou", extra={"database": connection_data.get('database'), "error": str(e)}, exc_info=True)
            return False, f"Connection failed: {str(e)}"

    def connect(self, connection_string: str) -> bool:
        """
        Estabelece conexão com o banco de dados usando connection pooling.
        Retorna True se a conexão for bem-sucedida.
        """
        try:
            # Configurar connection pooling para melhor performance
            pool_config = {
                'poolclass': QueuePool,
                'pool_size': 5,
                'max_overflow': 10,
                'pool_pre_ping': True,
                'pool_recycle': 3600,
                'connect_args': {'connect_timeout': 10}
            }
            
            self.engine = create_engine(connection_string, **pool_config)
            self.connection_string = connection_string
            with self.engine.connect() as connection: # Teste a conexão real
                connection.execute(text("SELECT 1"))
            
            db_info = connection_string.split('@')[-1] if '@' in connection_string else 'SQLite'
            log_info("Conexão com banco de dados estabelecida", extra={"db_info": db_info, "pool_size": pool_config['pool_size']})
            return True
        except Exception as e:
            log_error("Erro ao conectar com banco de dados", extra={"error": str(e)}, exc_info=True)
            self.engine = None
            self.connection_string = None
            return False

    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        Retorna a lista de tabelas do banco conectado.
        Para PostgreSQL, o schema padrão é 'public'.
        """
        if not self.engine:
            log_warning("Não é possível obter tabelas - sem conexão com banco de dados")
            return []
        try:
            inspector = inspect(self.engine)
            db_type = str(self.engine.url).split(':')[0]

            if db_type == 'postgresql':
                # Se o schema não for fornecido, buscar em 'public' e outros schemas comuns se necessário
                # Ou listar todos os schemas e prefixar as tabelas
                current_schema = schema or 'public' # Default to public for PostgreSQL
                # Garantir que o schema existe
                # schema_names = inspector.get_schema_names()
                # if schema and schema not in schema_names:
                # print(f"Schema '{schema}' not found. Available schemas: {schema_names}")
                # return []
                tables = inspector.get_table_names(schema=current_schema)
                return [f"{current_schema}.{t}" for t in tables] if current_schema else tables
            elif db_type == 'mssql':
                # Para SQL Server, o schema padrão é 'dbo'
                current_schema = schema or 'dbo'
                tables = inspector.get_table_names(schema=current_schema)
                return [f"{current_schema}.{t}" for t in tables] if current_schema else tables
            else: # Para MySQL, SQLite, etc.
                tables = inspector.get_table_names(schema=schema)
                return tables
        except Exception as e:
            log_error("Erro ao obter lista de tabelas", extra={"schema": schema, "error": str(e)}, exc_info=True)
            return []

    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> pd.DataFrame:
        """
        Retorna o schema (colunas e tipos) de uma tabela específica.
        """
        if not self.engine:
            log_warning("Não é possível obter schema da tabela - sem conexão com banco de dados")
            return pd.DataFrame()
        try:
            # Handle schema.table format if passed directly
            if '.' in table_name and not schema:
                schema, table_name = table_name.split('.', 1)

            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name, schema=schema)
            schema_df = pd.DataFrame([
                {'Column': col['name'],
                 'Type': str(col['type']),
                 'Nullable': col.get('nullable', True)} # Default nullable to True if not specified
                for col in columns
            ])
            return schema_df
        except Exception as e:
            table_ref = f"{schema}.{table_name}" if schema else table_name
            log_error("Erro ao obter schema da tabela", extra={"table": table_ref, "error": str(e)}, exc_info=True)
            return pd.DataFrame()

    def _validate_identifier(self, name: str) -> bool:
        """
        Valida identificadores de tabela/schema para evitar SQL Injection.
        Permite apenas letras, números, underline e ponto.
        """
        return bool(re.match(r'^[A-Za-z0-9_\.]+$', name))

    def execute_query(self, query: str, params: dict = None) -> pd.DataFrame:
        """
        Executa uma query SQL customizada e retorna um DataFrame.
        ALERTA: Use sempre queries parametrizadas para evitar SQL Injection!
        Se detectar comandos perigosos em query sem params, loga alerta.
        """
        if not self.engine:
            log_warning("Não é possível executar query - sem conexão com banco de dados")
            return pd.DataFrame()
        # ALERTA: Detecta concatenação perigosa
        if any(op in query.lower() for op in [';--', 'drop ', 'delete ', 'insert ', 'update ', 'alter ', 'exec ', 'union ', ' or ', ' and ']) and params is None:
            log_warning("Query potencialmente perigosa detectada. Use sempre queries parametrizadas!", extra={"query_preview": query[:100]})
        try:
            if params:
                df = pd.read_sql_query(text(query), self.engine, params=params)
            else:
                df = pd.read_sql_query(text(query), self.engine)
            log_info("Query executada com sucesso", extra={"rows_returned": len(df), "query_preview": query[:100]})
            return df
        except Exception as e:
            log_error("Erro ao executar query", extra={"query_preview": query[:100], "error": str(e)}, exc_info=True)
            return pd.DataFrame()

    def get_table_sample(self, table_name: str, schema: Optional[str] = None, sample_size: int = 100) -> pd.DataFrame:
        """
        Retorna uma amostra de dados de uma tabela, validando nomes para evitar SQL Injection.
        """
        if not self.engine:
            log_warning("Não é possível obter amostra da tabela - sem conexão com banco de dados")
            return pd.DataFrame()
        # Handle schema.table format if passed directly
        if '.' in table_name and not schema:
            schema, table_name = table_name.split('.', 1)
        # Validação de nomes
        if not self._validate_identifier(table_name) or (schema and not self._validate_identifier(schema)):
            log_error("Nome de tabela ou schema inválido detectado!", extra={"table": table_name, "schema": schema})
            return pd.DataFrame()
        db_type = str(self.engine.url).split(':')[0]
        
        try:
            # Construir o nome completo da tabela com schema, tratando aspas para diferentes BDs
            if db_type == 'postgresql':
                table_ref = f'"{schema}"."{table_name}"' if schema else f'"{table_name}"'
                query = f"SELECT * FROM {table_ref} TABLESAMPLE SYSTEM(1) LIMIT {sample_size}"
            elif db_type == 'mssql':
                table_ref = f'[{schema}].[{table_name}]' if schema else f'[{table_name}]'
                query = f"SELECT TOP ({sample_size}) * FROM {table_ref}"
            elif db_type == 'mysql':
                table_ref = f'`{schema}`.`{table_name}`' if schema else f'`{table_name}`'
                query = f"SELECT * FROM {table_ref} LIMIT {sample_size}" # MySQL usa LIMIT
            elif db_type == 'sqlite':
                table_ref = f'"{table_name}"' # SQLite não tem schemas da mesma forma
                query = f"SELECT * FROM {table_ref} LIMIT {sample_size}"
            else: # Fallback genérico
                table_ref = f"{schema}.{table_name}" if schema else table_name
                query = f"SELECT * FROM {table_ref} LIMIT {sample_size}"
            
            log_debug("Executando query de amostragem", extra={"query": query, "table": table_ref})
            df = pd.read_sql_query(text(query), self.engine)
            log_info("Amostra da tabela carregada", extra={"table": table_ref, "rows": len(df), "sample_size": sample_size})
            return df
        except Exception as e:
            log_warning("Erro ao obter amostra com método específico - tentando fallback", extra={"error": str(e), "table": table_name})
            # Fallback para um LIMIT simples se o método específico falhar
            try:
                table_ref_fallback = f'"{table_name}"' # Ou ajuste conforme necessário
                query_fallback = f"SELECT * FROM {table_ref_fallback} LIMIT {sample_size}"
                log_debug("Executando query de fallback", extra={"query": query_fallback})
                df = pd.read_sql_query(text(query_fallback), self.engine)
                log_info("Amostra da tabela carregada (fallback)", extra={"table": table_ref_fallback, "rows": len(df)})
                return df
            except Exception as e2:
                log_error("Erro ao obter amostra da tabela (fallback)", extra={"table": table_name, "error": str(e2)}, exc_info=True)
                return pd.DataFrame()

    def close_connection(self):
        """
        Fecha a conexão com o banco de dados e libera recursos.
        """
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.connection_string = None
            log_info("Conexão com banco de dados fechada")