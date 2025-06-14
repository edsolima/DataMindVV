# -*- coding: utf-8 -*-
"""
Integration Manager - Gerenciador de Integrações
Integração com ferramentas externas como Slack, Teams, email, webhooks
"""

import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import base64
import hashlib
import hmac
from urllib.parse import urlencode

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager

class IntegrationType(Enum):
    """Tipos de integração"""
    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    WEBHOOK = "webhook"
    DISCORD = "discord"
    TELEGRAM = "telegram"

class MessageType(Enum):
    """Tipos de mensagem"""
    ALERT = "alert"
    INSIGHT = "insight"
    REPORT = "report"
    NOTIFICATION = "notification"
    DASHBOARD_SHARE = "dashboard_share"
    COMMENT = "comment"

class Priority(Enum):
    """Prioridades de mensagem"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class IntegrationConfig:
    """Configuração de integração"""
    id: str
    name: str
    type: IntegrationType
    enabled: bool
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

@dataclass
class Message:
    """Mensagem para envio"""
    title: str
    content: str
    type: MessageType
    priority: Priority
    recipient: str  # canal, email, user_id, etc.
    attachments: List[str] = None
    metadata: Dict[str, Any] = None
    scheduled_at: Optional[datetime] = None

@dataclass
class DeliveryResult:
    """Resultado de entrega"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = None
    response_data: Dict[str, Any] = None

