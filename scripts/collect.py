"""Conservative public-site collector. No login, bypass, or unofficial-source claims."""
import hashlib, json, re, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'activities.json'
STATUS=ROOT/'data'/'source_status.json'
HEADERS={'User-Agent':'ME-Tourism-Intelligence-Hub/0.1 (+respectful public page research)','Accept':'text/html,application/xhtml+xml'}
KEYWORDS={'B2C Campaign':['campaign','promotion','offer','discount','sale','marketing','推广','促销'],
 'B2B Trade Activation':['roadshow','webinar','trade','travel agent','fam trip','workshop','路演','同业'],
 'OTA & Sales Conversion':['booking','package','travel platform','ota','ctrip','fliggy','携程','飞猪'],
 'Airline & Connectivity':['flight','route','airline','direct service','frequency','stopover','航线','航班'],
 'PR, KOL & Celebrity':['influencer','celebrity','media campaign','ambassador','kol','明星'],
 'Destination Development':['hotel','resort','attraction','visa','destination','度假区'],
 'Events & Sponsorship':['festival','event','sponsor','concert','sport','展会'],
 'Market Intelligence & Data':['visitor','arrival','tourism statistics','research','report','游客']}
CHINA=['china','chinese','beijing','shanghai','guangzhou','shenzhen','chengdu','ctrip','fliggy','wechat','中国','携程','飞猪','上海','北京']
MONTHS='January February March April May June July August September October November December'.split()
DATE_PATTERN=re.compile(r'\b(?:[0-3]?\d\s+(?:'+ '|'.join(MONTHS)+r')\s+20\d{2}|(?:'+'|'.join(MONTHS)+r')\s+[0-3]?\d,?\s+20\d{2}|20\d{2}-\d{2}-\d{2})\b',re.I)

def normalized_url(url):
    url=urldefrag(url)[0]
    return url.split('?')[0].rstrip('/')

def allowed(url,domain):
    parsed=urlparse(url)
    return parsed.scheme=='https' and (parsed.hostname==domain or (parsed.hostname or '').endswith('.'+domain))

def categorize(text):
    lower=text.lower()
    matches=[(sum(term in lower for term in terms),category) for category,terms in KEYWORDS.items()]
    matches.sort(reverse=True)
    return matches[0][1] if matches[0][0]>0 else 'Other / Review'

def find_date(text):
    m=DATE_PATTERN.search(text or '')
    if not m:return None
    try:
        d=dateparser.parse(m.group(0),fuzzy=False).date()
        if not 2015<=d.year<=2040:return None
        return d.isoformat()
    except (ValueError,OverflowError,TypeError):return None

def extract_dates(text, published):
    # Conservative rule: never infer an event date from the publication date alone.
    cues=r'(?:from|starting|begins?|launch(?:es|ing)?|open(?:s|ing)?|commenc(?:es|ing)|on|until|through|计划于|将于|开始于)\s+'
    for m in re.finditer(cues,text or '',re.I):
        fragment=(text or '')[m.end():m.end()+65]
        d=find_date(fragment)
        if d and (not published or d!=published):return d
    return None

def make_record(source,url,title,body='',published=None):
    title=' '.join(title.split())[:280]
    body=' '.join(body.split())[:1600]
    combined=title+' '+body
    if not title or len(title)<12:return None
    canonical=normalized_url(url)
    category=categorize(combined)
    relevance='High' if any(x in combined.lower() for x in CHINA) else 'Global'
    future=extract_dates(combined,published)
    record={
      'id':hashlib.sha256(canonical.encode()).hexdigest()[:20],
      'title':title,'summary':body[:600], 'competitor':source['competitor'],
      'category':category,'published_date':published,'activity_start_date':future,
      'activity_end_date':None,'china_relevance':relevance,
      'activity_status': 'Upcoming' if future and future>datetime.now(timezone.utc).date().isoformat() else 'Unknown',
      'verification':'Official source page' if allowed(url,source['domain']) else 'Needs review',
      'source_type':'Official','source_url':canonical,'source_id':source['id'],
      'confidence':'Source verified; activity details unreviewed',
      'sta_implication':None,'recommended_action':None,
      'first_seen':datetime.now(timezone.utc).isoformat(timespec='seconds')}
    return record

def collect_source(session,src):
    r=session.get(src['url'],headers=HEADERS,timeout=20)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser')
    for el in soup(['script','style','nav','footer','header']):el.decompose()
    candidates=[]; seen=set()
    for a in soup.find_all('a',href=True):
        url=urljoin(src['url'],a['href'])
        if not allowed(url,src['domain']):continue
        url=normalized_url(url)
        if url==normalized_url(src['url']) or url in seen:continue
        title=' '.join(a.get_text(' ',strip=True).split())
        if not 18<=len(title)<=280:continue
        # Exclude high-noise navigation / generic category links.
        if len(title.split())<4 or re.fullmatch(r'(read more|learn more|view all|more news).*',title,re.I):continue
        container=a.find_parent(['article','li','div'])
        context=container.get_text(' ',strip=True)[:900] if container else title
        if categorize(title+' '+context)=='Other / Review':continue
        published=find_date(context)
        rec=make_record(src,url,title,context,published)
        if rec:candidates.append(rec);seen.add(url)
        if len(candidates)>=45:break
    return candidates

def main():
    sources=json.loads((ROOT/'sources.json').read_text())
    existing=json.loads(DATA.read_text()) if DATA.exists() else []
    byid={x['id']:x for x in existing}
    logs=[]; session=requests.Session()
    for src in sources:
        if not src['enabled']:
            logs.append({'source':src['id'],'state':'disabled / needs collector review'})
            continue
        try:
            rows=collect_source(session,src);added=0
            for row in rows:
                if row['id'] not in byid:byid[row['id']]=row;added+=1
            logs.append({'source':src['id'],'state':'ok','found':len(rows),'new':added})
        except requests.RequestException as exc:
            logs.append({'source':src['id'],'state':'failed','error':str(exc)[:200]})
        time.sleep(1)
    rows=sorted(byid.values(),key=lambda x:(x.get('published_date') or '',x.get('first_seen') or ''),reverse=True)[:2500]
    DATA.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    STATUS.write_text(json.dumps({'last_run':datetime.now(timezone.utc).isoformat(),'sources':logs,'total_saved':len(rows)},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(logs,indent=2))
    # Do not hide source failures; status is recorded and shown in UI.

if __name__=='__main__':main()
