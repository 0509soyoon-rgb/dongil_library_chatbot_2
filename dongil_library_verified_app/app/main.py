import json
import random
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'data' / 'library.db'
STATIC_DIR = Path(__file__).resolve().parent / 'static'

app = FastAPI(title='동일여고 AI 도서관', version='2.0')
app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')

def conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def norm(s: str) -> str:
    return re.sub(r'[^0-9a-zA-Z가-힣]+', '', (s or '').lower())

def loads(s, default):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default

def book(row):
    if row is None: return None
    d = dict(row)
    d['tags'] = loads(d.pop('tags_json', '[]'), [])
    d['careers'] = loads(d.pop('careers_json', '[]'), [])
    d['topics'] = loads(d.pop('topics_json', '[]'), [])
    d['kyobo_search_url'] = 'https://search.kyobobook.co.kr/search?keyword=' + re.sub(r'\s+', '+', d.get('title',''))
    return d

def query_books(sql, params=()):
    with conn() as con:
        return [book(r) for r in con.execute(sql, params).fetchall()]

def one(sql, params=()):
    with conn() as con:
        return book(con.execute(sql, params).fetchone())

def career_key(q: str):
    ql = (q or '').lower()
    aliases = {
        '의사':'의학/보건','간호':'의학/보건','간호학과':'의학/보건','의대':'의학/보건','약대':'의학/보건','약사':'의학/보건','보건':'의학/보건','생명':'의학/보건',
        'ai':'공학/AI','인공지능':'공학/AI','개발자':'공학/AI','컴퓨터':'공학/AI','컴공':'공학/AI','공학':'공학/AI','데이터':'공학/AI','로봇':'공학/AI',
        '수학':'수학/통계','통계':'수학/통계','수학교육':'수학/통계','수학교사':'수학/통계',
        '교사':'교육/교사','교육':'교육/교사','사범':'교육/교사',
        '법':'법/사회','변호사':'법/사회','판사':'법/사회','정치':'법/사회','사회':'법/사회','인권':'법/사회',
        '경영':'경제/경영','경제':'경제/경영','회계':'경제/경영','마케팅':'경제/경영','창업':'경제/경영',
        '문학':'문학/창작','작가':'문학/창작','국어':'문학/창작','문예':'문학/창작',
        '심리':'심리/상담','상담':'심리/상담','마음':'심리/상담',
        '디자인':'예술/디자인','건축':'예술/디자인','미술':'예술/디자인','예술':'예술/디자인','음악':'예술/디자인',
        '환경':'환경/생태','기후':'환경/생태','생태':'환경/생태',
        '역사':'역사/문화','문화':'역사/문화','한국사':'역사/문화','세계사':'역사/문화'
    }
    for k,v in aliases.items():
        if k in ql:
            return v
    return None

@app.get('/')
def index():
    return FileResponse(STATIC_DIR / 'index.html')

@app.get('/api/meta')
def meta():
    with conn() as con:
        m = {r['key']: loads(r['value'], r['value']) for r in con.execute('SELECT key,value FROM meta')}
    return m

@app.get('/api/search')
def search(q: str = Query(..., min_length=1), limit: int = 12):
    n = norm(q)
    ck = career_key(q)
    if ck and any(w in q for w in ['추천','되고','학과','진로','생기부','탐구','책']):
        return {'mode':'career', 'message':f'{ck}와 관련된 실제 소장 도서만 골랐습니다.', 'books': recommend_by_career(ck, limit)}
    # 1 exact normalized title
    exact = query_books('SELECT * FROM books WHERE title_norm=? ORDER BY original_no LIMIT ?', (n, limit))
    if exact:
        return {'mode':'exact_title', 'message':'제목이 정확히 일치하는 실제 소장 도서입니다.', 'books': exact}
    # 2 startswith normalized title
    starts = query_books('SELECT * FROM books WHERE title_norm LIKE ? ORDER BY LENGTH(title), original_no LIMIT ?', (n+'%', limit))
    if starts:
        return {'mode':'title_starts', 'message':'정확히 같은 제목은 없고, 제목이 검색어로 시작하는 실제 소장 도서입니다.', 'books': starts}
    # 3 title contains / author/publisher contains
    like = f'%{q}%'
    rows = query_books('''SELECT * FROM books
        WHERE title LIKE ? OR author LIKE ? OR publisher LIKE ? OR genre LIKE ?
        ORDER BY CASE WHEN title LIKE ? THEN 0 ELSE 1 END, LENGTH(title), original_no LIMIT ?''',
        (like, like, like, like, like, limit))
    if rows:
        return {'mode':'keyword', 'message':'검색어와 관련된 실제 소장 도서입니다.', 'books': rows}
    # 4 career fallback
    if ck:
        return {'mode':'career', 'message':f'{ck}와 관련된 실제 소장 도서만 골랐습니다.', 'books': recommend_by_career(ck, limit)}
    return {'mode':'empty', 'message':'원본 소장도서 목록에서 찾지 못했습니다. 검색어를 짧게 바꿔 보세요.', 'books': []}

