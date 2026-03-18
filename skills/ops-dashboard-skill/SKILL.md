---
name: ops-dashboard-skill
description: Deterministically run the bundled ops dashboard scripts to fetch backend graph data, infer natural-language filters, and generate or update the bundled HTML template. Use when an agent must produce the dashboard via local scripts; do not hand-write HTML.
---

# Ops Dashboard Skill

Use this skill to produce the dashboard only through the bundled scripts and bundled HTML template.

The generated HTML is self-contained and host-framework agnostic:
- Do not depend on Vue/React/App.vue.
- Support URL-driven control and `postMessage` control out of the box.

## Non-Negotiable Rules

- MUST execute `python3 scripts/run_ops_dashboard.py ...` for normal skill usage.
- MUST use `assets/dashboard.template.html`; do not hand-write a new HTML page.
- MUST NOT redesign the page layout in the response or generate a substitute HTML file.
- MUST NOT invent data or fallback HTML when script execution fails.
- If the backend or script fails, stop and report the real failure.
- Final response MUST include the exact `htmlPath`; in live mode it MUST also include `url`.
- If `--api-url` is provided, treat backend errors as fatal. The runner already defaults to strict backend mode for this case.

## Workflow

### Step 1: Required execution path

Always use the single runner below. It decides automatically:
- first run: create the live session and open the page
- later runs: update the existing page without regenerating `dashboard.html`

```bash
python3 scripts/run_ops_dashboard.py \
  --api-url http://127.0.0.1:8787/api/ops-graph \
  --app-alias-file ./references/app-aliases.example.json \
  --prompt "看全部关系看板"
```

The runner behavior is fixed:
- if no live session exists, it calls `scripts/dashboard_session.py start`
- if a live session already exists, it calls `scripts/dashboard_session.py update`
- if `--api-url` is present, backend fetch failure is fatal by default
- if `--api-url` is absent, mock data is allowed
- if `assets/dashboard.template.html` changed since the last live run, the next update automatically rebuilds `dashboard.html` once

### Step 2: Choose data source

Pass one of these source configurations to `scripts/run_ops_dashboard.py`:
- Backend mode: pass `--api-url` to fetch live data.
- If the backend filters by application, also pass `--app-id` so the request becomes `?appId=...`.
- If users refer to apps by spoken Chinese names, pass `--app-alias-file` with a JSON map from alias -> appId/app_user.
- Mock mode: omit `--api-url`, or pass `--mock-file`.

Mock backend script for local simulation:

```bash
python3 scripts/mock_backend.py --port 8787
```

Default API endpoint returned by the mock backend:
- `http://127.0.0.1:8787/api/ops-graph`

### Step 3: Natural-language execution

Normal usage:

```bash
python3 scripts/run_ops_dashboard.py \
  --api-url http://127.0.0.1:8787/api/ops-graph \
  --app-id app-001 \
  --app-alias-file ./references/app-aliases.example.json \
  --prompt "看 P002 告警 API，关键词: 风控"
```

What the runner and bundled scripts do:
- Load backend payload or mock payload.
- Normalize either `data.nodes/links` or `data.datas[].nodes/relations`.
- For your internal graph shape, normalized `project` prefers `nodes[].app_user`; `--app-id` is used for request filtering and fallback only.
- Infer filters (`project`, `entityType`, `relationType`, `health`, `keyword`) from prompt.
- Render only through `assets/dashboard.template.html`.
- In live mode, generate HTML once and update only session JSON on later prompts.

The generated HTML includes:
- `window.__OPS_DASHBOARD_SKILL__` runtime API
- `window.postMessage` handlers for agent orchestration
- URL parameter bootstrap support (`prompt`, `project`, `entityType`, `relationType`, `health`, `keyword`)

### Step 4: Live session mode details

The runner defaults to this live mode, but the underlying script is here for debugging:

Start a live session once:

```bash
python3 scripts/dashboard_session.py start \
  --api-url http://127.0.0.1:8787/api/ops-graph \
  --app-alias-file ./references/app-aliases.example.json \
  --prompt "看全部关系看板" \
  --session-dir ./runtime/default-session
```

Update the existing page later:

```bash
python3 scripts/dashboard_session.py update \
  --session-dir ./runtime/default-session \
  --prompt "只看 P001 数据库告警"
```

Live mode behavior:
- `start` renders HTML once, starts a local static server, and can open the page automatically
- `update` only rewrites session JSON files; it does not regenerate the HTML file
- exception: if the bundled template changed or the session HTML is missing, `update` automatically rebuilds the HTML once
- `update` refreshes backend/mock data by default, then reapplies natural-language filters
- pass `--no-refresh-data` if you only want to reuse the cached dataset and update filters/UI

