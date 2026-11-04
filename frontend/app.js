import {buscar} from './api.js';
import {prepararPrazo,BUCKETS,diaKey,rotuloDia,dataCompleta,parsePrazo,horaCurta} from './prazo.js';

const UFS='AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(' ');
const S={items:[],total:0,totalConsultado:0,totalPages:0,page:1,pageSize:25,sync:null,status:'idle',erro:null,f:{produto:'',uf:''},modo:'timeline',periodo:'tudo',ctl:null,expanded:{},animarView:false};
const $=s=>document.querySelector(s),main=$('#main');let liveTimer=null;
const h=(t,a={},...c)=>{const e=document.createElement(t);for(const[k,v]of Object.entries(a)){if(k==='class')e.className=v;else if(k.startsWith('on'))e.addEventListener(k.slice(2),v);else if(v!==false&&v!=null)e.setAttribute(k,v===true?'':v)}e.append(...c.flat().filter(x=>x!=null&&x!==false));return e};
const brl=v=>v==null||isNaN(+v)?'Não informado':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(+v);
const STATUS={vermelho:'status-red',roxo:'status-purple',azul:'status-blue',verde:'status-green',cinza:'status-muted',encerrado:'status-muted',sem:'status-muted'};
const STATUS_TEXT={vermelho:'Encerra em breve',roxo:'Prazo intermediário',azul:'Ainda há tempo',verde:'Contratada',encerrado:'Encerrada',sem:'Sem prazo informado'};
const cls=i=>({...i,c:prepararPrazo(i)});

async function carregar({reset=true}={}){
  if(reset)S.page=1;
  S.ctl?.abort();S.ctl=new AbortController();S.status='loading';render();
  const rota=location.hash.replace('#/','')||'geral';
  const prazoDias=rota==='licitacoes'&&S.periodo!=='tudo'?Number(S.periodo):null;
  try{const r=await buscar({...S.f,page:S.page,pageSize:S.pageSize,prazoDias},S.ctl.signal);Object.assign(S,{items:r.items.map(cls),total:r.total,totalConsultado:r.totalConsultado,totalPages:r.totalPages,page:r.page,pageSize:r.pageSize,sync:r.sync,status:'ok',erro:null})}
  catch(e){if(e.name==='AbortError')return;S.status='erro';S.erro=e}
  render();
}
const ordenar=l=>[...l].sort((a,b)=>{const da=a.c.date?.getTime()??Infinity,db=b.c.date?.getTime()??Infinity;return da-db});
const visiveis=()=>ordenar(S.items);
const fmtRestante=ms=>{const m=Math.max(0,Math.floor(ms/60000)),d=Math.floor(m/1440),h=Math.floor((m%1440)/60),r=m%60;return d?`${d} d ${h} h`:h?`${h} h ${r} min`:`${r} min`};
const horaPrazo=i=>i.c.date?horaCurta(i.c.date):'—';
const prazoPill=i=>h('span',{class:`deadline-pill ${STATUS[i.c.estado]||'status-muted'}`},`${horaPrazo(i)} · ${i.c.estado==='encerrado'?'encerrada':i.c.date?`em ${fmtRestante(i.c.ms)}`:'sem prazo'}`);
const countdown=i=>h('div',{class:`cd ${STATUS[i.c.estado]||''}`},STATUS_TEXT[i.c.estado]||STATUS_TEXT.sem, i.c.date&&` · ${fmtRestante(i.c.ms)}`);
function abrir(i){
  const d=$('#drawer');d.replaceChildren(
    h('h2',{id:'drawer-t'},i.id||'Licitação'),h('p',{},i.objeto||'Objeto não informado'),countdown(i),
    h('dl',{},...[['Prazo de propostas',i.c.date?dataCompleta(i.c.date):'Não informado'],['Órgão',i.orgao],['Unidade',i.unidade],['Município / UF',[i.municipio,i.uf].filter(Boolean).join(' / ')],['Modalidade',i.modalidade],['Situação',i.situacao],['Valor estimado',brl(i.valor)]]
      .flatMap(([k,v])=>[h('dt',{},k),h('dd',{},v||'Não informado')])),
    i.link?h('p',{},h('a',{href:i.link,target:'_blank',rel:'noopener noreferrer'},'Abrir no PNCP')):h('p',{class:'muted'},'Link do PNCP não disponível na API atual.'),
    h('button',{class:'btn',type:'button',onclick:()=>d.close()},'Fechar'));
  d.showModal();
}
const estado=()=>{
  if(S.status==='loading')return h('div',{role:'status'},h('span',{class:'muted'},'Consultando a base do NEXUS…'),...[1,2,3].map(()=>h('div',{class:'skel'})));
  if(S.status==='erro')return h('div',{class:'notice err',role:'alert'},S.erro.message+' ',h('button',{class:'btn',type:'button',onclick:()=>carregar({reset:false})},'Tentar novamente'));
  if(!S.items.length){const periodoAtivo=S.periodo!=='tudo';const mensagem=S.total>0?'Não há resultados nesta página. Volte à página anterior.':(S.f.produto||S.f.uf||periodoAtivo)?'Nenhuma licitação para estes filtros. Ajuste o termo, a UF ou o período.':S.sync?'Não há oportunidades vigentes na base coletada.':'A base ainda não tem licitações coletadas. Execute a sincronização com o PNCP.';return h('div',{class:'empty'},mensagem)}
  return null;
};
const aviso=()=>{const inicio=S.total?(S.page-1)*S.pageSize+1:0,fim=Math.min(S.page*S.pageSize,S.total);const faixa=S.total?`Exibindo ${inicio}–${fim} de ${S.total} licitações. `:'Nenhuma licitação corresponde à consulta. ';return h('div',{class:'muted notice-line'},`${faixa}Base coletada pelo NEXUS, não todas as contratações do PNCP. `,S.sync?`Última sincronização: ${dataCompleta(new Date(S.sync))}.`:'Última sincronização não informada.')};
const paginacao=()=>S.totalPages>1&&h('div',{class:'pg','aria-label':'Paginação das licitações'},h('button',{class:'btn',type:'button',disabled:S.page<=1,onclick:()=>{S.page--;carregar({reset:false})}},'Anterior'),h('span',{class:'muted',role:'status'},`Página ${S.page} de ${S.totalPages}`),h('button',{class:'btn',type:'button',disabled:S.page>=S.totalPages,onclick:()=>{S.page++;carregar({reset:false})}},'Próxima'));

