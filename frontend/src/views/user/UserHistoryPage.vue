<template>
  <UserShell title="任务记录" subtitle="查看任务状态和下载结果" :credits="userCredits" @buy="showBuy = !showBuy">
    <div class="space-y-4">
      <section v-if="isGuest" class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">游客模式</h3>
        <p class="mt-2 text-sm leading-6 text-[#556470]">任务记录属于个人数据，登录后可查看处理状态、失败原因和结果下载。</p>
        <button class="mt-4 rounded-lg bg-[#0f7a5f] px-4 py-2 text-sm text-white" @click="goLogin">
          登录后查看任务记录
        </button>
      </section>

      <section v-else class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="mb-4 space-y-4 rounded-2xl border border-[#dee6ed] bg-[#f8fbff] p-4">
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
          <div class="grid gap-2 md:grid-cols-[1fr_1fr_auto]">
            <input v-model="filters.startDate" type="date" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none" />
            <input v-model="filters.endDate" type="date" class="rounded-lg border border-[#ccd5dd] px-3 py-2 text-sm outline-none" />
            <div class="flex gap-2 md:justify-end">
              <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#32414f]" @click="applyFilters">查询</button>
              <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-sm text-[#32414f]" @click="resetFilters">重置</button>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">任务ID</th>
                <th class="px-2 py-2">类型</th>
                <th class="px-2 py-2">平台</th>
                <th class="px-2 py-2">状态</th>
                <th class="px-2 py-2">字符数</th>
                <th class="px-2 py-2">积分</th>
                <th class="px-2 py-2">时间</th>
                <th class="px-2 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in tasks" :key="item.id" class="border-b border-[#eef2f5]">
                <td class="px-2 py-2">{{ item.id }}</td>
                <td class="px-2 py-2">{{ mapTaskType(item.task_type) }}</td>
                <td class="px-2 py-2">{{ mapPlatform(item.platform) }}</td>
                <td class="px-2 py-2">
                  <span :class="statusClass(item.status)" class="inline-flex items-center rounded-full border px-2 py-1 text-xs">
                    {{ mapStatus(item.status) }}
                  </span>
                </td>
                <td class="px-2 py-2">{{ item.char_count }}</td>
                <td class="px-2 py-2">{{ item.cost_credits }}</td>
                <td class="px-2 py-2">{{ formatTime(item.created_at) }}</td>
                <td class="px-2 py-2">
                  <div class="flex gap-2">
                    <button class="rounded bg-[#edf2f6] px-2 py-1 text-xs text-[#344250] disabled:opacity-40" :disabled="item.status !== 'completed'" @click="openResult(item)">
                      查看结果
                    </button>
                    <button class="rounded bg-[#0f7a5f] px-2 py-1 text-xs text-white disabled:opacity-40" :disabled="item.status !== 'completed'" @click="download(item.id)">
                      下载结果
                    </button>
                    <button
                      class="rounded bg-[#edf2f6] px-2 py-1 text-xs text-[#344250] disabled:opacity-40"
                      :disabled="item.status !== 'failed'"
                      @click="showError(item)"
                    >
                      查看原因
                    </button>
                    <button class="rounded bg-[#edf2f6] px-2 py-1 text-xs text-[#344250]" @click="removeTask(item)">
                      删除记录
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="tasks.length === 0">
                <td class="px-2 py-3 text-[#5b6771]" colspan="8">暂无任务记录</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="totalPages > 1" class="mt-4 flex items-center justify-center gap-2">
          <button class="rounded bg-[#edf2f6] px-3 py-1 text-sm text-[#344250] disabled:opacity-50" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">上一页</button>
          <span class="text-sm text-[#5b6771]">第 {{ currentPage }} / {{ totalPages }} 页</span>
          <button class="rounded bg-[#edf2f6] px-3 py-1 text-sm text-[#344250] disabled:opacity-50" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页</button>
        </div>
      </section>

      <div v-if="selectedTask" class="fixed inset-0 z-30 flex items-center justify-center bg-[#0d141a]/45 px-4 py-6">
        <div class="max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-[28px] border border-[#d5dde4] bg-white p-6 shadow-[0_24px_60px_rgba(16,24,34,0.22)]">
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">Task Result</div>
              <h3 class="mt-2 text-xl font-semibold text-[#18242b]">{{ mapTaskType(selectedTask.task_type) }}结果摘要</h3>
              <p class="mt-2 text-sm leading-6 text-[#5b6771]">{{ resultSummary(selectedTask) }}</p>
            </div>
            <button class="rounded-full bg-[#eef2f6] px-3 py-1.5 text-sm text-[#344250]" @click="closeResult">关闭</button>
          </div>

          <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <article v-for="metric in resultMetrics(selectedTask)" :key="metric.label" class="rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
              <div class="text-xs tracking-[0.1em] text-[#6d7a86]">{{ metric.label }}</div>
              <div class="mt-2 text-lg font-semibold text-[#16222a]">{{ metric.value }}</div>
            </article>
          </div>

          <section v-if="resultReportMetrics(selectedTask).length" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
            <h4 class="text-sm font-semibold text-[#1c2831]">辅助报告指标</h4>
            <div class="mt-3 grid gap-3 md:grid-cols-2">
              <div v-for="metric in resultReportMetrics(selectedTask)" :key="metric.label" class="rounded-xl border border-[#e4eaf0] bg-white px-3 py-2 text-sm text-[#44525d]">
                {{ metric.label }}：{{ metric.value }}{{ metric.unit || "" }}
              </div>
            </div>
          </section>

          <section v-if="resultRiskParagraphs(selectedTask).length" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
            <h4 class="text-sm font-semibold text-[#1c2831]">高风险段落</h4>
            <div class="mt-3 space-y-3">
              <div v-for="item in resultRiskParagraphs(selectedTask)" :key="`${item.index}-${item.score}`" class="rounded-xl border border-[#e4eaf0] bg-white p-3">
                <div class="text-xs text-[#6b7884]">段落 {{ item.index }} · 风险 {{ item.score }}%</div>
                <div class="mt-2 text-sm leading-6 text-[#31404b]">{{ item.excerpt }}</div>
              </div>
            </div>
          </section>

          <section v-if="resultReviewPoints(selectedTask).length" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
            <h4 class="text-sm font-semibold text-[#1c2831]">复核建议</h4>
            <div class="mt-3 space-y-2">
              <div v-for="point in resultReviewPoints(selectedTask)" :key="point" class="flex items-start gap-2 rounded-xl border border-[#e4eaf0] bg-white px-3 py-2">
                <span class="mt-1 h-1.5 w-1.5 rounded-full bg-[#0f7a5f]"></span>
                <span class="text-sm leading-6 text-[#3c4b56]">{{ point }}</span>
              </div>
            </div>
          </section>

          <section v-if="resultOutputPreview(selectedTask)" class="mt-5 rounded-2xl border border-[#dce3e9] bg-[#fbfcfd] p-4">
            <h4 class="text-sm font-semibold text-[#1c2831]">结果预览</h4>
            <div class="mt-3 whitespace-pre-wrap rounded-xl border border-[#e4eaf0] bg-white p-3 text-sm leading-6 text-[#2f3d48]">
              {{ resultOutputPreview(selectedTask) }}
            </div>
          </section>

          <div class="mt-5 flex flex-wrap items-center gap-2 border-t border-[#e7ecf0] pt-4">
            <button class="rounded-lg bg-[#0f7a5f] px-4 py-2 text-sm text-white" @click="download(selectedTask.id)">下载结果文件</button>
            <button class="rounded-lg bg-[#edf2f6] px-4 py-2 text-sm text-[#344250]" @click="closeResult">返回列表</button>
          </div>
        </div>
      </div>
      <BuyCreditsPanel v-if="showBuy" @paid="afterPaid" />
    </div>
  </UserShell>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { downloadAxiosBlobResponse } from "../../lib/download"
import { userHttp } from "../../lib/http"
import { ensureUserLogin } from "../../lib/requireLogin"
import { getUserToken } from "../../lib/session"
import {
  taskResultMetrics,
  taskResultOutputPreview,
  taskResultReportMetrics,
  taskResultReviewPoints,
  taskResultRiskParagraphs,
  taskResultSummary,
} from "../../lib/taskResult"

const route = useRoute()
const router = useRouter()
const showBuy = ref(false)
const tasks = ref([])
const selectedTask = ref(null)
const pageSize = 20
const total = ref(0)
const currentPage = ref(1)
const loadingTasks = ref(false)
const filters = reactive({
  taskType: "",
  platform: "",
  status: "",
  startDate: "",
  endDate: "",
})
let pollTimer = null
const taskTypeOptions = [
  { value: "", label: "全部" },
  { value: "aigc_detect", label: "AIGC检测" },
  { value: "dedup", label: "降重复率" },
  { value: "rewrite", label: "降AIGC率" },
]
const platformOptions = [
  { value: "", label: "全部" },
  { value: "cnki", label: "知网 CNKI" },
  { value: "vip", label: "维普 VIP" },
  { value: "paperpass", label: "PaperPass" },
]
const statusOptions = [
  { value: "", label: "全部" },
  { value: "pending", label: "等待中" },
  { value: "running", label: "处理中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
]

const { user, refreshUser } = useUserProfile()
const isGuest = computed(() => !getUserToken())
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  if (typeof value === "number") {
    return value
  }
  return null
})
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

