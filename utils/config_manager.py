# utils/config_manager.py
import os
import yaml
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
from utils.logger import log_info, log_error, log_warning, log_debug
# Import DatabaseManager para test_connection_config, mas dentro do método para evitar importação circular
# from utils.database_manager import DatabaseManager

class ConfigManager:
    """
    Gerencia configurações de conexões com bancos de dados, incluindo criptografia de senhas,
    persistência em arquivo YAML e gerenciamento seguro de chaves.
    """
    def __init__(self):
        """
        Inicializa o ConfigManager, garantindo diretórios, carregando variáveis de ambiente e
        preparando a chave de criptografia.
        """
        self.config_file = "config/connections.yml"
        self.env_file = ".env"
        self.ensure_directories()
        load_dotenv(self.env_file)

        self.encryption_key = self._get_or_create_encryption_key()
        if self.encryption_key:
            self.cipher = Fernet(self.encryption_key)
            log_info("ConfigManager inicializado com criptografia habilitada")
        else:
            self.cipher = None # Lidar com o caso de não ter chave (embora _get_or_create_encryption_key deva criar)
            log_error("Chave de criptografia não encontrada ou gerada - senhas não serão criptografadas")

        log_info("ConfigManager inicializado", extra={"config_file": self.config_file, "env_file": self.env_file})

    def ensure_directories(self):
        """
        Garante que o diretório de configuração e o arquivo .env existam.
        """
        os.makedirs("config", exist_ok=True)
        if not os.path.exists(self.env_file):
            with open(self.env_file, 'w') as f:
                f.write("# Database connection environment variables\n")
            log_info("Arquivo .env criado", extra={"file_path": self.env_file})

    def _get_or_create_encryption_key(self) -> Optional[bytes]:
        """
        Obtém a chave de criptografia de variável de ambiente ou .env, ou gera uma nova se necessário.
        Prioriza variáveis de ambiente para produção.
        """
        key_str = os.environ.get("ENCRYPTION_KEY")
        if key_str:
            log_info("Chave de criptografia carregada de variável de ambiente ENCRYPTION_KEY (recomendado para produção)")
            return key_str.encode()
        # Se não está na env-var, tenta .env
        key_str = os.getenv("ENCRYPTION_KEY")
        if key_str:
            log_warning("Chave de criptografia carregada do .env. Para produção, use variável de ambiente ENCRYPTION_KEY.")
            return key_str.encode()
        # Se não existe, gera e salva no .env (apenas para desenvolvimento/local)
        try:
            key_str = Fernet.generate_key().decode()
            if os.path.exists(self.env_file):
                set_key(self.env_file, "ENCRYPTION_KEY", key_str, quote_mode='never')
                log_warning("Nova chave de criptografia gerada e salva no .env. Para produção, configure ENCRYPTION_KEY como variável de ambiente.")
            else:
                log_error("Arquivo .env não encontrado - chave de criptografia será mantida apenas em memória (NÃO RECOMENDADO)")
            return key_str.encode()
        except Exception as e:
            log_error("Erro ao gerar ou salvar chave de criptografia", extra={"error": str(e)}, exc_info=True)
            return None

    def encrypt_password(self, password: str) -> str:
        """
        Criptografa uma senha usando a chave do ConfigManager.
        Retorna a senha original se não houver cifra ou senha.
        """
        if not self.cipher or not password:
            return password
        try:
            encrypted = self.cipher.encrypt(password.encode()).decode()
            log_debug("Senha criptografada com sucesso")
            return encrypted
        except Exception as e:
            log_error("Erro ao criptografar senha", extra={"error": str(e)}, exc_info=True)
            return password

    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Descriptografa uma senha criptografada. Se não for possível, retorna o valor original.
        """
        if not self.cipher or not encrypted_password:
            return encrypted_password
        try:
            decrypted = self.cipher.decrypt(encrypted_password.encode()).decode()
            log_debug("Senha descriptografada com sucesso")
            return decrypted
        except Exception as e:
            log_debug("Não foi possível descriptografar senha - pode ser texto plano", extra={"error": str(e)})
            return encrypted_password

    def save_connection(self, name: str, connection_data: Dict) -> bool:
        """
        Salva uma configuração de conexão de banco de dados, criptografando a senha.
        """
        try:
            connections = self.load_connections(decrypt_passwords=False)
            if 'password' in connection_data and connection_data['password']:
                connection_data['password'] = self.encrypt_password(connection_data['password'])
            connections[name] = connection_data
            with open(self.config_file, 'w') as f:
                yaml.dump(connections, f, default_flow_style=False, sort_keys=False)
            log_info("Conexão salva com sucesso", extra={"connection_name": name, "db_type": connection_data.get('db_type', 'unknown')})
            return True
        except Exception as e:
            log_error("Erro ao salvar conexão", extra={"connection_name": name, "error": str(e)}, exc_info=True)
            return False

    def load_connections(self, decrypt_passwords: bool = True) -> Dict:
        """
        Carrega todas as configurações de conexão salvas.
        Se decrypt_passwords=True, descriptografa as senhas.
        """
        connections = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_conns = yaml.safe_load(f)
                    if loaded_conns is None:
                        return {}
                    connections = loaded_conns
                if decrypt_passwords:
                    for conn_name, conn_data in connections.items():
                        if isinstance(conn_data, dict) and 'password' in conn_data and conn_data['password']:
                            conn_data['password'] = self.decrypt_password(conn_data['password'])
            except Exception as e:
                log_error("Erro ao carregar conexões", extra={"config_file": self.config_file, "error": str(e)}, exc_info=True)
                connections = {}
        return connections

    def get_connection(self, connection_name: str) -> Optional[Dict]:
        """
        Retorna a configuração de conexão salva (com senha descriptografada) para o nome informado.
        """
        connections = self.load_connections(decrypt_passwords=True)
        return connections.get(connection_name)

    def delete_connection(self, connection_name: str) -> bool:
        """
        Remove uma configuração de conexão salva pelo nome.
        """
        try:
            connections = self.load_connections(decrypt_passwords=False)
            if connection_name in connections:
                del connections[connection_name]
                with open(self.config_file, 'w') as f:
                    yaml.dump(connections, f, default_flow_style=False, sort_keys=False)
                log_info("Conexão deletada com sucesso", extra={"connection_name": connection_name})
                return True
            log_warning("Conexão não encontrada para deleção", extra={"connection_name": connection_name})
            return False
        except Exception as e:
            log_error("Erro ao deletar conexão", extra={"connection_name": connection_name, "error": str(e)}, exc_info=True)
            return False
            
    def list_connections(self) -> List[str]:
        """
        Lista todos os nomes de conexões salvas.
        """
        try:
            connections = self.load_connections(decrypt_passwords=False)
            return list(connections.keys())
        except Exception as e:
            log_error("Erro ao listar conexões", extra={"error": str(e)}, exc_info=True)
            return []
    
    def test_connection_config(self, connection_data_raw: Dict) -> Tuple[bool, str]:
        """
        Testa uma configuração de conexão de banco de dados.
        A senha deve estar em texto plano (já descriptografada).
        """
        from utils.database_manager import DatabaseManager
        db_manager_local = DatabaseManager()
        connection_data_for_test = connection_data_raw.copy()
        return db_manager_local.test_connection(connection_data_for_test)