const metadata=i=>[i.orgao||i.unidade,i.uf,i.valor!=null?brl(i.valor):null].filter(Boolean).join(' · ')||'Sem detalhes de órgão';
const prazoTooltip=i=>[i.objeto,i.orgao,i.uf,brl(i.valor),i.id,i.c.date&&dataCompleta(i.c.date)].filter(Boolean).join(' · ');
const stat=(title,value,klass='')=>h('article',{class:'stat-card'},h('span',{class:'stat-label'},title),h('strong',{class:`stat-value ${klass}`},value));

function eixoHoras(){return S.periodo==='tudo'?72:Number(S.periodo)*24}
function timeline(l){
  const now=new Date(),horizon=eixoHoras(l),horizonMs=horizon*3600000;
  const ticks=[],step=horizon<=72?12:24;for(let n=0;n<=horizon;n+=step)ticks.push({n,label:n===0?'Agora':n%24===0?`+${n/24} d`:`+${n} h`});
  const axis=h('div',{class:'timeline-axis'},h('div',{class:'axis-label'},'Licitação'),h('div',{class:'axis-plot'},ticks.map(t=>h('span',{class:'axis-tick',style:`left:${t.n/horizon*100}%`},t.label))));
  const groups=new Map();for(const i of l){const key=i.c.date?diaKey(i.c.date):'semdata';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(i)}
  const rows=[];let rowIndex=0;
  for(const [key,items] of groups){const expanded=Boolean(S.expanded[key]),shown=expanded?items:items.slice(0,8);
    for(const i of shown){const horasRestantes=i.c.date?Math.max(0,i.c.ms/3600000):0;const pct=i.c.date?Math.min(100,Math.max(3,(horasRestantes/72)*100)):0;if(i.c.date)console.log(horasRestantes,pct);const status=STATUS[i.c.estado]||'status-muted',label=i.c.date?`${horaPrazo(i)} · ${fmtRestante(i.c.ms)}`:'Prazo não informado';
      rows.push(h('button',{type:'button',class:'timeline-row',style:`--row-delay:${rowIndex++*30}ms`,title:prazoTooltip(i), 'aria-label':`${i.objeto||'Licitação'}, ${STATUS_TEXT[i.c.estado]||STATUS_TEXT.sem}, prazo ${label}`,onclick:()=>abrir(i)},
        h('span',{class:'timeline-info'},h('span',{class:'timeline-title'},i.objeto||'Objeto não informado'),h('span',{class:'timeline-meta'},metadata(i))),
        h('span',{class:'timeline-plot'},h('span',{class:'now-line','aria-hidden':'true'}),i.c.date&&h('span',{class:`timeline-bar ${status}`,style:`width:${pct}%`,'aria-hidden':'true'}),
          i.c.date?h('span',{class:'timeline-label',style:`left:calc(${pct}% + 14px)`},h('b',{},horaPrazo(i)),` · ${fmtRestante(i.c.ms)}`):h('span',{class:'timeline-label muted'},'Sem prazo'))));
    }
    if(items.length>8){const rest=items.slice(8),dots=rest.map((i,index)=>{const pos=i.c.date?Math.min(100,Math.max(0,(i.c.date-now)/horizonMs*100)):0;return h('i',{class:`overflow-dot ${STATUS[i.c.estado]||'status-muted'}`,style:`left:${pos}%;opacity:${Math.max(.15,.75-index*.03)}`,'aria-hidden':'true'})});
      rows.push(h('div',{class:'timeline-overflow'},h('span',{class:'timeline-info'},h('button',{class:'expand-group',type:'button',onclick:()=>{S.expanded[key]=!expanded;render()}},expanded?'Mostrar menos':`+ ${rest.length} outras ${key==='semdata'?'sem prazo':`com prazo em ${rotuloDia(items[0].c.date)}`}`)),h('span',{class:'timeline-plot'},h('span',{class:'now-line','aria-hidden':'true'}),dots)));
    }
  }
  return h('section',{class:'timeline-panel panel', 'aria-label':'Timeline de prazos'},
    h('div',{class:'legend',role:'list','aria-label':'Legenda de urgência'},['vermelho','roxo','azul','verde'].map(k=>h('span',{class:`legend-item ${STATUS[k]}`,role:'listitem'},h('i',{}),STATUS_TEXT[k]))),
    axis,h('div',{class:'timeline-rows'},rows));
}

