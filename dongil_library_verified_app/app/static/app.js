const $ = (s) => document.querySelector(s);
const results = $('#results');
const notice = $('#notice');

function stars(n){ return '⭐'.repeat(Number(n || 1)); }
function esc(s){ return String(s ?? '').replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])); }

async function getJSON(url){
  const res = await fetch(url);
  if(!res.ok) throw new Error('요청 실패');
  return await res.json();
}

function renderBooks(title, message, books){
  notice.textContent = message || '';
  if(!books || books.length === 0){
    results.innerHTML = `<section class="panel"><h2>검색 결과 없음</h2><p class="hint">원본 소장도서 목록에서 찾지 못했습니다. 제목 일부나 저자명으로 다시 검색해 보세요.</p></section>`;
    return;
  }
  results.innerHTML = `
    <div class="sectionTitle"><h2>${esc(title)}</h2><span class="hint">카드를 클릭하면 상세정보가 열립니다.</span></div>
    <div class="cards">${books.map(bookCard).join('')}</div>`;
  document.querySelectorAll('[data-book]').forEach(el => el.addEventListener('click', () => openBook(el.dataset.book)));
}

function bookCard(b){
  return `<article class="book" data-book="${b.id}">
    <h3>${esc(b.title)}</h3>
    <div class="author">${esc(b.author || '저자 정보 없음')}</div>
    <div class="pillRow"><span class="pill">${esc(b.genre || '미분류')}</span><span class="pill">${stars(b.difficulty)} ${esc(b.difficulty_label)}</span></div>
    <p>${esc(b.intro || '동일여고 소장도서입니다.')}</p>
    <p><b>추천 이유</b><br>${esc(b.recommend_reason || '')}</p>
    <div class="sourceMark">실제 소장 도서 · 원본 자료명 그대로</div>
  </article>`;
}

async function search(q){
  q = (q || $('#searchInput').value).trim();
  if(!q){ $('#searchInput').focus(); return; }
  results.innerHTML = `<section class="panel"><p>검색 중...</p></section>`;
  const data = await getJSON(`/api/search?q=${encodeURIComponent(q)}&limit=12`);
  renderBooks(data.mode === 'career' ? '🎓 진로 맞춤 추천' : '🔍 검색 결과', data.message, data.books);
}

async function openBook(id){
  const data = await getJSON(`/api/book/${id}`);
  if(data.error) return;
  const b = data.book;
  $('#detail').innerHTML = `
    <div class="detailTitle">
      <h2>${esc(b.title)}</h2>
      <div class="hint">${esc(b.author || '저자 정보 없음')} · ${esc(b.publisher || '출판사 정보 없음')}</div>
      <div class="pillRow"><span class="pill">실제 동일여고 소장도서</span><span class="pill">${esc(b.genre)}</span><span class="pill">${stars(b.difficulty)} ${esc(b.difficulty_label)}</span></div>
    </div>
    <div class="split">
      <section class="box">
        <h3>원본 정보</h3>
        <table class="infoTable">
          <tr><th>자료명</th><td>${esc(b.title)}</td></tr>
          <tr><th>저자</th><td>${esc(b.author)}</td></tr>
          <tr><th>출판사</th><td>${esc(b.publisher)}</td></tr>
          <tr><th>출판년도</th><td>${esc(b.pub_year)}</td></tr>
          <tr><th>청구기호</th><td>${esc(b.call_no)}</td></tr>
          <tr><th>소장처</th><td>${esc(b.location)}</td></tr>
          <tr><th>등록번호</th><td>${esc(b.reg_no)}</td></tr>
        </table>
      </section>
      <section class="box">
        <h3>AI 보조 정보</h3>
        <p>${esc(b.intro)}</p>
        <p><b>추천 이유</b><br>${esc(b.recommend_reason)}</p>
        <p><b>관련 진로</b><br>${(b.careers || []).map(esc).join(', ') || '자동 분류 없음'}</p>
        <p><b>태그</b><br>${(b.tags || []).map(t=>`<span class="pill">${esc(t)}</span>`).join(' ')}</p>
      </section>
    </div>
    <section class="box" style="margin-top:14px">
      <h3>탐구주제 추천</h3>
      <ul class="topics">${(b.topics || []).map(t=>`<li>${esc(t)}</li>`).join('')}</ul>
      <p class="hint">※ 탐구주제는 자동 보조 제안입니다. 실제 독서 내용에 맞게 수정해서 사용하세요.</p>
    </section>
    <section class="box" style="margin-top:14px">
      <h3>비슷한 실제 소장도서</h3>
      <div class="similar">${(data.similar || []).map(s=>`<div class="mini" data-book="${s.id}"><b>${esc(s.title)}</b><br><span class="hint">${esc(s.author || '')}</span></div>`).join('')}</div>
    </section>
    <section class="box" style="margin-top:14px">
      <h3>외부 정보 확인</h3>
      <p class="hint">추가 설명이 필요하면 교보문고 또는 출판사 정보를 직접 확인하세요. 프로그램 안에서는 원본에 없는 책을 만들지 않습니다.</p>
      <a href="${b.kyobo_search_url}" target="_blank" rel="noopener">교보문고에서 이 제목 검색하기</a>
    </section>
  `;
  $('#modal').classList.remove('hidden');
  document.querySelectorAll('.mini[data-book]').forEach(el => el.addEventListener('click', () => openBook(el.dataset.book)));
}

