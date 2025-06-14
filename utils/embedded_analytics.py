# -*- coding: utf-8 -*-
"""
Embedded Analytics - Sistema de Análises Embutidas
Permite incorporar visualizações e dashboards em aplicações externas
"""

import json
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urlencode
from flask import Flask, request, jsonify, render_template_string

from utils.logger import log_info, log_error, log_warning
from utils.config_manager import ConfigManager
from utils.database_manager import DatabaseManager

@dataclass
class EmbedToken:
    """Token para acesso embarcado"""
    token_id: str
    user_id: str
    dashboard_id: Optional[str]
    chart_id: Optional[str]
    permissions: List[str]
    expires_at: datetime
    domain_whitelist: List[str]
    created_at: datetime
    is_active: bool = True

@dataclass
class EmbedConfig:
    """Configuração de incorporação"""
    id: str
    name: str
    type: str  # 'dashboard', 'chart', 'report'
    resource_id: str
    allowed_domains: List[str]
    theme: str
    width: Optional[str] = None
    height: Optional[str] = None
    auto_refresh: bool = False
    refresh_interval: int = 300  # segundos
    show_toolbar: bool = True
    show_filters: bool = True
    interactive: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class EmbeddedAnalytics:
    """Sistema de análises embutidas"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager()
        
        # Armazenamento de tokens e configurações
        self.embed_tokens: Dict[str, EmbedToken] = {}
        self.embed_configs: Dict[str, EmbedConfig] = {}
        
        # Configurações de segurança
        self.secret_key = self._get_secret_key()
        self.token_expiry_hours = 24
        
        log_info("Sistema de análises embutidas inicializado")
    
    def _get_secret_key(self) -> str:
        """Obtém chave secreta para JWT de forma segura"""
        try:
            from utils.security_config import security_config
            return security_config.get_jwt_secret()
        except Exception as e:
            log_error("Erro ao obter chave JWT segura", extra={"error": str(e)})
            raise ValueError("Não foi possível obter chave JWT segura")
    
    def create_embed_config(self, config: EmbedConfig) -> bool:
        """Cria configuração de incorporação"""
        try:
            self.embed_configs[config.id] = config
            log_info(f"Configuração de incorporação criada: {config.name}")
            return True
        except Exception as e:
            log_error(f"Erro ao criar configuração de incorporação: {e}")
            return False
    
    def generate_embed_token(self, user_id: str, resource_type: str, 
                           resource_id: str, permissions: List[str],
                           domain_whitelist: List[str] = None) -> Optional[str]:
        """Gera token para acesso embarcado"""
        try:
            token_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=self.token_expiry_hours)
            
            # Cria token interno
            embed_token = EmbedToken(
                token_id=token_id,
                user_id=user_id,
                dashboard_id=resource_id if resource_type == 'dashboard' else None,
                chart_id=resource_id if resource_type == 'chart' else None,
                permissions=permissions,
                expires_at=expires_at,
                domain_whitelist=domain_whitelist or [],
                created_at=datetime.now()
            )
            
            self.embed_tokens[token_id] = embed_token
            
            # Cria JWT
            payload = {
                'token_id': token_id,
                'user_id': user_id,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'permissions': permissions,
                'exp': expires_at.timestamp(),
                'iat': datetime.now().timestamp()
            }
            
            jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            
            log_info(f"Token de incorporação gerado para usuário {user_id}")
            return jwt_token
            
        except Exception as e:
            log_error(f"Erro ao gerar token de incorporação: {e}")
            return None
    
    def validate_embed_token(self, token: str, domain: str = None) -> Optional[Dict[str, Any]]:
        """Valida token de incorporação"""
        try:
            # Decodifica JWT
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_id = payload.get('token_id')
            
            # Verifica se token existe
            if token_id not in self.embed_tokens:
                log_warning(f"Token não encontrado: {token_id}")
                return None
            
            embed_token = self.embed_tokens[token_id]
            
            # Verifica se token está ativo
            if not embed_token.is_active:
                log_warning(f"Token inativo: {token_id}")
                return None
            
            # Verifica expiração
            if datetime.now() > embed_token.expires_at:
                log_warning(f"Token expirado: {token_id}")
                return None
            
            # Verifica domínio se especificado
            if domain and embed_token.domain_whitelist:
                if not any(allowed in domain for allowed in embed_token.domain_whitelist):
                    log_warning(f"Domínio não autorizado: {domain}")
                    return None
            
            return {
                'token_id': token_id,
                'user_id': embed_token.user_id,
                'permissions': embed_token.permissions,
                'resource_type': 'dashboard' if embed_token.dashboard_id else 'chart',
                'resource_id': embed_token.dashboard_id or embed_token.chart_id
            }
            
        except jwt.ExpiredSignatureError:
            log_warning("Token JWT expirado")
            return None
        except jwt.InvalidTokenError as e:
            log_warning(f"Token JWT inválido: {e}")
            return None
        except Exception as e:
            log_error(f"Erro ao validar token: {e}")
            return None
    
    def revoke_embed_token(self, token_id: str) -> bool:
        """Revoga token de incorporação"""
        try:
            if token_id in self.embed_tokens:
                self.embed_tokens[token_id].is_active = False
                log_info(f"Token revogado: {token_id}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao revogar token: {e}")
            return False
    
    def generate_embed_url(self, config_id: str, token: str, 
                          base_url: str = "http://localhost:8050") -> str:
        """Gera URL para incorporação"""
        try:
            if config_id not in self.embed_configs:
                raise ValueError(f"Configuração não encontrada: {config_id}")
            
            config = self.embed_configs[config_id]
            
            params = {
                'token': token,
                'config': config_id,
                'theme': config.theme
            }
            
            if config.auto_refresh:
                params['refresh'] = config.refresh_interval
            
            if not config.show_toolbar:
                params['toolbar'] = 'false'
            
            if not config.show_filters:
                params['filters'] = 'false'
            
            if not config.interactive:
                params['interactive'] = 'false'
            
            url = f"{base_url}/embed/{config.type}/{config.resource_id}?{urlencode(params)}"
            
            log_info(f"URL de incorporação gerada para config {config_id}")
            return url
            
        except Exception as e:
            log_error(f"Erro ao gerar URL de incorporação: {e}")
            return ""
    
    def generate_iframe_code(self, config_id: str, token: str, 
                           base_url: str = "http://localhost:8050") -> str:
        """Gera código HTML do iframe"""
        try:
            if config_id not in self.embed_configs:
                raise ValueError(f"Configuração não encontrada: {config_id}")
            
            config = self.embed_configs[config_id]
            embed_url = self.generate_embed_url(config_id, token, base_url)
            
            width = config.width or "100%"
            height = config.height or "600px"
            
            iframe_code = f'''
<iframe 
    src="{embed_url}"
    width="{width}"
    height="{height}"
    frameborder="0"
    allowtransparency="true"
    sandbox="allow-scripts allow-same-origin allow-forms"
    title="{config.name}">
</iframe>
'''.strip()
            
            log_info(f"Código iframe gerado para config {config_id}")
            return iframe_code
            
        except Exception as e:
            log_error(f"Erro ao gerar código iframe: {e}")
            return ""
    
    def generate_javascript_embed(self, config_id: str, token: str,
                                container_id: str = "bi-embed",
                                base_url: str = "http://localhost:8050") -> str:
        """Gera código JavaScript para incorporação"""
        try:
            if config_id not in self.embed_configs:
                raise ValueError(f"Configuração não encontrada: {config_id}")
            
            config = self.embed_configs[config_id]
            embed_url = self.generate_embed_url(config_id, token, base_url)
            
            width = config.width or "100%"
            height = config.height or "600px"
            
            js_code = f'''
(function() {{
    var container = document.getElementById('{container_id}');
    if (!container) {{
        console.error('Container {container_id} não encontrado');
        return;
    }}
    
    var iframe = document.createElement('iframe');
    iframe.src = '{embed_url}';
    iframe.width = '{width}';
    iframe.height = '{height}';
    iframe.frameBorder = '0';
    iframe.allowTransparency = 'true';
    iframe.sandbox = 'allow-scripts allow-same-origin allow-forms';
    iframe.title = '{config.name}';
    
    // Adiciona estilos responsivos
    iframe.style.maxWidth = '100%';
    iframe.style.border = 'none';
    
    container.appendChild(iframe);
    
    // Auto-refresh se configurado
    {f'''
    if ({str(config.auto_refresh).lower()}) {{
        setInterval(function() {{
            iframe.src = iframe.src;
        }}, {config.refresh_interval * 1000});
    }}''' if config.auto_refresh else ''}
    
    // Comunicação com iframe (opcional)
    window.addEventListener('message', function(event) {{
        if (event.origin !== '{base_url}') return;
        
        // Processa mensagens do iframe
        if (event.data.type === 'resize') {{
            iframe.height = event.data.height + 'px';
        }}
    }});
}})();
'''.strip()
            
            log_info(f"Código JavaScript gerado para config {config_id}")
            return js_code
            
        except Exception as e:
            log_error(f"Erro ao gerar código JavaScript: {e}")
            return ""
    
    def get_embed_analytics(self, config_id: str = None) -> Dict[str, Any]:
        """Retorna analytics de incorporação"""
        try:
            # Estatísticas gerais
            total_configs = len(self.embed_configs)
            total_tokens = len(self.embed_tokens)
            active_tokens = len([t for t in self.embed_tokens.values() if t.is_active])
            expired_tokens = len([t for t in self.embed_tokens.values() 
                                if datetime.now() > t.expires_at])
            
            # Estatísticas por configuração
            config_stats = {}
            if config_id and config_id in self.embed_configs:
                config = self.embed_configs[config_id]
                config_tokens = [t for t in self.embed_tokens.values() 
                               if (t.dashboard_id == config.resource_id or 
                                   t.chart_id == config.resource_id)]
                
                config_stats = {
                    'name': config.name,
                    'type': config.type,
                    'total_tokens': len(config_tokens),
                    'active_tokens': len([t for t in config_tokens if t.is_active]),
                    'domains': config.allowed_domains
                }
            
            # Tokens por usuário
            user_stats = {}
            for token in self.embed_tokens.values():
                user_id = token.user_id
                if user_id not in user_stats:
                    user_stats[user_id] = {'total': 0, 'active': 0}
                user_stats[user_id]['total'] += 1
                if token.is_active:
                    user_stats[user_id]['active'] += 1
            
            return {
                'total_configs': total_configs,
                'total_tokens': total_tokens,
                'active_tokens': active_tokens,
                'expired_tokens': expired_tokens,
                'config_stats': config_stats,
                'user_stats': user_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(f"Erro ao obter analytics de incorporação: {e}")
            return {}
    
    def cleanup_expired_tokens(self) -> int:
        """Remove tokens expirados"""
        try:
            expired_count = 0
            current_time = datetime.now()
            
            expired_tokens = []
            for token_id, token in self.embed_tokens.items():
                if current_time > token.expires_at:
                    expired_tokens.append(token_id)
            
            for token_id in expired_tokens:
                del self.embed_tokens[token_id]
                expired_count += 1
            
            if expired_count > 0:
                log_info(f"Removidos {expired_count} tokens expirados")
            
            return expired_count
            
        except Exception as e:
            log_error(f"Erro ao limpar tokens expirados: {e}")
            return 0
    
    def get_embed_config(self, config_id: str) -> Optional[EmbedConfig]:
        """Retorna configuração de incorporação"""
        return self.embed_configs.get(config_id)
    
    def update_embed_config(self, config_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza configuração de incorporação"""
        try:
            if config_id not in self.embed_configs:
                return False
            
            config = self.embed_configs[config_id]
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            log_info(f"Configuração de incorporação atualizada: {config_id}")
            return True
        except Exception as e:
            log_error(f"Erro ao atualizar configuração: {e}")
            return False
    
    def delete_embed_config(self, config_id: str) -> bool:
        """Remove configuração de incorporação"""
        try:
            if config_id in self.embed_configs:
                del self.embed_configs[config_id]
                log_info(f"Configuração de incorporação removida: {config_id}")
                return True
            return False
        except Exception as e:
            log_error(f"Erro ao remover configuração: {e}")
            return False
    
    def list_embed_configs(self) -> List[EmbedConfig]:
        """Lista todas as configurações de incorporação"""
        return list(self.embed_configs.values())
    
    def generate_embed_preview(self, config_id: str, token: str) -> str:
        """Gera página de preview para incorporação"""
        try:
            if config_id not in self.embed_configs:
                return "<h1>Configuração não encontrada</h1>"
            
            config = self.embed_configs[config_id]
            iframe_code = self.generate_iframe_code(config_id, token)
            
            preview_html = f'''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview - {config.name}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .content {{
            padding: 20px;
        }}
        .embed-container {{
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
        }}
        .info {{
            background: #ecf0f1;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }}
        .code-block {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            overflow-x: auto;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Preview: {config.name}</h1>
            <p>Tipo: {config.type.title()} | Recurso: {config.resource_id}</p>
        </div>
        <div class="content">
            <div class="info">
                <strong>Informações da Incorporação:</strong><br>
                • Domínios permitidos: {', '.join(config.allowed_domains) if config.allowed_domains else 'Todos'}<br>
                • Tema: {config.theme}<br>
                • Auto-refresh: {'Sim' if config.auto_refresh else 'Não'}<br>
                • Interativo: {'Sim' if config.interactive else 'Não'}
            </div>
            
            <div class="embed-container">
                {iframe_code}
            </div>
            
            <div class="code-block">
                <strong>Código para incorporação:</strong><br><br>
                {iframe_code.replace('<', '&lt;').replace('>', '&gt;')}
            </div>
        </div>
    </div>
</body>
</html>
'''.strip()
            
            return preview_html
            
        except Exception as e:
            log_error(f"Erro ao gerar preview: {e}")
            return f"<h1>Erro ao gerar preview: {e}</h1>"