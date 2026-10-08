# NEXUS — Plataforma de Inteligência e Gestão de Licitações Públicas

![Status do Projeto](https://img.shields.io/badge/status-em_desenvolvimento-orange)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)
![License](https://img.shields.io/badge/license-MIT-green)

O **NEXUS** é uma solução de inteligência e gestão para oportunidades em licitações públicas, concebida para atender às necessidades operacionais reais da **RCCS Licitações**. A plataforma centraliza dados do **Portal Nacional de Contratações Públicas (PNCP)**, otimizando desde a fase de captação de oportunidades até o acompanhamento do ciclo pós-contratação.

Além de sua aplicação prática no mercado, o NEXUS é um projeto de portfólio focado nas disciplinas de **Desenvolvimento Backend**, **Engenharia de Dados**, **Resiliência de Integração** e **Arquitetura de Software**.

---

## 📌 Visão Geral e Problema de Negócio

A identificação de oportunidades no mercado público costuma exigir pesquisas manuais frequentes, descentralizadas e sujeitas a perda de prazos. Após a homologação da licitação, surge um segundo desafio operacional: o controle de Atas de Registro de Preços, saldo de quantitativos, vigências e reajustes contratuais.

O **NEXUS** foi idealizado para resolver essas duas dores em um único ecossistema:

1. **Busca e Inteligência de Oportunidades:** Localização e filtragem ágil de editais por estado (UF), palavra-chave/produto, modalidade e prazos de encerramento.
2. **Gestão Pós-Contratação:** Acompanhamento contínuo do ciclo de vida dos contratos e atas, garantindo controle sobre saldos disponíveis, vencimentos e renovações.

---

## 🎯 Status Atual do Projeto

Atualmente, o projeto encontra-se na **Fase 1 (Consolidação da Coleta e API REST)**. O sistema já realiza consultas diretas à API de propostas do PNCP, normaliza a estrutura dos dados recebidos, aplica filtros de negócio e expõe esses resultados por meio de uma API REST construída em FastAPI com um painel frontend inicial.

---

## 🛠️ Tecnologias Utilizadas e Planejadas

### Já Utilizadas na Implementação Atual
* **Linguagem:** Python
* **Framework Web:** FastAPI (com uvicorn)
* **Requisições HTTP & Integração:** Requests
* **Interface & Frontend:** HTML5, CSS3, JavaScript (Vanilla ES6)
* **Ferramentas de Desenvolvimento & SO:** Git, GitHub, Linux, DBeaver
* **Formato de Dados:** JSON / REST

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

### 2. Arquitetura-Alvo (Ingestão Assíncrona & Data Pipeline)
Para evitar lentidão e dependência excessiva das taxas de limite da API externa, a arquitetura está migrando para um modelo desacoplado:

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

### Tratamento de Paginação e Desafio de Rate Limit
Durante o desenvolvimento da rotina de paginação (que consolida os registros retornados pela API em uma lista única utilizando `extend()`), identificou-se que consultas extensas (ex: 30+ páginas) disparavam respostas **HTTP 429 (Too Many Requests)** a partir da 10ª página.

### Camada Inicial de Resiliência Implementada
Para contornar o limite de taxa do servidor de origem, foi implementada uma política de resiliência em `app/pncp/client.py`:
* **Intervalo programado:** Pausas entre as requisições de páginas sucessivas.
* **Detecção de Retry-After:** Leitura dos cabeçalhos HTTP para respeitar o tempo de espera solicitado pelo PNCP.
* **Exponential Backoff:** Em respostas 429 sem o cabeçalho `Retry-After`, o código realiza retries progressivos utilizando a fórmula de tempo $2^{\text{tentativa}}$.
* **Limite de Tentativas:** Limite máximo de 5 retries antes de registrar a falha.

> ⚠️ **Nota de Engenharia:** Essa estratégia representa uma **primeira camada de resiliência** para mitigar falhas transitórias. Nos testes sob alto volume, ainda foram observadas lentidões e picos de HTTP 429. Esse comportamento motivou a decisão arquitetural prioritária de migrar para armazenamento persistente em PostgreSQL, eliminando consultas síncronas exaustivas à API externa.

---

## 📂 Estrutura de Arquivos do Repositório

```text
nexus/
├── app/
│   ├── pncp/
│   │   ├── client.py         # Cliente HTTP, paginação e políticas de retry/backoff
│   │   └── parser.py         # Normalização do payload JSON do PNCP
│   ├── services/
│   │   └── licitacao_service.py  # Regras de negócio e filtragem
│   └── main.py               # Inicialização da aplicação FastAPI e rotas REST
├── frontend/
│   ├── index.html            # Estrutura do painel de controle
│   ├── style.css             # Estilização (design escuro / estética operacional)
│   ├── variables.css         # Variáveis de temas e paleta de cores (#ee6018, #a0ca92)
│   ├── app.js                # Lógica de consumo da API do NEXUS no frontend
│   └── assets/               # Recursos visuais estáticos
├── .gitignore
├── requirements.txt          # Dependências do projeto Python
└── README.md                 # Documentação do projeto
```

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
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Iniciar o servidor Backend (FastAPI + Uvicorn):**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

5. **Acessar a aplicação:**
   * **Interface Web (Frontend):** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Documentação Interativa (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📡 Endpoints da API

### `GET /api/licitacoes`
Realiza a consulta de oportunidades vigentes no PNCP aplicadas aos filtros locais.

#### Parâmetros da Requisição (Query Params)
| Parâmetro | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `uf` | `string` | **Sim** | Sigla da Unidade Federativa com 2 caracteres (Ex: `RJ`, `SP`). |
| `produto` | `string` | Não | Termo para busca textual no objeto da licitação (Ex: `material`, `software`). |

#### Exemplo de Chamada
```bash
curl -X GET "http://127.0.0.1:8000/api/licitacoes?uf=RJ&produto=material"
```

#### Exemplo de Resposta (`200 OK`)
```json
{
  "uf": "RJ",
  "termo_pesquisado": "material",
  "total_consultados": 150,
  "total_filtrados": 12,
  "licitacoes": [
    {
      "numero_compra": "00001/2026",
      "descricao": "Aquisição de material de expediente...",
      "codigo_unidade": "123456",
      "municipio": "Rio de Janeiro",
      "uf": "RJ",
      "data_encerramento": "2026-10-15T23:59:59"
    }
  ]
}
```

---

## 🗺️ Roadmap de Desenvolvimento

O desenvolvimento do NEXUS é estruturado de forma iterativa e incremental:

- [x] **Fase 1 — Consolidação da Coleta e API REST**
  - [x] Integração funcional com a API do PNCP.
  - [x] Normalização de payload em DTOs internos (`parser.py`).
  - [x] Implementação de Rate Limiting e Exponential Backoff para erros 429.
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

Este projeto está sob a licença [MIT](LICENSE).

---

**Desenvolvido por Gabriel Draco**  
*Engenharia de Software & Data Engineering* — [GitHub](https://github.com/gdracojj)