<template>
  <div class="ops-root">
    <div class="header">
      <div class="logo">
        <div class="logo-icon">OG</div>
        OpsGraph
      </div>
      <div class="header-divider"></div>
      <div class="header-subtitle">运维知识图谱 v3.0</div>
      <div class="header-badges">
        <span class="badge badge-green"><span class="pulse-dot"></span> 实时同步</span>
        <span class="badge badge-blue">节点 {{ stats.nodeCount }}</span>
        <span class="badge badge-blue">关系 {{ stats.linkCount }}</span>
        <span class="badge badge-yellow">告警 {{ stats.warnCount }}</span>
        <span class="badge badge-red">异常 {{ stats.errorCount }}</span>
      </div>
    </div>

    <div class="toolbar">
      <div class="tb-group">
        <div class="tb-label">项目</div>
        <el-select v-model="filters.project" size="mini" popper-class="ops-select-popper" class="ops-select">
          <el-option label="P001 · 电商平台" value="P001"></el-option>
          <el-option label="P002 · 金融平台" value="P002"></el-option>
        </el-select>
      </div>
      <div class="tb-group">
        <div class="tb-label">实体类型</div>
        <el-select v-model="filters.entityType" size="mini" popper-class="ops-select-popper" class="ops-select">
          <el-option label="全部类型" value="all"></el-option>
          <el-option v-for="item in entityTypes" :key="item.key" :label="item.label" :value="item.key"></el-option>
        </el-select>
      </div>
      <div class="tb-group">
        <div class="tb-label">关系类型</div>
        <el-select v-model="filters.relationType" size="mini" popper-class="ops-select-popper" class="ops-select">
          <el-option label="全部关系" value="all"></el-option>
          <el-option v-for="item in relationTypes" :key="item.key" :label="item.label" :value="item.key"></el-option>
        </el-select>
      </div>
      <div class="tb-group">
        <div class="tb-label">健康状态</div>
        <el-select v-model="filters.health" size="mini" popper-class="ops-select-popper" class="ops-select">
          <el-option label="全部状态" value="all"></el-option>
          <el-option label="正常" value="ok"></el-option>
          <el-option label="告警" value="warn"></el-option>
          <el-option label="异常" value="err"></el-option>
        </el-select>
      </div>
      <div class="tb-sep"></div>
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <el-input
          v-model="filters.keyword"
          size="mini"
          class="ops-input"
          placeholder="搜索实体名称"
        ></el-input>
      </div>
      <div class="tb-spacer"></div>
      <el-button class="btn btn-primary" size="mini" @click="toggleAgg">
        {{ aggMode ? '普通视图' : '聚合视图' }}
      </el-button>
      <el-button class="btn btn-default" size="mini" @click="fitView">适应视图</el-button>
      <el-button class="btn btn-default" size="mini">刷新数据</el-button>
      <el-button class="btn btn-default" size="mini">分析报告</el-button>
      <el-button class="btn btn-default" size="mini">部署架构图</el-button>
      <el-button class="btn btn-default" size="mini">数据链路图</el-button>
    </div>

    <div class="main">
      <div class="sidebar">
        <div class="sidebar-header">
          <div class="sidebar-title">实体列表</div>
          <div class="sidebar-count">{{ stats.nodeCount }} 个实体</div>
        </div>
        <div class="sidebar-body">
          <div class="etype-group" v-for="item in entityTypes" :key="item.key">
            <div class="etype-header">
              <div class="etype-dot" :style="{ background: item.color }"></div>
              <div class="etype-name">{{ item.label }}</div>
              <div class="etype-num">{{ item.count }}</div>
              <div class="etype-arrow">▶</div>
            </div>
          </div>
        </div>
      </div>

      <div class="canvas-wrap">
        <div class="stats-bar">
          <div class="stat-item"><span class="stat-label">节点</span><span class="stat-val">{{ stats.nodeCount }}</span></div>
          <div class="stat-item"><span class="stat-label">关系</span><span class="stat-val">{{ stats.linkCount }}</span></div>
          <div class="stat-item"><span class="stat-label">项目</span><span class="stat-val">1</span></div>
          <div class="stat-item"><span class="stat-label" style="color: var(--green)">正常</span><span class="stat-val">{{ stats.okCount }}</span></div>
          <div class="stat-item"><span class="stat-label" style="color: var(--yellow)">告警</span><span class="stat-val">{{ stats.warnCount }}</span></div>
          <div class="stat-item"><span class="stat-label" style="color: var(--red)">异常</span><span class="stat-val">{{ stats.errorCount }}</span></div>
        </div>

        <div class="legend-wrap">
          <div class="legend-title">实体类型</div>
          <div class="legend-row" v-for="item in entityTypes" :key="item.key + '-legend'">
            <span class="legend-swatch" :style="{ background: item.color }"></span>
            <span class="legend-label">{{ item.label }}</span>
          </div>
          <div class="legend-sep"></div>
          <div class="legend-title">关系类型</div>
          <div class="legend-row" v-for="item in relationTypes" :key="item.key">
            <span class="legend-swatch" style="background: var(--r-access)"></span>
            <span class="legend-label">{{ item.label }}</span>
          </div>
        </div>

        <div class="minimap-wrap">
          <div class="minimap-label">概览</div>
          <svg ref="minimapSvg" id="minimap-svg"></svg>
        </div>

        <div class="canvas-controls">
          <div class="cc-btn" @click="zoomIn">+</div>
          <div class="cc-btn" @click="zoomOut">-</div>
          <div class="cc-btn" @click="resetZoom">⟳</div>
        </div>

        <svg id="graph-svg" ref="graphSvg"></svg>
      </div>

      <div class="detail-panel" :class="{ open: detailOpen }">
        <div class="detail-header">
          <div class="detail-title-bar">
            <div class="detail-type-dot" :style="{ background: selectedTypeColor }"></div>
            <div class="detail-title-text">实体详情</div>
          </div>
          <div class="detail-close" @click="detailOpen = false">✕</div>
        </div>
        <div class="detail-body" v-if="selectedNode">
          <div class="detail-section">
            <div class="detail-section-title">基本信息</div>
            <div class="detail-row">
              <div class="detail-key">名称</div>
              <div class="detail-val">{{ selectedNode.label }}</div>
            </div>
            <div class="detail-row">
              <div class="detail-key">类型</div>
              <div class="detail-val">{{ selectedNode.typeLabel }}</div>
            </div>
            <div class="detail-row">
              <div class="detail-key">状态</div>
              <div class="detail-val" :class="selectedNode.healthClass">{{ selectedNode.health }}</div>
            </div>
            <div class="detail-row" v-if="selectedNode.count">
              <div class="detail-key">数量</div>
              <div class="detail-val">{{ selectedNode.count }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="statusbar">
      <div class="sb-item">节点 <span class="sb-val">{{ stats.nodeCount }}</span></div>
      <div class="sb-item">关系 <span class="sb-val">{{ stats.linkCount }}</span></div>
      <div class="sb-item">项目 <span class="sb-val">1</span></div>
      <div class="sb-item" style="color: var(--green)">正常 <span class="sb-val">{{ stats.okCount }}</span></div>
      <div class="sb-item" style="color: var(--yellow)">告警 <span class="sb-val">{{ stats.warnCount }}</span></div>
      <div class="sb-item" style="color: var(--red)">异常 <span class="sb-val">{{ stats.errorCount }}</span></div>
      <div class="sb-spacer"></div>
      <div class="sb-time">{{ nowTime }}</div>
    </div>

    <div
      class="tooltip-el"
      :class="{ visible: tooltip.visible }"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tt-name" :style="{ color: tooltip.color }">{{ tooltip.title }}</div>
      <div class="tt-row" v-for="row in tooltip.rows" :key="row.key">
        <span class="tt-key">{{ row.key }}</span>
        <span class="tt-val" :style="{ color: row.color || 'var(--text)' }">{{ row.value }}</span>
      </div>
    </div>
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
        health: 'all',
        keyword: ''
      },
      stats: {
        nodeCount: 8,
        linkCount: 7,
        okCount: 10,
        warnCount: 4,
        errorCount: 5
      },
      entityTypes: [
        { key: 'user', label: '用户', color: '#4db8ff', count: 1 },
        { key: 'domain', label: '域名上下文', color: '#00e5ff', count: 2 },
        { key: 'api', label: 'API接口', color: '#ff8c33', count: 3 },
        { key: 'service', label: '应用微服务', color: '#00d68f', count: 4 },
        { key: 'db', label: '数据库', color: '#ffcc00', count: 2 },
        { key: 'middleware', label: '中间件', color: '#9d6fff', count: 2 },
        { key: 'compute', label: '计算资源', color: '#7fa8cc', count: 3 },
        { key: 'alarm', label: '告警', color: '#ff4040', count: 2 }
      ],
      relationTypes: [
        { key: 'access', label: '访问' },
        { key: 'call', label: '调用' },
        { key: 'lb', label: '负载均衡' },
        { key: 'host', label: '承载' },
        { key: 'monitor', label: '监控' }
      ],
      graphData: {
        nodes: [
          { id: 'user', label: '用户', type: 'user', health: '正常', x: 180, y: 360 },
          { id: 'domain', label: '域名上下文', type: 'domain', health: '正常', x: 360, y: 360 },
          { id: 'api', label: 'API接口', type: 'api', health: '告警', x: 540, y: 360 },
          { id: 'service', label: '应用微服务', type: 'service', health: '正常', x: 720, y: 360 },
          { id: 'middleware', label: '中间件', type: 'middleware', health: '正常', x: 900, y: 360 },
          { id: 'alarm', label: '告警', type: 'alarm', health: '异常', x: 1080, y: 360 },
          { id: 'db', label: '数据库', type: 'db', health: '告警', x: 840, y: 210 },
          { id: 'compute', label: '计算资源', type: 'compute', health: '正常', x: 840, y: 520 }
        ],
        links: [
          { source: 'user', target: 'domain', type: 'access' },
          { source: 'domain', target: 'api', type: 'call' },
          { source: 'api', target: 'service', type: 'call' },
          { source: 'service', target: 'middleware', type: 'lb' },
          { source: 'middleware', target: 'alarm', type: 'monitor' },
          { source: 'service', target: 'db', type: 'host' },
          { source: 'service', target: 'compute', type: 'host' }
        ]
      },
      nowTime: '',
      aggMode: false,
      detailOpen: true,
      selectedNode: null,
      tooltip: {
        visible: false,
        x: 0,
        y: 0,
        title: '',
        color: 'var(--accent2)',
        rows: []
      }
    }
  },
  computed: {
    selectedTypeColor() {
      if (!this.selectedNode) return 'var(--c-domain)'
      return this.colorByType(this.selectedNode.type)
    }
  },
  mounted() {
    this.updateTime()
    this.renderGraph()
    window.addEventListener('resize', this.renderGraph)
    this._timeTimer = setInterval(this.updateTime, 1000)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.renderGraph)
    clearInterval(this._timeTimer)
  },
  methods: {
    updateTime() {
      const now = new Date()
      const pad = (n) => String(n).padStart(2, '0')
      this.nowTime = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
    },
    toggleAgg() {
      this.aggMode = !this.aggMode
      this.renderGraph()
    },
    fitView() {
      this.resetZoom()
    },
    zoomIn() {
      if (this._zoom) {
        this._zoom.scaleBy(d3.select(this.$refs.graphSvg), 1.2)
      }
    },
    zoomOut() {
      if (this._zoom) {
        this._zoom.scaleBy(d3.select(this.$refs.graphSvg), 0.8)
      }
    },
    resetZoom() {
      if (this._zoom) {
        d3.select(this.$refs.graphSvg).transition().duration(200).call(this._zoom.transform, d3.zoomIdentity)
      }
    },
    getGraphViewData() {
      if (!this.aggMode) {
        return { nodes: this.graphData.nodes, links: this.graphData.links }
      }

      const typeMap = new Map()
      this.graphData.nodes.forEach((n) => {
        const key = n.type
        if (!typeMap.has(key)) {
          typeMap.set(key, { id: `type-${key}`, type: key, label: this.typeLabel(key), count: 0, health: '正常' })
        }
        const agg = typeMap.get(key)
        agg.count += 1
        if (n.health === '异常') agg.health = '异常'
        else if (n.health === '告警' && agg.health !== '异常') agg.health = '告警'
      })

      const nodes = Array.from(typeMap.values())
      const cols = 4
      const gapX = 210
      const gapY = 150
      nodes.forEach((n, i) => {
        const col = i % cols
        const row = Math.floor(i / cols)
        n.x = 220 + col * gapX
        n.y = 220 + row * gapY
      })

      const linkCount = new Map()
      this.graphData.links.forEach((l) => {
        const sourceType = this.nodeTypeById(l.source)
        const targetType = this.nodeTypeById(l.target)
        if (!sourceType || !targetType) return
        const key = `${sourceType}|${targetType}`
        linkCount.set(key, (linkCount.get(key) || 0) + 1)
      })

      const links = Array.from(linkCount.entries()).map(([key, count]) => {
        const [sourceType, targetType] = key.split('|')
        return {
          source: `type-${sourceType}`,
          target: `type-${targetType}`,
          count
        }
      })

      return { nodes, links }
    },
    nodeTypeById(id) {
      const node = this.graphData.nodes.find((n) => n.id === id)
      return node ? node.type : null
    },
    typeLabel(type) {
      const hit = this.entityTypes.find((t) => t.key === type)
      return hit ? hit.label : type
    },
    renderGraph() {
      const svgEl = this.$refs.graphSvg
      if (!svgEl) return

      const wrap = svgEl.parentElement
      const width = wrap.clientWidth
      const height = wrap.clientHeight

      const svg = d3.select(svgEl)
      svg.selectAll('*').remove()
      svg.attr('width', width).attr('height', height)

      const root = svg.append('g')

      const zoom = d3.zoom().scaleExtent([0.2, 4]).on('zoom', (event) => {
        root.attr('transform', event.transform)
        this._currentTransform = event.transform
        this.updateMinimapViewport(width, height)
      })
      svg.call(zoom)
      this._zoom = zoom
      this._currentTransform = d3.zoomIdentity

      const { nodes, links } = this.getGraphViewData()
      const d3Nodes = nodes.map((n) => ({ ...n, w: this.aggMode ? 140 : 120, h: this.aggMode ? 46 : 42 }))
      const nodeById = new Map(d3Nodes.map((n) => [n.id, n]))
      const d3Links = links
        .map((l) => ({ ...l, source: nodeById.get(l.source), target: nodeById.get(l.target) }))
        .filter((l) => l.source && l.target)

      const edgeG = root.append('g')
      edgeG
        .selectAll('path')
        .data(d3Links)
        .enter()
        .append('path')
        .attr('class', 'edge-path')
        .attr('stroke', 'var(--r-access)')
        .attr('stroke-width', 1.2)
        .attr('stroke-opacity', 0.55)
        .attr('fill', 'none')
        .attr('d', (d) => `M${d.source.x},${d.source.y} L${d.target.x},${d.target.y}`)

      const nodeG = root.append('g')
      const node = nodeG
        .selectAll('g')
        .data(d3Nodes)
        .enter()
        .append('g')
        .attr('class', 'node-g')
        .attr('transform', (d) => `translate(${d.x - d.w / 2}, ${d.y - d.h / 2})`)
        .on('click', (event, d) => this.openDetail(d))
        .on('mousemove', (event, d) => this.showTooltip(event, d, d3Links))
        .on('mouseleave', () => this.hideTooltip())

      node
        .append('rect')
        .attr('class', 'node-body')
        .attr('width', (d) => d.w)
        .attr('height', (d) => d.h)
        .attr('fill', '#0f1e33')
        .attr('stroke', (d) => this.colorByType(d.type))
        .attr('stroke-width', 1.3)

      node
        .append('rect')
        .attr('width', 4)
        .attr('height', (d) => d.h)
        .attr('fill', (d) => this.colorByType(d.type))

      node
        .append('text')
        .attr('x', 10)
        .attr('y', 24)
        .attr('fill', '#cce4ff')
        .attr('font-size', 11)
        .attr('font-weight', 600)
        .attr('font-family', 'Noto Sans SC, sans-serif')
        .text((d) => d.label)

      if (this.aggMode) {
        node
          .append('text')
          .attr('x', (d) => d.w - 12)
          .attr('y', 14)
          .attr('text-anchor', 'end')
          .attr('fill', '#7fa8cc')
          .attr('font-size', 9)
          .attr('font-family', 'IBM Plex Mono, monospace')
          .text((d) => `×${d.count}`)
      }

      this.renderMinimap(d3Nodes, d3Links, width, height)
    },
    renderMinimap(nodes, links, width, height) {
      const svgEl = this.$refs.minimapSvg
      if (!svgEl) return
      const w = 168
      const h = 106
      const padding = 40

      const minX = Math.min(...nodes.map((n) => n.x)) - padding
      const maxX = Math.max(...nodes.map((n) => n.x)) + padding
      const minY = Math.min(...nodes.map((n) => n.y)) - padding
      const maxY = Math.max(...nodes.map((n) => n.y)) + padding

      const scale = Math.min(w / (maxX - minX), h / (maxY - minY))
      const offsetX = (w - (maxX - minX) * scale) / 2
      const offsetY = (h - (maxY - minY) * scale) / 2

      const mapX = (x) => (x - minX) * scale + offsetX
      const mapY = (y) => (y - minY) * scale + offsetY

      const svg = d3.select(svgEl)
      svg.selectAll('*').remove()
      svg.attr('width', w).attr('height', h)

      svg
        .append('g')
        .selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('x1', (d) => mapX(d.source.x))
        .attr('y1', (d) => mapY(d.source.y))
        .attr('x2', (d) => mapX(d.target.x))
        .attr('y2', (d) => mapY(d.target.y))
        .attr('stroke', 'rgba(77,184,255,0.4)')
        .attr('stroke-width', 0.8)

      svg
        .append('g')
        .selectAll('circle')
        .data(nodes)
        .enter()
        .append('circle')
        .attr('cx', (d) => mapX(d.x))
        .attr('cy', (d) => mapY(d.y))
        .attr('r', 2)
        .attr('fill', '#4db8ff')

      this._minimap = { minX, minY, scale, offsetX, offsetY, width: w, height: h }
      this._minimapSvg = svg
      this.updateMinimapViewport(width, height)
    },
    updateMinimapViewport(viewW, viewH) {
      if (!this._minimap || !this._minimapSvg) return
      const { minX, minY, scale, offsetX, offsetY, width, height } = this._minimap
      const t = this._currentTransform || d3.zoomIdentity

      const worldX = -t.x / t.k
      const worldY = -t.y / t.k
      const worldW = viewW / t.k
      const worldH = viewH / t.k

      const rectX = (worldX - minX) * scale + offsetX
      const rectY = (worldY - minY) * scale + offsetY
      const rectW = worldW * scale
      const rectH = worldH * scale

      this._minimapSvg.selectAll('rect.viewport').remove()
      this._minimapSvg
        .append('rect')
        .attr('class', 'viewport')
        .attr('x', rectX)
        .attr('y', rectY)
        .attr('width', Math.min(rectW, width))
        .attr('height', Math.min(rectH, height))
        .attr('fill', 'rgba(26,159,255,0.12)')
        .attr('stroke', 'rgba(77,184,255,0.7)')
        .attr('stroke-width', 0.8)
    },
    openDetail(node) {
      this.detailOpen = true
      this.selectedNode = {
        label: node.label,
        type: node.type,
        typeLabel: this.typeLabel(node.type),
        health: node.health || '正常',
        count: node.count,
        healthClass: node.health === '异常' ? 'err' : node.health === '告警' ? 'warn' : 'ok'
      }
    },
    showTooltip(event, node, links) {
      const inCount = links.filter((l) => l.target.id === node.id).length
      const outCount = links.filter((l) => l.source.id === node.id).length
      const color = this.colorByType(node.type)

      this.tooltip.title = node.label
      this.tooltip.color = color
      this.tooltip.rows = [
        { key: '类型', value: this.typeLabel(node.type) },
        { key: '状态', value: node.health || '正常', color: node.health === '异常' ? 'var(--red)' : node.health === '告警' ? 'var(--yellow)' : 'var(--green)' },
        { key: '上游', value: `${inCount} 条` },
        { key: '下游', value: `${outCount} 条` }
      ]

      this.tooltip.x = event.clientX + 12
      this.tooltip.y = event.clientY + 12
      this.tooltip.visible = true
    },
    hideTooltip() {
      this.tooltip.visible = false
    },
    colorByType(type) {
      const hit = this.entityTypes.find((t) => t.key === type)
      return hit ? hit.color : '#4db8ff'
    }
  }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

