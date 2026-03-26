# MCP 数据结构说明

当 agent 已经调用内部 MCP 工具，并拿到一个可读取的本地 JSON 文件，或把结果写入 skill 本地 JSON 文件后，请按本说明解析数据。

## 支持的返回结构

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
- 每个 `data.datas[i].nodes` 必须是数组
- 每个 `data.datas[i].relations` 必须是数组

## 节点字段映射

渲染器会使用这些节点字段：
- 节点 ID：`nodes[].id`
- 节点名称：`nodes[].name`
- 资源类型：`nodes[].resource_type`
- 部署层级：`nodes[].type`
- 项目 / 应用维度：
  - 优先使用：`nodes[].project`、`nodes[].project_id`、`nodes[].app_id`、`nodes[].appId`
  - 兜底使用：`nodes[].app_user`

说明：
- `nodes[].type` 是部署架构图里最重要的字段，表示节点应该落在哪一层
- 相同 `type` 的节点会渲染到同一层级区域里
- 层级区域按从上到下排序
- 如果 `type` 缺失，渲染器会回退到实体类型或资源类型

## 关系字段映射

渲染器会使用这些关系字段：
- 关系起点：`relations[].startNode`
- 关系终点：`relations[].endNode`
- 关系类型：`relations[].relation_type`

兼容旧字段别名：
- `relations[].startNodeId`
- `relations[].endNodeId`

## 健康状态规则

- 页面上的资源 health 只看该资源是否通过 `relations` 关联到 `resource_type == "alarm"` 的节点
- 有关联 alarm：`告警`
- 无关联 alarm：`正常`
- `alarm` 节点本身不显示 health
