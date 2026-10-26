"""Public tourism intelligence collector: conservative extract, traceability, incremental persistence."""
import hashlib, json, re, time, html
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'activities.json'
STATUS=ROOT/'data'/'source_status.json'
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; METourismIntelligenceHub/0.2; public research)','Accept':'text/html,application/xhtml+xml'}
KEYWORDS={
 'B2C Campaign':['campaign','promotion','offer','discount','sale','marketing','loyalty','reward','推广','促销'],
 'B2B Trade Activation':['roadshow','webinar','travel trade','trade partners','travel agent','fam trip','familiarisation','workshop','路演','同业'],
 'OTA & Sales Conversion':['online travel','travel package','booking platform','ota','ctrip','fliggy','携程','飞猪'],
 'Airline & Connectivity':['flight','route','airline','airways','direct service','frequency','stopover','charter','航线','航班'],
 'PR, KOL & Celebrity':['influencer','celebrity','brand ambassador','media partnership','kol','明星'],
 'Destination Development':['hotel','resort','attraction','visa','destination development','度假区'],
 'Events & Sponsorship':['festival','event','sponsor','concert','sport','exhibition','展会'],
 'Market Intelligence & Data':['visitor arrivals','tourism statistics','tourism performance','market research','tourism report','游客']}
CHINA=['china','chinese','beijing','shanghai','guangzhou','shenzhen','chengdu','ctrip','fliggy','wechat','中国','携程','飞猪','上海','北京']
MONTHS='January February March April May June July August September October November December'.split()
MONTH_RE='(?:'+'|'.join(MONTHS)+')'
DATE_PATTERN=re.compile(r'\b(?:[0-3]?\d\s+'+MONTH_RE+r'\s+20\d{2}|'+MONTH_RE+r'\s+[0-3]?\d,?\s+20\d{2}|20\d{2}-\d{2}-\d{2})\b',re.I)
FUTURE_CUES=re.compile(r'\b(?:will (?:be held|take place|open|begin|start|launch|run)|scheduled (?:for|to)|set to (?:open|launch|begin)|takes place|taking place|starting|starts|begins|opens|launches|from|on)\b|(?:将于|定于|计划于|预计于|举办时间)',re.I)
BLOCKED_PATHS=('privacy','cookie','terms','contact','careers','login','register','signup','about-us','javascript:')

def normalized_url(url):
    p=urlparse(urldefrag(url)[0]);return p._replace(query='',fragment='').geturl().rstrip('/')

def allowed(url,domain):
    p=urlparse(url);host=p.hostname or ''
    return p.scheme=='https' and (host==domain or host.endswith('.'+domain))

def categorize(text):
    lower=(text or '').lower();score={category:sum(1 for term in terms if term in lower) for category,terms in KEYWORDS.items()}
    # Specific marketing intent should supersede generic airline or development mentions.
    for cat in ['OTA & Sales Conversion','B2B Trade Activation','B2C Campaign','PR, KOL & Celebrity','Airline & Connectivity','Events & Sponsorship','Market Intelligence & Data','Destination Development']:
        if score[cat]>0 and score[cat]>=max(score.values()):return cat
    return 'Other / Review'

def find_date(text):
    m=DATE_PATTERN.search(text or '')
    if not m:return None
    try:
        dt=dateparser.parse(m.group(0),fuzzy=False).date()
        return dt.isoformat() if 2018<=dt.year<=2040 else None
    except (ValueError,OverflowError,TypeError):return None

def extract_dates(text,published):
    today=datetime.now(timezone.utc).date().isoformat()
    for cue in FUTURE_CUES.finditer(text or ''):
        snippet=text[cue.start():cue.end()+105]
        dm=DATE_PATTERN.search(snippet)
        if not dm:continue
        date=find_date(dm.group(0))
        # Preserve only future or active dates; do not mistake dates in old retrospective reports.
        if date and date>today and date!=published:return date
    return None

def compact_text(t,limit=200):
    return ' '.join(html.unescape(t or '').split()).strip()[:limit]

def read_meta(soup,keys):
    for attr,key in keys:
        node=soup.find('meta',attrs={attr:key})
        if node and node.get('content'):return compact_text(node['content'],300)
    return None

def get_jsonld(soup):
    for script in soup.find_all('script',type='application/ld+json'):
        try: data=json.loads(script.string or script.get_text())
        except (ValueError,TypeError):continue
        pool=data if isinstance(data,list) else [data]
        for obj in pool:
            if isinstance(obj,dict) and '@graph' in obj:pool+=obj['@graph'] if isinstance(obj['@graph'],list) else []
        for obj in pool:
            if isinstance(obj,dict) and (obj.get('headline') or obj.get('datePublished')):return obj
    return {}

