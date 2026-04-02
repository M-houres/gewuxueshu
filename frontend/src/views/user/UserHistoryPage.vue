<template>
  <UserShell title="任务记录" subtitle="查看任务状态、结果摘要、失败原因与下载入口。" :credits="userCredits" @buy="showBuy = !showBuy">
    <section v-if="isGuest" class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <div class="scholar-kicker">Guest Mode</div>
        <h3 class="scholar-subtitle">游客模式下不展示任务历史</h3>
        <p class="scholar-lead">
          任务记录属于个人数据，登录后可查看处理状态、失败原因、结果摘要和文件下载。
        </p>
        <button class="scholar-button" type="button" style="margin-top: 18px" @click="goLogin">
          登录后查看任务记录
        </button>
      </div>
    </section>

    <section v-else class="scholar-panel">
      <div class="scholar-panel__header">
        <div class="scholar-kicker">Filters</div>
        <h3 class="scholar-subtitle">筛选与检索</h3>
      </div>

      <div class="scholar-panel__body">
        <div class="scholar-stack">
          <div>
            <div class="scholar-field__label">任务类型</div>
            <div class="scholar-inline-actions" style="margin-top: 10px">
              <button
                v-for="item in taskTypeOptions"
                :key="item.value || 'all-task'"
                type="button"
                class="scholar-chip"
                :class="{ 'is-active': filters.taskType === item.value }"
                @click="filters.taskType = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>

          <div>
            <div class="scholar-field__label">目标平台</div>
            <div class="scholar-inline-actions" style="margin-top: 10px">
              <button
                v-for="item in platformOptions"
                :key="item.value || 'all-platform'"
                type="button"
                class="scholar-chip"
                :class="{ 'is-active': filters.platform === item.value }"
                @click="filters.platform = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>

          <div>
            <div class="scholar-field__label">处理状态</div>
            <div class="scholar-inline-actions" style="margin-top: 10px">
              <button
                v-for="item in statusOptions"
                :key="item.value || 'all-status'"
                type="button"
                class="scholar-chip"
                :class="{ 'is-active': filters.status === item.value }"
                @click="filters.status = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>

          <div class="scholar-grid md:grid-cols-[1fr_1fr_auto]">
            <input v-model="filters.startDate" type="date" class="scholar-input" />
            <input v-model="filters.endDate" type="date" class="scholar-input" />
            <div class="scholar-inline-actions">
              <button class="scholar-button" type="button" @click="applyFilters">查询</button>
              <button class="scholar-button scholar-button--secondary" type="button" @click="resetFilters">
                重置
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="!isGuest" class="scholar-panel">
      <div class="scholar-panel__header">
        <div class="scholar-kicker">Task List</div>
        <h3 class="scholar-subtitle">历史任务</h3>
      </div>

      <div class="scholar-panel__body">
        <div class="overflow-x-auto">
          <table class="scholar-table">
            <thead>
              <tr>
                <th>任务 ID</th>
                <th>类型</th>
                <th>平台</th>
                <th>状态</th>
                <th>字符数</th>
                <th>积分</th>
                <th>时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in tasks" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ mapTaskType(item.task_type) }}</td>
                <td>{{ mapPlatform(item.platform) }}</td>
                <td>
                  <span class="scholar-badge" :class="statusClass(item.status)">
                    {{ mapStatus(item.status) }}
                  </span>
                </td>
                <td>{{ item.char_count }}</td>
                <td>{{ item.cost_credits }}</td>
                <td>{{ formatTime(item.created_at) }}</td>
                <td>
                  <div class="scholar-inline-actions">
                    <button
                      class="scholar-button scholar-button--secondary"
                      type="button"
                      :disabled="item.status !== 'completed'"
                      @click="openResult(item)"
                    >
                      查看结果
                    </button>
                    <button
                      class="scholar-button"
                      type="button"
                      :disabled="item.status !== 'completed'"
                      @click="download(item.id)"
                    >
                      下载结果
                    </button>
                    <button
                      class="scholar-button scholar-button--secondary"
                      type="button"
                      :disabled="item.status !== 'failed'"
                      @click="showError(item)"
                    >
                      查看原因
                    </button>
                    <button
                      class="scholar-button scholar-button--ghost"
                      type="button"
                      @click="removeTask(item)"
                    >
                      删除记录
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="tasks.length === 0">
                <td colspan="8">
                  <div class="scholar-empty">暂无任务记录</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="totalPages > 1" class="scholar-inline-actions" style="justify-content: center; margin-top: 18px">
          <button class="scholar-button scholar-button--secondary" type="button" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">
            上一页
          </button>
          <span class="scholar-pill">第 {{ currentPage }} / {{ totalPages }} 页</span>
          <button class="scholar-button scholar-button--secondary" type="button" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">
            下一页
          </button>
        </div>
      </div>
    </section>

    <div v-if="selectedTask" class="scholar-modal" @click.self="closeResult">
      <div class="scholar-modal__dialog">
        <div class="scholar-panel__header">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="scholar-kicker">Task Result</div>
              <h3 class="scholar-subtitle">{{ mapTaskType(selectedTask.task_type) }}结果摘要</h3>
              <p class="scholar-lead">{{ resultSummary(selectedTask) }}</p>
            </div>
            <button class="scholar-button scholar-button--secondary" type="button" @click="closeResult">
              关闭
            </button>
          </div>
        </div>

        <div class="scholar-panel__body">
          <div class="scholar-grid scholar-grid--stats">
            <article v-for="metric in resultMetrics(selectedTask)" :key="metric.label" class="scholar-stat">
              <div class="scholar-stat__label">{{ metric.label }}</div>
              <div class="scholar-stat__value" style="font-size: 26px">{{ metric.value }}</div>
            </article>
          </div>

          <section v-if="resultReportMetrics(selectedTask).length" class="scholar-panel scholar-panel--soft" style="margin-top: 18px">
            <div class="scholar-panel__body">
              <div class="scholar-kicker">Report Metrics</div>
              <h4 class="scholar-subtitle">辅助报告指标</h4>
              <div class="scholar-grid md:grid-cols-2" style="margin-top: 16px">
                <div
                  v-for="metric in resultReportMetrics(selectedTask)"
                  :key="metric.label"
                  class="scholar-note"
                >
                  {{ metric.label }}：{{ metric.value }}{{ metric.unit || "" }}
                </div>
              </div>
            </div>
          </section>

          <section v-if="resultRiskParagraphs(selectedTask).length" class="scholar-panel scholar-panel--soft" style="margin-top: 18px">
            <div class="scholar-panel__body">
              <div class="scholar-kicker">High Risk Paragraphs</div>
              <h4 class="scholar-subtitle">高风险段落</h4>
              <div class="scholar-list" style="margin-top: 16px">
                <div
                  v-for="item in resultRiskParagraphs(selectedTask)"
                  :key="`${item.index}-${item.score}`"
                  class="scholar-list-item"
                >
                  <div class="text-xs text-[var(--ink-faint)]">段落 {{ item.index }} / 风险 {{ item.score }}%</div>
                  <div class="mt-2 text-sm leading-7 text-[var(--ink-soft)]">{{ item.excerpt }}</div>
                </div>
              </div>
            </div>
          </section>

          <section v-if="resultReviewPoints(selectedTask).length" class="scholar-panel scholar-panel--soft" style="margin-top: 18px">
            <div class="scholar-panel__body">
              <div class="scholar-kicker">Review Suggestions</div>
              <h4 class="scholar-subtitle">复核建议</h4>
              <div class="scholar-list" style="margin-top: 16px">
                <div v-for="point in resultReviewPoints(selectedTask)" :key="point" class="scholar-list-item">
                  {{ point }}
                </div>
              </div>
            </div>
          </section>

          <section v-if="resultOutputPreview(selectedTask)" class="scholar-panel scholar-panel--soft" style="margin-top: 18px">
            <div class="scholar-panel__body">
              <div class="scholar-kicker">Output Preview</div>
              <h4 class="scholar-subtitle">结果预览</h4>
              <div class="scholar-note" style="margin-top: 16px; white-space: pre-wrap">
                {{ resultOutputPreview(selectedTask) }}
              </div>
            </div>
          </section>

          <div class="scholar-inline-actions" style="margin-top: 18px">
            <button class="scholar-button" type="button" @click="download(selectedTask.id)">下载结果文件</button>
            <button class="scholar-button scholar-button--secondary" type="button" @click="closeResult">
              返回列表
            </button>
          </div>
        </div>
      </div>
    </div>

    <BuyCreditsPanel v-if="showBuy" @paid="afterPaid" />
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
  { value: "aigc_detect", label: "AIGC 检测" },
  { value: "dedup", label: "降重复率" },
  { value: "rewrite", label: "降 AIGC 率" },
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
    aigc_detect: "AIGC 检测",
    dedup: "降重复率",
    rewrite: "降 AIGC 率",
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
  if (status === "completed") return "scholar-badge--success"
  if (status === "failed") return "scholar-badge--danger"
  if (status === "running") return "scholar-badge--info"
  return "scholar-badge--warn"
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