:root {
  --bg: #060b14;
  --bg1: #091120;
  --bg2: #0c1628;
  --panel: #0f1e33;
  --panel2: #152540;
  --panel3: #1a2d4a;
  --border: #1e3554;
  --border2: #234065;
  --border3: #2a4d78;
  --accent: #1a9fff;
  --accent2: #4db8ff;
  --accent3: #80d0ff;
  --green: #00d68f;
  --green2: #00ff9d;
  --yellow: #ffcc00;
  --yellow2: #ffe033;
  --red: #ff4040;
  --red2: #ff6666;
  --purple: #9d6fff;
  --orange: #ff8c33;
  --cyan: #00e5ff;
  --text: #cce4ff;
  --text2: #7fa8cc;
  --text3: #4a6e8a;
  --text4: #2d4a60;

  --c-user: #4db8ff;
  --c-svc: #00d68f;
  --c-db: #ffcc00;
  --c-mw: #9d6fff;
  --c-api: #ff8c33;
  --c-compute: #7fa8cc;
  --c-alert: #ff4040;
  --c-domain: #00e5ff;

  --r-access: #4db8ff;
  --r-call: #00d68f;
  --r-lb: #9d6fff;
  --r-host: #7fa8cc;
  --r-monitor: #ff4040;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { width: 100%; height: 100%; overflow: hidden; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Noto Sans SC', sans-serif;
}

