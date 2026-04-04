<template>
  <AdminShell title="任务管理" subtitle="多维筛选与任务详情">
    <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
      <div class="mb-4 space-y-4 rounded-2xl border border-[#dee6ed] bg-[#f8fbff] p-4">
        <div class="grid gap-2 md:grid-cols-[1fr_1fr_1fr]">
          <input v-model.trim="filters.qPhone" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none" placeholder="用户手机号" />
          <input v-model="filters.startDate" type="date" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none" />
          <input v-model="filters.endDate" type="date" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none" />
        </div>
        <div class="space-y-3">
          <div>
            <div class="mb-2 text-xs font-semibold tracking-[0.08em] text-[#6b7a86]">任务类型</div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="item in taskTypeOptions"
                :key="item.value || 'all-task'"
                type="button"
                :class="chipClass(filters.taskType, item.value)"
                @click="filters.taskType = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
          <div>
            <div class="mb-2 text-xs font-semibold tracking-[0.08em] text-[#6b7a86]">目标平台</div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="item in platformOptions"
                :key="item.value || 'all-platform'"
                type="button"
                :class="chipClass(filters.platform, item.value)"
                @click="filters.platform = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
          <div>
            <div class="mb-2 text-xs font-semibold tracking-[0.08em] text-[#6b7a86]">处理状态</div>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="item in statusOptions"
                :key="item.value || 'all-status'"
                type="button"
                :class="chipClass(filters.status, item.value)"
                @click="filters.status = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>
        </div>
        <div class="flex gap-2">
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="loadData">查询</button>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="resetFilters">重置</button>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
              <th class="px-2 py-2">任务ID</th>
              <th class="px-2 py-2">用户ID</th>
              <th class="px-2 py-2">类型</th>
              <th class="px-2 py-2">平台</th>
              <th class="px-2 py-2">状态</th>
              <th class="px-2 py-2">字符数</th>
              <th class="px-2 py-2">积分</th>
              <th class="px-2 py-2">创建时间</th>
              <th class="px-2 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id" class="border-b border-[#eef2f5]">
              <td class="px-2 py-2">{{ row.id }}</td>
              <td class="px-2 py-2">{{ row.user_id }}</td>
              <td class="px-2 py-2">{{ mapTaskType(row.task_type) }}</td>
              <td class="px-2 py-2">{{ mapPlatform(row.platform) }}</td>
              <td class="px-2 py-2">
                <span :class="statusClass(row.status)" class="inline-flex items-center rounded-full border px-2 py-1 text-xs">
                  {{ mapStatus(row.status) }}
                </span>
              </td>
              <td class="px-2 py-2">{{ row.char_count }}</td>
              <td class="px-2 py-2">{{ row.cost_credits }}</td>
              <td class="px-2 py-2">{{ formatTime(row.created_at) }}</td>
              <td class="px-2 py-2">
                <button class="rounded bg-[#0f7a5f] px-2 py-1 text-xs text-white" @click="openDetail(row.id)">查看详情</button>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td class="px-2 py-3 text-[#5b6771]" colspan="9">暂无任务</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="taskDetail" class="mt-4 rounded-2xl border border-[#d9dee4] bg-white p-5">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">Task Insight</div>
          <h3 class="mt-2 text-base font-semibold">任务详情 #{{ taskDetail.id }}</h3>
          <p class="mt-1 text-sm leading-6 text-[#5c6872]">{{ resultSummary(taskDetail) }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            class="rounded-lg bg-[#0f7a5f] px-3 py-2 text-sm text-white disabled:opacity-50"
            :disabled="taskDetail.status !== 'completed'"
            @click="downloadResult(taskDetail.id)"
          >
            下载结果
          </button>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="openDetail(taskDetail.id)">刷新</button>
          <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="closeDetail">关闭</button>
        </div>
      </div>

      <div class="grid gap-2 text-sm md:grid-cols-2 xl:grid-cols-3">
        <div>用户：{{ taskDetail.user_id }} {{ taskDetail.user_phone ? `(${taskDetail.user_phone})` : "" }}</div>
        <div>类型：{{ mapTaskType(taskDetail.task_type) }}</div>
        <div>平台：{{ mapPlatform(taskDetail.platform) }}</div>
        <div>状态：{{ mapStatus(taskDetail.status) }}</div>
        <div>字符数：{{ taskDetail.char_count }}</div>
        <div>积分：{{ taskDetail.cost_credits }}</div>
        <div>原文件：{{ taskDetail.source_filename || "-" }}</div>
        <div>创建时间：{{ formatTime(taskDetail.created_at) }}</div>
        <div>更新时间：{{ formatTime(taskDetail.updated_at) }}</div>
        <div class="xl:col-span-3">辅助报告：{{ taskDetail.report_path || "-" }}</div>
        <div class="xl:col-span-3">结果文件：{{ taskDetail.output_path || "-" }}</div>
        <div class="xl:col-span-3">错误信息：{{ taskDetail.error_message || "-" }}</div>
      </div>

      <div v-if="resultMetrics(taskDetail).length" class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article v-for="metric in resultMetrics(taskDetail)" :key="metric.label" class="rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
          <div class="text-xs tracking-[0.1em] text-[#6d7a86]">{{ metric.label }}</div>
          <div class="mt-2 text-lg font-semibold text-[#16222a]">{{ metric.value }}</div>
        </article>
      </div>

      <section v-if="resultReportMetrics(taskDetail).length" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
        <h4 class="text-sm font-semibold text-[#1c2831]">辅助报告指标</h4>
        <div class="mt-3 grid gap-3 md:grid-cols-2">
          <div v-for="metric in resultReportMetrics(taskDetail)" :key="metric.label" class="rounded-xl border border-[#e4eaf0] bg-white px-3 py-2 text-sm text-[#44525d]">
            {{ metric.label }}：{{ metric.value }}{{ metric.unit || "" }}
          </div>
        </div>
      </section>

      <section v-if="resultRiskParagraphs(taskDetail).length" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
        <h4 class="text-sm font-semibold text-[#1c2831]">高风险段落</h4>
        <div class="mt-3 space-y-3">
          <div v-for="item in resultRiskParagraphs(taskDetail)" :key="`${item.index}-${item.score}`" class="rounded-xl border border-[#e4eaf0] bg-white p-3">
            <div class="text-xs text-[#6b7884]">段落 {{ item.index }} · 风险 {{ item.score }}%</div>
            <div class="mt-2 text-sm leading-6 text-[#31404b]">{{ item.excerpt }}</div>
          </div>
        </div>
      </section>

      <section v-if="resultReviewPoints(taskDetail).length" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
        <h4 class="text-sm font-semibold text-[#1c2831]">复核建议</h4>
        <div class="mt-3 space-y-2">
          <div v-for="point in resultReviewPoints(taskDetail)" :key="point" class="flex items-start gap-2 rounded-xl border border-[#e4eaf0] bg-white px-3 py-2">
            <span class="mt-1 h-1.5 w-1.5 rounded-full bg-[#0f7a5f]"></span>
            <span class="text-sm leading-6 text-[#3c4b56]">{{ point }}</span>
          </div>
        </div>
      </section>

      <section v-if="resultOutputPreview(taskDetail)" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
        <h4 class="text-sm font-semibold text-[#1c2831]">结果预览</h4>
        <div class="mt-3 whitespace-pre-wrap rounded-xl border border-[#e4eaf0] bg-white p-3 text-sm leading-6 text-[#2f3d48]">
          {{ resultOutputPreview(taskDetail) }}
        </div>
      </section>

      <section v-if="taskDetail.result_json" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
        <h4 class="text-sm font-semibold text-[#1c2831]">原始结果 JSON</h4>
        <pre class="mt-3 overflow-x-auto rounded-xl border border-[#e4eaf0] bg-white p-3 text-xs leading-6 text-[#31404b]">{{ formatJson(taskDetail.result_json) }}</pre>
      </section>
    </section>
  </AdminShell>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import AdminShell from "../../components/AdminShell.vue"
import { downloadAxiosBlobResponse } from "../../lib/download"
import { adminHttp } from "../../lib/http"
import {
  taskResultMetrics,
  taskResultOutputPreview,
  taskResultReportMetrics,
  taskResultReviewPoints,
  taskResultRiskParagraphs,
  taskResultSummary,
} from "../../lib/taskResult"

const rows = ref([])
const taskDetail = ref(null)
const route = useRoute()
const router = useRouter()
const filters = reactive({
  qPhone: "",
  taskType: "",
  platform: "",
  status: "",
  startDate: "",
  endDate: "",
})
let syncingRouteTask = false
const taskTypeOptions = [
  { value: "", label: "全部" },
  { value: "aigc_detect", label: "AIGC检测" },
  { value: "dedup", label: "降重" },
  { value: "rewrite", label: "降AIGC率" },
]
const platformOptions = [
  { value: "", label: "全部" },
  { value: "cnki", label: "格物学术标准版" },
  { value: "vip", label: "格物学术专业版" },
  { value: "paperpass", label: "格物学术极速版" },
]
const statusOptions = [
  { value: "", label: "全部" },
  { value: "pending", label: "等待中" },
  { value: "running", label: "处理中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
]

watch(
  () => route.query.task_id,
  async (value) => {
    if (syncingRouteTask) {
      return
    }
    const taskId = Number(value || 0)
    if (Number.isInteger(taskId) && taskId > 0) {
      await openDetail(taskId, { syncRoute: false })
      return
    }
    taskDetail.value = null
  }
)

onMounted(async () => {
  await loadData()
  await syncTaskFromRoute()
})

async function loadData() {
  const params = {
    page: 1,
    page_size: 100,
    q_phone: filters.qPhone || undefined,
    task_type: filters.taskType || undefined,
    platform: filters.platform || undefined,
    status: filters.status || undefined,
    start_date: filters.startDate || undefined,
    end_date: filters.endDate || undefined,
  }
  const data = await adminHttp.get("/admin/tasks", { params })
  rows.value = data.items || []
}

function resetFilters() {
  filters.qPhone = ""
  filters.taskType = ""
  filters.platform = ""
  filters.status = ""
  filters.startDate = ""
  filters.endDate = ""
  loadData()
}

async function syncTaskFromRoute() {
  const taskId = Number(route.query.task_id || 0)
  if (Number.isInteger(taskId) && taskId > 0) {
    await openDetail(taskId, { syncRoute: false })
  }
}

async function openDetail(taskId, options = {}) {
  taskDetail.value = await adminHttp.get(`/admin/tasks/${taskId}/detail`)
  if (options.syncRoute === false) {
    return
  }
  syncingRouteTask = true
  try {
    await router.replace({ path: "/admin/tasks", query: { task_id: String(taskId) } })
  } finally {
    syncingRouteTask = false
  }
}

async function downloadResult(taskId) {
  const resp = await adminHttp.get(`/admin/tasks/${taskId}/download`, { responseType: "blob" })
  downloadAxiosBlobResponse(resp, `admin_task_${taskId}_result`)
}

async function closeDetail() {
  taskDetail.value = null
  if (!route.query.task_id) {
    return
  }
  syncingRouteTask = true
  try {
    await router.replace({ path: "/admin/tasks" })
  } finally {
    syncingRouteTask = false
  }
}

function mapTaskType(type) {
  const mapping = {
    aigc_detect: "AIGC检测",
    dedup: "降重",
    rewrite: "降AIGC率",
  }
  return mapping[type] || type
}

function mapPlatform(platform) {
  const mapping = {
    cnki: "格物学术标准版",
    vip: "格物学术专业版",
    paperpass: "格物学术极速版",
  }
  return mapping[platform] || platform
}

function mapStatus(status) {
  const mapping = {
    pending: "等待中",
    running: "处理中",
    completed: "已完成",
    failed: "失败",
  }
  return mapping[status] || status
}

function statusClass(status) {
  if (status === "completed") return "border-[#b8e7d5] bg-[#dbf5ea] text-[#106c4f]"
  if (status === "failed") return "border-[#f4c5c1] bg-[#ffe1df] text-[#9c2d2a]"
  return "border-[#f2dfb3] bg-[#fff2d8] text-[#8a5a10]"
}

function chipClass(current, value) {
  const active = current === value
  if (active) {
    return "rounded-xl border border-[#0f7a5f] bg-[#e8f4ef] px-3 py-1.5 text-sm font-medium text-[#0f6c53]"
  }
  return "rounded-xl border border-[#cfd8e0] bg-white px-3 py-1.5 text-sm text-[#485864] hover:border-[#98adbb]"
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function resultSummary(task) {
  return taskResultSummary(task)
}

function resultMetrics(task) {
  return taskResultMetrics(task)
}

function resultReportMetrics(task) {
  return taskResultReportMetrics(task)
}

function resultRiskParagraphs(task) {
  return taskResultRiskParagraphs(task)
}

function resultReviewPoints(task) {
  return taskResultReviewPoints(task)
}

function resultOutputPreview(task) {
  return taskResultOutputPreview(task)
}

function formatJson(value) {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value || "")
  }
}
</script>
