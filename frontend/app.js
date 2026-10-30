import {buscar} from './api.js';
import {classificar,BUCKETS,diaKey,rotuloDia,dataCompleta,parsePrazo,horaCurta,restante} from './prazo.js';

const UFS='AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(' ');
const S={items:[],total:0,sync:null,status:'idle',erro:null,f:{produto:'',uf:''},modo:'timeline',periodo:'tudo',pag:1,ctl:null};
const $=s=>document.querySelector(s),main=$('#main');
const h=(t,a={},...c)=>{const e=document.createElement(t);for(const[k,v]of Object.entries(a)){if(k==='class')e.className=v;else if(k.startsWith('on'))e.addEventListener(k.slice(2),v);else if(v!==false&&v!=null)e.setAttribute(k,v===true?'':v)}e.append(...c.flat().filter(x=>x!=null&&x!==false));return e};
const brl=v=>v==null||isNaN(+v)?'Não informado':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(+v);
const ICON={urgente:'▲ ',atencao:'● ',encerrado:'✕ ',normal:'',sem:'? '};
const cls=i=>({...i,c:classificar(i.prazo)});

async function carregar(){
  S.ctl?.abort();S.ctl=new AbortController();S.status='loading';S.pag=1;render();
  try{const r=await buscar(S.f,S.ctl.signal);Object.assign(S,{items:r.items.map(cls),total:r.total,sync:r.sync,status:'ok',erro:null})}
  catch(e){if(e.name==='AbortError')return;S.status='erro';S.erro=e}
  render();
}
const ordenar=l=>[...l].sort((a,b)=>{const r=x=>x.c.estado==='encerrado'?2:x.c.date?0:1;return r(a)-r(b)||(r(a)===2?b.c.date-a.c.date:(a.c.date??0)-(b.c.date??0))});
const noPeriodo=i=>S.periodo==='tudo'||(i.c.date&&i.c.ms>0&&i.c.ms<=S.periodo*864e5);
const visiveis=()=>ordenar(S.items.filter(noPeriodo));

const countdown=i=>h('div',{class:'cd '+i.c.estado},ICON[i.c.estado],i.c.label);
const tm=i=>{const c=i.c,p=parsePrazo(i.prazo);return h('div',{class:'tm '+c.estado},c.date&&h('small',{},rotuloDia(c.date)),h('b',{},c.date&&!p.semHora?horaCurta(c.date):'—'),h('span',{},c.estado==='encerrado'?'✕ Encerrado':c.date?ICON[c.estado]+'em '+restante(c.ms):c.label))};
const card=i=>h('button',{class:'card '+i.c.estado,type:'button',onclick:()=>abrir(i)},tm(i),
  h('div',{class:'bd'},h('div',{class:'t'},i.objeto||'Objeto não informado'),
  h('div',{class:'s'},[i.orgao||i.unidade,i.uf,i.valor!=null&&brl(i.valor)].filter(Boolean).join(' · ')||'Sem detalhes de órgão')));
function abrir(i){
  const d=$('#drawer');d.replaceChildren(
    h('h2',{id:'drawer-t'},i.id||'Licitação'),h('p',{},i.objeto||'Objeto não informado'),countdown(i),
    h('dl',{},...[['Prazo de propostas',i.c.date?dataCompleta(i.c.date):'Não informado'],['Órgão',i.orgao],['Unidade',i.unidade],['Município / UF',[i.municipio,i.uf].filter(Boolean).join(' / ')],['Modalidade',i.modalidade],['Valor estimado',brl(i.valor)]]
      .flatMap(([k,v])=>[h('dt',{},k),h('dd',{},v||'Não informado')])),
    i.link?h('p',{},h('a',{href:i.link,target:'_blank',rel:'noopener noreferrer'},'Abrir no PNCP')):h('p',{class:'muted'},'Link do PNCP não disponível na API atual.'),
    h('button',{class:'btn',type:'button',onclick:()=>d.close()},'Fechar'));
  d.showModal();
}
const estado=()=>{
  if(S.status==='loading')return h('div',{role:'status'},h('span',{class:'muted'},'Consultando a base do NEXUS…'),...[1,2,3].map(()=>h('div',{class:'skel'})));
  if(S.status==='erro')return h('div',{class:'notice err',role:'alert'},S.erro.message+' ',h('button',{class:'btn',type:'button',onclick:carregar},'Tentar novamente'));
  if(!S.items.length)return h('div',{class:'empty'},(S.f.produto||S.f.uf)?'Nenhuma licitação para estes filtros. Remova um filtro ou tente outro termo.':'A base ainda não tem licitações coletadas. Execute a sincronização com o PNCP.');
  return null;
};
const aviso=()=>h('div',{class:'muted'},`${S.items.length} licitações carregadas${S.total>S.items.length?` de ${S.total}`:''}. O painel mostra apenas a base coletada pelo NEXUS, não todas as contratações do PNCP. `,S.sync?`Última sincronização: ${dataCompleta(new Date(S.sync))}.`:'Última sincronização: não informada pela API atual.');

