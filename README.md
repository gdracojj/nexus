# Nexus — Plataforma de Inteligência e Gestão de Licitações Públicas

![Status do Projeto](https://img.shields.io/badge/status-em_desenvolvimento-orange)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.143.0-009688?logo=fastapi)

O **NEXUS** consulta oportunidades publicadas no **Portal Nacional de Contratações Públicas (PNCP)** e permite filtrá-las por estado e termo do objeto. O projeto foi concebido a partir de necessidades operacionais da **RCCS Licitações** e também é um projeto de portfólio sobre integração com APIs externas e desenvolvimento backend.

Além de sua aplicação prática no mercado, o NEXUS é um projeto de portfólio focado nas disciplinas de **Desenvolvimento Backend**, **Engenharia de Dados**, **Resiliência de Integração** e **Arquitetura de Software**.

---

## 📌 Visão Geral e Problema de Negócio

A identificação de oportunidades no mercado público pode exigir pesquisas frequentes no PNCP. Hoje, o NEXUS consulta o portal em tempo de execução e apresenta os resultados filtrados. O controle de Atas de Registro de Preços, saldos, vigências e reajustes é um objetivo futuro do produto; não está implementado nesta versão.

O projeto tem dois objetivos de produto, em estágios diferentes:

1. **Disponível:** consulta de contratações no PNCP, normalização dos registros e filtragem local por UF e termo textual no objeto.
2. **Planejado:** gestão pós-contratação de Atas de Registro de Preços, incluindo saldos e vigências.

---

## 🎯 Status Atual do Projeto

O projeto oferece uma API FastAPI e um painel frontend inicial. A aplicação consulta o endpoint de contratações do PNCP, percorre as páginas informadas pela API, normaliza os registros, grava ou atualiza os dados no PostgreSQL e filtra por UF e termo do objeto.

---

## 🛠️ Tecnologias Utilizadas e Planejadas

### Implementadas
* **Backend:** Python 3.10+, FastAPI e Uvicorn.
* **Integração HTTP:** Requests para consultar o PNCP.
* **Frontend:** HTML, CSS e JavaScript sem framework.
* **Comunicação:** API HTTP com payloads JSON.
* **Persistência:** PostgreSQL com SQLAlchemy e Alembic; contratações são deduplicadas pelo `numeroControlePNCP` do PNCP.

As dependências de execução estão declaradas em `requirements.txt`. A URL do banco é lida de `DATABASE_URL` (ou `POSTGRES_URL`). O schema é aplicado por migrations Alembic; a aplicação não cria tabelas automaticamente.

### Planejadas para as Próximas Fases
* **Engenharia de Dados:** Pipelines ETL/ELT, atualização incremental
* **Infraestrutura e Conteinerização:** Docker, Docker Compose
* **Testes e Qualidade:** Pytest com testes unitários e de integração PostgreSQL
* **Analytics & IA:** Integração com Power BI / BI Tools e recursos de Processamento de Linguagem Natural (NLP) para análise de editais

---

## 🏗️ Arquitetura do Sistema

### 1. Arquitetura Atual (Consulta Síncrona com Persistência)
As pesquisas consultam o PNCP em tempo de execução, normalizam os registros, fazem upsert no PostgreSQL e retornam os registros filtrados.

```
[ Usuário / Frontend ]
         │
         ▼
[ FastAPI (app/main.py) ]
         │
         ▼
[ LicitacaoService ] ──▶ [ PNCP Client ] ──(HTTP)──▶ [ API do PNCP ]
         │                        │
         ▼                        ▼
[ Filtro por UF/Produto ] ◀── [ Parser / Normalização ]
         │
         └──▶ [ Repository ] ──▶ [ PostgreSQL ]
```

### 2. Próxima evolução (ingestão desacoplada)
Uma evolução possível é desacoplar a consulta do usuário das chamadas externas por meio de uma rotina de coleta recorrente:

```
[ API PNCP ] ──▶ [ Ingestão / ETL ] ──▶ [ Parser ] ──▶ [ PostgreSQL ]
                                                            │
[ Usuário / Frontend ] ◀── [ FastAPI ] ◀── [ Repositorio ] ─┘
```

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
* **Falhas permanentes:** outros status HTTP e erros TLS não são repetidos. Se o prazo total acabar antes de uma nova tentativa, a consulta termina e a API responde com erro genérico `502`.

> A consulta e ingestão são síncronas e dependem da disponibilidade e do tempo de resposta do PNCP. Requests limita a inatividade da conexão, não o tempo absoluto de download da resposta; por isso, uma resposta que envie dados continuamente pode ultrapassar o prazo de 120 segundos. A persistência mantém os registros coletados; coleta recorrente desacoplada permanece no roadmap.

---

## 📂 Estrutura de Arquivos do Repositório

```text
nexus/
├── app/
│   ├── core/
│   │   ├── config.py          # configuração por ambiente
│   │   └── logger.py          # vazio; reservado
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
│   │   └── licitacao_service.py  # Regras de negócio e filtragem
│   └── main.py               # Aplicação FastAPI, rota REST e montagem do frontend
├── frontend/
│   ├── app.js
│   ├── assets.js
│   ├── index.html
│   ├── style.css
│   ├── variables.css
│   └── assets/
│       ├── favicon.png
│       ├── nexus-mark.png
│       └── nexus-wordmark.png
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_persistence.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md                 # Documentação do projeto
```

Os testes incluem parser/cliente e integração PostgreSQL. Para a integração é obrigatório apontar `NEXUS_TEST_DATABASE_URL` para uma base descartável; cada execução cria e remove um schema isolado.

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
   pip install -r requirements.txt
   ```

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

7. **Acessar a aplicação:**
   * **Interface Web (Frontend):** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Documentação Interativa (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Para executar os testes unitários use `python -m pytest -q`. Os testes de integração PostgreSQL são habilitados com `NEXUS_TEST_DATABASE_URL` apontando para um banco de testes descartável; eles criam e removem um schema `nexus_test_*` dentro dessa base.

### Persistência PNCP

`licitacoes.numero_controle_pncp` usa o `numeroControlePNCP` do PNCP como chave externa única. A tabela `pncp_payloads` mantém um único snapshot JSONB por contratação: o SHA-256 evita regravar cópias idênticas e o snapshot é substituído quando o conteúdo muda. O histórico das execuções fica em `sync_execucoes`; cada lote de upserts e a conclusão da execução são confirmados na mesma transação. Falhas de ingestão são registradas em transação separada, quando o banco continua acessível.

O mapeamento usa o resumo do endpoint de propostas abertas e os campos documentados pelo [Swagger da API de Consulta do PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html) e pelo [manual oficial de integração](https://pncp.gov.br/manual/pt-br/latest/singlehtml/index.html). Datas sem fuso explícito são interpretadas no horário de Brasília; valores monetários são persistidos como `NUMERIC(20,4)`.

O endpoint atual consulta contratações com propostas abertas e não consulta itens. Por isso a primeira versão não cria `licitacao_itens`. Atas de Registro de Preços são entidades distintas: sua futura modelagem deve confirmar os identificadores de contratação/ata publicados pelo PNCP e preservar movimentações de saldo em histórico próprio.

PostgreSQL local não oferece branches do conteúdo do banco. Para isolar cada alteração de schema, crie uma branch Git `db/<alteracao>` e uma migration Alembic própria; migrations são a trilha reproduzível de mudanças entre local e Docker. A branch Git não é uma cópia isolada dos dados.

---

## 📡 Endpoints da API

### `GET /api/licitacoes`
Realiza a consulta de oportunidades vigentes no PNCP aplicadas aos filtros locais.

#### Parâmetros da Requisição (Query Params)
| Parâmetro | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `uf` | `string` | **Sim** | Sigla da Unidade Federativa com 2 caracteres (Ex: `RJ`, `SP`). |
| `produto` | `string` | Não | Termo opcional para busca sem distinção entre maiúsculas e minúsculas na descrição/objeto. O padrão é vazio. |

`uf` é removido de espaços nas extremidades e convertido para maiúsculas. A rota verifica se possui exatamente dois caracteres; não valida se esses caracteres correspondem a uma UF oficial. A consulta do cliente envia ao PNCP a data atual e os sete dias seguintes, a modalidade de contratação `6` e o número da página.

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
  "resultados": [
    {
      "numero": "00001/2026",
      "descricao": "Aquisição de material de expediente...",
      "codigo_unidade": "123456",
      "municipio": "Rio de Janeiro",
      "uf": "RJ",
      "data_encerramento_proposta": "2026-10-15T23:59:59"
    }
  ]
}
```

`total_consultado` conta os registros normalizados consultados; `total` conta os que passaram pelo filtro de UF e, quando informado, pelo termo em `produto`. A rota também pode responder:

| Status | Situação | Corpo |
| :--- | :--- | :--- |
| `400` | `uf` com comprimento diferente de 2 | `{"detail":"Informe a sigla do estado com 2 letras."}` |
| `422` | Parâmetro obrigatório ausente ou parâmetros que não passam pela validação do FastAPI | Corpo de validação do FastAPI |
| `502` | Falha de requisição ao PNCP, incluindo timeout, conexão ou erro HTTP | `{"detail":"Não foi possível consultar o PNCP. Tente novamente mais tarde."}` |
| `500` | Erro interno inesperado | `{"detail":"Erro interno ao processar a consulta."}` |

As mensagens públicas dos erros `502` e `500` são genéricas; detalhes técnicos são enviados ao diagnóstico do servidor, não ao corpo da resposta.

---

## 🗺️ Roadmap de Desenvolvimento

O desenvolvimento do NEXUS é estruturado de forma iterativa e incremental:

- [x] **Fase 1 — Consolidação da Coleta e API REST**
  - [x] Integração funcional com a API do PNCP.
  - [x] Normalização de payload em DTOs internos (`parser.py`).
  - [x] Tentativas limitadas e espera exponencial para falhas transitórias do PNCP.
  - [x] Endpoint FastAPI e Painel Frontend com estilização operacional.
- [x] **Fase 2 — Implementação da persistência e migration inicial**
  - [x] Campos normalizados do endpoint PNCP, com payload original JSONB.
  - [x] Upsert idempotente pelo identificador estável `numeroControlePNCP`.
  - [x] Registro de cada execução e seu resultado.
  - [x] Migration versionada com Alembic.
  - [ ] Expansão do schema conforme novos endpoints e necessidades confirmadas.
- [ ] **Fase 3 — Engenharia de Dados & Ingestão Assíncrona**
  - [ ] Desacoplamento da busca do usuário em relação às chamadas externas.
  - [ ] Criação de rotinas de coleta recorrente e atualização incremental da base.
- [ ] **Fase 4 — Módulo de Gestão Pós-Contratação**
  - [ ] Cadastro e vinculação de Atas de Registro de Preços.
  - [ ] Controle automatizado de saldo de quantitativos, prazos de vigência e reajustes.
- [ ] **Fase 5 — Observabilidade, Testes & Conteinerização**
  - [ ] Testes unitários e de integração com `pytest`.
  - [ ] Conteinerização total da solução via `Docker` e `Docker Compose`.
  - [ ] Estruturação de dashboards analíticos e exploração de recursos de IA para leitura de editais.

---

## ⚠️ Limitações Conhecidas

* **Dependência Síncrona Temporária:** A consulta síncrona atual pode apresentar latência em buscas com volume extenso de páginas no PNCP.
* **Filtros Textuais Básicos:** A filtragem por palavra-chave é puramente textual (case-insensitive), sem suporte a sinônimos ou busca semântica (planejada para etapas futuras).
* **Ausência de Módulo Persistente Pós-Compra:** As telas de acompanhamento de atas e saldos encontram-se em fase de especificação e modelagem.

---

## 📄 Licença

O repositório não contém atualmente um arquivo `LICENSE`; a licença do projeto ainda não está documentada.

---

**Desenvolvido por Gabriel Draco**  
*Engenharia de Software & Data Engineering* — [GitHub](https://github.com/gdracojj)
