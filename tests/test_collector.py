from scripts.collect import categorize,find_date,extract_dates,allowed,make_record
SRC={'competitor':'Etihad Airways','domain':'etihad.com','id':'etihad'}
def test_category():
    assert categorize('new direct flight route to China')=='Airline & Connectivity'
def test_date():
    assert find_date('opening on 14 November 2026')=='2026-11-14'
def test_future_not_publication():
    assert extract_dates('published 14 November 2026','2026-11-14') is None
def test_future_explicit():
    assert extract_dates('Flights launch from 14 November 2026','2026-10-01')=='2026-11-14'
def test_official_domain():
    assert allowed('https://www.etihad.com/en-us/news/x','etihad.com')
    assert not allowed('https://etihad.com.attacker.org/x','etihad.com')
def test_record():
    item=make_record(SRC,'https://www.etihad.com/en-us/news/new-route','Etihad new flight route to China','Flights launch from 14 November 2026','2026-10-01')
    assert item['china_relevance']=='High'
    assert item['activity_start_date']=='2026-11-14'
