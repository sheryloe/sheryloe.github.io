import urllib.request
import json
import os
from datetime import datetime

def generate_sitemap():
    # 1. GitHub 환경변수에서 사용자명 추출
    repository = os.environ.get('GITHUB_REPOSITORY')
    if not repository:
        print("실행 오류: GITHUB_REPOSITORY 환경변수를 찾을 수 없습니다.")
        return
    
    username = repository.split('/')[0]
    root_url = f"https://{username}.github.io"
    
    print(f"작업 시작: {username} 계정의 리포지토리 탐색 중...")

    # 2. GitHub API로 퍼블릭 리포지토리 목록 가져오기 (최대 100개)
    # 깃헙 페이지가 활성화된 것 위주로 확인하기 위해 has_pages 정보가 포함된 API를 사용합니다.
    api_url = f"https://api.github.com/users/{username}/repos?type=public&per_page=100"
    req = urllib.request.Request(api_url)
    req.add_header('User-Agent', 'Python-Sitemap-Generator')

    try:
        with urllib.request.urlopen(req) as response:
            repos = json.loads(response.read().decode())
    except Exception as e:
        print(f"API 요청 실패: {e}")
        return

    # 3. 사이트맵 내용 생성 시작
    now = datetime.now().strftime("%Y-%m-%d")
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # (1) 최상위 루트 도메인 추가 (sheryloe.github.io)
    sitemap_lines.append(f'''  <url>
    <loc>{root_url}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>''')

    # (2) 각 프로젝트 리포지토리 추가
    count = 0
    for repo in repos:
        repo_name = repo['name']
        
        # 본인 계정명 리포지토리는 위에서 루트로 추가했으므로 건너뜁니다.
        if repo_name == f"{username}.github.io":
            continue

        # GitHub Pages가 활성화되어 있는지 확인
        if repo.get('has_pages'):
            last_updated = repo.get('updated_at', now)[:10]
            project_url = f"{root_url}/{repo_name}/"
            
            sitemap_lines.append(f'''  <url>
    <loc>{project_url}</loc>
    <lastmod>{last_updated}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>''')
            count += 1
            print(f"추가됨: /{repo_name}")

    sitemap_lines.append('</urlset>')

    # 4. 파일 쓰기
    with open('sitemap.xml', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sitemap_lines))

    print(f"완료: 총 {count + 1}개의 URL이 sitemap.xml에 기록되었습니다.")

if __name__ == "__main__":
    generate_sitemap()
