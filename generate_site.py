from __future__ import annotations

import html
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "site-config.json"
TEMPLATE_PATH = ROOT / "templates" / "index.template.html"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def github_headers() -> dict[str, str]:
    headers = {"User-Agent": "sheryloe-root-site-generator"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/vnd.github+json"
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


def normalize_repositories(config: dict[str, Any], repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    excluded = set(config.get("exclude_repositories", []))
    featured = set(config.get("featured_repositories", []))
    overrides = dict(config.get("repository_overrides", {}))
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
        description = str(override.get("description") or (repo.get("description") or "").strip())
        homepage = str(override.get("live_url") or (repo.get("homepage") or "").strip())
        derived_page_url = f"{site_url}{quote_repo_path(name)}/"
        live_url = ""
        if repo.get("has_pages"):
            live_url = homepage or derived_page_url

        topics = [str(topic) for topic in (repo.get("topics") or []) if topic]
        language = str(repo.get("language") or "Unknown")

        normalized.append(
            {
                "name": name,
                "description": description,
                "repo_url": str(repo["html_url"]),
                "live_url": live_url,
                "pages_url": derived_page_url if repo.get("has_pages") else "",
                "language": language,
                "topics": topics,
                "has_pages": bool(repo.get("has_pages")),
                "featured": bool(override.get("featured", name in featured)),
                "created_at": created_at,
                "updated_at": updated_at,
                "sort_at": pushed_at,
                "sort_label": pushed_at.astimezone(timezone.utc).strftime("%Y-%m-%d"),
                "stars": int(repo.get("stargazers_count") or 0),
                "size": int(repo.get("size") or 0),
                "default_branch": str(repo.get("default_branch") or "main"),
            }
        )

    normalized.sort(key=lambda item: item["sort_at"], reverse=True)
    return normalized


def render_tags(repository: dict[str, Any], max_topics: int = 4) -> str:
    tags = [f'<span class="tag">{html.escape(repository["language"])}</span>']
    if repository["featured"]:
        tags.append('<span class="tag">Featured</span>')
    if repository["has_pages"]:
        tags.append('<span class="tag">GitHub Pages</span>')
    for topic in repository["topics"][:max_topics]:
        tags.append(f'<span class="tag">{html.escape(topic)}</span>')
    return "".join(tags)


def repository_search_text(repository: dict[str, Any]) -> str:
    parts = [
        repository["name"],
        repository["description"],
        repository["language"],
        " ".join(repository["topics"]),
    ]
    return " ".join(part.lower() for part in parts if part)


def render_repository_card(repository: dict[str, Any], primary_label: str) -> str:
    title_badge = '<span class="badge live">Live</span>' if repository["has_pages"] else '<span class="badge repo">Repo</span>'
    primary_url = repository["live_url"] or repository["repo_url"]
    description = html.escape(repository["description"] or "설명이 아직 없는 저장소입니다.")
    if repository["has_pages"]:
        primary_text = primary_label
        secondary_link = f'<a class="button" href="{html.escape(repository["repo_url"])}">GitHub Repo</a>'
    else:
        primary_text = "GitHub Repo"
        secondary_link = '<span class="button" aria-disabled="true">Live 없음</span>'

    return f"""          <article class="repo-card" data-repo-card data-search="{html.escape(repository_search_text(repository), quote=True)}">
            <div class="repo-head">
              <div class="repo-title">
                <div class="subtle">{repository['sort_label']} 업데이트</div>
                <h3 class="repo-name">{html.escape(repository['name'])}</h3>
              </div>
              {title_badge}
            </div>
            <p>{description}</p>
            <div class="repo-tags">{render_tags(repository)}</div>
            <div class="repo-meta">
              <span>기본 브랜치 {html.escape(repository['default_branch'])}</span>
              <span>스타 {repository['stars']}</span>
              <span>크기 {repository['size']}</span>
            </div>
            <div class="link-row">
              <a class="button primary" href="{html.escape(primary_url)}">{html.escape(primary_text)}</a>
              {secondary_link}
            </div>
          </article>"""


def render_live_card(repository: dict[str, Any]) -> str:
    description = html.escape(repository["description"] or "GitHub Pages가 활성화된 라이브 프로젝트입니다.")
    live_url = html.escape(repository["live_url"] or repository["pages_url"])
    repo_url = html.escape(repository["repo_url"])
    return f"""          <article class="repo-card">
            <div class="repo-head">
              <div class="repo-title">
                <div class="subtle">{repository['sort_label']} 업데이트</div>
                <h3 class="repo-name">{html.escape(repository['name'])}</h3>
              </div>
              <span class="badge live">Live</span>
            </div>
            <p>{description}</p>
            <div class="repo-tags">{render_tags(repository, max_topics=3)}</div>
            <div class="link-row">
              <a class="button primary" href="{live_url}">라이브 페이지</a>
              <a class="button" href="{repo_url}">GitHub Repo</a>
            </div>
          </article>"""


def build_schema(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    max_schema_entries = int(config.get("max_schema_entries", 20))
    items = []
    for position, repository in enumerate(repositories[:max_schema_entries], start=1):
        items.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": repository["name"],
                "url": repository["live_url"] or repository["repo_url"],
            }
        )

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": str(config["site_name"]),
                "url": str(config["site_url"]),
                "description": str(config["description"]),
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
                "itemListElement": items,
            },
        ],
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


