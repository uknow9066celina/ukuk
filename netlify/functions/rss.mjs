import { XMLParser } from 'fast-xml-parser';
const SOURCE='https://www.mois.go.kr/gpms/view/jsp/rss/rss.jsp?ctxCd=1012';
const parser=new XMLParser({ignoreAttributes:false,processEntities:true});
const text=v=>typeof v==='string'?v:typeof v==='number'?String(v):v?.['#text']??'';
export const handler=async()=>{
 try{
  const response=await fetch(SOURCE,{signal:AbortSignal.timeout(15000),headers:{Accept:'application/rss+xml, application/xml, text/xml'}});
  if(!response.ok)throw Error('RSS upstream HTTP '+response.status);
  const xml=await response.text();if(xml.length>5000000)throw Error('Feed too large');
  const parsed=parser.parse(xml);let raw=parsed?.rss?.channel?.item??[];raw=Array.isArray(raw)?raw:[raw];
  const items=raw.map((n,index)=>{let link=text(n.link).trim();try{const u=new URL(link,SOURCE);if(!['https:','http:'].includes(u.protocol)||!(u.hostname==='mois.go.kr'||u.hostname.endsWith('.mois.go.kr')))return null;u.protocol='https:';link=u.href}catch{return null}
   const title=text(n.title).replace(/<[^>]*>/g,'').trim();const date=text(n.pubDate)||text(n['dc:date']);const desc=text(n.description).replace(/<[^>]*>/g,'');return {title,date,link,ethics:/청렴|윤리|반부패|이해충돌|공직기강|부패/.test(title+' '+desc),index};
  }).filter(n=>n&&n.title&&n.date&&n.link);
  items.sort((a,b)=>{const x=Date.parse(a.date),y=Date.parse(b.date);return Number.isFinite(x)&&Number.isFinite(y)?y-x:a.index-b.index});
  if(items.length<5)throw Error('Fewer than 5 valid feed items');
  return {statusCode:200,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'public, max-age=600'},body:JSON.stringify({source:SOURCE,fetchedAt:new Date().toISOString(),items:items.map(({index,...item})=>item)})};
 }catch(error){console.error('RSS retrieval failed:',error.message);return {statusCode:502,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'},body:JSON.stringify({error:'행안부 RSS 수신 실패',source:SOURCE})}}
};