function timeline(l){
  const g=new Map();for(const i of l){const k=i.c.estado==='encerrado'?'enc':i.c.date?diaKey(i.c.date):'sem';(g.get(k)||g.set(k,[]).get(k)).push(i)}
  const rank=k=>k==='enc'?2:k==='sem'?1:0;
  const ks=[...g.keys()].sort((a,b)=>rank(a)-rank(b)||(a<b?-1:1));
  return h('div',{class:'tl'},ks.map(k=>{const it=g.get(k);const t=k==='enc'?'Encerradas':k==='sem'?'Sem prazo informado':rotuloDia(it[0].c.date);
    return h('section',{},h('div',{class:'day'},h('h3',{class:'dh'},t),h('span',{class:'muted'},`${it.length}`)),h('div',{class:'list'},it.map(card)))}));
}
const quadro=l=>h('div',{class:'board'},BUCKETS.map(([k,nome])=>{const it=l.filter(i=>i.c.bucket===k);
  return h('section',{class:'col '+({hoje:'urgente',amanha:'atencao'}[k]||''),'aria-label':nome},h('h3',{},nome,h('span',{class:'mono muted'},it.length)),h('div',{class:'list'},it.slice(0,50).map(card),it.length>50&&h('div',{class:'muted'},`+${it.length-50} na tabela`)))}));
function tabela(l){
  const n=25,pg=Math.min(S.pag,Math.ceil(l.length/n)||1),fat=l.slice((pg-1)*n,pg*n);
  const linhas=fat.map(i=>h('tr',{},
    h('td',{},countdown(i)),
    h('td',{},
      h('button',{type:'button',onclick:()=>abrir(i)},(i.objeto||'Objeto não informado').slice(0,140)),
      h('div',{class:'muted mono'},i.id||'')),
    h('td',{},i.orgao||i.unidade||'—'),
    h('td',{},i.uf||'—'),
    h('td',{class:'mono'},brl(i.valor))));
  const tabela=h('table',{},
    h('caption',{class:'muted',style:'text-align:left;padding:4px 10px'},'Licitações ordenadas por prazo de propostas'),
    h('thead',{},h('tr',{},['Prazo','Licitação','Órgão / unidade','UF','Valor'].map(x=>h('th',{scope:'col'},x)))),
    h('tbody',{},linhas));
  const paginacao=h('div',{class:'pg'},
    h('button',{class:'btn',type:'button',disabled:pg<=1,onclick:()=>{S.pag=pg-1;render()}},'Anterior'),
    h('span',{class:'muted'},`Página ${pg} de ${Math.ceil(l.length/n)||1}`),
    h('button',{class:'btn',type:'button',disabled:pg*n>=l.length,onclick:()=>{S.pag=pg+1;render()}},'Próxima'));
  return h('div',{},h('div',{class:'tw'},tabela),paginacao);
}

