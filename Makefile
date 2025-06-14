# Makefile para DataMindVV
# Automatiza tarefas comuns de desenvolvimento

.PHONY: help install setup test test-unit test-integration test-security test-performance
.PHONY: lint format check security clean run dev build deploy
.PHONY: docs coverage report logs backup

# Configurações
PYTHON := python
PIP := pip
PYTEST := pytest
PORT := 8050
HOST := 0.0.0.0

# Cores para output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RESET := \033[0m

# Help
help: ## Mostra esta ajuda
	@echo "$(CYAN)DataMindVV - Comandos Disponíveis$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Exemplos de uso:$(RESET)"
	@echo "  make setup     # Configuração inicial completa"
	@echo "  make test      # Executar todos os testes"
	@echo "  make run       # Executar aplicação"
	@echo "  make lint      # Verificar qualidade do código"

# Instalação e Configuração
install: ## Instala dependências
	@echo "$(BLUE)📦 Instalando dependências...$(RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Dependências instaladas$(RESET)"

install-dev: ## Instala dependências de desenvolvimento
	@echo "$(BLUE)📦 Instalando dependências de desenvolvimento...$(RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	$(PIP) install pre-commit black isort flake8 mypy bandit safety
	@echo "$(GREEN)✅ Dependências de desenvolvimento instaladas$(RESET)"

setup: install-dev ## Configuração inicial completa
	@echo "$(MAGENTA)🚀 Configurando ambiente DataMindVV...$(RESET)"
	$(PYTHON) scripts/setup_environment.py
	pre-commit install
	@echo "$(GREEN)✅ Configuração concluída$(RESET)"

# Testes
test: ## Executa todos os testes
	@echo "$(BLUE)🧪 Executando todos os testes...$(RESET)"
	$(PYTHON) scripts/run_tests.py --all

test-unit: ## Executa testes unitários
	@echo "$(BLUE)🧪 Executando testes unitários...$(RESET)"
	$(PYTEST) tests/ -m "unit" -v --tb=short

test-integration: ## Executa testes de integração
	@echo "$(BLUE)🧪 Executando testes de integração...$(RESET)"
	$(PYTEST) tests/ -m "integration" -v --tb=short

test-security: ## Executa testes de segurança
	@echo "$(BLUE)🔒 Executando testes de segurança...$(RESET)"
	$(PYTEST) tests/ -m "security" -v --tb=short

test-performance: ## Executa testes de performance
	@echo "$(BLUE)⚡ Executando testes de performance...$(RESET)"
	$(PYTEST) tests/ -m "performance" -v --benchmark-only

test-smoke: ## Executa testes de smoke
	@echo "$(BLUE)💨 Executando testes de smoke...$(RESET)"
	$(PYTEST) tests/ -m "smoke" -v --tb=short

test-watch: ## Executa testes em modo watch
	@echo "$(BLUE)👀 Executando testes em modo watch...$(RESET)"
	$(PYTEST) tests/ -f --tb=short

# Qualidade de Código
lint: ## Verifica qualidade do código
	@echo "$(BLUE)🔍 Verificando qualidade do código...$(RESET)"
	flake8 utils/ pages/ tests/ --max-line-length=100 --ignore=E203,W503
	mypy utils/ pages/ --ignore-missing-imports --no-strict-optional
	@echo "$(GREEN)✅ Verificação de qualidade concluída$(RESET)"

format: ## Formata código
	@echo "$(BLUE)🎨 Formatando código...$(RESET)"
	black utils/ pages/ tests/ --line-length=100
	isort utils/ pages/ tests/ --profile=black --line-length=100
	@echo "$(GREEN)✅ Código formatado$(RESET)"

format-check: ## Verifica formatação sem alterar
	@echo "$(BLUE)🎨 Verificando formatação...$(RESET)"
	black --check --diff utils/ pages/ tests/ --line-length=100
	isort --check-only --diff utils/ pages/ tests/ --profile=black --line-length=100

security: ## Verifica vulnerabilidades de segurança
	@echo "$(BLUE)🔒 Verificando segurança...$(RESET)"
	bandit -r utils/ pages/ -f json -o reports/bandit-report.json
	safety check --json --output reports/safety-report.json
	pip-audit --format=json --output=reports/pip-audit-report.json
	@echo "$(GREEN)✅ Verificação de segurança concluída$(RESET)"

check: format-check lint security ## Executa todas as verificações
	@echo "$(GREEN)✅ Todas as verificações concluídas$(RESET)"

# Execução
run: ## Executa a aplicação
	@echo "$(BLUE)🚀 Iniciando DataMindVV...$(RESET)"
	$(PYTHON) app.py

dev: ## Executa em modo desenvolvimento com auto-reload
	@echo "$(BLUE)🔧 Iniciando em modo desenvolvimento...$(RESET)"
	DEBUG=true $(PYTHON) app.py

