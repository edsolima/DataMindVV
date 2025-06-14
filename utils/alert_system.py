# -*- coding: utf-8 -*-
"""
Alert System - Sistema de Alertas Inteligentes
Gerencia alertas baseados em insights, anomalias e condições personalizadas
"""

import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager
from utils.insights_engine import Insight, InsightsEngine

class AlertType(Enum):
    """Tipos de alerta"""
    ANOMALY = "anomaly"
    THRESHOLD = "threshold"
    TREND = "trend"
    PATTERN = "pattern"
    FORECAST = "forecast"
    CUSTOM = "custom"

class AlertSeverity(Enum):
    """Níveis de severidade"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertChannel(Enum):
    """Canais de notificação"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    IN_APP = "in_app"

@dataclass
class AlertRule:
    """Regra de alerta"""
    id: str
    name: str
    description: str
    type: AlertType
    severity: AlertSeverity
    condition: Dict[str, Any]
    channels: List[AlertChannel]
    recipients: List[str]
    is_active: bool = True
    cooldown_minutes: int = 60
    created_at: datetime = None
    last_triggered: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Alert:
    """Alerta gerado"""
    id: str
    rule_id: str
    title: str
    message: str
    severity: AlertSeverity
    type: AlertType
    data: Dict[str, Any]
    timestamp: datetime
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

