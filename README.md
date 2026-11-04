# Nexus | Plataforma de Engenharia de Dados e Analytics para Licitações Públicas

**Versão 1.0 — Escopo funcional concluído**

O **Nexus** é uma plataforma de Engenharia de Dados e Analytics desenvolvida para coletar, processar, estruturar e disponibilizar informações de contratações públicas provenientes do **Portal Nacional de Contratações Públicas (PNCP)**.

O projeto foi desenvolvido com o propósito de transformar dados públicos disponibilizados por uma API externa em informações estruturadas e consultáveis, permitindo identificar oportunidades, acompanhar prazos e explorar padrões relacionados às contratações públicas.

A solução implementa um fluxo de dados de ponta a ponta, contemplando ingestão, transformação, validação, persistência, disponibilização por API REST e visualização analítica.

Mais do que uma aplicação de consulta, o Nexus representa a construção de uma infraestrutura de dados orientada à confiabilidade, rastreabilidade, organização e apoio à tomada de decisão.

---

## 1. Visão geral da arquitetura

O Nexus foi estruturado em camadas, separando as responsabilidades de integração externa, processamento, regras de negócio, persistência e apresentação.

### Arquitetura do fluxo de dados

```text
                  PNCP
                   |
                   v
             API REST externa
                   |
                   v
            PNCP API Client
                   |
                   v
          Extração e paginação
                   |
                   v
        Parsing e normalização
                   |
                   v
         Validação dos registros
                   |
                   v
          Camada de serviços
                   |
                   v
        Repository / Persistência
                   |
                   v
              PostgreSQL
                   |
          +--------+--------+
          |                 |
          v                 v
       FastAPI          Consultas SQL
          |                 |
          v                 v
       Frontend       Análise dos dados
          |                 |
          +--------+--------+
                   |
                   v
           Visualização analítica
```

### Etapas do pipeline

| Etapa | Responsabilidade |
|---|---|
| Ingestion | Extração dos dados disponibilizados pelo PNCP |
| Extraction | Comunicação HTTP e recuperação paginada dos registros |
| Transformation | Parsing, normalização e padronização dos dados |
| Validation | Verificação da estrutura e consistência dos registros |
| Loading | Persistência e atualização dos dados no PostgreSQL |
| Serving | Disponibilização dos registros por meio da API REST |
| Analytics | Filtragem, exploração e visualização das oportunidades |

O pipeline segue uma abordagem de processamento ETL (Extract, Transform, Load), na qual os registros são preparados antes de sua persistência estruturada.

---

## 2. Engenharia de Dados

A camada de Engenharia de Dados concentra os mecanismos responsáveis por transformar as respostas da API externa em registros consistentes, rastreáveis e disponíveis para consulta.

### 2.1 Ingestão de dados

A integração com o PNCP foi implementada utilizando Python e Requests, por meio de um cliente responsável pela comunicação HTTP.

Recursos implementados:

- Consumo de API REST externa.
- Requisições HTTP parametrizadas.
- Paginação para recuperação de grandes volumes de registros.
- Controle de limites de consulta.
- Tratamento de respostas HTTP.
- Separação entre comunicação externa e regras de negócio.
- Coleta individual por unidade federativa.
- Orquestração nacional de coleta das 27 unidades federativas.

### 2.2 Transformação e qualidade dos dados

Os dados recebidos passam por etapas de parsing, normalização e validação antes de serem encaminhados à persistência.

Técnicas aplicadas:

- Normalização de estruturas JSON.
- Padronização de atributos.
- Validação estrutural dos registros.
- Tratamento de campos ausentes ou inconsistentes.
- Conversão de registros externos para estruturas internas de persistência.
- Preservação do payload original.
- Identificação de alterações por meio de hash SHA-256.

A preservação do conteúdo original permite manter a rastreabilidade da informação recebida e oferece flexibilidade para futuras transformações.

### 2.3 Persistência e integridade

O PostgreSQL é utilizado como banco de dados relacional principal.

A camada de persistência foi desenvolvida com SQLAlchemy, utilizando o padrão Repository para isolar as operações de acesso aos dados.

Principais estratégias:

