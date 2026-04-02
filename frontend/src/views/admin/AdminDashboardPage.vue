<template>
  <AdminShell title="后台总览" subtitle="每 30 秒自动刷新一次，关注任务、收入与模式状态。">
    <section
      v-if="switchStatus.current_mode === 'ALGO_ONLY'"
      class="scholar-note scholar-note--danger"
    >
      当前系统处于算法降级模式，原因：{{ switchStatus.last_switch_reason || "大模型异常" }}。
      <button class="scholar-button scholar-button--danger" type="button" style="margin-left: 12px" @click="recoverMode">
        手动恢复大模型模式
      </button>
    </section>

    <section class="scholar-grid scholar-grid--stats">
      <article class="scholar-stat" v-for="item in statCards" :key="item.label">
        <div class="scholar-stat__label">{{ item.label }}</div>
        <div class="scholar-stat__value">{{ item.value }}</div>
        <div class="scholar-stat__hint">{{ item.hint }}</div>
      </article>
    </section>

    <section class="scholar-hero-grid">
      <article class="scholar-chart-card">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="scholar-kicker">Task Trend</div>
            <h3 class="scholar-subtitle">近 7 天任务趋势</h3>
          </div>
          <button class="scholar-button scholar-button--secondary" type="button" @click="loadData">刷新</button>
        </div>
        <div ref="taskChartEl" class="mt-4 h-72 w-full"></div>
      </article>

      <article class="scholar-chart-card">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="scholar-kicker">Revenue Trend</div>
            <h3 class="scholar-subtitle">近 7 天收入趋势</h3>
          </div>
          <button class="scholar-button scholar-button--secondary" type="button" @click="loadData">刷新</button>
        </div>
        <div ref="revenueChartEl" class="mt-4 h-72 w-full"></div>
      </article>
    </section>

    <section class="scholar-grid scholar-grid--halves">
      <article class="scholar-chart-card">
        <div class="scholar-kicker">Usage Distribution</div>
        <h3 class="scholar-subtitle">功能使用占比</h3>
        <div ref="taskTypeChartEl" class="mt-4 h-60 w-full"></div>
      </article>

      <article class="scholar-chart-card">
        <div class="scholar-kicker">Platform Distribution</div>
        <h3 class="scholar-subtitle">平台使用量对比</h3>
        <div ref="platformChartEl" class="mt-4 h-60 w-full"></div>
      </article>
    </section>

    <section class="scholar-chart-card">
      <div class="scholar-kicker">Conversion Funnel</div>
      <h3 class="scholar-subtitle">用户转化对比</h3>
      <div ref="funnelChartEl" class="mt-4 h-56 w-full"></div>
    </section>
  </AdminShell>
</template>

<script setup>
import * as echarts from "echarts/core"
import { BarChart, LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent } from "echarts/components"
import { CanvasRenderer } from "echarts/renderers"
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue"

import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"
import { getAdminInfo } from "../../lib/session"

echarts.use([LineChart, BarChart, TooltipComponent, GridComponent, CanvasRenderer])

const dashboard = ref(null)
const taskChartEl = ref(null)
const revenueChartEl = ref(null)
const taskTypeChartEl = ref(null)
const platformChartEl = ref(null)
const funnelChartEl = ref(null)

let timer = null
let taskChart = null
let revenueChart = null
let taskTypeChart = null
let platformChart = null
let funnelChart = null

const statCards = computed(() => {
  const overview = dashboard.value?.overview || {}
  const totalUsers = typeof overview.total_users === "number" ? overview.total_users : 0
  const totalTasks = typeof overview.total_tasks === "number" ? overview.total_tasks : 0
  const totalOrders = typeof overview.total_orders === "number" ? overview.total_orders : 0
  const totalRevenue = typeof overview.total_revenue === "number" ? overview.total_revenue : 0
  return [
    { label: "累计用户", value: totalUsers, hint: "注册用户总量" },
    { label: "累计任务", value: totalTasks, hint: "含检测、降重、降 AIGC 率" },
    { label: "支付订单", value: totalOrders, hint: "已创建订单总数" },
    { label: "累计收入", value: totalRevenue, hint: "订单支付后的累计金额" },
  ]
})

const switchStatus = computed(() => dashboard.value?.switch_status || {})
const adminInfo = getAdminInfo()
const trendRows = computed(() => {
  const rows = dashboard.value?.trend_30d || []
  return rows.slice(-7)
})

watch(
  dashboard,
  async () => {
    await nextTick()
    renderCharts()
  },
  { deep: true }
)

onMounted(async () => {
  await loadData()
  timer = setInterval(loadData, 30000)
  window.addEventListener("resize", handleResize)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
  window.removeEventListener("resize", handleResize)
  disposeCharts()
})

async function loadData() {
  dashboard.value = await adminHttp.get("/admin/dashboard")
}

async function recoverMode() {
  if (adminInfo?.role !== "super_admin") {
    window.alert("仅 super_admin 可执行手动恢复")
    return
  }
  const confirmed = window.confirm("确认切换回大模型 + 算法模式吗？")
  if (!confirmed) {
    return
  }
  await adminHttp.post("/admin/switch/mode", { mode: "LLM_PLUS_ALGO" })
  await loadData()
}

