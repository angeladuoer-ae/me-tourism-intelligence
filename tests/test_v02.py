from scripts.collect import article_data,discover_links,extract_dates,categorize,make_record
SRC={'id':'emirates','competitor':'Emirates','domain':'emirates.com','url':'https://www.emirates.com/media-centre/','article_path':'/media-centre/[^/]+$'}
def test_article_meta():
 html='''<html><head><meta property="og:title" content="Emirates launches visitor rewards"><meta property="article:published_time" content="2026-10-22T10:00:00Z"></head><body><article><h1>Emirates launches visitor rewards</h1><p>Emirates has launched a new visitor reward programme designed to encourage overnight stays in Dubai.</p></article></body></html>'''
 title,body,date=article_data(html)
 assert title=='Emirates launches visitor rewards' and date=='2026-10-22' and 'Dubai' in body

def test_only_allowed_article_paths():
 html='''<a href="/media-centre/emirates-announces-new-flights">Emirates announces new direct flights</a><a href="/media-centre/">Media Centre Dubai Latest News</a><a href="https://evil.com/media-centre/travel-agent-promotion">Travel agent promotion</a>'''
 items=discover_links(html,SRC)
 assert len(items)==1 and items[0][0].endswith('new-flights')

def test_future_calendar_cues():
 assert extract_dates('The roadshow will take place on 14 November 2027','2026-10-26')=='2027-11-14'
 assert extract_dates('Results for 14 November 2020 are now available','2026-10-26') is None

def test_b2c_precedence():
 assert categorize('Emirates loyalty promotion offer to Dubai visitors')=='B2C Campaign'
