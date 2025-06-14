# -*- coding: utf-8 -*-
"""
Sistema de Colaboração Avançada
Implementa compartilhamento, colaboração em tempo real e trabalho em equipe
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import threading
from collections import defaultdict

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager
from utils.database_manager import DatabaseManager

class ActionType(Enum):
    """Tipos de ação para versionamento"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    COMMENT = "comment"
    SHARE = "share"
    EXPORT = "export"

class PermissionLevel(Enum):
    """Níveis de permissão"""
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"
    OWNER = "owner"

class CommentType(Enum):
    """Tipos de comentário"""
    GENERAL = "general"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    APPROVAL = "approval"

class ShareType(Enum):
    """Tipos de compartilhamento"""
    VIEW_ONLY = "view_only"
    EDIT = "edit"
    COMMENT = "comment"
    ADMIN = "admin"
    OWNER = "owner"

class ResourceType(Enum):
    """Tipos de recursos compartilháveis"""
    DASHBOARD = "dashboard"
    REPORT = "report"
    DATASET = "dataset"
    CHART = "chart"
    FILTER = "filter"
    TEMPLATE = "template"
    WORKSPACE = "workspace"
    PROJECT = "project"

class CollaborationEvent(Enum):
    """Tipos de eventos de colaboração"""
    SHARE_CREATED = "share_created"
    SHARE_UPDATED = "share_updated"
    SHARE_REVOKED = "share_revoked"
    RESOURCE_EDITED = "resource_edited"
    COMMENT_ADDED = "comment_added"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    PERMISSION_CHANGED = "permission_changed"
    VERSION_CREATED = "version_created"
    CONFLICT_DETECTED = "conflict_detected"

class ConflictResolution(Enum):
    """Estratégias de resolução de conflitos"""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MANUAL_MERGE = "manual_merge"
    AUTO_MERGE = "auto_merge"
    CREATE_BRANCH = "create_branch"

@dataclass
class User:
    """Usuário do sistema"""
    id: str
    name: str
    email: str
    avatar_url: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None

@dataclass
class Comment:
    """Comentário em dashboard/visualização"""
    id: str
    user_id: str
    user_name: str
    resource_type: str  # 'dashboard', 'chart', 'filter'
    resource_id: str
    content: str
    type: CommentType
    position: Optional[Dict[str, float]] = None  # x, y para comentários posicionais
    parent_id: Optional[str] = None  # para respostas
    mentions: List[str] = field(default_factory=list)  # IDs de usuários mencionados
    attachments: List[str] = field(default_factory=list)  # URLs de anexos
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    reactions: Dict[str, List[str]] = field(default_factory=dict)  # emoji -> user_ids

@dataclass
class Version:
    """Versão de dashboard/visualização"""
    id: str
    resource_type: str
    resource_id: str
    version_number: int
    title: str
    description: str
    data: Dict[str, Any]  # snapshot dos dados
    created_by: str
    created_at: datetime
    action_type: ActionType
    changes_summary: str
    parent_version_id: Optional[str] = None
    is_published: bool = False
    tags: List[str] = field(default_factory=list)

@dataclass
class ShareSettings:
    """Configurações de compartilhamento"""
    id: str
    resource_type: str
    resource_id: str
    shared_by: str
    shared_with: List[str]  # user IDs
    permission_level: PermissionLevel
    expires_at: Optional[datetime] = None
    allow_download: bool = False
    allow_comments: bool = True
    require_login: bool = True
    public_link: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Activity:
    """Atividade do usuário"""
    id: str
    user_id: str
    user_name: str
    action_type: ActionType
    resource_type: str
    resource_id: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Notification:
    """Notificação para usuário"""
    id: str
    user_id: str
    title: str
    message: str
    type: str  # 'comment', 'mention', 'share', 'version'
    resource_type: str
    resource_id: str
    is_read: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

