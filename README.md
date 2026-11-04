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
- Deduplicação pela chave de negócio `numeroControlePNCP`.
- Preservação dos payloads originais em JSON.
- Controle de histórico de sincronizações.
- Hash SHA-256 para identificação de alterações.
- Transações para garantir a consistência das operações.
- Persistência de checkpoints por página processada.

### Paginação e limite de taxa

O cliente percorre as páginas utilizando o campo `totalPaginas` retornado pelo PNCP, processando e persistindo uma página por vez.

Os limites de processamento são configurados por consulta:

- Até 110 páginas por consulta.
- Até 160 páginas para São Paulo (SP).
- Prazo total configurado de 300 segundos por execução.

Cada página processada tem seus registros e checkpoint confirmados na mesma transação, permitindo identificar com precisão o progresso persistido.

Em caso de falha após a confirmação de páginas anteriores, a execução é registrada