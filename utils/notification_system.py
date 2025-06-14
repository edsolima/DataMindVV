# -*- coding: utf-8 -*-
"""
Sistema de Notificações
Implementa notificações em tempo real, push notifications e alertas personalizados
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path
import asyncio
from threading import Thread
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationType(Enum):
    """Tipos de notificação"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"
    REMINDER = "reminder"
    SYSTEM = "system"
    SOCIAL = "social"

class NotificationChannel(Enum):
    """Canais de notificação"""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"

class NotificationPriority(Enum):
    """Prioridade da notificação"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationStatus(Enum):
    """Status da notificação"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Notification:
    """Notificação individual"""
    id: str
    user_id: str
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    channels: List[NotificationChannel]
    data: Dict[str, Any]  # Dados adicionais
    action_url: Optional[str]
    action_text: Optional[str]
    expires_at: Optional[datetime]
    status: NotificationStatus
    created_at: datetime
    sent_at: Optional[datetime]
    read_at: Optional[datetime]
    retry_count: int
    max_retries: int

@dataclass
class NotificationTemplate:
    """Template de notificação"""
    id: str
    name: str
    title_template: str
    message_template: str
    notification_type: NotificationType
    default_channels: List[NotificationChannel]
    default_priority: NotificationPriority
    variables: List[str]
    is_active: bool

@dataclass
class UserPreferences:
    """Preferências de notificação do usuário"""
    user_id: str
    email_enabled: bool
    push_enabled: bool
    in_app_enabled: bool
    quiet_hours_start: Optional[str]  # HH:MM
    quiet_hours_end: Optional[str]    # HH:MM
    frequency_limit: int  # Max notificações por hora
    categories: Dict[str, bool]  # Categorias habilitadas
    channels_by_priority: Dict[str, List[str]]  # Canais por prioridade

