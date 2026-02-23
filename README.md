# gh-md-fetch

gh extension: Fetch web articles and convert to Markdown.

JS レンダリングされた Web 記事を Playwright で取得し、サイト固有のルールで Markdown に変換する。

## Install

```bash
gh extension install A-hosoda/gh-md-fetch
```

初回実行時に `.venv` の作成と Chromium のインストールが自動で行われる。

### Manual setup

```bash
git clone https://github.com/A-hosoda/gh-md-fetch.git
cd gh-md-fetch
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m playwright install chromium
```

## Usage

```bash
gh md-fetch https://note.com/user/n/xxxxxxxxxx
gh md-fetch https://note.com/user/n/xxxxxxxxxx -o ./output
```

出力: `YYYY-MM-DD-<slug>.md`（デフォルト: `~/Downloads`）

## Supported sites

| Site | Host pattern |
|------|-------------|
| note | `note.com`, `*.note.com` |
| Qiita | `qiita.com`, `*.qiita.com` |

## Claude Code integration

Claude Code のサンドボックス内では Chromium が起動できない（Mach ポート権限エラー）。
`playwright-http-server` をサンドボックス外で常駐させ、localhost 経由で中継することで解決する。

### Architecture

```
Sandbox outside:
  playwright-http-server (127.0.0.1:19877)
       ^ POST {"url": "...", "timeout_ms": 30000}
       v {"html": "...", "error": null}

Sandbox inside (Claude Code):
  fetcher.py fetch_page()
    1. Proxy health check (GET, 2s timeout)
    2. Available -> _fetch_via_proxy()
    3. Unavailable -> _fetch_via_playwright() (fallback)
```

### Setup

#### 1. Start the proxy server

サンドボックス外のターミナルで実行:

```bash
cd /path/to/gh-md-fetch
.venv/bin/python hooks/playwright-http-server.py &
```

verbose モード:

```bash
.venv/bin/python hooks/playwright-http-server.py --verbose &
```

#### 2. Configure Claude Code hook (optional)

Claude Code が `WebFetch` で note.com / qiita.com URL にアクセスした際、自動的にプロキシ経由で取得するための hook。
記事は temp ファイルに保存され、`additionalContext` でファイルパスが Claude に通知される。

`.claude/settings.local.json` に追加:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": ".venv/bin/python hooks/site-fetch-hook.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

#### 3. Symlink to ~/.claude/hooks (alternative)

グローバルに使いたい場合:

```bash
ln -s /path/to/gh-md-fetch/hooks/playwright-http-server.py ~/.claude/hooks/
ln -s /path/to/gh-md-fetch/hooks/site-fetch-hook.py ~/.claude/hooks/
```

`~/.claude/settings.json` の hooks に追加:

```json
{
  "matcher": "WebFetch",
  "hooks": [
    {
      "type": "command",
      "command": "/path/to/gh-md-fetch/.venv/bin/python ~/.claude/hooks/site-fetch-hook.py",
      "timeout": 60
    }
  ]
}
```

### Server commands

```bash
# Start
.venv/bin/python hooks/playwright-http-server.py &

# Health check
curl -s http://127.0.0.1:19877/ | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('status')=='ok' else 'NG')"

# Stop
kill $(cat /tmp/playwright-http-server.pid)
```

## Development

```bash
# Run all tests (mock tests, no Playwright needed)
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_fetcher.py
.venv/bin/python -m pytest tests/test_fetcher.py -v -k "Proxy or Fallback or Convert"

# Run Playwright integration tests (requires Chromium outside sandbox)
.venv/bin/python -m pytest tests/test_fetcher.py -v
```

## Project structure

```
gh-md-fetch
├── gh-md-fetch          # gh extension entry point (bash)
├── md_fetch/
│   ├── cli.py           # CLI pipeline
│   ├── fetcher.py       # HTML fetcher (proxy + Playwright fallback)
│   ├── converter.py     # HTML to Markdown converter
│   └── sites/           # Site-specific configs
│       ├── base.py      # SiteConfig ABC
│       ├── note.py      # note.com config
│       ├── qiita.py     # qiita.com config
│       └── __init__.py  # SiteRegistry
├── hooks/
│   ├── playwright-http-server.py  # Proxy server for sandbox bypass
│   └── site-fetch-hook.py        # WebFetch hook for Claude Code
├── tests/
└── pyproject.toml
```
