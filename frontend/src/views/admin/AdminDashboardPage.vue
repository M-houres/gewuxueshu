<template>
  <AdminShell title="后台仪表盘" subtitle="每30秒自动刷新">
    <div class="space-y-4">
      <section
        v-if="switchStatus.current_mode === 'ALGO_ONLY'"
        class="rounded-2xl border border-[#f1c6c3] bg-[#fff1f0] px-4 py-3 text-sm text-[#8e302c]"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span>当前运行于仅算法降级模式，原因：{{ switchStatus.last_switch_reason || "LLM异常" }}</span>
          <button class="rounded bg-[#bc4138] px-3 py-1.5 text-white" @click="recoverMode">手动恢复大模型模式</button>
        </div>
      </section>

      <section class="grid gap-4 md:grid-cols-4">
        <article class="rounded-2xl border border-[#d9dee4] bg-white p-4" v-for="item in statCards" :key="item.label">
          <div class="text-xs text-[#5b6771]">{{ item.label }}</div>
          <div class="mt-2 text-2xl font-semibold">{{ item.value }}</div>
        </article>
      </section>

      <div class="grid gap-4 xl:grid-cols-2">
        <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-base font-semibold">近7天任务趋势</h3>
            <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadData">刷新</button>
          </div>
          <div ref="taskChartEl" class="h-64 w-full"></div>
        </section>

        <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-base font-semibold">近7天收入趋势</h3>
            <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadData">刷新</button>
          </div>
          <div ref="revenueChartEl" class="h-64 w-full"></div>
        </section>
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
          <h3 class="mb-3 text-base font-semibold">功能使用占比</h3>
          <div ref="taskTypeChartEl" class="h-56 w-full"></div>
        </section>

        <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
          <h3 class="mb-3 text-base font-semibold">平台使用量对比</h3>
          <div ref="platformChartEl" class="h-56 w-full"></div>
        </section>
      </div>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="mb-3 text-base font-semibold">用户转化对比</h3>
        <div ref="funnelChartEl" class="h-48 w-full"></div>
      </section>
    </div>
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
    { label: "总用户数", value: totalUsers },
    { label: "总任务量", value: totalTasks },
    { label: "支付订单数", value: totalOrders },
    { label: "累计收入", value: totalRevenue },
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
  const confirmed = window.confirm("确认手动切换回大模型+算法模式吗？")
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
      grid: { left: 36, right: 12, top: 16, bottom: 28 },
      xAxis: { type: "category", data: dates },
      yAxis: { type: "value" },
      tooltip: { trigger: "axis" },
      series: [{ type: "line", smooth: true, data: taskSeries, areaStyle: {}, lineStyle: { width: 3, color: "#0f7a5f" } }],
    })
  }
  if (revenueChart) {
    revenueChart.setOption({
      grid: { left: 36, right: 12, top: 16, bottom: 28 },
      xAxis: { type: "category", data: dates },
      yAxis: { type: "value" },
      tooltip: { trigger: "axis" },
      series: [{ type: "line", smooth: true, data: revenueSeries, lineStyle: { width: 3, color: "#1d5ea8" }, areaStyle: {} }],
    })
  }
  if (taskTypeChart) {
    taskTypeChart.setOption({
      grid: { left: 56, right: 12, top: 8, bottom: 24 },
      xAxis: { type: "value" },
      yAxis: { type: "category", data: taskTypeDist.map((r) => r.task_type) },
      tooltip: { trigger: "axis" },
      series: [{ type: "bar", data: taskTypeDist.map((r) => r.count), itemStyle: { color: "#0f7a5f" }, barWidth: 18 }],
    })
  }
  if (platformChart) {
    platformChart.setOption({
      grid: { left: 36, right: 12, top: 8, bottom: 28 },
      xAxis: { type: "category", data: platformDist.map((r) => r.platform) },
      yAxis: { type: "value" },
      tooltip: { trigger: "axis" },
      series: [{ type: "bar", data: platformDist.map((r) => r.count), itemStyle: { color: "#2f7bde" }, barWidth: 34 }],
    })
  }
  if (funnelChart) {
    const visitors = funnel.visitors || 0
    const registered = funnel.registered || 0
    const paidUsers = funnel.paid_users || 0
    const taskUsers = funnel.task_users || 0
    funnelChart.setOption({
      grid: { left: 56, right: 12, top: 10, bottom: 24 },
      xAxis: { type: "value" },
      yAxis: { type: "category", data: ["访问用户", "注册用户", "支付用户", "任务用户"] },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "bar",
          data: [visitors, registered, paidUsers, taskUsers],
          itemStyle: { color: "#2f7bde" },
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
