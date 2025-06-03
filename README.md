# 📊 Advanced BI Dashboard - Python Data Visualization Platform

Um sistema completo de Business Intelligence desenvolvido em Python com Plotly Dash, oferecendo visualizações avançadas, análises automáticas e interface web moderna para exploração de dados.

## 🚀 Características Principais

### 🗄️ Conectividade de Dados
- **Bancos de Dados**: PostgreSQL e SQL Server via SQLAlchemy
- **Arquivos**: Upload de CSV e Excel com processamento automático
- **Conexões Seguras**: Gerenciamento criptografado de credenciais
- **Teste de Conexão**: Validação antes de salvar configurações

### 📈 Visualizações Interativas
- **Gráficos Nativos**: Bar, Line, Scatter, Pie, Heatmap, Box plots
- **Drill-down**: Navegação hierárquica em dados
- **Zoom Dinâmico**: Pan e zoom nativos do Plotly
- **Tooltips Customizáveis**: Informações detalhadas on-hover
- **Filtros Combinados**: Sliders, dropdowns e seleções múltiplas

### 🧠 Análises Automáticas
- **Estatísticas Descritivas**: Por grupo e categoria
- **Análise de Correlação**: Heatmaps interativos
- **Detecção de Outliers**: Métodos IQR e Z-score
- **Análise de Distribuição**: Histogramas e box plots
- **Relatório de Qualidade**: Avaliação automática dos dados
- **Análise Comparativa**: Comparações entre grupos

### 📊 Dashboard Executivo
- **Métricas-chave**: Cards com indicadores principais
- **Visualizações Múltiplas**: Combinação de gráficos
- **Atualização Automática**: Refresh configurável
- **Filtros Globais**: Aplicação em todo o dashboard
- **Indicadores de Qualidade**: Score de qualidade dos dados

## 🛠️ Tecnologias Utilizadas

- **Frontend**: Plotly Dash + Dash Bootstrap Components
- **Backend**: Python + Flask
- **Análise de Dados**: Pandas + NumPy + SciPy
- **Visualização**: Plotly + Plotly Express
- **Banco de Dados**: SQLAlchemy + psycopg2 + pyodbc
- **Segurança**: python-dotenv + cryptography
- **Configuração**: PyYAML

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Acesso a PostgreSQL ou SQL Server (opcional)

## 🔧 Instalação

### 1. Clone ou baixe o projeto
```bash
git clone <repository-url>
cd BI-25-05
```

### 2. Crie um ambiente virtual (recomendado)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure o ambiente
O sistema criará automaticamente:
- Pasta `config/` para configurações
- Arquivo `.env` para chaves de segurança
- Arquivo `config/connections.yml` para conexões salvas

## 🚀 Como Usar

### 1. Iniciar a aplicação
```bash
python app.py
```

### 2. Acessar a interface
Abra seu navegador e acesse: `http://localhost:8050`

### 3. Fluxo de trabalho recomendado

#### Opção A: Upload de Arquivos
1. **Upload Files** → Faça upload de CSV ou Excel
2. **Visualizations** → Crie gráficos interativos
3. **Analytics** → Execute análises automáticas
4. **Dashboard** → Visualize o painel executivo

#### Opção B: Conexão com Banco
1. **Database** → Configure conexão com PostgreSQL/SQL Server
2. **Database** → Teste e salve a conexão
3. **Database** → Explore schemas e execute queries
4. **Visualizations** → Crie visualizações dos dados
5. **Analytics** → Analise os resultados
6. **Dashboard** → Monitore métricas-chave

## 📊 Funcionalidades Detalhadas

### 🗄️ Página Database
- **Nova Conexão**: Formulário para PostgreSQL/SQL Server
- **Teste de Conexão**: Validação antes de salvar
- **Conexões Salvas**: Lista e gerenciamento de perfis
- **Exploração de Schema**: Visualização de tabelas e colunas
- **Editor SQL**: Execute queries personalizadas
- **Preview de Dados**: Amostra e schema das tabelas

### 📁 Página Upload Files
- **Upload Drag & Drop**: Interface intuitiva
- **Múltiplos Formatos**: CSV, Excel (.xlsx, .xls)
- **Detecção Automática**: Encoding e separadores
- **Preview Inteligente**: Primeiras linhas e estatísticas
- **Relatório de Qualidade**: Dados faltantes e tipos

