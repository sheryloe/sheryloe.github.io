# Repository Service Map

## 서비스형 프로젝트

| 저장소 | 현재 역할 | 서비스 설명 | 다음 개선 포인트 |
| --- | --- | --- | --- |
| `Automethemoney` | 자동매매 운영 콘솔 | 전략, 일별 손익, 시그널, Supabase 상태를 함께 보는 트레이딩 서비스 | 모델 비교, 리스크 가드, 손익 리포트 자동화 |
| `donggri_gagyeobu` | 개인 재무 서비스 | 자산, 카드 결제 예정, 예산, 소비 흐름을 관리하는 가계부 서비스 | 예산 알림, 가족 공유 모드, 데이터 검증 자동화 |
| `BloggerGent` | 멀티 채널 발행 스튜디오 | 여러 Blogger 계열 블로그를 운영하는 AI 발행 허브 | 발행 승인 단계, 채널별 워크플로 분리, SEO 검수 강화 |
| `BloManagent` | 블로그 분석 대시보드 | URL 수집과 비교 리포트로 블로그 성과를 진단하는 서비스 | 비동기 수집, 리포트 공유, 등급 근거 시각화 |

## 운영 자동화와 AI 백엔드

| 저장소 | 현재 역할 | 서비스 설명 | 다음 개선 포인트 |
| --- | --- | --- | --- |
| `AI_BISEO` | 개인 AI 운영 루프 | AI 비서 응답, Notion 로그, n8n 연동, 블로그 자동화를 묶는 운영 서비스 | 권한 분리, 운영 알림, 버전 비교 |
| `AI_Writer_TISTORY` | 티스토리 발행 백엔드 | AI 초안 생성부터 발행 전 검수까지 다루는 티스토리 운영 백엔드 | 발행 승인 단계, SEO 체크, 실패 복구 로그 |
| `Vibe_Cowork_Thinking` | AI 협업 실험 워크스페이스 | Runner와 Orchestrator 구조로 작업 흐름을 추적하는 실험 환경 | diff 뷰, 권한 모델, 에이전트 비교 리포트 |

## 도구형 유틸리티

| 저장소 | 현재 역할 | 서비스 설명 | 다음 개선 포인트 |
| --- | --- | --- | --- |
| `Favorit` | Windows 런처 위젯 | 파일, 폴더, URL을 빠르게 실행하는 데스크톱 위젯 | Windows 위젯 느낌 UI, 검색, 그룹 정렬 |
| `grid-crop-image` | 이미지 작업 유틸리티 | 스크린샷 분할과 잘라내기, 저장 규칙을 관리하는 도구 | 배치 처리, OCR 보조, Undo/Redo |

## 플랫폼과 허브

| 저장소 | 현재 역할 | 서비스 설명 | 다음 개선 포인트 |
| --- | --- | --- | --- |
| `donggeuri-cloudflare-blog` | Cloudflare 블로그 플랫폼 | Public, Admin, API를 분리한 블로그 워크스페이스 | 역할 분리, 미리보기, SEO와 RSS 완성 |
| `sheryloe.github.io` | 공개 루트 허브 | 공개 저장소, Pages, RSS, sitemap, wiki를 묶는 허브 | 중앙 위키 노출, 상태 카드 자동화, 검색성 강화 |

## 메모

- `Automethemoney`와 `donggri_gagyeobu`는 가장 먼저 서비스형 구조로 고도화할 가치가 큽니다.
- `Favorit`은 오픈소스 UI 라이브러리를 활용해 Windows 위젯 느낌을 강하게 살리면 완성도가 크게 올라갑니다.
- `donggeuri-cloudflare-blog`는 구조가 이미 좋아서 CMS와 운영 UX를 붙이면 제품 레벨에 가까워질 수 있습니다.
