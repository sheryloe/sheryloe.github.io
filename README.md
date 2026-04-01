# sheryloe.github.io

`sheryloe.github.io`는 sheryloe의 공개 저장소를 서비스 관점으로 다시 묶어 보여주는 루트 허브이자 중앙 문서 인덱스입니다.
단순 포트폴리오 목록이 아니라 다음 세 가지를 함께 관리합니다.

- 라이브 GitHub Pages와 공개 저장소 탐색
- 중앙 위키와 저장소별 `wiki/` 진입점
- RSS, Atom, sitemap, 구조화 데이터 같은 검색 노출 메타데이터

## 생성 구조

- `generate_site.py`: GitHub API를 읽어 루트 허브, 중앙 위키 랜딩, 개별 HTML 문서, 피드 파일을 생성합니다.
- `site-config.json`: 영문/국문 설명, 포트폴리오 트랙, 위키 문서 카드, 저장소별 설명 오버라이드를 관리합니다.
- `templates/index.template.html`: 루트 허브 템플릿
- `templates/wiki.template.html`: 중앙 위키 랜딩 템플릿
- `templates/wiki-doc.template.html`: `wiki/*.md`를 퍼블리시하는 HTML 문서 템플릿
- `projects.json`: 현재 공개 저장소 메타데이터 캐시
- `wiki/*.md`: 서비스 맵, Timeline DO, Service TODO 등 중앙 문서

## 생성 결과물

- `index.html`
- `wiki/index.html`
- `wiki/*.html`
- `projects.json`
- `rss.xml`
- `feed.xml`
- `sitemap.xml`
- `robots.txt`
- `site.webmanifest`
- `.nojekyll`

## 실행 방법

```powershell
python generate_site.py
```

호환용으로 기존 명령도 계속 유지됩니다.

```powershell
python generate_sitemap.py
```

## 미리보기 캡처

라이브 Pages 썸네일과 루트 허브 소셜 이미지는 아래 순서로 다시 만들 수 있습니다.

```powershell
python generate_site.py
powershell -ExecutionPolicy Bypass -File scripts/capture_previews.ps1
python generate_site.py
```

첫 번째 생성은 최신 공개 저장소 목록과 HTML을 만들고, 두 번째 명령은 각 라이브 페이지와 루트 허브를 스크린샷으로 캡처합니다.
마지막 생성은 새 썸네일을 포함한 최종 `index.html`, `wiki/index.html`, `wiki/*.html`, `projects.json`, `sitemap.xml`을 다시 빌드합니다.

## 이번 리디자인 포인트

- 공개 저장소를 `AI Automation`, `Service Products`, `Desktop Utilities`, `Platform Docs` 네 축으로 재구성
- 홈은 `Overview / Projects / Docs / Activity` 탭 중심의 compact 허브로 구성
- 중앙 위키 문서를 `wiki/*.html`로 퍼블리시해 완성형 문서처럼 연결
- shadcn/ui 스타일의 카드, 탭, 시트, 배지 패턴과 Fuse.js, Iconify를 조합해 탐색성과 가독성을 함께 강화

## 자동 갱신

GitHub Actions는 `main` 브랜치에서 생성기, 설정, 템플릿이 바뀌거나 스케줄이 돌 때 루트 허브를 다시 생성합니다.
자동 커밋 대상에는 `wiki/index.html`과 `wiki/*.html`도 포함됩니다.