async function today(){
  const data = await getJSON('/api/today');
  renderBooks('📖 오늘의 책', data.message, data.book ? [data.book] : []);
}
async function randomBook(){
  const data = await getJSON('/api/random');
  renderBooks('🎲 운명의 책 뽑기', '원본 소장도서 중 무작위로 뽑았습니다.', data.book ? [data.book] : []);
}
async function career(c){
  const data = await getJSON(`/api/career?q=${encodeURIComponent(c)}&limit=9`);
  renderBooks(`🎓 ${data.career} 추천`, '해당 분야와 연결되는 실제 소장도서입니다.', data.books);
}

const questions = [
  ['책을 고를 때 더 끌리는 것은?', ['인물과 사건이 있는 이야기', 'S'], ['개념과 지식을 얻는 책', 'C']],
  ['읽기 방식은?', ['짧고 쉽게 읽히는 책부터', 'L'], ['어려워도 깊이 있는 책', 'D']],
  ['더 관심 있는 주제는?', ['현실 문제와 실제 사례', 'R'], ['상상력, 세계관, 미래', 'I']],
  ['책을 읽는 목적은?', ['진로·학과·생기부에 도움', 'G'], ['내 취향과 감정에 맞는 책', 'T']],
  ['좋아하는 설명 방식은?', ['사람 이야기로 풀어주는 설명', 'S'], ['원리와 구조가 분명한 설명', 'C']],
  ['책 난이도는?', ['부담 없는 책이 좋다', 'L'], ['도전적인 책도 좋다', 'D']],
  ['끌리는 배경은?', ['학교, 사회, 역사, 실제 세계', 'R'], ['판타지, 미래, 철학적 상상', 'I']],
  ['추천받고 싶은 책은?', ['진로 로드맵에 맞는 책', 'G'], ['지금 내 마음에 맞는 책', 'T']]
];
function renderTypeTest(){
  const area = $('#questions');
  area.innerHTML = questions.map((q,i)=>`
    <div class="question">
      <b>Q${i+1}. ${esc(q[0])}</b>
      <div class="choices">
        <label><input type="radio" name="q${i}" value="${q[1][1]}"> ${esc(q[1][0])}</label>
        <label><input type="radio" name="q${i}" value="${q[2][1]}"> ${esc(q[2][0])}</label>
      </div>
    </div>`).join('');
}
async function calcType(){
  const counts = {S:0,C:0,L:0,D:0,R:0,I:0,G:0,T:0};
  for(let i=0;i<questions.length;i++){
    const selected = document.querySelector(`input[name="q${i}"]:checked`);
    if(!selected){ alert('모든 문항에 답해주세요.'); return; }
    counts[selected.value] += 1;
  }
  const code = `${counts.S>=counts.C?'S':'C'}${counts.L>=counts.D?'L':'D'}${counts.R>=counts.I?'R':'I'}${counts.G>=counts.T?'G':'T'}`;
  const data = await getJSON(`/api/type-result?code=${code}`);
  $('#typeResult').innerHTML = `<div class="panel"><h2>당신의 독서유형: ${data.name} (${data.code})</h2><p>${esc(data.description)}</p><p><b>추천 분야</b>: ${(data.recommended_tags||[]).map(esc).join(', ')}</p></div>`;
  renderBooks(`🧠 ${data.name}에게 맞는 소장도서`, '독서유형 결과에 맞는 실제 소장도서입니다.', data.books);
}

async function init(){
  try{
    const m = await getJSON('/api/meta');
    $('#meta').textContent = `원본 반영 권수: ${m.book_count?.toLocaleString?.() || m.book_count}권 · 기준 파일: ${m.source_file}`;
  }catch(e){}
  renderTypeTest();
  today();
}

$('#searchBtn').addEventListener('click', () => search());
$('#searchInput').addEventListener('keydown', e => { if(e.key === 'Enter') search(); });
document.querySelectorAll('.chip').forEach(b => b.addEventListener('click', () => { $('#searchInput').value = b.textContent; search(b.textContent); }));
$('#todayBtn').addEventListener('click', today);
$('#randomBtn').addEventListener('click', randomBook);
document.querySelectorAll('[data-career]').forEach(b => b.addEventListener('click', () => career(b.dataset.career)));
$('#typeBtn').addEventListener('click', () => { $('#typeTest').classList.toggle('hidden'); $('#typeTest').scrollIntoView({behavior:'smooth'}); });
$('#calcType').addEventListener('click', calcType);
$('#closeModal').addEventListener('click', () => $('#modal').classList.add('hidden'));
$('#modal').addEventListener('click', e => { if(e.target.id === 'modal') $('#modal').classList.add('hidden'); });
init();
