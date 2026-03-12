# sheryloe.github.io

`sheryloe.github.io`는 sheryloe의 공개 프로젝트를 한곳에 모아 보여주는 GitHub Pages 루트 허브입니다. 루트 사이트, sitemap, RSS, Atom 피드를 자동 생성해서 공개 저장소와 라이브 프로젝트 페이지를 한 번에 관리합니다.

- Site: `https://sheryloe.github.io/`
- Purpose: 공개 저장소 허브, 프로젝트 탐색, 루트 Search Console 대응, feed/sitemap 자동화

## 생성되는 파일

- `index.html`: 루트 허브 랜딩 페이지
- `sitemap.xml`: 루트 도메인과 GitHub Pages 프로젝트 URL 목록
- `rss.xml`: 공개 저장소 업데이트 RSS 피드
- `feed.xml`: 공개 저장소 업데이트 Atom 피드
- `robots.txt`: 검색엔진 크롤링 힌트
- `projects.json`: 저장소 메타데이터 JSON
- `.nojekyll`: 정적 파일 그대로 배포

## 설정 파일

- `site-config.json`: 사이트 제목, 설명, 제외 저장소, 수동 설명 오버라이드, 피드 설정
- `templates/index.template.html`: 루트 랜딩 페이지 템플릿

## 생성 스크립트

```powershell
python generate_site.py
```

호환용으로 아래 명령도 동일하게 동작합니다.

```powershell
python generate_sitemap.py
```

## 자동 갱신

GitHub Actions가 아래 경우에 루트 사이트를 다시 생성합니다.

- `main` 브랜치에서 루트 사이트 소스 파일이 변경될 때
- 6시간마다 스케줄 실행될 때
- 수동 `workflow_dispatch`

워크플로 파일:

- `.github/workflows/site.yml`

## 루트 전략

- Search Console 속성 기준은 `https://sheryloe.github.io/`
- 각 프로젝트 저장소는 자기 Pages 품질과 메타데이터를 유지
- 루트 저장소는 전체 허브, feed, sitemap를 유지
- 수동 설명은 `site-config.json` 오버라이드로 관리하고, 목록/피드는 자동 생성으로 유지