function initChart(el, chartRef) {
  if (!el) {
    return null
  }
  if (chartRef) {
    return chartRef
  }
  return echarts.init(el)
}

function baseAxisStyle() {
  return {
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: "rgba(107, 119, 130, 0.12)" } },
    axisLabel: { color: "#6a7782" },
  }
}

function renderCharts() {
  const rows = trendRows.value
  const dates = rows.map((r) => r.date.slice(5))
  const taskSeries = rows.map((r) => r.tasks)
  const revenueSeries = rows.map((r) => r.revenue)
  const taskTypeDist = dashboard.value?.task_type_dist || []
  const platformDist = dashboard.value?.platform_dist || []
  const funnel = dashboard.value?.funnel || {}

  taskChart = initChart(taskChartEl.value, taskChart)
  revenueChart = initChart(revenueChartEl.value, revenueChart)
  taskTypeChart = initChart(taskTypeChartEl.value, taskTypeChart)
  platformChart = initChart(platformChartEl.value, platformChart)
  funnelChart = initChart(funnelChartEl.value, funnelChart)

  if (taskChart) {
    taskChart.setOption({
      grid: { left: 36, right: 16, top: 16, bottom: 28 },
      xAxis: { type: "category", data: dates, ...baseAxisStyle(), splitLine: { show: false } },
      yAxis: { type: "value", ...baseAxisStyle() },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "line",
          smooth: true,
          data: taskSeries,
          areaStyle: { color: "rgba(23, 74, 82, 0.14)" },
          lineStyle: { width: 3, color: "#174a52" },
          symbol: "circle",
          symbolSize: 8,
          itemStyle: { color: "#174a52" },
        },
      ],
    })
  }
  if (revenueChart) {
    revenueChart.setOption({
      grid: { left: 36, right: 16, top: 16, bottom: 28 },
      xAxis: { type: "category", data: dates, ...baseAxisStyle(), splitLine: { show: false } },
      yAxis: { type: "value", ...baseAxisStyle() },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "line",
          smooth: true,
          data: revenueSeries,
          areaStyle: { color: "rgba(138, 100, 53, 0.16)" },
          lineStyle: { width: 3, color: "#8a6435" },
          symbol: "circle",
          symbolSize: 8,
          itemStyle: { color: "#8a6435" },
        },
      ],
    })
  }
  if (taskTypeChart) {
    taskTypeChart.setOption({
      grid: { left: 72, right: 16, top: 12, bottom: 24 },
      xAxis: { type: "value", ...baseAxisStyle() },
      yAxis: {
        type: "category",
        data: taskTypeDist.map((r) => r.task_type),
        ...baseAxisStyle(),
        splitLine: { show: false },
      },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "bar",
          data: taskTypeDist.map((r) => r.count),
          itemStyle: { color: "#174a52", borderRadius: [0, 8, 8, 0] },
          barWidth: 18,
        },
      ],
    })
  }
  if (platformChart) {
    platformChart.setOption({
      grid: { left: 36, right: 16, top: 12, bottom: 28 },
      xAxis: { type: "category", data: platformDist.map((r) => r.platform), ...baseAxisStyle(), splitLine: { show: false } },
      yAxis: { type: "value", ...baseAxisStyle() },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "bar",
          data: platformDist.map((r) => r.count),
          itemStyle: { color: "#4e7283", borderRadius: [8, 8, 0, 0] },
          barWidth: 34,
        },
      ],
    })
  }
  if (funnelChart) {
    const visitors = funnel.visitors || 0
    const registered = funnel.registered || 0
    const paidUsers = funnel.paid_users || 0
    const taskUsers = funnel.task_users || 0
    funnelChart.setOption({
      grid: { left: 70, right: 16, top: 12, bottom: 24 },
      xAxis: { type: "value", ...baseAxisStyle() },
      yAxis: {
        type: "category",
        data: ["访问用户", "注册用户", "支付用户", "任务用户"],
        ...baseAxisStyle(),
        splitLine: { show: false },
      },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "bar",
          data: [visitors, registered, paidUsers, taskUsers],
          itemStyle: { color: "#8a6435", borderRadius: [0, 8, 8, 0] },
          barWidth: 20,
        },
      ],
    })
  }
}

function handleResize() {
  if (taskChart) taskChart.resize()
  if (revenueChart) revenueChart.resize()
  if (taskTypeChart) taskTypeChart.resize()
  if (platformChart) platformChart.resize()
  if (funnelChart) funnelChart.resize()
}

function disposeCharts() {
  if (taskChart) taskChart.dispose()
  if (revenueChart) revenueChart.dispose()
  if (taskTypeChart) taskTypeChart.dispose()
  if (platformChart) platformChart.dispose()
  if (funnelChart) funnelChart.dispose()
  taskChart = null
  revenueChart = null
  taskTypeChart = null
  platformChart = null
  funnelChart = null
}
</script>
