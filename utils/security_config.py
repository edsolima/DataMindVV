import os
import secrets
from cryptography.fernet import Fernet
from typing import Optional
from utils.logger import log_info, log_error, log_warning

class SecurityConfig:
    """
    Gerencia configurações de segurança da aplicação de forma centralizada e segura.
    """
    
    def __init__(self):
        self.environment = os.environ.get('APP_ENV', os.environ.get('ENVIRONMENT', 'development'))
        self.jwt_secret = self._get_jwt_secret()
        self.encryption_key = self._get_encryption_key()
        
    def _get_jwt_secret(self) -> str:
        """
        Obtém a chave secreta JWT de forma segura.
        Em produção, deve estar nas variáveis de ambiente.
        """
        jwt_secret = os.environ.get('JWT_SECRET')
        
        if jwt_secret:
            log_info("JWT secret carregado de variável de ambiente")
            return jwt_secret
            
        if self.environment == 'production':
            log_error("JWT_SECRET deve ser definido em produção")
            raise ValueError("JWT_SECRET must be set in production environment")
            
        # Para desenvolvimento, gera uma chave temporária
        generated_secret = secrets.token_urlsafe(32)
        log_warning("JWT secret gerado temporariamente para desenvolvimento. Configure JWT_SECRET em produção.")
        return generated_secret
        
    def _get_encryption_key(self) -> Optional[bytes]:
        """
        Obtém a chave de criptografia de forma segura.
        """
        key_str = os.environ.get('ENCRYPTION_KEY')
        
        if key_str:
            log_info("Chave de criptografia carregada de variável de ambiente")
            return key_str.encode()
            
        if self.environment == 'production':
            log_error("ENCRYPTION_KEY deve ser definido em produção")
            raise ValueError("ENCRYPTION_KEY must be set in production environment")
            
        # Para desenvolvimento, gera uma chave temporária
        generated_key = Fernet.generate_key()
        log_warning("Chave de criptografia gerada temporariamente para desenvolvimento. Configure ENCRYPTION_KEY em produção.")
        return generated_key
        
    def get_jwt_secret(self) -> str:
        """Retorna a chave secreta JWT"""
        return self.jwt_secret
        
    def get_encryption_key(self) -> Optional[bytes]:
        """Retorna a chave de criptografia"""
        return self.encryption_key
        
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção"""
        return self.environment == 'production'
        
    def validate_security_config(self) -> bool:
        """
        Valida se todas as configurações de segurança estão adequadas.
        """
        issues = []
        
        if self.is_production():
            if not os.environ.get('JWT_SECRET'):
                issues.append("JWT_SECRET não definido em produção")
            if not os.environ.get('ENCRYPTION_KEY'):
                issues.append("ENCRYPTION_KEY não definido em produção")
                
        if issues:
            for issue in issues:
                log_error(f"Problema de segurança: {issue}")
            return False
            
        log_info("Configurações de segurança validadas com sucesso")
        return True

# Instância global para uso na aplicação
security_config = SecurityConfig()