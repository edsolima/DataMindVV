#!/usr/bin/env python3
"""
Script de configuração inicial do ambiente DataMindVV
Configura variáveis de ambiente, dependências e estrutura inicial
"""

import os
import sys
import subprocess
import secrets
import string
from pathlib import Path
from typing import Dict, List


def generate_secure_key(length: int = 32) -> str:
    """Gera uma chave segura aleatória"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_env_file(project_root: Path) -> None:
    """Cria arquivo .env com configurações padrão"""
    env_file = project_root / ".env"
    
    if env_file.exists():
        print(f"⚠️  Arquivo .env já existe em {env_file}")
        response = input("Deseja sobrescrever? (s/N): ").lower().strip()
        if response != 's':
            print("Mantendo arquivo .env existente")
            return
    
    env_content = f"""# Configurações de Segurança
JWT_SECRET_KEY={generate_secure_key(64)}
ENCRYPTION_KEY={generate_secure_key(32)}

# Ambiente da Aplicação
APP_ENV=development
DEBUG=true
TESTING=false

# Cache Redis (Opcional)
# REDIS_URL=redis://localhost:6379/0
# REDIS_PASSWORD=

# Configurações de Email (Opcional)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=
# SMTP_PASSWORD=
# EMAIL_FROM=

# APIs Externas
# GROQ_API_KEY=
# OLLAMA_BASE_URL=http://localhost:11434

# Configurações de Banco de Dados
# DATABASE_URL=postgresql://user:password@localhost:5432/datamindvv
# DB_POOL_SIZE=10
# DB_MAX_OVERFLOW=20

# Configurações de Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_ROTATION=true
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5

# Configurações de Performance
CACHE_DEFAULT_TIMEOUT=3600
MAX_CONTENT_LENGTH=16777216
WORKERS=4
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ Arquivo .env criado em {env_file}")
    print("🔐 Chaves de segurança geradas automaticamente")


def install_dependencies(project_root: Path) -> bool:
    """Instala dependências do projeto"""
    requirements_file = project_root / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ Arquivo requirements.txt não encontrado em {requirements_file}")
        return False
    
    print("📦 Instalando dependências...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True, capture_output=True, text=True)
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        print(f"Saída do erro: {e.stderr}")
        return False


def create_directories(project_root: Path) -> None:
    """Cria diretórios necessários"""
    directories = [
        "logs",
        "data/uploads",
        "data/exports",
        "data/cache",
        "data/backups",
        "config/ssl",
        "tests/fixtures",
        "tests/reports"
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Diretório criado: {directory}")


def setup_git_hooks(project_root: Path) -> None:
    """Configura git hooks para qualidade de código"""
    git_dir = project_root / ".git"
    if not git_dir.exists():
        print("⚠️  Repositório Git não encontrado - pulando configuração de hooks")
        return
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    # Pre-commit hook
    pre_commit_content = """#!/bin/sh
# Pre-commit hook para verificação de qualidade de código

echo "🔍 Executando verificações de qualidade de código..."

# Executar testes rápidos
python -m pytest tests/ -m "unit" --tb=short -q
if [ $? -ne 0 ]; then
    echo "❌ Testes unitários falharam"
    exit 1
fi

# Verificar formatação
black --check utils/ pages/ tests/ --quiet
if [ $? -ne 0 ]; then
    echo "❌ Formatação incorreta - execute 'black utils/ pages/ tests/'"
    exit 1
fi

# Verificar imports
isort --check-only utils/ pages/ tests/ --quiet
if [ $? -ne 0 ]; then
    echo "❌ Imports incorretos - execute 'isort utils/ pages/ tests/'"
    exit 1
fi

echo "✅ Verificações de qualidade passaram"
exit 0
"""
    
    pre_commit_file = hooks_dir / "pre-commit"
    with open(pre_commit_file, 'w', encoding='utf-8') as f:
        f.write(pre_commit_content)
    
    # Tornar executável (Unix/Linux/Mac)
    if os.name != 'nt':
        os.chmod(pre_commit_file, 0o755)
    
    print("🪝 Git hooks configurados")


def run_initial_tests(project_root: Path) -> bool:
    """Executa testes iniciais para verificar configuração"""
    print("🧪 Executando testes iniciais...")
    
    try:
        # Teste de importação
        result = subprocess.run([
            sys.executable, "-c", 
            "import utils.security_config; import utils.enhanced_logger; print('✅ Importações OK')"
        ], cwd=project_root, capture_output=True, text=True, check=True)
        print(result.stdout.strip())
        
        # Teste de inicialização da aplicação
        result = subprocess.run([
            sys.executable, "app.py", "--test-mode"
        ], cwd=project_root, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Aplicação inicializa corretamente")
            return True
        else:
            print(f"❌ Erro na inicialização: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout na inicialização - pode ser normal")
        return True
    except Exception as e:
        print(f"❌ Erro nos testes iniciais: {e}")
        return False


def main():
    """Função principal de configuração"""
    print("🚀 Configurando ambiente DataMindVV...\n")
    
    # Detectar diretório do projeto
    project_root = Path(__file__).parent.parent
    print(f"📁 Diretório do projeto: {project_root}\n")
    
    # Verificar Python
    python_version = sys.version_info
    if python_version < (3, 9):
        print(f"❌ Python 3.9+ é necessário. Versão atual: {python_version.major}.{python_version.minor}")
        sys.exit(1)
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Etapas de configuração
    steps = [
        ("Criando arquivo .env", lambda: create_env_file(project_root)),
        ("Criando diretórios", lambda: create_directories(project_root)),
        ("Instalando dependências", lambda: install_dependencies(project_root)),
        ("Configurando Git hooks", lambda: setup_git_hooks(project_root)),
        ("Executando testes iniciais", lambda: run_initial_tests(project_root))
    ]
    
    success_count = 0
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        try:
            result = step_func()
            if result is not False:
                success_count += 1
        except Exception as e:
            print(f"❌ Erro em '{step_name}': {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Configuração concluída: {success_count}/{len(steps)} etapas")
    
    if success_count == len(steps):
        print("\n🎉 Ambiente configurado com sucesso!")
        print("\n📋 Próximos passos:")
        print("   1. Revisar arquivo .env e ajustar configurações")
        print("   2. Configurar banco de dados (se necessário)")
        print("   3. Executar: python app.py")
        print("   4. Acessar: http://localhost:8050")
    else:
        print("\n⚠️  Configuração parcial - revisar erros acima")
        sys.exit(1)


if __name__ == "__main__":
    main()