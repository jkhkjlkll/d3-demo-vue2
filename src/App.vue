<template>
  <div id="app" class="ops-app">
    <el-container class="layout">
      <el-header class="header">
        <div class="title">
          <span class="title-main">OpsGraph</span>
          <span class="title-sub">运维知识图谱</span>
        </div>
        <div class="header-tags">
          <el-tag size="mini" type="success">实时同步</el-tag>
          <el-tag size="mini">节点 {{ stats.nodeCount }}</el-tag>
          <el-tag size="mini">关系 {{ stats.linkCount }}</el-tag>
          <el-tag size="mini" type="warning">告警 {{ stats.warnCount }}</el-tag>
          <el-tag size="mini" type="danger">异常 {{ stats.errorCount }}</el-tag>
        </div>
      </el-header>

      <el-main class="main">
        <el-card class="filter-card" shadow="never">
          <el-form :inline="true" size="mini" class="filter-form">
            <el-form-item label="项目">
              <el-select v-model="filters.project" placeholder="选择项目">
                <el-option label="P001 · 电商平台" value="P001"></el-option>
                <el-option label="P002 · 金融平台" value="P002"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="实体类型">
              <el-select v-model="filters.entityType" placeholder="全部类型">
                <el-option label="全部类型" value="all"></el-option>
                <el-option v-for="item in entityTypes" :key="item.key" :label="item.label" :value="item.key"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="关系类型">
              <el-select v-model="filters.relationType" placeholder="全部关系">
                <el-option label="全部关系" value="all"></el-option>
                <el-option v-for="item in relationTypes" :key="item.key" :label="item.label" :value="item.key"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-input v-model="filters.keyword" prefix-icon="el-icon-search" placeholder="搜索实体名称"></el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="refresh">刷新</el-button>
              <el-button @click="fitView">适应视图</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-container class="content">
          <el-aside class="aside" width="220px">
            <el-card class="panel" shadow="never">
              <div class="panel-title">实体列表</div>
              <ul class="list">
                <li v-for="item in entityTypes" :key="item.key" class="list-item">
                  <span class="dot" :style="{ background: item.color }"></span>
                  <span class="list-label">{{ item.label }}</span>
                  <span class="list-count">{{ item.count }}</span>
                </li>
              </ul>
            </el-card>
          </el-aside>

          <el-main class="graph-main">
            <el-card class="panel graph-panel" shadow="never">
              <div class="panel-header">
                <div class="panel-title">拓扑视图</div>
                <div class="panel-stats">
                  <el-tag size="mini">节点 {{ stats.nodeCount }}</el-tag>
                  <el-tag size="mini">关系 {{ stats.linkCount }}</el-tag>
                  <el-tag size="mini" type="success">正常 {{ stats.okCount }}</el-tag>
                  <el-tag size="mini" type="warning">告警 {{ stats.warnCount }}</el-tag>
                  <el-tag size="mini" type="danger">异常 {{ stats.errorCount }}</el-tag>
                </div>
              </div>
              <div ref="graphWrap" class="graph-wrap">
                <svg ref="graphSvg" class="graph-svg"></svg>
              </div>
            </el-card>
          </el-main>

          <el-aside class="aside" width="220px">
            <el-card class="panel" shadow="never">
              <div class="panel-title">实体类型</div>
              <ul class="list">
                <li v-for="item in entityTypes" :key="item.key + '-legend'" class="list-item">
                  <span class="dot" :style="{ background: item.color }"></span>
                  <span class="list-label">{{ item.label }}</span>
                </li>
              </ul>
              <div class="panel-title" style="margin-top: 16px;">关系类型</div>
              <ul class="list">
                <li v-for="item in relationTypes" :key="item.key" class="list-item">
                  <span class="line"></span>
                  <span class="list-label">{{ item.label }}</span>
                </li>
              </ul>
            </el-card>
          </el-aside>
        </el-container>
      </el-main>

      <el-footer class="footer">
        <span>节点 {{ stats.nodeCount }}</span>
        <span>关系 {{ stats.linkCount }}</span>
        <span>项目 1</span>
        <span class="ok">正常 {{ stats.okCount }}</span>
        <span class="warn">告警 {{ stats.warnCount }}</span>
        <span class="danger">异常 {{ stats.errorCount }}</span>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import * as d3 from 'd3'

