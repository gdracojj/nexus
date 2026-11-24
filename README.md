# Nexus — Engenharia de Dados e Analytics para Licitações Públicas

![Status](https://img.shields.io/badge/status-em_desenvolvimento-orange)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.143.0-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?logo=sqlalchemy)
![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?logo=pytest)

O **Nexus** é uma plataforma em desenvolvimento de **Engenharia de Dados e Analytics** voltada à coleta, transformação, organização e exploração de dados de contratações públicas disponibilizados pelo **Portal Nacional de Contratações Públicas (PNCP)**.

O projeto transforma dados provenientes de uma API pública em informações estruturadas e consultáveis, utilizando um pipeline de processamento desenvolvido em Python, persistência relacional em PostgreSQL e uma camada de disponibilização por API REST integrada a um painel analítico.

A proposta é reduzir o esforço necessário para identificar oportunidades no mercado público e criar uma base de dados confiável para análises operacionais e estratégicas.

Mais do que uma interface de consulta, o Nexus busca aplicar conceitos de engenharia de dados em um cenário real: ingestão de dados externos, normalização, validação, deduplicação, persistência incremental, rastreabilidade, orquestração e disponibilização de informações para análise.

> **Foco técnico:** Data Engineering, ETL, integração de APIs, Python, SQL, PostgreSQL, modelagem relacional, qualidade de dados, pipelines resilientes, Analytics e visualização de informações.

---

## 1. Visão geral do projeto

A identificação de oportunidades em licitações públicas exige consultas frequentes a diferentes informações disponibilizadas pelo PNCP. O volume de registros, a distribuição dos dados e a necessidade de acompanhar prazos tornam importante estruturar um processo confiável de coleta e consulta.

O Nexus foi concebido a partir de necessidades operacionais relacionadas à análise de licitações e evoluiu para uma plataforma que organiza esse processo em diferentes camadas.

### Objetivos

- Automatizar a ingestão de oportunidades publicadas no PNCP.
- Processar e padronizar registros recebidos de uma fonte externa.
- Preservar os dados originais para rastreabilidade.
- Evitar duplicidade e controlar atualizações.
- Manter histórico e progresso das sincronizações.
- Disponibilizar os dados por meio de uma API REST.
- Permitir exploração das oportunidades por filtros e indicadores visuais.
- Construir uma base estruturada para futuras análises de comportamento e padrões das contratações públicas.

### Escopo funcional

| Área | Funcionalidade | Situação |
|---|---|---|
| Ingestão | Integração com API do PNCP | Implementada |
| Ingestão | Coleta individual por UF | Implementada |
| Orquestração | Coleta nacional das 27 UFs | Implementada no código; validação operacional pendente |
| Transformação | Parsing, normalização e validação | Implementada |
| Persistência | PostgreSQL e SQLAlchemy | Implementada |
| Integridade | UPSERT e deduplicação | Implementada |
| Rastreabilidade | Payload original e histórico de sincronização | Implementada |
| Recuperação | Checkpoint e retomada de coleta | Implementada |
| Serving | API REST com FastAPI | Implementada |
| Analytics | Filtros, indicadores, timeline e visualização de prazos | Implementada |
| Analytics avançado | Análise histórica e indicadores de mercado | Evolução planejada |
| Gestão de atas | Vigência, saldos e movimentações | Planejada |
| IA | Classificação e análise semântica de oportunidades | Planejada |

---

## 2. Arquitetura da solução

O Nexus utiliza uma arquitetura modular em camadas, separando comunicação externa, processamento, regras de negócio, persistência e disponibilização dos dados.

### Fluxo de dados

```text
                   FONTE EXTERNA
                        |
                        v
                  API DO PNCP
                        |
                        v
                  PNCP CLIENT
                        |
              Extração e paginação
                        |
                        v
                PARSING / ETL
                        |
             Normalização e validação
                        |
                        v
                 DATA SERVICES
                        |
              Regras de processamento
                        |
                        v
                  REPOSITORY
                        |
              UPSERT / CHECKPOINT
                        |
                        v
                   POSTGRESQL
                        |
             +----------+----------+
             |                     |
             v                     v
          FASTAPI             CONSULTAS SQL
             |                     |
             v                     v
        API REST             EXPLORAÇÃO ANALÍTICA
             |                     |
             +----------+----------+
                        |
                        v
                  FRONTEND NEXUS
                        |
                        v
              VISUALIZAÇÃO DE DADOS
```

A coleta é executada separadamente da API de leitura. Isso permite que o painel continue consultando os dados já persistidos mesmo quando o PNCP estiver indisponível.

### Organização por responsabilidades

| Camada | Responsabilidade |
|---|---|
| PNCP Client | Comunicação HTTP, paginação, timeout e retries |
| Parser | Interpretação, normalização e validação dos registros |
| Services | Orquestração das regras de negócio e do processamento |
| Repository | Operações de persistência e consultas ao banco |
| Database | Modelagem relacional, sessões e transações |
| CLI | Execução operacional das coletas |
| FastAPI | Disponibilização dos dados por endpoints REST |
| Frontend | Consulta, filtragem e visualização analítica |

---

## 3. Engenharia de Dados

A Engenharia de Dados é o núcleo técnico do Nexus. O pipeline foi desenvolvido para transformar respostas de uma API externa em registros estruturados, consistentes e disponíveis para consulta.

### 3.1 Ingestão de dados — Data Ingestion

A ingestão utiliza Python e Requests para consumir o endpoint de consulta de contratações do PNCP:

```text
https://pncp.gov.br/api/consulta/v1/contratacoes/proposta
```

O cliente HTTP é responsável por controlar os parâmetros das requisições, recuperar as páginas disponíveis e tratar falhas de comunicação.

Recursos implementados:

- Consumo de API REST externa.
- Requisições HTTP parametrizadas.
- Paginação baseada no campo `totalPaginas`.
- Controle de quantidade máxima de páginas.
- Tratamento de timeouts e falhas de conexão.
- Retentativas para erros transitórios.
- Interpretação do cabeçalho `Retry-After`.
- Controle de intervalo entre requisições.
- Coleta individual por unidade federativa.
- Orquestração sequencial da coleta nacional.

### 3.2 Orquestração da coleta

A coleta pode ser executada individualmente por UF ou por meio de um processo nacional.

**Coleta individual:**

```bash
python -m app.cli coletar --uf RJ
```

**Coleta nacional:**

```bash
python -m app.cli coletar-nacional
```

O orquestrador nacional percorre sequencialmente as 27 unidades federativas brasileiras, delegando a execução ao serviço responsável pela coleta individual.

A implementação contempla:

- Execução sequencial das UFs.
- Reutilização do fluxo de coleta individual.
- Isolamento de falhas por unidade federativa.
- Continuidade do processamento quando uma UF apresenta erro.
- Consolidação dos resultados da execução nacional.
- Intervalos operacionais para reduzir a pressão sobre a API externa.

A separação entre orquestração e coleta individual facilita a manutenção do pipeline e permite evoluir futuramente para estratégias de execução distribuída, caso o volume e a necessidade operacional justifiquem essa mudança.

**Importante:** a implementação do comando nacional está disponível no código, mas sua execução completa e a medição da taxa de sucesso das 27 UFs ainda precisam ser validadas em uma coleta operacional.

### 3.3 Transformação — Data Transformation

Os registros recebidos do PNCP passam por parsing, normalização e validação antes de serem encaminhados à camada de persistência.

Técnicas aplicadas:

- Parsing de estruturas JSON.
- Normalização de atributos externos.
- Padronização de campos.
- Conversão de tipos de dados.
- Tratamento de campos ausentes ou inconsistentes.
- Validação estrutural dos registros.
- Separação entre payload externo e modelo interno.
- Conversão dos registros para estruturas de persistência.

A transformação reduz a dependência direta do formato recebido da API externa e estabelece uma representação interna consistente para as operações seguintes.

### 3.4 Qualidade e integridade dos dados

O pipeline utiliza identificadores de negócio e mecanismos de validação para controlar a integridade dos registros.

Estratégias implementadas:

- Deduplicação pelo identificador `numeroControlePNCP`.
- Utilização de chave externa única.
- UPSERT para inserção ou atualização.
- Hash SHA-256 para identificar alterações no conteúdo.
- Preservação do payload original em JSONB.
- Controle transacional das operações.
- Checkpoint por página processada.
- Histórico das execuções de sincronização.

A utilização do `numeroControlePNCP` evita que a mesma contratação seja inserida repetidamente durante coletas posteriores.

O hash SHA-256 permite identificar se o conteúdo recebido sofreu alterações, evitando a substituição desnecessária de snapshots idênticos.

### 3.5 Persistência — Data Loading

O PostgreSQL é utilizado como banco de dados relacional principal.

A camada de persistência utiliza SQLAlchemy e o padrão Repository para separar as regras de acesso ao banco da lógica de processamento.

Principais estratégias:

- Modelagem relacional.
- ORM com SQLAlchemy.
- Operações de INSERT e UPDATE.
- UPSERT para inserção ou atualização de registros.
- Deduplicação por identificador de negócio.
- Armazenamento de payloads originais em JSONB.
- Controle de histórico de sincronizações.
- Hash SHA-256 para identificação de alterações.
- Transações para consistência dos registros.
- Persistência de checkpoints por página.

### 3.6 Checkpoint e recuperação de execução

A coleta foi estruturada para confirmar o processamento por página, em vez de depender exclusivamente da conclusão de toda a consulta.

Os registros processados e o checkpoint correspondente são confirmados na mesma transação.

Com isso:

1. O cliente consulta uma página do PNCP.
2. Os registros são processados e normalizados.
3. O Repository executa os UPSERTs.
4. O checkpoint da página é atualizado.
5. A transação é confirmada.
6. A próxima página é processada.

Se ocorrer uma falha depois de páginas confirmadas, o progresso anterior permanece persistido.

Uma nova execução com os mesmos parâmetros pode retomar o processamento a partir da próxima página pendente.

Essa estratégia reduz o custo de reprocessamento e melhora a recuperação de falhas em consultas extensas.

A retomada não representa um snapshot imutável da API externa: a paginação e os registros disponibilizados pelo PNCP podem mudar entre execuções.

---

## 4. Resiliência e confiabilidade da integração

A integração com o PNCP considera que APIs externas podem apresentar instabilidade, limitação de requisições e indisponibilidade temporária.

O cliente implementa uma política de retentativas controladas.

### Política de retry

| Recurso | Comportamento |
|---|---|
| Tentativas | Até 5 por página, incluindo a requisição inicial |
| Backoff exponencial | 2, 4, 8 e 16 segundos |
| `Retry-After` | Aceita segundos inteiros ou data HTTP |
| Intervalo entre páginas | 1 segundo |
| Timeout de requisição | Configurado no cliente HTTP |
| Prazo total configurado | 300 segundos por execução |
| Status transitórios | 408, 429, 500, 502, 503 e 504 |
| Falhas permanentes | Outros status HTTP e erros TLS não são repetidos |

Quando o PNCP informa um `Retry-After` superior a 60 segundos, a execução falha imediatamente em vez de manter o processo aguardando indefinidamente.

O cliente também diferencia erros transitórios de falhas permanentes, evitando repetir requisições que não devem ser recuperadas por retry.

**Limitação técnica:** o timeout de leitura do Requests limita o período de inatividade da conexão, não necessariamente o tempo absoluto de download. Uma resposta que continue transmitindo dados pode ultrapassar o prazo total configurado.

---

## 5. Banco de dados e modelagem

O PostgreSQL concentra os dados estruturados e os registros necessários à rastreabilidade das sincronizações.

### Entidades principais

| Estrutura | Finalidade |
|---|---|
| `licitacoes` | Registros normalizados das contratações |
| `pncp_payloads` | Snapshots originais das respostas recebidas |
| `sync_execucoes` | Histórico e estado das sincronizações |

### Estratégia de identificação

O campo `numeroControlePNCP` é utilizado como identificador externo único da contratação.

A persistência diferencia:

- `coletada_em`: primeira coleta conhecida pelo Nexus.
- `atualizada_em`: sincronização mais recente do registro.
- `data_publicacao`: data de publicação informada pelo PNCP.

O snapshot JSONB é mantido separadamente dos atributos normalizados. Seu hash SHA-256 permite verificar alterações no conteúdo recebido.

### Transações e checkpoints

Cada página processada tem seus registros e checkpoint confirmados na mesma transação.

Esse desenho evita que o sistema registre uma página como concluída quando seus registros não foram efetivamente persistidos.

### Concorrência e conexão com o banco

A coleta utiliza um advisory lock global de sessão no PostgreSQL para impedir coletas simultâneas entre processos conectados ao mesmo banco.

Se outra coleta estiver ativa, uma nova execução é recusada.

A configuração de conexão utiliza:

- 5 conexões persistentes no pool SQLAlchemy.
- Até 10 conexões excedentes.
- 30 segundos de espera por uma conexão disponível.

Cada processo ou worker de aplicação mantém seu próprio pool.

---

## 6. Analytics e exploração dos dados

A camada de Analytics transforma os registros persistidos em informações acessíveis para exploração e acompanhamento das oportunidades.

Nesta versão, o foco está na consulta estruturada, nos filtros operacionais e na visualização dos prazos.

### Recursos analíticos implementados

- Consulta por unidade federativa.
- Pesquisa textual pelo objeto da contratação.
- Filtros por prazo.
- Paginação dos resultados.
- Ordenação por encerramento de propostas.
- Indicadores de quantidade de registros.
- Identificação de oportunidades com prazos próximos.
- Visualização em timeline.
- Organização visual por situação.
- Tabela responsiva para exploração dos registros.

### Proposta de evolução analítica

A estrutura de dados permite evoluir para análises mais aprofundadas sobre o comportamento das contratações públicas.

Entre as possibilidades futuras:

- Volume de contratações por UF e município.
- Distribuição de oportunidades por modalidade.
- Análise de valores estimados.
- Identificação de categorias recorrentes de compras.
- Evolução temporal do volume de publicações.
- Comparação de oportunidades por órgão.
- Frequência de publicação por segmento.
- Indicadores de concentração e recorrência.
- Análise de sazonalidade.
- Identificação de padrões para apoiar estratégias comerciais.

Essas análises dependem da ampliação e validação dos dados disponíveis, da definição de métricas e da construção de consultas analíticas específicas.

**O Nexus ainda não possui um data warehouse ou uma camada dimensional dedicada.** A base PostgreSQL atual atende à persistência operacional e à disponibilização dos registros. Uma arquitetura analítica separada poderá ser considerada conforme a evolução do produto e dos requisitos de consulta.

---

## 7. API REST e camada de disponibilização

A API foi desenvolvida com FastAPI e disponibiliza os registros persistidos no PostgreSQL.

A separação entre coleta e leitura permite que as consultas continuem funcionando sem depender de uma chamada em tempo real ao PNCP.

### Endpoint principal

`GET /api/licitacoes`

Consulta oportunidades vigentes persistidas no banco.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `uf` | string | Sigla da unidade federativa |
| `produto` | string | Termo textual para pesquisa no objeto |
| `page` | integer | Número da página, baseado em 1 |
| `page_size` | integer | Quantidade de registros por página |
| `prazo_dias` | integer | Limita a consulta às oportunidades nos próximos dias |

### Exemplo

```bash
curl "http://127.0.0.1:8000/api/licitacoes?uf=RJ&produto=material&page=1&page_size=25"
```

### Paginação

A API utiliza paginação baseada em página e tamanho de página.

- Página inicial padrão: `1`.
- Tamanho padrão: `25`.
- Tamanho máximo: `100`.
- Número máximo de página: `10000`.

A resposta informa a quantidade total de registros correspondentes aos filtros, a página atual, o tamanho solicitado e o total de páginas.

A ordenação considera o prazo de encerramento e o número da contratação.

### Proteção da API

As rotas sob `/api/` utilizam um limitador token bucket em memória por endereço IP.

Por padrão:

- Limite de 60 consultas por minuto.
- Rajadas de até 60 requisições.
- Resposta HTTP `429` quando o limite é excedido.
- Cabeçalhos `X-RateLimit-Limit` e `X-RateLimit-Remaining`.
- Cabeçalho `Retry-After` em respostas de limite excedido.

O limite pode ser configurado por `NEXUS_API_RATE_LIMIT_PER_MINUTE`.

Em ambientes com múltiplos workers ou instâncias, o limitador em memória é local a cada processo. Um proxy ou gateway deve ser utilizado caso seja necessário aplicar um limite compartilhado.

---

## 8. Interface e visualização

O frontend foi desenvolvido com tecnologias web nativas, sem dependência de framework JavaScript.

### Tecnologias

- HTML5.
- CSS3.
- JavaScript com módulos ES.
- Consumo da API REST.
- Renderização dinâmica de registros.
- Layout responsivo.
- Alternância de tema.
- Componentes visuais para acompanhamento de prazos.

### Recursos de interface

- Dashboard de oportunidades.
- Filtros por UF e termo de pesquisa.
- Paginação integrada à API.
- Timeline de prazos.
- Quadro de oportunidades por situação.
- Tabela de resultados.
- Indicadores de contexto.
- Estados de carregamento, erro e ausência de resultados.
- Tema visual e adaptação responsiva.

A interface consome os dados disponibilizados pela API, sem realizar consultas diretamente ao PNCP.

---

## 9. Tecnologias e ferramentas

### Stack implementada

| Categoria | Tecnologia | Aplicação |
|---|---|---|
| Linguagem | Python | Pipeline, serviços e backend |
| API | FastAPI | Disponibilização de dados |
| Servidor | Uvicorn | Execução da aplicação |
| Integração HTTP | Requests | Consumo do PNCP |
| Banco de dados | PostgreSQL | Persistência relacional |
| ORM | SQLAlchemy | Mapeamento e operações de banco |
| Migrations | Alembic | Versionamento do schema |
| Interface | HTML5 | Estrutura da aplicação |
| Estilização | CSS3 | Layout e responsividade |
| Interface dinâmica | JavaScript | Consumo da API e renderização |
| Testes | Pytest | Testes automatizados |
| CI | GitHub Actions | Integração contínua |
| Versionamento | Git e GitHub | Controle de versão e colaboração |

### Conceitos e práticas aplicados

- Engenharia de Dados.
- ETL (Extract, Transform, Load).
- Integração de APIs REST.
- Processamento e normalização de JSON.
- Modelagem relacional.
- SQL e PostgreSQL.
- UPSERT e idempotência.
- Deduplicação por chave de negócio.
- Hashing SHA-256.
- Controle transacional.
- Checkpoint e retomada de processamento.
- Paginação e tratamento de falhas.
- Retry e backoff exponencial.
- Orquestração de processos.
- Repository Pattern.
- Separação de responsabilidades.
- Testes unitários e de integração.
- Integração contínua.

---

## 10. Estrutura do repositório

```text
nexus/
├── .github/
│   └── workflows/
│       └── tests.yml
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_persistence.py
├── app/
│   ├── core/
│   │   ├── config.py
│   │   └── logger.py
│   ├── database/
│   │   ├── connection.py
│   │   └── models.py
│   ├── pncp/
│   │   ├── client.py
│   │   └── parser.py
│   ├── repositories/
│   │   └── licitacao_repository.py
│   ├── services/
│   │   ├── licitacao_service.py
│   │   └── coleta_nacional_service.py
│   ├── cli.py
│   └── main.py
├── frontend/
│   ├── api.js
│   ├── app.js
│   ├── index.html
│   ├── nexus.css
│   ├── prazo.js
│   └── theme.js
├── tests/
│   ├── test_api_route.py
│   ├── test_cli.py
│   ├── test_persistence_postgresql.py
│   ├── test_pncp_pagination.py
│   ├── test_pncp_parser.py
│   ├── test_pncp_record_validation.py
│   └── test_pncp_transient_retries.py
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-test.txt
└── README.md
```

A estrutura representa os principais módulos da aplicação. Os nomes e arquivos podem evoluir conforme a implementação.

---

## 11. Como executar localmente

### Pré-requisitos

- Python 3.10 ou superior.
- PostgreSQL.
- Git.
- Ambiente Linux, macOS ou Windows com WSL2/PowerShell.

### 1. Clonar o repositório

```bash
git clone https://github.com/gdracojj/nexus.git
cd nexus
```

### 2. Criar o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependências

```bash
pip install -r requirements-test.txt
```

Para instalar somente as dependências da aplicação:

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Configure a conexão PostgreSQL em `DATABASE_URL`.

Exemplo:

```env
DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/nexus
```

A aplicação também aceita `POSTGRES_URL` como alternativa de configuração.

### 5. Aplicar migrations

```bash
python -m alembic upgrade head
```

Verificar a versão atual:

```bash
python -m alembic current
```

### 6. Iniciar a aplicação

```bash
python -m uvicorn app.main:app --reload
```

### 7. Executar uma coleta

Em outro terminal:

```bash
python -m app.cli coletar --uf RJ
```

Para iniciar a coleta nacional:

```bash
python -m app.cli coletar-nacional
```

### 8. Acessar a API

- Aplicação: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

---

## 12. Testes e qualidade

O projeto utiliza Pytest para validar componentes do pipeline, regras de negócio, integração HTTP, CLI e persistência.

A cobertura de testes contempla:

- Parsing e normalização de registros.
- Validação de dados recebidos do PNCP.
- Paginação e comportamento do cliente HTTP.
- Retentativas para erros transitórios.
- Comandos da CLI.
- Rotas da API.
- Persistência e operações PostgreSQL.

### Executar os testes

```bash
python -m pytest -q
```

Para executar testes específicos:

```bash
python -m pytest tests/test_pncp_pagination.py
```

### Testes de integração PostgreSQL

Os testes de persistência utilizam uma base PostgreSQL descartável configurada por `NEXUS_TEST_DATABASE_URL`.

Exemplo:

```env
NEXUS_TEST_DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/nexus_test
```

Os testes criam e removem schemas isolados para evitar interferência entre execuções.

### Integração contínua

O GitHub Actions executa verificações automatizadas em pull requests, incluindo testes Python, PostgreSQL e verificações de sintaxe JavaScript.

O workflow também contempla auditoria de dependências Python por meio de `pip-audit`.

---

## 13. Variáveis de ambiente

| Variável | Finalidade |
|---|---|
| `DATABASE_URL` | URL principal de conexão com PostgreSQL |
| `POSTGRES_URL` | Alternativa para conexão com PostgreSQL |
| `NEXUS_TEST_DATABASE_URL` | Banco descartável para testes de integração |
| `PNCP_SYNC_CACHE_TTL_SECONDS` | Janela de reuso de coleta recente |
| `NEXUS_API_RATE_LIMIT_PER_MINUTE` | Limite de consultas por IP na API |
| `NEXUS_TRUSTED_PROXY_CIDRS` | Redes de proxies confiáveis |

A configuração efetiva depende dos valores definidos no ambiente e dos padrões estabelecidos em `app/core/config.py`.

---

## 14. Limitações conhecidas

O Nexus permanece em desenvolvimento. As seguintes limitações são consideradas no planejamento técnico:

- A coleta depende da disponibilidade e do comportamento da API do PNCP.
- A execução nacional precisa ser validada em operação real para medir sua taxa de sucesso.
- A paginação do PNCP pode sofrer alterações entre execuções.
- O agendamento é externo; não há scheduler interno.
- O rate limiting em memória não é compartilhado entre múltiplas instâncias.
- A camada analítica atual está concentrada em filtros, consultas e visualizações operacionais.
- Não existe ainda um data warehouse ou modelo dimensional dedicado.
- A gestão de Atas de Registro de Preços ainda não foi implementada.
- Não há autenticação e autorização de usuários implementadas para um produto multiusuário.
- Recursos de IA e busca semântica ainda fazem parte da evolução planejada.

---

## 15. Roadmap

### Engenharia de Dados e operação

- [x] Integração com a API do PNCP.
- [x] Coleta individual por UF.
- [x] Paginação e controle de requisições.
- [x] Parsing, normalização e validação.
- [x] Persistência PostgreSQL.
- [x] UPSERT e deduplicação.
- [x] Preservação de payload original.
- [x] Histórico de sincronizações.
- [x] Checkpoint e retomada por página.
- [x] Política de retry e backoff.
- [x] Orquestração nacional implementada no código.
- [ ] Validar uma execução nacional completa.
- [ ] Ampliar observabilidade com logs estruturados e métricas por execução.
- [ ] Avaliar processamento em lotes e otimizações de memória.
- [ ] Criar ambiente reproduzível com Docker e Docker Compose.
- [ ] Avaliar estratégias de agendamento e monitoramento operacional.

### Analytics e exploração

- [x] API para consulta dos dados persistidos.
- [x] Filtros por UF e termo de pesquisa.
- [x] Paginação de resultados.
- [x] Classificação e visualização de prazos.
- [x] Dashboard com timeline, quadro e tabela.
- [ ] Ampliar indicadores por UF, município, modalidade e órgão.
- [ ] Construir análises históricas e temporais.
- [ ] Avaliar índices e otimizações com `EXPLAIN ANALYZE`.
- [ ] Avaliar modelo dimensional para consultas analíticas.
- [ ] Estudar integração com ferramentas de BI.

### Evolução de produto

- [ ] Especificar módulo de Atas de Registro de Preços.
- [ ] Modelar vigência, fornecedores e movimentações de saldo.
- [ ] Implementar acompanhamento de reajustes e vencimentos.
- [ ] Definir autenticação, autorização e perfis de acesso.
- [ ] Avaliar classificação de oportunidades por categorias.
- [ ] Investigar recursos de NLP e busca semântica.
- [ ] Avaliar recursos de IA para apoiar a análise de editais.

---

## 16. Referências técnicas

- [Portal Nacional de Contratações Públicas](https://www.gov.br/pncp/pt-br)
- [API de Consulta do PNCP — Swagger](https://pncp.gov.br/api/consulta/swagger-ui/index.html)
- [Manual de Integração do PNCP](https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html)
- [Documentação do FastAPI](https://fastapi.tiangolo.com/)
- [Documentação do SQLAlchemy](https://docs.sqlalchemy.org/)
- [Documentação do PostgreSQL](https://www.postgresql.org/docs/)
- [Documentação do Alembic](https://alembic.sqlalchemy.org/)

---

## 17. Autor

**Gabriel Silva**

Desenvolvimento do Nexus com foco em Engenharia de Dados, integração de sistemas, processamento de dados e Analytics.

- GitHub: [github.com/gdracojj](https://github.com/gdracojj)

---

*O Nexus é um projeto em desenvolvimento. Seu objetivo é evoluir continuamente como uma plataforma de dados aplicada ao domínio das contratações públicas, combinando engenharia, confiabilidade e análise de informações.*
