<template>
  <UserShell
    title="个人中心"
    subtitle="统一管理账户信息、任务记录与积分流水。"
    :credits="userCredits"
    @buy="goBuy"
  >
    <section v-if="isGuest" class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <h3 class="scholar-subtitle">登录后查看个人数据</h3>
        <p class="scholar-lead">
          个人中心会统一归档任务记录、积分流水和账户信息。浏览流程不受影响，提交任务或查看个人数据时再登录即可。
        </p>
        <button class="scholar-button" type="button" style="margin-top: 18px" @click="goLogin">
          登录后进入个人中心
        </button>
      </div>
    </section>

    <template v-else>
      <section class="scholar-panel scholar-panel--soft">
        <div class="scholar-panel__body">
          <div class="scholar-inline-actions">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              type="button"
              class="scholar-chip"
              :class="{ 'is-active': activeTab === tab.key }"
              @click="switchTab(tab.key)"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'overview'" class="scholar-grid scholar-grid--halves">
        <article class="scholar-panel scholar-panel--soft">
          <div class="scholar-panel__body">
            <div class="scholar-kicker">Account</div>
            <h3 class="scholar-subtitle">账户信息</h3>
            <div class="scholar-stack" style="margin-top: 18px">
              <div class="scholar-note">手机号：{{ user.value?.phone || "-" }}</div>
              <div class="scholar-note">注册时间：{{ formatTime(user.value?.created_at) }}</div>
              <label class="scholar-field">
                <span class="scholar-field__label">昵称</span>
                <div class="scholar-inline-actions">
                  <input v-model.trim="nickname" class="scholar-input" style="flex: 1" />
                  <button class="scholar-button" type="button" @click="saveNickname">保存昵称</button>
                </div>
              </label>
            </div>
          </div>
        </article>

        <article class="scholar-panel scholar-panel--soft">
          <div class="scholar-panel__body">
            <div class="scholar-kicker">Credits Overview</div>
            <h3 class="scholar-subtitle">积分概览</h3>
            <div class="scholar-grid md:grid-cols-3" style="margin-top: 18px">
              <div class="scholar-stat">
                <div class="scholar-stat__label">当前余额</div>
                <div class="scholar-stat__value" style="font-size: 26px">
                  {{ typeof userCredits === "number" ? userCredits : 0 }} 积分
                </div>
              </div>
              <div class="scholar-stat">
                <div class="scholar-stat__label">累计入账</div>
                <div class="scholar-stat__value" style="font-size: 26px">{{ summary.income }} 积分</div>
              </div>
              <div class="scholar-stat">
                <div class="scholar-stat__label">累计支出</div>
                <div class="scholar-stat__value" style="font-size: 26px">{{ summary.outcome }} 积分</div>
              </div>
            </div>
            <div class="scholar-inline-actions" style="margin-top: 18px">
              <button class="scholar-button" type="button" @click="goBuy">去充值</button>
              <button class="scholar-button scholar-button--secondary" type="button" @click="switchTab('history')">
                查看任务记录
              </button>
              <button class="scholar-button scholar-button--secondary" type="button" @click="switchTab('credits')">
                查看积分流水
              </button>
            </div>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'history'" class="scholar-panel">
        <div class="scholar-panel__header">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="scholar-kicker">Task History</div>
              <h3 class="scholar-subtitle">任务记录</h3>
            </div>
            <button class="scholar-button scholar-button--secondary" type="button" @click="loadTasks">
              刷新
            </button>
          </div>
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
                  <td>{{ item.char_count || 0 }}</td>
                  <td>{{ item.cost_credits || 0 }} 积分</td>
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
        </div>
      </section>

      <section v-else class="scholar-panel">
        <div class="scholar-panel__header">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="scholar-kicker">Credit Transactions</div>
              <h3 class="scholar-subtitle">积分流水</h3>
            </div>
            <button class="scholar-button scholar-button--secondary" type="button" @click="loadTransactions">
              刷新
            </button>
          </div>
        </div>

        <div class="scholar-panel__body">
          <div class="overflow-x-auto">
            <table class="scholar-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>类型</th>
                  <th>变化</th>
                  <th>前余额</th>
                  <th>后余额</th>
                  <th>备注</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in txRows" :key="row.id">
                  <td>{{ formatTime(row.created_at) }}</td>
                  <td>{{ mapCreditType(row.tx_type) }}</td>
                  <td :style="{ color: row.delta >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }">
                    {{ row.delta }} 积分
                  </td>
                  <td>{{ row.balance_before }} 积分</td>
                  <td>{{ row.balance_after }} 积分</td>
                  <td>{{ row.reason || "-" }}</td>
                </tr>
                <tr v-if="txRows.length === 0">
                  <td colspan="6">
                    <div class="scholar-empty">暂无流水</div>
                  </td>
                </tr>
              </tbody>
            </table>
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
    </template>
  </UserShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

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