.ops-root {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

.header {
  height: 48px;
  background: var(--bg1);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  flex-shrink: 0;
  position: relative;
  z-index: 100;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--accent2);
  letter-spacing: -0.01em;
  white-space: nowrap;
}
.logo-icon {
  width: 28px; height: 28px;
  background: linear-gradient(135deg, var(--accent), var(--purple));
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
  color: #fff;
}
.header-divider { width: 1px; height: 20px; background: var(--border2); }
.header-subtitle { font-size: 12px; color: var(--text3); font-family: 'IBM Plex Mono'; }
.header-badges { display: flex; gap: 6px; margin-left: auto; align-items: center; }
.badge {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-family: 'IBM Plex Mono';
  letter-spacing: 0.02em;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.badge-blue { background: rgba(26,159,255,0.12); color: var(--accent2); border: 1px solid rgba(26,159,255,0.25); }
.badge-green { background: rgba(0,214,143,0.12); color: var(--green); border: 1px solid rgba(0,214,143,0.25); }
.badge-yellow { background: rgba(255,204,0,0.12); color: var(--yellow); border: 1px solid rgba(255,204,0,0.25); }
.badge-red { background: rgba(255,64,64,0.12); color: var(--red); border: 1px solid rgba(255,64,64,0.25); }
.pulse-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--green);
  box-shadow: 0 0 6px var(--green);
  animation: pulse-glow 2s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%,100% { opacity: 1; box-shadow: 0 0 6px var(--green); }
  50% { opacity: 0.5; box-shadow: 0 0 2px var(--green); }
}