### 📈 Página Visualizations
- **Configuração Dinâmica**: Eixos X/Y, cores, tamanhos
- **Tipos de Gráfico**: 8+ tipos nativos do Plotly
- **Filtros Interativos**: Múltiplos filtros simultâneos
- **Agregações**: Sum, Mean, Count, Min, Max
- **Drill-down**: Clique para detalhes
- **Export**: Salvar gráficos como imagem

### 🧠 Página Analytics
- **Estatísticas Descritivas**: Automáticas por grupo
- **Matriz de Correlação**: Heatmap interativo
- **Análise de Distribuição**: Histogramas e densidade
- **Detecção de Outliers**: Visualização e estatísticas
- **Relatório de Qualidade**: Score e recomendações
- **Análise Comparativa**: Entre categorias

### 📊 Página Dashboard
- **Métricas Executivas**: Cards com KPIs
- **Refresh Automático**: 30s, 1min, 5min
- **Filtros Globais**: Por categoria e data
- **Múltiplas Visualizações**: Grid responsivo
- **Indicadores de Qualidade**: Score e progresso
- **Insights Automáticos**: Correlações e outliers

## 🔒 Segurança

### Gerenciamento de Credenciais
- **Criptografia**: Senhas criptografadas com Fernet
- **Variáveis de Ambiente**: Chaves em arquivo `.env`
- **Não Versionamento**: `.env` no `.gitignore`
- **Configurações Separadas**: Dados sensíveis isolados

### Estrutura de Arquivos
```
config/
├── connections.yml    # Conexões salvas (sem senhas)
└── .env              # Chave de criptografia
```

## 🎨 Interface e UX

### Design Responsivo
- **Bootstrap Components**: Interface moderna
- **Grid System**: Adaptação a diferentes telas
- **Cards e Alerts**: Feedback visual claro
- **Loading States**: Indicadores de progresso

### Navegação Intuitiva
- **Navbar Fixa**: Acesso rápido a todas as seções
- **Breadcrumbs**: Localização atual
- **Tooltips**: Ajuda contextual
- **Shortcuts**: Atalhos de teclado

## 🔧 Configurações Avançadas

### Personalização de Gráficos
```python
# Temas personalizados
app.layout = dbc.themes.BOOTSTRAP

# Cores customizadas
color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c']
```

### Otimização de Performance
```python
# Cache de dados
@app.callback(
    Output('data-store', 'data'),
    Input('upload-data', 'contents'),
    prevent_initial_call=True
)
```

## 🐛 Solução de Problemas

### Problemas Comuns

#### Erro de Conexão com Banco
```bash
# Verificar drivers
pip install psycopg2-binary  # PostgreSQL
pip install pyodbc          # SQL Server
```

#### Erro de Encoding em CSV
- Tente diferentes encodings: UTF-8, Latin-1, CP1252
- Use o preview para verificar a detecção automática

#### Performance Lenta
- Limite o número de linhas para análise
- Use amostragem para datasets grandes
- Considere agregações prévias

### Logs e Debug
```python
# Ativar modo debug
app.run_server(debug=True)

# Logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Roadmap Futuro

### Próximas Funcionalidades
- [ ] **Análise Temporal**: Séries temporais e forecasting
- [ ] **Machine Learning**: Clustering e classificação
- [ ] **Exportação Avançada**: PDF e PowerPoint
- [ ] **Colaboração**: Compartilhamento de dashboards
- [ ] **APIs**: Endpoints REST para integração
- [ ] **Alertas**: Notificações automáticas

### Melhorias Planejadas
- [ ] **Cache Inteligente**: Redis para performance
- [ ] **Autenticação**: Login e controle de acesso
- [ ] **Temas**: Dark mode e personalização
- [ ] **Mobile**: Otimização para dispositivos móveis

## 🤝 Contribuição

### Como Contribuir
1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

### Padrões de Código
- **PEP 8**: Estilo de código Python
- **Docstrings**: Documentação de funções
- **Type Hints**: Tipagem quando possível
- **Tests**: Testes unitários para novas features

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

### Documentação
- **Plotly Dash**: https://dash.plotly.com/
- **Plotly Python**: https://plotly.com/python/
- **Pandas**: https://pandas.pydata.org/docs/

### Comunidade
- **Issues**: Reporte bugs e solicite features
- **Discussions**: Tire dúvidas e compartilhe ideias
- **Wiki**: Documentação adicional e tutoriais

---

**Desenvolvido com ❤️ usando Python e Plotly Dash**

*Para mais informações sobre o projeto DeepBI que serviu de inspiração, visite: https://github.com/DeepInsight-AI/DeepBI*