---
name: deploy-architecture-skill
description: 通过本地脚本和内置 HTML 模板渲染部署架构图。这个 skill 只接受 agent 先调用 MCP 后提供的本地 JSON 输入，优先直接使用 MCP 返回的原始文件路径；不允许直连后端 API，也不允许 mock 回退。
---

# 部署架构图 Skill

这个 skill 是一个 MCP 渲染器。

它只做两件事：
- 读取 agent 提供的 MCP JSON 输入
- 基于 D3 和 `assets/dashboard.template.html` 生成或更新部署架构图

它不能做这些事：
- 不能自己请求后端 API
- 不能自己启动 mock 数据源
- 不能手写新的 HTML 页面替代模板
- 不能在数据失败时兜底造假数据

## 不可违反的规则

- 必须先由 agent 调用内置 MCP 工具，再执行本 skill
- 脚本参数 `--prompt` 必须传用户这一次的最新原话，不能传 skill 的 `default_prompt`、`SKILL.md` 说明或其他执行指令
- 优先直接使用 MCP 返回的原始文件路径作为 `--input-json`
- 只有宿主拿到的是纯 JSON 文本、而不是可直接读取的本地文件时，才写入 `./runtime/mcp-input.json`
- 必须执行 `python3 scripts/run_deploy_architecture.py --input-json "<MCP原始文件路径或./runtime/mcp-input.json>" --prompt "..."`
- 必须使用 `assets/dashboard.template.html`
- 脚本失败时必须直接报告真实错误
- 最终回复里必须包含准确的 `htmlPath`
- live 模式下最终回复还必须包含 `url`

## MCP 契约

当前使用的 MCP 配置：

- `server="ges_mcp_server"`
- `tool="query_ges"`

推荐的 MCP 调用契约：

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

## 固定工作流

### 第 1 步：agent 调 MCP

agent 负责从用户自然语言中抽取 MCP 参数：
- `appId`
- `resourceType`

然后由 agent 调用内置 MCP 工具取数。

如果 MCP 返回的是一个宿主可直接读取的本地文件：
- 直接把这个文件路径传给 `--input-json`
- 文件名没有 `.json` 后缀也可以，只要内容本身是合法 JSON

如果 MCP 返回里只有符合 schema 的 JSON 文本，没有可直接读取的文件：
- 再把这段文本写入 `./runtime/mcp-input.json`
- 不要再额外包装一层更大的 JSON

### 第 2 步：执行统一入口

始终使用下面这个统一入口：

```bash
python3 scripts/run_deploy_architecture.py \
  --input-json "<MCP原始文件路径或./runtime/mcp-input.json>" \
  --prompt "把这个应用渲染成部署架构图"
```

统一入口脚本的行为是固定的：
- 如果 live session 不存在，就调用 `scripts/architecture_session.py start`
- 如果 live session 已存在，就调用 `scripts/architecture_session.py update`
- 首次运行会创建 HTML 并启动本地预览地址
- 后续运行默认只更新 session JSON，除非模板变化才重建 HTML

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
- 顶层必须是 JSON 对象
- 必须包含 `data`
- `data.datas` 必须是非空数组
- 每个 `datas[i]` 必须包含数组类型的 `nodes` 和 `relations`

## 分层规则

- 渲染主视图是部署架构图
- `nodes[].type` 表示资源所属层级，例如 `接入层`、`网关层`、`应用层`
- 相同层级的节点会被放在同一块区域中
- 区域顺序按从上到下排列
- 如果某些节点没有 `type`，脚本会回退到实体类型或资源类型，保证页面仍能渲染

## 健康状态规则

- 当前接口可视为只返回 `lifecycle_state == Active` 的资源全集
- 页面上的资源 health 只看该资源是否通过 `relations` 关联到 `resource_type == "alarm"` 的节点：
  - 有关联 alarm：`告警`
  - 没有关联 alarm：`正常`
- `alarm` 节点继续展示，但不显示 health

## 返回结果

`run_deploy_architecture.py` 会输出：
- `htmlPath`
- `url`（仅 live 模式）
- `mode: start|update`

`architecture_session.py update` 还会输出：
- `refreshedData: true`
- `rebuiltHtml: true|false`

## 关键文件

- `scripts/run_deploy_architecture.py`：统一入口，自动判断 start / update
- `scripts/build_architecture.py`：读取 MCP JSON、解析 prompt、生成 HTML
- `scripts/architecture_session.py`：首次生成 HTML，后续只更新 session 数据
- `assets/dashboard.template.html`：D3 模板
- `references/data-schema.md`：输入字段说明
