# Data Schema Reference

Use this schema when normalizing backend payload for the dashboard renderer.

## Accepted payload shapes

### Shape A

```json
{
  "status": "ok",
  "data": {
    "nodes": [],
    "links": []
  }
}
```

### Shape B

```json
{
  "nodes": [],
  "links": []
}
```

### Shape C

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

## Node schema

Required fields:
- `id` (string)
- `label` (string)
- `type` (string)
- `health` (string: `正常|告警|异常` or `ok|warn|err`)
- `project` (string)

Optional fields:
- any additional business fields are preserved in metadata but not required for rendering

## Link schema

Required fields:
- `source` (string)
- `target` (string)
- `type` (string)

## Normalization rules

1. Convert health aliases to Chinese display values:
- `ok` -> `正常`
- `warn` -> `告警`
- `err` or `error` -> `异常`

2. Drop malformed nodes or links missing required IDs.

3. Keep only links whose `source` and `target` both exist in node IDs after filtering.

## Internal graph adapter notes

This skill can also normalize a backend shape like:

```json
{
  "status": "ok|error",
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

Field mapping used by the adapter:
- Node ID: `nodes[].id`
- Node label: `nodes[].name`
- Node type: `nodes[].resource_type`
- Node health: `nodes[].lifecycle_state`
- Project/app dimension: normalized `project` prefers `nodes[].app_user`; request-side `appId` is only used as query param and fallback
- Relation source: `relations[].startNodeId`
- Relation target: `relations[].endNodeId`
- Relation type: `relations[].relation_type`

Lifecycle health mapping:
- `Active` -> `正常`
- `Recycle` -> `异常`
- unknown values default to `正常`

Known relation aliases:
- `contains` -> `包含`
- `calls` -> `调用`
- `same_as` -> `同一资源`

`result[]` is ignored unless a future adapter explicitly consumes it.

Natural-language project parsing also recognizes these explicit forms:
- `appId=xxx`
- `app_id=xxx`
- `app_user=xxx`
- `应用 xxx`
- `项目 xxx`

If users speak a Chinese app name that does not appear directly in `nodes[].app_user`,
pass an alias file such as:

```json
{
  "支付系统": "app-pay-001",
  "风控平台": "app-risk-001"
}
```

The adapter will resolve the spoken alias to the canonical `appId`/`app_user` before filtering.

## Filter fields

Inferred filter object:

```json
{
  "project": "all|P001|P002|...",
  "entityType": "all|api|service|db|middleware|compute|alarm|user|domain",
  "relationType": "all|access|call|lb|host|monitor",
  "health": "all|ok|warn|err",
  "keyword": "string"
}
```
