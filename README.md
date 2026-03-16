# sheryloe.github.io

`sheryloe.github.io`는 sheryloe의 공개 저장소와 GitHub Pages를 한 곳에서 모아 보여주는 루트 허브입니다.
포트폴리오 목록만 나열하는 수준을 넘어서, 프로젝트 탐색, 최신 업데이트 확인, RSS/Atom/Sitemap 생성, 중앙 위키 문서 연결까지 담당합니다.

- 사이트: `https://sheryloe.github.io/`
- 목적: 공개 프로젝트 허브, Pages 진입점, 검색 노출용 메타데이터 관리
- 포함 요소: `index.html`, `projects.json`, `rss.xml`, `feed.xml`, `sitemap.xml`, `robots.txt`

## 하는 일

- GitHub 공개 저장소를 읽어 루트 허브 페이지를 생성합니다.
- Pages가 있는 저장소를 우선 노출해 바로 데모 페이지로 이동할 수 있게 합니다.
- 최근 변경 저장소를 날짜 기준으로 정리해 작업 흐름을 보여줍니다.
- 검색 엔진을 위한 RSS, Atom, Sitemap을 함께 유지합니다.
- 중앙 문서 성격의 `wiki/` 폴더에서 전체 저장소 운영 문서를 관리합니다.

## 주요 파일

- `site-config.json`: 사이트 제목, 설명, 강조 저장소, 저장소별 설명 오버라이드
- `generate_site.py`: GitHub API 기준으로 허브 페이지와 피드 파일 생성
- `templates/index.template.html`: 루트 페이지 템플릿
- `projects.json`: 생성된 저장소 메타데이터 캐시
- `wiki/`: 전체 저장소 맵, 날짜별 DO, 서비스 TODO 문서

## 실행 방법

```powershell
python generate_site.py
```

필요하면 아래 명령으로 별도 사이트맵 생성 스크립트도 실행할 수 있습니다.

```powershell
python generate_sitemap.py
```

## 중앙 위키

- `wiki/Home.md`: 전체 개요
- `wiki/Repository-Service-Map.md`: 저장소별 서비스 포지션 정리
- `wiki/Timeline-DO.md`: 커밋 로그 기반 날짜별 완료 작업
- `wiki/Service-TODO.md`: 서비스형 관점의 다음 작업 목록

## 다음 단계

- 루트 허브에서 저장소별 태그 필터와 검색 UX 강화
- 프로젝트별 스크린샷/상태 배지 자동 수집
- 중앙 위키를 루트 허브에서 바로 탐색할 수 있도록 링크 노출 강화