export default {
  name: 'App',
  data() {
    return {
      filters: {
        project: 'P001',
        entityType: 'all',
        relationType: 'all',
        keyword: ''
      },
      linkColor: '#2d7ef7',
      entityTypes: [],
      relationTypes: [],
      stats: {
        nodeCount: 0,
        linkCount: 0,
        okCount: 0,
        warnCount: 0,
        errorCount: 0
      },
      graphData: {
        nodes: [],
        links: []
      }
    }
  },
  mounted() {
    this.loadData()
    window.addEventListener('resize', this.handleResize)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize)
  },
  methods: {
    handleResize() {
      this.renderGraph()
    },
    refresh() {
      this.loadData()
    },
    fitView() {
      this.renderGraph()
    },
    async loadData() {
      const payload = await this.fetchGraphData()
      this.applyData(payload)
      this.$nextTick(() => this.renderGraph())
    },
    async fetchGraphData() {
      // TODO: Replace with real API call
      // Example:
      // const res = await fetch('/api/ops-graph?project=' + this.filters.project)
      // return await res.json()
      return Promise.resolve(this.mockApiResponse())
    },
    applyData(payload) {
      if (!payload) return
      this.entityTypes = payload.entityTypes || []
      this.relationTypes = payload.relationTypes || []
      this.stats = payload.stats || this.stats
      this.graphData = payload.graph || { nodes: [], links: [] }
    },
    mockApiResponse() {
      return {
        stats: {
          nodeCount: 8,
          linkCount: 7,
          okCount: 10,
          warnCount: 4,
          errorCount: 5
        },
        entityTypes: [
          { key: 'user', label: '用户', color: '#5AC8FA', count: 1 },
          { key: 'domain', label: '域名上下文', color: '#3CD2FF', count: 2 },
          { key: 'api', label: 'API接口', color: '#F3A84F', count: 3 },
          { key: 'service', label: '应用微服务', color: '#42D98F', count: 4 },
          { key: 'db', label: '数据库', color: '#F1C95C', count: 2 },
          { key: 'middleware', label: '中间件', color: '#8B6CFF', count: 2 },
          { key: 'compute', label: '计算资源', color: '#7DAAF7', count: 3 },
          { key: 'alarm', label: '告警', color: '#FF5C5C', count: 2 }
        ],
        relationTypes: [
          { key: 'access', label: '访问' },
          { key: 'call', label: '调用' },
          { key: 'depend', label: '依赖' },
          { key: 'route', label: '路由' },
          { key: 'monitor', label: '监控' },
          { key: 'support', label: '资源' }
        ],
        graph: {
          nodes: [
            { id: 'user', label: '用户', type: 'user', count: 1, x: 140, y: 300 },
            { id: 'domain', label: '域名上下文', type: 'domain', count: 2, x: 320, y: 300 },
            { id: 'api', label: 'API接口', type: 'api', count: 3, x: 500, y: 300 },
            { id: 'service', label: '应用微服务', type: 'service', count: 4, x: 680, y: 300 },
            { id: 'middleware', label: '中间件', type: 'middleware', count: 2, x: 860, y: 300 },
            { id: 'alarm', label: '告警', type: 'alarm', count: 2, x: 1040, y: 300 },
            { id: 'db', label: '数据库', type: 'db', count: 2, x: 820, y: 170 },
            { id: 'compute', label: '计算资源', type: 'compute', count: 3, x: 820, y: 470 }
          ],
          links: [
            { source: 'user', target: 'domain', label: '访问 x2', type: 'access' },
            { source: 'domain', target: 'api', label: 'API请求 x4', type: 'call' },
            { source: 'api', target: 'service', label: '依赖 x4', type: 'depend' },
            { source: 'service', target: 'middleware', label: '依赖 x2', type: 'depend' },
            { source: 'middleware', target: 'alarm', label: '告警 x1', type: 'monitor' },
            { source: 'service', target: 'db', label: '查询 x1', type: 'route' },
            { source: 'service', target: 'compute', label: '资源 x3', type: 'support' }
          ]
        }
      }
    },
    renderGraph() {
      const svgEl = this.$refs.graphSvg
      const wrapEl = this.$refs.graphWrap
      if (!svgEl || !wrapEl) return

      const width = wrapEl.clientWidth
      const height = wrapEl.clientHeight

      const svg = d3.select(svgEl)
      svg.selectAll('*').remove()
      const worldWidth = Math.max(width, 2400)
      const worldHeight = Math.max(height, 1600)
      const worldX = -(worldWidth - width) / 2
      const worldY = -(worldHeight - height) / 2

      svg
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', `${worldX} ${worldY} ${worldWidth} ${worldHeight}`)
        .attr('preserveAspectRatio', 'xMidYMid meet')

      const root = svg.append('g').attr('class', 'graph-root')
      const zoom = d3
        .zoom()
        .scaleExtent([0.2, 4])
        .on('zoom', (event) => {
          root.attr('transform', event.transform)
        })

      svg.call(zoom)

      const nodes = this.graphData.nodes.map((node, index) => ({
        ...node,
        w: 140,
        h: 54,
        x: typeof node.x === 'number' ? node.x : 140 + index * 180,
        y: typeof node.y === 'number' ? node.y : height / 2
      }))

      const nodeById = new Map(nodes.map((node) => [node.id, node]))
      const links = this.graphData.links
        .map((link) => ({
          ...link,
          source: nodeById.get(link.source),
          target: nodeById.get(link.target)
        }))
        .filter((link) => link.source && link.target)

      const linkPath = (link) => {
        const sx = link.source.x
        const sy = link.source.y
        const tx = link.target.x
        const ty = link.target.y
        return `M${sx},${sy} L${tx},${ty}`
      }

      const linkGroup = root.append('g').attr('class', 'links')
      const linkPaths = linkGroup
        .selectAll('path')
        .data(links)
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('stroke', this.linkColor)
        .attr('d', (d) => linkPath(d))

      root
        .append('g')
        .attr('class', 'link-labels')
        .selectAll('text')
        .data(links)
        .enter()
        .append('text')
        .attr('class', 'link-label')
        .attr('x', (d) => (d.source.x + d.target.x) / 2)
        .attr('y', (d) => (d.source.y + d.target.y) / 2 - 6)
        .text((d) => d.label)

      const nodeGroup = root.append('g').attr('class', 'nodes')
      const node = nodeGroup
        .selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', (d) => `translate(${d.x - d.w / 2}, ${d.y - d.h / 2})`)
        .call(
          d3
            .drag()
            .on('drag', function (event, d) {
              d.x = event.x
              d.y = event.y
              d3.select(this).attr('transform', `translate(${d.x - d.w / 2}, ${d.y - d.h / 2})`)
              linkPaths.attr('d', (link) => linkPath(link))
              root
                .selectAll('.link-label')
                .attr('x', (l) => (l.source.x + l.target.x) / 2)
                .attr('y', (l) => (l.source.y + l.target.y) / 2 - 6)
            })
        )

      node
        .append('rect')
        .attr('width', (d) => d.w)
        .attr('height', (d) => d.h)
        .attr('rx', 10)
        .attr('ry', 10)
        .attr('fill', '#ffffff')
        .attr('stroke', (d) => this.findTypeColor(d.type))
        .attr('stroke-width', 2)

      node
        .append('text')
        .attr('x', 14)
        .attr('y', 24)
        .attr('class', 'node-title')
        .text((d) => d.label)

      node
        .append('text')
        .attr('x', 14)
        .attr('y', 42)
        .attr('class', 'node-count')
        .text((d) => `${d.count} 个实体`)
    },
    findTypeColor(type) {
      const found = this.entityTypes.find((item) => item.key === type)
      return found ? found.color : '#4cd4ff'
    }
  }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600&display=swap');

