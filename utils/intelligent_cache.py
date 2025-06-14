# -*- coding: utf-8 -*-
"""
Intelligent Cache - Cache Inteligente
Sistema de cache avançado com estratégias de invalidação e otimização automática
"""

import json
import pickle
import hashlib
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import redis
from collections import OrderedDict, defaultdict
import weakref
import gc

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager

class CacheStrategy(Enum):
    """Estratégias de cache"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptativo baseado em padrões
    PRIORITY = "priority"  # Baseado em prioridade

class CacheLevel(Enum):
    """Níveis de cache"""
    MEMORY = "memory"      # Cache em memória
    DISK = "disk"          # Cache em disco
    REDIS = "redis"        # Cache Redis
    HYBRID = "hybrid"      # Cache híbrido

class Priority(Enum):
    """Prioridades de cache"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class CacheEntry:
    """Entrada do cache"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl: Optional[int] = None  # segundos
    priority: Priority = Priority.MEDIUM
    size: int = 0  # bytes
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.size == 0:
            self.size = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Calcula tamanho aproximado da entrada"""
        try:
            return len(pickle.dumps(self.value))
        except:
            return len(str(self.value).encode('utf-8'))
    
    def is_expired(self) -> bool:
        """Verifica se entrada expirou"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    def update_access(self):
        """Atualiza informações de acesso"""
        self.last_accessed = datetime.now()
        self.access_count += 1

@dataclass
class CacheStats:
    """Estatísticas do cache"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    avg_access_time: float = 0.0
    memory_usage: int = 0
    
    def calculate_hit_rate(self):
        """Calcula taxa de acerto"""
        total = self.hits + self.misses
        self.hit_rate = (self.hits / total * 100) if total > 0 else 0.0

class LRUCache:
    """Cache LRU (Least Recently Used)"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Obtém entrada do cache"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                # Move para o final (mais recente)
                self.cache.move_to_end(key)
                entry.update_access()
                return entry
            return None
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Adiciona entrada ao cache"""
        with self.lock:
            if key in self.cache:
                self.cache[key] = entry
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # Remove o menos recente
                    self.cache.popitem(last=False)
                self.cache[key] = entry
            return True
    
    def remove(self, key: str) -> bool:
        """Remove entrada do cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Limpa o cache"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """Retorna número de entradas"""
        return len(self.cache)
    
    def keys(self) -> List[str]:
        """Retorna chaves do cache"""
        with self.lock:
            return list(self.cache.keys())

class LFUCache:
    """Cache LFU (Least Frequently Used)"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.frequencies = defaultdict(int)
        self.freq_to_keys = defaultdict(set)
        self.min_freq = 0
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Obtém entrada do cache"""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            self._update_frequency(key)
            entry.update_access()
            return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Adiciona entrada ao cache"""
        with self.lock:
            if key in self.cache:
                self.cache[key] = entry
                self._update_frequency(key)
                return True
            
            if len(self.cache) >= self.max_size:
                self._evict()
            
            self.cache[key] = entry
            self.frequencies[key] = 1
            self.freq_to_keys[1].add(key)
            self.min_freq = 1
            return True
    
    def _update_frequency(self, key: str):
        """Atualiza frequência de acesso"""
        freq = self.frequencies[key]
        self.freq_to_keys[freq].remove(key)
        
        if not self.freq_to_keys[freq] and freq == self.min_freq:
            self.min_freq += 1
        
        self.frequencies[key] += 1
        self.freq_to_keys[freq + 1].add(key)
    
    def _evict(self):
        """Remove entrada menos frequente"""
        key_to_remove = self.freq_to_keys[self.min_freq].pop()
        del self.cache[key_to_remove]
        del self.frequencies[key_to_remove]
    
    def remove(self, key: str) -> bool:
        """Remove entrada do cache"""
        with self.lock:
            if key not in self.cache:
                return False
            
            freq = self.frequencies[key]
            self.freq_to_keys[freq].remove(key)
            del self.cache[key]
            del self.frequencies[key]
            return True
    
    def clear(self):
        """Limpa o cache"""
        with self.lock:
            self.cache.clear()
            self.frequencies.clear()
            self.freq_to_keys.clear()
            self.min_freq = 0
    
    def size(self) -> int:
        """Retorna número de entradas"""
        return len(self.cache)
    
    def keys(self) -> List[str]:
        """Retorna chaves do cache"""
        with self.lock:
            return list(self.cache.keys())

