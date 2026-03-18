---
name: ops-dashboard-skill
description: 通过本地脚本确定性地拉取运维图谱后端数据、解析自然语言过滤条件，并基于内置 HTML 模板生成或更新看板。适用于 agent 必须通过脚本产出图谱页面、不能手写 HTML 的场景。
---

# 运维图谱看板 Skill

这个 skill 只能通过内置脚本和内置 HTML 模板产出看板。

生成的 HTML 是自包含的，并且不依赖宿主前端框架：
- 不依赖 Vue、React 或 `App.vue`
- 默认支持 URL 参数控制和 `postMessage` 控制

## 不可违反的规则

- 正常使用时，必须执行 `python3 scripts/run_ops_dashboard.py ...`
- 必须使用 `assets/dashboard.template.html`，不能手写新的 HTML 页面替代
- 不能在回复里重新设计页面，也不能生成一个“功能相似但不是模板产物”的 HTML
- 脚本或后端失败时，不能自己编造数据或兜底 HTML
- 后端或脚本失败后，必须直接报告真实错误
- 最终回复里必须包含准确的 `htmlPath`；如果是 live 模式，还必须包含 `url`
- 如果传入了 `--api-url`，后端错误必须按致命错误处理；runner 默认也会按严格模式执行

## 工作流

### 第 1 步：固定入口

始终使用下面这个统一入口。它会自动判断：
- 第一次运行：创建 live session 并打开页面
- 后续运行：更新已有页面，而不是重复生成 `dashboard.html`

```bash
python3 scripts/run_ops_dashboard.py \
  --api-url http://127.0.0.1:8787/api/ops-graph \
  --app-alias-file ./references/app-aliases.example.json \
  --prompt "看全部关系看板"
```

runner 的行为是固定的：
- 如果 live session 不存在，就调用 `scripts/dashboard_session.py start`
- 如果 live session 已存在，就调用 `scripts/dashboard_session.py update`
- 如果传了 `--api-url`，后端获取失败默认按致命错误处理
- 如果没传 `--api-url`，允许使用 mock 数据
- 如果 `assets/dashboard.template.html` 相比上次 live 运行发生变化，下一次 update 会自动重建一次 `dashboard.html`

### 第 2 步：选择数据源

调用 `scripts/run_ops_dashboard.py` 时，按下面两种模式之一提供数据源：

- 后端模式：传 `--api-url`，从真实接口拉取数据
- 如果后端支持按应用过滤，再额外传 `--app-id`，请求会拼成 `?appId=...`
- 如果用户会用中文口语名称提应用，再额外传 `--app-alias-file`，文件内容是 `alias -> appId/app_user` 的 JSON 映射
- Mock 模式：不传 `--api-url`，或者显式传 `--mock-file`

本地模拟后端脚本：

```bash
python3 scripts/mock_backend.py --port 8787
```

默认 mock 接口地址：
- `http://127.0.0.1:8787/api/ops-graph`

### 第 3 步：自然语言执行

常规调用示例：

```bash
python3 scripts/run_ops_dashboard.py \
  --api-url http://127.0.0.1:8787/api/ops-graph \
  --app-id app-001 \
  --app-alias-file ./references/app-aliases.example.json \
  --prompt "看 P002 告警 API，关键词: 风控"
```

runner 和内置脚本会完成这些事情：
- 加载后端返回或 mock 返回的数据
- 兼容并归一化 `data.nodes/links` 和 `data.datas[].nodes/relations`
- 对你当前的图谱结构，内部 `project` 优先取 `nodes[].app_user`；`--app-id` 主要用于请求过滤和兜底
- 根据 prompt 推断过滤条件：`project`、`entityType`、`relationType`、`health`、`keyword`
- 只通过 `assets/dashboard.template.html` 渲染页面
- 在 live 模式下只生成一次 HTML，后续 prompt 只更新 session JSON

生成后的 HTML 默认提供：
- `window.__OPS_DASHBOARD_SKILL__` 运行时 API
- `window.postMessage` 消息处理
- 基于 URL 参数的初始化能力，例如 `prompt`、`project`、`entityType`、`relationType`、`health`、`keyword`

### 第 4 步：live session 模式

runner 默认就是 live 模式。下面是调试时可直接使用的底层脚本：

首次启动：

```bash
python3 scripts/dashboard_session.py start \
  --api-url http://127.0.0.1:8787/api/ops-graph \
  --app-alias-file ./references/app-aliases.example.json \
  --prompt "看全部关系看板" \
  --session-dir ./runtime/default-session
```

后续更新：

```bash
python3 scripts/dashboard_session.py update \
  --session-dir ./runtime/default-session \
  --prompt "只看 P001 数据库告警"
```