@app.get('/api/book/{book_id}')
def detail(book_id: int):
    b = one('SELECT * FROM books WHERE id=?', (book_id,))
    if not b:
        return {'error':'not_found'}
    similar = query_books('''SELECT * FROM books WHERE id<>? AND (genre=? OR tags_json LIKE ?)
        ORDER BY ABS(difficulty-?), RANDOM() LIMIT 6''', (book_id, b['genre'], f'%{b["genre"]}%', b['difficulty']))
    return {'book': b, 'similar': similar}

def recommend_by_career(career: str, limit=8, max_level: Optional[int]=None):
    level_clause = ''
    params = [f'%{career}%']
    if max_level:
        level_clause = ' AND difficulty <= ?'
        params.append(max_level)
    params.append(limit)
    return query_books(f'''SELECT * FROM books
        WHERE careers_json LIKE ? {level_clause}
        ORDER BY difficulty, RANDOM() LIMIT ?''', tuple(params))

@app.get('/api/career')
def career(q: str, level: Optional[int] = None, limit: int = 8):
    ck = career_key(q) or q
    return {'career': ck, 'books': recommend_by_career(ck, limit, level)}

@app.get('/api/today')
def today():
    # 날짜 기반 고정 추천: 매일 같고 다음날 바뀜. 실제 DB에서만 선택.
    with conn() as con:
        count = con.execute('SELECT COUNT(*) AS c FROM books').fetchone()['c']
    rnd = random.Random(date.today().isoformat())
    offset = rnd.randrange(max(count,1))
    b = one('SELECT * FROM books ORDER BY id LIMIT 1 OFFSET ?', (offset,))
    if not b:
        return {'book': None}
    return {'book': b, 'message':'오늘의 책은 원본 소장도서 목록에서 날짜 기준으로 선정됩니다.'}

@app.get('/api/random')
def random_book(level: Optional[int] = None):
    if level:
        rows = query_books('SELECT * FROM books WHERE difficulty<=? ORDER BY RANDOM() LIMIT 1', (level,))
    else:
        rows = query_books('SELECT * FROM books ORDER BY RANDOM() LIMIT 1')
    return {'book': rows[0] if rows else None}

TYPE_NAMES = {
    'SLRG':'현실공감 진로독서가','SLRT':'감성공감 독서가','SLIG':'상상형 진로탐험가','SLIT':'이야기 여행가',
    'SDRG':'깊이파는 현실분석가','SDRT':'문학탐구형 독서가','SDIG':'세계관 탐험가','SDIT':'몰입형 감성독서가',
    'CLRG':'실용지식 수집가','CLRT':'호기심 지식러','CLIG':'미래진로 설계자','CLIT':'상상지식 탐험가',
    'CDRG':'심화진로 탐구자','CDRT':'개념덕후 탐구자','CDIG':'미래연구형 독서가','CDIT':'철학적 사색가'
}
TYPE_DESC = {
    'S':'인물과 사건을 따라가며 의미를 찾는 편입니다.', 'C':'개념과 원리를 이해하는 독서를 좋아합니다.',
    'L':'부담 없이 읽히는 책에서 시작할 때 오래 갑니다.', 'D':'어려워도 깊이 파고드는 독서에 강합니다.',
    'R':'현실 문제와 실제 사례에 관심이 큽니다.', 'I':'상상력, 세계관, 미래 가능성에 끌립니다.',
    'G':'진로와 학과 목표에 연결되는 책을 선호합니다.', 'T':'취향과 감정에 맞는 책을 찾는 편입니다.'
}

def tags_for_type(code):
    tags=[]
    if code[0]=='S': tags += ['문학/창작','심리/상담','교육/교사']
    else: tags += ['수학/통계','공학/AI','자연과학','경제/경영']
    if code[2]=='R': tags += ['법/사회','역사/문화','의학/보건']
    else: tags += ['문학/창작','공학/AI','예술/디자인']
    if code[3]=='G': tags += ['교육/교사','의학/보건','공학/AI','경제/경영']
    else: tags += ['문학/창작','심리/상담','예술/디자인']
    return list(dict.fromkeys(tags))

@app.get('/api/type-result')
def type_result(code: str):
    code = ''.join([c for c in code.upper() if c in 'SCLDRIGT'])[:4]
    if len(code) != 4:
        return {'error':'invalid_code'}
    target_tags = tags_for_type(code)
    level_limit = 2 if code[1]=='L' else 5
    placeholders = ' OR '.join(['careers_json LIKE ? OR tags_json LIKE ?' for _ in target_tags])
    params=[]
    for t in target_tags:
        params += [f'%{t}%', f'%{t}%']
    params += [level_limit, 8]
    books = query_books(f'''SELECT * FROM books WHERE ({placeholders}) AND difficulty<=?
        ORDER BY difficulty, RANDOM() LIMIT ?''', tuple(params))
    return {
        'code': code,
        'name': TYPE_NAMES.get(code, '나만의 독서유형'),
        'description': ' '.join(TYPE_DESC[c] for c in code),
        'recommended_tags': target_tags,
        'books': books
    }
