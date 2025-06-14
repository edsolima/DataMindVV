# -*- coding: utf-8 -*-
"""
Audit System - Sistema de Auditoria
Sistema completo de auditoria e logs para rastreamento de ações
"""

import json
import hashlib
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import inspect
import traceback
import os
import gzip
import shutil
from pathlib import Path

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager

class ActionType(Enum):
    """Tipos de ação"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    SHARE = "share"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    EXECUTE = "execute"
    CONFIGURE = "configure"
    ADMIN = "admin"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CUSTOM = "custom"

class Severity(Enum):
    """Níveis de severidade"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditStatus(Enum):
    """Status da auditoria"""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    CANCELLED = "cancelled"

@dataclass
class AuditEntry:
    """Entrada de auditoria"""
    id: str
    timestamp: datetime
    user_id: str
    session_id: str
    action_type: ActionType
    resource_type: str
    resource_id: str
    description: str
    status: AuditStatus
    severity: Severity
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class SecurityEvent:
    """Evento de segurança"""
    id: str
    timestamp: datetime
    event_type: str
    user_id: str
    ip_address: str
    description: str
    severity: Severity
    details: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

@dataclass
class ComplianceReport:
    """Relatório de conformidade"""
    id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_actions: int
    failed_actions: int
    security_events: int
    compliance_score: float
    violations: List[Dict[str, Any]]
    recommendations: List[str]