:root {
  --bg: #f5f7fb;
  --panel: #ffffff;
  --border: #d6e2f2;
  --text: #22324d;
  --muted: #6b7c99;
  --link: #2d7ef7;
}

* {
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: 'Rajdhani', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

#app,
.ops-app {
  height: 100%;
}

.ops-app {
  background: radial-gradient(circle at 20% 20%, rgba(77, 140, 240, 0.12), transparent 45%),
    radial-gradient(circle at 80% 0%, rgba(72, 196, 236, 0.12), transparent 35%),
    var(--bg);
}

.layout {
  height: 100%;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  background: #ffffff;
  border-bottom: 1px solid var(--border);
}

.title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.title-main {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
}

.title-sub {
  font-size: 12px;
  color: var(--muted);
}

.header-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.main {
  padding: 12px 16px 0;
}

.filter-card {
  background: var(--panel);
  border: 1px solid var(--border);
  margin-bottom: 12px;
}

.filter-form .el-form-item {
  margin-bottom: 8px;
}

.filter-form .el-form-item__label {
  color: var(--muted);
}

.content {
  min-height: 0;
}

.aside {
  padding-right: 10px;
}

.graph-main {
  padding: 0 10px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  height: 100%;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.panel-stats {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text);
}

.list-label {
  flex: 1;
}

.list-count {
  color: var(--muted);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.line {
  width: 18px;
  height: 3px;
  border-radius: 999px;
  background: var(--link);
}

.graph-panel {
  display: flex;
  flex-direction: column;
}

.graph-wrap {
  flex: 1;
  min-height: 0;
  height: 100%;
  border-radius: 10px;
  border: 1px dashed rgba(120, 140, 170, 0.4);
  background: radial-gradient(rgba(35, 64, 108, 0.08) 1px, transparent 1px);
  background-size: 28px 28px;
}

.graph-svg {
  width: 100%;
  height: 100%;
}

.link {
  fill: none;
  stroke-width: 1.6;
  opacity: 0.8;
}

.link-label {
  fill: #51607a;
  font-size: 11px;
}

.node-title {
  fill: #22324d;
  font-size: 13px;
  font-weight: 600;
}

.node-count {
  fill: #6b7c99;
  font-size: 12px;
}

.footer {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 16px;
  background: #ffffff;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 12px;
}

.footer .ok {
  color: #44e0ae;
}

.footer .warn {
  color: #f3c969;
}

.footer .danger {
  color: #ff6b6b;
}

.el-card__body {
  padding: 12px;
}

.el-input__inner,
.el-select .el-input__inner {
  background: #ffffff;
  border: 1px solid var(--border);
  color: var(--text);
}

.el-select-dropdown__item {
  color: #303133;
}

@media (max-width: 1100px) {
  .content {
    height: auto;
  }

  .aside {
    display: none;
  }

  .graph-main {
    padding: 0;
  }
}
</style>
