---
name: ops-dashboard-skill
description: Build a reusable operations dashboard from backend graph data and natural-language requests. Use when an agent must fetch monitoring/topology data, infer filter conditions from user text, and generate a portable HTML dashboard output (without framework lock-in) for quick delivery or sharing.
---

# Ops Dashboard Skill

Generate a portable dashboard by combining three steps:
1. Fetch data from backend API or mock backend.
2. Convert natural language into filter conditions.
3. Render filtered data into an HTML dashboard template.

The generated HTML is self-contained and host-framework agnostic:
- Do not depend on Vue/React/App.vue.
- Support URL-driven control and `postMessage` control out of the box.

## Workflow

### Step 1: Choose data source

Use one of these modes:
- Backend mode: pass `--api-url` to fetch live data.
- Mock mode: pass `--mock-file` or use default mock data.

Mock backend script:

```bash
python3 scripts/mock_backend.py --port 8787
```

Default API endpoint returned by the mock backend:
- `http://127.0.0.1:8787/api/ops-graph`

### Step 2: Build dashboard from natural language

Run:

```bash
python3 scripts/build_dashboard.py \
  --api-url http://127.0.0.1:8787/api/ops-graph \
  --prompt "看 P002 告警 API，关键词: 风控" \
  --output ./out/dashboard.html
```

What the script does:
- Load backend payload.
- Infer filters (`project`, `entityType`, `relationType`, `health`, `keyword`) from prompt.
- Filter `nodes` and `links`.
- Render `assets/dashboard.template.html` with filtered data.
- Write HTML and sidecar JSON metadata.

The generated HTML includes:
- `window.__OPS_DASHBOARD_SKILL__` runtime API
- `window.postMessage` handlers for agent orchestration
- URL parameter bootstrap support (`prompt`, `project`, `entityType`, `relationType`, `health`, `keyword`)

### Step 3: Open output

Use any static server:

```bash
python3 -m http.server 9000 --directory ./out
```

Open:
- `http://127.0.0.1:9000/dashboard.html`

## Natural-language filter behavior

Supported intent extraction in `scripts/build_dashboard.py`:
- Project: `P001`, `P002`, `全部项目`, `跨项目`
- Entity type: `API`, `服务`, `数据库`, `中间件`, `计算`, `告警`, `用户`, `域名`
- Relation type: `访问`, `调用`, `负载`, `承载`, `监控`
- Health: `正常`, `告警`, `异常`
- Keyword: `关键词: xxx` or quoted string

If no condition is recognized, keep defaults (`all`) and still render dashboard.

## Output contract

`build_dashboard.py` produces:
- HTML dashboard file at `--output`
- Sidecar JSON `${output}.meta.json` with:
  - inferred filters
  - summary counts
  - source metadata

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
- Replace mock data: `assets/mock_data.json`

## Resources

### scripts/
- `build_dashboard.py`: fetch + parse NL + filter + render HTML
- `mock_backend.py`: serve mock API payload for local simulation

### references/
- `data-schema.md`: expected backend payload and normalization rules

### assets/
- `dashboard.template.html`: portable HTML dashboard template
- `mock_data.json`: simulation dataset