const router = useRouter()
const route = useRoute()
const { user, refreshUser } = useUserProfile()

const tabs = [
  { key: "overview", label: "账户信息" },
  { key: "history", label: "任务记录" },
  { key: "credits", label: "积分流水" },
]

const nickname = ref("")
const txRows = ref([])
const tasks = ref([])
const selectedTask = ref(null)
const summary = reactive({ income: 0, outcome: 0 })
const activeTab = ref("overview")
const isGuest = computed(() => !getUserToken())

const userCredits = computed(() => {
  const value = user.value && user.value.credits
  return typeof value === "number" ? value : null
})

watch(
  () => route.query.tab,
  (value) => {
    activeTab.value = normalizeTab(value)
  }
)

onMounted(async () => {
  activeTab.value = normalizeTab(route.query.tab)
  if (getUserToken()) {
    await refreshUser()
    await Promise.all([loadTransactions(), loadTasks()])
  }
  nickname.value = user.value?.nickname || ""
})

function normalizeTab(tab) {
  if (tab === "history" || tab === "credits") {
    return tab
  }
  return "overview"
}

function switchTab(tab) {
  activeTab.value = normalizeTab(tab)
  if (activeTab.value === "overview") {
    router.replace({ path: "/app/profile", query: {} })
    return
  }
  router.replace({ path: "/app/profile", query: { tab: activeTab.value } })
}

async function loadTransactions() {
  if (!getUserToken()) {
    txRows.value = []
    summary.income = 0
    summary.outcome = 0
    return
  }
  const data = await userHttp.get("/users/me/credit-transactions", { params: { page: 1, page_size: 100 } })
  txRows.value = data.items || []
  let income = 0
  let outcome = 0
  for (const row of txRows.value) {
    if (row.delta >= 0) income += row.delta
    else outcome += Math.abs(row.delta)
  }
  summary.income = income
  summary.outcome = outcome
}

async function loadTasks() {
  if (!getUserToken()) {
    tasks.value = []
    return
  }
  const data = await userHttp.get("/tasks/my", { params: { page: 1, page_size: 20 } })
  tasks.value = data.items || []
}

async function saveNickname() {
  if (!ensureUserLogin(router, { fullPath: "/app/profile" }, "/app/profile")) {
    return
  }
  if (!nickname.value) return
  await userHttp.patch("/users/me", { nickname: nickname.value })
  await refreshUser()
}

async function download(taskId) {
  if (!ensureUserLogin(router, route, "/app/profile?tab=history")) {
    return
  }
  const resp = await userHttp.get(`/tasks/${taskId}/download`, { responseType: "blob" })
  downloadAxiosBlobResponse(resp, `task_${taskId}_result`)
}

function openResult(item) {
  selectedTask.value = item
}

function closeResult() {
  selectedTask.value = null
}

function mapCreditType(type) {
  const map = {
    init: "初始积分",
    task_consume: "任务消费",
    task_refund: "任务退款",
    package_pay: "积分充值",
    referral_invite: "邀请奖励",
    referral_bonus: "被邀请福利",
    referral_first_pay: "首充返佣",
    referral_recurring: "持续返利",
    admin_adjust: "管理员调整",
  }
  return map[type] || type
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
    cnki: "格物学术标准版",
    vip: "格物学术专业版",
    paperpass: "格物学术极速版",
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

function goBuy() {
  router.push("/app/buy")
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/profile")
  router.push(`/login?redirect=${redirect}`)
}
</script>