.toolbar {
  height: 46px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 10px;
  flex-shrink: 0;
  overflow-x: auto;
}
.toolbar::-webkit-scrollbar { height: 0; }
.tb-group { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.tb-label { font-size: 11px; color: var(--text3); white-space: nowrap; }
.tb-sep { width: 1px; height: 22px; background: var(--border); flex-shrink: 0; }
.tb-spacer { flex: 1; }

.search-wrap { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 8px; color: var(--text3); font-size: 11px; pointer-events: none; }

.btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 4px;
  border: 1px solid var(--border2);
  cursor: pointer;
  font-size: 12px;
  font-family: 'Noto Sans SC', sans-serif;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}
.btn-default { background: var(--panel); color: var(--text2); }
.btn-default:hover { background: var(--panel2); color: var(--text); border-color: var(--accent); }
.btn-primary { background: rgba(26,159,255,0.15); color: var(--accent2); border-color: rgba(26,159,255,0.35); }
.btn-primary:hover { background: rgba(26,159,255,0.25); }

.main { display: flex; flex: 1; overflow: hidden; position: relative; }

.sidebar {
  width: 250px;
  flex-shrink: 0;
  background: var(--bg1);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-header {
  padding: 10px 12px 8px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sidebar-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text3);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: 'IBM Plex Mono';
}
.sidebar-count { font-size: 11px; color: var(--text3); font-family: 'IBM Plex Mono'; }
.sidebar-body { flex: 1; overflow-y: auto; }

