<template>
  <div class="ops-root light">
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
          <el-option v-for="item in projectOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
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
      <el-button class="btn btn-default" size="mini" :loading="refreshing" @click="doRefresh">刷新数据</el-button>
      <el-button class="btn btn-default" size="mini" @click="showAnalysis">分析报告</el-button>
      <el-button class="btn btn-default" size="mini" @click="showDeployDiagram">部署架构图</el-button>
      <el-button class="btn btn-default" size="mini" @click="showDataFlowDiagram">数据链路图</el-button>
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
            <span class="legend-swatch" :style="{ background: relationColor(item.key) }"></span>
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

      <div class="chat-sidebar" :class="{ collapsed: chatCollapsed }">
        <div v-show="!chatCollapsed" class="chat-sidebar-toggle">
          <div class="chat-sidebar-title">
            <img class="chat-agent-icon" src="./assets/robot-flat.svg" alt="机器人" />
            <span>智能客服</span>
          </div>
          <div class="chat-collapse-btn" @click="chatCollapsed = true">
            <i class="el-icon-arrow-right"></i>
          </div>
        </div>
        <div v-show="!chatCollapsed" class="chat-sidebar-body">
          <chat-dialog ref="opsChat" @send="handleChatSend"></chat-dialog>
        </div>
      </div>

      <div v-if="chatCollapsed" class="chat-fab" @click="chatCollapsed = false" title="打开智能客服">
        <img class="chat-agent-icon" src="./assets/robot-flat.svg" alt="机器人" />
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

    <div class="skill-overlay" :class="{ visible: deployPanelVisible }">
      <div class="skill-topbar">
        <span class="skill-topbar-title">部署架构图</span>
        <span class="skill-topbar-sub">{{ deploySubtitle }}</span>
        <el-button class="btn btn-default skill-top-btn" size="mini" @click="exportSkillSVG('deploySvg', 'deploy-arch.svg')">导出 SVG</el-button>
        <el-button class="btn btn-default skill-top-btn" size="mini" @click="closeSkillPanel('deploy')">关闭</el-button>
      </div>
      <div class="skill-canvas">
        <svg ref="deploySvg"></svg>
      </div>
      <div class="skill-legend">
        <div class="skill-legend-item" v-for="item in deployLegendItems" :key="`deploy-${item.label}`">
          <span class="skill-legend-dot" :style="{ background: item.color }"></span>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div class="skill-overlay" :class="{ visible: dataflowPanelVisible }">
      <div class="skill-topbar">
        <span class="skill-topbar-title">数据链路图</span>
        <span class="skill-topbar-sub">{{ dataflowSubtitle }}</span>
        <el-button class="btn btn-default skill-top-btn" size="mini" @click="exportSkillSVG('dataflowSvg', 'data-flow.svg')">导出 SVG</el-button>
        <el-button class="btn btn-default skill-top-btn" size="mini" @click="closeSkillPanel('dataflow')">关闭</el-button>
      </div>
      <div class="skill-canvas">
        <svg ref="dataflowSvg"></svg>
      </div>
      <div class="skill-legend">
        <div class="skill-legend-item" v-for="item in dataflowLegendItems" :key="`flow-${item.label}`">
          <span class="skill-legend-line" :style="{ background: item.color }"></span>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div class="modal-overlay" :class="{ visible: analysisVisible }" @click.self="closeModal">
      <div class="modal-box">
        <div class="modal-title">图谱分析报告</div>
        <div class="modal-body">
          <div class="analysis-line" v-for="(line, index) in analysisLines" :key="`analysis-${index}`">{{ line }}</div>
        </div>
        <div class="modal-footer">
          <el-button class="btn btn-primary" size="mini" @click="closeModal">关闭</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
import ChatDialog from './components/ChatDialog.vue'