function quadro(l){const columns=BUCKETS.filter(([key])=>key!=='semdata').concat([['semdata','Sem prazo informado']]);return h('div',{class:'board'},columns.map(([key,name])=>{const items=l.filter(i=>i.c.bucket===key),tone=STATUS[items.find(i=>i.corQuadro==='verde')?'verde':items[0]?.corQuadro]||'status-muted';
    return h('section',{class:'col','aria-label':`${name}, ${items.length} licitações`},h('h3',{},name,h('span',{class:`count-pill ${tone}`},items.length)),items.length?h('div',{class:'board-list'},items.slice(0,50).map(i=>{const color=STATUS[i.corQuadro]||'status-muted';return h('button',{class:'board-card',type:'button',title:prazoTooltip(i),'aria-label':`${i.objeto||'Licitação'}, ${STATUS_TEXT[i.c.estado]||STATUS_TEXT.sem}, prazo ${horaPrazo(i)}`,onclick:()=>abrir(i)},h('div',{class:'board-time'},h('strong',{},horaPrazo(i)),h('i',{class:`status-dot ${color}`,'aria-hidden':'true'})),h('div',{class:'board-object'},i.objeto||'Objeto não informado'),h('div',{class:'board-meta'},metadata(i)),i.c.estado==='verde'&&h('span',{class:'contracted-label'},'Contratada'),h('span',{class:`board-progress ${color}`}))})):h('div',{class:'empty-column'},'Nada por aqui'),items.length>50&&h('p',{class:'muted'},`+ ${items.length-50} na tabela`));}));}