- Modelagem relacional.
- ORM com SQLAlchemy.
- Operações de INSERT e UPDATE.
- UPSERT para inserção ou atualização de registros.
- Deduplicação por identificadores de negócio.
- Preservação de payloads originais em JSON.
- Controle de histórico de sincronizações.
- Hash SHA-256 para identificação de alterações.
- Transações e integridade das operações no banco.

### 2.4 Idempotência e confiabilidade

Um dos desafios centrais do projeto foi desenvolver uma rotina de ingestão que pudesse ser executada repetidamente sem produzir duplicidades ou comprometer a consistência dos registros.

Para isso, foram implementados mecanismos de:

- Processamento idempotente.
- UPSERT.
- Controle de concorrência com PostgreSQL Advisory Locks.
- Registro de execuções de sincronização.
- Checkpoints e controle de progresso da coleta.
- Controle de cache e janela de reutilização da sincronização.
- Separação entre execução de coleta e consulta dos dados persistidos.

Essas estratégias permitem que o processo de ingestão seja reutilizado sem depender de uma nova coleta externa a cada consulta realizada pelo usuário.

### 2.5 Resiliência da integração externa

A comunicação com uma API pública exige tratamento de instabilidades, limites de requisição e respostas temporárias.

O cliente do PNCP implementa:

- Retry para falhas transitórias.
- Exponential Backoff.
- Interpretação do cabeçalho HTTP `Retry-After`.
- Tratamento de HTTP 429 (Too Many Requests).
- Tratamento de respostas HTTP 408, 500, 502, 503 e 504.
- Timeout individual de requisições.
- Prazo máximo total de execução.
- Limitação de tentativas e páginas consultadas.
- Tratamento de falhas de conexão e timeout.

A política de retry considera o tempo indicado pelo servidor quando disponível e utiliza backoff exponencial como estratégia alternativa.

---

## 3. Orquestração e processamento nacional

A coleta foi organizada em duas modalidades.

**Coleta individual por UF**

Permite executar a sincronização de uma unidade federativa específica, reutilizando o mesmo serviço de processamento.

**Orquestração nacional**

Coordena a execução sequencial da coleta para as 27 unidades federativas brasileiras.

O serviço de orquestração:

- Coordena as execuções individuais.
- Reutiliza a camada de sincronização.
- Mantém o isolamento de falhas por unidade federativa.
- Registra resultados individuais.
- Consolida o resultado geral da execução.
- Permite identificar unidades processadas com sucesso e unidades que apresentaram falhas.

A separação entre orquestração e processamento individual reduz o acoplamento e facilita a evolução da rotina de ingestão.

### Interface de linha de comando

A aplicação disponibiliza uma CLI desenvolvida com `argparse`.

```bash
# Coleta de uma unidade federativa
python -m app.cli coletar --uf RJ

# Orquestração da coleta nacional
python -m app.cli coletar-nacional
```

Essa abordagem permite executar processos de ingestão independentemente da interface web.

---

## 4. Analytics e exploração de dados

A camada de Analytics foi desenvolvida para transformar os registros armazenados em informações úteis para identificação e acompanhamento de oportunidades públicas.

O frontend funciona como uma camada de exploração dos dados, consumindo os registros disponibilizados pela API.

### 4.1 Exploração e segmentação

A interface oferece mecanismos para segmentar e consultar os registros de acordo com diferentes dimensões:

- Unidade federativa.
- Palavras-chave.
- Modalidade de contratação.
- Datas e prazos relacionados às oportunidades.
- Situação temporal das disputas.
- Registros com datas definidas ou não informadas.

Esses filtros permitem reduzir o universo de registros e direcionar a análise para oportunidades relevantes.

### 4.2 Indicadores e visualização temporal

A interface foi construída para facilitar a interpretação dos dados por meio de elementos visuais.

Recursos implementados:

- Indicadores de quantidade de registros.
- Organização temporal das oportunidades.
- Linha do tempo proporcional aos intervalos de datas.
- Identificação visual de prazos.
- Diferenciação de oportunidades por contexto temporal.
- Visualização tabular.
- Paginação dos resultados.
- Atualização dinâmica dos dados consultados.

