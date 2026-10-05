const UFS = [
  "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
  "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
];

const form = document.getElementById("filtro");
const selectUf = document.getElementById("uf");
const inputProduto = document.getElementById("produto");
const botao = document.getElementById("buscar");
const statusEl = document.getElementById("status");
const kpis = document.getElementById("kpis");
const painel = document.getElementById("painel");

UFS.forEach((uf) => selectUf.add(new Option(uf, uf)));

const fmt = new Intl.NumberFormat("pt-BR");

function setStatus(texto, erro = false) {
  statusEl.textContent = texto;
  statusEl.classList.toggle("erro", erro);
}

function celula(texto, classe) {
  const td = document.createElement("td");
  if (classe) td.className = classe;
  td.textContent = texto ?? "";
  return td;
}

function renderKpis(dados) {
  const municipios = new Set(dados.resultados.map((l) => (l.municipio || "Não informado")));
  const unidades = new Set(dados.resultados.map((l) => l.codigo_unidade));

  document.getElementById("k-total").textContent = fmt.format(dados.total);
  document.getElementById("k-consultado").textContent = fmt.format(dados.total_consultado);
  document.getElementById("k-municipios").textContent = fmt.format(municipios.size);
  document.getElementById("k-unidades").textContent = fmt.format(unidades.size);
}

function renderBarras(resultados) {
  const contagem = {};
  resultados.forEach((l) => {
    const m = l.municipio || "Não informado";
    contagem[m] = (contagem[m] || 0) + 1;
  });

  const top = Object.entries(contagem)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const maximo = top.length ? top[0][1] : 1;

  const lista = document.getElementById("barras");
  lista.replaceChildren();

  top.forEach(([municipio, qtd]) => {
    const li = document.createElement("li");

    const rotulo = document.createElement("div");
    rotulo.className = "rotulo";
    const nome = document.createElement("span");
    nome.textContent = municipio;
    const valor = document.createElement("span");
    valor.textContent = qtd;
    rotulo.append(nome, valor);

    const trilho = document.createElement("div");
    trilho.className = "trilho";
    const barra = document.createElement("div");
    barra.className = "preenchido";
    barra.style.width = `${(qtd / maximo) * 100}%`;
    trilho.append(barra);

    li.append(rotulo, trilho);
    lista.append(li);
  });
}

function renderTabela(resultados) {
  const corpo = document.getElementById("linhas");
  corpo.replaceChildren();

  resultados.forEach((l) => {
    const tr = document.createElement("tr");
    tr.append(celula(l.numero, "num"), celula(l.descricao, "desc"), celula((l.municipio || "Não informado")));

    const tdUf = document.createElement("td");
    const tag = document.createElement("span");
    tag.className = "uf-tag";
    tag.textContent = l.uf;
    tdUf.append(tag);
    tr.append(tdUf, celula(l.codigo_unidade));

    corpo.append(tr);
  });
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const uf = selectUf.value;
  const produto = inputProduto.value.trim();
  if (!uf) return setStatus("Selecione um estado para buscar.", true);

  botao.disabled = true;
  setStatus("Consultando o PNCP…");
  kpis.hidden = true;
  painel.hidden = true;

  try {
    const params = new URLSearchParams({ uf, produto });
    const resp = await fetch(`/api/licitacoes?${params}`);
    const dados = await resp.json();

    if (!resp.ok) throw new Error(dados.detail || "Erro ao buscar licitações.");

    if (dados.total === 0) {
      setStatus(
        produto
          ? `Nenhuma licitação em ${uf} com "${produto}". Tente outro termo.`
          : `Nenhuma licitação encontrada em ${uf}.`
      );
      return;
    }

    renderKpis(dados);
    renderBarras(dados.resultados);
    renderTabela(dados.resultados);
    kpis.hidden = false;
    painel.hidden = false;
    setStatus(`${fmt.format(dados.total)} licitações em ${uf}${produto ? ` para "${produto}"` : ""}.`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    botao.disabled = false;
  }
});

/* Tema claro / escuro */
const botaoTema = document.getElementById("tema");

botaoTema.addEventListener("click", () => {
  const raiz = document.documentElement;
  const proximo = raiz.dataset.theme === "dark" ? "light" : "dark";
  raiz.dataset.theme = proximo;
  try {
    localStorage.setItem("nexus-theme", proximo);
  } catch (e) {}
});