class AuditLogger:
    """Logger de auditoria"""
    
    def __init__(self, db_path: str = "audit.db", log_dir: str = "audit_logs"):
        self.db_path = db_path
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.lock = threading.RLock()
        self._init_db()
        
        # Configurações
        self.max_log_size_mb = 100
        self.retention_days = 365
        self.compress_after_days = 30
    
    def _init_db(self):
        """Inicializa banco de dados"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Tabela de auditoria
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_entries (
                        id TEXT PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        description TEXT NOT NULL,
                        status TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        ip_address TEXT,
                        user_agent TEXT,
                        details TEXT,
                        before_state TEXT,
                        after_state TEXT,
                        duration_ms REAL,
                        error_message TEXT,
                        stack_trace TEXT,
                        tags TEXT
                    )
                """)
                
                # Tabela de eventos de segurança
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS security_events (
                        id TEXT PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        event_type TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        ip_address TEXT,
                        description TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        details TEXT,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolved_at TIMESTAMP,
                        resolved_by TEXT
                    )
                """)
                
                # Tabela de sessões
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        ip_address TEXT,
                        user_agent TEXT,
                        active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Índices
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                    ON audit_entries(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_user_action 
                    ON audit_entries(user_id, action_type)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_security_timestamp 
                    ON security_events(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_user 
                    ON user_sessions(user_id)
                """)
                
        except Exception as e:
            log_error(f"Erro ao inicializar banco de auditoria: {e}")
    
    def log_action(self, entry: AuditEntry) -> bool:
        """Registra ação de auditoria"""
        with self.lock:
            try:
                # Salva no banco
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO audit_entries 
                        (id, timestamp, user_id, session_id, action_type, 
                         resource_type, resource_id, description, status, severity,
                         ip_address, user_agent, details, before_state, after_state,
                         duration_ms, error_message, stack_trace, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.id,
                        entry.timestamp.isoformat(),
                        entry.user_id,
                        entry.session_id,
                        entry.action_type.value,
                        entry.resource_type,
                        entry.resource_id,
                        entry.description,
                        entry.status.value,
                        entry.severity.value,
                        entry.ip_address,
                        entry.user_agent,
                        json.dumps(entry.details, default=str),
                        json.dumps(entry.before_state, default=str) if entry.before_state else None,
                        json.dumps(entry.after_state, default=str) if entry.after_state else None,
                        entry.duration_ms,
                        entry.error_message,
                        entry.stack_trace,
                        json.dumps(entry.tags)
                    ))
                
                # Salva em arquivo de log
                self._write_log_file(entry)
                
                return True
                
            except Exception as e:
                log_error(f"Erro ao registrar auditoria: {e}")
                return False
    
    def log_security_event(self, event: SecurityEvent) -> bool:
        """Registra evento de segurança"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO security_events 
                        (id, timestamp, event_type, user_id, ip_address, 
                         description, severity, details, resolved, resolved_at, resolved_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.id,
                        event.timestamp.isoformat(),
                        event.event_type,
                        event.user_id,
                        event.ip_address,
                        event.description,
                        event.severity.value,
                        json.dumps(event.details, default=str),
                        event.resolved,
                        event.resolved_at.isoformat() if event.resolved_at else None,
                        event.resolved_by
                    ))
                
                return True
                
            except Exception as e:
                log_error(f"Erro ao registrar evento de segurança: {e}")
                return False
    
    def _write_log_file(self, entry: AuditEntry):
        """Escreve entrada em arquivo de log"""
        try:
            # Nome do arquivo baseado na data
            log_file = self.log_dir / f"audit_{entry.timestamp.strftime('%Y%m%d')}.log"
            
            # Linha do log
            log_line = {
                'timestamp': entry.timestamp.isoformat(),
                'user_id': entry.user_id,
                'action': entry.action_type.value,
                'resource': f"{entry.resource_type}:{entry.resource_id}",
                'status': entry.status.value,
                'severity': entry.severity.value,
                'description': entry.description,
                'ip': entry.ip_address,
                'duration_ms': entry.duration_ms
            }
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_line, ensure_ascii=False) + '\n')
            
            # Verifica se precisa comprimir
            self._check_log_rotation(log_file)
            
        except Exception as e:
            log_error(f"Erro ao escrever arquivo de log: {e}")
    
    def _check_log_rotation(self, log_file: Path):
        """Verifica se precisa fazer rotação/compressão do log"""
        try:
            if not log_file.exists():
                return
            
            # Verifica tamanho
            size_mb = log_file.stat().st_size / 1024 / 1024
            
            if size_mb > self.max_log_size_mb:
                # Comprime arquivo
                compressed_file = log_file.with_suffix('.log.gz')
                
                with open(log_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove arquivo original
                log_file.unlink()
                
                log_info(f"Log comprimido: {compressed_file}")
            
        except Exception as e:
            log_error(f"Erro na rotação de logs: {e}")
    
    def get_audit_entries(self, 
                         user_id: str = None,
                         action_type: ActionType = None,
                         start_date: datetime = None,
                         end_date: datetime = None,
                         limit: int = 1000) -> List[AuditEntry]:
        """Obtém entradas de auditoria"""
        try:
            query = "SELECT * FROM audit_entries WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type.value)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                
                entries = []
                for row in cursor.fetchall():
                    entry = AuditEntry(
                        id=row['id'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        action_type=ActionType(row['action_type']),
                        resource_type=row['resource_type'],
                        resource_id=row['resource_id'],
                        description=row['description'],
                        status=AuditStatus(row['status']),
                        severity=Severity(row['severity']),
                        ip_address=row['ip_address'],
                        user_agent=row['user_agent'],
                        details=json.loads(row['details']) if row['details'] else {},
                        before_state=json.loads(row['before_state']) if row['before_state'] else None,
                        after_state=json.loads(row['after_state']) if row['after_state'] else None,
                        duration_ms=row['duration_ms'],
                        error_message=row['error_message'],
                        stack_trace=row['stack_trace'],
                        tags=json.loads(row['tags']) if row['tags'] else []
                    )
                    entries.append(entry)
                
                return entries
                
        except Exception as e:
            log_error(f"Erro ao obter entradas de auditoria: {e}")
            return []
    
    def get_security_events(self, 
                           resolved: bool = None,
                           severity: Severity = None,
                           limit: int = 100) -> List[SecurityEvent]:
        """Obtém eventos de segurança"""
        try:
            query = "SELECT * FROM security_events WHERE 1=1"
            params = []
            
            if resolved is not None:
                query += " AND resolved = ?"
                params.append(resolved)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity.value)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                
                events = []
                for row in cursor.fetchall():
                    event = SecurityEvent(
                        id=row['id'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        event_type=row['event_type'],
                        user_id=row['user_id'],
                        ip_address=row['ip_address'],
                        description=row['description'],
                        severity=Severity(row['severity']),
                        details=json.loads(row['details']) if row['details'] else {},
                        resolved=bool(row['resolved']),
                        resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None,
                        resolved_by=row['resolved_by']
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            log_error(f"Erro ao obter eventos de segurança: {e}")
            return []
    
    def cleanup_old_entries(self, days: int = None):
        """Remove entradas antigas"""
        try:
            days = days or self.retention_days
            cutoff = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                # Remove entradas de auditoria
                cursor = conn.execute(
                    "DELETE FROM audit_entries WHERE timestamp < ?",
                    (cutoff.isoformat(),)
                )
                deleted_audit = cursor.rowcount
                
                # Remove eventos de segurança resolvidos
                cursor = conn.execute(
                    "DELETE FROM security_events WHERE timestamp < ? AND resolved = TRUE",
                    (cutoff.isoformat(),)
                )
                deleted_security = cursor.rowcount
                
                log_info(f"Limpeza: {deleted_audit} entradas de auditoria e {deleted_security} eventos de segurança removidos")
            
            # Remove arquivos de log antigos
            self._cleanup_log_files(days)
            
        except Exception as e:
            log_error(f"Erro na limpeza de auditoria: {e}")
    
    def _cleanup_log_files(self, days: int):
        """Remove arquivos de log antigos"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            for log_file in self.log_dir.glob("audit_*.log*"):
                # Extrai data do nome do arquivo
                try:
                    date_str = log_file.stem.split('_')[1][:8]  # YYYYMMDD
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff:
                        log_file.unlink()
                        log_info(f"Arquivo de log removido: {log_file}")
                        
                except (ValueError, IndexError):
                    continue
                    
        except Exception as e:
            log_error(f"Erro na limpeza de arquivos de log: {e}")

