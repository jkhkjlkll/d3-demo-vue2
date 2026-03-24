# MCP 数据结构说明

当 agent 已经调用内部 MCP 工具，并把结果写入 skill 本地 JSON 文件后，请按本说明解析数据。

如果 `query_ges` 已经直接返回符合本说明的 JSON 文本，就把这段文本原样写入 `./runtime/mcp-input.json`。不要再额外包装一层更大的 JSON。

## 输入路径

默认相对路径：

```text
./runtime/mcp-input.json
```

仓库内绝对路径：

```text
/Users/xiao/code/d3-demo-vue2/skills/ops-dashboard-skill/runtime/mcp-input.json
```

如果宿主 file tool 在覆盖已有文件前要求先读取：
- 先读取 `./runtime/mcp-input.json`
- 再覆盖写回同一路径
- 如果文件还不存在，可以直接创建

对于大 payload，不要退回到 PowerShell 或字符串拼接脚本去重写文件；如果宿主无法把原始 JSON 文本稳定写到这个固定路径，就直接报告真实错误。

## MCP 调用契约

当前使用下面这套 MCP 契约：

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

如果宿主 agent 没有 `server/tool` 二级概念，而是只暴露一个 MCP 调用入口，就把 `query_ges` 当成那个入口名。

## 支持的返回结构

渲染器目前只接受下面这种 MCP 返回结构：

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

校验规则：
- 顶层必须是 JSON 对象
- `data` 必须是 JSON 对象
- `data.datas` 必须是非空数组
- 每个 `data.datas[i]` 必须是对象
- 每个 `data.datas[i].nodes` 必须是数组
- 每个 `data.datas[i].relations` 必须是数组
- JSON 非法或结构不合法时，直接视为致命错误，不允许兜底

## 节点字段映射

渲染器会使用这些节点字段：
- 节点 ID：`nodes[].id`
- 节点名称：`nodes[].name`
- 节点类型：`nodes[].resource_type`
- 节点状态：`nodes[].lifecycle_state`
- 项目 / 应用维度：
  - 优先使用：`nodes[].project`、`nodes[].project_id`、`nodes[].app_id`、`nodes[].appId`
  - 兜底使用：`nodes[].app_user`

可选字段：
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
- 其他业务扩展字段

特殊处理：
- 当 `nodes[].resource_type = "alarm"` 时，渲染器会把它识别成 `告警` 类型节点
- 页面上的 `告警` 数量按 alarm 节点数量统计
- `alarm` 节点自己的 `nodes[].hrn` 表示它对应的是哪个资源的告警
- 渲染器会按下面顺序寻找 alarm 对应的资源：
  - 先匹配普通资源节点的 `hrn`
  - 再匹配普通资源节点的 `resource_id`
  - 最后匹配普通资源节点的节点 `id`
- 一旦匹配成功，渲染器会内部补一条 `监控` 关系用于展示，并把该资源标成红色异常
- 如果普通资源没有关联任何 alarm 节点，则显示为绿色正常

## 关系字段映射

渲染器会使用这些关系字段：
- 关系起点：`relations[].startNode`
- 关系终点：`relations[].endNode`
- 关系类型：`relations[].relation_type`

仍然兼容的旧字段别名：
- `relations[].startNodeId`
- `relations[].endNodeId`

已知关系类型别名：
- `contains` -> `包含`
- `calls` -> `调用`
- `same_as` -> `同一资源`

`result[]` 当前会被忽略。

## 生命周期状态展示

页面展示时会保留 MCP 返回的原始状态文本。

例如：
- `Active` 页面就显示 `Active`
- `Recycle` 页面就显示 `Recycle`

内部为了做颜色、筛选和统计，仍然可能把这些值归一化成 `正常 / 告警 / 异常`，但展示文本不会被改写。

## Prompt 职责边界

职责拆分如下：

- agent 负责从用户自然语言里提取 MCP 请求参数：
  - `appId`
  - `resourceType`
- 渲染器只把 prompt 用于展示层筛选：
  - `relationType`
  - `health`
  - `keyword`
  - `expandNeighbors`

渲染器不再负责从 prompt 里推断请求侧的 `appId`。

## 本地输出行为

构建脚本支持在本地打开生成结果：
- 传入 `--open-output` 会尝试用本机默认应用 / 浏览器打开 HTML
- 标准输出里会包含 `htmlPath`
- 即使打开失败，HTML 生成仍然算成功，同时会返回 `openError`

对于 live session 模式：
- `scripts/dashboard_session.py start` 会先生成一次 `dashboard.html`，然后在本地 HTTP 地址上提供访问
- `scripts/dashboard_session.py update` 会重新读取最新的 MCP JSON，并更新 `session-control.json` 和 `session-state.json`
- 页面会轮询这些 session 文件，从而在不重建 HTML 的情况下刷新数据