def article_data(html_text,fallback=''):
    soup=BeautifulSoup(html_text,'html.parser');ld=get_jsonld(soup)
    h=soup.find('h1')
    title=compact_text(ld.get('headline') or read_meta(soup,[('property','og:title'),('name','twitter:title')]) or (h.get_text(' ',strip=True) if h else '') or fallback,240)
    # Reject common pasted list-card dates/excerpts and site chrome.
    title=re.split(r'\s+(?:'+MONTH_RE+r')\s+\d{1,2}\s*,?\s*20\d{2}\s*\|',title,maxsplit=1,flags=re.I)[0]
    title=re.sub(r'\s*\|\s*(?:Emirates|Etihad Airways|Dubai DET|GoTürkiye).*$','',title,flags=re.I)
    rawdate=ld.get('datePublished') or read_meta(soup,[('property','article:published_time'),('name','datePublished'),('name','pubdate'),('itemprop','datePublished')])
    time_tag=soup.find('time',datetime=True)
    if not rawdate and time_tag:rawdate=time_tag.get('datetime')
    date=None
    if rawdate:
        try:date=dateparser.parse(rawdate).date().isoformat()
        except (ValueError,TypeError,OverflowError):pass
    if not date:
        head=soup.find(['article','main']) or soup
        date=find_date(head.get_text(' ',strip=True)[:450])
    desc=compact_text(ld.get('description') or read_meta(soup,[('name','description'),('property','og:description')]) or '',650)
    article=soup.find('article') or soup.find('main') or soup
    for el in article(['script','style','nav','footer','header','aside','form']):el.decompose()
    paras=[compact_text(p.get_text(' ',strip=True),900) for p in article.find_all('p')]
    paras=[p for p in paras if len(p)>=45 and not p.lower().startswith(('subscribe','cookie','read more'))]
    body=compact_text(' '.join(paras[:9]),1800)
    if not body:body=desc
    return title,body,date

def make_record(source,url,title,body='',published=None):
    title=compact_text(title,240);body=compact_text(body,1800)
    if len(title)<12:return None
    canonical=normalized_url(url);combined=title+' '+body
    category=categorize(combined)
    relevance='High' if any(x in combined.lower() for x in CHINA) else 'Global'
    future=extract_dates(combined,published)
    return {'id':hashlib.sha256(canonical.encode()).hexdigest()[:20], 'title':title,'summary':body[:650],
        'competitor':source['competitor'],'category':category,'published_date':published,
        'activity_start_date':future,'activity_end_date':None,'china_relevance':relevance,
        'activity_status':'Upcoming' if future else 'Unknown',
        'verification':'Official source page' if allowed(url,source['domain']) else 'Needs review',
        'source_type':'Official','source_url':canonical,'source_id':source['id'],
        'confidence':'Official source URL; automatically extracted fields require review',
        'sta_implication':None,'recommended_action':None,
        'first_seen':datetime.now(timezone.utc).isoformat(timespec='seconds')}

def discover_links(html_text,src):
    soup=BeautifulSoup(html_text,'html.parser');out=[];seen=set()
    for a in soup.find_all('a',href=True):
        url=normalized_url(urljoin(src['url'],a['href']))
        if not allowed(url,src['domain']) or url in seen or url==normalized_url(src['url']):continue
        path=urlparse(url).path.lower()
        if any(x in path for x in BLOCKED_PATHS):continue
        if src.get('article_path') and not re.search(src['article_path'],path,re.I):continue
        title=compact_text(a.get_text(' ',strip=True),240)
        if len(title)<18 or len(title.split())<4 or title.lower() in ('read more','learn more','view all'):continue
        if categorize(title)=='Other / Review' and not src.get('article_path'):continue
        seen.add(url);out.append((url,title))
        if len(out)>=src.get('max_articles',12):break
    return out

def collect_source(session,src):
    r=session.get(src['url'],headers=HEADERS,timeout=(10,18));r.raise_for_status()
    candidates=discover_links(r.text,src);results=[]
    for url,fallback in candidates:
        try:
            response=session.get(url,headers=HEADERS,timeout=(8,12));response.raise_for_status()
            title,body,published=article_data(response.text,fallback)
            if len(title)<12 or not body:continue
            # avoid stale undated articles from broad link collections
            if not published:continue
            if (datetime.now(timezone.utc).date()-dateparser.parse(published).date()).days>180:continue
            rec=make_record(src,url,title,body,published)
            if rec and categorize(title+' '+body)!='Other / Review':results.append(rec)
        except requests.RequestException:continue
        time.sleep(0.15)
    return results

def main():
    sources=json.loads((ROOT/'sources.json').read_text(encoding='utf8'))
    existing=json.loads(DATA.read_text(encoding='utf8')) if DATA.exists() else []
    byid={x['id']:x for x in existing};logs=[];session=requests.Session()
    for src in sources:
        if not src['enabled']:
            logs.append({'source':src['id'],'state':'disabled / pending compatibility check'});continue
        try:
            rows=collect_source(session,src);added=updated=0
            for row in rows:
                old=byid.get(row['id'])
                if old:
                    row['first_seen']=old.get('first_seen',row['first_seen'])
                    if any(old.get(k)!=row.get(k) for k in ('title','summary','published_date','category','activity_start_date')):updated+=1
                else:added+=1
                byid[row['id']]=row
            logs.append({'source':src['id'],'state':'ok' if rows else 'no verified articles / review required','found':len(rows),'new':added,'updated':updated})
        except requests.RequestException as exc:logs.append({'source':src['id'],'state':'failed','error':str(exc)[:220]})
        time.sleep(0.3)
    rows=sorted(byid.values(),key=lambda x:(x.get('published_date') or '',x.get('first_seen') or ''),reverse=True)[:2500]
    DATA.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    STATUS.write_text(json.dumps({'last_run':datetime.now(timezone.utc).isoformat(),'sources':logs,'total_saved':len(rows)},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(logs,indent=2))

if __name__=='__main__':main()