class CollaborationSystem:
    """Sistema de colaboração"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager()
        
        # Armazenamento em memória (em produção, usar banco de dados)
        self.users: Dict[str, User] = {}
        self.comments: Dict[str, Comment] = {}
        self.versions: Dict[str, List[Version]] = {}  # resource_id -> versions
        self.share_settings: Dict[str, ShareSettings] = {}
        self.activities: List[Activity] = []
        self.notifications: Dict[str, List[Notification]] = {}  # user_id -> notifications
        
        # Usuários online
        self.online_users: Set[str] = set()
        self.user_sessions: Dict[str, Dict[str, Any]] = {}  # user_id -> session_info
        
        # Configurações
        self.max_versions_per_resource = 50
        self.activity_retention_days = 90
        
        log_info("Sistema de colaboração inicializado")
    
    # === Gerenciamento de Usuários ===
    
    def register_user(self, user: User) -> bool:
        """Registra usuário no sistema"""
        try:
            self.users[user.id] = user
            log_info(f"Usuário registrado: {user.name} ({user.email})")
            return True
        except Exception as e:
            log_error(f"Erro ao registrar usuário: {e}")
            return False
    
    def set_user_online(self, user_id: str, session_info: Dict[str, Any] = None) -> bool:
        """Marca usuário como online"""
        try:
            if user_id in self.users:
                self.users[user_id].is_online = True
                self.users[user_id].last_seen = datetime.now()
                self.online_users.add(user_id)
                
                if session_info:
                    self.user_sessions[user_id] = session_info
                
                log_info(f"Usuário {user_id} está online")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao marcar usuário online: {e}")
            return False
    
    def set_user_offline(self, user_id: str) -> bool:
        """Marca usuário como offline"""
        try:
            if user_id in self.users:
                self.users[user_id].is_online = False
                self.users[user_id].last_seen = datetime.now()
                self.online_users.discard(user_id)
                
                if user_id in self.user_sessions:
                    del self.user_sessions[user_id]
                
                log_info(f"Usuário {user_id} está offline")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao marcar usuário offline: {e}")
            return False
    
    def get_online_users(self, resource_id: str = None) -> List[User]:
        """Retorna usuários online (opcionalmente filtrados por recurso)"""
        try:
            online_users = []
            for user_id in self.online_users:
                if user_id in self.users:
                    user = self.users[user_id]
                    
                    # Filtro por recurso se especificado
                    if resource_id:
                        session = self.user_sessions.get(user_id, {})
                        if session.get('current_resource') != resource_id:
                            continue
                    
                    online_users.append(user)
            
            return online_users
        except Exception as e:
            log_error(f"Erro ao obter usuários online: {e}")
            return []
    
    # === Sistema de Comentários ===
    
    def add_comment(self, comment: Comment) -> bool:
        """Adiciona comentário"""
        try:
            self.comments[comment.id] = comment
            
            # Registra atividade
            self._add_activity(
                user_id=comment.user_id,
                user_name=comment.user_name,
                action_type=ActionType.COMMENT,
                resource_type=comment.resource_type,
                resource_id=comment.resource_id,
                description=f"Adicionou comentário: {comment.content[:50]}...",
                metadata={'comment_id': comment.id, 'comment_type': comment.type.value}
            )
            
            # Cria notificações para menções
            self._create_mention_notifications(comment)
            
            log_info(f"Comentário adicionado por {comment.user_name}")
            return True
        except Exception as e:
            log_error(f"Erro ao adicionar comentário: {e}")
            return False
    
    def update_comment(self, comment_id: str, content: str, user_id: str) -> bool:
        """Atualiza comentário"""
        try:
            if comment_id not in self.comments:
                return False
            
            comment = self.comments[comment_id]
            
            # Verifica permissão
            if comment.user_id != user_id:
                log_warning(f"Usuário {user_id} tentou editar comentário de outro usuário")
                return False
            
            comment.content = content
            comment.updated_at = datetime.now()
            
            log_info(f"Comentário {comment_id} atualizado")
            return True
        except Exception as e:
            log_error(f"Erro ao atualizar comentário: {e}")
            return False
    
    def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """Remove comentário"""
        try:
            if comment_id not in self.comments:
                return False
            
            comment = self.comments[comment_id]
            
            # Verifica permissão (autor ou admin)
            if comment.user_id != user_id:
                # TODO: Verificar se é admin
                log_warning(f"Usuário {user_id} tentou deletar comentário de outro usuário")
                return False
            
            del self.comments[comment_id]
            
            log_info(f"Comentário {comment_id} removido")
            return True
        except Exception as e:
            log_error(f"Erro ao remover comentário: {e}")
            return False
    
    def resolve_comment(self, comment_id: str, user_id: str) -> bool:
        """Resolve comentário"""
        try:
            if comment_id not in self.comments:
                return False
            
            comment = self.comments[comment_id]
            comment.is_resolved = True
            comment.resolved_by = user_id
            comment.resolved_at = datetime.now()
            
            log_info(f"Comentário {comment_id} resolvido por {user_id}")
            return True
        except Exception as e:
            log_error(f"Erro ao resolver comentário: {e}")
            return False
    
    def add_reaction(self, comment_id: str, emoji: str, user_id: str) -> bool:
        """Adiciona reação a comentário"""
        try:
            if comment_id not in self.comments:
                return False
            
            comment = self.comments[comment_id]
            
            if emoji not in comment.reactions:
                comment.reactions[emoji] = []
            
            if user_id not in comment.reactions[emoji]:
                comment.reactions[emoji].append(user_id)
            
            log_info(f"Reação {emoji} adicionada ao comentário {comment_id}")
            return True
        except Exception as e:
            log_error(f"Erro ao adicionar reação: {e}")
            return False
    
    def get_comments(self, resource_type: str, resource_id: str, 
                    include_resolved: bool = True) -> List[Comment]:
        """Retorna comentários de um recurso"""
        try:
            comments = []
            for comment in self.comments.values():
                if (comment.resource_type == resource_type and 
                    comment.resource_id == resource_id):
                    
                    if not include_resolved and comment.is_resolved:
                        continue
                    
                    comments.append(comment)
            
            # Ordena por data de criação
            comments.sort(key=lambda c: c.created_at)
            return comments
        except Exception as e:
            log_error(f"Erro ao obter comentários: {e}")
            return []
    
    # === Sistema de Versionamento ===
    
    def create_version(self, version: Version) -> bool:
        """Cria nova versão"""
        try:
            resource_key = f"{version.resource_type}_{version.resource_id}"
            
            if resource_key not in self.versions:
                self.versions[resource_key] = []
            
            # Determina número da versão
            if not self.versions[resource_key]:
                version.version_number = 1
            else:
                version.version_number = max(v.version_number for v in self.versions[resource_key]) + 1
            
            self.versions[resource_key].append(version)
            
            # Limita número de versões
            if len(self.versions[resource_key]) > self.max_versions_per_resource:
                # Remove versões mais antigas (mantém as publicadas)
                versions_to_remove = []
                for v in self.versions[resource_key][:-self.max_versions_per_resource]:
                    if not v.is_published:
                        versions_to_remove.append(v)
                
                for v in versions_to_remove:
                    self.versions[resource_key].remove(v)
            
            # Registra atividade
            self._add_activity(
                user_id=version.created_by,
                user_name=self.users.get(version.created_by, User('', 'Unknown', '')).name,
                action_type=version.action_type,
                resource_type=version.resource_type,
                resource_id=version.resource_id,
                description=f"Criou versão {version.version_number}: {version.title}",
                metadata={'version_id': version.id, 'version_number': version.version_number}
            )
            
            log_info(f"Versão {version.version_number} criada para {resource_key}")
            return True
        except Exception as e:
            log_error(f"Erro ao criar versão: {e}")
            return False
    
    def get_versions(self, resource_type: str, resource_id: str) -> List[Version]:
        """Retorna versões de um recurso"""
        try:
            resource_key = f"{resource_type}_{resource_id}"
            versions = self.versions.get(resource_key, [])
            
            # Ordena por número da versão (mais recente primeiro)
            versions.sort(key=lambda v: v.version_number, reverse=True)
            return versions
        except Exception as e:
            log_error(f"Erro ao obter versões: {e}")
            return []
    
    def get_version(self, version_id: str) -> Optional[Version]:
        """Retorna versão específica"""
        try:
            for versions_list in self.versions.values():
                for version in versions_list:
                    if version.id == version_id:
                        return version
            return None
        except Exception as e:
            log_error(f"Erro ao obter versão: {e}")
            return None
    
    def publish_version(self, version_id: str, user_id: str) -> bool:
        """Publica versão"""
        try:
            version = self.get_version(version_id)
            if not version:
                return False
            
            version.is_published = True
            
            # Registra atividade
            self._add_activity(
                user_id=user_id,
                user_name=self.users.get(user_id, User('', 'Unknown', '')).name,
                action_type=ActionType.UPDATE,
                resource_type=version.resource_type,
                resource_id=version.resource_id,
                description=f"Publicou versão {version.version_number}",
                metadata={'version_id': version.id, 'version_number': version.version_number}
            )
            
            log_info(f"Versão {version_id} publicada")
            return True
        except Exception as e:
            log_error(f"Erro ao publicar versão: {e}")
            return False
    
    def revert_to_version(self, resource_type: str, resource_id: str, 
                         version_id: str, user_id: str) -> Optional[Version]:
        """Reverte para versão específica"""
        try:
            target_version = self.get_version(version_id)
            if not target_version:
                return None
            
            # Cria nova versão baseada na versão alvo
            new_version = Version(
                id=str(uuid.uuid4()),
                resource_type=resource_type,
                resource_id=resource_id,
                version_number=0,  # Será definido em create_version
                title=f"Revertido para v{target_version.version_number}",
                description=f"Revertido para versão {target_version.version_number}: {target_version.title}",
                data=target_version.data.copy(),
                created_by=user_id,
                created_at=datetime.now(),
                action_type=ActionType.UPDATE,
                changes_summary=f"Revertido para versão {target_version.version_number}",
                parent_version_id=version_id
            )
            
            if self.create_version(new_version):
                return new_version
            
            return None
        except Exception as e:
            log_error(f"Erro ao reverter versão: {e}")
            return None
    
    # === Sistema de Compartilhamento ===
    
    def create_share(self, share_settings: ShareSettings) -> bool:
        """Cria configuração de compartilhamento"""
        try:
            self.share_settings[share_settings.id] = share_settings
            
            # Gera link público se necessário
            if not share_settings.require_login:
                share_settings.public_link = f"/public/{share_settings.id}"
            
            # Cria notificações para usuários compartilhados
            for user_id in share_settings.shared_with:
                self._create_notification(
                    user_id=user_id,
                    title="Novo compartilhamento",
                    message=f"Um {share_settings.resource_type} foi compartilhado com você",
                    type="share",
                    resource_type=share_settings.resource_type,
                    resource_id=share_settings.resource_id,
                    data={'share_id': share_settings.id, 'permission': share_settings.permission_level.value}
                )
            
            # Registra atividade
            self._add_activity(
                user_id=share_settings.shared_by,
                user_name=self.users.get(share_settings.shared_by, User('', 'Unknown', '')).name,
                action_type=ActionType.SHARE,
                resource_type=share_settings.resource_type,
                resource_id=share_settings.resource_id,
                description=f"Compartilhou com {len(share_settings.shared_with)} usuários",
                metadata={'share_id': share_settings.id, 'permission': share_settings.permission_level.value}
            )
            
            log_info(f"Compartilhamento criado: {share_settings.id}")
            return True
        except Exception as e:
            log_error(f"Erro ao criar compartilhamento: {e}")
            return False
    
    def get_user_permissions(self, user_id: str, resource_type: str, 
                           resource_id: str) -> Optional[PermissionLevel]:
        """Retorna permissões do usuário para um recurso"""
        try:
            # Verifica compartilhamentos
            for share in self.share_settings.values():
                if (share.resource_type == resource_type and 
                    share.resource_id == resource_id and 
                    user_id in share.shared_with):
                    
                    # Verifica expiração
                    if share.expires_at and datetime.now() > share.expires_at:
                        continue
                    
                    return share.permission_level
            
            # TODO: Verificar se é proprietário do recurso
            return None
        except Exception as e:
            log_error(f"Erro ao obter permissões: {e}")
            return None
    
    def revoke_share(self, share_id: str, user_id: str) -> bool:
        """Revoga compartilhamento"""
        try:
            if share_id not in self.share_settings:
                return False
            
            share = self.share_settings[share_id]
            
            # Verifica permissão
            if share.shared_by != user_id:
                log_warning(f"Usuário {user_id} tentou revogar compartilhamento de outro usuário")
                return False
            
            del self.share_settings[share_id]
            
            log_info(f"Compartilhamento {share_id} revogado")
            return True
        except Exception as e:
            log_error(f"Erro ao revogar compartilhamento: {e}")
            return False
    
    # === Sistema de Notificações ===
    
    def _create_notification(self, user_id: str, title: str, message: str,
                           type: str, resource_type: str, resource_id: str,
                           data: Dict[str, Any] = None) -> bool:
        """Cria notificação para usuário"""
        try:
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=title,
                message=message,
                type=type,
                resource_type=resource_type,
                resource_id=resource_id,
                data=data or {}
            )
            
            if user_id not in self.notifications:
                self.notifications[user_id] = []
            
            self.notifications[user_id].append(notification)
            
            # Limita número de notificações por usuário
            if len(self.notifications[user_id]) > 100:
                self.notifications[user_id] = self.notifications[user_id][-100:]
            
            return True
        except Exception as e:
            log_error(f"Erro ao criar notificação: {e}")
            return False
    
    def _create_mention_notifications(self, comment: Comment):
        """Cria notificações para menções em comentários"""
        try:
            for mentioned_user_id in comment.mentions:
                if mentioned_user_id in self.users:
                    user = self.users[mentioned_user_id]
                    self._create_notification(
                        user_id=mentioned_user_id,
                        title="Você foi mencionado",
                        message=f"{comment.user_name} mencionou você em um comentário",
                        type="mention",
                        resource_type=comment.resource_type,
                        resource_id=comment.resource_id,
                        data={'comment_id': comment.id, 'commenter': comment.user_name}
                    )
        except Exception as e:
            log_error(f"Erro ao criar notificações de menção: {e}")
    
    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        """Retorna notificações do usuário"""
        try:
            notifications = self.notifications.get(user_id, [])
            
            if unread_only:
                notifications = [n for n in notifications if not n.is_read]
            
            # Ordena por data (mais recente primeiro)
            notifications.sort(key=lambda n: n.created_at, reverse=True)
            return notifications
        except Exception as e:
            log_error(f"Erro ao obter notificações: {e}")
            return []
    
    def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Marca notificação como lida"""
        try:
            notifications = self.notifications.get(user_id, [])
            
            for notification in notifications:
                if notification.id == notification_id:
                    notification.is_read = True
                    return True
            
            return False
        except Exception as e:
            log_error(f"Erro ao marcar notificação como lida: {e}")
            return False
    
    # === Sistema de Atividades ===
    
    def _add_activity(self, user_id: str, user_name: str, action_type: ActionType,
                     resource_type: str, resource_id: str, description: str,
                     metadata: Dict[str, Any] = None):
        """Adiciona atividade ao log"""
        try:
            activity = Activity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                user_name=user_name,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                metadata=metadata or {}
            )
            
            self.activities.append(activity)
            
            # Limita número de atividades
            if len(self.activities) > 1000:
                self.activities = self.activities[-1000:]
            
        except Exception as e:
            log_error(f"Erro ao adicionar atividade: {e}")
    
    def get_activities(self, resource_type: str = None, resource_id: str = None,
                      user_id: str = None, limit: int = 50) -> List[Activity]:
        """Retorna atividades filtradas"""
        try:
            activities = self.activities.copy()
            
            # Aplica filtros
            if resource_type:
                activities = [a for a in activities if a.resource_type == resource_type]
            
            if resource_id:
                activities = [a for a in activities if a.resource_id == resource_id]
            
            if user_id:
                activities = [a for a in activities if a.user_id == user_id]
            
            # Ordena por timestamp (mais recente primeiro)
            activities.sort(key=lambda a: a.timestamp, reverse=True)
            
            return activities[:limit]
        except Exception as e:
            log_error(f"Erro ao obter atividades: {e}")
            return []
    
    def share_resource(self, 
                      resource_id: str,
                      resource_type: ResourceType,
                      owner_id: str,
                      shared_with_id: str,
                      share_type: ShareType,
                      custom_permissions: Dict[str, bool] = None,
                      expires_at: datetime = None) -> str:
        """Compartilha um recurso com outro usuário"""
        try:
            permission_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Permissões padrão baseadas no tipo de compartilhamento
            default_permissions = {
                ShareType.VIEW_ONLY: {'read': True, 'write': False, 'delete': False, 'share': False, 'admin': False},
                ShareType.EDIT: {'read': True, 'write': True, 'delete': False, 'share': False, 'admin': False},
                ShareType.COMMENT: {'read': True, 'write': False, 'delete': False, 'share': False, 'admin': False},
                ShareType.ADMIN: {'read': True, 'write': True, 'delete': True, 'share': True, 'admin': True},
                ShareType.OWNER: {'read': True, 'write': True, 'delete': True, 'share': True, 'admin': True}
            }
            
            permissions = custom_permissions or default_permissions[share_type]
            
            # Salva no banco de dados (implementação simplificada)
            share_data = {
                'id': permission_id,
                'resource_id': resource_id,
                'resource_type': resource_type.value,
                'owner_id': owner_id,
                'shared_with_id': shared_with_id,
                'share_type': share_type.value,
                'permissions': permissions,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'created_at': now.isoformat(),
                'is_active': True
            }
            
            # Adiciona à lista de compartilhamentos (em memória)
            if not hasattr(self, 'shares'):
                self.shares = []
            self.shares.append(share_data)
            
            # Registra atividade
            self.add_activity(
                user_id=owner_id,
                user_name="Sistema",
                action_type=ActionType.SHARE,
                resource_type=resource_type.value,
                resource_id=resource_id,
                description=f"Recurso compartilhado com {shared_with_id}",
                metadata={'shared_with': shared_with_id, 'share_type': share_type.value}
            )
            
            log_info(f"Recurso {resource_id} compartilhado com {shared_with_id}")
            return permission_id
            
        except Exception as e:
            log_error(f"Erro ao compartilhar recurso: {e}")
            return ""
    
    def get_user_permissions(self, user_id: str, resource_id: str) -> Optional[Dict[str, Any]]:
        """Obtém permissões do usuário para um recurso"""
        try:
            if not hasattr(self, 'shares'):
                return None
            
            now = datetime.now()
            
            for share in self.shares:
                if (share['shared_with_id'] == user_id or share['owner_id'] == user_id) and \
                   share['resource_id'] == resource_id and share['is_active']:
                    
                    # Verifica expiração
                    if share['expires_at']:
                        expires_at = datetime.fromisoformat(share['expires_at'])
                        if now > expires_at:
                            continue
                    
                    return share
            
            return None
            
        except Exception as e:
            log_error(f"Erro ao obter permissões: {e}")
            return None
    
    def create_collaboration_session(self, 
                                   resource_id: str,
                                   resource_type: ResourceType,
                                   created_by: str) -> str:
        """Cria uma sessão de colaboração em tempo real"""
        try:
            session_id = str(uuid.uuid4())
            now = datetime.now()
            
            session_data = {
                'id': session_id,
                'resource_id': resource_id,
                'resource_type': resource_type.value,
                'participants': [created_by],
                'created_by': created_by,
                'created_at': now.isoformat(),
                'last_activity': now.isoformat(),
                'is_active': True
            }
            
            # Adiciona à lista de sessões (em memória)
            if not hasattr(self, 'sessions'):
                self.sessions = []
            self.sessions.append(session_data)
            
            log_info(f"Sessão de colaboração criada: {session_id}")
            return session_id
            
        except Exception as e:
            log_error(f"Erro ao criar sessão de colaboração: {e}")
            return ""
    
    def join_collaboration_session(self, session_id: str, user_id: str) -> bool:
        """Usuário entra em uma sessão de colaboração"""
        try:
            if not hasattr(self, 'sessions'):
                return False
            
            for session in self.sessions:
                if session['id'] == session_id and session['is_active']:
                    if user_id not in session['participants']:
                        session['participants'].append(user_id)
                        session['last_activity'] = datetime.now().isoformat()
                        
                        log_info(f"Usuário {user_id} entrou na sessão {session_id}")
                        return True
            
            return False
            
        except Exception as e:
            log_error(f"Erro ao entrar na sessão: {e}")
            return False
    
    def broadcast_change_event(self, 
                              session_id: str,
                              user_id: str,
                              event_type: str,
                              data: Dict[str, Any]) -> bool:
        """Transmite evento de mudança para todos os participantes da sessão"""
        try:
            if not hasattr(self, 'sessions'):
                return False
            
            for session in self.sessions:
                if session['id'] == session_id and session['is_active']:
                    # Atualiza última atividade
                    session['last_activity'] = datetime.now().isoformat()
                    
                    # Em uma implementação real, aqui seria enviado via WebSocket
                    # para todos os participantes da sessão
                    event_data = {
                        'session_id': session_id,
                        'user_id': user_id,
                        'event_type': event_type,
                        'data': data,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    log_info(f"Evento transmitido na sessão {session_id}: {event_type}")
                    return True
            
            return False
            
        except Exception as e:
            log_error(f"Erro ao transmitir evento: {e}")
            return False
    
    def detect_conflicts(self, 
                        resource_id: str,
                        user1_changes: Dict[str, Any],
                        user2_changes: Dict[str, Any],
                        user1_id: str,
                        user2_id: str) -> Optional[str]:
        """Detecta conflitos entre mudanças de diferentes usuários"""
        try:
            conflicts = []
            
            for key in user1_changes:
                if key in user2_changes and user1_changes[key] != user2_changes[key]:
                    conflicts.append({
                        'field': key,
                        'user1_value': user1_changes[key],
                        'user2_value': user2_changes[key]
                    })
            
            if conflicts:
                conflict_id = str(uuid.uuid4())
                
                conflict_data = {
                    'id': conflict_id,
                    'resource_id': resource_id,
                    'user1_id': user1_id,
                    'user2_id': user2_id,
                    'conflicts': conflicts,
                    'created_at': datetime.now().isoformat(),
                    'is_resolved': False
                }
                
                # Adiciona à lista de conflitos (em memória)
                if not hasattr(self, 'conflicts'):
                    self.conflicts = []
                self.conflicts.append(conflict_data)
                
                log_warning(f"Conflito detectado no recurso {resource_id}: {conflict_id}")
                return conflict_id
            
            return None
            
        except Exception as e:
            log_error(f"Erro ao detectar conflitos: {e}")
            return None
    
    def get_collaboration_analytics(self, 
                                   resource_id: str = None,
                                   days: int = 30) -> Dict[str, Any]:
        """Obtém analytics de colaboração"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Filtra atividades por período
            recent_activities = [
                a for a in self.activities 
                if a.timestamp >= start_date and 
                (not resource_id or a.resource_id == resource_id)
            ]
            
            # Estatísticas básicas
            analytics = {
                'total_activities': len(recent_activities),
                'unique_users': len(set(a.user_id for a in recent_activities)),
                'activities_by_type': {},
                'most_active_users': {},
                'daily_activity': {}
            }
            
            # Atividades por tipo
            for activity in recent_activities:
                action_type = activity.action_type.value
                analytics['activities_by_type'][action_type] = \
                    analytics['activities_by_type'].get(action_type, 0) + 1
            
            # Usuários mais ativos
            for activity in recent_activities:
                user_id = activity.user_id
                analytics['most_active_users'][user_id] = \
                    analytics['most_active_users'].get(user_id, 0) + 1
            
            # Atividade diária
            for activity in recent_activities:
                date_key = activity.timestamp.strftime('%Y-%m-%d')
                analytics['daily_activity'][date_key] = \
                    analytics['daily_activity'].get(date_key, 0) + 1
            
            return analytics
            
        except Exception as e:
            log_error(f"Erro ao obter analytics: {e}")
            return {}
    
    # === Métodos Utilitários ===
    
    def cleanup_expired_shares(self) -> int:
        """Remove compartilhamentos expirados"""
        try:
            if not hasattr(self, 'shares'):
                return 0
            
            now = datetime.now()
            initial_count = len(self.shares)
            
            self.shares = [
                share for share in self.shares
                if not share['expires_at'] or 
                datetime.fromisoformat(share['expires_at']) > now
            ]
            
            removed_count = initial_count - len(self.shares)
            if removed_count > 0:
                log_info(f"Removidos {removed_count} compartilhamentos expirados")
            
            return removed_count
            
        except Exception as e:
            log_error(f"Erro ao limpar compartilhamentos expirados: {e}")
            return 0
    
    def cleanup_old_events(self, days: int = 30) -> int:
        """Remove eventos antigos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            initial_count = len(self.activities)
            
            self.activities = [
                activity for activity in self.activities
                if activity.timestamp >= cutoff_date
            ]
            
            removed_count = initial_count - len(self.activities)
            if removed_count > 0:
                log_info(f"Removidos {removed_count} eventos antigos")
            
            return removed_count
            
        except Exception as e:
            log_error(f"Erro ao limpar eventos antigos: {e}")
            return 0
    
    def revoke_resource_access(self, permission_id: str) -> bool:
        """Revoga acesso a um recurso"""
        try:
            if not hasattr(self, 'shares'):
                return False
            
            for share in self.shares:
                if share['id'] == permission_id:
                    share['is_active'] = False
                    log_info(f"Acesso revogado: {permission_id}")
                    return True
            
            return False
            
        except Exception as e:
            log_error(f"Erro ao revogar acesso: {e}")
            return False
    
    def get_shared_resources(self, user_id: str) -> List[Dict[str, Any]]:
        """Obtém recursos compartilhados com o usuário"""
        try:
            if not hasattr(self, 'shares'):
                return []
            
            now = datetime.now()
            shared_resources = []
            
            for share in self.shares:
                if share['shared_with_id'] == user_id and share['is_active']:
                    # Verifica expiração
                    if share['expires_at']:
                        expires_at = datetime.fromisoformat(share['expires_at'])
                        if now > expires_at:
                            continue
                    
                    shared_resources.append(share)
            
            return shared_resources
            
        except Exception as e:
            log_error(f"Erro ao obter recursos compartilhados: {e}")
            return []
    
    def add_event_listener(self, event_type: str, callback: callable):
        """Adiciona listener para eventos de colaboração"""
        try:
            if not hasattr(self, 'event_listeners'):
                self.event_listeners = defaultdict(list)
            
            self.event_listeners[event_type].append(callback)
            log_info(f"Listener adicionado para evento: {event_type}")
            
        except Exception as e:
            log_error(f"Erro ao adicionar listener: {e}")
    
    def trigger_event(self, event_type: str, data: Dict[str, Any]):
        """Dispara evento para todos os listeners"""
        try:
            if hasattr(self, 'event_listeners') and event_type in self.event_listeners:
                for callback in self.event_listeners[event_type]:
                    try:
                        callback(data)
                    except Exception as e:
                        log_error(f"Erro no callback do evento {event_type}: {e}")
            
        except Exception as e:
            log_error(f"Erro ao disparar evento: {e}")


# Instância global do sistema de colaboração
collaboration_system = CollaborationSystem()