class DiskCache:
    """Cache em disco usando SQLite"""
    
    def __init__(self, db_path: str = "cache.db", max_size_mb: int = 100):
        self.db_path = db_path
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Inicializa banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at TIMESTAMP,
                    last_accessed TIMESTAMP,
                    access_count INTEGER,
                    ttl INTEGER,
                    priority INTEGER,
                    size INTEGER,
                    tags TEXT,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed 
                ON cache_entries(last_accessed)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON cache_entries(created_at)
            """)
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Obtém entrada do cache"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM cache_entries WHERE key = ?",
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    # Deserializa valor
                    value = pickle.loads(row['value'])
                    
                    # Cria entrada
                    entry = CacheEntry(
                        key=row['key'],
                        value=value,
                        created_at=datetime.fromisoformat(row['created_at']),
                        last_accessed=datetime.fromisoformat(row['last_accessed']),
                        access_count=row['access_count'],
                        ttl=row['ttl'],
                        priority=Priority(row['priority']),
                        size=row['size'],
                        tags=json.loads(row['tags']) if row['tags'] else [],
                        metadata=json.loads(row['metadata']) if row['metadata'] else {}
                    )
                    
                    # Verifica expiração
                    if entry.is_expired():
                        self.remove(key)
                        return None
                    
                    # Atualiza acesso
                    entry.update_access()
                    self._update_access(key, entry)
                    
                    return entry
                    
            except Exception as e:
                log_error(f"Erro ao obter do cache em disco: {e}")
                return None
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Adiciona entrada ao cache"""
        with self.lock:
            try:
                # Verifica espaço disponível
                if self._get_total_size() + entry.size > self.max_size_bytes:
                    self._cleanup()
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_entries 
                        (key, value, created_at, last_accessed, access_count, 
                         ttl, priority, size, tags, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.key,
                        pickle.dumps(entry.value),
                        entry.created_at.isoformat(),
                        entry.last_accessed.isoformat(),
                        entry.access_count,
                        entry.ttl,
                        entry.priority.value,
                        entry.size,
                        json.dumps(entry.tags),
                        json.dumps(entry.metadata)
                    ))
                
                return True
                
            except Exception as e:
                log_error(f"Erro ao salvar no cache em disco: {e}")
                return False
    
    def _update_access(self, key: str, entry: CacheEntry):
        """Atualiza informações de acesso"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE cache_entries SET last_accessed = ?, access_count = ? WHERE key = ?",
                    (entry.last_accessed.isoformat(), entry.access_count, key)
                )
        except Exception as e:
            log_error(f"Erro ao atualizar acesso: {e}")
    
    def remove(self, key: str) -> bool:
        """Remove entrada do cache"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM cache_entries WHERE key = ?",
                        (key,)
                    )
                    return cursor.rowcount > 0
            except Exception as e:
                log_error(f"Erro ao remover do cache: {e}")
                return False
    
    def clear(self):
        """Limpa o cache"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM cache_entries")
            except Exception as e:
                log_error(f"Erro ao limpar cache: {e}")
    
    def _get_total_size(self) -> int:
        """Retorna tamanho total do cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(size) FROM cache_entries")
                result = cursor.fetchone()[0]
                return result if result else 0
        except Exception as e:
            log_error(f"Erro ao calcular tamanho do cache: {e}")
            return 0
    
    def _cleanup(self):
        """Remove entradas antigas para liberar espaço"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remove entradas expiradas
                conn.execute(
                    "DELETE FROM cache_entries WHERE ttl IS NOT NULL AND "
                    "(julianday('now') - julianday(created_at)) * 86400 > ttl"
                )
                
                # Remove 25% das entradas menos acessadas
                conn.execute("""
                    DELETE FROM cache_entries WHERE key IN (
                        SELECT key FROM cache_entries 
                        ORDER BY last_accessed ASC 
                        LIMIT (SELECT COUNT(*) / 4 FROM cache_entries)
                    )
                """)
        except Exception as e:
            log_error(f"Erro na limpeza do cache: {e}")
    
    def size(self) -> int:
        """Retorna número de entradas"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
                return cursor.fetchone()[0]
        except Exception as e:
            log_error(f"Erro ao contar entradas: {e}")
            return 0
    
    def keys(self) -> List[str]:
        """Retorna chaves do cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT key FROM cache_entries")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            log_error(f"Erro ao obter chaves: {e}")
            return []

class RedisCache:
    """Cache Redis"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: str = None, prefix: str = 'cache:'):
        self.prefix = prefix
        try:
            import redis
            self.redis_client = redis.Redis(
                host=host, port=port, db=db, password=password,
                decode_responses=False
            )
            # Testa conexão
            self.redis_client.ping()
            self.available = True
        except Exception as e:
            log_warning(f"Redis não disponível: {e}")
            self.redis_client = None
            self.available = False
    
    def _make_key(self, key: str) -> str:
        """Cria chave com prefixo"""
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Obtém entrada do cache"""
        if not self.available:
            return None
        
        try:
            redis_key = self._make_key(key)
            data = self.redis_client.get(redis_key)
            
            if not data:
                return None
            
            entry = pickle.loads(data)
            
            # Verifica expiração
            if entry.is_expired():
                self.remove(key)
                return None
            
            # Atualiza acesso
            entry.update_access()
            self.redis_client.set(redis_key, pickle.dumps(entry))
            
            return entry
            
        except Exception as e:
            log_error(f"Erro ao obter do Redis: {e}")
            return None
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Adiciona entrada ao cache"""
        if not self.available:
            return False
        
        try:
            redis_key = self._make_key(key)
            data = pickle.dumps(entry)
            
            if entry.ttl:
                self.redis_client.setex(redis_key, entry.ttl, data)
            else:
                self.redis_client.set(redis_key, data)
            
            return True
            
        except Exception as e:
            log_error(f"Erro ao salvar no Redis: {e}")
            return False
    
    def remove(self, key: str) -> bool:
        """Remove entrada do cache"""
        if not self.available:
            return False
        
        try:
            redis_key = self._make_key(key)
            return self.redis_client.delete(redis_key) > 0
        except Exception as e:
            log_error(f"Erro ao remover do Redis: {e}")
            return False
    
    def clear(self):
        """Limpa o cache"""
        if not self.available:
            return
        
        try:
            pattern = f"{self.prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            log_error(f"Erro ao limpar Redis: {e}")
    
    def size(self) -> int:
        """Retorna número de entradas"""
        if not self.available:
            return 0
        
        try:
            pattern = f"{self.prefix}*"
            return len(self.redis_client.keys(pattern))
        except Exception as e:
            log_error(f"Erro ao contar entradas Redis: {e}")
            return 0
    
    def keys(self) -> List[str]:
        """Retorna chaves do cache"""
        if not self.available:
            return []
        
        try:
            pattern = f"{self.prefix}*"
            redis_keys = self.redis_client.keys(pattern)
            return [key.decode('utf-8').replace(self.prefix, '') for key in redis_keys]
        except Exception as e:
            log_error(f"Erro ao obter chaves Redis: {e}")
            return []