class SlackIntegration:
    """Integração com Slack"""
    
    def __init__(self, webhook_url: str, bot_token: str = None):
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.api_base = "https://slack.com/api"
    
    def send_message(self, message: Message) -> DeliveryResult:
        """Envia mensagem para Slack"""
        try:
            # Monta payload
            payload = {
                "text": message.title,
                "channel": message.recipient,
                "attachments": [{
                    "color": self._get_color_for_priority(message.priority),
                    "title": message.title,
                    "text": message.content,
                    "footer": "BI Platform",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            # Adiciona campos extras baseado no tipo
            if message.type == MessageType.ALERT:
                payload["attachments"][0]["fields"] = [
                    {"title": "Tipo", "value": "Alerta", "short": True},
                    {"title": "Prioridade", "value": message.priority.value.upper(), "short": True}
                ]
            
            # Envia via webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return DeliveryResult(
                    success=True,
                    message_id=response.headers.get('X-Slack-Req-Id'),
                    timestamp=datetime.now(),
                    response_data={'status_code': response.status_code}
                )
            else:
                return DeliveryResult(
                    success=False,
                    error=f"Slack API error: {response.status_code} - {response.text}",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            return DeliveryResult(
                success=False,
                error=f"Erro ao enviar para Slack: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _get_color_for_priority(self, priority: Priority) -> str:
        """Retorna cor baseada na prioridade"""
        colors = {
            Priority.LOW: "#36a64f",      # Verde
            Priority.MEDIUM: "#ffaa00",   # Amarelo
            Priority.HIGH: "#ff6600",     # Laranja
            Priority.CRITICAL: "#ff0000"  # Vermelho
        }
        return colors.get(priority, "#36a64f")
    
    def upload_file(self, file_path: str, channel: str, title: str = None) -> DeliveryResult:
        """Faz upload de arquivo para Slack"""
        try:
            if not self.bot_token:
                return DeliveryResult(
                    success=False,
                    error="Bot token necessário para upload de arquivos",
                    timestamp=datetime.now()
                )
            
            with open(file_path, 'rb') as file:
                response = requests.post(
                    f"{self.api_base}/files.upload",
                    headers={"Authorization": f"Bearer {self.bot_token}"},
                    data={
                        "channels": channel,
                        "title": title or "Arquivo do BI Platform"
                    },
                    files={"file": file},
                    timeout=60
                )
            
            result = response.json()
            
            if result.get("ok"):
                return DeliveryResult(
                    success=True,
                    message_id=result.get("file", {}).get("id"),
                    timestamp=datetime.now(),
                    response_data=result
                )
            else:
                return DeliveryResult(
                    success=False,
                    error=f"Slack upload error: {result.get('error')}",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            return DeliveryResult(
                success=False,
                error=f"Erro no upload para Slack: {str(e)}",
                timestamp=datetime.now()
            )

class TeamsIntegration:
    """Integração com Microsoft Teams"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_message(self, message: Message) -> DeliveryResult:
        """Envia mensagem para Teams"""
        try:
            # Monta payload para Teams
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": self._get_color_for_priority(message.priority),
                "summary": message.title,
                "sections": [{
                    "activityTitle": message.title,
                    "activitySubtitle": f"BI Platform - {message.type.value.title()}",
                    "text": message.content,
                    "facts": [
                        {"name": "Tipo", "value": message.type.value.title()},
                        {"name": "Prioridade", "value": message.priority.value.upper()},
                        {"name": "Timestamp", "value": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
                    ]
                }]
            }
            
            # Adiciona ações baseado no tipo
            if message.type in [MessageType.DASHBOARD_SHARE, MessageType.REPORT]:
                payload["potentialAction"] = [{
                    "@type": "OpenUri",
                    "name": "Visualizar Dashboard",
                    "targets": [{
                        "os": "default",
                        "uri": message.metadata.get('dashboard_url', '#') if message.metadata else '#'
                    }]
                }]
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return DeliveryResult(
                    success=True,
                    message_id=response.headers.get('request-id'),
                    timestamp=datetime.now(),
                    response_data={'status_code': response.status_code}
                )
            else:
                return DeliveryResult(
                    success=False,
                    error=f"Teams API error: {response.status_code} - {response.text}",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            return DeliveryResult(
                success=False,
                error=f"Erro ao enviar para Teams: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _get_color_for_priority(self, priority: Priority) -> str:
        """Retorna cor baseada na prioridade"""
        colors = {
            Priority.LOW: "28a745",      # Verde
            Priority.MEDIUM: "ffc107",   # Amarelo
            Priority.HIGH: "fd7e14",     # Laranja
            Priority.CRITICAL: "dc3545"  # Vermelho
        }
        return colors.get(priority, "28a745")

class EmailIntegration:
    """Integração com Email"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, 
                 password: str, use_tls: bool = True):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
    
    def send_message(self, message: Message) -> DeliveryResult:
        """Envia email"""
        try:
            # Cria mensagem
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = message.recipient
            msg['Subject'] = message.title
            
            # Corpo do email em HTML
            html_body = self._create_html_body(message)
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # Adiciona anexos
            if message.attachments:
                for attachment_path in message.attachments:
                    self._add_attachment(msg, attachment_path)
            
            # Conecta e envia
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            return DeliveryResult(
                success=True,
                message_id=msg['Message-ID'],
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return DeliveryResult(
                success=False,
                error=f"Erro ao enviar email: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _create_html_body(self, message: Message) -> str:
        """Cria corpo HTML do email"""
        priority_colors = {
            Priority.LOW: "#28a745",
            Priority.MEDIUM: "#ffc107",
            Priority.HIGH: "#fd7e14",
            Priority.CRITICAL: "#dc3545"
        }
        
        color = priority_colors.get(message.priority, "#28a745")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6c757d; font-size: 12px; }}
                .badge {{ background-color: {color}; color: white; padding: 4px 8px; border-radius: 3px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{message.title}</h2>
                    <span class="badge">{message.type.value.title()} - {message.priority.value.upper()}</span>
                </div>
                <div class="content">
                    <p>{message.content.replace(chr(10), '<br>')}</p>
                    <hr>
                    <p><strong>Timestamp:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
                <div class="footer">
                    <p>Enviado pelo BI Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _add_attachment(self, msg: MIMEMultipart, file_path: str):
        """Adiciona anexo ao email"""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {file_path.split("/")[-1]}'
            )
            
            msg.attach(part)
        except Exception as e:
            log_warning(f"Erro ao adicionar anexo {file_path}: {e}")

class WebhookIntegration:
    """Integração genérica com Webhooks"""
    
    def __init__(self, url: str, headers: Dict[str, str] = None, 
                 secret: str = None, auth_type: str = None):
        self.url = url
        self.headers = headers or {}
        self.secret = secret
        self.auth_type = auth_type  # 'bearer', 'basic', 'signature'
    
    def send_message(self, message: Message) -> DeliveryResult:
        """Envia via webhook"""
        try:
            # Monta payload
            payload = {
                "title": message.title,
                "content": message.content,
                "type": message.type.value,
                "priority": message.priority.value,
                "recipient": message.recipient,
                "timestamp": datetime.now().isoformat(),
                "metadata": message.metadata or {}
            }
            
            headers = self.headers.copy()
            headers['Content-Type'] = 'application/json'
            
            # Adiciona autenticação
            if self.auth_type == 'signature' and self.secret:
                signature = self._create_signature(json.dumps(payload))
                headers['X-Signature'] = signature
            elif self.auth_type == 'bearer' and self.secret:
                headers['Authorization'] = f'Bearer {self.secret}'
            
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                return DeliveryResult(
                    success=True,
                    message_id=response.headers.get('X-Message-ID'),
                    timestamp=datetime.now(),
                    response_data=response.json() if response.content else {}
                )
            else:
                return DeliveryResult(
                    success=False,
                    error=f"Webhook error: {response.status_code} - {response.text}",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            return DeliveryResult(
                success=False,
                error=f"Erro no webhook: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _create_signature(self, payload: str) -> str:
        """Cria assinatura HMAC"""
        return hmac.new(
            self.secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

class IntegrationManager:
    """Gerenciador de integrações"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.integrations: Dict[str, IntegrationConfig] = {}
        self.delivery_history: List[Dict[str, Any]] = []
        
        # Carrega configurações
        self._load_integrations()
        
        log_info("Gerenciador de integrações inicializado")
    
    def _load_integrations(self):
        """Carrega configurações de integração"""
        try:
            # Configurações padrão (podem ser sobrescritas por config)
            default_configs = {
                'slack': {
                    'enabled': False,
                    'webhook_url': '',
                    'bot_token': '',
                    'default_channel': '#general'
                },
                'teams': {
                    'enabled': False,
                    'webhook_url': ''
                },
                'email': {
                    'enabled': False,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'use_tls': True
                },
                'webhook': {
                    'enabled': False,
                    'url': '',
                    'headers': {},
                    'secret': '',
                    'auth_type': 'signature'
                }
            }
            
            # Carrega do config manager
            for integration_type, default_config in default_configs.items():
                config_key = f"integrations.{integration_type}"
                settings = self.config_manager.get_config(config_key, default_config)
                
                integration_config = IntegrationConfig(
                    id=integration_type,
                    name=integration_type.title(),
                    type=IntegrationType(integration_type),
                    enabled=settings.get('enabled', False),
                    settings=settings,
                    created_at=datetime.now()
                )
                
                self.integrations[integration_type] = integration_config
            
            log_info(f"Carregadas {len(self.integrations)} configurações de integração")
            
        except Exception as e:
            log_error(f"Erro ao carregar integrações: {e}")
    
    def update_integration(self, integration_id: str, settings: Dict[str, Any]) -> bool:
        """Atualiza configuração de integração"""
        try:
            if integration_id not in self.integrations:
                return False
            
            integration = self.integrations[integration_id]
            integration.settings.update(settings)
            integration.updated_at = datetime.now()
            
            # Salva no config manager
            config_key = f"integrations.{integration_id}"
            self.config_manager.update_config(config_key, integration.settings)
            
            log_info(f"Integração {integration_id} atualizada")
            return True
            
        except Exception as e:
            log_error(f"Erro ao atualizar integração: {e}")
            return False
    
    def send_message(self, integration_type: str, message: Message) -> DeliveryResult:
        """Envia mensagem via integração específica"""
        try:
            if integration_type not in self.integrations:
                return DeliveryResult(
                    success=False,
                    error=f"Integração {integration_type} não encontrada",
                    timestamp=datetime.now()
                )
            
            integration = self.integrations[integration_type]
            
            if not integration.enabled:
                return DeliveryResult(
                    success=False,
                    error=f"Integração {integration_type} está desabilitada",
                    timestamp=datetime.now()
                )
            
            # Cria cliente da integração
            client = self._create_integration_client(integration)
            
            if not client:
                return DeliveryResult(
                    success=False,
                    error=f"Não foi possível criar cliente para {integration_type}",
                    timestamp=datetime.now()
                )
            
            # Envia mensagem
            result = client.send_message(message)
            
            # Registra no histórico
            self._log_delivery(integration_type, message, result)
            
            return result
            
        except Exception as e:
            result = DeliveryResult(
                success=False,
                error=f"Erro ao enviar via {integration_type}: {str(e)}",
                timestamp=datetime.now()
            )
            
            self._log_delivery(integration_type, message, result)
            return result
    
    def broadcast_message(self, message: Message, 
                         integration_types: List[str] = None) -> Dict[str, DeliveryResult]:
        """Envia mensagem para múltiplas integrações"""
        results = {}
        
        # Se não especificado, usa todas as integrações habilitadas
        if not integration_types:
            integration_types = [
                integration_id for integration_id, integration in self.integrations.items()
                if integration.enabled
            ]
        
        for integration_type in integration_types:
            results[integration_type] = self.send_message(integration_type, message)
        
        return results
    
    def _create_integration_client(self, integration: IntegrationConfig):
        """Cria cliente para integração"""
        try:
            settings = integration.settings
            
            if integration.type == IntegrationType.SLACK:
                webhook_url = settings.get('webhook_url')
                bot_token = settings.get('bot_token')
                
                if not webhook_url:
                    return None
                
                return SlackIntegration(webhook_url, bot_token)
            
            elif integration.type == IntegrationType.TEAMS:
                webhook_url = settings.get('webhook_url')
                
                if not webhook_url:
                    return None
                
                return TeamsIntegration(webhook_url)
            
            elif integration.type == IntegrationType.EMAIL:
                required_fields = ['smtp_server', 'smtp_port', 'username', 'password']
                
                if not all(settings.get(field) for field in required_fields):
                    return None
                
                return EmailIntegration(
                    smtp_server=settings['smtp_server'],
                    smtp_port=settings['smtp_port'],
                    username=settings['username'],
                    password=settings['password'],
                    use_tls=settings.get('use_tls', True)
                )
            
            elif integration.type == IntegrationType.WEBHOOK:
                url = settings.get('url')
                
                if not url:
                    return None
                
                return WebhookIntegration(
                    url=url,
                    headers=settings.get('headers', {}),
                    secret=settings.get('secret'),
                    auth_type=settings.get('auth_type')
                )
            
            return None
            
        except Exception as e:
            log_error(f"Erro ao criar cliente de integração: {e}")
            return None
    
    def _log_delivery(self, integration_type: str, message: Message, result: DeliveryResult):
        """Registra entrega no histórico"""
        try:
            log_entry = {
                'integration_type': integration_type,
                'message_title': message.title,
                'message_type': message.type.value,
                'priority': message.priority.value,
                'recipient': message.recipient,
                'success': result.success,
                'error': result.error,
                'message_id': result.message_id,
                'timestamp': result.timestamp.isoformat() if result.timestamp else None
            }
            
            self.delivery_history.append(log_entry)
            
            # Limita histórico
            if len(self.delivery_history) > 1000:
                self.delivery_history = self.delivery_history[-1000:]
            
            if result.success:
                log_info(f"Mensagem enviada via {integration_type} para {message.recipient}")
            else:
                log_error(f"Falha ao enviar via {integration_type}: {result.error}")
                
        except Exception as e:
            log_error(f"Erro ao registrar entrega: {e}")
    
    def get_delivery_history(self, integration_type: str = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna histórico de entregas"""
        try:
            history = self.delivery_history.copy()
            
            if integration_type:
                history = [h for h in history if h['integration_type'] == integration_type]
            
            # Ordena por timestamp (mais recente primeiro)
            history.sort(key=lambda h: h['timestamp'] or '', reverse=True)
            
            return history[:limit]
            
        except Exception as e:
            log_error(f"Erro ao obter histórico: {e}")
            return []
    
    def test_integration(self, integration_type: str) -> DeliveryResult:
        """Testa integração"""
        try:
            test_message = Message(
                title="Teste de Integração - BI Platform",
                content="Esta é uma mensagem de teste para verificar se a integração está funcionando corretamente.",
                type=MessageType.NOTIFICATION,
                priority=Priority.LOW,
                recipient=self._get_test_recipient(integration_type)
            )
            
            return self.send_message(integration_type, test_message)
            
        except Exception as e:
            return DeliveryResult(
                success=False,
                error=f"Erro no teste de integração: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _get_test_recipient(self, integration_type: str) -> str:
        """Retorna destinatário de teste para integração"""
        integration = self.integrations.get(integration_type)
        
        if not integration:
            return "test"
        
        settings = integration.settings
        
        if integration_type == 'slack':
            return settings.get('default_channel', '#general')
        elif integration_type == 'email':
            return settings.get('username', 'test@example.com')
        else:
            return "test"
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Retorna status das integrações"""
        try:
            status = {}
            
            for integration_id, integration in self.integrations.items():
                recent_deliveries = [
                    h for h in self.delivery_history[-50:]
                    if h['integration_type'] == integration_id
                ]
                
                success_rate = 0
                if recent_deliveries:
                    successful = len([h for h in recent_deliveries if h['success']])
                    success_rate = (successful / len(recent_deliveries)) * 100
                
                status[integration_id] = {
                    'enabled': integration.enabled,
                    'configured': self._is_integration_configured(integration),
                    'recent_deliveries': len(recent_deliveries),
                    'success_rate': round(success_rate, 2),
                    'last_delivery': recent_deliveries[0]['timestamp'] if recent_deliveries else None
                }
            
            return status
            
        except Exception as e:
            log_error(f"Erro ao obter status das integrações: {e}")
            return {}
    
    def _is_integration_configured(self, integration: IntegrationConfig) -> bool:
        """Verifica se integração está configurada"""
        settings = integration.settings
        
        if integration.type == IntegrationType.SLACK:
            return bool(settings.get('webhook_url'))
        elif integration.type == IntegrationType.TEAMS:
            return bool(settings.get('webhook_url'))
        elif integration.type == IntegrationType.EMAIL:
            required = ['smtp_server', 'smtp_port', 'username', 'password']
            return all(settings.get(field) for field in required)
        elif integration.type == IntegrationType.WEBHOOK:
            return bool(settings.get('url'))
        
        return False