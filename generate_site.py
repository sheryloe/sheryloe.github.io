from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "site-config.json"
HOME_TEMPLATE_PATH = ROOT / "templates" / "index.template.html"
WIKI_TEMPLATE_PATH = ROOT / "templates" / "wiki.template.html"
WIKI_DOC_TEMPLATE_PATH = ROOT / "templates" / "wiki-doc.template.html"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def github_headers() -> dict[str, str]:
    headers = {
        "User-Agent": "sheryloe-root-site-generator",
        "Accept": "application/vnd.github+json",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_public_repositories(username: str) -> list[dict[str, Any]]:
    headers = github_headers()
    repositories: list[dict[str, Any]] = []
    page = 1

    while True:
        params = urllib.parse.urlencode(
            {
                "type": "public",
                "sort": "updated",
                "per_page": 100,
                "page": page,
            }
        )
        url = f"https://api.github.com/users/{username}/repos?{params}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            batch = json.loads(response.read().decode("utf-8"))
        if not batch:
            break
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return repositories


def parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def quote_repo_path(name: str) -> str:
    return urllib.parse.quote(name, safe="")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def relative_asset_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def absolute_asset_url(config: dict[str, Any], path: str) -> str:
    return urllib.parse.urljoin(str(config["site_url"]), relative_asset_path(path))


def render_google_analytics_snippet(config: dict[str, Any]) -> str:
    analytics = config.get("analytics", {})
    if not isinstance(analytics, dict):
        return ""

    measurement_id = str(analytics.get("google_measurement_id", "")).strip()
    if not measurement_id:
        return ""

    escaped_id = html.escape(measurement_id, quote=True)
    return (
        f'  <script async src="https://www.googletagmanager.com/gtag/js?id={escaped_id}"></script>\n'
        "  <script>\n"
        "    window.dataLayer = window.dataLayer || [];\n"
        "    function gtag(){dataLayer.push(arguments);}\n"
        "    gtag('js', new Date());\n"
        f"    gtag('config', '{escaped_id}');\n"
        "  </script>"
    )


def default_category(name: str, language: str) -> str:
    labels = {
        "AI_BISEO": "Automation Ops",
        "AI_Writer_TISTORY": "Publishing Workflow",
        "Automethemoney": "Trading Ops",
        "BloggerGent": "Publishing Studio",
        "BloManagent": "Analytics Dashboard",
        "DonggriWorld": "Service Seed",
        "cloudflare-blog": "Cloud Platform",
        "donggri_gagyeobu": "Local Finance",
        "Favorit": "Desktop Utility",
        "grid-crop-image": "Image Workflow",
        "Vibe_Cowork_Thinking": "AI Workflow Lab",
    }
    return labels.get(name, language)


def default_track(name: str) -> str:
    labels = {
        "AI_BISEO": "ai-automation",
        "AI_Writer_TISTORY": "ai-automation",
        "Automethemoney": "service-products",
        "BloggerGent": "ai-automation",
        "BloManagent": "service-products",
        "DonggriWorld": "service-products",
        "cloudflare-blog": "platform-docs",
        "donggri_gagyeobu": "service-products",
        "Favorit": "desktop-utilities",
        "grid-crop-image": "desktop-utilities",
        "Vibe_Cowork_Thinking": "ai-automation",
    }
    return labels.get(name, "platform-docs")


def default_subtitle(name: str, description: str, language: str) -> str:
    subtitles = {
        "AI_BISEO": "AI 비서와 운영 자동화를 묶는 개인 Ops 루프",
        "AI_Writer_TISTORY": "AI 초안 생성부터 발행 전 검수까지",
        "Automethemoney": "전략과 리스크를 잇는 자동매매 콘솔",
        "BloggerGent": "멀티 채널 발행을 위한 AI 스튜디오",
        "BloManagent": "블로그 수집과 리포트를 잇는 분석 대시보드",
        "DonggriWorld": "서비스 아이디어를 제품 요구사항으로 구체화하는 시드 저장소",
        "cloudflare-blog": "Public, Admin, API를 분리한 플랫폼",
        "donggri_gagyeobu": "브라우저 기반 개인 가계부 서비스",
        "Favorit": "실행 즐겨찾기를 위젯처럼 여는 런처",
        "grid-crop-image": "스크린샷 자르기와 분할 저장 유틸리티",
        "Vibe_Cowork_Thinking": "Runner와 Orchestrator를 분리한 협업 실험실",
    }
    return subtitles.get(name, description or language)


def default_stage(has_pages: bool) -> str:
    return "Operate" if has_pages else "Build"


def default_accent(track: str) -> str:
    labels = {
        "ai-automation": "teal",
        "service-products": "amber",
        "desktop-utilities": "ocean",
        "platform-docs": "slate",
    }
    return labels.get(track, "slate")


def track_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(track["slug"]): track for track in config.get("portfolio_tracks", [])}


def wiki_documents(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(document) for document in config.get("wiki_documents", [])]


def generated_wiki_documents(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(document)
        for document in wiki_documents(config)
        if document.get("source_path") and document.get("output_path")
    ]