class IntelligentCache:
    """Cache inteligente com múltiplas estratégias e níveis"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.strategy = CacheStrategy(self.config.get('strategy', 'adaptive'))
        self.levels = self.config.get('levels', ['memory', 'disk'])
        
        # Inicializa caches por nível
        self.caches = {}
        self._init_caches()
        
        # Estatísticas
        self.stats = CacheStats()
        
        # Configurações
        self.max_memory_size = self.config.get('max_memory_size', 1000)
        self.max_disk_size_mb = self.config.get('max_disk_size_mb', 100)
        self.default_ttl = self.config.get('default_ttl', 3600)  # 1 hora
        
        # Thread para limpeza automática
        self.cleanup_interval = self.config.get('cleanup_interval', 300)  # 5 minutos
        self.cleanup_thread = None
        self.running = True
        
        self._start_cleanup_thread()
        
        log_info(f"Cache inteligente inicializado com estratégia {self.strategy.value}")
    
    def _init_caches(self):
        """Inicializa caches por nível"""
        for level in self.levels:
            if level == 'memory':
                if self.strategy == CacheStrategy.LRU:
                    self.caches[level] = LRUCache(self.max_memory_size)
                elif self.strategy == CacheStrategy.LFU:
                    self.caches[level] = LFUCache(self.max_memory_size)
                else:
                    self.caches[level] = LRUCache(self.max_memory_size)
            
            elif level == 'disk':
                db_path = self.config.get('disk_cache_path', 'intelligent_cache.db')
                self.caches[level] = DiskCache(db_path, self.max_disk_size_mb)
            
            elif level == 'redis':
                redis_config = self.config.get('redis', {})
                self.caches[level] = RedisCache(**redis_config)
    
    def _start_cleanup_thread(self):
        """Inicia thread de limpeza automática"""
        def cleanup_worker():
            while self.running:
                try:
                    time.sleep(self.cleanup_interval)
                    if self.running:
                        self._cleanup_expired()
                        self._optimize_cache()
                except Exception as e:
                    log_error(f"Erro na limpeza automática: {e}")
        
        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor do cache"""
        start_time = time.time()
        
        try:
            # Procura nos níveis em ordem
            for level in self.levels:
                cache = self.caches.get(level)
                if not cache:
                    continue
                
                entry = cache.get(key)
                if entry:
                    self.stats.hits += 1
                    
                    # Promove para níveis superiores se necessário
                    self._promote_entry(key, entry, level)
                    
                    # Atualiza estatísticas
                    access_time = time.time() - start_time
                    self._update_access_stats(access_time)
                    
                    return entry.value
            
            # Cache miss
            self.stats.misses += 1
            self.stats.calculate_hit_rate()
            
            return default
            
        except Exception as e:
            log_error(f"Erro ao obter do cache: {e}")
            self.stats.misses += 1
            return default
    
    def put(self, key: str, value: Any, ttl: int = None, 
           priority: Priority = Priority.MEDIUM, tags: List[str] = None) -> bool:
        """Adiciona valor ao cache"""
        try:
            # Cria entrada
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                ttl=ttl or self.default_ttl,
                priority=priority,
                tags=tags or []
            )
            
            # Adiciona em todos os níveis configurados
            success = False
            for level in self.levels:
                cache = self.caches.get(level)
                if cache and cache.put(key, entry):
                    success = True
            
            if success:
                self.stats.entry_count += 1
                self.stats.total_size += entry.size
            
            return success
            
        except Exception as e:
            log_error(f"Erro ao adicionar ao cache: {e}")
            return False
    
    def remove(self, key: str) -> bool:
        """Remove entrada do cache"""
        try:
            success = False
            for level in self.levels:
                cache = self.caches.get(level)
                if cache and cache.remove(key):
                    success = True
            
            if success:
                self.stats.entry_count = max(0, self.stats.entry_count - 1)
            
            return success
            
        except Exception as e:
            log_error(f"Erro ao remover do cache: {e}")
            return False
    
    def clear(self, tags: List[str] = None):
        """Limpa cache (opcionalmente por tags)"""
        try:
            if tags:
                # Remove apenas entradas com tags específicas
                self._clear_by_tags(tags)
            else:
                # Limpa tudo
                for cache in self.caches.values():
                    if cache:
                        cache.clear()
                
                self.stats = CacheStats()
            
        except Exception as e:
            log_error(f"Erro ao limpar cache: {e}")
    
    def _promote_entry(self, key: str, entry: CacheEntry, current_level: str):
        """Promove entrada para níveis superiores"""
        try:
            level_priority = {'memory': 0, 'redis': 1, 'disk': 2}
            current_priority = level_priority.get(current_level, 999)
            
            # Promove para níveis com prioridade menor (mais rápidos)
            for level in self.levels:
                if level_priority.get(level, 999) < current_priority:
                    cache = self.caches.get(level)
                    if cache:
                        cache.put(key, entry)
                        
        except Exception as e:
            log_error(f"Erro ao promover entrada: {e}")
    
    def _cleanup_expired(self):
        """Remove entradas expiradas"""
        try:
            for level, cache in self.caches.items():
                if not cache:
                    continue
                
                keys_to_remove = []
                
                for key in cache.keys():
                    entry = cache.get(key)
                    if entry and entry.is_expired():
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    cache.remove(key)
                    self.stats.evictions += 1
                
                if keys_to_remove:
                    log_info(f"Removidas {len(keys_to_remove)} entradas expiradas do {level}")
                    
        except Exception as e:
            log_error(f"Erro na limpeza de expirados: {e}")
    
    def _optimize_cache(self):
        """Otimiza cache baseado em padrões de uso"""
        try:
            if self.strategy == CacheStrategy.ADAPTIVE:
                self._adaptive_optimization()
            
            # Força garbage collection
            gc.collect()
            
        except Exception as e:
            log_error(f"Erro na otimização: {e}")
    
    def _adaptive_optimization(self):
        """Otimização adaptativa baseada em padrões"""
        try:
            # Analisa padrões de acesso
            if self.stats.hit_rate < 50:  # Taxa de acerto baixa
                # Aumenta TTL padrão
                self.default_ttl = min(self.default_ttl * 1.2, 7200)
                log_info("TTL aumentado devido à baixa taxa de acerto")
            
            elif self.stats.hit_rate > 90:  # Taxa de acerto alta
                # Diminui TTL para liberar espaço
                self.default_ttl = max(self.default_ttl * 0.9, 300)
                log_info("TTL diminuído devido à alta taxa de acerto")
            
        except Exception as e:
            log_error(f"Erro na otimização adaptativa: {e}")
    
    def _clear_by_tags(self, tags: List[str]):
        """Remove entradas por tags"""
        try:
            for cache in self.caches.values():
                if not cache:
                    continue
                
                keys_to_remove = []
                
                for key in cache.keys():
                    entry = cache.get(key)
                    if entry and any(tag in entry.tags for tag in tags):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    cache.remove(key)
                    
        except Exception as e:
            log_error(f"Erro ao limpar por tags: {e}")
    
    def _update_access_stats(self, access_time: float):
        """Atualiza estatísticas de acesso"""
        try:
            # Média móvel do tempo de acesso
            if self.stats.avg_access_time == 0:
                self.stats.avg_access_time = access_time
            else:
                self.stats.avg_access_time = (
                    self.stats.avg_access_time * 0.9 + access_time * 0.1
                )
            
            self.stats.calculate_hit_rate()
            
        except Exception as e:
            log_error(f"Erro ao atualizar estatísticas: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        try:
            # Atualiza contadores
            total_entries = sum(cache.size() for cache in self.caches.values() if cache)
            self.stats.entry_count = total_entries
            
            # Calcula uso de memória
            import psutil
            process = psutil.Process()
            self.stats.memory_usage = process.memory_info().rss
            
            return {
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'hit_rate': round(self.stats.hit_rate, 2),
                'evictions': self.stats.evictions,
                'entry_count': self.stats.entry_count,
                'total_size': self.stats.total_size,
                'avg_access_time': round(self.stats.avg_access_time * 1000, 2),  # ms
                'memory_usage_mb': round(self.stats.memory_usage / 1024 / 1024, 2),
                'strategy': self.strategy.value,
                'levels': self.levels,
                'cache_sizes': {
                    level: cache.size() for level, cache in self.caches.items() if cache
                }
            }
            
        except Exception as e:
            log_error(f"Erro ao obter estatísticas: {e}")
            return {'error': str(e)}
    
    def shutdown(self):
        """Finaliza cache"""
        try:
            self.running = False
            
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                self.cleanup_thread.join(timeout=5)
            
            log_info("Cache inteligente finalizado")
            
        except Exception as e:
            log_error(f"Erro ao finalizar cache: {e}")
    
    def __del__(self):
        """Destrutor"""
        self.shutdown()

# Instância global do cache
_global_cache = None

def get_cache(config: Dict[str, Any] = None) -> IntelligentCache:
    """Retorna instância global do cache"""
    global _global_cache
    
    if _global_cache is None:
        _global_cache = IntelligentCache(config)
    
    return _global_cache

def cache_result(ttl: int = None, tags: List[str] = None, 
                priority: Priority = Priority.MEDIUM):
    """Decorator para cache de resultados de função"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Gera chave baseada na função e argumentos
            key_data = {
                'function': func.__name__,
                'module': func.__module__,
                'args': args,
                'kwargs': kwargs
            }
            
            key = hashlib.md5(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            
            cache = get_cache()
            
            # Tenta obter do cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Executa função e armazena resultado
            result = func(*args, **kwargs)
            cache.put(key, result, ttl=ttl, priority=priority, tags=tags)
            
            return result
        
        return wrapper
    return decorator