# Nexus — Plataforma de Inteligência e Gestão de Licitações Públicas

![Status do Projeto](https://img.shields.io/badge/status-em_desenvolvimento-orange)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.143.0-009688?logo=fastapi)

O **NEXUS** coleta oportunidades publicadas no **Portal Nacional de Contratações Públicas (PNCP)** e permite consultá-las por estado, prazo e termo do objeto através de uma API REST e de um painel web responsivo. O projeto foi concebido a partir de necessidades operacionais da **RCCS Licitações** e também é um projeto de portfólio sobre integração com APIs externas e desenvolvimento backend.

Além de sua aplicação prática no mercado, o NEXUS é um projeto de portfólio focado nas disciplinas de **Desenvolvimento Backend**, **Engenharia de Dados**, **Resiliência de Integração** e **Arquitetura de Software**.

---

## 📌 Visão Geral e Problema de Negócio

A identificação de oportunidades no mercado público pode exigir pesquisas frequentes no PNCP. O NEXUS coleta oportunidades por um comando operacional separado, persiste os resultados e permite consultá-los pela API. O controle de Atas de Registro de Preços, saldos, vigências e reajustes é um objetivo futuro do produto; não está implementado nesta versão.

O projeto tem dois objetivos de produto, em estágios diferentes:

1. **Disponível:** coleta explícita de contratações no PNCP, normalização, persistência e consulta por UF e termo textual no objeto.
2. **Planejado:** gestão pós-contratação de Atas de Registro de Preços, incluindo saldos e vigências.

---

## 🎯 Status Atual do Projeto

O projeto oferece uma API FastAPI e um painel web sem framework JavaScript. O comando de coleta consulta o PNCP, percorre as páginas informadas pela API, normaliza os registros e grava ou atualiza os dados no PostgreSQL. A API consulta os dados persistidos; o painel apresenta prazos em visões geral, timeline e quadro.

---

## 🛠️ Tecnologias Utilizadas e Planejadas

### Implementadas
* **Backend:** Python 3.10+, FastAPI e Uvicorn.
* **Integração HTTP:** Requests para consultar o PNCP.
* **Interface:** HTML, CSS responsivo e JavaScript em módulos ES nativos.
* **Comunicação:** API HTTP com payloads JSON.
* **Persistência:** PostgreSQL com SQLAlchemy e Alembic; contratações são deduplicadas pelo `numeroControlePNCP` do PNCP.

As dependências de execução estão declaradas em `requirements.txt`. A URL do banco é lida de `DATABASE_URL` (ou `POSTGRES_URL`). O schema é aplicado por migrations Alembic; a aplicação não cria tabelas automaticamente.

### Planejadas para as Próximas Fases
* **Engenharia de Dados:** Pipelines ETL/ELT, atualização incremental
* **Infraestrutura e Conteinerização:** Docker, Docker Compose
* **Testes e Qualidade:** expansão da cobertura e execução da integração PostgreSQL em ambiente de teste
* **Analytics & IA:** Integração com Power BI / BI Tools e recursos de Processamento de Linguagem Natural (NLP) para análise de editais

---

## 🏗️ Arquitetura do Sistema

### 1. Arquitetura Atual (Leitura Persistida e Coleta Explícita)
O endpoint de leitura consulta somente os registros já persistidos no PostgreSQL. A coleta do PNCP é iniciada separadamente pelo comando `python -m app.cli coletar --uf RJ`; esse comando pode ser executado manualmente ou agendado pelo scheduler do sistema operacional.

```
[ Navegador / Painel ] ──▶ [ FastAPI ] ──▶ [ Repository ] ──▶ [ PostgreSQL ]
                                            ▲
[ Scheduler / Operador ] ──▶ [ CLI ] ──▶ [ Serviço de Coleta ]
                                             │
                                             ▼
                         [ PNCP Client ] ──(HTTP)──▶ [ API do PNCP ]
                               │
                               ▼
                     [ Parser / Normalização ] ──▶ [ Repository ]
```

O PostgreSQL mantém um advisory lock global de sessão durante a coleta, permitindo apenas uma coleta simultânea entre processos e workers conectados ao mesmo banco. Se outra coleta já estiver ativa, o comando termina com erro em vez de iniciar trabalho duplicado. Cada processo limita o pool SQLAlchemy a 5 conexões persistentes, 10 conexões excedentes e 30 segundos para aguardar uma conexão; cada worker de aplicação mantém seu próprio pool. Não há scheduler interno: a periodicidade é definida pelo operador no cron, Task Scheduler ou ferramenta equivalente.

A CLI reutiliza a contagem da coleta concluída mais recente quando endpoint e parâmetros são idênticos e a execução terminou nos últimos 900 segundos. A janela pode ser alterada por `PNCP_SYNC_CACHE_TTL_SECONDS` entre 0 e 86400; `0` desativa o reuso. Uma execução falha ou ainda em andamento mais recente invalida o resultado anterior. O lock global ainda limita toda coleta a uma por vez, inclusive para UFs diferentes, como limite conservador de concorrência com o PNCP.

---

## ⚡ Integração PNCP, Paginação e Resiliência HTTP

### Endpoint de Consulta Integrado
A aplicação consome o seguinte endpoint oficial do PNCP:
`https://pncp.gov.br/api/consulta/v1/contratacoes/proposta`

### Paginação e limite de taxa
O cliente percorre as páginas usando o campo `totalPaginas` retornado pelo PNCP e agrega os registros antes de normalizá-los. Cada consulta aceita no máximo 100 páginas. O prazo de 120 segundos é compartilhado entre todas as páginas, tentativas, esperas e normalização dos registros.

### Camada Inicial de Resiliência Implementada
O comportamento implementado em `app/pncp/client.py` é:
* **Intervalo entre páginas:** pausa de 1 segundo entre páginas sucessivas.
* **Tentativas:** até 5 por página, contando a requisição inicial, para timeouts, erros de conexão e status HTTP `408`, `429`, `500`, `502`, `503` ou `504`.
* **Backoff:** espera exponencial de `2`, `4`, `8` e `16` segundos quando não há um `Retry-After` válido.
* **`Retry-After`:** aceita segundos inteiros ou uma data HTTP. Datas passadas resultam em espera zero. Esperas solicitadas acima de 60 segundos causam falha imediata.
* **Falhas permanentes:** outros status HTTP e erros TLS não são repetidos. Se o prazo total acabar antes de uma nova tentativa, a coleta falha e o comando termina com código diferente de zero.

> A coleta é síncrona no processo CLI e depende da disponibilidade e do tempo de resposta do PNCP. Requests limita a inatividade da conexão, não o tempo absoluto de download da resposta; por isso, uma resposta que envie dados continuamente pode ultrapassar o prazo de 120 segundos. A rota de leitura não depende do PNCP e continua consultando os registros já persistidos durante uma indisponibilidade externa.

---

## 📂 Estrutura de Arquivos do Repositório

```text
nexus/
├── app/
│   ├── core/
│   │   ├── config.py          # configuração por ambiente
│   │   └── logger.py          # vazio; reservado
│   ├── cli.py                 # comando explícito de coleta PNCP
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py      # engine e sessões SQLAlchemy
│   │   └── models.py          # licitações, payloads e execuções PNCP
│   ├── pncp/
│   │   ├── client.py         # Cliente HTTP, paginação e políticas de retry/backoff
│   │   └── parser.py         # Normalização do payload JSON do PNCP
│   ├── repositories/
│   │   └── licitacao_repository.py  # upsert e consultas persistidas
│   ├── services/
│   │   └── licitacao_service.py  # consulta persistida e serviço de coleta
│   └── main.py               # Aplicação FastAPI, rota REST e arquivos estáticos
├── frontend/
│   ├── api.js                 # cliente HTTP e normalização da resposta
│   ├── app.js                 # navegação, filtros e renderização
│   ├── index.html             # shell da aplicação
│   ├── nexus.css              # temas e layout responsivo
│   ├── prazo.js               # parsing e classificação de prazos
│   └── theme.js               # restauração do tema salvo
├── tests/
│   ├── test_api_route.py
│   ├── test_cli.py
│   ├── test_persistence_postgresql.py
│   ├── test_pncp_pagination.py
│   ├── test_pncp_parser.py
│   ├── test_pncp_record_validation.py
│   └── test_pncp_transient_retries.py
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_persistence.py
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-test.txt
└── README.md                 # Documentação do projeto
```

`requirements.txt` contém as dependências da aplicação; `requirements-test.txt` inclui essas dependências mais `pytest` e `httpx2` para os testes HTTP com FastAPI `TestClient`. Para executar integração PostgreSQL, aponte `NEXUS_TEST_DATABASE_URL` para uma base descartável; cada execução cria e remove um schema isolado.

---

## 🚀 Como Executar o Projeto Localmente

### Pré-requisitos
* **Python 3.10+** instalado
* **PostgreSQL** acessível, com um banco criado para o NEXUS
* Ambientes baseados em **Linux/macOS** ou **Windows (WSL2/PowerShell)**
* Git

### Passos para Instalação e Execução

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/gdracojj/nexus.git
   cd nexus
   ```

2. **Criar e ativar o ambiente virtual (venv):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   # No Windows (PowerShell): .venv\Scripts\activate
   ```

3. **Instalar as dependências:**
   ```bash
   pip install -r requirements-test.txt
   ```
   Para instalar apenas o necessário à aplicação, use `pip install -r requirements.txt`.

4. **Configurar o banco:**
   ```bash
   cp .env.example .env
   ```
   Ajuste `DATABASE_URL` no `.env` para as credenciais do PostgreSQL e para o banco `main` (ou o nome escolhido). Exemplo:
   `postgresql+psycopg2://usuario:senha@localhost:5432/main`

5. **Aplicar o schema versionado:**
   ```bash
   python -m alembic upgrade head
   python -m alembic current
   ```

6. **Iniciar o servidor Backend (FastAPI + Uvicorn):**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

7. **Executar uma coleta inicial (em outro terminal):**
   ```bash
   python -m app.cli coletar --uf RJ
   ```
   O mesmo comando pode ser agendado no cron, Windows Task Scheduler ou ferramenta operacional equivalente. Enquanto uma coleta estiver ativa, outra execução é recusada pelo lock PostgreSQL.

8. **Acessar a aplicação:**
   * **Documentação Interativa (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   * **OpenAPI:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

Para executar os testes use `python -m pytest -q`. Os testes de integração PostgreSQL são habilitados com `NEXUS_TEST_DATABASE_URL` apontando para um banco de testes descartável; eles criam e removem um schema `nexus_test_*` dentro dessa base.

### Persistência PNCP

`licitacoes.numero_controle_pncp` usa o `numeroControlePNCP` do PNCP como chave externa única. A tabela `pncp_payloads` mantém um único snapshot JSONB por contratação: o SHA-256 evita regravar cópias idênticas e o snapshot é substituído quando o conteúdo muda. `coletada_em` registra a primeira coleta conhecida pelo NEXUS e permanece inalterado em upserts posteriores; `atualizada_em` registra a sincronização mais recente; `data_publicacao` é a data de publicação informada pelo PNCP. A migration inicial já tinha os dois campos de coleta/atualização, portanto essa correção não requer migration nem inventa datas para registros existentes. Para dados anteriores à correção, `coletada_em` pode representar uma sincronização posterior à descoberta original, e esse histórico não pode ser reconstruído com segurança. O histórico das execuções fica em `sync_execucoes`; os upserts de licitações e payloads são enviados em lotes de até 250 chaves, e os lotes e a conclusão da execução são confirmados na mesma transação. Falhas de ingestão são registradas em transação separada, quando o banco continua acessível.

O mapeamento usa o resumo do endpoint de propostas abertas e os campos documentados pelo [Swagger da API de Consulta do PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html) e pelo [manual oficial de integração](https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html). Datas sem fuso explícito são interpretadas no horário de Brasília; valores monetários são persistidos como `NUMERIC(20,4)`.

O endpoint atual consulta contratações com propostas abertas e não consulta itens. Por isso a primeira versão não cria `licitacao_itens`. Atas de Registro de Preços são entidades distintas: sua futura modelagem deve confirmar os identificadores de contratação/ata publicados pelo PNCP e preservar movimentações de saldo em histórico próprio.

PostgreSQL local não oferece branches do conteúdo do banco. Para isolar cada alteração de schema, crie uma branch Git `db/<alteracao>` e uma migration Alembic própria; migrations são a trilha reproduzível de mudanças entre local e Docker. A branch Git não é uma cópia isolada dos dados.

---

## 📡 Endpoints da API

### `GET /api/licitacoes`
Consulta oportunidades vigentes já persistidas no PostgreSQL (ou registros sem prazo de encerramento informado). A rota não inicia coleta PNCP; uma lista vazia é uma resposta válida quando ainda não houve coleta ou quando não há oportunidades vigentes para a UF solicitada.

#### Parâmetros da Requisição (Query Params)
| Parâmetro | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `uf` | `string` | Não | Sigla da Unidade Federativa com 2 caracteres (Ex: `RJ`, `SP`). Se omitida, consulta todas as UFs. |
| `produto` | `string` | Não | Termo opcional para busca sem distinção entre maiúsculas e minúsculas na descrição/objeto. O padrão é vazio. |

`uf`, quando informado, é removido de espaços nas extremidades e convertido para maiúsculas. A rota verifica se possui exatamente dois caracteres; não valida se esses caracteres correspondem a uma UF oficial. O termo `produto` é removido de espaços nas extremidades e convertido para minúsculas.

#### Exemplo de Chamada
```bash
curl -X GET "http://127.0.0.1:8000/api/licitacoes?uf=RJ&produto=material"
```

#### Exemplo de Resposta (`200 OK`)
```json
{
  "uf": "RJ",
  "produto": "material",
  "total_consultado": 150,
  "total": 12,
  "ultima_sincronizacao": "2026-10-30T12:00:00+00:00",
  "resultados": [
    {
      "numero_controle_pncp": "12345678000199-1-000001/2026",
      "numero": "00001/2026",
      "descricao": "Aquisição de material de expediente...",
      "codigo_unidade": "123456",
      "unidade": "123456",
      "orgao": "Órgão público",
      "codigo_modalidade": 6,
      "municipio": "Rio de Janeiro",
      "uf": "RJ",
      "valor_estimado": 1200.5,
      "data_encerramento_proposta": "2026-10-15T23:59:59"
    }
  ]
}
```

`total_consultado` conta os registros persistidos com prazo vigente (ou sem prazo informado) para a UF antes do filtro `produto`; `total` conta os registros que correspondem à UF e ao termo informado. Se `uf` for omitida, ambos consideram todas as UFs. `ultima_sincronizacao` informa a conclusão mais recente de uma sincronização bem-sucedida. A rota também pode responder:

| Status | Situação | Corpo |
| :--- | :--- | :--- |
| `400` | `uf` com comprimento diferente de 2 | `{"detail":"Informe a sigla do estado com 2 letras."}` |
| `422` | Parâmetros que não passam pela validação de tipos do FastAPI | Corpo de validação do FastAPI |
| `500` | Falha inesperada ao consultar o PostgreSQL ou erro interno | `{"detail":"Erro interno ao processar a consulta."}` |

Falhas do PNCP ocorrem no comando de coleta, que termina com código diferente de zero; não alteram o status HTTP das consultas aos dados já persistidos. As mensagens públicas de erro `500` são genéricas e não incluem detalhes técnicos.

---

## 🗺️ Roadmap de Desenvolvimento

O desenvolvimento do NEXUS é estruturado de forma iterativa e incremental:

- [x] **Fase 1 — Consolidação da Coleta e API REST**
  - [x] Integração funcional com a API do PNCP.
  - [x] Normalização de payload em DTOs internos (`parser.py`).
  - [x] Tentativas limitadas e espera exponencial para falhas transitórias do PNCP.
  - [x] Endpoint FastAPI com documentação OpenAPI.
- [x] **Fase 2 — Implementação da persistência e migration inicial**
  - [x] Campos normalizados do endpoint PNCP, com payload original JSONB.
  - [x] Upsert idempotente pelo identificador estável `numeroControlePNCP`.
  - [x] Registro de cada execução e seu resultado.
  - [x] Migration versionada com Alembic.
  - [x] Leitura da API desacoplada da coleta PNCP, iniciada por CLI com lock PostgreSQL.
  - [ ] Expansão do schema conforme novos endpoints e necessidades confirmadas.
- [ ] **Fase 3 — Engenharia de Dados & Automação de Coleta**
  - [ ] Agendamento operacional da coleta e atualização incremental da base.
  - [ ] Ampliação da observabilidade e recuperação de execuções interrompidas.
- [ ] **Fase 4 — Módulo de Gestão Pós-Contratação**
  - [ ] Cadastro e vinculação de Atas de Registro de Preços.
  - [ ] Controle automatizado de saldo de quantitativos, prazos de vigência e reajustes.
- [ ] **Fase 5 — Observabilidade & Conteinerização**
  - [x] Testes unitários, de integração e do contrato HTTP com `pytest`.
  - [x] Painel web para consulta e acompanhamento visual dos prazos.
  - [ ] Conteinerização total da solução via `Docker` e `Docker Compose`.
  - [ ] Estruturação de dashboards analíticos e exploração de recursos de IA para leitura de editais.

---

## ⚠️ Limitações Conhecidas

* **Coleta Síncrona Operacional:** o comando que coleta o PNCP permanece ativo durante paginação, tentativas e persistência, dentro do prazo configurado; a API de leitura não aguarda esse trabalho.
* **Painel informativo:** o painel apresenta oportunidades persistidas pelo NEXUS; a confirmação e os detalhes oficiais devem ser consultados no PNCP.
* **Filtros Textuais Básicos:** A filtragem por palavra-chave é puramente textual (case-insensitive), sem suporte a sinônimos ou busca semântica (planejada para etapas futuras).
* **Ausência de Módulo Persistente Pós-Compra:** As telas de acompanhamento de atas e saldos encontram-se em fase de especificação e modelagem.

---

## 📄 Licença

O repositório não contém atualmente um arquivo `LICENSE`; a licença do projeto ainda não está documentada.

---

**Desenvolvido por Gabriel Draco**  
*Engenharia de Software & Data Engineering* — [GitHub](https://github.com/gdracojj)
