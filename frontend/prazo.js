// Fonte única da lógica de prazos. Campo usado: data_encerramento_proposta (prazo de propostas).
const TZ='America/Sao_Paulo';
const fDia=new Intl.DateTimeFormat('en-CA',{timeZone:TZ,year:'numeric',month:'2-digit',day:'2-digit'});
const fHora=new Intl.DateTimeFormat('pt-BR',{timeZone:TZ,hour:'2-digit',minute:'2-digit'});
const fRot=new Intl.DateTimeFormat('pt-BR',{timeZone:TZ,weekday:'short',day:'2-digit',month:'2-digit'});
const fData=new Intl.DateTimeFormat('pt-BR',{timeZone:TZ,day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
export const diaKey=d=>fDia.format(d);
const diaNum=d=>{const[y,m,x]=fDia.format(d).split('-').map(Number);return Date.UTC(y,m-1,x)/864e5};
/** null = ausente; {invalid:true} = inválido; {date,semHora}. Sem offset => America/Sao_Paulo. */
export function parsePrazo(v){
  if(v==null||String(v).trim()==='')return null;
  let s=String(v).trim().replace(' ','T'),semHora=false;
  if(/^\d{4}-\d{2}-\d{2}$/.test(s)){s+='T23:59:59';semHora=true}
  if(!/(Z|[+-]\d{2}:?\d{2})$/.test(s))s+='-03:00';
  const date=new Date(s);return isNaN(date)?{invalid:true}:{date,semHora};
}
export const BUCKETS=[['hoje','Hoje'],['amanha','Amanhã'],['tres','Próximos 3 dias'],['sete','Próximos 7 dias'],['adiante','Mais adiante'],['encerrado','Encerradas'],['semdata','Sem prazo informado']];
export function classificar(valor,now=new Date()){
  const p=parsePrazo(valor);
  if(!p)return{bucket:'semdata',estado:'sem',label:'Data não informada'};
  if(p.invalid)return{bucket:'semdata',estado:'sem',label:'Data inconsistente',invalido:true};
  const ms=p.date-now,dd=diaNum(p.date)-diaNum(now),hora=p.semHora?'':` às ${fHora.format(p.date)}`;
  if(ms<=0)return{bucket:'encerrado',estado:'encerrado',label:'Prazo encerrado',date:p.date,ms,dd};
  const h=Math.floor(ms/36e5),mi=Math.max(1,Math.floor(ms/6e4));
  const estado=ms<864e5?'urgente':ms<=3*864e5?'atencao':'normal';
  const bucket=dd<=0?'hoje':dd===1?'amanha':dd<=3?'tres':dd<=7?'sete':'adiante';
  const label=dd<=0?`Hoje${hora} · faltam ${h>=1?h+' h':mi+' min'}`:dd===1?`Amanhã${hora}`:`Faltam ${dd} dias`;
  return{bucket,estado,label,date:p.date,ms,dd};
}
export const rotuloDia=d=>fRot.format(d);
export const dataCompleta=d=>fData.format(d);
export const horaCurta=d=>fHora.format(d);
export function restante(ms){const m=Math.floor(ms/6e4);if(m<60)return `${Math.max(m,1)} min`;const h=Math.floor(m/60);return h<24?`${h} h ${m%60} min`:`${Math.floor(h/24)} dias`}
