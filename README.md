# DataMindVV - Plataforma Analítica Integrada

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Dash](https://img.shields.io/badge/dash-2.14+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-black.svg)

Uma plataforma analítica moderna e integrada com IA para visualização, análise e processamento de dados empresariais.

## 🚀 Características Principais

### 📊 Análise de Dados
- **Conexões Múltiplas**: PostgreSQL, MySQL, SQLite, CSV, Excel
- **Query Builder Visual**: Interface intuitiva para construção de consultas
- **Transformações Avançadas**: ETL integrado com validação de dados
- **Joins Inteligentes**: Combinação automática de datasets

### 🤖 Inteligência Artificial
- **Chat com IA**: Análise conversacional usando Groq e Ollama
- **Previsões Automáticas**: Machine Learning para forecasting
- **RAG (Retrieval-Augmented Generation)**: Consultas inteligentes aos dados
- **Análise de Sentimentos**: Processamento de texto avançado

### 📈 Visualizações
- **Dashboards Interativos**: Construtor visual de dashboards
- **Gráficos Dinâmicos**: Plotly.js com interatividade avançada
- **Relatórios Automatizados**: Geração programada de relatórios
- **Exportação Múltipla**: PDF, Excel, PNG, HTML

### 🔒 Segurança e Qualidade
- **Autenticação JWT**: Sistema seguro de autenticação
- **Validação Pydantic**: Validação robusta de entrada de dados
- **Auditoria Completa**: Log de todas as ações do sistema
- **Criptografia**: Proteção de dados sensíveis

### 🏗️ Arquitetura Moderna
- **Dependency Injection**: Arquitetura desacoplada e testável
- **Cache Inteligente**: Sistema de cache SQLite otimizado
- **Logging Avançado**: Sistema de logs estruturado com rotação
- **Tratamento de Erros**: Middleware centralizado de erros

## Visão Geral

Esta aplicação é uma plataforma web interativa para análise, visualização e transformação de dados, com suporte a múltiplas fontes (upload, bancos de dados), geração de gráficos avançados, chat com IA e automação de relatórios.

## Instalação

1. **Clone o repositório:**
```bash
   git clone <URL_DO_REPOSITORIO>
   cd <PASTA_DO_PROJETO>
```
2. **Crie um ambiente virtual (opcional, mas recomendado):**
```bash
python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   ```
3. **Instale as dependências:**
```bash
pip install -r requirements.txt
   # Para ambiente de desenvolvimento/testes:
   pip install -r requirements-dev.txt
   ```

## Configuração Inicial

- **Variáveis de Ambiente:**
  - Para produção, defina a variável `ENCRYPTION_KEY` no ambiente do sistema para a chave de criptografia.
  - Para desenvolvimento/local, a chave será gerada automaticamente e salva no `.env`.
- **Banco de Dados:**
  - Configure conexões em `config/connections.yml` ou via interface web.
- **Outros arquivos de configuração:**
  - `.env`: Armazena variáveis sensíveis em desenvolvimento.

## Como Executar

```bash
python app.py
```
Acesse `http://localhost:8050` no navegador.

## Estrutura de Diretórios

```
├── app.py                  # Arquivo principal da aplicação Dash
├── pages/                  # Páginas da aplicação (upload, database, transform, visualizations, etc.)
├── utils/                  # Utilitários (config_manager, database_manager, data_analyzer, etc.)
├── config/                 # Arquivos de configuração (connections.yml, .env)
├── tests/                  # Testes unitários e de integração
├── requirements.txt        # Dependências principais
├── requirements-dev.txt    # Dependências de desenvolvimento/teste
└── README.md               # Este arquivo
```

## Exemplos de Uso

- **Upload de Arquivos:**
  - Suporta CSV, XLS, XLSX. Preview otimizado para grandes arquivos.
- **Conexão com Banco de Dados:**
  - Suporte a PostgreSQL, SQL Server, MySQL, SQLite.
  - Queries customizadas com validação e prevenção de SQL Injection.
- **Transformações e Visualizações:**
  - Operações de limpeza, agregação, criação de colunas, gráficos interativos.
- **Chat com IA:**
  - Geração de insights, gráficos e análises automáticas via LLM.

## Testes Automatizados

- Para rodar todos os testes:
```bash
  pytest
  ```
- Testes cobrem utilitários principais e fluxos críticos.

## Contribuição

- Siga as boas práticas de código Python (PEP8).
- Adicione docstrings e comentários claros.
- Sempre escreva testes para novas funcionalidades.
- Para dúvidas ou sugestões, abra uma issue ou envie um pull request.

---

**Dúvidas?** Consulte os comentários e docstrings no código para exemplos detalhados de uso de cada módulo.

