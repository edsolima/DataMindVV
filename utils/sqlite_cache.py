# utils/sqlite_cache.py
import os
import pickle
import sqlite3
import time
from flask_caching.backends.base import BaseCache
from utils.logger import log_info, log_error

class SQLiteCache(BaseCache):
    """
    SQLite backend para Flask-Caching.
    
    Este backend armazena os dados de cache em um banco de dados SQLite,
    permitindo persistência entre reinicializações do servidor e melhor
    gerenciamento do cache.
    """
    
    def __init__(self, config):
        """
        Inicializa o SQLiteCache com as configurações fornecidas.
        Cria o banco de dados e a tabela de cache se necessário.
        """
        super(SQLiteCache, self).__init__(config)
        self.config = config
        self.default_timeout = config.get('CACHE_DEFAULT_TIMEOUT', 300)
        
        # Obter o caminho do banco de dados SQLite
        db_path = config.get('CACHE_SQLITE_PATH')
        if not db_path:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, 'cache.sqlite')
        
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self):
        """
        Inicializa o banco de dados SQLite com a tabela necessária para o cache.
        Cria índices para performance.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Criar tabela de cache se não existir
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_entries (
            key TEXT PRIMARY KEY,
            value BLOB,
            expiry FLOAT
        )
        """)
        
        # Criar índice para melhorar a performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expiry ON cache_entries(expiry)")
        
        conn.commit()
        conn.close()
        
        log_info(f"SQLiteCache inicializado em: {self.db_path}")
    
    def _get_conn(self):
        """
        Retorna uma conexão com o banco de dados SQLite.
        """
        return sqlite3.connect(self.db_path)
    
    def get(self, key):
        """
        Recupera um item do cache pelo key.
        Retorna o valor desserializado ou None se não existir ou estiver expirado.
        """
        key = str(key)
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT value, expiry FROM cache_entries WHERE key = ?",
                (key,)
            )
            result = cursor.fetchone()
            log_info(f"[SQLiteCache:get] db_path={self.db_path} | key={key} | select_result={'None' if result is None else 'OK'} | file_size={os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 'N/A'} bytes")
            if result is None:
                return None
            
            value, expiry = result
            
            # Verificar se o item expirou
            if expiry != 0 and expiry < time.time():
                self.delete(key)  # Remover item expirado
                return None
            
            return pickle.loads(value)
        
        except Exception as e:
            log_error(f"Erro ao recuperar do cache SQLite:", exception=e)
            return None
        
        finally:
            conn.close()
    
    def set(self, key, value, timeout=None):
        """
        Armazena um item no cache com a chave e timeout especificados.
        Serializa o valor com pickle.
        """
        key = str(key)
        timeout = self.default_timeout if timeout is None else timeout
        
        # Calcular o tempo de expiração
        expiry = 0 if timeout == 0 else time.time() + timeout
        
        # Serializar o valor
        try:
            value_pickle = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            log_error(f"Erro ao serializar valor para cache SQLite:", exception=e)
            return False
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "REPLACE INTO cache_entries (key, value, expiry) VALUES (?, ?, ?)",
                (key, value_pickle, expiry)
            )
            conn.commit()
            file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 'N/A'
            log_info(f"[SQLiteCache:set] db_path={self.db_path} | key={key} | file_size={file_size} bytes | value_type={type(value)}")
            return True
        
        except Exception as e:
            log_error(f"Erro ao armazenar no cache SQLite:", exception=e)
            conn.rollback()
            return False
        
        finally:
            conn.close()
    
    def delete(self, key):
        """
        Remove um item do cache pelo key.
        """
        key = str(key)
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            conn.commit()
            return True
        
        except Exception as e:
            log_error(f"Erro ao excluir do cache SQLite:", exception=e)
            conn.rollback()
            return False
        
        finally:
            conn.close()
    
    def has(self, key):
        """
        Verifica se um item existe no cache e não está expirado.
        Retorna True se existir, False caso contrário.
        """
        return self.get(key) is not None
    
    def clear(self):
        """
        Limpa todos os itens do cache.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM cache_entries")
            conn.commit()
            return True
        
        except Exception as e:
            log_error(f"Erro ao limpar cache SQLite:", exception=e)
            conn.rollback()
            return False
        
        finally:
            conn.close()
    
    def cleanup(self):
        """
        Remove todos os itens expirados do cache.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "DELETE FROM cache_entries WHERE expiry > 0 AND expiry < ?",
                (time.time(),)
            )
            conn.commit()
            return True
        
        except Exception as e:
            log_error(f"Erro na limpeza do cache SQLite:", exception=e)
            conn.rollback()
            return False
        
        finally:
            conn.close()