function tabela(l){const rows=l.map(i=>h('tr',{},h('td',{},prazoPill(i)),h('td',{},h('button',{type:'button',onclick:()=>abrir(i)},i.objeto||'Objeto não informado'),h('div',{class:'sub-id'},i.id||'Número PNCP não informado')),h('td',{},i.orgao||i.unidade||'—'),h('td',{class:'numeric'},i.uf||'—'),h('td',{class:'numeric value'},brl(i.valor))));return h('div',{class:'table-card panel'},h('div',{class:'tw'},h('table',{},h('caption',{},'Licitações ordenadas por prazo de propostas'),h('thead',{},h('tr',{},['Prazo','Licitação','Órgão / unidade','UF','Valor'].map(x=>h('th',{scope:'col'},x)))),h('tbody',{},rows))))}

function geral(){const c=k=>S.items.filter(i=>i.c.bucket===k).length,prox=ordenar(S.items).filter(i=>i.c.ms>0).slice(0,8);const por={};S.items.forEach(i=>{if(i.uf)por[i.uf]=(por[i.uf]||0)+1});const top=Object.entries(por).sort((a,b)=>b[1]-a[1]).slice(0,8),max=top[0]?.[1]||1;const e=estado(),nx=prox[0],hero=nx&&h('button',{class:'hero '+(STATUS[nx.c.estado]||''),type:'button',onclick:()=>abrir(nx)},h('span',{class:'muted'},'Próximo prazo de propostas'),h('b',{},fmtRestante(nx.c.ms)),h('span',{},nx.objeto||'Objeto não informado'),h('span',{class:'muted'},metadata(nx)));const metrics=[['Licitações nesta página',S.items.length],['Encerram hoje',c('hoje')],['Encerram amanhã',c('amanha')],['Sem prazo informado',c('semdata')]].map(([name,value])=>h('div',{},h('b',{},S.status==='ok'?value:'—'),h('span',{},name)));const contents=e||h('div',{class:'cols'},h('div',{class:'panel'},h('h2',{},'Próximos prazos nesta página'),h('div',{class:'list'},prox.length?prox.map(i=>h('button',{class:'card',type:'button',onclick:()=>abrir(i)},prazoPill(i),h('span',{class:'bd'},h('span',{class:'t'},i.objeto||'Objeto não informado'),h('span',{class:'s'},metadata(i))))):h('div',{class:'muted'},'Nenhum prazo futuro nos resultados carregados.')),h('p',{},h('a',{href:'#/licitacoes'},'Ver todas as licitações'))),h('div',{class:'panel'},h('h2',{},'Distribuição por UF nesta página'),top.map(([uf,n])=>h('div',{class:'uf'},h('b',{class:'numeric'},uf),h('i',{style:`width:${n/max*100}%`}),h('b',{class:'numeric muted'},n)))));return h('div',{},h('h1',{},'Visão geral'),aviso(),h('div',{class:'metrics'},metrics),S.status==='ok'&&hero,contents,paginacao())}

