<template>
  <UserShell
    title="降AIGC率"
    subtitle="任务按时间倒序展示，最新提交优先在顶部显示。"
    :credits="userCredits"
    :hide-topbar="true"
    @buy="showBuy = !showBuy"
  >
    <section class="aigc-record-head">
      <div class="aigc-record-head__title">降AIGC率</div>
      <p class="aigc-record-head__hint">
        <span>i</span>
        保留论点结构并降低AI痕迹，完成后可下载处理文档。
      </p>
    </section>

    <section class="aigc-record-tools">
      <div class="aigc-record-tools__left">
        <label class="aigc-search">
          <svg viewBox="0 0 24 24">
            <path
              d="M11 4.5a6.5 6.5 0 1 1 0 13a6.5 6.5 0 0 1 0-13Zm0 0v0m8.5 13.5L17 15.5"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.8"
            />
          </svg>
          <input v-model.trim="keyword" type="text" placeholder="请输入关键词" />
        </label>

        <div class="aigc-status-tabs">
          <button
            v-for="tab in statusTabs"
            :key="tab.key"
            type="button"
            class="aigc-status-tabs__item"
            :class="{ 'is-active': statusFilter === tab.key }"
            @click="statusFilter = tab.key"
          >
            {{ tab.label }}（{{ tab.count }}）
          </button>
        </div>
      </div>

      <button class="scholar-button scholar-button--secondary aigc-record-tools__upload" type="button" @click="goUpload">
        上传文档
      </button>
    </section>

    <p class="aigc-record-retain">报告将保留 30 天，请及时下载与归档。</p>

    <section v-if="loading" class="scholar-note">正在加载记录...</section>

    <section v-else-if="pagedTasks.length === 0" class="aigc-empty">
      <div class="aigc-empty__icon">R</div>
      <h3>暂无降AIGC记录</h3>
      <p>提交任务后，这里会显示处理进度与结果下载入口。</p>
      <button class="scholar-button" type="button" @click="goUpload">立即上传</button>
    </section>

    <section v-else class="aigc-record-list">
      <article
        v-for="item in pagedTasks"
        :id="`rewrite-task-${item.id}`"
        :key="item.id"
        class="aigc-record-item"
        :class="{ 'is-focused': focusTaskId === item.id }"
      >
        <div class="aigc-record-item__left">
          <div class="aigc-record-item__title-row">
            <button class="aigc-record-item__title" type="button" @click="openDetails(item)">
              {{ item.source_filename || `任务 #${item.id}` }}
            </button>
          </div>

          <div class="aigc-record-item__meta">
            <div>作者：{{ safeText(item.result_json?.authors) }}</div>
            <div>提交时间：{{ formatTime(item.created_at) }}</div>
            <div>文档字数：{{ item.char_count || 0 }}</div>
            <div>消耗积分：{{ item.cost_credits || 0 }} 积分</div>
            <div>AIGC报告：{{ item.has_report ? "已上传" : "未上传" }}</div>
          </div>
        </div>

        <div class="aigc-record-item__mid">
          <template v-if="item.status === 'completed'">
            <span class="service-status-tag service-status-tag--success">已完成</span>
            <div class="aigc-record-item__score">{{ changeRate(item) }}</div>
            <div class="aigc-record-item__score-note">降AIGC幅度</div>
          </template>
          <template v-else-if="item.status === 'running' || item.status === 'pending'">
            <span class="service-status-tag service-status-tag--processing">处理中</span>
            <div class="service-dot-loading"><span /><span /><span /></div>
            <div class="aigc-record-item__score-note">预计 3-10 分钟完成</div>
          </template>
          <template v-else>
            <span class="service-status-tag service-status-tag--failed">处理异常</span>
          </template>
        </div>

        <div class="aigc-record-item__right">
          <button
            class="aigc-record-item__delete"
            type="button"
            :disabled="item.status === 'running' || removingId === item.id"
            @click="removeTask(item)"
          >
            删除
          </button>

          <template v-if="item.status === 'completed'">
            <button class="aigc-record-item__detail" type="button" @click="openDetails(item)">查看详情</button>
            <button class="scholar-button scholar-button--secondary" type="button" @click="downloadResult(item.id)">
              下载改写文档
            </button>
            <p class="aigc-record-item__deadline">有效期至：{{ reportDeadline(item.created_at) }}</p>
          </template>
          <template v-else>
            <p class="aigc-record-item__waiting">处理完成后可下载</p>
          </template>
        </div>
      </article>
    </section>

    <nav v-if="totalPages > 1" class="aigc-pagination">
      <button type="button" :disabled="page <= 1" @click="page -= 1">上一页</button>
      <button
        v-for="num in visiblePages"
        :key="num"
        type="button"
        :class="{ 'is-active': page === num }"
        @click="page = num"
      >
        {{ num }}
      </button>
      <button type="button" :disabled="page >= totalPages" @click="page += 1">下一页</button>
    </nav>

    <div v-if="selectedTask" class="scholar-modal" @click.self="selectedTask = null">
      <div class="scholar-modal__dialog">
        <div class="scholar-panel__header">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="scholar-kicker">Task Result</div>
              <h3 class="scholar-subtitle">降AIGC率结果详情</h3>
              <p class="scholar-lead">{{ taskResultSummary(selectedTask) }}</p>
            </div>
            <button class="scholar-button scholar-button--secondary" type="button" @click="selectedTask = null">
              关闭
            </button>
          </div>
        </div>
        <div class="scholar-panel__body">
          <div class="scholar-grid scholar-grid--stats">
            <article v-for="metric in taskResultMetrics(selectedTask)" :key="metric.label" class="scholar-stat">
              <div class="scholar-stat__label">{{ metric.label }}</div>
              <div class="scholar-stat__value" style="font-size: 24px">{{ metric.value }}</div>
            </article>
          </div>
          <div class="scholar-inline-actions" style="margin-top: 18px">
            <button class="scholar-button" type="button" @click="downloadResult(selectedTask.id)">下载改写文档</button>
            <button class="scholar-button scholar-button--secondary" type="button" @click="selectedTask = null">
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
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { downloadAxiosBlobResponse } from "../../lib/download"
import { userHttp } from "../../lib/http"
import { getUserToken } from "../../lib/session"
import { taskResultMetrics, taskResultSummary } from "../../lib/taskResult"