.etype-group { border-bottom: 1px solid var(--border); }
.etype-header {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: background 0.12s;
  user-select: none;
}
.etype-header:hover { background: var(--panel); }
.etype-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.etype-name { font-size: 12px; flex: 1; }
.etype-num { font-size: 10px; font-family: 'IBM Plex Mono'; color: var(--text3); }
.etype-arrow { font-size: 9px; color: var(--text4); }

.canvas-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: var(--bg);
}
.canvas-wrap::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle 600px at 15% 30%, rgba(26,159,255,0.03) 0%, transparent 70%),
    radial-gradient(circle 400px at 85% 70%, rgba(157,111,255,0.025) 0%, transparent 70%);
  pointer-events: none;
}
.canvas-wrap::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(30,53,84,0.8) 1px, transparent 1px);
  background-size: 28px 28px;
  pointer-events: none;
  opacity: 0.4;
}
#graph-svg { width: 100%; height: 100%; display: block; }

.canvas-controls {
  position: absolute;
  bottom: 18px;
  right: 18px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  z-index: 10;
}
.cc-btn {
  width: 30px; height: 30px;
  background: var(--panel);
  border: 1px solid var(--border2);
  border-radius: 5px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text2);
  font-size: 15px;
  font-weight: 600;
  transition: all 0.12s;
  user-select: none;
}
.cc-btn:hover { background: var(--panel2); color: var(--accent2); border-color: var(--accent); }