function licitacoes(){const form=h('form',{class:'filters',onsubmit:ev=>{ev.preventDefault();S.f={produto:ev.target.produto.value.trim().slice(0,100),uf:ev.target.uf.value};carregar()}},h('label',{class:'grow'},'Produto ou palavra-chave',h('input',{name:'produto',type:'search',value:S.f.produto,maxlength:100,placeholder:'Ex.: armários, água mineral'})),h('label',{},'UF',h('select',{name:'uf'},h('option',{value:''},'Todas'),UFS.map(u=>h('option',{value:u,selected:u===S.f.uf},u)))),h('button',{class:'btn pri',type:'submit'},'Aplicar'),h('button',{class:'btn ghost',type:'button',onclick:()=>{S.f={produto:'',uf:''};carregar()}},'Limpar'));
  const seg=(list,current,fn,label)=>h('div',{class:'seg',role:'group','aria-label':label},list.map(([v,name])=>h('button',{class:'btn',type:'button','aria-pressed':String(v===current),onclick:()=>fn(v)},name)));
  const chips=[S.f.produto&&`Produto: ${S.f.produto}`,S.f.uf&&`UF: ${S.f.uf}`,S.periodo!=='tudo'&&`Prazo: ${S.periodo} dias`].filter(Boolean),e=estado(),l=visiveis();
  const pgs=l.filter(i=>i.c.bucket==='hoje').length,tom=l.filter(i=>i.c.bucket==='amanha').length,soon=ordenar(l).find(i=>i.c.ms>0);
  const metrics=[stat('Encerram hoje',S.status==='ok'?pgs:'—','status-red-text'),stat('Encerram amanhã',S.status==='ok'?tom:'—','status-purple-text'),stat('Próximo encerramento',S.status==='ok'&&soon?fmtRestante(soon.c.ms):'—',''),stat('Base coletada',S.status==='ok'?new Intl.NumberFormat('pt-BR').format(S.totalConsultado):'—','status-blue-text')];
  const tabs=seg([['tabela','Tabela'],['timeline','Timeline'],['quadro','Quadro']],S.modo,v=>{S.modo=v;S.animarView=true;render()},'Visualização');
  const periods=seg([[7,'7 dias'],[15,'15 dias'],[30,'30 dias'],['tudo','Todos']],S.periodo,v=>{S.periodo=v;carregar()},'Período do prazo');
  const inicio=S.total?(S.page-1)*S.pageSize+1:0,fim=Math.min(S.page*S.pageSize,S.total),sinc=S.sync?dataCompleta(new Date(S.sync)):'Sincronização não informada';
  const titulo=S.modo==='timeline'?'Timeline':S.modo==='quadro'?'Quadro':'Tabela';
  const subtitulo=S.modo==='timeline'?`${S.status==='ok'?new Intl.NumberFormat('pt-BR').format(S.totalConsultado):'—'} licitações na base · última sincronização ${sinc}`:S.modo==='quadro'?'Colunas por proximidade do encerramento':'Licitações ordenadas por prazo de propostas';
  const statusPage=`Exibindo ${inicio}–${fim} de ${S.total} licitações. O painel mostra a base coletada pelo NEXUS, não todas as contratações do PNCP.`;
  const page=h('div',{class:'lic-page'},h('div',{class:'page-heading'},h('div',{},h('h1',{},titulo),h('p',{class:'page-subtitle'},subtitulo)),h('div',{class:'view-controls'},tabs,periods)),form,chips.length&&h('div',{class:'chips'},chips.map(x=>h('span',{class:'chip'},x))),h('div',{class:'metrics timeline-metrics'},metrics),e||(!l.length?h('div',{class:'empty'},'Nenhuma licitação com prazo neste período. Escolha “Todos”.'):{timeline,quadro,tabela}[S.modo](l)),h('p',{class:'page-status muted'},`${statusPage} Última sincronização: ${sinc}.`),paginacao());
  return page;
}

function scheduleLiveUpdates(route){clearInterval(liveTimer);liveTimer=null;if(route!=='licitacoes')return;liveTimer=setInterval(()=>{if(S.status==='ok'&&!$('#drawer').open){S.items=S.items.map(cls);render()}},60000)}
function render(){const route=location.hash.replace('#/','')||'geral',r=route==='licitacoes'?'licitacoes':'geral';document.querySelectorAll('[data-route]').forEach(a=>a.dataset.route===r?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current'));const focus=document.activeElement?.name,y=scrollY;main.setAttribute('aria-busy',S.status==='loading');main.replaceChildren(r==='geral'?geral():licitacoes());if(S.animarView){main.querySelector('.lic-page')?.classList.add('view-enter');S.animarView=false}if(focus){const el=main.querySelector(`[name=${focus}]`);el?.focus()}scrollTo(0,y);scheduleLiveUpdates(r)}
const tema=$('#tema'),syncTema=()=>{const dark=document.documentElement.dataset.theme==='dark';tema.querySelector('.theme-icon').textContent=dark?'☾':'☀';tema.setAttribute('aria-pressed',String(dark));const logo=$('.logo');if(logo)logo.src=dark?'assets/nexus-logo.png':'assets/nexus-logo-light.png';const theme=document.querySelector('meta[name="theme-color"]');if(theme)theme.content=dark?'#09090d':'#f4f4f8'};
tema.onclick=()=>{const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem('nexus-tema',next)}catch(_e){}syncTema()};
addEventListener('hashchange',()=>{carregar();main.focus()});document.addEventListener('visibilitychange',()=>{if(!document.hidden&&S.status==='ok'&&location.hash.includes('licitacoes')){S.items=S.items.map(cls);render()}});syncTema();
carregar();
