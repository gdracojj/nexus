export class ApiError extends Error {
  constructor(kind, msg) {
    super(msg);
    this.kind = kind;
  }
}

const pick=(o,ks)=>{for(const k of ks){const v=k.split('.').reduce((a,p)=>a?.[p],o);if(v!=null&&v!=='')return v}return null};
const http=u=>/^https?:\/\//i.test(u||'')?u:null;

export const normalizar=r=>({
  id:pick(r,['numero_controle_pncp','numeroControlePNCP','numero','id']),
  objeto:pick(r,['descricao','objeto','objetoCompra']),
  orgao:pick(r,['orgao','orgao_nome','orgaoEntidade.razaoSocial']),
  unidade:pick(r,['unidade','unidade_nome','unidadeOrgao.nomeUnidade','codigo_unidade']),
  municipio:pick(r,['municipio','unidadeOrgao.municipioNome']),
  uf:pick(r,['uf','unidadeOrgao.ufSigla']),
  prazo:pick(r,['data_encerramento_proposta','dataEncerramentoProposta']),
  valor:pick(r,['valor_estimado','valorTotalEstimado','valor_total_estimado']),
  modalidade:pick(r,['modalidade','modalidade_nome','codigo_modalidade']),
  link:http(pick(r,['link_pncp','link','url']))
});

export async function buscar(
  {produto='',uf='',page=1,pageSize=25,prazoDias=null},
  signal,
  timeoutMs=15000
){
  const q=new URLSearchParams({page:String(page),page_size:String(pageSize)});
  if(produto)q.set('produto',produto);if(uf)q.set('uf',uf);
  if(prazoDias!=null)q.set('prazo_dias',String(prazoDias));
  const ctl=new AbortController();let timedOut=false;
  const cancelar=()=>ctl.abort();
  signal?.addEventListener('abort',cancelar,{once:true});
  const t=setTimeout(()=>{timedOut=true;ctl.abort()},timeoutMs);
  try{
    const res=await fetch('/api/licitacoes'+(q.size?'?'+q:''),{signal:ctl.signal,headers:{Accept:'application/json'}});
    if(!res.ok)throw new ApiError('http',res.status>=500?'O servidor do NEXUS não respondeu corretamente.':'Os filtros enviados não foram aceitos.');
    if(!(res.headers.get('content-type')||'').includes('json'))throw new ApiError('formato','Resposta inesperada do servidor.');
    const j=await res.json();
    const lista=Array.isArray(j)?j:j?.items??j?.licitacoes??j?.resultados;
    if(!Array.isArray(lista))throw new ApiError('formato','O formato da resposta não corresponde ao esperado.');
    const sync=!Array.isArray(j)?(j.ultima_sincronizacao??j.sincronizacao?.concluida_em??null):null;
    return{
      items:lista.map(normalizar),
      total:j?.total??lista.length,
      page:j?.page??page,
      pageSize:j?.page_size??pageSize,
      totalPages:j?.total_pages??0,
      sync,
      syncRun:!Array.isArray(j)?(j.ultima_execucao??null):null
    };
  }catch(e){
    if(e instanceof ApiError)throw e;
    if(e.name==='AbortError'){if(timedOut)throw new ApiError('timeout','A consulta demorou mais que o esperado.');throw e}
    throw new ApiError('rede','Não foi possível contatar a API do NEXUS.');
  }finally{clearTimeout(t);signal?.removeEventListener('abort',cancelar)}
}