.minimap-wrap {
  position: absolute;
  bottom: 18px;
  left: 260px;
  width: 168px;
  height: 106px;
  background: rgba(9,17,32,0.9);
  border: 1px solid var(--border2);
  border-radius: 6px;
  overflow: hidden;
  z-index: 10;
  backdrop-filter: blur(4px);
}
.minimap-label {
  position: absolute;
  top: 4px;
  left: 6px;
  font-size: 9px;
  font-family: 'IBM Plex Mono';
  color: var(--text4);
  pointer-events: none;
  z-index: 1;
}
#minimap-svg { width: 100%; height: 100%; }

.stats-bar {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 1px;
  background: var(--border);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border2);
  z-index: 10;
}
.stat-item {
  padding: 5px 14px;
  background: var(--panel);
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: 'IBM Plex Mono';
}
.stat-label { color: var(--text3); }
.stat-val { color: var(--text); font-weight: 500; }

.legend-wrap {
  position: absolute;
  top: 14px;
  right: 14px;
  background: rgba(9,17,32,0.88);
  border: 1px solid var(--border2);
  border-radius: 6px;
  padding: 10px 12px;
  z-index: 10;
  backdrop-filter: blur(6px);
}
.legend-title { font-size: 9px; font-family: 'IBM Plex Mono'; color: var(--text3); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 7px; }
.legend-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.legend-swatch { width: 12px; height: 8px; border-radius: 2px; }
.legend-label { font-size: 11px; color: var(--text2); }
.legend-sep { height: 1px; background: var(--border); margin: 6px 0; }