def render_index_html(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    live_repositories = [repo for repo in repositories if repo["has_pages"]]
    recent_repositories = repositories[:6]
    feed_limit = int(config.get("max_feed_entries", 30))
    generated_at = datetime.now(timezone.utc)
    latest_push = repositories[0]["sort_at"] if repositories else generated_at

    replacements = {
        "__SITE_TITLE__": html.escape(str(config["site_title"])),
        "__SITE_NAME__": html.escape(str(config["site_name"])),
        "__DESCRIPTION__": html.escape(str(config["description"])),
        "__AUTHOR_NAME__": html.escape(str(config["author_name"])),
        "__SITE_URL__": html.escape(str(config["site_url"])),
        "__GITHUB_PROFILE__": html.escape(str(config["github_profile"])),
        "__GENERATED_LABEL__": generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "__LATEST_PUSH_LABEL__": latest_push.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "__PUBLIC_REPO_COUNT__": str(len(repositories)),
        "__LIVE_PAGE_COUNT__": str(len(live_repositories)),
        "__FEED_ENTRY_COUNT__": str(min(len(repositories), feed_limit)),
        "__RECENT_CARDS__": "\n".join(render_repository_card(repo, "바로 보기") for repo in recent_repositories),
        "__LIVE_CARDS__": "\n".join(render_live_card(repo) for repo in live_repositories) or '          <article class="repo-card"><h3>라이브 프로젝트가 아직 없습니다.</h3><p>GitHub Pages가 켜진 저장소가 생기면 여기에 자동으로 표시됩니다.</p></article>',
        "__ALL_CARDS__": "\n".join(render_repository_card(repo, "열기") for repo in repositories),
        "__SCHEMA_JSON__": build_schema(config, repositories),
    }

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def render_sitemap_xml(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    site_url = str(config["site_url"])
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url>",
        f"    <loc>{site_url}</loc>",
        f"    <lastmod>{datetime.now(timezone.utc).date().isoformat()}</lastmod>",
        "    <changefreq>daily</changefreq>",
        "    <priority>1.0</priority>",
        "  </url>",
    ]

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
                "  </url>",
            ]
        )

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def summary_html(repository: dict[str, Any]) -> str:
    description = html.escape(repository["description"] or "설명이 아직 없는 저장소입니다.")
    parts = [
        f"<p><strong>{html.escape(repository['name'])}</strong></p>",
        f"<p>{description}</p>",
    ]
    if repository["has_pages"]:
        parts.append(
            f"<p>Live page: <a href=\"{html.escape(repository['live_url'])}\">{html.escape(repository['live_url'])}</a></p>"
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
        categories = []
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
    return f"User-agent: *\nAllow: /\n\nSitemap: {config['site_url']}sitemap.xml\n"


def render_projects_json(config: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    payload = {
        "generated_at": isoformat_z(datetime.now(timezone.utc)),
        "site_url": config["site_url"],
        "repository_count": len(repositories),
        "live_pages_count": sum(1 for repository in repositories if repository["has_pages"]),
        "repositories": [
            {
                "name": repository["name"],
                "description": repository["description"],
                "repo_url": repository["repo_url"],
                "live_url": repository["live_url"],
                "pages_url": repository["pages_url"],
                "language": repository["language"],
                "topics": repository["topics"],
                "has_pages": repository["has_pages"],
                "updated_at": isoformat_z(repository["updated_at"]),
                "pushed_at": isoformat_z(repository["sort_at"]),
            }
            for repository in repositories
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    config = load_config()
    repositories = normalize_repositories(config, fetch_public_repositories(str(config["username"])))

    write_file(ROOT / "index.html", render_index_html(config, repositories))
    write_file(ROOT / "sitemap.xml", render_sitemap_xml(config, repositories))
    write_file(ROOT / "rss.xml", render_rss_xml(config, repositories))
    write_file(ROOT / "feed.xml", render_atom_xml(config, repositories))
    write_file(ROOT / "robots.txt", render_robots_txt(config))
    write_file(ROOT / "projects.json", render_projects_json(config, repositories))
    write_file(ROOT / ".nojekyll", "\n")

    print("Generated: index.html, sitemap.xml, rss.xml, feed.xml, robots.txt, projects.json, .nojekyll")
    print(f"Repositories: {len(repositories)} total, {sum(1 for repository in repositories if repository['has_pages'])} live pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