test-app: ## Testa se a aplicação inicializa corretamente
	@echo "$(BLUE)🧪 Testando inicialização da aplicação...$(RESET)"
	$(PYTHON) app.py --test-mode
	@echo "$(GREEN)✅ Aplicação inicializa corretamente$(RESET)"

# Cobertura de Testes
coverage: ## Gera relatório de cobertura
	@echo "$(BLUE)📊 Gerando relatório de cobertura...$(RESET)"
	$(PYTEST) tests/ --cov=utils --cov=pages --cov-report=html --cov-report=xml --cov-report=term
	@echo "$(GREEN)✅ Relatório de cobertura gerado em htmlcov/$(RESET)"

coverage-open: coverage ## Abre relatório de cobertura no navegador
	@echo "$(BLUE)🌐 Abrindo relatório de cobertura...$(RESET)"
	@if command -v xdg-open > /dev/null; then \
		xdg-open htmlcov/index.html; \
	elif command -v open > /dev/null; then \
		open htmlcov/index.html; \
	else \
		echo "$(YELLOW)Abra manualmente: htmlcov/index.html$(RESET)"; \
	fi

# Relatórios
report: ## Gera relatório completo
	@echo "$(BLUE)📋 Gerando relatório completo...$(RESET)"
	mkdir -p reports
	$(PYTHON) scripts/run_tests.py --report
	@echo "$(GREEN)✅ Relatório gerado em reports/$(RESET)"

# Limpeza
clean: ## Remove arquivos temporários
	@echo "$(BLUE)🧹 Limpando arquivos temporários...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	@echo "$(GREEN)✅ Limpeza concluída$(RESET)"

clean-logs: ## Remove logs antigos
	@echo "$(BLUE)🧹 Limpando logs antigos...$(RESET)"
	find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true
	find logs/ -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Logs antigos removidos$(RESET)"

clean-cache: ## Remove cache
	@echo "$(BLUE)🧹 Limpando cache...$(RESET)"
	rm -f cache.sqlite*
	rm -rf data/cache/*
	@echo "$(GREEN)✅ Cache limpo$(RESET)"

clean-all: clean clean-logs clean-cache ## Remove todos os arquivos temporários
	@echo "$(GREEN)✅ Limpeza completa concluída$(RESET)"

# Backup e Restore
backup: ## Cria backup dos dados
	@echo "$(BLUE)💾 Criando backup...$(RESET)"
	mkdir -p data/backups
	$(PYTHON) -c "import shutil, datetime; shutil.make_archive(f'data/backups/backup_{datetime.datetime.now().strftime(\"%Y%m%d_%H%M%S\")}', 'zip', 'data', exclude=['backups', 'cache'])"
	@echo "$(GREEN)✅ Backup criado em data/backups/$(RESET)"

# Logs
logs: ## Mostra logs em tempo real
	@echo "$(BLUE)📋 Monitorando logs...$(RESET)"
	tail -f logs/app.log 2>/dev/null || echo "$(YELLOW)Arquivo de log não encontrado$(RESET)"

logs-error: ## Mostra apenas logs de erro
	@echo "$(BLUE)❌ Monitorando logs de erro...$(RESET)"
	tail -f logs/error.log 2>/dev/null || echo "$(YELLOW)Arquivo de log de erro não encontrado$(RESET)"

# Documentação
docs: ## Gera documentação
	@echo "$(BLUE)📚 Gerando documentação...$(RESET)"
	@echo "$(YELLOW)Documentação será implementada em versão futura$(RESET)"

# Utilitários
info: ## Mostra informações do sistema
	@echo "$(CYAN)📊 Informações do Sistema$(RESET)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version)"
	@echo "Diretório: $$(pwd)"
	@echo "Usuário: $$(whoami)"
	@echo "Data: $$(date)"
	@echo ""
	@echo "$(CYAN)📦 Dependências Principais$(RESET)"
	@$(PIP) list | grep -E "(dash|plotly|pandas|flask|sqlalchemy)" || true

status: ## Mostra status do projeto
	@echo "$(CYAN)📊 Status do Projeto$(RESET)"
	@echo "Arquivos Python: $$(find . -name '*.py' | wc -l)"
	@echo "Linhas de código: $$(find . -name '*.py' -exec wc -l {} + | tail -1 | awk '{print $$1}')"
	@echo "Testes: $$(find tests/ -name 'test_*.py' | wc -l)"
	@echo "Última modificação: $$(find . -name '*.py' -exec stat -c %Y {} \; | sort -n | tail -1 | xargs -I {} date -d @{})"

# Comandos de desenvolvimento rápido
quick-test: format-check test-unit ## Teste rápido (formatação + testes unitários)
	@echo "$(GREEN)✅ Teste rápido concluído$(RESET)"

quick-check: format lint test-unit ## Verificação rápida completa
	@echo "$(GREEN)✅ Verificação rápida concluída$(RESET)"

# Default target
.DEFAULT_GOAL := help