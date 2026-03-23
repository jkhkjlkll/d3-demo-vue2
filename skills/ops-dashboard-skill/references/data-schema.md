# MCP Data Schema Reference

Use this schema when the agent has already called the internal MCP tool and written the result to the skill's local JSON file.

## Input path

Default relative path:

```text
./runtime/mcp-input.json
```

Repository absolute path:

```text
/Users/xiao/code/d3-demo-vue2/skills/ops-dashboard-skill/runtime/mcp-input.json
```

If the host file tool refuses to overwrite existing files unless they were read first, allocate a fresh input path instead:

```bash
python3 scripts/next_input_path.py
```

Example output:

```text
/Users/xiao/code/d3-demo-vue2/skills/ops-dashboard-skill/runtime/inbox/mcp-input-20260323T113000-ab12cd34.json
```

The renderer accepts any local JSON path passed through `--input-json`.

## MCP contract

Use the following MCP contract:

```json
{
  "server": "ges_mcp_server",
  "tool": "query_ges",
  "arguments": {
    "appId": "<appId>",
    "resourceType": "<resourceType>"
  }
}
```

If the host agent exposes a single MCP entrypoint rather than separate server/tool names, treat `query_ges` as that single entrypoint name.

## Accepted payload shape

The renderer now accepts only the MCP payload shape below.

```json
{
  "status": "ok",
  "data": {
    "datas": [
      {
        "nodes": [],
        "relations": [],
        "result": []
      }
    ]
  }
}
```

Validation rules:
- top-level payload must be a JSON object
- `data` must be a JSON object
- `data.datas` must be a non-empty array
- every `data.datas[i]` must be an object
- every `data.datas[i].nodes` must be an array
- every `data.datas[i].relations` must be an array
- invalid JSON or invalid shape is a fatal error; no fallback path exists

## Node mapping

Input fields used by the renderer:
- Node ID: `nodes[].id`
- Node label: `nodes[].name`
- Node type: `nodes[].resource_type`
- Node health: `nodes[].lifecycle_state`
- Project/app dimension: `nodes[].app_user`

Optional fields that may exist and are tolerated:
- `resource_id`
- `resource_type`
- `hrn`
- `lifecycle_state`
- `source`
- `region_code`
- `az_code`
- `rack_code`
- `room_code`
- `env`
- `app_user`
- `labels`
- other business metadata

## Relation mapping

Input fields used by the renderer:
- Relation source: `relations[].startNodeId`
- Relation target: `relations[].endNodeId`
- Relation type: `relations[].relation_type`

Known relation aliases:
- `contains` -> `包含`
- `calls` -> `调用`
- `same_as` -> `同一资源`

`result[]` is currently ignored.

## Lifecycle state display

The UI preserves the original lifecycle text for display.

Examples:
- `Active` is displayed as `Active`
- `Recycle` is displayed as `Recycle`

Internal coloring/filtering may still normalize these values into `正常 / 告警 / 异常`, but the displayed text stays as the original lifecycle value.

## Prompt responsibility split

Responsibility is intentionally split:

- the agent extracts MCP request arguments from the user's natural language:
  - `appId`
  - `resourceType`
- the renderer only uses the prompt for display-side filtering:
  - `relationType`
  - `health`
  - `keyword`
  - `expandNeighbors`

The renderer should not infer request-side `appId` from the prompt anymore.

## Local output behavior

The dashboard builder can open the generated file locally:
- pass `--open-output` to open the generated HTML with the default local app/browser
- stdout includes `htmlPath`
- if opening fails, stdout includes `openError` but HTML generation still succeeds

For live-session mode:
- `scripts/dashboard_session.py start` renders `dashboard.html` once and serves it over a local HTTP URL
- `scripts/dashboard_session.py update` rereads the JSON file provided by `--input-json` and rewrites `session-control.json` plus `session-state.json`
- the page polls these session files to refresh data without regenerating HTML on every run
