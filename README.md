# OpsGraph (Vue2 + D3 + Element UI)

运维知识图谱示例项目，基于 Vue2 + D3 + Element UI，支持可拖拽的拓扑节点与统一风格的连线展示。

## 环境要求
- Node.js 14+ (建议 16)
- pnpm 7+

## 安装依赖
```
pnpm install
```

如果遇到 pnpm store 路径错误或无 TTY，可使用：
```
CI=true pnpm install --store-dir .pnpm-store
pnpm add element-ui d3 --store-dir .pnpm-store
```

## 本地开发
```
pnpm run serve
```

## 构建
```
pnpm run build
```

## 后端接口约定

### 接口地址示例
- `GET /api/ops-graph?project=P001`

### 返回格式
```
{
  "code": 0,
  "message": "ok",
  "data": {
    "stats": {
      "nodeCount": 8,
      "linkCount": 7,
      "okCount": 10,
      "warnCount": 4,
      "errorCount": 5
    },
    "entityTypes": [
      { "key": "user", "label": "用户", "color": "#5AC8FA", "count": 1 },
      { "key": "domain", "label": "域名上下文", "color": "#3CD2FF", "count": 2 },
      { "key": "api", "label": "API接口", "color": "#F3A84F", "count": 3 }
    ],
    "relationTypes": [
      { "key": "access", "label": "访问" },
      { "key": "call", "label": "调用" }
    ],
    "graph": {
      "nodes": [
        { "id": "user", "label": "用户", "type": "user", "count": 1, "x": 140, "y": 300 },
        { "id": "domain", "label": "域名上下文", "type": "domain", "count": 2, "x": 320, "y": 300 }
      ],
      "links": [
        { "source": "user", "target": "domain", "label": "访问 x2", "type": "access" }
      ]
    }
  }
}
```

### 字段说明
- `stats`: 顶部/底部统计信息。
- `entityTypes`: 左侧实体类型列表与节点颜色映射。
- `relationTypes`: 右侧关系类型列表。
- `graph.nodes`: 拓扑节点数据。
  - `id`: 节点唯一标识
  - `label`: 节点名称
  - `type`: 节点类型，对应 `entityTypes.key`
  - `count`: 实体数量
  - `x`,`y`: 可选，节点初始位置，缺省则自动布局
- `graph.links`: 关系连线数据。
  - `source`,`target`: 指向节点 `id`
  - `label`: 连线显示文字
  - `type`: 关系类型，对应 `relationTypes.key`

## 数据接入位置
前端数据接入入口：`/Users/xiao/code/d3-demo-vue2/src/App.vue` 的 `fetchGraphData()`。

数据落地变量（`applyData(payload)` 内写入）：
- `this.graphData`: 图谱节点与连线（`graph.nodes` / `graph.links`）
- `this.entityTypes`: 实体类型列表（左侧与图例）
- `this.relationTypes`: 关系类型列表（右侧与图例）
- `this.stats`: 统计信息（顶部/底部）

## Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).