watch(
  () => route.query.page,
  (value) => {
    const page = Number(value || 1)
    if (Number.isInteger(page) && page >= 1 && page !== currentPage.value) {
      currentPage.value = page
      loadTasks(false)
    }
  }
)

onMounted(async () => {
  if (getUserToken()) {
    await refreshUser()
  }
  const page = Number(route.query.page || 1)
  currentPage.value = Number.isInteger(page) && page >= 1 ? page : 1
  await loadTasks(false)
})

onBeforeUnmount(() => {
  clearPolling()
})

async function loadTasks(syncUrl = true) {
  if (!getUserToken()) {
    tasks.value = []
    total.value = 0
    clearPolling()
    return
  }
  if (loadingTasks.value) {
    return
  }
  loadingTasks.value = true
  const params = {
    page: currentPage.value,
    page_size: pageSize,
    task_type: filters.taskType || undefined,
    platform: filters.platform || undefined,
    status: filters.status || undefined,
    start_date: filters.startDate || undefined,
    end_date: filters.endDate || undefined,
  }
  try {
    const data = await userHttp.get("/tasks/my", { params })
    tasks.value = data.items || []
    total.value = data.pagination?.total || 0
    if (selectedTask.value) {
      selectedTask.value = tasks.value.find((item) => item.id === selectedTask.value.id) || selectedTask.value
    }
    syncPolling()
    if (syncUrl) {
      router.replace({ path: "/app/history", query: { page: String(currentPage.value) } })
    }
  } finally {
    loadingTasks.value = false
  }
}

