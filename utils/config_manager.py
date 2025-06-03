# utils/config_manager.py
import os
import yaml
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
# Import DatabaseManager para test_connection_config, mas dentro do método para evitar importação circular
# from utils.database_manager import DatabaseManager

class ConfigManager:
    def __init__(self):
        self.config_file = "config/connections.yml"
        self.env_file = ".env"
        self.ensure_directories()
        load_dotenv(self.env_file)

        self.encryption_key = self._get_or_create_encryption_key()
        if self.encryption_key:
            self.cipher = Fernet(self.encryption_key)
        else:
            self.cipher = None # Lidar com o caso de não ter chave (embora _get_or_create_encryption_key deva criar)
            print("ERROR: Encryption key not found or generated. Passwords will not be encrypted.")

        print("ConfigManager initialized.")


    def ensure_directories(self):
        """Ensure necessary directories exist"""
        os.makedirs("config", exist_ok=True)
        if not os.path.exists(self.env_file):
            with open(self.env_file, 'w') as f:
                f.write("# Database connection environment variables\n")
            print(f".env file created at {self.env_file}")

    def _get_or_create_encryption_key(self) -> Optional[bytes]:
        """Get existing encryption key or create a new one"""
        key_str = os.getenv("ENCRYPTION_KEY")
        if not key_str:
            try:
                key_str = Fernet.generate_key().decode()
                # set_key pode dar erro se o .env não existir ou não tiver permissão
                if os.path.exists(self.env_file):
                    set_key(self.env_file, "ENCRYPTION_KEY", key_str, quote_mode='never')
                    print("New encryption key generated and saved to .env")
                else: # Se .env não existe, apenas retorna a chave para uso em memória (menos seguro)
                    print("Warning: .env file not found. Encryption key will be in-memory.")
            except Exception as e:
                print(f"Error generating or saving encryption key: {e}")
                return None
        return key_str.encode()

    def encrypt_password(self, password: str) -> str:
        """Encrypt a password"""
        if not self.cipher or not password:
            return password # Retorna a senha original se não houver cifra ou senha
        try:
            return self.cipher.encrypt(password.encode()).decode()
        except Exception as e:
            print(f"Error encrypting password: {e}")
            return password # Retorna original em caso de erro

    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt an encrypted password"""
        if not self.cipher or not encrypted_password:
            return encrypted_password
        try:
            # Tenta descriptografar, mas se falhar (por ex, a senha não estava criptografada), retorna o original
            return self.cipher.decrypt(encrypted_password.encode()).decode()
        except Exception: # cryptography.fernet.InvalidToken or other errors
            # print(f"Could not decrypt password (it might be plaintext or wrong key): {e}")
            return encrypted_password # Assume que já está em plaintext ou é inválido

    def save_connection(self, name: str, connection_data: Dict) -> bool:
        """Save a database connection configuration"""
        try:
            connections = self.load_connections(decrypt_passwords=False) # Carregar raw para salvar
            
            # Criptografar senha antes de salvar se ela existir
            if 'password' in connection_data and connection_data['password']:
                connection_data['password'] = self.encrypt_password(connection_data['password'])
            
            connections[name] = connection_data
            with open(self.config_file, 'w') as f:
                yaml.dump(connections, f, default_flow_style=False, sort_keys=False)
            print(f"Connection '{name}' saved successfully.")
            return True
        except Exception as e:
            print(f"Error saving connection '{name}': {e}")
            return False

    def load_connections(self, decrypt_passwords: bool = True) -> Dict:
        """Load all saved connection configurations"""
        connections = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_conns = yaml.safe_load(f)
                    if loaded_conns is None: # Arquivo vazio
                        return {}
                    connections = loaded_conns
                
                if decrypt_passwords:
                    for conn_name, conn_data in connections.items():
                        if isinstance(conn_data, dict) and 'password' in conn_data and conn_data['password']:
                            conn_data['password'] = self.decrypt_password(conn_data['password'])
            except Exception as e:
                print(f"Error loading connections from {self.config_file}: {e}")
                connections = {} # Retornar vazio em caso de erro
        return connections

    def get_connection(self, connection_name: str) -> Optional[Dict]:
        """Get a specific saved connection configuration (with decrypted password)"""
        connections = self.load_connections(decrypt_passwords=True)
        return connections.get(connection_name)

    def delete_connection(self, connection_name: str) -> bool:
        """Delete a saved connection"""
        try:
            connections = self.load_connections(decrypt_passwords=False) # Carregar raw para deletar
            if connection_name in connections:
                del connections[connection_name]
                with open(self.config_file, 'w') as f:
                    yaml.dump(connections, f, default_flow_style=False, sort_keys=False)
                print(f"Connection '{connection_name}' deleted.")
                return True
            print(f"Connection '{connection_name}' not found for deletion.")
            return False
        except Exception as e:
            print(f"Error deleting connection '{connection_name}': {e}")
            return False
            
    def list_connections(self) -> List[str]:
        """List all saved connection names"""
        try:
            connections = self.load_connections(decrypt_passwords=False) # Não precisa descriptografar para listar chaves
            return list(connections.keys())
        except Exception as e:
            print(f"Error listing connections: {e}")
            return []
    
    def test_connection_config(self, connection_data_raw: Dict) -> Tuple[bool, str]:
        """Test a database connection configuration.
           Ensures password is in plaintext for testing if it came from user input.
           If it's a stored config, it would have been decrypted by get_connection.
        """
        # Import local para evitar importação circular no topo do arquivo
        from utils.database_manager import DatabaseManager
        db_manager_local = DatabaseManager() # Instância local para teste

        # Criar uma cópia para não modificar o original
        connection_data_for_test = connection_data_raw.copy()

        # Para testes, a senha deve estar em plaintext.
        # A função `get_connection` já descriptografa.
        # Se `connection_data_raw` veio direto do formulário, a senha já está em plaintext.
        # Se `connection_data_raw` veio de `load_connections(decrypt_passwords=False)`,
        # precisaríamos descriptografar aqui, mas é mais simples garantir que quem chama
        # `test_connection_config` envie a senha já descriptografada se necessário.
        # Para este método, vamos assumir que a senha em `connection_data_raw` é a que deve ser usada.

        return db_manager_local.test_connection(connection_data_for_test)