.detail-panel {
  width: 0;
  flex-shrink: 0;
  background: var(--bg1);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.22s cubic-bezier(0.4,0,0.2,1);
}
.detail-panel.open { width: 280px; }
.detail-header {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.detail-title-bar { display: flex; align-items: center; gap: 7px; }
.detail-type-dot { width: 10px; height: 10px; border-radius: 2px; }
.detail-title-text { font-size: 13px; font-weight: 500; }
.detail-close { cursor: pointer; color: var(--text3); font-size: 14px; transition: color 0.12s; }
.detail-close:hover { color: var(--text); }
.detail-body { flex: 1; overflow-y: auto; padding: 0; }
.detail-section { border-bottom: 1px solid var(--border); }
.detail-section-title {
  padding: 8px 14px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text3);
  font-family: 'IBM Plex Mono';
  background: rgba(0,0,0,0.15);
}
.detail-row {
  display: flex;
  align-items: flex-start;
  padding: 5px 14px;
  gap: 8px;
  border-bottom: 1px solid rgba(30,53,84,0.5);
}
.detail-row:last-child { border-bottom: none; }
.detail-key { font-size: 11px; color: var(--text3); min-width: 80px; flex-shrink: 0; padding-top: 1px; }
.detail-val { font-size: 11px; color: var(--text); font-family: 'IBM Plex Mono'; word-break: break-all; }
.detail-val.ok { color: var(--green); }
.detail-val.warn { color: var(--yellow); }
.detail-val.err { color: var(--red); }