A linha do tempo utiliza representação proporcional para facilitar a comparação visual entre datas e intervalos de disputa.

### 4.3 Estratégia de consulta e paginação

A integração entre frontend e backend foi desenvolvida para manter a consulta desacoplada da ingestão.

A aplicação utiliza:

- API REST como camada de disponibilização.
- Consultas filtradas no backend.
- Paginação de resultados.
- Parâmetros de consulta para segmentação dos registros.
- JavaScript para atualização dinâmica da interface.
- Separação entre os dados persistidos e a apresentação visual.

Essa arquitetura evita que a interface dependa diretamente da API externa do PNCP durante a navegação.

---

## 5. Arquitetura de software e padrões utilizados

O projeto adota uma arquitetura em camadas, com separação de responsabilidades e componentes especializados.

| Componente | Responsabilidade |
|---|---|
| `app/pncp/` | Integração com o PNCP, requisições e paginação |
| `app/services/` | Regras de negócio, sincronização e orquestração |
| `app/repositories/` | Persistência e acesso aos dados |
| `app/` | API REST e inicialização da aplicação |
| `frontend/` | Interface e visualização dos dados |
| `tests/` | Testes automatizados |

### Padrões e conceitos aplicados

- **Layered Architecture:** separação das responsabilidades em camadas.
- **Repository Pattern:** abstração da persistência e acesso aos dados.
- **Service Layer:** centralização das regras de negócio.
- **Idempotent Processing:** execução repetida sem duplicação indevida.
- **Upsert Strategy:** inserção ou atualização de registros.
- **Separation of Concerns:** isolamento das responsabilidades.
- **Fault Isolation:** tratamento de falhas sem interromper necessariamente todo o processamento nacional.
- **Pagination:** recuperação e disponibilização controlada de grandes conjuntos de registros.
- **Retry with Exponential Backoff:** recuperação de falhas transitórias.
- **Data Validation:** verificação de consistência antes da persistência.

---

## 6. API REST

A API foi construída utilizando FastAPI e funciona como camada de serviço entre o banco de dados e a interface.

Características:

- Endpoints REST.
- Validação de parâmetros.
- Consultas filtradas.
- Paginação.
- Separação entre rotas, serviços e repositórios.
- Tratamento de exceções.
- Documentação OpenAPI.
- Swagger UI para exploração dos endpoints.

Documentação local:

`http://127.0.0.1:8000/docs`

---

## 7. Tecnologias e ferramentas

### Backend e Engenharia de Dados

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem principal e processamento dos dados |
| Requests | Comunicação HTTP com o PNCP |
| FastAPI | Construção da API REST |
| SQLAlchemy | ORM e camada de persistência |
| PostgreSQL | Banco de dados relacional |
| Alembic | Migrações e versionamento do schema |
| JSON | Formato de intercâmbio e preservação dos dados originais |
| SHA-256 | Identificação de alterações nos registros |
| Argparse | Interface de linha de comando |

### Analytics e Frontend

| Tecnologia | Aplicação |
|---|---|
| JavaScript | Manipulação dinâmica e integração com a API |
| HTML5 | Estrutura da interface |
| CSS3 | Estilização e visualizações |
| Fetch API | Comunicação entre frontend e backend |
| REST | Contrato de comunicação entre as camadas |

### Qualidade e desenvolvimento

| Tecnologia | Aplicação |
|---|---|
| Pytest | Testes automatizados |
| Git | Controle de versão |
| GitHub | Hospedagem e gerenciamento do código |
| GitHub Actions | Integração contínua |
| pip-audit | Auditoria de vulnerabilidades em dependências |

---

## 8. Qualidade, testes e segurança

A qualidade do processamento e a confiabilidade da aplicação foram consideradas durante o desenvolvimento.

### Testes automatizados

A suíte de testes contempla diferentes níveis de validação:

- Testes unitários de funções de processamento.
- Testes do cliente de integração com o PNCP.
- Testes de paginação.
- Testes de normalização e validação dos registros.
- Testes de retry e tratamento de erros transitórios.
- Testes da camada de persistência.
- Testes de rotas da API.
- Testes da CLI.
- Testes de integração com PostgreSQL.