function geral(){
  const c=k=>S.items.filter(i=>i.c.bucket===k).length,prox=ordenar(S.items).filter(i=>i.c.ms>0).slice(0,8);
  const por={};S.items.forEach(i=>{if(i.uf)por[i.uf]=(por[i.uf]||0)+1});const top=Object.entries(por).sort((a,b)=>b[1]-a[1]).slice(0,8),max=top[0]?.[1]||1;
  const e=estado(),nx=prox[0],hero=nx&&h('button',{class:'hero '+nx.c.estado,type:'button',onclick:()=>abrir(nx)},h('span',{class:'muted'},'Próximo prazo de propostas'),h('b',{class:'mono'},restante(nx.c.ms)),h('span',{},nx.objeto||'Objeto não informado'),h('span',{class:'muted'},[nx.orgao||nx.unidade,nx.uf].filter(Boolean).join(' · ')));
  const metricas=[
    ['Licitações carregadas',S.items.length],
    ['Prazo hoje',c('hoje')],
    ['Em até 3 dias',c('hoje')+c('amanha')+c('tres')],
    ['Sem prazo informado',c('semdata')],
  ].map(([nome,valor])=>h('div',{},h('b',{},S.status==='ok'?valor:'—'),h('span',{},nome)));
  const painelPrazos=h('div',{class:'panel'},
    h('h2',{},'Próximos prazos'),
    h('div',{class:'list'},prox.length?prox.map(card):h('div',{class:'muted'},'Nenhum prazo futuro nos resultados carregados.')),
    h('p',{},h('a',{href:'#/licitacoes'},'Ver todas as licitações')));
  const painelUf=h('div',{class:'panel'},
    h('h2',{},'Distribuição por UF'),
    top.map(([uf,quantidade])=>h('div',{class:'uf'},
      h('span',{class:'mono'},uf),
      h('i',{style:`width:${quantidade/max*100}%`}),
      h('span',{class:'mono muted'},quantidade))));
  const conteudo=e||h('div',{class:'cols'},painelPrazos,painelUf);
  return h('div',{},h('h1',{},'Visão geral'),aviso(),h('div',{class:'metrics'},metricas),
    S.status==='ok'&&hero,conteudo);
}
function licitacoes(){
  const form=h('form',{class:'filters',onsubmit:ev=>{ev.preventDefault();S.f={produto:ev.target.produto.value.trim().slice(0,100),uf:ev.target.uf.value};carregar()}},
    h('label',{class:'grow'},'Produto ou palavra-chave',h('input',{name:'produto',type:'search',value:S.f.produto,maxlength:100})),
    h('label',{},'UF',h('select',{name:'uf'},h('option',{value:''},'Todas'),UFS.map(u=>h('option',{value:u,selected:u===S.f.uf},u)))),
    h('button',{class:'btn pri',type:'submit'},'Aplicar'),
    h('button',{class:'btn',type:'button',onclick:()=>{S.f={produto:'',uf:''};carregar()}},'Limpar'));
  const seg=(lista,atual,fn,rot)=>h('div',{class:'seg',role:'group','aria-label':rot},lista.map(([v,n])=>h('button',{class:'btn',type:'button','aria-pressed':String(v===atual),onclick:()=>fn(v)},n)));
  const chips=[S.f.produto&&`Produto: ${S.f.produto}`,S.f.uf&&`UF: ${S.f.uf}`].filter(Boolean);
  const e=estado(),l=visiveis(),oculto=S.items.length-l.length;
  return h('div',{},h('h1',{},'Licitações'),form,
    chips.length>0&&h('div',{class:'chips'},chips.map(c=>h('span',{class:'chip'},c))),
    h('div',{class:'bar'},seg([['tabela','Tabela'],['timeline','Timeline'],['quadro','Quadro']],S.modo,v=>{S.modo=v;render()},'Visualização'),
      seg([[7,'7 dias'],[15,'15 dias'],[30,'30 dias'],['tudo','Todos']],S.periodo,v=>{S.periodo=v;S.pag=1;render()},'Período do prazo')),
    aviso(),S.periodo!=='tudo'&&oculto>0&&h('div',{class:'notice'},`${oculto} licitações fora do período (incluindo encerradas e sem prazo) estão ocultas.`),
    e||(!l.length?h('div',{class:'empty'},'Nenhuma licitação com prazo neste período. Escolha "Todos".'):{timeline,quadro,tabela}[S.modo](l)));
}

function render(){
  const rota=location.hash.replace('#/','')||'geral',r=rota==='licitacoes'?'licitacoes':'geral';
  document.querySelectorAll('[data-route]').forEach(a=>a.dataset.route===r?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current'));
  const foco=document.activeElement?.name,y=scrollY;
  main.setAttribute('aria-busy',S.status==='loading');main.replaceChildren(r==='geral'?geral():licitacoes());
  if(foco){const el=main.querySelector(`[name=${foco}]`);el?.focus()}scrollTo(0,y);
}
const tema=$('#tema'),syncTema=()=>{const d=document.documentElement.dataset.theme==='dark';tema.textContent=d?'Tema escuro':'Tema claro';tema.setAttribute('aria-pressed',String(d))};
tema.onclick=()=>{const t=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=t;try{localStorage.setItem('nexus-tema',t)}catch(e){}syncTema()};
addEventListener('hashchange',()=>{render();main.focus()});syncTema();
setInterval(()=>{if(S.status==='ok'&&!$('#drawer').open&&document.activeElement?.tagName!=='INPUT'){S.items=S.items.map(cls);render()}},60000);
carregar();
