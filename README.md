# Plataforma de Análise de Dados Interativa

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

