---
name: ops-dashboard-mcp-skill
description: 当运维图谱数据需要通过 MCP 工具获取而不是通过 HTTP 接口获取时，先调用 MCP 取数并整理成现有 ops dashboard 脚本可识别的 JSON，再复用现有渲染脚本生成或更新 HTML 看板。不要修改现有 ops-dashboard-skill，也不要手写 HTML。
---

# 运维图谱 MCP Skill

这个 skill 是给 “MCP 取数” 场景准备的外层包装器。

它不替代现有的 `ops-dashboard-skill`，而是复用现有渲染链路：
- 先由 agent 调用 MCP 工具拿图谱数据
- 再把 MCP 返回整理成现有脚本支持的 JSON
- 最后继续调用现有的 `run_ops_dashboard.py` 生成看板

这样做的目标是：
- 不修改当前 `ops-dashboard-skill`
- 不重写前端模板
- 不重写自然语言过滤逻辑
- 只替换“数据从哪里来”这一层

## 不可违反的规则

- 不能修改现有 `skills/ops-dashboard-skill` 目录下的代码来适配 MCP
- 必须先调用 MCP，再把结果写成本地 JSON 文件
- 必须复用现有渲染入口：`python3 skills/ops-dashboard-skill/scripts/run_ops_dashboard.py`
- 不能手写 HTML 页面替代现有模板
- 最终回复必须返回准确的 `htmlPath`；如果是 live 模式，还必须返回 `url`

## 最小改造思路

这个 skill 的核心思想是：

1. Agent 调 MCP 工具拿图谱数据
2. 把返回结果整理成现有 renderer 可识别的结构
3. 写到临时 JSON 文件，例如 `/tmp/ops-dashboard-mcp.json`
4. 调用现有脚本时，把这个 JSON 当成 `--mock-file`

也就是说，MCP 只是替换了“数据源获取方式”，后面的：
- 自然语言解析
- 过滤逻辑
- session 热更新
- HTML 模板渲染

全部继续复用现有实现。

## 推荐执行流程

### 第 1 步：调用 MCP 工具

先在当前 agent 环境里调用已经配置好的 MCP 图谱工具。

选择原则：
- 能返回当前应用 / 项目的图谱数据
- 返回里至少能映射出节点列表和关系列表
- 最好支持按 `appId`、项目名或其他业务条件拉取

如果 MCP 工具名未知，先查看当前 agent 可用的 MCP 工具列表，再选图谱相关的那个。

### 第 2 步：把 MCP 返回整理成标准 JSON

优先整理成下面这个结构：

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

当前 renderer 也兼容这些近似形态：
- `data.nodes` / `data.links`
- `data.datas[].nodes` / `data.datas[].relations`

节点建议至少能映射这些字段：
- `id`
- `name`
- `resource_type`
- `lifecycle_state`
- `app_user`

关系建议至少能映射这些字段：
- `startNodeId`
- `endNodeId`
- `relation_type`

### 第 3 步：写入临时文件

把整理后的数据写入一个本地 JSON 文件，例如：

```text
/tmp/ops-dashboard-mcp.json
```

建议每次运行都覆盖同一个临时文件，方便 live session 反复更新。

### 第 4 步：调用现有渲染脚本

直接复用现有脚本：

```bash
python3 skills/ops-dashboard-skill/scripts/run_ops_dashboard.py \
  --session-dir skills/ops-dashboard-mcp-skill/runtime/default-session \
  --mock-file /tmp/ops-dashboard-mcp.json \
  --app-alias-file skills/ops-dashboard-skill/references/app-aliases.example.json \
  --prompt "看 P002 的全部 docker 上下游数据"
```

这里的关键点：
- `--mock-file` 实际上承载的是 MCP 返回，而不是传统 mock 数据
- `--session-dir` 使用这个新 skill 自己的 runtime 目录，避免和旧 skill 的 session 混用
- 自然语言仍然由现有 `build_dashboard.py` 里的规则解析

## 自然语言处理仍然是谁在做

这个 skill 本身不负责解析自然语言。

自然语言仍然由现有脚本处理：
- `skills/ops-dashboard-skill/scripts/build_dashboard.py`
- 前端模板里的运行时过滤逻辑也继续沿用现有实现

所以它现在仍然属于：
- LLM 选 skill
- MCP 负责取数
- Python 规则负责 prompt 解析
- HTML 模板负责展示

换句话说，这个 MCP 版 skill 只换了“取数方式”，没有换“参数理解方式”。

## 适用场景

适合下面这些情况：
- 数据只能通过 MCP 拿，不能直连 HTTP 接口
- 不想改当前 `ops-dashboard-skill`
- 想先快速验证 MCP 接入链路是否可行
- 想复用已有 HTML 模板、session 更新和过滤能力

## 不适合的场景

如果你想做到下面这些，这个 skill 还不够：
- 让 Python 脚本直接原生调用 MCP
- 让自然语言先由 LLM 输出结构化参数
- 彻底摆脱 `--mock-file` 这一层

那种场景就不是“最小改造”了，而是正式把 renderer 升级成 MCP 原生版。

## 最终回复要求

执行完成后，最终回复必须包含：
- `htmlPath`
- `url`（如果是 live 模式）

如果 MCP 取数失败，或者 JSON 整理失败，必须直接报告真实错误，不能自行编造页面。

## 资源复用

这个 skill 复用的现有资源如下：

- `skills/ops-dashboard-skill/scripts/run_ops_dashboard.py`
- `skills/ops-dashboard-skill/scripts/build_dashboard.py`
- `skills/ops-dashboard-skill/scripts/dashboard_session.py`
- `skills/ops-dashboard-skill/assets/dashboard.template.html`
- `skills/ops-dashboard-skill/references/app-aliases.example.json`

## 一句话总结

这个 MCP skill 本质上是：

`MCP 取数 -> 写本地 JSON -> 复用现有 run_ops_dashboard.py -> 生成 / 更新 HTML 看板`

如果你之后决定正式改造现有 skill，再把“写本地 JSON”这一步替换成“脚本直接接 MCP”即可。