### Segurança

Foram consideradas práticas de desenvolvimento seguro, incluindo:

- Configurações sensíveis por variáveis de ambiente.
- Validação de entradas.
- Consultas parametrizadas.
- Tratamento de exceções.
- Headers de segurança HTTP.
- Content Security Policy (CSP).
- Rate limiting.
- Auditoria de dependências.

### Integração contínua

O GitHub Actions automatiza verificações do projeto, incluindo execução de testes e validações do ambiente de desenvolvimento.

O objetivo é identificar regressões e problemas antes da integração de novas alterações à base de código.

---

## 9. Execução local

### Pré-requisitos

- Python 3.12 ou superior.
- PostgreSQL.
- Git.

### Clonagem

```bash
git clone https://github.com/gdracojj/nexus.git
cd nexus
```

### Ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate
```

### Dependências

```bash
pip install -r requirements.txt
```

### Configuração

Configure as variáveis de ambiente necessárias para a conexão com o PostgreSQL e os parâmetros da aplicação.

### Migrações

```bash
alembic upgrade head
```

### Inicialização da API

```bash
uvicorn app.main:app --reload
```

### Execução da coleta

```bash
# Individual
python -m app.cli coletar --uf RJ

# Nacional
python -m app.cli coletar-nacional
```

### Testes

```bash
python -m pytest -q
```

---

## 10. Escopo encerrado — Nexus V1

A versão 1.0 consolida o fluxo principal de Engenharia de Dados e Analytics da plataforma.

| Entrega | Status |
|---|---|
| Integração com a API do PNCP | Concluído |
| Pipeline de ingestão ETL | Concluído |
| Paginação e extração | Concluído |
| Parsing e normalização | Concluído |
| Validação dos registros | Concluído |
| Persistência PostgreSQL | Concluído |
| UPSERT e deduplicação | Concluído |
| Hash e preservação de payload | Concluído |
| Histórico de sincronização | Concluído |
| Retry e Exponential Backoff | Concluído |
| Coleta individual por UF | Concluído |
| Orquestração nacional | Implementada |
| API REST | Concluído |
| Frontend integrado | Concluído |
| Filtros e paginação analítica | Concluído |
| Linha do tempo e indicadores | Concluído |
| Testes automatizados | Implementados |
| Integração contínua | Implementada |

**Nexus V1 — Escopo funcional encerrado.**

A V1 entrega uma estrutura integrada para ingestão, tratamento, armazenamento, consulta e exploração de dados públicos de contratações.

---

## 11. Roadmap — Nexus V2

A próxima etapa de evolução está direcionada à ampliação das capacidades analíticas e à gestão de informações posteriores à publicação das oportunidades.

Possíveis evoluções:

- Gestão de Atas de Registro de Preços.
- Controle de vigência e saldo quantitativo.
- Monitoramento de reajustes e prazos.
- Autenticação e controle de acesso.
- Análise automatizada de editais.
- Extração de informações com modelos de IA.
- Agentes especializados para enriquecimento e classificação dos dados.
- Ampliação da arquitetura analítica.
- Exploração de tecnologias de processamento e análise em larga escala.

Essas funcionalidades pertencem ao planejamento da V2 e não são apresentadas como entregas concluídas da primeira versão.

---

## 12. Objetivo técnico do projeto

O Nexus foi desenvolvido para explorar desafios práticos encontrados em projetos de Engenharia de Dados e Analytics:

- Integração com fontes externas de dados.
- Ingestão de registros em escala.
- Tratamento de inconsistências.
- Garantia de integridade e rastreabilidade.
- Persistência estruturada.
- Resiliência em integrações HTTP.
- Orquestração de processos.
- Disponibilização de dados por APIs.
- Construção de interfaces para exploração analítica.

O projeto demonstra a construção de um fluxo completo de dados, desde a origem até a disponibilização de informações para análise e apoio à tomada de decisão.

---

**Desenvolvido por Gabriel Silva**

GitHub: https://github.com/gdracojj

Repositório: https://github.com/gdracojj/nexus