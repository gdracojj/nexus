// Fonte única da lógica de prazos. Campo usado: data_encerramento_proposta (prazo de propostas).
const fDia=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'});
const fHora=new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit'});
const fRot=new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',weekday:'short',day:'2-digit',month:'2-digit'});
const fData=new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
export const diaKey=d=>fDia.format(d);
const diaNum=d=>{const[y,m,x]=fDia.format(d).split('-').map(Number);return Date.UTC(y,m-1,x)/864e5};
/** Datas recebidas da API já têm fuso; aqui só são convertidas para exibição. */
export function parsePrazo(v){
  if(v==null||String(v).trim()==='')return null;
  const s=String(v).trim();
  if(!/(Z|[+-]\d{2}:?\d{2})$/i.test(s))return{invalid:true};
  const date=new Date(s);return isNaN(date)?{invalid:true}:{date};
}
export const BUCKETS=[['hoje','Hoje'],['amanha','Amanhã'],['tres','Próximos 3 dias'],['sete','Próximos 7 dias'],['adiante','Mais adiante'],['encerrado','Encerradas'],['semdata','Sem prazo informado']];
export function prepararPrazo(item,now=new Date()){
  const p=parsePrazo(item.prazo);
  if(!p)return{bucket:item.bucketPrazo||'semdata',estado:item.urgencia||'sem',label:'Data não informada'};
  if(p.invalid)return{bucket:item.bucketPrazo||'semdata',estado:item.urgencia||'sem',label:'Data inconsistente',invalido:true};
  const ms=p.date-now,dd=diaNum(p.date)-diaNum(now);
  const estado=item.urgencia||'azul',bucket=item.bucketPrazo||'semdata';
  const label=estado==='encerrado'?'Prazo encerrado':bucket==='hoje'?'Hoje':bucket==='amanha'?'Amanhã':`Prazo em ${Math.max(dd,1)} dias`;
  return{bucket,estado,label,date:p.date,ms,dd};
}
export const rotuloDia=d=>fRot.format(d);
export const dataCompleta=d=>fData.format(d);
export const horaCurta=d=>fHora.format(d);
export function restante(ms){const m=Math.floor(ms/6e4);if(m<60)return `${Math.max(m,1)} min`;const h=Math.floor(m/60);return h<24?`${h} h ${m%60} min`:`${Math.floor(h/24)} dias`}