export default {
  name: 'App',
  components: {
    ChatDialog
  },
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
        nodeCount: 26,
        linkCount: 30,
        okCount: 17,
        warnCount: 8,
        errorCount: 1
      },
      projectOptions: [
        { label: 'P001 · 电商平台', value: 'P001' },
        { label: 'P002 · 金融平台', value: 'P002' }
      ],
      entityTypes: [
        { key: 'user', label: '用户', color: '#4db8ff', count: 2 },
        { key: 'domain', label: '域名上下文', color: '#00e5ff', count: 2 },
        { key: 'api', label: 'API接口', color: '#ff8c33', count: 5 },
        { key: 'service', label: '应用微服务', color: '#00d68f', count: 5 },
        { key: 'db', label: '数据库', color: '#ffcc00', count: 4 },
        { key: 'middleware', label: '中间件', color: '#9d6fff', count: 4 },
        { key: 'compute', label: '计算资源', color: '#7fa8cc', count: 2 },
        { key: 'alarm', label: '告警', color: '#ff4040', count: 2 }
      ],
      relationTypes: [
        { key: 'access', label: '访问' },
        { key: 'call', label: '调用' },
        { key: 'lb', label: '负载均衡' },
        { key: 'host', label: '承载' },
        { key: 'monitor', label: '监控' }
      ],
      relationColors: {
        access: '#4db8ff',
        call: '#00d68f',
        lb: '#9d6fff',
        host: '#7fa8cc',
        monitor: '#ff4040'
      },
      graphData: {
        nodes: [
          { id: 'user-p001', label: '用户入口(P001)', type: 'user', health: '正常', project: 'P001', x: 120, y: 300 },
          { id: 'domain-p001', label: '域名上下文(P001)', type: 'domain', health: '正常', project: 'P001', x: 300, y: 300 },
          { id: 'api-gw-p001', label: 'API网关(P001)', type: 'api', health: '正常', project: 'P001', x: 480, y: 220 },
          { id: 'api-order-p001', label: '订单API(P001)', type: 'api', health: '告警', project: 'P001', x: 480, y: 300 },
          { id: 'api-pay-p001', label: '支付API(P001)', type: 'api', health: '正常', project: 'P001', x: 480, y: 380 },
          { id: 'svc-order-p001', label: '订单服务(P001)', type: 'service', health: '告警', project: 'P001', x: 680, y: 250 },
          { id: 'svc-pay-p001', label: '支付服务(P001)', type: 'service', health: '正常', project: 'P001', x: 680, y: 330 },
          { id: 'svc-inv-p001', label: '库存服务(P001)', type: 'service', health: '正常', project: 'P001', x: 680, y: 410 },
          { id: 'mq-p001', label: '消息队列(P001)', type: 'middleware', health: '正常', project: 'P001', x: 870, y: 260 },
          { id: 'redis-p001', label: 'Redis缓存(P001)', type: 'middleware', health: '告警', project: 'P001', x: 870, y: 340 },
          { id: 'db-order-p001', label: '订单库(P001)', type: 'db', health: '正常', project: 'P001', x: 1040, y: 250 },
          { id: 'db-pay-p001', label: '支付库(P001)', type: 'db', health: '告警', project: 'P001', x: 1040, y: 330 },
          { id: 'k8s-p001', label: 'K8S集群(P001)', type: 'compute', health: '正常', project: 'P001', x: 1040, y: 430 },
          { id: 'alarm-p001', label: '核心告警(P001)', type: 'alarm', health: '异常', project: 'P001', x: 1220, y: 330 },

          { id: 'user-p002', label: '用户入口(P002)', type: 'user', health: '正常', project: 'P002', x: 120, y: 560 },
          { id: 'domain-p002', label: '域名上下文(P002)', type: 'domain', health: '正常', project: 'P002', x: 300, y: 560 },
          { id: 'api-core-p002', label: '核心API(P002)', type: 'api', health: '正常', project: 'P002', x: 480, y: 520 },
          { id: 'api-risk-p002', label: '风控API(P002)', type: 'api', health: '告警', project: 'P002', x: 480, y: 600 },
          { id: 'svc-core-p002', label: '核心服务(P002)', type: 'service', health: '正常', project: 'P002', x: 680, y: 520 },
          { id: 'svc-risk-p002', label: '风控服务(P002)', type: 'service', health: '告警', project: 'P002', x: 680, y: 600 },
          { id: 'kafka-p002', label: 'Kafka集群(P002)', type: 'middleware', health: '正常', project: 'P002', x: 870, y: 520 },
          { id: 'es-p002', label: 'ES检索(P002)', type: 'middleware', health: '正常', project: 'P002', x: 870, y: 600 },
          { id: 'db-core-p002', label: '核心库(P002)', type: 'db', health: '正常', project: 'P002', x: 1040, y: 520 },
          { id: 'db-risk-p002', label: '风控库(P002)', type: 'db', health: '告警', project: 'P002', x: 1040, y: 600 },
          { id: 'vm-p002', label: '计算节点(P002)', type: 'compute', health: '正常', project: 'P002', x: 1040, y: 680 },
          { id: 'alarm-p002', label: '风控告警(P002)', type: 'alarm', health: '告警', project: 'P002', x: 1220, y: 600 }
        ],
        links: [
          { source: 'user-p001', target: 'domain-p001', type: 'access' },
          { source: 'domain-p001', target: 'api-gw-p001', type: 'call' },
          { source: 'domain-p001', target: 'api-order-p001', type: 'call' },
          { source: 'domain-p001', target: 'api-pay-p001', type: 'call' },
          { source: 'api-gw-p001', target: 'svc-order-p001', type: 'call' },
          { source: 'api-order-p001', target: 'svc-order-p001', type: 'call' },
          { source: 'api-pay-p001', target: 'svc-pay-p001', type: 'call' },
          { source: 'api-order-p001', target: 'svc-inv-p001', type: 'call' },
          { source: 'svc-order-p001', target: 'mq-p001', type: 'lb' },
          { source: 'svc-pay-p001', target: 'redis-p001', type: 'lb' },
          { source: 'svc-inv-p001', target: 'redis-p001', type: 'lb' },
          { source: 'svc-order-p001', target: 'db-order-p001', type: 'host' },
          { source: 'svc-pay-p001', target: 'db-pay-p001', type: 'host' },
          { source: 'svc-inv-p001', target: 'k8s-p001', type: 'host' },
          { source: 'mq-p001', target: 'alarm-p001', type: 'monitor' },
          { source: 'redis-p001', target: 'alarm-p001', type: 'monitor' },
          { source: 'db-pay-p001', target: 'alarm-p001', type: 'monitor' },

          { source: 'user-p002', target: 'domain-p002', type: 'access' },
          { source: 'domain-p002', target: 'api-core-p002', type: 'call' },
          { source: 'domain-p002', target: 'api-risk-p002', type: 'call' },
          { source: 'api-core-p002', target: 'svc-core-p002', type: 'call' },
          { source: 'api-risk-p002', target: 'svc-risk-p002', type: 'call' },
          { source: 'svc-core-p002', target: 'kafka-p002', type: 'lb' },
          { source: 'svc-risk-p002', target: 'es-p002', type: 'lb' },
          { source: 'svc-core-p002', target: 'db-core-p002', type: 'host' },
          { source: 'svc-risk-p002', target: 'db-risk-p002', type: 'host' },
          { source: 'svc-risk-p002', target: 'vm-p002', type: 'host' },
          { source: 'kafka-p002', target: 'alarm-p002', type: 'monitor' },
          { source: 'db-risk-p002', target: 'alarm-p002', type: 'monitor' },
          { source: 'es-p002', target: 'alarm-p002', type: 'monitor' }
        ]
      },
      nowTime: '',
      aggMode: false,
      refreshing: false,
      detailOpen: true,
      chatCollapsed: false,
      analysisVisible: false,
      analysisLines: [],
      deployPanelVisible: false,
      dataflowPanelVisible: false,
      deploySubtitle: '基于知识图谱自动生成',
      dataflowSubtitle: '基于知识图谱自动生成',
      deployLegendItems: [],
      dataflowLegendItems: [],
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
      if (!this.selectedNode) return this.relationColors.access
      return this.colorByType(this.selectedNode.type)
    }
  },
  watch: {
    filters: {
      deep: true,
      handler() {
        this.renderGraph()
        if (this.deployPanelVisible) this.$nextTick(() => this.renderDeployDiagram())
        if (this.dataflowPanelVisible) this.$nextTick(() => this.renderDataFlowDiagram())
      }
    }
  },
  mounted() {
    this.updateTime()
    this.loadAllData()
      .then(() => {
        this.applyBootstrapFromUrl()
      })
      .catch(() => {})
    this.registerAgentBridge()
    window.addEventListener('resize', this.handleResize)
    this._timeTimer = setInterval(this.updateTime, 1000)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize)
    this.unregisterAgentBridge()
    clearInterval(this._timeTimer)
  },
  methods: {
    handleResize() {
      this.renderGraph()
      if (this.deployPanelVisible) this.$nextTick(() => this.renderDeployDiagram())
      if (this.dataflowPanelVisible) this.$nextTick(() => this.renderDataFlowDiagram())
    },
    notify(type, message) {
      if (this.$message && typeof this.$message[type] === 'function') {
        this.$message[type](message)
      }
    },
    updateTime() {
      const now = new Date()
      const pad = (n) => String(n).padStart(2, '0')
      this.nowTime = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
    },

    // ===== Data loaders (placeholders for backend integration) =====
    async loadAllData() {
      await Promise.all([
        this.fetchProjects(),
        this.fetchEntityTypes(),
        this.fetchRelationTypes(),
        this.fetchStats(),
        this.fetchGraphData(),
        this.fetchDetailData()
      ])
      this.$nextTick(() => this.renderGraph())
    },
    async fetchProjects() {
      // TODO: backend returns {status:'', data:{datas:[]}}
      // const res = await fetch('/api/projects')
      // const payload = await res.json()
      const payload = { status: 'ok', data: { datas: this.projectOptions } }
      const list = (payload && payload.data && payload.data.datas) || []
      this.projectOptions = list
      if (list[0] && !this.filters.project) this.filters.project = list[0].value
    },
    async fetchEntityTypes() {
      // TODO: backend returns {status:'', data:[]}
      // const res = await fetch('/api/entity-types')
      // const payload = await res.json()
      const payload = { status: 'ok', data: this.entityTypes }
      this.entityTypes = payload.data || []
    },
    async fetchRelationTypes() {
      // TODO: backend structure TBD
      const payload = { status: 'ok', data: this.relationTypes }
      this.relationTypes = payload.data || []
    },
    async fetchStats() {
      // TODO: backend structure TBD
      const payload = { status: 'ok', data: this.stats }
      this.stats = payload.data || this.stats
    },
    async fetchGraphData() {
      // TODO: backend structure TBD
      const payload = { status: 'ok', data: this.graphData }
      this.graphData = payload.data || this.graphData
    },
    async fetchDetailData() {
      // TODO: backend structure TBD
      return Promise.resolve()
    },
    waitMs(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms))
    },
    normalizeText(text) {
      return String(text || '').toLowerCase()
    },
    healthToKey(healthText) {
      if (healthText === '异常') return 'err'
      if (healthText === '告警') return 'warn'
      return 'ok'
    },
    relationLabel(key) {
      const hit = this.relationTypes.find((t) => t.key === key)
      return hit ? hit.label : key
    },
    sanitizeFilterPatch(patch = {}) {
      const next = {}
      const projectMap = new Map(this.projectOptions.map((item) => [this.normalizeText(item.value), item.value]))
      const entityTypeSet = new Set(this.entityTypes.map((item) => item.key))
      const relationTypeSet = new Set(this.relationTypes.map((item) => item.key))
      const healthSet = new Set(['all', 'ok', 'warn', 'err'])

      if (patch.project !== undefined && patch.project !== null) {
        const raw = this.normalizeText(String(patch.project).trim())
        if (raw === 'all' || raw === '全部') next.project = 'all'
        else if (projectMap.has(raw)) next.project = projectMap.get(raw)
      }
      if (patch.entityType !== undefined && patch.entityType !== null) {
        const raw = this.normalizeText(String(patch.entityType).trim())
        if (raw === 'all' || raw === '全部') next.entityType = 'all'
        else if (entityTypeSet.has(raw)) next.entityType = raw
      }
      if (patch.relationType !== undefined && patch.relationType !== null) {
        const raw = this.normalizeText(String(patch.relationType).trim())
        if (raw === 'all' || raw === '全部') next.relationType = 'all'
        else if (relationTypeSet.has(raw)) next.relationType = raw
      }
      if (patch.health !== undefined && patch.health !== null) {
        const raw = this.normalizeText(String(patch.health).trim())
        if (raw === '正常') next.health = 'ok'
        else if (raw === '告警') next.health = 'warn'
        else if (raw === '异常') next.health = 'err'
        else if (healthSet.has(raw)) next.health = raw
      }
      if (patch.keyword !== undefined && patch.keyword !== null) {
        next.keyword = String(patch.keyword).trim().slice(0, 80)
      }

      return next
    },
    applyFiltersPatch(patch = {}, source = 'unknown') {
      const normalizedPatch = this.sanitizeFilterPatch(patch)
      if (!Object.keys(normalizedPatch).length) {
        return { applied: false, summary: this.getCurrentFilterSummary(), patch: {}, source }
      }
      this.filters = { ...this.filters, ...normalizedPatch }
      return { applied: true, summary: this.getCurrentFilterSummary(), patch: normalizedPatch, source }
    },
    resolveProjectFromText(rawText, normalizedText) {
      if (/全部项目|所有项目|跨项目|全项目/.test(rawText)) return 'all'
      if (/p001|p1|电商/.test(normalizedText)) return 'P001'
      if (/p002|p2|金融/.test(normalizedText)) return 'P002'

      const hit = this.projectOptions.find((item) => {
        const value = this.normalizeText(item.value)
        const label = this.normalizeText(item.label)
        return normalizedText.includes(value) || normalizedText.includes(label)
      })
      return hit ? hit.value : null
    },
    resolveEntityTypeFromText(rawText, normalizedText) {
      if (/全部实体|所有实体|类型不限/.test(rawText)) return 'all'
      const entityHints = [
        { key: 'api', patterns: ['api', '接口'] },
        { key: 'service', patterns: ['服务', '微服务', 'svc'] },
        { key: 'db', patterns: ['数据库', 'db', 'mysql', 'postgres', 'oracle'] },
        { key: 'middleware', patterns: ['中间件', 'mq', 'kafka', 'redis', 'es'] },
        { key: 'compute', patterns: ['计算', '节点', 'k8s', 'vm'] },
        { key: 'alarm', patterns: ['告警', 'alarm'] },
        { key: 'user', patterns: ['用户'] },
        { key: 'domain', patterns: ['域名'] }
      ]
      const hit = entityHints.find((item) => item.patterns.some((pattern) => normalizedText.includes(pattern)))
      return hit ? hit.key : null
    },
    resolveRelationTypeFromText(rawText, normalizedText) {
      if (/全部关系|所有关系|关系不限/.test(rawText)) return 'all'
      const relationHints = [
        { key: 'access', patterns: ['访问'] },
        { key: 'call', patterns: ['调用'] },
        { key: 'lb', patterns: ['负载', 'lb'] },
        { key: 'host', patterns: ['承载', '部署到', '运行在'] },
        { key: 'monitor', patterns: ['监控'] }
      ]
      const hit = relationHints.find((item) => item.patterns.some((pattern) => normalizedText.includes(pattern)))
      return hit ? hit.key : null
    },
    resolveHealthFromText(rawText, normalizedText) {
      if (/全部状态|所有状态|状态不限/.test(rawText)) return 'all'
      if (/异常|故障|错误|error|err/.test(normalizedText)) return 'err'
      if (/告警|warning|warn/.test(normalizedText)) return 'warn'
      if (/正常|ok|healthy/.test(normalizedText)) return 'ok'
      return null
    },
    extractKeywordFromText(rawText) {
      const explicitMatch = rawText.match(/(?:关键词|关键字|搜索|查找)\s*[:：]?\s*([^\n,，;；]+)/)
      if (explicitMatch && explicitMatch[1]) return explicitMatch[1].trim()
      const quotedMatch = rawText.match(/[“"]([^"”]{1,40})[”"]/)
      if (quotedMatch && quotedMatch[1]) return quotedMatch[1].trim()
      return ''
    },
    inferFilterPatchFromText(text) {
      const rawText = String(text || '').trim()
      if (!rawText) return { matched: false, patch: {}, mode: 'empty' }

      const normalizedText = this.normalizeText(rawText)
      const commandText = normalizedText.replace(/\s+/g, '')
      const commandMap = [
        {
          keys: ['/demo-api', 'demo-api', '看p001api'],
          patch: { project: 'P001', entityType: 'api', relationType: 'all', health: 'all', keyword: '' }
        },
        {
          keys: ['/demo-db', 'demo-db', '看p001数据库'],
          patch: { project: 'P001', entityType: 'db', relationType: 'all', health: 'all', keyword: '' }
        },
        {
          keys: ['/demo-p002-api', 'demo-p002-api', '看p002api'],
          patch: { project: 'P002', entityType: 'api', relationType: 'all', health: 'all', keyword: '' }
        },
        {
          keys: ['/demo-p002-warn', 'demo-p002-warn', '看p002告警'],
          patch: { project: 'P002', entityType: 'all', relationType: 'all', health: 'warn', keyword: '' }
        },
        {
          keys: ['/demo-warn', 'demo-warn', '只看告警'],
          patch: { project: 'P001', entityType: 'all', relationType: 'all', health: 'warn', keyword: '' }
        },
        {
          keys: ['/demo-reset', 'demo-reset', '重置筛选'],
          patch: { project: 'P001', entityType: 'all', relationType: 'all', health: 'all', keyword: '' }
        }
      ]
      const commandHit = commandMap.find((item) => item.keys.includes(commandText))
      if (commandHit) {
        return { matched: true, patch: { ...commandHit.patch }, mode: 'command' }
      }

      const patch = {}
      if (/重置筛选|清空筛选|恢复默认|reset/.test(normalizedText)) {
        Object.assign(patch, {
          project: 'all',
          entityType: 'all',
          relationType: 'all',
          health: 'all',
          keyword: ''
        })
      }

      const project = this.resolveProjectFromText(rawText, normalizedText)
      const entityType = this.resolveEntityTypeFromText(rawText, normalizedText)
      const relationType = this.resolveRelationTypeFromText(rawText, normalizedText)
      const health = this.resolveHealthFromText(rawText, normalizedText)
      const keyword = this.extractKeywordFromText(rawText)

      if (project) patch.project = project
      if (entityType) patch.entityType = entityType
      if (relationType) patch.relationType = relationType
      if (health) patch.health = health
      if (keyword) patch.keyword = keyword

      if (!Object.keys(patch).length) return { matched: false, patch: {}, mode: 'none' }
      return { matched: true, patch, mode: 'natural' }
    },
    applyAgentPrompt(prompt, options = {}) {
      const { silent = false, source = 'agent_prompt' } = options
      const parsed = this.inferFilterPatchFromText(prompt)
      if (!parsed.matched) {
        return { applied: false, summary: this.getCurrentFilterSummary(), patch: {}, source }
      }

      const result = this.applyFiltersPatch(parsed.patch, source)
      if (!silent && result.applied) {
        this.notify('success', `已应用筛选：${result.summary}`)
      }
      return result
    },
    openPanelByName(panelName) {
      const key = this.normalizeText(panelName || '')
      if (!key) return false
      if (key.includes('deploy') || key.includes('架构')) {
        this.showDeployDiagram()
        return true
      }
      if (key.includes('dataflow') || key.includes('链路') || key.includes('flow')) {
        this.showDataFlowDiagram()
        return true
      }
      if (key.includes('analysis') || key.includes('报告')) {
        this.showAnalysis()
        return true
      }
      return false
    },
    applyAgentPayload(payload = {}, options = {}) {
      const { silent = false, source = 'agent_payload' } = options
      const data = payload && typeof payload === 'object' ? payload : {}
      let applied = false
      let summary = this.getCurrentFilterSummary()

      if (data.filters && typeof data.filters === 'object') {
        const filterResult = this.applyFiltersPatch(data.filters, source)
        applied = applied || filterResult.applied
        summary = filterResult.summary
      }

      if (data.prompt || data.text) {
        const promptResult = this.applyAgentPrompt(data.prompt || data.text, { silent: true, source })
        applied = applied || promptResult.applied
        summary = promptResult.summary
      }

      if (data.panel) this.openPanelByName(data.panel)

      if (!silent && applied) {
        this.notify('success', `Agent 指令已生效：${summary}`)
      }

      return { applied, summary }
    },
    readUrlControlPayload() {
      if (typeof window === 'undefined') return {}
      const params = new URLSearchParams(window.location.search || '')
      const payload = {}
      const filters = {}

      const prompt = params.get('prompt') || params.get('q') || params.get('nl')
      if (prompt) payload.prompt = prompt

      const project = params.get('project')
      const entityType = params.get('entityType')
      const relationType = params.get('relationType')
      const health = params.get('health')
      const keyword = params.get('keyword')
      const panel = params.get('panel')

      if (project) filters.project = project
      if (entityType) filters.entityType = entityType
      if (relationType) filters.relationType = relationType
      if (health) filters.health = health
      if (keyword) filters.keyword = keyword
      if (Object.keys(filters).length) payload.filters = filters
      if (panel) payload.panel = panel

      return payload
    },
    applyBootstrapFromUrl() {
      const payload = this.readUrlControlPayload()
      if (!payload || !Object.keys(payload).length) return
      this.applyAgentPayload(payload, { silent: true, source: 'url' })
    },
    handleAgentMessage(event) {
      const data = event && event.data
      if (!data || typeof data !== 'object') return
      const type = String(data.type || data.action || '')
      if (!type.startsWith('opsgraph.')) return

      let result = { applied: false, summary: this.getCurrentFilterSummary() }
      if (type === 'opsgraph.applyPrompt') {
        result = this.applyAgentPrompt(data.prompt || data.text || '', { silent: true, source: 'post_message' })
        if (data.panel) this.openPanelByName(data.panel)
      } else if (type === 'opsgraph.setFilters') {
        result = this.applyFiltersPatch(data.filters || data.payload || {}, 'post_message')
        if (data.panel) this.openPanelByName(data.panel)
      } else if (type === 'opsgraph.run') {
        result = this.applyAgentPayload(data.payload || data, { silent: true, source: 'post_message' })
      } else if (type === 'opsgraph.openPanel') {
        const opened = this.openPanelByName(data.panel || data.name)
        result = { applied: opened, summary: this.getCurrentFilterSummary() }
      } else if (type === 'opsgraph.getState') {
        result = { applied: true, summary: this.getCurrentFilterSummary(), filters: { ...this.filters } }
      }

      if (event && event.source && typeof event.source.postMessage === 'function') {
        event.source.postMessage(
          {
            type: 'opsgraph.result',
            requestId: data.requestId || null,
            ...result
          },
          event.origin || '*'
        )
      }
    },
    registerAgentBridge() {
      if (typeof window === 'undefined') return
      this._agentMessageHandler = (event) => this.handleAgentMessage(event)
      window.addEventListener('message', this._agentMessageHandler)

      this._agentBridge = {
        applyPrompt: (prompt, options = {}) =>
          this.applyAgentPrompt(prompt, { ...options, silent: options.silent !== undefined ? options.silent : true, source: 'window_bridge' }),
        setFilters: (filters, options = {}) =>
          this.applyFiltersPatch(filters, options.source || 'window_bridge'),
        run: (payload, options = {}) =>
          this.applyAgentPayload(payload, { ...options, silent: options.silent !== undefined ? options.silent : true, source: 'window_bridge' }),
        openPanel: (panel) => this.openPanelByName(panel),
        getState: () => ({ filters: { ...this.filters }, summary: this.getCurrentFilterSummary() })
      }
      window.__OPS_GRAPH__ = this._agentBridge
    },
    unregisterAgentBridge() {
      if (typeof window === 'undefined') return
      if (this._agentMessageHandler) {
        window.removeEventListener('message', this._agentMessageHandler)
        this._agentMessageHandler = null
      }
      if (window.__OPS_GRAPH__ === this._agentBridge) {
        delete window.__OPS_GRAPH__
      }
      this._agentBridge = null
    },
    getFilteredGraphData() {
      const { project, entityType, relationType, health, keyword } = this.filters
      const kw = this.normalizeText((keyword || '').trim())

      const filteredNodes = this.graphData.nodes.filter((node) => {
        const nodeProject = node.project || 'P001'
        const matchProject = !project || project === 'all' || nodeProject === project
        const matchType = entityType === 'all' || node.type === entityType
        const matchHealth = health === 'all' || this.healthToKey(node.health) === health
        const matchKeyword = !kw || this.normalizeText(node.label).includes(kw) || this.normalizeText(node.id).includes(kw)
        return matchProject && matchType && matchHealth && matchKeyword
      })

      const nodeIds = new Set(filteredNodes.map((n) => n.id))
      const filteredLinks = this.graphData.links.filter((link) => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source
        const targetId = typeof link.target === 'object' ? link.target.id : link.target
        const matchNodes = nodeIds.has(sourceId) && nodeIds.has(targetId)
        const matchRelation = relationType === 'all' || link.type === relationType
        return matchNodes && matchRelation
      })

      return { nodes: filteredNodes, links: filteredLinks }
    },
    getCurrentFilterSummary() {
      const parts = []
      const projectLabel = (this.projectOptions.find((p) => p.value === this.filters.project) || {}).label || this.filters.project
      parts.push(`项目：${projectLabel || '全部'}`)
      if (this.filters.entityType !== 'all') parts.push(`实体：${this.typeLabel(this.filters.entityType)}`)
      if (this.filters.relationType !== 'all') parts.push(`关系：${this.relationLabel(this.filters.relationType)}`)
      if (this.filters.health !== 'all') {
        const healthMap = { ok: '正常', warn: '告警', err: '异常' }
        parts.push(`状态：${healthMap[this.filters.health] || this.filters.health}`)
      }
      if ((this.filters.keyword || '').trim()) parts.push(`关键词：${this.filters.keyword.trim()}`)
      return parts.join('，')
    },
    applyChatFiltersFromText(text) {
      const result = this.applyAgentPrompt(text, { silent: true, source: 'chat' })
      return { applied: result.applied, summary: result.summary }
    },
    async handleChatSend({ text, assistantMessageId }) {
      const chat = this.$refs.opsChat
      if (!chat || !assistantMessageId) return

      try {
        const steps = [
          '正在分析请求...',
          '正在匹配固定命令...',
          '正在联动图谱筛选器...',
          '正在生成最终回复...'
        ]

        for (let i = 0; i < steps.length; i += 1) {
          await this.waitMs(650)
          const type = i === steps.length - 1 ? 'success' : 'primary'
          chat.appendAssistantStep(assistantMessageId, steps[i], type)
        }

        const filterResult = this.applyChatFiltersFromText(text)
        await this.waitMs(400)
        if (filterResult.applied) {
          chat.finishAssistantReply(
            assistantMessageId,
            `已按你的指令联动筛选图谱。\n当前条件：${filterResult.summary}\n左侧知识图谱已经同步更新。`
          )
        } else {
          chat.finishAssistantReply(
            assistantMessageId,
            `我没有识别出可执行筛选。\n你可以直接说自然语言，比如：\n1) 看 P002 告警\n2) 只看 API\n3) 项目 P001，状态正常，关键词: 支付\n也支持固定命令：/demo-api /demo-db /demo-p002-api /demo-warn /demo-p002-warn /demo-reset`
          )
        }
      } catch (error) {
        chat.failAssistantReply(assistantMessageId, '处理失败，请检查后端服务后重试。')
      }
    },
    async doRefresh() {
      if (this.refreshing) return
      this.refreshing = true
      try {
        await Promise.all([this.fetchStats(), this.fetchGraphData(), this.fetchDetailData()])
        this.renderGraph()
        if (this.deployPanelVisible) this.$nextTick(() => this.renderDeployDiagram())
        if (this.dataflowPanelVisible) this.$nextTick(() => this.renderDataFlowDiagram())
        this.notify('success', '图谱数据已刷新')
      } catch (error) {
        this.notify('error', '刷新失败，请检查数据源后重试')
      } finally {
        this.refreshing = false
      }
    },
    showAnalysis() {
      const { nodes, links } = this.getFilteredGraphData()
      if (!nodes.length) {
        this.analysisLines = ['当前筛选条件下没有匹配节点。']
        this.analysisVisible = true
        return
      }

      const abnormalNodes = nodes.filter((node) => node.health === '告警' || node.health === '异常')
      const nodeIdSet = new Set(nodes.map((node) => node.id))
      const degreeMap = new Map(nodes.map((node) => [node.id, { in: 0, out: 0 }]))
      links.forEach((link) => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source
        const targetId = typeof link.target === 'object' ? link.target.id : link.target
        if (degreeMap.has(sourceId)) degreeMap.get(sourceId).out += 1
        if (degreeMap.has(targetId)) degreeMap.get(targetId).in += 1
      })

      const typeCountMap = new Map()
      nodes.forEach((node) => {
        typeCountMap.set(node.type, (typeCountMap.get(node.type) || 0) + 1)
      })
      const topTypes = Array.from(typeCountMap.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([type, count]) => `${this.typeLabel(type)} ${count}`)

      const criticalNodes = abnormalNodes
        .map((node) => {
          const degree = degreeMap.get(node.id) || { in: 0, out: 0 }
          return { node, score: degree.in + degree.out }
        })
        .sort((a, b) => b.score - a.score)
        .slice(0, 3)

      const projectSet = new Set(nodes.map((node) => node.project || '未知项目'))
      const crossProjectLinks = links.filter((link) => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source
        const targetId = typeof link.target === 'object' ? link.target.id : link.target
        if (!nodeIdSet.has(sourceId) || !nodeIdSet.has(targetId)) return false
        const sourceNode = nodes.find((node) => node.id === sourceId)
        const targetNode = nodes.find((node) => node.id === targetId)
        if (!sourceNode || !targetNode) return false
        return sourceNode.project !== targetNode.project
      })

      const lines = [
        `筛选范围：${this.getCurrentFilterSummary()}`,
        `覆盖项目：${projectSet.size} 个，节点 ${nodes.length} 个，关系 ${links.length} 条`,
        `健康概况：正常 ${nodes.filter((node) => node.health === '正常').length}，告警 ${nodes.filter((node) => node.health === '告警').length}，异常 ${nodes.filter((node) => node.health === '异常').length}`,
        `高频实体类型：${topTypes.length ? topTypes.join('，') : '暂无'}`,
        `跨项目链路：${crossProjectLinks.length} 条`
      ]

      if (criticalNodes.length) {
        lines.push('重点关注节点：')
        criticalNodes.forEach((item) => {
          lines.push(`- ${item.node.label}（${item.node.health}，关联 ${item.score}）`)
        })
      } else {
        lines.push('重点关注节点：暂无告警/异常节点')
      }

      this.analysisLines = lines
      this.analysisVisible = true
    },
    closeModal() {
      this.analysisVisible = false
    },
    showDeployDiagram() {
      this.dataflowPanelVisible = false
      this.deployPanelVisible = true
      this.$nextTick(() => this.renderDeployDiagram())
    },
    showDataFlowDiagram() {
      this.deployPanelVisible = false
      this.dataflowPanelVisible = true
      this.$nextTick(() => this.renderDataFlowDiagram())
    },
    closeSkillPanel(panel) {
      if (panel === 'deploy') this.deployPanelVisible = false
      if (panel === 'dataflow') this.dataflowPanelVisible = false
    },
    getActiveProjects() {
      const selected = this.filters.project
      if (!selected || selected === 'all') {
        return this.projectOptions.map((item) => item.value)
      }
      return [selected]
    },
    getProjectScopedGraphData() {
      const selected = this.filters.project
      const activeProjects = new Set(this.getActiveProjects())
      const matchAll = !selected || selected === 'all'
      const nodes = this.graphData.nodes.filter((node) => {
        if (matchAll) return true
        return activeProjects.has(node.project)
      })

      const nodeIds = new Set(nodes.map((node) => node.id))
      const links = this.graphData.links.filter((link) => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source
        const targetId = typeof link.target === 'object' ? link.target.id : link.target
        return nodeIds.has(sourceId) && nodeIds.has(targetId)
      })
      return { nodes, links }
    },
    projectLabel(projectId) {
      const hit = this.projectOptions.find((item) => item.value === projectId)
      return hit ? hit.label : projectId
    },
    healthColor(health) {
      if (health === '异常') return '#f05252'
      if (health === '告警') return '#f0b429'
      return '#00b37a'
    },
    shortLabel(text, maxLen = 14) {
      const source = String(text || '')
      if (source.length <= maxLen) return source
      return `${source.slice(0, maxLen - 1)}…`
    },
    makeCurvePath(source, target) {
      const sx = source.x
      const sy = source.y
      const tx = target.x
      const ty = target.y
      if (tx <= sx) {
        const midX = (sx + tx) / 2
        const lift = Math.max(40, Math.abs(ty - sy) * 0.55 + 22)
        return `M${sx},${sy} C${midX},${sy - lift} ${midX},${ty - lift} ${tx},${ty}`
      }
      const dx = tx - sx
      const c1x = sx + Math.max(36, dx * 0.42)
      const c2x = tx - Math.max(36, dx * 0.42)
      return `M${sx},${sy} C${c1x},${sy} ${c2x},${ty} ${tx},${ty}`
    },
    layoutNodesByProjectAndLayer(nodes, layerByType, layerCount, width, height) {
      const projects = [...new Set(nodes.map((node) => node.project || '未命名项目'))].sort()
      const laneGap = 20
      const topPad = 70
      const bottomPad = 38
      const leftPad = 190
      const rightPad = 72
      const laneHeight = Math.max(
        120,
        (height - topPad - bottomPad - laneGap * Math.max(0, projects.length - 1)) / Math.max(projects.length, 1)
      )
      const usableWidth = Math.max(300, width - leftPad - rightPad)
      const layerStep = layerCount > 1 ? usableWidth / (layerCount - 1) : 0
      const projectTopMap = new Map(projects.map((project, index) => [project, topPad + index * (laneHeight + laneGap)]))

      const positionedNodes = nodes.map((node) => {
        const layerRaw = layerByType(node.type)
        const layer = Number.isFinite(layerRaw) ? layerRaw : 0
        return {
          ...node,
          layer: Math.max(0, Math.min(layerCount - 1, layer))
        }
      })

      const grouped = new Map()
      positionedNodes.forEach((node) => {
        const key = `${node.project || '未命名项目'}|${node.layer}`
        if (!grouped.has(key)) grouped.set(key, [])
        grouped.get(key).push(node)
      })

      grouped.forEach((groupNodes, key) => {
        const [project, layerText] = key.split('|')
        const layer = Number(layerText)
        const laneTop = projectTopMap.get(project) || topPad
        const innerTop = laneTop + 42
        const innerBottom = Math.max(innerTop + 6, laneTop + laneHeight - 18)
        const centerY = (innerTop + innerBottom) / 2
        const x = leftPad + layerStep * layer
        groupNodes.sort((a, b) => String(a.label).localeCompare(String(b.label)))

        if (groupNodes.length === 1) {
          groupNodes[0].x = x
          groupNodes[0].y = centerY
          return
        }

        const step = (innerBottom - innerTop) / Math.max(groupNodes.length - 1, 1)
        groupNodes.forEach((node, index) => {
          node.x = x
          node.y = innerTop + step * index
        })
      })

      return {
        nodes: positionedNodes,
        projects,
        metrics: {
          topPad,
          laneGap,
          laneHeight,
          leftPad,
          rightPad,
          layerStep
        }
      }
    },
    renderDeployDiagram() {
      const svgEl = this.$refs.deploySvg
      if (!svgEl) return
      const wrap = svgEl.parentElement
      const width = Math.max((wrap && wrap.clientWidth) || 0, 920)
      const height = Math.max((wrap && wrap.clientHeight) || 0, 520)
      const svg = d3.select(svgEl)
      svg.selectAll('*').remove()
      svg.attr('width', width).attr('height', height)

      const { nodes, links } = this.getProjectScopedGraphData()
      if (!nodes.length) {
        svg
          .append('text')
          .attr('x', width / 2)
          .attr('y', height / 2)
          .attr('text-anchor', 'middle')
          .attr('fill', '#8b97ad')
          .attr('font-size', 14)
          .attr('font-family', 'Noto Sans SC, sans-serif')
          .text('暂无部署数据')
        this.deployLegendItems = []
        return
      }

      const layers = [
        { label: '入口层', types: ['user', 'domain'], color: '#00bcd4' },
        { label: 'API 层', types: ['api'], color: '#1a7bf2' },
        { label: '应用层', types: ['service'], color: '#00b37a' },
        { label: '数据/中间件', types: ['middleware', 'db'], color: '#8b6cff' },
        { label: '基础设施', types: ['compute', 'alarm'], color: '#ff8c33' }
      ]
      const typeToLayer = {}
      layers.forEach((layer, index) => {
        layer.types.forEach((type) => {
          typeToLayer[type] = index
        })
      })

      const layout = this.layoutNodesByProjectAndLayer(
        nodes,
        (type) => (typeToLayer[type] === undefined ? 2 : typeToLayer[type]),
        layers.length,
        width,
        height
      )
      const nodeMap = new Map(layout.nodes.map((node) => [node.id, node]))
      const edgeData = links
        .map((link) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source
          const targetId = typeof link.target === 'object' ? link.target.id : link.target
          return {
            ...link,
            source: nodeMap.get(sourceId),
            target: nodeMap.get(targetId)
          }
        })
        .filter((edge) => edge.source && edge.target)

      const guideLayer = svg.append('g')
      layers.forEach((layer, index) => {
        const x = layout.metrics.leftPad + layout.metrics.layerStep * index
        guideLayer
          .append('line')
          .attr('x1', x)
          .attr('y1', 46)
          .attr('x2', x)
          .attr('y2', height - 20)
          .attr('stroke', '#d5dfef')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '4 6')
        guideLayer
          .append('text')
          .attr('x', x)
          .attr('y', 26)
          .attr('text-anchor', 'middle')
          .attr('fill', layer.color)
          .attr('font-size', 11)
          .attr('font-family', 'IBM Plex Mono, monospace')
          .text(layer.label)
      })

      const bands = svg.append('g')
      layout.projects.forEach((project, index) => {
        const y = layout.metrics.topPad + index * (layout.metrics.laneHeight + layout.metrics.laneGap)
        bands
          .append('rect')
          .attr('x', 18)
          .attr('y', y)
          .attr('width', width - 36)
          .attr('height', layout.metrics.laneHeight)
          .attr('rx', 10)
          .attr('fill', index % 2 === 0 ? 'rgba(26,123,242,0.04)' : 'rgba(0,179,122,0.04)')
          .attr('stroke', 'rgba(185,201,225,0.6)')
        bands
          .append('text')
          .attr('x', 28)
          .attr('y', y + 20)
          .attr('fill', '#5d6b86')
          .attr('font-size', 11)
          .attr('font-family', 'IBM Plex Mono, monospace')
          .text(this.projectLabel(project))
      })

      svg
        .append('g')
        .selectAll('path')
        .data(edgeData)
        .enter()
        .append('path')
        .attr('class', 'dep-edge-flow')
        .attr('d', (edge) => this.makeCurvePath(edge.source, edge.target))
        .attr('fill', 'none')
        .attr('stroke', (edge) => this.relationColor(edge.type))
        .attr('stroke-width', 1.3)
        .attr('stroke-opacity', 0.42)
        .attr('stroke-dasharray', (edge) => (edge.type === 'monitor' ? '3 5' : '7 6'))

      const nodeG = svg.append('g').selectAll('g').data(layout.nodes).enter().append('g')
      const nodeWidth = 136
      const nodeHeight = 46
      nodeG.attr('transform', (node) => `translate(${node.x - nodeWidth / 2}, ${node.y - nodeHeight / 2})`)

      nodeG
        .append('rect')
        .attr('width', nodeWidth)
        .attr('height', nodeHeight)
        .attr('rx', 6)
        .attr('fill', '#ffffff')
        .attr('stroke', (node) => this.colorByType(node.type))
        .attr('stroke-width', 1.3)

      nodeG
        .append('rect')
        .attr('width', 4)
        .attr('height', nodeHeight)
        .attr('rx', 4)
        .attr('fill', (node) => this.colorByType(node.type))

      nodeG
        .append('text')
        .attr('x', 10)
        .attr('y', 19)
        .attr('fill', '#23334d')
        .attr('font-size', 11)
        .attr('font-weight', 600)
        .attr('font-family', 'Noto Sans SC, sans-serif')
        .text((node) => this.shortLabel(node.label, 15))

      nodeG
        .append('text')
        .attr('x', 10)
        .attr('y', 34)
        .attr('fill', '#8b97ad')
        .attr('font-size', 9)
        .attr('font-family', 'IBM Plex Mono, monospace')
        .text((node) => this.typeLabel(node.type))

      nodeG
        .append('circle')
        .attr('cx', nodeWidth - 12)
        .attr('cy', 12)
        .attr('r', 4)
        .attr('fill', (node) => this.healthColor(node.health))

      const projectNames = layout.projects.map((project) => this.projectLabel(project)).join('、')
      this.deploySubtitle = `当前项目：${projectNames} · 节点 ${layout.nodes.length} · 链路 ${edgeData.length}`
      this.deployLegendItems = layers.map((layer) => ({ label: layer.label, color: layer.color }))
    },
    renderDataFlowDiagram() {
      const svgEl = this.$refs.dataflowSvg
      if (!svgEl) return
      const wrap = svgEl.parentElement
      const width = Math.max((wrap && wrap.clientWidth) || 0, 920)
      const height = Math.max((wrap && wrap.clientHeight) || 0, 520)
      const svg = d3.select(svgEl)
      svg.selectAll('*').remove()
      svg.attr('width', width).attr('height', height)

      const { nodes, links } = this.getProjectScopedGraphData()
      if (!nodes.length) {
        svg
          .append('text')
          .attr('x', width / 2)
          .attr('y', height / 2)
          .attr('text-anchor', 'middle')
          .attr('fill', '#8b97ad')
          .attr('font-size', 14)
          .attr('font-family', 'Noto Sans SC, sans-serif')
          .text('暂无数据链路')
        this.dataflowLegendItems = []
        return
      }

      const layers = [
        { label: '入口', types: ['user', 'domain'] },
        { label: '接口', types: ['api'] },
        { label: '服务', types: ['service'] },
        { label: '中间件', types: ['middleware'] },
        { label: '存储', types: ['db'] },
        { label: '基础设施', types: ['compute', 'alarm'] }
      ]
      const typeToLayer = {}
      layers.forEach((layer, index) => {
        layer.types.forEach((type) => {
          typeToLayer[type] = index
        })
      })

      const layout = this.layoutNodesByProjectAndLayer(
        nodes,
        (type) => (typeToLayer[type] === undefined ? 2 : typeToLayer[type]),
        layers.length,
        width,
        height
      )
      const nodeMap = new Map(layout.nodes.map((node) => [node.id, node]))
      const edgeData = links
        .map((link) => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source
          const targetId = typeof link.target === 'object' ? link.target.id : link.target
          return {
            ...link,
            source: nodeMap.get(sourceId),
            target: nodeMap.get(targetId)
          }
        })
        .filter((edge) => edge.source && edge.target)

      const defs = svg.append('defs')
      const relationDefs = [...this.relationTypes, { key: 'default', label: '默认' }]
      relationDefs.forEach((rel) => {
        const color = rel.key === 'default' ? '#2f8bff' : this.relationColor(rel.key)
        const marker = defs
          .append('marker')
          .attr('id', `flow-arrow-${rel.key}`)
          .attr('viewBox', '0 0 10 10')
          .attr('refX', 9)
          .attr('refY', 5)
          .attr('markerWidth', 5)
          .attr('markerHeight', 5)
          .attr('orient', 'auto')
        marker
          .append('path')
          .attr('d', 'M 0 0 L 10 5 L 0 10 z')
          .attr('fill', color)
      })

      const bands = svg.append('g')
      layout.projects.forEach((project, index) => {
        const y = layout.metrics.topPad + index * (layout.metrics.laneHeight + layout.metrics.laneGap)
        bands
          .append('rect')
          .attr('x', 18)
          .attr('y', y)
          .attr('width', width - 36)
          .attr('height', layout.metrics.laneHeight)
          .attr('rx', 10)
          .attr('fill', index % 2 === 0 ? 'rgba(139,108,255,0.04)' : 'rgba(47,139,255,0.04)')
          .attr('stroke', 'rgba(185,201,225,0.6)')
        bands
          .append('text')
          .attr('x', 28)
          .attr('y', y + 20)
          .attr('fill', '#5d6b86')
          .attr('font-size', 11)
          .attr('font-family', 'IBM Plex Mono, monospace')
          .text(this.projectLabel(project))
      })

      const edgeG = svg.append('g')
      edgeG
        .selectAll('path')
        .data(edgeData)
        .enter()
        .append('path')
        .attr('class', 'dataflow-edge')
        .attr('d', (edge) => this.makeCurvePath(edge.source, edge.target))
        .attr('fill', 'none')
        .attr('stroke', (edge) => this.relationColor(edge.type))
        .attr('stroke-width', 1.4)
        .attr('stroke-opacity', 0.5)
        .attr('marker-end', (edge) => {
          const key = this.relationColors[edge.type] ? edge.type : 'default'
          return `url(#flow-arrow-${key})`
        })

      const nodeW = 126
      const nodeH = 30
      const nodeG = svg.append('g').selectAll('g').data(layout.nodes).enter().append('g')
      nodeG.attr('transform', (node) => `translate(${node.x - nodeW / 2}, ${node.y - nodeH / 2})`)
      nodeG
        .append('rect')
        .attr('width', nodeW)
        .attr('height', nodeH)
        .attr('rx', 14)
        .attr('fill', '#ffffff')
        .attr('stroke', (node) => this.colorByType(node.type))
        .attr('stroke-width', 1.2)
      nodeG
        .append('text')
        .attr('x', nodeW / 2)
        .attr('y', 19)
        .attr('text-anchor', 'middle')
        .attr('fill', '#2d3a4a')
        .attr('font-size', 11)
        .attr('font-family', 'Noto Sans SC, sans-serif')
        .text((node) => this.shortLabel(node.label, 13))

      const flowProjectNames = layout.projects.map((project) => this.projectLabel(project)).join('、')
      this.dataflowSubtitle = `当前项目：${flowProjectNames} · 节点 ${layout.nodes.length} · 链路 ${edgeData.length}`
      this.dataflowLegendItems = this.relationTypes.map((rel) => ({
        label: rel.label,
        color: this.relationColor(rel.key)
      }))
    },
    exportSkillSVG(refName, fileName) {
      const svgEl = this.$refs[refName]
      if (!svgEl) return
      if (!svgEl.querySelector('*')) {
        this.notify('warning', '当前图为空，无法导出')
        return
      }

      const clone = svgEl.cloneNode(true)
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
      clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
      const source = new XMLSerializer().serializeToString(clone)
      const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      this.notify('success', `已导出 ${fileName}`)
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
    relationColor(key) {
      return this.relationColors[key] || '#4db8ff'
    },

    getGraphViewData() {
      const baseData = this.getFilteredGraphData()
      if (!this.aggMode) {
        return baseData
      }

      const typeMap = new Map()
      baseData.nodes.forEach((n) => {
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
      const nodeMap = new Map(baseData.nodes.map((n) => [n.id, n]))
      baseData.links.forEach((l) => {
        const sourceType = (nodeMap.get(l.source) || {}).type
        const targetType = (nodeMap.get(l.target) || {}).type
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
      if (!d3Nodes.length) {
        root
          .append('text')
          .attr('x', width / 2)
          .attr('y', height / 2)
          .attr('text-anchor', 'middle')
          .attr('fill', '#8b97ad')
          .attr('font-size', 14)
          .attr('font-family', 'Noto Sans SC, sans-serif')
          .text('暂无匹配数据，请调整筛选条件')
        d3.select(this.$refs.minimapSvg).selectAll('*').remove()
        return
      }
      const nodeById = new Map(d3Nodes.map((n) => [n.id, n]))
      const d3Links = links
        .map((l) => ({ ...l, source: nodeById.get(l.source), target: nodeById.get(l.target) }))
        .filter((l) => l.source && l.target)

      const edgeG = root.append('g')
      const linkPaths = edgeG
        .selectAll('path')
        .data(d3Links)
        .enter()
        .append('path')
        .attr('class', 'edge-path')
        .attr('stroke', (d) => this.relationColor(d.type))
        .attr('stroke-width', 1.2)
        .attr('stroke-opacity', 0.6)
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
        .call(
          d3
            .drag()
            .on('drag', (event, d) => {
              d.x = event.x
              d.y = event.y
              d3.select(event.sourceEvent.target.closest('g'))
                .attr('transform', `translate(${d.x - d.w / 2}, ${d.y - d.h / 2})`)
              linkPaths.attr('d', (l) => `M${l.source.x},${l.source.y} L${l.target.x},${l.target.y}`)
              this.renderMinimap(d3Nodes, d3Links, width, height)
            })
        )

      node
        .append('rect')
        .attr('class', 'node-body')
        .attr('width', (d) => d.w)
        .attr('height', (d) => d.h)
        .attr('fill', '#ffffff')
        .attr('stroke', (d) => this.colorByType(d.type))
        .attr('stroke-width', 1.4)

      node
        .append('rect')
        .attr('width', 4)
        .attr('height', (d) => d.h)
        .attr('fill', (d) => this.colorByType(d.type))

      node
        .append('text')
        .attr('x', 10)
        .attr('y', 24)
        .attr('fill', '#2d3a4a')
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
        .attr('stroke', 'rgba(77,184,255,0.5)')
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
        .attr('fill', 'rgba(26,159,255,0.15)')
        .attr('stroke', 'rgba(77,184,255,0.8)')
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
  --bg: #f4f7fb;
  --bg1: #ffffff;
  --bg2: #f1f4f9;
  --panel: #ffffff;
  --panel2: #f6f8fc;
  --panel3: #eef3fb;
  --border: #dbe4f2;
  --border2: #cdd8ea;
  --border3: #b9c9e1;
  --accent: #1a7bf2;
  --accent2: #2f8bff;
  --accent3: #6ab2ff;
  --green: #00b37a;
  --green2: #00d68f;
  --yellow: #f0b429;
  --yellow2: #ffd166;
  --red: #f05252;
  --red2: #ff6b6b;
  --purple: #8b6cff;
  --orange: #ff8c33;
  --cyan: #00bcd4;
  --text: #23334d;
  --text2: #5d6b86;
  --text3: #8b97ad;
  --text4: #aab5c7;
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
.badge-blue { background: rgba(47,139,255,0.1); color: var(--accent); border: 1px solid rgba(47,139,255,0.2); }
.badge-green { background: rgba(0,179,122,0.1); color: var(--green); border: 1px solid rgba(0,179,122,0.2); }
.badge-yellow { background: rgba(240,180,41,0.12); color: var(--yellow); border: 1px solid rgba(240,180,41,0.25); }
.badge-red { background: rgba(240,82,82,0.12); color: var(--red); border: 1px solid rgba(240,82,82,0.25); }
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
.btn-primary { background: rgba(47,139,255,0.15); color: var(--accent); border-color: rgba(47,139,255,0.35); }
.btn-primary:hover { background: rgba(47,139,255,0.25); }

.main { display: flex; flex: 1; overflow: hidden; position: relative; }

.chat-sidebar {
  width: 420px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  background: var(--bg1);
  display: flex;
  flex-direction: column;
  transition: width 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-sidebar.collapsed {
  width: 0;
  border-left: none;
}

.chat-sidebar-toggle {
  height: 40px;
  border-bottom: 1px solid var(--border);
  background: var(--panel2);
  color: var(--text2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.chat-sidebar-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding-left: 10px;
}

.chat-agent-icon {
  width: 18px;
  height: 18px;
  display: inline-block;
}

.chat-sidebar-body {
  flex: 1;
  min-height: 0;
  padding: 8px;
}

.chat-sidebar.collapsed .chat-sidebar-toggle {
  display: none;
}

.chat-collapse-btn {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text3);
  margin-right: 8px;
}

.chat-collapse-btn:hover {
  background: var(--panel3);
  color: var(--text);
}

.chat-fab {
  position: absolute;
  right: 18px;
  bottom: 16px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #ffffff;
  border: 1px solid #d5e3f7;
  color: var(--accent2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 10px 20px rgba(23, 46, 89, 0.14);
  cursor: pointer;
  z-index: 25;
  transition: transform 0.16s ease, box-shadow 0.16s ease, background-color 0.16s ease;
}

.chat-fab .chat-agent-icon {
  width: 26px;
  height: 26px;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.12));
}

.chat-fab:hover {
  background: #f6f9ff;
  transform: translateY(-2px) scale(1.03);
  box-shadow: 0 14px 24px rgba(23, 46, 89, 0.2);
}

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
.etype-header:hover { background: var(--panel2); }
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
    radial-gradient(circle 600px at 15% 30%, rgba(47,139,255,0.05) 0%, transparent 70%),
    radial-gradient(circle 400px at 85% 70%, rgba(139,108,255,0.05) 0%, transparent 70%);
  pointer-events: none;
}
.canvas-wrap::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(210,222,240,0.8) 1px, transparent 1px);
  background-size: 28px 28px;
  pointer-events: none;
  opacity: 0.5;
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
  background: rgba(255,255,255,0.9);
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
  background: rgba(255,255,255,0.88);
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
  background: rgba(0,0,0,0.03);
}
.detail-row {
  display: flex;
  align-items: flex-start;
  padding: 5px 14px;
  gap: 8px;
  border-bottom: 1px solid rgba(30,53,84,0.08);
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
.node-g:hover .node-body { filter: brightness(1.05); }
.edge-path { fill: none; transition: stroke-opacity 0.2s; }

.tooltip-el {
  position: fixed;
  background: #ffffff;
  border: 1px solid var(--border2);
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 11px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.12s;
  z-index: 9999;
  max-width: 240px;
  box-shadow: 0 10px 30px rgba(15, 32, 60, 0.12);
}
.tooltip-el.visible { opacity: 1; }
.tt-name { font-weight: 600; color: var(--accent2); margin-bottom: 7px; font-size: 12px; }
.tt-row { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 3px; }
.tt-key { color: var(--text3); }
.tt-val { color: var(--text); font-family: 'IBM Plex Mono'; }

.skill-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 2200;
  background: var(--bg);
  flex-direction: column;
}

.skill-overlay.visible {
  display: flex;
}

.skill-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  background: var(--bg1);
  border-bottom: 1px solid var(--border2);
  flex-shrink: 0;
}

.skill-topbar-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  flex: 1;
}

.skill-topbar-sub {
  font-size: 11px;
  color: var(--text3);
  font-family: 'IBM Plex Mono', monospace;
}

.skill-top-btn {
  min-width: 88px;
  justify-content: center;
}

.skill-canvas {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.skill-canvas svg {
  width: 100%;
  height: 100%;
}

.skill-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  padding: 7px 18px;
  background: var(--bg1);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.skill-legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: var(--text3);
  font-family: 'IBM Plex Mono', monospace;
}

.skill-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.skill-legend-line {
  width: 22px;
  height: 2px;
  border-radius: 2px;
  flex-shrink: 0;
}

.dep-edge-flow {
  animation: dep-flow 2.4s linear infinite;
}

.dataflow-edge {
  stroke-dasharray: 6 6;
  animation: data-flow 2s linear infinite;
}

@keyframes dep-flow {
  from { stroke-dashoffset: 18; }
  to { stroke-dashoffset: 0; }
}

@keyframes data-flow {
  to { stroke-dashoffset: -24; }
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(19, 33, 57, 0.35);
  backdrop-filter: blur(3px);
  z-index: 2300;
  display: none;
  align-items: center;
  justify-content: center;
}

.modal-overlay.visible {
  display: flex;
}

.modal-box {
  width: min(560px, calc(100vw - 36px));
  background: #ffffff;
  border: 1px solid var(--border2);
  border-radius: 10px;
  box-shadow: 0 20px 60px rgba(15, 32, 60, 0.16);
  padding: 20px 22px 18px;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent2);
  margin-bottom: 14px;
}

.modal-body {
  font-size: 13px;
  color: var(--text2);
  line-height: 1.65;
  max-height: 55vh;
  overflow-y: auto;
}

.analysis-line + .analysis-line {
  margin-top: 6px;
}

.modal-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

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
  background: rgba(47,139,255,0.15);
  color: var(--accent);
  border-color: rgba(47,139,255,0.35);
}
.el-button.btn.btn-default:hover {
  background: var(--panel2);
  color: var(--text);
  border-color: var(--accent);
}

.ops-select-popper .el-select-dropdown__item { color: var(--text); }
.ops-select-popper { background: var(--panel); border: 1px solid var(--border2); }

@media (max-width: 1360px) {
  .chat-sidebar {
    width: 360px;
  }
}

@media (max-width: 1100px) {
  .chat-sidebar {
    width: 320px;
  }

  .chat-fab {
    right: 12px;
    bottom: 12px;
  }
}
</style>
