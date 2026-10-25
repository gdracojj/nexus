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

O projeto oferece uma API FastAPI e um painel frontend inicial. A aplicação consulta diretamente o endpoint de contratações do PNCP, percorre as páginas informadas pela API, normaliza os registros e filtra por UF e termo do objeto. Não há persistência conectada ao fluxo da aplicação: os dados são obtidos novamente a cada consulta.

---

## 🛠️ Tecnologias Utilizadas e Planejadas

### Implementadas
* **Backend:** Python 3.10+, FastAPI e Uvicorn.
* **Integração HTTP:** Requests para consultar o PNCP.
* **Frontend:** HTML, CSS e JavaScript sem framework.
* **Comunicação:** API HTTP com payloads JSON.

As dependências de execução estão declaradas em `requirements.txt`. O arquivo também inclui `psycopg2-binary`, mas a aplicação ainda não usa PostgreSQL para persistir dados.

### Planejadas para as Próximas Fases
* **Banco de Dados Relacional:** PostgreSQL
* **Modelagem e Persistência:** SQLAlchemy / SQLModel, Alembic (migrações)
* **Engenharia de Dados:** Pipelines ETL/ELT, atualização incremental
* **Infraestrutura e Conteinerização:** Docker, Docker Compose
* **Testes e Qualidade:** Pytest, cobertura de testes automatizados
* **Analytics & IA:** Integração com Power BI / BI Tools e recursos de Processamento de Linguagem Natural (NLP) para análise de editais

---

## 🏗️ Arquitetura do Sistema

### 1. Arquitetura Atual (Consulta Síncrona)
Atualmente, as pesquisas feitas na interface consultam diretamente a API do PNCP em tempo de execução, realizando a paginação e normalização dos dados antes de retornar ao usuário.

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
```

### 2. Arquitetura planejada (ingestão e persistência)
Uma evolução possível é desacoplar a consulta do usuário da API externa e armazenar os dados em uma base persistente. Esse fluxo ainda não está implementado:

```
[ API PNCP ] ──▶ [ Ingestão / ETL ] ──▶ [ Parser ] ──▶ [ PostgreSQL ]
                                                            │
[ Usuário / Frontend ] ◀── [ FastAPI ] ◀── [ Repositorio ] ─┘
```

---

## ⚡ Integração PNCP, Paginação e Resiliência (HTTP 429)

### Endpoint de Consulta Integrado
A aplicação consome o seguinte endpoint oficial do PNCP:
`https://pncp.gov.br/api/consulta/v1/contratacoes/proposta`

### Paginação e limite de taxa
O cliente percorre as páginas usando o campo `totalPaginas` retornado pelo PNCP e agrega os registros antes de normalizá-los. Não há um limite máximo de páginas configurado localmente. Respostas HTTP 429 são tratadas com novas tentativas; os demais erros HTTP e falhas de conexão são propagados para a API do NEXUS.

### Camada Inicial de Resiliência Implementada
O comportamento implementado em `app/pncp/client.py` é:
* **Intervalo entre páginas:** pausa de 1 segundo entre páginas sucessivas.
* **Tentativas para HTTP 429:** até 5 tentativas no total, incluindo a primeira requisição. Portanto, após a resposta inicial, podem ocorrer até 4 novas tentativas.
* **`Retry-After`:** aceita segundos inteiros (delta-seconds) ou uma data HTTP. Valores ausentes ou inválidos usam espera exponencial (`2`, `4`, `8` e `16` segundos nas tentativas que ainda podem ser repetidas). Datas passadas resultam em espera zero. Esperas solicitadas acima de 60 segundos causam falha imediata.
* **Outras falhas:** timeouts, erros de conexão e status HTTP diferentes de 429 não são repetidos pelo cliente.

> A consulta é síncrona e depende da disponibilidade e do tempo de resposta do PNCP. Persistência local e coleta desacoplada permanecem no roadmap.

---

## 📂 Estrutura de Arquivos do Repositório

```text
nexus/
├── app/
│   ├── core/
│   │   ├── config.py          # vazio; reservado
│   │   └── logger.py          # vazio; reservado
│   ├── database/
│   │   ├── __init__.py        # vazio
│   │   ├── connection.py      # vazio; sem conexão ativa ao PostgreSQL
│   │   └── models.py          # vazio; sem modelos persistentes
│   ├── pncp/
│   │   ├── client.py         # Cliente HTTP, paginação e políticas de retry/backoff
│   │   └── parser.py         # Normalização do payload JSON do PNCP
│   ├── repositories/
│   │   └── licitacao_repository.py  # vazio; repositório não implementado
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
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md                 # Documentação do projeto
```

Não há diretório de testes versionado neste momento. Os módulos `app/core`, `app/database` e `app/repositories` listados como vazios ainda não participam do fluxo executado.

---

## 🚀 Como Executar o Projeto Localmente

### Pré-requisitos
* **Python 3.10+** instalado
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

4. **Iniciar o servidor Backend (FastAPI + Uvicorn):**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

5. **Acessar a aplicação:**
   * **Interface Web (Frontend):** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Documentação Interativa (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

O comando de inicialização pressupõe que as dependências foram instaladas no ambiente virtual. Não há uma suíte de testes automatizados configurada no repositório; portanto, ainda não existe um comando de testes validado para documentar.

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
  - [x] Tentativas limitadas e espera exponencial para respostas HTTP 429.
  - [x] Endpoint FastAPI e Painel Frontend com estilização operacional.
- [ ] **Fase 2 — Implementação do PostgreSQL & Modelagem de Dados** *(Prioridade Atual)*
  - [ ] Mapeamento rigoroso do schema do JSON completo da API do PNCP.
  - [ ] Modelagem relacional e definição de chaves únicas de negócio para evitar duplicidades.
  - [ ] Implementação da camada de persistência com suporte a operação *Upsert*.
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