class AlertSystem:
    """Sistema de alertas inteligentes"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.insights_engine = InsightsEngine()
        
        # Armazenamento de regras e alertas
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Configurações de notificação
        self.notification_config = self._load_notification_config()
        
        # Carrega regras padrão
        self._setup_default_rules()
        
        log_info("Sistema de alertas inicializado")
    
    def _load_notification_config(self) -> Dict[str, Any]:
        """Carrega configurações de notificação"""
        try:
            config = self.config_manager.get_config()
            return config.get('notifications', {
                'email': {
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'from_email': ''
                },
                'slack': {
                    'webhook_url': '',
                    'channel': '#alerts'
                },
                'teams': {
                    'webhook_url': ''
                },
                'webhooks': []
            })
        except Exception as e:
            log_error(f"Erro ao carregar configurações de notificação: {e}")
            return {}
    
    def _setup_default_rules(self):
        """Configura regras de alerta padrão"""
        default_rules = [
            AlertRule(
                id="anomaly_detection",
                name="Detecção de Anomalias",
                description="Alerta quando anomalias são detectadas nos dados",
                type=AlertType.ANOMALY,
                severity=AlertSeverity.HIGH,
                condition={'min_anomalies': 3, 'confidence_threshold': 0.8},
                channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
                recipients=['admin@empresa.com']
            ),
            AlertRule(
                id="critical_trend",
                name="Tendência Crítica",
                description="Alerta para tendências críticas (declínio acentuado)",
                type=AlertType.TREND,
                severity=AlertSeverity.CRITICAL,
                condition={'direction': 'down', 'strength_threshold': 0.8},
                channels=[AlertChannel.IN_APP, AlertChannel.EMAIL, AlertChannel.SLACK],
                recipients=['admin@empresa.com', 'manager@empresa.com']
            ),
            AlertRule(
                id="data_quality",
                name="Qualidade dos Dados",
                description="Alerta para problemas de qualidade dos dados",
                type=AlertType.CUSTOM,
                severity=AlertSeverity.MEDIUM,
                condition={'missing_data_threshold': 0.3, 'duplicate_threshold': 0.1},
                channels=[AlertChannel.IN_APP],
                recipients=['data_team@empresa.com']
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.id] = rule
    
    def add_alert_rule(self, rule: AlertRule) -> bool:
        """Adiciona nova regra de alerta"""
        try:
            self.alert_rules[rule.id] = rule
            log_info(f"Regra de alerta adicionada: {rule.name}")
            return True
        except Exception as e:
            log_error(f"Erro ao adicionar regra de alerta: {e}")
            return False
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove regra de alerta"""
        try:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                log_info(f"Regra de alerta removida: {rule_id}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao remover regra de alerta: {e}")
            return False
    
    def update_alert_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza regra de alerta"""
        try:
            if rule_id not in self.alert_rules:
                return False
            
            rule = self.alert_rules[rule_id]
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            log_info(f"Regra de alerta atualizada: {rule_id}")
            return True
        except Exception as e:
            log_error(f"Erro ao atualizar regra de alerta: {e}")
            return False
    
    def check_insights_for_alerts(self, insights: List[Insight]):
        """Verifica insights e gera alertas conforme necessário"""
        for insight in insights:
            self._evaluate_insight_against_rules(insight)
    
    def _evaluate_insight_against_rules(self, insight: Insight):
        """Avalia um insight contra todas as regras ativas"""
        for rule in self.alert_rules.values():
            if not rule.is_active:
                continue
            
            # Verifica cooldown
            if self._is_in_cooldown(rule):
                continue
            
            # Avalia condição
            if self._evaluate_rule_condition(rule, insight):
                alert = self._create_alert_from_insight(rule, insight)
                self._trigger_alert(alert)
    
    def _is_in_cooldown(self, rule: AlertRule) -> bool:
        """Verifica se a regra está em período de cooldown"""
        if rule.last_triggered is None:
            return False
        
        cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
        return datetime.now() < cooldown_end
    
    def _evaluate_rule_condition(self, rule: AlertRule, insight: Insight) -> bool:
        """Avalia se um insight satisfaz a condição da regra"""
        try:
            if rule.type == AlertType.ANOMALY and insight.type == "anomaly":
                return self._evaluate_anomaly_condition(rule, insight)
            
            elif rule.type == AlertType.TREND and insight.type == "trend":
                return self._evaluate_trend_condition(rule, insight)
            
            elif rule.type == AlertType.PATTERN and insight.type == "pattern":
                return self._evaluate_pattern_condition(rule, insight)
            
            elif rule.type == AlertType.FORECAST and insight.type == "forecast":
                return self._evaluate_forecast_condition(rule, insight)
            
            elif rule.type == AlertType.CUSTOM:
                return self._evaluate_custom_condition(rule, insight)
            
            return False
        
        except Exception as e:
            log_error(f"Erro ao avaliar condição da regra {rule.id}: {e}")
            return False
    
    def _evaluate_anomaly_condition(self, rule: AlertRule, insight: Insight) -> bool:
        """Avalia condição para alertas de anomalia"""
        condition = rule.condition
        
        # Verifica número mínimo de anomalias
        min_anomalies = condition.get('min_anomalies', 1)
        anomaly_count = insight.metadata.get('count', 0)
        
        if anomaly_count < min_anomalies:
            return False
        
        # Verifica threshold de confiança
        confidence_threshold = condition.get('confidence_threshold', 0.5)
        if insight.confidence < confidence_threshold:
            return False
        
        # Verifica severidade mínima
        min_severity = condition.get('min_severity', 'low')
        severity_order = ['low', 'medium', 'high', 'critical']
        
        if severity_order.index(insight.severity) < severity_order.index(min_severity):
            return False
        
        return True
    
    def _evaluate_trend_condition(self, rule: AlertRule, insight: Insight) -> bool:
        """Avalia condição para alertas de tendência"""
        condition = rule.condition
        
        # Verifica direção da tendência
        required_direction = condition.get('direction')
        if required_direction and insight.metadata.get('direction') != required_direction:
            return False
        
        # Verifica força da tendência
        strength_threshold = condition.get('strength_threshold', 0.5)
        if insight.metadata.get('strength', 0) < strength_threshold:
            return False
        
        # Verifica duração mínima
        min_duration = condition.get('min_duration_days', 0)
        if insight.metadata.get('duration', 0) < min_duration:
            return False
        
        return True
    
    def _evaluate_pattern_condition(self, rule: AlertRule, insight: Insight) -> bool:
        """Avalia condição para alertas de padrão"""
        condition = rule.condition
        
        # Verifica tipo de padrão
        required_pattern = condition.get('pattern_type')
        if required_pattern and insight.metadata.get('pattern_type') != required_pattern:
            return False
        
        return True
    
    def _evaluate_forecast_condition(self, rule: AlertRule, insight: Insight) -> bool:
        """Avalia condição para alertas de previsão"""
        condition = rule.condition
        
        # Verifica mudança percentual
        change_threshold = condition.get('change_threshold_percent', 10)
        change_percent = abs(insight.metadata.get('change_percent', 0))
        
        return change_percent >= change_threshold
    
    def _evaluate_custom_condition(self, rule: AlertRule, insight: Insight) -> bool:
        """Avalia condição customizada"""
        # Implementação básica - pode ser expandida
        return True
    
    def _create_alert_from_insight(self, rule: AlertRule, insight: Insight) -> Alert:
        """Cria alerta baseado em insight"""
        alert_id = f"alert_{rule.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return Alert(
            id=alert_id,
            rule_id=rule.id,
            title=f"[{rule.severity.value.upper()}] {insight.title}",
            message=self._format_alert_message(rule, insight),
            severity=rule.severity,
            type=rule.type,
            data={
                'insight': asdict(insight),
                'rule': asdict(rule)
            },
            timestamp=datetime.now()
        )
    
    def _format_alert_message(self, rule: AlertRule, insight: Insight) -> str:
        """Formata mensagem do alerta"""
        message = f"**Alerta: {rule.name}**\n\n"
        message += f"**Descrição:** {insight.description}\n\n"
        message += f"**Fonte de Dados:** {insight.data_source}\n"
        message += f"**Confiança:** {insight.confidence:.2%}\n"
        message += f"**Timestamp:** {insight.timestamp.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        
        if insight.recommendations:
            message += "**Recomendações:**\n"
            for rec in insight.recommendations:
                message += f"• {rec}\n"
        
        return message
    
    def _trigger_alert(self, alert: Alert):
        """Dispara um alerta"""
        try:
            # Adiciona aos alertas ativos
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            
            # Atualiza timestamp da regra
            if alert.rule_id in self.alert_rules:
                self.alert_rules[alert.rule_id].last_triggered = alert.timestamp
            
            # Envia notificações
            rule = self.alert_rules.get(alert.rule_id)
            if rule:
                self._send_notifications(alert, rule)
            
            log_info(f"Alerta disparado: {alert.title}")
            
        except Exception as e:
            log_error(f"Erro ao disparar alerta: {e}")
    
    def _send_notifications(self, alert: Alert, rule: AlertRule):
        """Envia notificações pelos canais configurados"""
        for channel in rule.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email_notification(alert, rule)
                elif channel == AlertChannel.SLACK:
                    self._send_slack_notification(alert, rule)
                elif channel == AlertChannel.TEAMS:
                    self._send_teams_notification(alert, rule)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_notification(alert, rule)
                elif channel == AlertChannel.IN_APP:
                    # Notificação in-app já está no sistema
                    pass
                    
            except Exception as e:
                log_error(f"Erro ao enviar notificação via {channel.value}: {e}")
    
    def _send_email_notification(self, alert: Alert, rule: AlertRule):
        """Envia notificação por email"""
        email_config = self.notification_config.get('email', {})
        
        if not email_config.get('username') or not email_config.get('password'):
            log_warning("Configuração de email não encontrada")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['Subject'] = f"[BI Alert] {alert.title}"
            
            body = alert.message
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            for recipient in rule.recipients:
                msg['To'] = recipient
                server.send_message(msg)
                del msg['To']
            
            server.quit()
            log_info(f"Email enviado para {len(rule.recipients)} destinatários")
            
        except Exception as e:
            log_error(f"Erro ao enviar email: {e}")
    
    def _send_slack_notification(self, alert: Alert, rule: AlertRule):
        """Envia notificação para Slack"""
        slack_config = self.notification_config.get('slack', {})
        webhook_url = slack_config.get('webhook_url')
        
        if not webhook_url:
            log_warning("URL do webhook do Slack não configurada")
            return
        
        try:
            import requests
            
            payload = {
                'channel': slack_config.get('channel', '#alerts'),
                'username': 'BI Alert Bot',
                'text': alert.title,
                'attachments': [{
                    'color': self._get_slack_color(alert.severity),
                    'fields': [
                        {'title': 'Severidade', 'value': alert.severity.value, 'short': True},
                        {'title': 'Tipo', 'value': alert.type.value, 'short': True},
                        {'title': 'Timestamp', 'value': alert.timestamp.strftime('%d/%m/%Y %H:%M:%S'), 'short': True}
                    ],
                    'text': alert.message
                }]
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
            log_info("Notificação enviada para Slack")
            
        except Exception as e:
            log_error(f"Erro ao enviar notificação para Slack: {e}")
    
    def _send_teams_notification(self, alert: Alert, rule: AlertRule):
        """Envia notificação para Microsoft Teams"""
        teams_config = self.notification_config.get('teams', {})
        webhook_url = teams_config.get('webhook_url')
        
        if not webhook_url:
            log_warning("URL do webhook do Teams não configurada")
            return
        
        try:
            import requests
            
            payload = {
                '@type': 'MessageCard',
                '@context': 'http://schema.org/extensions',
                'themeColor': self._get_teams_color(alert.severity),
                'summary': alert.title,
                'sections': [{
                    'activityTitle': alert.title,
                    'activitySubtitle': f"Severidade: {alert.severity.value}",
                    'text': alert.message,
                    'facts': [
                        {'name': 'Tipo', 'value': alert.type.value},
                        {'name': 'Timestamp', 'value': alert.timestamp.strftime('%d/%m/%Y %H:%M:%S')}
                    ]
                }]
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
            log_info("Notificação enviada para Teams")
            
        except Exception as e:
            log_error(f"Erro ao enviar notificação para Teams: {e}")
    
    def _send_webhook_notification(self, alert: Alert, rule: AlertRule):
        """Envia notificação via webhook customizado"""
        webhooks = self.notification_config.get('webhooks', [])
        
        if not webhooks:
            return
        
        try:
            import requests
            
            payload = {
                'alert_id': alert.id,
                'rule_id': alert.rule_id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity.value,
                'type': alert.type.value,
                'timestamp': alert.timestamp.isoformat(),
                'data': alert.data
            }
            
            for webhook_url in webhooks:
                response = requests.post(webhook_url, json=payload)
                response.raise_for_status()
            
            log_info(f"Webhook enviado para {len(webhooks)} URLs")
            
        except Exception as e:
            log_error(f"Erro ao enviar webhook: {e}")
    
    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """Retorna cor para Slack baseada na severidade"""
        colors = {
            AlertSeverity.LOW: 'good',
            AlertSeverity.MEDIUM: 'warning',
            AlertSeverity.HIGH: 'danger',
            AlertSeverity.CRITICAL: '#ff0000'
        }
        return colors.get(severity, 'good')
    
    def _get_teams_color(self, severity: AlertSeverity) -> str:
        """Retorna cor para Teams baseada na severidade"""
        colors = {
            AlertSeverity.LOW: '00FF00',
            AlertSeverity.MEDIUM: 'FFA500',
            AlertSeverity.HIGH: 'FF4500',
            AlertSeverity.CRITICAL: 'FF0000'
        }
        return colors.get(severity, '00FF00')
    
    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Reconhece um alerta"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.now()
                
                log_info(f"Alerta {alert_id} reconhecido por {user}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao reconhecer alerta: {e}")
            return False
    
    def resolve_alert(self, alert_id: str, user: str) -> bool:
        """Resolve um alerta"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.is_resolved = True
                alert.resolved_at = datetime.now()
                
                # Remove dos alertas ativos
                del self.active_alerts[alert_id]
                
                log_info(f"Alerta {alert_id} resolvido por {user}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao resolver alerta: {e}")
            return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Retorna alertas ativos"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Retorna histórico de alertas"""
        return self.alert_history[-limit:]
    
    def get_alert_rules(self) -> List[AlertRule]:
        """Retorna todas as regras de alerta"""
        return list(self.alert_rules.values())
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos alertas"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        
        # Estatísticas por severidade
        by_severity = {}
        for alert in self.alert_history:
            severity = alert.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Estatísticas por tipo
        by_type = {}
        for alert in self.alert_history:
            alert_type = alert.type.value
            by_type[alert_type] = by_type.get(alert_type, 0) + 1
        
        # Alertas por dia (últimos 7 dias)
        recent_alerts = []
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        for alert in self.alert_history:
            if alert.timestamp >= seven_days_ago:
                recent_alerts.append(alert)
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': total_alerts - active_alerts,
            'by_severity': by_severity,
            'by_type': by_type,
            'recent_alerts_7_days': len(recent_alerts),
            'total_rules': len(self.alert_rules),
            'active_rules': len([r for r in self.alert_rules.values() if r.is_active])
        }