class AuditManager:
    """Gerenciador principal de auditoria"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Logger de auditoria
        db_path = self.config.get('db_path', 'audit.db')
        log_dir = self.config.get('log_dir', 'audit_logs')
        self.logger = AuditLogger(db_path, log_dir)
        
        # Configurações
        self.enabled = self.config.get('enabled', True)
        self.track_reads = self.config.get('track_reads', False)
        self.sensitive_fields = self.config.get('sensitive_fields', [
            'password', 'token', 'secret', 'key', 'credential'
        ])
        
        # Cache de sessões
        self.active_sessions = {}
        self.lock = threading.RLock()
        
        log_info("Sistema de auditoria inicializado")
    
    def start_session(self, user_id: str, ip_address: str = None, 
                     user_agent: str = None) -> str:
        """Inicia sessão de usuário"""
        try:
            session_id = self._generate_session_id(user_id)
            
            with self.lock:
                self.active_sessions[session_id] = {
                    'user_id': user_id,
                    'start_time': datetime.now(),
                    'ip_address': ip_address,
                    'user_agent': user_agent
                }
            
            # Registra no banco
            with sqlite3.connect(self.logger.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_sessions 
                    (session_id, user_id, start_time, ip_address, user_agent, active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    user_id,
                    datetime.now().isoformat(),
                    ip_address,
                    user_agent,
                    True
                ))
            
            # Log de auditoria
            self.log_action(
                user_id=user_id,
                session_id=session_id,
                action_type=ActionType.LOGIN,
                resource_type="session",
                resource_id=session_id,
                description="Usuário logado",
                status=AuditStatus.SUCCESS,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return session_id
            
        except Exception as e:
            log_error(f"Erro ao iniciar sessão: {e}")
            return None
    
    def end_session(self, session_id: str):
        """Finaliza sessão de usuário"""
        try:
            with self.lock:
                session_info = self.active_sessions.get(session_id)
                if session_info:
                    del self.active_sessions[session_id]
            
            if session_info:
                # Atualiza no banco
                with sqlite3.connect(self.logger.db_path) as conn:
                    conn.execute("""
                        UPDATE user_sessions 
                        SET end_time = ?, active = FALSE
                        WHERE session_id = ?
                    """, (datetime.now().isoformat(), session_id))
                
                # Log de auditoria
                self.log_action(
                    user_id=session_info['user_id'],
                    session_id=session_id,
                    action_type=ActionType.LOGOUT,
                    resource_type="session",
                    resource_id=session_id,
                    description="Usuário deslogado",
                    status=AuditStatus.SUCCESS,
                    ip_address=session_info.get('ip_address'),
                    user_agent=session_info.get('user_agent')
                )
                
        except Exception as e:
            log_error(f"Erro ao finalizar sessão: {e}")
    
    def log_action(self, 
                   user_id: str,
                   session_id: str,
                   action_type: ActionType,
                   resource_type: str,
                   resource_id: str,
                   description: str,
                   status: AuditStatus = AuditStatus.SUCCESS,
                   severity: Severity = Severity.LOW,
                   ip_address: str = None,
                   user_agent: str = None,
                   details: Dict[str, Any] = None,
                   before_state: Dict[str, Any] = None,
                   after_state: Dict[str, Any] = None,
                   duration_ms: float = None,
                   error_message: str = None,
                   tags: List[str] = None) -> bool:
        """Registra ação de auditoria"""
        
        if not self.enabled:
            return True
        
        # Filtra leituras se configurado
        if not self.track_reads and action_type == ActionType.READ:
            return True
        
        try:
            # Gera ID único
            entry_id = self._generate_entry_id(user_id, action_type, resource_id)
            
            # Remove campos sensíveis
            clean_details = self._sanitize_data(details or {})
            clean_before = self._sanitize_data(before_state or {})
            clean_after = self._sanitize_data(after_state or {})
            
            # Cria entrada
            entry = AuditEntry(
                id=entry_id,
                timestamp=datetime.now(),
                user_id=user_id,
                session_id=session_id,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                status=status,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                details=clean_details,
                before_state=clean_before if before_state else None,
                after_state=clean_after if after_state else None,
                duration_ms=duration_ms,
                error_message=error_message,
                stack_trace=traceback.format_exc() if error_message else None,
                tags=tags or []
            )
            
            return self.logger.log_action(entry)
            
        except Exception as e:
            log_error(f"Erro ao registrar ação de auditoria: {e}")
            return False
    
    def log_security_event(self,
                          event_type: str,
                          user_id: str,
                          description: str,
                          severity: Severity = Severity.MEDIUM,
                          ip_address: str = None,
                          details: Dict[str, Any] = None) -> bool:
        """Registra evento de segurança"""
        try:
            event_id = self._generate_event_id(event_type, user_id)
            
            event = SecurityEvent(
                id=event_id,
                timestamp=datetime.now(),
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                description=description,
                severity=severity,
                details=self._sanitize_data(details or {})
            )
            
            return self.logger.log_security_event(event)
            
        except Exception as e:
            log_error(f"Erro ao registrar evento de segurança: {e}")
            return False
    
    def _generate_session_id(self, user_id: str) -> str:
        """Gera ID de sessão"""
        data = f"{user_id}_{datetime.now().isoformat()}_{os.urandom(8).hex()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def _generate_entry_id(self, user_id: str, action_type: ActionType, resource_id: str) -> str:
        """Gera ID de entrada"""
        data = f"{user_id}_{action_type.value}_{resource_id}_{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def _generate_event_id(self, event_type: str, user_id: str) -> str:
        """Gera ID de evento"""
        data = f"{event_type}_{user_id}_{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove campos sensíveis dos dados"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        
        for key, value in data.items():
            # Verifica se é campo sensível
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def generate_compliance_report(self, 
                                  start_date: datetime,
                                  end_date: datetime) -> ComplianceReport:
        """Gera relatório de conformidade"""
        try:
            report_id = hashlib.sha256(
                f"compliance_{start_date.isoformat()}_{end_date.isoformat()}".encode()
            ).hexdigest()[:16]
            
            # Obtém dados do período
            entries = self.logger.get_audit_entries(
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )
            
            security_events = self.logger.get_security_events(limit=1000)
            period_events = [
                e for e in security_events 
                if start_date <= e.timestamp <= end_date
            ]
            
            # Calcula métricas
            total_actions = len(entries)
            failed_actions = len([e for e in entries if e.status == AuditStatus.FAILURE])
            security_count = len(period_events)
            
            # Calcula score de conformidade
            compliance_score = self._calculate_compliance_score(
                total_actions, failed_actions, security_count
            )
            
            # Identifica violações
            violations = self._identify_violations(entries, period_events)
            
            # Gera recomendações
            recommendations = self._generate_recommendations(violations)
            
            return ComplianceReport(
                id=report_id,
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                total_actions=total_actions,
                failed_actions=failed_actions,
                security_events=security_count,
                compliance_score=compliance_score,
                violations=violations,
                recommendations=recommendations
            )
            
        except Exception as e:
            log_error(f"Erro ao gerar relatório de conformidade: {e}")
            return None
    
    def _calculate_compliance_score(self, total: int, failed: int, security: int) -> float:
        """Calcula score de conformidade"""
        if total == 0:
            return 100.0
        
        # Score baseado em taxa de sucesso e eventos de segurança
        success_rate = ((total - failed) / total) * 100
        security_penalty = min(security * 5, 50)  # Máximo 50 pontos de penalidade
        
        score = max(0, success_rate - security_penalty)
        return round(score, 2)
    
    def _identify_violations(self, entries: List[AuditEntry], 
                           events: List[SecurityEvent]) -> List[Dict[str, Any]]:
        """Identifica violações de conformidade"""
        violations = []
        
        # Violações por falhas
        failed_entries = [e for e in entries if e.status == AuditStatus.FAILURE]
        if failed_entries:
            violations.append({
                'type': 'failed_actions',
                'count': len(failed_entries),
                'description': f"{len(failed_entries)} ações falharam",
                'severity': 'medium'
            })
        
        # Violações por eventos de segurança críticos
        critical_events = [e for e in events if e.severity == Severity.CRITICAL]
        if critical_events:
            violations.append({
                'type': 'critical_security_events',
                'count': len(critical_events),
                'description': f"{len(critical_events)} eventos de segurança críticos",
                'severity': 'high'
            })
        
        # Violações por acessos suspeitos
        suspicious_ips = self._detect_suspicious_activity(entries)
        if suspicious_ips:
            violations.append({
                'type': 'suspicious_activity',
                'count': len(suspicious_ips),
                'description': f"Atividade suspeita de {len(suspicious_ips)} IPs",
                'severity': 'high',
                'details': suspicious_ips
            })
        
        return violations
    
    def _detect_suspicious_activity(self, entries: List[AuditEntry]) -> List[str]:
        """Detecta atividade suspeita"""
        ip_activity = defaultdict(int)
        
        for entry in entries:
            if entry.ip_address:
                ip_activity[entry.ip_address] += 1
        
        # IPs com muita atividade (mais de 1000 ações)
        suspicious = [ip for ip, count in ip_activity.items() if count > 1000]
        
        return suspicious
    
    def _generate_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Gera recomendações baseadas em violações"""
        recommendations = []
        
        for violation in violations:
            if violation['type'] == 'failed_actions':
                recommendations.append(
                    "Investigar causas das falhas de ação e implementar melhorias"
                )
            
            elif violation['type'] == 'critical_security_events':
                recommendations.append(
                    "Revisar e resolver eventos de segurança críticos imediatamente"
                )
            
            elif violation['type'] == 'suspicious_activity':
                recommendations.append(
                    "Implementar rate limiting e monitoramento de IPs suspeitos"
                )
        
        if not violations:
            recommendations.append(
                "Sistema em conformidade. Manter monitoramento contínuo."
            )
        
        return recommendations
    
    def export_audit_data(self, filename: str, 
                         start_date: datetime = None,
                         end_date: datetime = None,
                         format: str = 'json'):
        """Exporta dados de auditoria"""
        try:
            entries = self.logger.get_audit_entries(
                start_date=start_date,
                end_date=end_date,
                limit=50000
            )
            
            if format.lower() == 'json':
                data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'period_start': start_date.isoformat() if start_date else None,
                    'period_end': end_date.isoformat() if end_date else None,
                    'total_entries': len(entries),
                    'entries': [asdict(entry) for entry in entries]
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            elif format.lower() == 'csv':
                import csv
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if entries:
                        writer = csv.DictWriter(f, fieldnames=asdict(entries[0]).keys())
                        writer.writeheader()
                        
                        for entry in entries:
                            row = asdict(entry)
                            # Converte objetos complexos para string
                            for key, value in row.items():
                                if isinstance(value, (dict, list)):
                                    row[key] = json.dumps(value, default=str)
                                elif isinstance(value, datetime):
                                    row[key] = value.isoformat()
                                elif hasattr(value, 'value'):  # Enum
                                    row[key] = value.value
                            
                            writer.writerow(row)
            
            log_info(f"Dados de auditoria exportados para {filename}")
            
        except Exception as e:
            log_error(f"Erro ao exportar dados de auditoria: {e}")