async function applyFilters() {
  currentPage.value = 1
  await loadTasks(true)
}

async function resetFilters() {
  filters.taskType = ""
  filters.platform = ""
  filters.status = ""
  filters.startDate = ""
  filters.endDate = ""
  currentPage.value = 1
  await loadTasks(true)
}

async function goPage(page) {
  currentPage.value = page
  await loadTasks(true)
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/history")
  router.push(`/login?redirect=${redirect}`)
}

function openResult(item) {
  selectedTask.value = item
}

function closeResult() {
  selectedTask.value = null
}

async function download(taskId) {
  if (!ensureUserLogin(router, route, "/app/history")) {
    return
  }
  const resp = await userHttp.get(`/tasks/${taskId}/download`, { responseType: "blob" })
  downloadAxiosBlobResponse(resp, `task_${taskId}_result`)
}

function showError(item) {
  const msg = item.error_message || "暂无失败原因"
  window.alert(msg)
}

async function removeTask(item) {
  if (!ensureUserLogin(router, route, "/app/history")) {
    return
  }
  const confirmed = window.confirm(`确认删除任务 ${item.id} 吗？`)
  if (!confirmed) {
    return
  }
  await userHttp.delete(`/tasks/${item.id}`)
  await loadTasks(true)
}

function mapTaskType(type) {
  const mapping = {
    aigc_detect: "AIGC检测",
    dedup: "降重复率",
    rewrite: "降AIGC率",
  }
  return mapping[type] || type
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

function mapPlatform(platform) {
  const mapping = {
    cnki: "知网 CNKI",
    vip: "维普 VIP",
    paperpass: "PaperPass",
  }
  return mapping[platform] || platform
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

async function afterPaid() {
  if (getUserToken()) {
    await refreshUser()
  }
}

function syncPolling() {
  const hasActiveTask = tasks.value.some((item) => item.status === "pending" || item.status === "running")
  if (hasActiveTask && !pollTimer) {
    pollTimer = window.setInterval(() => {
      void loadTasks(false)
    }, 8000)
    return
  }
  if (!hasActiveTask) {
    clearPolling()
  }
}

function clearPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}
</script>
