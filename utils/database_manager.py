# utils/database_manager.py
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine, text, inspect
from typing import Dict, List, Tuple, Optional
import psycopg2 # Certifique-se de ter psycopg2-binary instalado: pip install psycopg2-binary
import pyodbc    # Certifique-se de ter pyodbc instalado e o driver ODBC para SQL Server: pip install pyodbc

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.connection_string = None
        print("DatabaseManager initialized.")

    def create_connection_string(self, connection_data: Dict) -> str:
        """Create SQLAlchemy connection string from connection data"""
        db_type = connection_data.get('type', 'postgresql')
        host = connection_data.get('host', 'localhost')
        port = connection_data.get('port')
        database = connection_data.get('database')
        username = connection_data.get('username')
        password = connection_data.get('password')

        if db_type == 'postgresql':
            port = port or 5432
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}?client_encoding=utf8"
        elif db_type == 'sqlserver':
            port = port or 1433
            # O driver ODBC para SQL Server pode variar. "ODBC Driver 17 for SQL Server" é comum.
            # Outros podem ser "SQL Server Native Client 11.0" ou apenas "SQL Server"
            # Adicione TrustServerCertificate=yes para desenvolvimento se necessário, mas não para produção.
            driver = connection_data.get('driver', 'ODBC Driver 17 for SQL Server').replace(' ', '+')
            conn_str = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver={driver}&charset=utf8"
            if connection_data.get('trust_server_certificate', False): # Adicionar opção para TrustServerCertificate
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
        """Test a database connection configuration"""
        try:
            conn_string = self.create_connection_string(connection_data)
            engine = create_engine(conn_string, connect_args={'connect_timeout': 5})
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print(f"Test connection successful for: {connection_data.get('database')}")
            return True, "Connection successful!"
        except Exception as e:
            print(f"Test connection failed: {e}")
            return False, f"Connection failed: {str(e)}"

    def connect(self, connection_string: str) -> bool:
        """Establish a database connection"""
        try:
            self.engine = create_engine(connection_string, connect_args={'connect_timeout': 10})
            self.connection_string = connection_string
            with self.engine.connect() as connection: # Teste a conexão real
                connection.execute(text("SELECT 1"))
            print(f"Successfully connected to database via: {connection_string.split('@')[-1] if '@' in connection_string else 'SQLite'}")
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            self.engine = None
            self.connection_string = None
            return False

    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """Get list of tables from the connected database.
           For PostgreSQL, schema defaults to 'public' if not provided.
        """
        if not self.engine:
            print("Cannot get tables: No database connection.")
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
            print(f"Error getting tables: {e}")
            return []

    def get_table_schema(self, table_name: str, schema: Optional[str] = None) -> pd.DataFrame:
        """Get schema (columns and types) of a table"""
        if not self.engine:
            print("Cannot get table schema: No database connection.")
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
            print(f"Error getting table schema for {schema}.{table_name if schema else table_name}: {e}")
            return pd.DataFrame()

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute a custom SQL query and return a DataFrame"""
        if not self.engine:
            print("Cannot execute query: No database connection established.")
            return pd.DataFrame()
        try:
            df = pd.read_sql_query(text(query), self.engine) # Use text() for literal SQL
            print(f"Query executed successfully, {len(df)} rows returned.")
            return df
        except Exception as e:
            print(f"Error executing query: {e}")
            return pd.DataFrame()

    def get_table_sample(self, table_name: str, schema: Optional[str] = None, sample_size: int = 100) -> pd.DataFrame:
        """Get a sample of data from a table"""
        if not self.engine:
            print("Cannot get table sample: No database connection.")
            return pd.DataFrame()

        # Handle schema.table format if passed directly
        if '.' in table_name and not schema:
            schema, table_name = table_name.split('.', 1)
        
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
            
            print(f"Sampling query: {query}")
            df = pd.read_sql_query(text(query), self.engine)
            print(f"Table sample loaded for {table_ref}, {len(df)} rows.")
            return df
        except Exception as e:
            print(f"Error getting table sample with specific method: {e}")
            # Fallback para um LIMIT simples se o método específico falhar
            try:
                table_ref_fallback = f'"{table_name}"' # Ou ajuste conforme necessário
                query_fallback = f"SELECT * FROM {table_ref_fallback} LIMIT {sample_size}"
                print(f"Fallback sampling query: {query_fallback}")
                df = pd.read_sql_query(text(query_fallback), self.engine)
                print(f"Table sample (fallback) loaded for {table_ref_fallback}, {len(df)} rows.")
                return df
            except Exception as e2:
                print(f"Error getting table sample (fallback): {e2}")
                return pd.DataFrame()

    def close_connection(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.connection_string = None
            print("Database connection closed.")