const router = useRouter()
const route = useRoute()
const showBuy = ref(false)
const loading = ref(false)
const removingId = ref(null)
const keyword = ref("")
const statusFilter = ref("all")
const page = ref(1)
const pageSize = 8
const selectedTask = ref(null)
const tasks = ref([])
const pollTimer = ref(null)

const { user, refreshUser } = useUserProfile()
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  return typeof value === "number" ? value : null
})
const focusTaskId = computed(() => {
  const raw = Number(route.query.focus)
  return Number.isFinite(raw) && raw > 0 ? raw : null
})

const counts = computed(() => {
  const all = tasks.value.length
  const processing = tasks.value.filter((item) => item.status === "pending" || item.status === "running").length
  const completed = tasks.value.filter((item) => item.status === "completed").length
  return { all, processing, completed }
})

const statusTabs = computed(() => [
  { key: "all", label: "全部", count: counts.value.all },
  { key: "processing", label: "处理中", count: counts.value.processing },
  { key: "completed", label: "已完成", count: counts.value.completed },
])

const filteredTasks = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return tasks.value.filter((item) => {
    if (statusFilter.value === "processing" && item.status !== "pending" && item.status !== "running") {
      return false
    }
    if (statusFilter.value === "completed" && item.status !== "completed") {
      return false
    }
    if (!text) {
      return true
    }
    const searchText = `${item.id} ${item.source_filename || ""}`.toLowerCase()
    return searchText.includes(text)
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredTasks.value.length / pageSize)))
const pagedTasks = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredTasks.value.slice(start, start + pageSize)
})
const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, page.value - 2)
  const end = Math.min(totalPages.value, page.value + 2)
  for (let i = start; i <= end; i += 1) {
    pages.push(i)
  }
  return pages
})

watch([keyword, statusFilter], () => {
  page.value = 1
})

watch(
  [filteredTasks, focusTaskId],
  () => {
    if (!focusTaskId.value) {
      return
    }
    const index = filteredTasks.value.findIndex((item) => item.id === focusTaskId.value)
    if (index >= 0) {
      page.value = Math.floor(index / pageSize) + 1
    }
  },
  { immediate: true }
)

watch(totalPages, (value) => {
  if (page.value > value) {
    page.value = value
  }
})

onMounted(async () => {
  const jobs = [loadTasks()]
  if (getUserToken()) {
    jobs.push(refreshUser())
  }
  await Promise.all(jobs)
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

async function loadTasks() {
  if (!getUserToken()) {
    tasks.value = []
    return
  }
  loading.value = true
  try {
    const data = await userHttp.get("/tasks/my", {
      params: { page: 1, page_size: 100, task_type: "rewrite" },
    })
    tasks.value = (data.items || []).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  if (!getUserToken()) {
    return
  }
  pollTimer.value = window.setInterval(() => {
    if (tasks.value.some((item) => item.status === "pending" || item.status === "running")) {
      loadTasks()
    }
  }, 15000)
}

function stopPolling() {
  if (pollTimer.value) {
    window.clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

function safeText(value) {
  if (typeof value === "string" && value.trim()) {
    return value.trim()
  }
  return "-"
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function reportDeadline(value) {
  if (!value) {
    return "-"
  }
  const time = new Date(value)
  if (Number.isNaN(time.getTime())) {
    return "-"
  }
  time.setDate(time.getDate() + 30)
  const iso = time.toISOString()
  return iso.slice(0, 19).replace("T", " ")
}

function changeRate(item) {
  const raw = Number(item.result_json?.change_ratio)
  if (!Number.isFinite(raw)) {
    return "--"
  }
  return `${Math.round(raw)}%`
}

function goUpload() {
  router.push("/app/rewrite")
}

async function removeTask(item) {
  if (item.status === "running") {
    return
  }
  const ok = window.confirm(`确认删除任务 #${item.id} 吗？`)
  if (!ok) {
    return
  }
  removingId.value = item.id
  try {
    await userHttp.delete(`/tasks/${item.id}`)
    tasks.value = tasks.value.filter((row) => row.id !== item.id)
  } finally {
    removingId.value = null
  }
}

async function downloadResult(taskId) {
  const resp = await userHttp.get(`/tasks/${taskId}/download`, { responseType: "blob" })
  downloadAxiosBlobResponse(resp, `rewrite_result_${taskId}`)
}

async function openDetails(item) {
  if (item.status !== "completed") {
    selectedTask.value = item
    return
  }
  try {
    const detail = await userHttp.get(`/tasks/${item.id}`)
    selectedTask.value = { ...item, ...detail }
  } catch {
    selectedTask.value = item
  }
}

async function afterPaid() {
  await refreshUser()
}
</script>