live 模式行为：
- `start` 只渲染一次 HTML，启动本地静态服务，并可自动打开浏览器
- `update` 默认只改 session JSON，不重新生成 HTML 文件
- 例外：如果模板改了，或者 session HTML 丢失了，`update` 会自动重建一次 HTML
- `update` 默认会重新拉一次后端或 mock 数据，然后重新套用自然语言过滤
- 如果只想复用缓存数据、不想重新取数，可以传 `--no-refresh-data`

重要说明：
- live 模式里的本地端口只是为了给已打开的页面提供一个可访问的 HTTP 地址，以及暴露 session JSON
- 后端接口拉取本身并不依赖这个本地端口
- 本地端口存在的原因，是浏览器页面要通过 HTTP 稳定轮询最新状态

### 第 5 步：返回结果

skill 执行完成后：
- 最终回复必须包含绝对路径的 HTML 文件地址
- 如果是 live 模式，还必须包含本地 URL
- 如果自动打开失败，也仍然要返回准确的 path / URL，并说明打开失败

live 模式下必须同时返回：
- 绝对路径 HTML
- 类似 `http://127.0.0.1:8765/dashboard.html` 这样的 URL

只有在用户明确要求 HTTP 预览或远程分享时，才额外启用通用静态服务，例如：

```bash
python3 -m http.server 9000 --directory ./out
```

然后访问：
- `http://127.0.0.1:9000/dashboard.html`

## 自然语言过滤规则

`scripts/build_dashboard.py` 当前支持的自然语言解析能力：

- 项目：`P001`、`P002`、`全部项目`、`跨项目`
- 应用 / 项目标识：`appId=xxx`、`app_id=xxx`、`app_user=xxx`、`应用 xxx`、`项目 xxx`
- 实体类型：`API`、`服务`、`数据库`、`中间件`、`计算`、`告警`、`用户`、`域名`
- 资源类型：`kafka`、`docker`、`redis`、`elasticsearch`、`mysql`、`postgres`、`oracle`、`rabbitmq`、`rocketmq`
  这部分支持同时识别多个资源类型并输出逗号列表，也支持常见拼写容错，例如 `docekr` 会被识别为 `docker`
- 关系类型：`访问`、`调用`、`包含`、`同一`、`负载`、`承载`、`监控`
- 健康状态：`正常`、`告警`、`异常`
- 关键词：`关键词: xxx` 或引号包裹的内容
- 上下游：`上下游`、`上游`、`下游`、`依赖`、`链路`、`调用链`
  识别后会自动把命中的节点向外扩 1 跳邻居

如果一句话里没有识别到任何条件，就保留默认值 `all`，但仍然会生成看板。

## 输出约定

`scripts/run_ops_dashboard.py` 是这个 skill 唯一允许的统一入口，它会输出：
- `htmlPath`
- `url`（仅 live 模式）
- `mode: start|update`
- `refreshedData: true|false`（update 时是否重新拉取过数据）

`build_dashboard.py` 会输出：
- `--output` 指定的 HTML 文件
- `${output}.meta.json` 辅助 JSON，里面包含：
  - 推断出的过滤条件
  - 汇总统计
  - 数据源元信息
- 如果传了 `--open-output`，脚本还会尝试直接打开本地 HTML 文件

`dashboard_session.py start` 会输出：
- session HTML 文件
- `session-config.json`、`session-control.json`、`session-state.json`
- 本地 live URL
- 可选的浏览器自动打开结果

`dashboard_session.py update` 会输出：
- 更新后的 session JSON 文件
- 原 session 里的 HTML 路径
- `refreshedData: true|false`
- `rebuiltHtml: true|false`

## 运行时控制协议

宿主 agent 加载生成后的 HTML 后，可以通过 JS API 或 `postMessage` 控制它。

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

- 修改数据结构约定：`references/data-schema.md`
- 修改自然语言解析规则：`scripts/build_dashboard.py` 里的 `infer_filters_from_prompt`
- 修改前端模板：`assets/dashboard.template.html`
- 修改统一入口：`scripts/run_ops_dashboard.py`
- 替换 mock 数据：`assets/mock_data.json`

## 资源说明

### `scripts/`

- `run_ops_dashboard.py`：这个 skill 的统一入口，自动判断 start / update
- `build_dashboard.py`：拉数据、解析自然语言、过滤数据、渲染 HTML
- `dashboard_session.py`：只在首次生成 HTML，后续通过 session JSON 更新页面
- `mock_backend.py`：本地模拟后端接口

### `references/`

- `data-schema.md`：后端返回结构和内部归一化规则
- `app-aliases.example.json`：中文口语名称到 `appId` / `app_user` 的映射示例

### `assets/`

- `dashboard.template.html`：可移植的 HTML 看板模板
- `mock_data.json`：默认模拟数据
