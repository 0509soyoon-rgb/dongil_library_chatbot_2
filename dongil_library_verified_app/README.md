# 동일여고 AI 도서관 - 원본 검증 버전

이 버전은 업로드된 `동일여고 소장도서 목록(2026.5.21)` 엑셀 원본만 사용합니다.

## 핵심 원칙

- 원본 엑셀에 있는 22,735권만 DB에 저장합니다.
- 책 제목, 저자, 출판사, 청구기호, 등록번호, 소장처는 원본 그대로 표시합니다.
- 엑셀에 없는 책은 추천하지 않습니다.
- 장르, 태그, 난이도, 추천 이유, 탐구주제는 청구기호와 제목 기반 자동 보조 분류입니다.
- 외부 정보는 자동으로 섞지 않습니다. 상세 페이지에서 교보문고 검색 링크만 제공합니다.

## 기능

- 책 제목 정확 검색 우선
- 검색 결과 카드 클릭 → 도서 상세정보
- 오늘의 책 추천
- 운명의 책 뽑기
- 진로/학과별 추천
- 난이도 표시
- 탐구주제 추천
- 비슷한 실제 소장도서 추천
- 16가지 독서 유형 테스트
- Render 배포 설정 포함

## VS Code에서 실행

```bash
python -m pip install -r requirements.txt -i https://pypi.org/simple
python prepare_data.py
python -m uvicorn app.main:app --reload
```

브라우저에서 접속:

```text
http://127.0.0.1:8000
```

## Render 배포 설정

Root Directory를 이 프로젝트 폴더로 지정한 뒤:

Build Command:

```bash
pip install -r requirements.txt && python prepare_data.py
```

Start Command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 업데이트 방법

수정 후:

```bash
git add .
git commit -m "update verified library app"
git push
```

Render가 자동으로 다시 배포합니다.
