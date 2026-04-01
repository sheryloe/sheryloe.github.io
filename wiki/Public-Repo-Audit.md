# Public Repo Audit

이 문서는 공개 저장소를 “배포 가능한 서비스/툴” 수준으로 유지하기 위한 **보안·품질·운영 점검 체크리스트**입니다.  
목표는 1) 민감정보 유출 방지, 2) GitHub Actions 권한 최소화, 3) 의존성/릴리즈 안정성 확보, 4) 공개 문서(README/Pages/wiki) 신뢰도 유지입니다.

---

## 0) 기준(원칙)

- **Secrets는 절대 커밋하지 않는다.** (현재 + 과거 커밋 히스토리 포함)
- Actions는 **최소 권한(least privilege)** + **핀(pin)된 버전**으로만 사용한다.
- 배포/자동 커밋 워크플로우는 **무한 루프를 만들지 않도록** 경로/권한을 제한한다.
- README/Pages/wiki는 **“현재 상태”**를 반영한다. (스냅샷/생성 시각 표기)

---

## 1) 10분 퀵체크(WSL 기준)

아래는 “일단 큰 사고부터 막기”용입니다.

### 1-1. 민감정보/토큰 문자열 탐지

```bash
# WSL에서 실행
# 예: /mnt/d/Donggri_Platform/<repo>
cd /path/to/repo

# 작업트리(현재 파일)에서 빠른 패턴 탐지
git grep -nEI \
  'AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,48}|AIzaSy[A-Za-z0-9_-]{30,}|-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----' \
  -- . || true

# 과거 커밋(히스토리)에서 민감 문자열 탐지(시간이 걸릴 수 있음)
git log -p --all -G 'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_|xox[baprs]-|AIzaSy|PRIVATE KEY' -- . | head -n 200
```

발견 시:
- **즉시 해당 토큰/키를 폐기(revoke/rotate)** 하고,  
- 히스토리에 남아있다면 `git filter-repo` 등으로 **과거 커밋 정리**(rewrite) 후 강제 푸시가 필요합니다.

### 1-2. `.env` / 빌드 산출물 / 키 파일 커밋 여부

```bash
git status -sb
git ls-files | grep -E '(^|/)(\\.env(\\..*)?|id_rsa|id_ed25519|.*\\.p12|.*\\.pem|.*\\.key)$' || true
```

### 1-3. GitHub Actions 권한 최소화(레포 전체)

```bash
# 워크플로우에 permissions가 명시되어 있는지 확인
ls -la .github/workflows
grep -RIn --line-number '^\\s*permissions\\s*:' .github/workflows || true
```

권장:
- 기본은 `contents: read`
- 배포/커밋이 필요한 워크플로우만 `contents: write` 부여

---

## 2) 워크플로우 점검(필수)

### 2-1. Actions 사용 버전 핀(공급망)

- `uses: actions/checkout@v4`처럼 **메이저 고정**은 최소 수준입니다.
- 더 엄격하게는 `@<commit-sha>`로 핀하는 방식을 권장합니다(변경 비용은 증가).

### 2-2. 외부 스크립트/다운로드

- `curl | bash`류는 가급적 피하고, 필요 시 **checksum 검증**을 넣습니다.
- 토큰을 로그로 출력하지 않도록 `set -x` 사용에 주의합니다.

---

## 3) 공개 페이지/문서 신뢰도

- “자동 생성(Generated)” 표기가 있는 문서는 **생성 시각**을 노출해 최신성을 명확히 합니다.
- README에는 최소한 아래 3가지를 유지합니다:
  - 무엇을 하는 저장소인지(1문단)
  - 실행/빌드 방법(최소 커맨드)
  - 배포/페이지 링크(있는 경우)

---

## 4) 감사 로그(템플릿)

아래 템플릿을 복붙해서 레포 이슈/위키에 남기면, 다음 점검이 빨라집니다.

```text
Audit Date: YYYY-MM-DD
Scope: <repo or org>

[Secrets]
- Findings:
- Actions:
- Rotation done: yes/no

[GitHub Actions]
- permissions minimized: yes/no
- uses pinned: yes/no
- risky steps (curl|bash, unverified downloads): none/<list>

[Docs / Pages]
- README up-to-date: yes/no
- Pages links verified: yes/no

Notes:
- ...
```