Important:
- the local port in live mode is only for serving the already-open HTML and session JSON files
- backend fetching itself does not require this local port
- the local port exists because an open browser page needs an HTTP URL to poll fresh JSON reliably

### Step 5: Open output

After running the skill:
- Always include the absolute HTML path in the final response.
- In live mode, also include the local URL.
- If local opening fails, still return the exact path/URL and mention the open failure.

For live session mode, include both:
- the absolute HTML path
- the live URL such as `http://127.0.0.1:8765/dashboard.html`

Use any static server only when the user explicitly asks for HTTP preview or remote sharing:

```bash
python3 -m http.server 9000 --directory ./out
```

Open:
- `http://127.0.0.1:9000/dashboard.html`

## Natural-language filter behavior

Supported intent extraction in `scripts/build_dashboard.py`:
- Project: `P001`, `P002`, `全部项目`, `跨项目`
- Application/project identifiers: `appId=xxx`, `app_id=xxx`, `app_user=xxx`, `应用 xxx`, `项目 xxx`
- Entity type: `API`, `服务`, `数据库`, `中间件`, `计算`, `告警`, `用户`, `域名`
- Resource type: `kafka`, `docker`, `redis`, `elasticsearch`, `mysql`, `postgres`, `oracle`, `rabbitmq`, `rocketmq` (支持同时识别多个并输出逗号列表；可容错常见拼写如 `docekr` → `docker`)
- Relation type: `访问`, `调用`, `包含`, `同一`, `负载`, `承载`, `监控`
- Health: `正常`, `告警`, `异常`
- Keyword: `关键词: xxx` or quoted string
- Upstream/downstream: `上下游`, `上游`, `下游`, `依赖`, `链路`, `调用链` (adds 1-hop neighbors of matched nodes)

If no condition is recognized, keep defaults (`all`) and still render dashboard.

## Output contract

`scripts/run_ops_dashboard.py` is the required skill entrypoint. It produces:
- `htmlPath`
- `url` for live mode
- `mode: start|update`
- `refreshedData: true|false` on updates

`build_dashboard.py` produces:
- HTML dashboard file at `--output`
- Sidecar JSON `${output}.meta.json` with:
  - inferred filters
  - summary counts
  - source metadata
- When `--open-output` is passed, the script also attempts to open the local HTML file

`dashboard_session.py start` produces:
- a session HTML file
- `session-config.json`, `session-control.json`, `session-state.json`
- a local live URL
- optional browser auto-open result

`dashboard_session.py update` produces:
- updated session JSON files
- the same HTML path as the original session
- `refreshedData: true|false` so the caller knows whether backend data was reloaded
- `rebuiltHtml: true|false` so the caller knows whether template changes caused an HTML rebuild

## Runtime control protocol (for any host agent)

Use either direct JS calls or `postMessage` after loading the generated HTML.

### Direct JS API

- `window.__OPS_DASHBOARD_SKILL__.run({ prompt, filters })`
- `window.__OPS_DASHBOARD_SKILL__.applyPrompt(prompt, filters?)`
- `window.__OPS_DASHBOARD_SKILL__.setFilters(filters)`
- `window.__OPS_DASHBOARD_SKILL__.getState()`

### postMessage API

Request messages:
- `opsgraph.run`
- `opsgraph.applyPrompt`
- `opsgraph.setFilters`
- `opsgraph.getState`

Response message:
- `opsgraph.result`

## Customize this skill

- Update schema expectations: `references/data-schema.md`
- Update NL parsing rules: `scripts/build_dashboard.py` (`infer_filters_from_prompt` section)
- Update UI template: `assets/dashboard.template.html`
- Update the deterministic entrypoint: `scripts/run_ops_dashboard.py`
- Replace mock data: `assets/mock_data.json`

## Resources

### scripts/
- `run_ops_dashboard.py`: required deterministic entrypoint for agents; auto start/update live session
- `build_dashboard.py`: fetch + parse NL + filter + render HTML
- `dashboard_session.py`: render once, then update session JSON for a live dashboard page
- `mock_backend.py`: serve mock API payload for local simulation

### references/
- `data-schema.md`: expected backend payload and normalization rules
- `app-aliases.example.json`: sample spoken-name to appId/app_user mapping

### assets/
- `dashboard.template.html`: portable HTML dashboard template
- `mock_data.json`: simulation dataset
