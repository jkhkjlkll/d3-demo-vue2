---
name: ops-dashboard-skill
description: 通过本地脚本和内置 HTML 模板渲染运维图谱看板。这个 skill 只接受 agent 先调用 MCP 后落盘的本地 JSON，不允许直连后端 API，也不允许 mock 回退。
---

# 运维图谱看板 Skill

这个 skill 是一个 MCP 渲染器。

它只能做两件事：
- 读取 agent 预先写好的 MCP JSON
- 基于 `assets/dashboard.template.html` 生成或更新看板

它不能做这些事：
- 不能自己请求后端 API
- 不能自己启动 mock 数据源
- 不能手写新的 HTML 页面替代模板
- 不能在数据失败时兜底造假数据

## 不可违反的规则

- 必须先由 agent 调用内置 MCP 工具，再执行本 skill
- MCP 返回必须先写入 `./runtime/mcp-input.json`
- 之后必须执行 `python3 scripts/run_ops_dashboard.py --input-json ./runtime/mcp-input.json --prompt "..."`
- 必须使用 `assets/dashboard.template.html`
- 脚本失败时必须直接报告真实错误
- 最终回复里必须包含准确的 `htmlPath`
- live 模式下最终回复还必须包含 `url`

## MCP 契约

文档里不写真实内网名称，统一使用占位符：

- `MCP_SERVER_NAME="__MCP_SERVER_NAME__"`
- `MCP_TOOL_NAME="__MCP_TOOL_NAME__"`

如果宿主 agent 没有 `server/tool` 二级概念，而是直接暴露一个 MCP 调用入口，就把 `MCP_TOOL_NAME` 当成那个入口名。

推荐的 MCP 调用契约：

```json
{
  "server": "__MCP_SERVER_NAME__",
  "tool": "__MCP_TOOL_NAME__",
  "arguments": {
    "appId": "<appId>",
    "resourceType": "<resourceType>"
  }
}
```

## 固定工作流

### 第 1 步：agent 调 MCP

agent 负责从用户自然语言中抽取 MCP 参数：
- `appId`
- `resourceType`

然后由 agent 调用内置 MCP 工具取数。

### 第 2 步：把 MCP 返回写到固定路径

固定相对路径：

```text
./runtime/mcp-input.json
```

在当前仓库中的绝对路径是：

```text
/Users/xiao/code/d3-demo-vue2/skills/ops-dashboard-skill/runtime/mcp-input.json
```

### 第 3 步：执行统一入口

始终使用下面这个统一入口：

```bash
python3 scripts/run_ops_dashboard.py \
  --input-json ./runtime/mcp-input.json \
  --prompt "看全部关系看板"
```

runner 的行为是固定的：
- 如果 live session 不存在，就调用 `scripts/dashboard_session.py start`
- 如果 live session 已存在，就调用 `scripts/dashboard_session.py update`
- 首次运行会创建 HTML 并启动本地预览地址
- 后续运行默认只更新 session JSON，除非模板变化才重建 HTML
- 每次 update 都会重新读取最新的 `mcp-input.json`

## 脚本接口

### 统一入口

```bash
python3 scripts/run_ops_dashboard.py \
  --input-json ./runtime/mcp-input.json \
  --prompt "只看 P001 数据库告警"
```

保留参数：
- `--prompt`
- `--session-dir`
- `--input-json`
- `--title`
- `--port`
- `--open-browser`
- `--poll-ms`

### 底层 live session 命令

首次启动：

```bash
python3 scripts/dashboard_session.py start \
  --input-json ./runtime/mcp-input.json \
  --prompt "看全部关系看板" \
  --session-dir ./runtime/default-session
```

后续更新：

```bash
python3 scripts/dashboard_session.py update \
  --session-dir ./runtime/default-session \
  --input-json ./runtime/mcp-input.json \
  --prompt "只看 P001 数据库告警"
```

## 输入数据要求

这个 skill 只接受 MCP JSON。

支持的输入结构：

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

要求：
- 顶层必须是 JSON object
- 必须包含 `data`
- `data.datas` 必须是非空数组
- 每个 `datas[i]` 必须包含数组类型的 `nodes` 和 `relations`
- 输入文件不存在、JSON 非法、结构不合法时，脚本必须直接失败

## 自然语言职责边界

职责固定如下：

- agent 负责抽取 MCP 参数：`appId`、`resourceType`
- 脚本只对已经拿到的 MCP 数据做前端展示筛选
- 脚本当前保留的 prompt 推断能力只用于：
  - `relationType`
  - `health`
  - `keyword`
  - `expandNeighbors`

项目 / 应用维度不再依赖脚本从 prompt 中推断；最终展示以 MCP 返回的 `nodes[].app_user` 为准。

## 返回结果

skill 执行完成后：
- 最终回复必须包含绝对路径的 HTML 文件地址
- live 模式还必须包含本地 URL
- 自动打开失败也要返回准确的 path / URL，并说明失败原因

`run_ops_dashboard.py` 会输出：
- `htmlPath`
- `url`（仅 live 模式）
- `mode: start|update`

`dashboard_session.py update` 还会输出：
- `refreshedData: true`
- `rebuiltHtml: true|false`

## 本地端口说明

live 模式里的本地端口只是为了：
- 承载已经生成的 HTML 页面
- 暴露 session JSON 给页面轮询更新

它不是后端接口代理，也不是 MCP 代理。

## 运行时控制协议

生成后的 HTML 提供：

### 直接 JS API

- `window.__OPS_DASHBOARD_SKILL__.run({ prompt, filters })`
- `window.__OPS_DASHBOARD_SKILL__.applyPrompt(prompt, filters?)`
- `window.__OPS_DASHBOARD_SKILL__.setFilters(filters)`
- `window.__OPS_DASHBOARD_SKILL__.getState()`

### `postMessage` API

请求消息：
- `opsgraph.run`
- `opsgraph.applyPrompt`
- `opsgraph.setFilters`
- `opsgraph.getState`

响应消息：
- `opsgraph.result`

## 如何定制这个 skill

- 修改输入结构约定：`references/data-schema.md`
- 修改 prompt 过滤规则：`scripts/build_dashboard.py` 里的 `infer_filters_from_prompt`
- 修改 live session 行为：`scripts/dashboard_session.py`
- 修改统一入口：`scripts/run_ops_dashboard.py`
- 修改前端模板：`assets/dashboard.template.html`

## 资源说明

### `scripts/`

- `run_ops_dashboard.py`：统一入口，自动判断 start / update
- `build_dashboard.py`：读取 MCP JSON、解析 prompt、过滤数据、渲染 HTML
- `dashboard_session.py`：首次生成 HTML，后续只更新 session 数据

### `references/`

- `data-schema.md`：MCP 返回结构和内部归一化规则

### `assets/`

- `dashboard.template.html`：可移植的 HTML 看板模板