def wiki_doc_lookup(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for document in generated_wiki_documents(config):
        source_path = str(document["source_path"]).replace("\\", "/")
        output_path = str(document["output_path"]).replace("\\", "/")
        mapping[source_path] = document
        mapping[Path(source_path).name] = document
        mapping[output_path] = document
        mapping[Path(output_path).name] = document
    return mapping


def repository_search_text(repository: dict[str, Any]) -> str:
    parts = [
        repository["name"],
        repository["description"],
        repository["subtitle"],
        repository["category"],
        repository["track_title"],
        repository["language"],
        repository["status"],
        repository["stage"],
        repository["audience"],
        repository["next_focus"],
        " ".join(repository["topics"]),
    ]
    return " ".join(part.lower() for part in parts if part)


def normalize_repositories(config: dict[str, Any], repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    excluded = set(config.get("exclude_repositories", []))
    featured = set(config.get("featured_repositories", []))
    overrides = dict(config.get("repository_overrides", {}))
    tracks = track_map(config)
    site_url = str(config["site_url"])
    normalized: list[dict[str, Any]] = []

    for repo in repositories:
        name = str(repo["name"])
        if name in excluded:
            continue
        if repo.get("private") or repo.get("archived"):
            continue

        pushed_at = parse_dt(repo.get("pushed_at") or repo.get("updated_at") or repo.get("created_at"))
        updated_at = parse_dt(repo.get("updated_at") or repo.get("created_at"))
        created_at = parse_dt(repo.get("created_at"))
        override = dict(overrides.get(name, {}))

        has_pages = bool(repo.get("has_pages"))
        description = str(override.get("description") or (repo.get("description") or "").strip())
        language = str(repo.get("language") or "Unknown")
        category = str(override.get("category") or default_category(name, language))
        subtitle = str(override.get("subtitle") or default_subtitle(name, description, language))
        track = str(override.get("track") or default_track(name))
        track_title = str(tracks.get(track, {}).get("title", track.replace("-", " ").title()))
        accent = str(override.get("accent") or default_accent(track))
        homepage = str(override.get("live_url") or (repo.get("homepage") or "").strip())
        derived_page_url = f"{site_url}{quote_repo_path(name)}/"
        live_url = homepage or derived_page_url if has_pages else ""
        topics_source = override.get("repo_topics") or repo.get("topics") or []
        topics = [str(topic) for topic in topics_source if topic]
        preview_path = relative_asset_path(
            str(override.get("preview_image") or f"assets/previews/{slugify(name)}.png")
        )
        default_branch = str(repo.get("default_branch") or "main")
        preview_alt = str(override.get("preview_alt") or f"{name} 프로젝트 미리보기")
        wiki_url = str(override.get("wiki_url") or f"{repo['html_url']}/tree/{default_branch}/wiki")
        status = str(override.get("status") or ("Live Pages" if has_pages else "Repository"))
        stage = str(override.get("stage") or default_stage(has_pages))
        audience = str(override.get("audience") or "사용자와 운영자를 위한 공개 저장소")
        next_focus = str(override.get("next_focus") or "다음 개선 포인트를 문서화 중입니다.")

        normalized.append(
            {
                "id": slugify(name),
                "name": name,
                "description": description,
                "subtitle": subtitle,
                "category": category,
                "track": track,
                "track_title": track_title,
                "repo_url": str(repo["html_url"]),
                "live_url": live_url,
                "pages_url": derived_page_url if has_pages else "",
                "wiki_url": wiki_url,
                "language": language,
                "topics": topics,
                "has_pages": has_pages,
                "availability": "live" if has_pages else "repo",
                "availability_label": "Live Pages" if has_pages else "Repository",
                "featured": bool(override.get("featured", name in featured)),
                "created_at": created_at,
                "updated_at": updated_at,
                "sort_at": pushed_at,
                "sort_label": pushed_at.astimezone(timezone.utc).strftime("%Y-%m-%d"),
                "updated_label": updated_at.astimezone(timezone.utc).strftime("%Y-%m-%d"),
                "stars": int(repo.get("stargazers_count") or 0),
                "size": int(repo.get("size") or 0),
                "default_branch": default_branch,
                "status": status,
                "stage": stage,
                "audience": audience,
                "next_focus": next_focus,
                "accent": accent,
                "preview_path": preview_path,
                "preview_url": absolute_asset_url(config, preview_path),
                "preview_alt": preview_alt,
                "has_preview": (ROOT / preview_path).exists(),
            }
        )

    normalized.sort(key=lambda item: item["sort_at"], reverse=True)

    for repository in normalized:
        repository["search_text"] = repository_search_text(repository)

    return normalized


def format_title_html(text: str) -> str:
    lines = [html.escape(line.strip()) for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    if len(lines) == 1:
        return lines[0]
    return "".join(f'<span class="block">{line}</span>' for line in lines)


def accent_class(repository: dict[str, Any]) -> str:
    return f"accent-{slugify(repository['accent'])}"


def render_tags(repository: dict[str, Any], max_topics: int = 3) -> str:
    tags = [
        f'<span class="meta-pill">{html.escape(repository["language"])}</span>',
        f'<span class="meta-pill">{html.escape(repository["stage"])}</span>',
    ]
    if repository["has_pages"]:
        tags.append('<span class="meta-pill">Live</span>')
    for topic in repository["topics"][:max_topics]:
        tags.append(f'<span class="meta-pill">{html.escape(topic)}</span>')
    return "".join(tags)


def render_preview_media(repository: dict[str, Any], figure_class: str, *, eager: bool = False) -> str:
    if repository["has_preview"]:
        loading = "eager" if eager else "lazy"
        fetchpriority = ' fetchpriority="high"' if eager else ""
        return (
            f'<figure class="{figure_class}">'
            f'<img src="{html.escape(repository["preview_path"])}" '
            f'alt="{html.escape(repository["preview_alt"])}" '
            f'width="1280" height="900" loading="{loading}" decoding="async"{fetchpriority}>'
            "</figure>"
        )

    return (
        f'<figure class="{figure_class} preview-empty">'
        '<div class="preview-empty-inner">'
        '<iconify-icon icon="solar:window-frame-linear"></iconify-icon>'
        f'<span>{html.escape(repository["name"])}</span>'
        "</div>"
        "</figure>"
    )


def primary_link_label(repository: dict[str, Any]) -> str:
    return "Live Page" if repository["has_pages"] else "Repository"


def render_action_group(repository: dict[str, Any], *, primary_class: str = "button button-primary") -> str:
    primary_href = repository["live_url"] or repository["repo_url"]
    actions = [
        f'<a class="{primary_class}" href="{html.escape(primary_href)}">{primary_link_label(repository)}</a>',
        f'<a class="button" href="{html.escape(repository["wiki_url"])}">Wiki</a>',
        f'<a class="button" href="{html.escape(repository["repo_url"])}">GitHub</a>',
    ]
    return "".join(actions)


def featured_card_class(index: int) -> str:
    if index == 0:
        return "feature-card feature-card--xl"
    if index == 1:
        return "feature-card feature-card--wide"
    return "feature-card"


def render_featured_card(repository: dict[str, Any], index: int) -> str:
    preview = render_preview_media(repository, "feature-media", eager=index < 2)
    return f"""            <article class="{featured_card_class(index)} {accent_class(repository)} reveal">
              <div class="feature-shell">
                <a class="feature-link" href="{html.escape(repository["live_url"] or repository["repo_url"])}" aria-label="{html.escape(repository["name"])} 열기">
                  {preview}
                </a>
                <div class="feature-body">
                  <div class="feature-head">
                    <div>
                      <p class="eyebrow eyebrow-small">{html.escape(repository["category"])}</p>
                      <h3>{html.escape(repository["name"])}</h3>
                    </div>
                    <span class="status-pill">{html.escape(repository["status"])}</span>
                  </div>
                  <p class="feature-subtitle">{html.escape(repository["subtitle"])}</p>
                  <p class="feature-desc">{html.escape(repository["description"])}</p>
                  <div class="meta-row">
                    {render_tags(repository, max_topics=2)}
                  </div>
                  <dl class="detail-grid">
                    <div>
                      <dt>Audience</dt>
                      <dd>{html.escape(repository["audience"])}</dd>
                    </div>
                    <div>
                      <dt>Next Focus</dt>
                      <dd>{html.escape(repository["next_focus"])}</dd>
                    </div>
                  </dl>
                  <div class="button-row">
                    {render_action_group(repository)}
                  </div>
                </div>
              </div>
            </article>"""


def render_track_card(track: dict[str, Any], repositories_by_name: dict[str, dict[str, Any]]) -> str:
    matched = [repositories_by_name[name] for name in track.get("repositories", []) if name in repositories_by_name]
    repo_count = len(matched)
    live_count = sum(1 for repository in matched if repository["has_pages"])
    repo_names = " · ".join(html.escape(repository["name"]) for repository in matched[:4]) or "문서와 루트 허브"
    accent = slugify(str(track.get("accent", "slate")))
    return f"""            <article class="track-card accent-{accent} reveal">
              <div class="track-copy">
                <p class="eyebrow eyebrow-small">{html.escape(track["title"])}</p>
                <h3>{html.escape(track["title"])}</h3>
                <p>{html.escape(str(track["summary"]))}</p>
              </div>
              <div class="track-metrics">
                <strong>{repo_count}</strong>
                <span>tracked repos · {live_count} live pages</span>
              </div>
              <p class="track-outcome">{html.escape(str(track["outcome"]))}</p>
              <p class="track-repos">{repo_names}</p>
              <button class="button button-ghost" type="button" data-track-jump="{html.escape(str(track["slug"]))}">
                Explorer에서 보기
              </button>
            </article>"""


def render_document_card(document: dict[str, Any]) -> str:
    buttons = [
        f'<a class="button button-primary" href="{html.escape(str(document["href"]))}">{html.escape(str(document["label"]))}</a>'
    ]
    if document.get("secondary_href") and document.get("secondary_label"):
        buttons.append(
            f'<a class="button" href="{html.escape(str(document["secondary_href"]))}">'
            f'{html.escape(str(document["secondary_label"]))}</a>'
        )
    return f"""            <article class="doc-card reveal">
              <p class="eyebrow eyebrow-small">{html.escape(str(document.get("badge", "Document")))}</p>
              <h3>{html.escape(str(document["title"]))}</h3>
              <p>{html.escape(str(document["summary"]))}</p>
              <div class="button-row">
                {' '.join(buttons)}
              </div>
            </article>"""


def render_wiki_link(repository: dict[str, Any]) -> str:
    return f"""              <a class="wiki-link" href="{html.escape(repository["wiki_url"])}">
                <div>
                  <strong>{html.escape(repository["name"])}</strong>
                  <span>{html.escape(repository["track_title"])} · {html.escape(repository["stage"])}</span>
                </div>
                <iconify-icon icon="solar:arrow-right-up-linear"></iconify-icon>
              </a>"""


def render_project_card(repository: dict[str, Any]) -> str:
    preview = render_preview_media(repository, "project-media")
    primary_href = repository["live_url"] or repository["repo_url"]
    primary_label = primary_link_label(repository)
    return f"""            <article class="project-row reveal" data-project-card data-id="{html.escape(repository["id"])}" data-track="{html.escape(repository["track"])}" data-availability="{html.escape(repository["availability"])}">
              <div class="project-row-main">
                <a class="project-link" href="{html.escape(primary_href)}" aria-label="{html.escape(repository["name"])} 열기">
                  {preview}
                </a>
                <div class="project-row-copy">
                  <div class="project-row-head">
                    <div>
                      <strong>{html.escape(repository["name"])}</strong>
                      <p>{html.escape(repository["subtitle"])}</p>
                    </div>
                    <span class="status-pill">{html.escape(repository["availability_label"])}</span>
                  </div>
                  <div class="meta-row">
                    <span class="meta-pill">{html.escape(repository["track_title"])}</span>
                    {render_tags(repository, max_topics=2)}
                  </div>
                </div>
              </div>
              <div class="project-row-side">
                <p class="project-row-next">{html.escape(repository["next_focus"])}</p>
                <div class="project-row-actions">
                  <button class="button button-ghost" type="button" data-open-project="{html.escape(repository["id"])}">Detail</button>
                  <a class="button" href="{html.escape(repository["wiki_url"])}">Wiki</a>
                  <a class="button button-primary" href="{html.escape(primary_href)}">{primary_label}</a>
                </div>
              </div>
            </article>"""


def render_recent_row(repository: dict[str, Any]) -> str:
    primary_href = repository["live_url"] or repository["repo_url"]
    primary_label = primary_link_label(repository)
    return f"""            <article class="recent-row reveal">
              <div class="recent-head">
                <div class="recent-main">
                  <strong>{html.escape(repository["name"])}</strong>
                  <span>{html.escape(repository["category"])} · {html.escape(repository["track_title"])}</span>
                </div>
                <time class="recent-date" datetime="{repository["sort_at"].date().isoformat()}">{repository["sort_label"]}</time>
              </div>
              <p class="recent-note">{html.escape(repository["next_focus"])}</p>
              <div class="recent-actions">
                <a class="button button-primary" href="{html.escape(primary_href)}">{primary_label}</a>
                <a class="button" href="{html.escape(repository["wiki_url"])}">Wiki</a>
              </div>
            </article>"""


def render_timeline_item(item: dict[str, Any]) -> str:
    highlights = "".join(f"<li>{html.escape(str(entry))}</li>" for entry in item.get("highlights", []))
    timeline_id = slugify(str(item["date"]) + "-" + str(item["title"]))
    return f"""            <article class="timeline-card reveal">
              <button class="accordion-trigger" type="button" aria-expanded="false" aria-controls="panel-{timeline_id}">
                <div class="accordion-copy">
                  <span class="timeline-date">{html.escape(str(item["date"]))}</span>
                  <strong>{html.escape(str(item["title"]))}</strong>
                </div>
                <span class="accordion-icon">+</span>
              </button>
              <div class="accordion-panel" id="panel-{timeline_id}" hidden>
                <p>{html.escape(str(item["summary"]))}</p>
                <ul class="timeline-points">{highlights}</ul>
              </div>
            </article>"""


def render_oss_card(tool: dict[str, Any]) -> str:
    return f"""            <article class="stack-card reveal">
              <strong>{html.escape(str(tool["name"]))}</strong>
              <p>{html.escape(str(tool["summary"]))}</p>
            </article>"""


def render_focus_items(items: list[str]) -> str:
    return "".join(f"                <li>{html.escape(item)}</li>" for item in items)


def render_filter_buttons(config: dict[str, Any]) -> str:
    buttons = ['<button class="filter-chip is-active" type="button" data-track-filter="all">전체</button>']
    for track in config.get("portfolio_tracks", []):
        buttons.append(
            f'<button class="filter-chip" type="button" data-track-filter="{html.escape(str(track["slug"]))}">'
            f'{html.escape(str(track["title"]))}</button>'
        )
    return "\n".join(f"              {button}" for button in buttons)


def render_track_legend(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    counts = Counter(repository["track"] for repository in repositories)
    cards = []
    for track in config.get("portfolio_tracks", []):
        slug = str(track["slug"])
        cards.append(
            f"""                <article class="legend-item accent-{slugify(str(track.get("accent", "slate")))}">
                  <strong>{counts.get(slug, 0)}</strong>
                  <span>{html.escape(str(track["title"]))}</span>
                </article>"""
        )
    return "\n".join(cards)


def build_track_chart_data(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    color_map = {
        "teal": "#1f8a72",
        "amber": "#d88c3a",
        "ocean": "#3a6fd8",
        "slate": "#556271",
        "rose": "#d46363",
    }
    counts = Counter(repository["track"] for repository in repositories)
    labels: list[str] = []
    values: list[int] = []
    colors: list[str] = []
    for track in config.get("portfolio_tracks", []):
        slug = str(track["slug"])
        labels.append(str(track["title"]))
        values.append(counts.get(slug, 0))
        colors.append(color_map.get(str(track.get("accent", "slate")), "#556271"))
    payload = {
        "labels": labels,
        "datasets": [
            {
                "label": "Tracked repositories",
                "data": values,
                "backgroundColor": colors,
                "borderColor": "#f4ede4",
                "borderWidth": 3,
                "hoverOffset": 6,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def build_schema(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    max_schema_entries = int(config.get("max_schema_entries", 20))
    social_image = dict(config.get("social_image", {}))
    social_image_url = absolute_asset_url(config, str(social_image.get("path", "assets/meta/root-hub-social.png")))

    item_list: list[dict[str, Any]] = []
    for position, repository in enumerate(repositories[:max_schema_entries], start=1):
        entry: dict[str, Any] = {
            "@type": "ListItem",
            "position": position,
            "name": repository["name"],
            "url": repository["live_url"] or repository["repo_url"],
            "description": repository["description"],
        }
        if repository["has_preview"]:
            entry["image"] = repository["preview_url"]
        item_list.append(entry)

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": str(config["site_name"]),
                "url": str(config["site_url"]),
                "description": str(config["description"]),
            },
            {
                "@type": "CollectionPage",
                "name": str(config["site_title"]),
                "url": str(config["site_url"]),
                "description": str(config["description"]),
                "image": social_image_url,
            },
            {
                "@type": "Person",
                "name": str(config["author_name"]),
                "url": str(config["github_profile"]),
                "sameAs": [str(config["github_profile"])],
            },
            {
                "@type": "ItemList",
                "name": "Public repositories by sheryloe",
                "itemListElement": item_list,
            },
        ],
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


def project_search_index(repositories: list[dict[str, Any]]) -> str:
    payload = [
        {
            "id": repository["id"],
            "name": repository["name"],
            "subtitle": repository["subtitle"],
            "description": repository["description"],
            "category": repository["category"],
            "track": repository["track"],
            "track_title": repository["track_title"],
            "language": repository["language"],
            "topics": repository["topics"],
            "stage": repository["stage"],
            "status": repository["status"],
            "audience": repository["audience"],
            "next_focus": repository["next_focus"],
            "availability": repository["availability"],
            "repo_url": repository["repo_url"],
            "live_url": repository["live_url"],
            "wiki_url": repository["wiki_url"],
            "preview_path": repository["preview_path"] if repository["has_preview"] else "",
            "preview_alt": repository["preview_alt"],
        }
        for repository in repositories
    ]
    return json.dumps(payload, ensure_ascii=False)


TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")
INLINE_MARKDOWN_RE = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*")


def split_markdown_table_row(line: str) -> list[str]:
    row = line.strip().strip("|")
    return [cell.strip() for cell in row.split("|")]


def relative_doc_href(from_output: str, to_output: str) -> str:
    return os.path.relpath(to_output, start=str(Path(from_output).parent)).replace("\\", "/")


def resolve_markdown_href(href: str, document: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> str:
    if not href or href.startswith(("http://", "https://", "mailto:", "#")):
        return href

    path_part, _, anchor = href.partition("#")
    path_value = path_part.strip()
    if not path_value:
        return f"#{anchor}" if anchor else href

    normalized = path_value.replace("\\", "/")
    if not normalized.startswith("/"):
        source_parent = Path(str(document["source_path"])).parent
        normalized = (source_parent / normalized).as_posix()
    else:
        normalized = normalized.lstrip("/")

    target = lookup.get(normalized) or lookup.get(Path(normalized).name)
    if target:
        resolved = relative_doc_href(str(document["output_path"]), str(target["output_path"]))
        return f"{resolved}#{anchor}" if anchor else resolved

    return href


def render_inline_markdown(text: str, document: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> str:
    chunks: list[str] = []
    cursor = 0
    for match in INLINE_MARKDOWN_RE.finditer(text):
        chunks.append(html.escape(text[cursor:match.start()]))
        code_text, link_text, link_href, bold_text = match.groups()
        if code_text is not None:
            chunks.append(f"<code>{html.escape(code_text)}</code>")
        elif link_text is not None and link_href is not None:
            resolved = resolve_markdown_href(link_href, document, lookup)
            chunks.append(f'<a href="{html.escape(resolved)}">{html.escape(link_text)}</a>')
        elif bold_text is not None:
            chunks.append(f"<strong>{html.escape(bold_text)}</strong>")
        cursor = match.end()
    chunks.append(html.escape(text[cursor:]))
    return "".join(chunks)


def render_markdown_document(markdown_text: str, document: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> str:
    lines = markdown_text.splitlines()
    blocks: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            if level == 1 and not blocks and heading_match.group(2).strip() == str(document["title"]).strip():
                index += 1
                continue
            blocks.append(f"<h{level}>{render_inline_markdown(heading_match.group(2), document, lookup)}</h{level}>")
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and TABLE_SEPARATOR_RE.match(lines[index + 1].strip()):
            header_cells = split_markdown_table_row(lines[index])
            table_rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_rows.append(split_markdown_table_row(lines[index]))
                index += 1

            header_html = "".join(
                f"<th>{render_inline_markdown(cell, document, lookup)}</th>" for cell in header_cells
            )
            row_html = "".join(
                "<tr>" + "".join(
                    f"<td>{render_inline_markdown(cell, document, lookup)}</td>" for cell in row
                ) + "</tr>"
                for row in table_rows
            )
            blocks.append(
                '<div class="doc-table-wrap"><table><thead><tr>'
                + header_html
                + "</tr></thead><tbody>"
                + row_html
                + "</tbody></table></div>"
            )
            continue

        if stripped.startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                item_text = lines[index].strip()[2:].strip()
                items.append(f"<li>{render_inline_markdown(item_text, document, lookup)}</li>")
                index += 1
            blocks.append("<ul>" + "".join(items) + "</ul>")
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            probe = lines[index].strip()
            if not probe:
                break
            if probe.startswith("- ") or probe.startswith("|") or re.match(r"^(#{1,6})\s+(.+)$", probe):
                break
            paragraph_lines.append(probe)
            index += 1
        blocks.append(
            "<p>" + render_inline_markdown(" ".join(paragraph_lines), document, lookup) + "</p>"
        )

    return "\n".join(blocks)


def render_wiki_doc_nav(config: dict[str, Any], active_document: dict[str, Any]) -> str:
    entries = [
        {
            "title": "Central Wiki",
            "href": "./",
            "active": False,
        }
    ]
    for document in generated_wiki_documents(config):
        entries.append(
            {
                "title": str(document["title"]),
                "href": relative_doc_href(str(active_document["output_path"]), str(document["output_path"])),
                "active": str(document["output_path"]) == str(active_document["output_path"]),
            }
        )

    return "\n".join(
        f'              <a class="doc-nav-link{" is-active" if entry["active"] else ""}" href="{html.escape(entry["href"])}">{html.escape(entry["title"])}</a>'
        for entry in entries
    )


def render_wiki_doc_html(config: dict[str, Any], document: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    template = WIKI_DOC_TEMPLATE_PATH.read_text(encoding="utf-8")
    lookup = wiki_doc_lookup(config)
    source_path = ROOT / str(document["source_path"])
    markdown_text = source_path.read_text(encoding="utf-8")
    rendered_markdown = render_markdown_document(markdown_text, document, lookup)
    generated_at = datetime.now(timezone.utc)
    social_image = dict(config.get("social_image", {}))
    social_image_path = relative_asset_path(str(social_image.get("path", "assets/meta/root-hub-social.png")))
    output_path = str(document["output_path"]).replace("\\", "/")
    doc_canonical_url = urllib.parse.urljoin(str(config["site_url"]), output_path)
    doc_source_url = (
        str(config["wiki_repo_url"]).rstrip("/") + "/" + urllib.parse.quote(Path(str(document["source_path"])).name)
    )

    replacements = {
        "__SITE_NAME__": html.escape(str(config["site_name"])),
        "__SITE_URL__": html.escape(str(config["site_url"])),
        "__SITE_TITLE__": html.escape(str(config["site_title"])),
        "__DESCRIPTION__": html.escape(str(config["description"])),
        "__GOOGLE_ANALYTICS_SNIPPET__": render_google_analytics_snippet(config),
        "__DOC_TITLE__": html.escape(str(document["title"])),
        "__DOC_BADGE__": html.escape(str(document.get("badge", "Document"))),
        "__DOC_SUMMARY__": html.escape(str(document.get("summary", ""))),
        "__DOC_CANONICAL_URL__": html.escape(doc_canonical_url),
        "__DOC_SOURCE_URL__": html.escape(doc_source_url),
        "__DOC_CONTENT__": rendered_markdown,
        "__DOC_NAV__": render_wiki_doc_nav(config, document),
        "__GENERATED_LABEL__": generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "__GITHUB_PROFILE__": html.escape(str(config["github_profile"])),
        "__WIKI_REPO_URL__": html.escape(str(config["wiki_repo_url"])),
        "__PUBLIC_REPO_COUNT__": str(len(repositories)),
        "__SOCIAL_IMAGE_URL__": html.escape(absolute_asset_url(config, social_image_path)),
        "__SOCIAL_IMAGE_ALT__": html.escape(str(social_image.get("alt", "Sheryloe Projects 대표 이미지"))),
    }

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def render_index_html(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    template = HOME_TEMPLATE_PATH.read_text(encoding="utf-8")
    tracks = config.get("portfolio_tracks", [])
    hero = dict(config.get("hero", {}))
    live_repositories = [repo for repo in repositories if repo["has_pages"]]
    featured_order = {name: index for index, name in enumerate(config.get("featured_repositories", []))}
    featured_live = sorted(
        [repo for repo in live_repositories if repo["name"] in featured_order],
        key=lambda repo: featured_order[repo["name"]],
    )[: min(5, len(live_repositories))]
    if len(featured_live) < min(5, len(live_repositories)):
        used = {repo["name"] for repo in featured_live}
        for repository in live_repositories:
            if repository["name"] in used:
                continue
            featured_live.append(repository)
            used.add(repository["name"])
            if len(featured_live) == min(5, len(live_repositories)):
                break

    generated_at = datetime.now(timezone.utc)
    latest_push = repositories[0]["sort_at"] if repositories else generated_at
    repositories_by_name = {repository["name"]: repository for repository in repositories}
    social_image = dict(config.get("social_image", {}))
    social_image_path = relative_asset_path(str(social_image.get("path", "assets/meta/root-hub-social.png")))

    replacements = {
        "__SITE_TITLE__": html.escape(str(config["site_title"])),
        "__SITE_NAME__": html.escape(str(config["site_name"])),
        "__DESCRIPTION__": html.escape(str(config["description"])),
        "__AUTHOR_NAME__": html.escape(str(config["author_name"])),
        "__SITE_URL__": html.escape(str(config["site_url"])),
        "__GOOGLE_ANALYTICS_SNIPPET__": render_google_analytics_snippet(config),
        "__GITHUB_PROFILE__": html.escape(str(config["github_profile"])),
        "__WIKI_REPO_URL__": html.escape(str(config["wiki_repo_url"])),
        "__GENERATED_LABEL__": generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "__LATEST_PUSH_LABEL__": latest_push.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "__LATEST_PUSH_SHORT__": latest_push.astimezone(timezone.utc).strftime("%Y-%m-%d"),
        "__PUBLIC_REPO_COUNT__": str(len(repositories)),
        "__LIVE_PAGE_COUNT__": str(len(live_repositories)),
        "__TRACK_COUNT__": str(len(tracks)),
        "__WIKI_DOC_COUNT__": str(len(config.get("wiki_documents", []))),
        "__HERO_EYEBROW__": html.escape(str(hero.get("eyebrow", "Project Atlas"))),
        "__HERO_TITLE_HTML__": format_title_html(str(hero.get("title", str(config["site_name"])))),
        "__HERO_SUMMARY__": html.escape(str(hero.get("summary", config["description"]))),
        "__FOCUS_ITEMS__": render_focus_items(list(config.get("current_focus", []))),
        "__PORTFOLIO_TRACKS__": "\n".join(
            render_track_card(track, repositories_by_name) for track in tracks
        ),
        "__FEATURED_CARDS__": "\n".join(
            render_featured_card(repository, index) for index, repository in enumerate(featured_live)
        ),
        "__DOCUMENTATION_CARDS__": "\n".join(
            render_document_card(document) for document in config.get("wiki_documents", [])
        ),
        "__WIKI_LINKS__": "\n".join(render_wiki_link(repository) for repository in repositories),
        "__FILTER_CHIPS__": render_filter_buttons(config),
        "__PROJECT_CARDS__": "\n".join(render_project_card(repository) for repository in repositories),
        "__TIMELINE_ITEMS__": "\n".join(
            render_timeline_item(item) for item in config.get("timeline_highlights", [])
        ),
        "__OSS_STACK_CARDS__": "\n".join(render_oss_card(tool) for tool in config.get("oss_stack", [])),
        "__RECENT_ROWS__": "\n".join(render_recent_row(repository) for repository in repositories),
        "__TRACK_LEGEND__": render_track_legend(config, repositories),
        "__TRACK_CHART_DATA__": build_track_chart_data(config, repositories),
        "__PROJECT_SEARCH_INDEX__": project_search_index(repositories),
        "__SCHEMA_JSON__": build_schema(config, repositories),
        "__SOCIAL_IMAGE_URL__": html.escape(absolute_asset_url(config, social_image_path)),
        "__SOCIAL_IMAGE_ALT__": html.escape(str(social_image.get("alt", "Sheryloe Projects 대표 이미지"))),
    }

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def render_wiki_repo_card(repository: dict[str, Any]) -> str:
    return f"""            <article class="wiki-repo-card {accent_class(repository)} reveal">
              <div class="wiki-repo-head">
                <div>
                  <p class="eyebrow eyebrow-small">{html.escape(repository["track_title"])}</p>
                  <h3>{html.escape(repository["name"])}</h3>
                </div>
                <span class="status-pill">{html.escape(repository["stage"])}</span>
              </div>
              <p>{html.escape(repository["subtitle"])}</p>
              <div class="meta-row">
                {render_tags(repository, max_topics=2)}
              </div>
              <div class="button-row">
                <a class="button button-primary" href="{html.escape(repository["wiki_url"])}">Repo Wiki</a>
                <a class="button" href="{html.escape(repository["live_url"] or repository["repo_url"])}">{primary_link_label(repository)}</a>
              </div>
            </article>"""


def render_wiki_track_card(track: dict[str, Any], repositories_by_name: dict[str, dict[str, Any]]) -> str:
    matched = [repositories_by_name[name] for name in track.get("repositories", []) if name in repositories_by_name]
    return f"""            <article class="wiki-track-card accent-{slugify(str(track.get("accent", "slate")))} reveal">
              <div>
                <p class="eyebrow eyebrow-small">{html.escape(str(track["title"]))}</p>
                <h3>{html.escape(str(track["title"]))}</h3>
                <p>{html.escape(str(track["summary"]))}</p>
              </div>
              <strong class="track-count">{len(matched)} tracked repos</strong>
            </article>"""


def render_wiki_index_html(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    template = WIKI_TEMPLATE_PATH.read_text(encoding="utf-8")
    generated_at = datetime.now(timezone.utc)
    live_repositories = [repo for repo in repositories if repo["has_pages"]]
    repositories_by_name = {repository["name"]: repository for repository in repositories}
    social_image = dict(config.get("social_image", {}))
    social_image_path = relative_asset_path(str(social_image.get("path", "assets/meta/root-hub-social.png")))

    replacements = {
        "__SITE_NAME__": html.escape(str(config["site_name"])),
        "__SITE_URL__": html.escape(str(config["site_url"])),
        "__SITE_TITLE__": html.escape(str(config["site_title"])),
        "__DESCRIPTION__": html.escape(str(config["description"])),
        "__GOOGLE_ANALYTICS_SNIPPET__": render_google_analytics_snippet(config),
        "__GITHUB_PROFILE__": html.escape(str(config["github_profile"])),
        "__WIKI_REPO_URL__": html.escape(str(config["wiki_repo_url"])),
        "__PUBLIC_REPO_COUNT__": str(len(repositories)),
        "__LIVE_PAGE_COUNT__": str(len(live_repositories)),
        "__WIKI_DOC_COUNT__": str(len(config.get("wiki_documents", []))),
        "__GENERATED_LABEL__": generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "__DOCUMENTATION_CARDS__": "\n".join(
            render_document_card(document) for document in config.get("wiki_documents", [])
        ),
        "__WIKI_TRACK_CARDS__": "\n".join(
            render_wiki_track_card(track, repositories_by_name) for track in config.get("portfolio_tracks", [])
        ),
        "__WIKI_REPO_CARDS__": "\n".join(render_wiki_repo_card(repository) for repository in repositories),
        "__TIMELINE_ITEMS__": "\n".join(
            render_timeline_item(item) for item in config.get("timeline_highlights", [])[:4]
        ),
        "__SCHEMA_JSON__": build_schema(config, repositories),
        "__SOCIAL_IMAGE_URL__": html.escape(absolute_asset_url(config, social_image_path)),
        "__SOCIAL_IMAGE_ALT__": html.escape(str(social_image.get("alt", "Sheryloe Projects 대표 이미지"))),
    }

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def append_image_metadata(
    lines: list[str],
    image_url: str | None,
    *,
    title: str | None = None,
    caption: str | None = None,
) -> None:
    if not image_url:
        return
    lines.append("    <image:image>")
    lines.append(f"      <image:loc>{html.escape(image_url)}</image:loc>")
    if title:
        lines.append(f"      <image:title>{html.escape(title)}</image:title>")
    if caption:
        lines.append(f"      <image:caption>{html.escape(caption)}</image:caption>")
    lines.append("    </image:image>")


def render_sitemap_xml(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    site_url = str(config["site_url"]).rstrip("/")
    social_image = dict(config.get("social_image", {}))
    social_image_url = absolute_asset_url(config, str(social_image.get("path", "assets/meta/root-hub-social.png")))
    today = datetime.now(timezone.utc).date().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        "  <url>",
        f"    <loc>{site_url}/</loc>",
        f"    <lastmod>{today}</lastmod>",
        "    <changefreq>daily</changefreq>",
        "    <priority>1.0</priority>",
    ]
    append_image_metadata(
        lines,
        social_image_url,
        title=str(config["site_name"]),
        caption=str(social_image.get("alt", config["site_name"])),
    )
    lines.append("  </url>")

    lines.extend(
        [
            "  <url>",
            f"    <loc>{site_url}/wiki/</loc>",
            f"    <lastmod>{today}</lastmod>",
            "    <changefreq>weekly</changefreq>",
            "    <priority>0.7</priority>",
        ]
    )
    append_image_metadata(
        lines,
        social_image_url,
        title=f"{config['site_name']} Wiki",
        caption="Central wiki landing",
    )
    lines.append("  </url>")

    for document in generated_wiki_documents(config):
        output_path = str(document["output_path"]).replace("\\", "/")
        doc_url = urllib.parse.urljoin(site_url, output_path)
        lines.extend(
            [
                "  <url>",
                f"    <loc>{doc_url}</loc>",
                f"    <lastmod>{today}</lastmod>",
                "    <changefreq>weekly</changefreq>",
                "    <priority>0.6</priority>",
            ]
        )
        append_image_metadata(
            lines,
            social_image_url,
            title=str(document["title"]),
            caption=str(document.get("summary", document["title"])),
        )
        lines.append("  </url>")

    for repository in repositories:
        if not repository["has_pages"]:
            continue
        lines.extend(
            [
                "  <url>",
                f"    <loc>{repository['pages_url']}</loc>",
                f"    <lastmod>{repository['sort_at'].date().isoformat()}</lastmod>",
                "    <changefreq>weekly</changefreq>",
                "    <priority>0.8</priority>",
            ]
        )
        append_image_metadata(
            lines,
            repository["preview_url"] if repository["has_preview"] else None,
            title=repository["name"],
            caption=repository["preview_alt"],
        )
        lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def summary_html(repository: dict[str, Any]) -> str:
    description = repository["description"] or "설명이 아직 정리되지 않은 저장소입니다."
    parts = [
        f"<p><strong>{html.escape(repository['name'])}</strong></p>",
        f"<p>{html.escape(repository['subtitle'])}</p>",
        f"<p>{html.escape(description)}</p>",
        (
            f"<p>Track: {html.escape(repository['track_title'])} · "
            f"Stage: {html.escape(repository['stage'])} · "
            f"Status: {html.escape(repository['status'])}</p>"
        ),
        f"<p>Next focus: {html.escape(repository['next_focus'])}</p>",
    ]
    if repository["has_pages"]:
        parts.append(
            f"<p>Live page: <a href=\"{html.escape(repository['live_url'])}\">{html.escape(repository['live_url'])}</a></p>"
        )
    parts.append(
        f"<p>Wiki: <a href=\"{html.escape(repository['wiki_url'])}\">{html.escape(repository['wiki_url'])}</a></p>"
    )
    parts.append(
        f"<p>GitHub: <a href=\"{html.escape(repository['repo_url'])}\">{html.escape(repository['repo_url'])}</a></p>"
    )
    return "".join(parts)


def wrap_cdata(value: str) -> str:
    return "<![CDATA[" + value.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def render_rss_xml(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    site_url = str(config["site_url"])
    max_entries = int(config.get("max_feed_entries", 30))
    entries = repositories[:max_entries]
    last_build = format_datetime(entries[0]["sort_at"] if entries else datetime.now(timezone.utc))
    items = []

    for repository in entries:
        primary_url = repository["live_url"] or repository["repo_url"]
        categories = [
            f"    <category>{html.escape(repository['track_title'])}</category>",
            f"    <category>{html.escape(repository['category'])}</category>",
            f"    <category>{html.escape(repository['stage'])}</category>",
        ]
        if repository["language"]:
            categories.append(f"    <category>{html.escape(repository['language'])}</category>")
        for topic in repository["topics"][:4]:
            categories.append(f"    <category>{html.escape(topic)}</category>")
        items.append(
            "\n".join(
                [
                    "  <item>",
                    f"    <title>{html.escape(repository['name'])}</title>",
                    f"    <link>{html.escape(primary_url)}</link>",
                    f"    <guid isPermaLink=\"false\">{html.escape(repository['repo_url'])}#{repository['sort_at'].date().isoformat()}</guid>",
                    f"    <pubDate>{format_datetime(repository['sort_at'])}</pubDate>",
                    f"    <description>{wrap_cdata(summary_html(repository))}</description>",
                    *categories,
                    "  </item>",
                ]
            )
        )

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
            "  <channel>",
            f"    <title>{html.escape(str(config['site_name']))} RSS</title>",
            f"    <link>{html.escape(site_url)}</link>",
            f"    <description>{html.escape(str(config['description']))}</description>",
            "    <language>ko-kr</language>",
            f"    <lastBuildDate>{last_build}</lastBuildDate>",
            f"    <atom:link href=\"{html.escape(site_url)}rss.xml\" rel=\"self\" type=\"application/rss+xml\" />",
            *items,
            "  </channel>",
            "</rss>",
            "",
        ]
    )


def render_atom_xml(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    site_url = str(config["site_url"])
    max_entries = int(config.get("max_feed_entries", 30))
    entries = repositories[:max_entries]
    updated = isoformat_z(entries[0]["sort_at"] if entries else datetime.now(timezone.utc))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{html.escape(str(config['site_name']))} Atom</title>",
        f"  <id>{html.escape(site_url)}feed.xml</id>",
        f"  <updated>{updated}</updated>",
        f"  <link href=\"{html.escape(site_url)}feed.xml\" rel=\"self\" />",
        f"  <link href=\"{html.escape(site_url)}\" rel=\"alternate\" />",
        f"  <subtitle>{html.escape(str(config['description']))}</subtitle>",
        "  <author>",
        f"    <name>{html.escape(str(config['author_name']))}</name>",
        "  </author>",
    ]

    for repository in entries:
        primary_url = repository["live_url"] or repository["repo_url"]
        lines.extend(
            [
                "  <entry>",
                f"    <title>{html.escape(repository['name'])}</title>",
                f"    <id>{html.escape(repository['repo_url'])}</id>",
                f"    <link href=\"{html.escape(primary_url)}\" />",
                f"    <updated>{isoformat_z(repository['sort_at'])}</updated>",
                f"    <published>{isoformat_z(repository['created_at'])}</published>",
                f"    <summary type=\"html\">{html.escape(summary_html(repository))}</summary>",
                "  </entry>",
            ]
        )

    lines.append("</feed>")
    lines.append("")
    return "\n".join(lines)


def render_robots_txt(config: dict[str, Any]) -> str:
    site_url = str(config['site_url']).rstrip("/")
    return f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n"


def render_site_webmanifest(config: dict[str, Any]) -> str:
    icon_path = relative_asset_path("assets/meta/icon.svg")
    payload = {
        "name": config["site_name"],
        "short_name": "Sheryloe",
        "description": config["description"],
        "start_url": config["site_url"],
        "scope": config["site_url"],
        "display": "standalone",
        "background_color": "#f4ede4",
        "theme_color": "#193630",
        "icons": [
            {
                "src": absolute_asset_url(config, icon_path),
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any",
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_projects_json(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    payload = {
        "generated_at": isoformat_z(datetime.now(timezone.utc)),
        "site_url": config["site_url"],
        "repository_count": len(repositories),
        "live_pages_count": sum(1 for repository in repositories if repository["has_pages"]),
        "repositories": [
            {
                "name": repository["name"],
                "track": repository["track"],
                "track_title": repository["track_title"],
                "category": repository["category"],
                "subtitle": repository["subtitle"],
                "description": repository["description"],
                "repo_url": repository["repo_url"],
                "live_url": repository["live_url"],
                "pages_url": repository["pages_url"],
                "wiki_url": repository["wiki_url"],
                "language": repository["language"],
                "topics": repository["topics"],
                "status": repository["status"],
                "stage": repository["stage"],
                "audience": repository["audience"],
                "next_focus": repository["next_focus"],
                "has_pages": repository["has_pages"],
                "availability": repository["availability"],
                "featured": repository["featured"],
                "preview_path": repository["preview_path"],
                "preview_image": repository["preview_url"] if repository["has_preview"] else "",
                "preview_alt": repository["preview_alt"],
                "updated_at": isoformat_z(repository["updated_at"]),
                "pushed_at": isoformat_z(repository["sort_at"]),
            }
            for repository in repositories
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    config = load_config()
    repositories = normalize_repositories(config, fetch_public_repositories(str(config["username"])))

    write_file(ROOT / "index.html", render_index_html(config, repositories))
    write_file(ROOT / "wiki" / "index.html", render_wiki_index_html(config, repositories))
    for document in generated_wiki_documents(config):
        write_file(ROOT / str(document["output_path"]), render_wiki_doc_html(config, document, repositories))
    write_file(ROOT / "sitemap.xml", render_sitemap_xml(config, repositories))
    write_file(ROOT / "rss.xml", render_rss_xml(config, repositories))
    write_file(ROOT / "feed.xml", render_atom_xml(config, repositories))
    write_file(ROOT / "robots.txt", render_robots_txt(config))
    write_file(ROOT / "projects.json", render_projects_json(config, repositories))
    write_file(ROOT / "site.webmanifest", render_site_webmanifest(config))
    write_file(ROOT / ".nojekyll", "\n")

    print(
        "Generated: index.html, wiki/index.html, wiki/*.html, sitemap.xml, rss.xml, feed.xml, "
        "robots.txt, projects.json, site.webmanifest, .nojekyll"
    )
    print(
        f"Repositories: {len(repositories)} total, "
        f"{sum(1 for repository in repositories if repository['has_pages'])} live pages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
