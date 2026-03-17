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