# Decorator para auditoria automática
def audit_action(action_type: ActionType, 
                resource_type: str,
                description: str = None,
                track_state: bool = False):
    """Decorator para auditoria automática de funções"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Obtém informações do contexto (se disponível)
            user_id = kwargs.get('user_id', 'system')
            session_id = kwargs.get('session_id', 'system')
            resource_id = kwargs.get('resource_id', 'unknown')
            
            # Estado anterior (se solicitado)
            before_state = None
            if track_state and hasattr(func, '__self__'):
                try:
                    before_state = getattr(func.__self__, 'get_state', lambda: None)()
                except:
                    pass
            
            start_time = datetime.now()
            error_msg = None
            status = AuditStatus.SUCCESS
            
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                error_msg = str(e)
                status = AuditStatus.FAILURE
                raise
                
            finally:
                # Estado posterior (se solicitado)
                after_state = None
                if track_state and hasattr(func, '__self__'):
                    try:
                        after_state = getattr(func.__self__, 'get_state', lambda: None)()
                    except:
                        pass
                
                # Calcula duração
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Registra auditoria
                audit_manager = get_audit_manager()
                audit_manager.log_action(
                    user_id=user_id,
                    session_id=session_id,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=str(resource_id),
                    description=description or f"{func.__name__} executado",
                    status=status,
                    duration_ms=duration,
                    before_state=before_state,
                    after_state=after_state,
                    error_message=error_msg,
                    details={
                        'function': func.__name__,
                        'module': func.__module__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                )
        
        return wrapper
    return decorator

# Instância global
_global_audit_manager = None

def get_audit_manager(config: Dict[str, Any] = None) -> AuditManager:
    """Retorna instância global do gerenciador de auditoria"""
    global _global_audit_manager
    
    if _global_audit_manager is None:
        _global_audit_manager = AuditManager(config)
    
    return _global_audit_manager