class NotificationSystem:
    """Sistema principal de notificações"""
    
    def __init__(self, db_path: str = "notifications.sqlite"):
        self.db_path = db_path
        self.subscribers = {}  # WebSocket subscribers
        self.email_config = {}
        self.webhook_handlers = {}
        self._init_database()
        self._load_default_templates()
        self._start_background_processor()
        
    def _init_database(self):
        """Inicializa o banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            # Tabela de notificações
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    channels TEXT NOT NULL,
                    data TEXT NOT NULL DEFAULT '{}',
                    action_url TEXT,
                    action_text TEXT,
                    expires_at TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    read_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            """)
            
            # Tabela de templates
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    title_template TEXT NOT NULL,
                    message_template TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    default_channels TEXT NOT NULL,
                    default_priority TEXT NOT NULL,
                    variables TEXT NOT NULL DEFAULT '[]',
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Tabela de preferências do usuário
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    email_enabled BOOLEAN DEFAULT TRUE,
                    push_enabled BOOLEAN DEFAULT TRUE,
                    in_app_enabled BOOLEAN DEFAULT TRUE,
                    quiet_hours_start TEXT,
                    quiet_hours_end TEXT,
                    frequency_limit INTEGER DEFAULT 10,
                    categories TEXT NOT NULL DEFAULT '{}',
                    channels_by_priority TEXT NOT NULL DEFAULT '{}'
                )
            """)
            
            # Tabela de logs de entrega
            conn.execute("""
                CREATE TABLE IF NOT EXISTS delivery_logs (
                    id TEXT PRIMARY KEY,
                    notification_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    delivered_at TEXT NOT NULL,
                    FOREIGN KEY (notification_id) REFERENCES notifications (id)
                )
            """)
            
            # Tabela de estatísticas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_stats (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    total_sent INTEGER DEFAULT 0,
                    by_type TEXT NOT NULL DEFAULT '{}',
                    by_channel TEXT NOT NULL DEFAULT '{}',
                    by_status TEXT NOT NULL DEFAULT '{}',
                    avg_delivery_time REAL DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def _load_default_templates(self):
        """Carrega templates padrão"""
        default_templates = [
            {
                'id': 'welcome',
                'name': 'Boas-vindas',
                'title_template': 'Bem-vindo ao DataMindVV, {username}!',
                'message_template': 'Olá {username}, seja bem-vindo à nossa plataforma de análise de dados. Explore nossas funcionalidades e crie visualizações incríveis!',
                'notification_type': NotificationType.INFO,
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                'default_priority': NotificationPriority.NORMAL,
                'variables': ['username']
            },
            {
                'id': 'data_processing_complete',
                'name': 'Processamento Concluído',
                'title_template': 'Processamento de dados concluído',
                'message_template': 'O processamento do arquivo {filename} foi concluído com sucesso. {records_count} registros foram processados.',
                'notification_type': NotificationType.SUCCESS,
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
                'default_priority': NotificationPriority.NORMAL,
                'variables': ['filename', 'records_count']
            },
            {
                'id': 'system_alert',
                'name': 'Alerta do Sistema',
                'title_template': 'Alerta: {alert_type}',
                'message_template': 'Detectamos um problema: {description}. Ação recomendada: {action}',
                'notification_type': NotificationType.ALERT,
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.PUSH],
                'default_priority': NotificationPriority.HIGH,
                'variables': ['alert_type', 'description', 'action']
            },
            {
                'id': 'dashboard_shared',
                'name': 'Dashboard Compartilhado',
                'title_template': 'Dashboard compartilhado com você',
                'message_template': '{sharer_name} compartilhou o dashboard "{dashboard_name}" com você. Clique para visualizar.',
                'notification_type': NotificationType.SOCIAL,
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                'default_priority': NotificationPriority.NORMAL,
                'variables': ['sharer_name', 'dashboard_name']
            },
            {
                'id': 'scheduled_report',
                'name': 'Relatório Agendado',
                'title_template': 'Seu relatório está pronto',
                'message_template': 'O relatório "{report_name}" foi gerado e está disponível para download.',
                'notification_type': NotificationType.INFO,
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                'default_priority': NotificationPriority.NORMAL,
                'variables': ['report_name']
            }
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for template in default_templates:
                conn.execute("""
                    INSERT OR IGNORE INTO notification_templates (
                        id, name, title_template, message_template, notification_type,
                        default_channels, default_priority, variables, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template['id'], template['name'], template['title_template'],
                    template['message_template'], template['notification_type'].value,
                    json.dumps([ch.value for ch in template['default_channels']]),
                    template['default_priority'].value, json.dumps(template['variables']),
                    True
                ))
            conn.commit()
    
    def create_notification(self, 
                          user_id: str,
                          title: str,
                          message: str,
                          notification_type: NotificationType = NotificationType.INFO,
                          priority: NotificationPriority = NotificationPriority.NORMAL,
                          channels: List[NotificationChannel] = None,
                          data: Dict[str, Any] = None,
                          action_url: str = None,
                          action_text: str = None,
                          expires_at: datetime = None) -> str:
        """Cria uma nova notificação"""
        
        notification_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Usa canais padrão se não especificado
        if channels is None:
            channels = [NotificationChannel.IN_APP]
        
        # Aplica preferências do usuário
        user_prefs = self.get_user_preferences(user_id)
        if user_prefs:
            channels = self._filter_channels_by_preferences(channels, user_prefs, priority)
        
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            channels=channels,
            data=data or {},
            action_url=action_url,
            action_text=action_text,
            expires_at=expires_at,
            status=NotificationStatus.PENDING,
            created_at=now,
            sent_at=None,
            read_at=None,
            retry_count=0,
            max_retries=3
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO notifications (
                    id, user_id, title, message, notification_type, priority,
                    channels, data, action_url, action_text, expires_at, status,
                    created_at, sent_at, read_at, retry_count, max_retries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification.id, notification.user_id, notification.title,
                notification.message, notification.notification_type.value,
                notification.priority.value, json.dumps([ch.value for ch in notification.channels]),
                json.dumps(notification.data), notification.action_url,
                notification.action_text, notification.expires_at.isoformat() if notification.expires_at else None,
                notification.status.value, notification.created_at.isoformat(),
                None, None, notification.retry_count, notification.max_retries
            ))
            conn.commit()
        
        # Agenda para envio imediato
        self._schedule_notification(notification_id)
        
        return notification_id
    
    def create_from_template(self, 
                           template_id: str,
                           user_id: str,
                           variables: Dict[str, str],
                           **kwargs) -> str:
        """Cria notificação a partir de template"""
        
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} não encontrado")
        
        # Substitui variáveis
        title = template.title_template.format(**variables)
        message = template.message_template.format(**variables)
        
        # Usa configurações do template como padrão
        notification_type = kwargs.get('notification_type', template.notification_type)
        priority = kwargs.get('priority', template.default_priority)
        channels = kwargs.get('channels', template.default_channels)
        
        return self.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            channels=channels,
            **{k: v for k, v in kwargs.items() if k not in ['notification_type', 'priority', 'channels']}
        )
    
    def send_notification(self, notification_id: str) -> bool:
        """Envia uma notificação"""
        notification = self.get_notification(notification_id)
        if not notification or notification.status != NotificationStatus.PENDING:
            return False
        
        # Verifica se expirou
        if notification.expires_at and datetime.now() > notification.expires_at:
            self._update_notification_status(notification_id, NotificationStatus.CANCELLED)
            return False
        
        # Verifica horário silencioso
        if self._is_quiet_hours(notification.user_id):
            return False  # Reagenda para mais tarde
        
        success = True
        
        # Envia por cada canal
        for channel in notification.channels:
            try:
                if channel == NotificationChannel.IN_APP:
                    self._send_in_app(notification)
                elif channel == NotificationChannel.EMAIL:
                    self._send_email(notification)
                elif channel == NotificationChannel.PUSH:
                    self._send_push(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook(notification)
                
                self._log_delivery(notification_id, channel, "delivered")
                
            except Exception as e:
                self._log_delivery(notification_id, channel, "failed", str(e))
                success = False
        
        # Atualiza status
        if success:
            self._update_notification_status(notification_id, NotificationStatus.SENT)
        else:
            # Incrementa retry count
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE notifications SET retry_count = retry_count + 1 WHERE id = ?",
                    (notification_id,)
                )
                conn.commit()
        
        return success
    
    def _send_in_app(self, notification: Notification):
        """Envia notificação in-app via WebSocket"""
        if notification.user_id in self.subscribers:
            message = {
                'type': 'notification',
                'data': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type.value,
                    'priority': notification.priority.value,
                    'action_url': notification.action_url,
                    'action_text': notification.action_text,
                    'created_at': notification.created_at.isoformat()
                }
            }
            
            # Envia para todos os WebSockets do usuário
            for ws in self.subscribers[notification.user_id]:
                try:
                    ws.send(json.dumps(message))
                except:
                    # Remove WebSocket inválido
                    self.subscribers[notification.user_id].remove(ws)
    
    def _send_email(self, notification: Notification):
        """Envia notificação por email"""
        if not self.email_config:
            raise Exception("Configuração de email não definida")
        
        # Obtém email do usuário
        user_email = self._get_user_email(notification.user_id)
        if not user_email:
            raise Exception("Email do usuário não encontrado")
        
        # Cria mensagem
        msg = MIMEMultipart()
        msg['From'] = self.email_config['from_email']
        msg['To'] = user_email
        msg['Subject'] = notification.title
        
        # Corpo do email
        body = f"""
        <html>
        <body>
            <h2>{notification.title}</h2>
            <p>{notification.message}</p>
            {f'<p><a href="{notification.action_url}">{notification.action_text}</a></p>' if notification.action_url else ''}
            <hr>
            <p><small>DataMindVV - Plataforma Analítica</small></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Envia
        with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
            if self.email_config.get('use_tls'):
                server.starttls()
            if self.email_config.get('username'):
                server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
    
    def _send_push(self, notification: Notification):
        """Envia push notification"""
        # Implementação de push notification
        # Pode usar Firebase, OneSignal, etc.
        pass
    
    def _send_webhook(self, notification: Notification):
        """Envia via webhook"""
        webhook_url = notification.data.get('webhook_url')
        if not webhook_url:
            return
        
        import requests
        
        payload = {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type.value,
            'priority': notification.priority.value,
            'user_id': notification.user_id,
            'created_at': notification.created_at.isoformat()
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    
    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Marca notificação como lida"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE notifications 
                SET status = ?, read_at = ?
                WHERE id = ? AND user_id = ? AND status != 'read'
            """, (NotificationStatus.READ.value, now.isoformat(), notification_id, user_id))
            
            return cursor.rowcount > 0
    
    def get_user_notifications(self, 
                              user_id: str,
                              unread_only: bool = False,
                              limit: int = 50,
                              offset: int = 0) -> List[Dict[str, Any]]:
        """Obtém notificações do usuário"""
        
        query = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]
        
        if unread_only:
            query += " AND status != 'read'"
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_unread_count(self, user_id: str) -> int:
        """Obtém contagem de notificações não lidas"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND status != 'read'",
                (user_id,)
            )
            return cursor.fetchone()[0]
    
    def set_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Define preferências do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences (
                    user_id, email_enabled, push_enabled, in_app_enabled,
                    quiet_hours_start, quiet_hours_end, frequency_limit,
                    categories, channels_by_priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                preferences.get('email_enabled', True),
                preferences.get('push_enabled', True),
                preferences.get('in_app_enabled', True),
                preferences.get('quiet_hours_start'),
                preferences.get('quiet_hours_end'),
                preferences.get('frequency_limit', 10),
                json.dumps(preferences.get('categories', {})),
                json.dumps(preferences.get('channels_by_priority', {}))
            ))
            conn.commit()
    
    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Obtém preferências do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return UserPreferences(
                    user_id=row['user_id'],
                    email_enabled=row['email_enabled'],
                    push_enabled=row['push_enabled'],
                    in_app_enabled=row['in_app_enabled'],
                    quiet_hours_start=row['quiet_hours_start'],
                    quiet_hours_end=row['quiet_hours_end'],
                    frequency_limit=row['frequency_limit'],
                    categories=json.loads(row['categories']),
                    channels_by_priority=json.loads(row['channels_by_priority'])
                )
            return None
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Obtém uma notificação específica"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM notifications WHERE id = ?", (notification_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_notification(row)
            return None
    
    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Obtém um template"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM notification_templates WHERE id = ?", (template_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return NotificationTemplate(
                    id=row['id'],
                    name=row['name'],
                    title_template=row['title_template'],
                    message_template=row['message_template'],
                    notification_type=NotificationType(row['notification_type']),
                    default_channels=[NotificationChannel(ch) for ch in json.loads(row['default_channels'])],
                    default_priority=NotificationPriority(row['default_priority']),
                    variables=json.loads(row['variables']),
                    is_active=row['is_active']
                )
            return None
    
    def _row_to_notification(self, row: sqlite3.Row) -> Notification:
        """Converte row para objeto Notification"""
        return Notification(
            id=row['id'],
            user_id=row['user_id'],
            title=row['title'],
            message=row['message'],
            notification_type=NotificationType(row['notification_type']),
            priority=NotificationPriority(row['priority']),
            channels=[NotificationChannel(ch) for ch in json.loads(row['channels'])],
            data=json.loads(row['data']),
            action_url=row['action_url'],
            action_text=row['action_text'],
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            status=NotificationStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']),
            sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None,
            read_at=datetime.fromisoformat(row['read_at']) if row['read_at'] else None,
            retry_count=row['retry_count'],
            max_retries=row['max_retries']
        )
    
    def _filter_channels_by_preferences(self, 
                                       channels: List[NotificationChannel],
                                       preferences: UserPreferences,
                                       priority: NotificationPriority) -> List[NotificationChannel]:
        """Filtra canais baseado nas preferências do usuário"""
        filtered = []
        
        for channel in channels:
            if channel == NotificationChannel.EMAIL and not preferences.email_enabled:
                continue
            elif channel == NotificationChannel.PUSH and not preferences.push_enabled:
                continue
            elif channel == NotificationChannel.IN_APP and not preferences.in_app_enabled:
                continue
            
            filtered.append(channel)
        
        return filtered
    
    def _is_quiet_hours(self, user_id: str) -> bool:
        """Verifica se está em horário silencioso"""
        preferences = self.get_user_preferences(user_id)
        if not preferences or not preferences.quiet_hours_start or not preferences.quiet_hours_end:
            return False
        
        now = datetime.now().time()
        start = datetime.strptime(preferences.quiet_hours_start, "%H:%M").time()
        end = datetime.strptime(preferences.quiet_hours_end, "%H:%M").time()
        
        if start <= end:
            return start <= now <= end
        else:  # Atravessa meia-noite
            return now >= start or now <= end
    
    def _schedule_notification(self, notification_id: str):
        """Agenda notificação para envio"""
        # Em uma implementação real, usaria Celery ou similar
        # Por simplicidade, envia imediatamente em thread separada
        def send_async():
            self.send_notification(notification_id)
        
        thread = Thread(target=send_async)
        thread.daemon = True
        thread.start()
    
    def _update_notification_status(self, notification_id: str, status: NotificationStatus):
        """Atualiza status da notificação"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE notifications SET status = ?, sent_at = ? WHERE id = ?",
                (status.value, now.isoformat(), notification_id)
            )
            conn.commit()
    
    def _log_delivery(self, notification_id: str, channel: NotificationChannel, status: str, error: str = None):
        """Registra log de entrega"""
        log_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO delivery_logs (id, notification_id, channel, status, error_message, delivered_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (log_id, notification_id, channel.value, status, error, now.isoformat()))
            conn.commit()
    
    def _get_user_email(self, user_id: str) -> Optional[str]:
        """Obtém email do usuário (implementar conforme sistema de usuários)"""
        # Implementar integração com sistema de usuários
        return None
    
    def _start_background_processor(self):
        """Inicia processador em background para reenvios e limpeza"""
        def background_task():
            while True:
                try:
                    # Reprocessa notificações falhadas
                    self._retry_failed_notifications()
                    
                    # Limpa notificações antigas
                    self._cleanup_old_notifications()
                    
                    # Aguarda 5 minutos
                    import time
                    time.sleep(300)
                    
                except Exception as e:
                    print(f"Erro no processador de notificações: {e}")
        
        thread = Thread(target=background_task)
        thread.daemon = True
        thread.start()
    
    def _retry_failed_notifications(self):
        """Reprocessa notificações falhadas"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM notifications 
                WHERE status = 'pending' AND retry_count < max_retries
                AND created_at < datetime('now', '-5 minutes')
            """)
            
            for row in cursor.fetchall():
                self.send_notification(row[0])
    
    def _cleanup_old_notifications(self):
        """Remove notificações antigas"""
        cutoff_date = datetime.now() - timedelta(days=30)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM notifications WHERE created_at < ? AND status = 'read'",
                (cutoff_date.isoformat(),)
            )
            conn.commit()
    
    def configure_email(self, smtp_server: str, smtp_port: int, username: str, password: str, from_email: str, use_tls: bool = True):
        """Configura email"""
        self.email_config = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'from_email': from_email,
            'use_tls': use_tls
        }
    
    def subscribe_websocket(self, user_id: str, websocket):
        """Registra WebSocket para notificações em tempo real"""
        if user_id not in self.subscribers:
            self.subscribers[user_id] = []
        self.subscribers[user_id].append(websocket)
    
    def unsubscribe_websocket(self, user_id: str, websocket):
        """Remove WebSocket"""
        if user_id in self.subscribers and websocket in self.subscribers[user_id]:
            self.subscribers[user_id].remove(websocket)

# Instância global
notification_system = NotificationSystem()