.statusbar {
  height: 24px;
  background: var(--bg1);
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 18px;
  flex-shrink: 0;
}
.sb-item { display: flex; align-items: center; gap: 5px; font-size: 10px; font-family: 'IBM Plex Mono'; color: var(--text3); }
.sb-val { color: var(--text2); }
.sb-spacer { flex: 1; }
.sb-time { color: var(--text4); }

.node-g { cursor: pointer; }
.node-body { rx: 5; ry: 5; transition: filter 0.2s; }
.node-g:hover .node-body { filter: brightness(1.25); }
.edge-path { fill: none; transition: stroke-opacity 0.2s; }

.tooltip-el {
  position: fixed;
  background: var(--panel2);
  border: 1px solid var(--border3);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 11px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.12s;
  z-index: 9999;
  max-width: 240px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(26,159,255,0.08);
  backdrop-filter: blur(8px);
}
.tooltip-el.visible { opacity: 1; }
.tt-name { font-weight: 600; color: var(--accent2); margin-bottom: 7px; font-size: 12px; }
.tt-row { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 3px; }
.tt-key { color: var(--text3); }
.tt-val { color: var(--text); font-family: 'IBM Plex Mono'; }

.ops-select .el-input__inner,
.ops-input .el-input__inner {
  background: var(--panel);
  border: 1px solid var(--border2);
  color: var(--text);
  height: 28px;
  line-height: 28px;
  font-size: 12px;
  border-radius: 4px;
  padding-left: 8px;
}
.ops-input .el-input__inner { padding-left: 22px; }

.el-button.btn {
  background: var(--panel);
  border: 1px solid var(--border2);
  color: var(--text2);
}
.el-button.btn.btn-primary {
  background: rgba(26,159,255,0.15);
  color: var(--accent2);
  border-color: rgba(26,159,255,0.35);
}
.el-button.btn.btn-default:hover {
  background: var(--panel2);
  color: var(--text);
  border-color: var(--accent);
}

.ops-select-popper .el-select-dropdown__item { color: #cce4ff; }
.ops-select-popper { background: var(--panel2); border: 1px solid var(--border2); }
</style>
