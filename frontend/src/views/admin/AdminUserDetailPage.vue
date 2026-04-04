<template>
  <AdminShell title="用户详情" subtitle="围绕账户、积分和最近任务做运营处理">
    <div class="space-y-4">
      <section class="overflow-hidden rounded-[28px] border border-[#d9dee4] bg-white">
        <div class="border-b border-[#e4eaf0] bg-[linear-gradient(135deg,#f6f4ed,#eef4f8)] px-6 py-5">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div class="text-[11px] uppercase tracking-[0.18em] text-[#72808c]">Operator Desk</div>
              <h2 class="mt-2 text-2xl font-semibold text-[#14212a]">
                {{ detail.user?.nickname || detail.user?.phone || `用户 #${detail.user?.id || "-"}` }}
              </h2>
              <div class="mt-3 flex flex-wrap items-center gap-2 text-sm text-[#5d6973]">
                <span class="rounded-full bg-white/80 px-3 py-1">用户ID {{ detail.user?.id || "-" }}</span>
                <span class="rounded-full bg-white/80 px-3 py-1">{{ detail.user?.phone || "-" }}</span>
                <span :class="detail.user?.is_banned ? 'bg-[#ffe8e3] text-[#a43e34]' : 'bg-[#eaf5ef] text-[#0f6d53]'" class="rounded-full px-3 py-1">
                  {{ detail.user?.is_banned ? "已封禁" : "状态正常" }}
                </span>
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="rounded-xl bg-white px-4 py-2 text-sm text-[#344250]" @click="loadDetail">刷新数据</button>
              <button class="rounded-xl bg-white px-4 py-2 text-sm text-[#344250]" @click="goBack">返回列表</button>
              <button
                class="rounded-xl px-4 py-2 text-sm text-white"
                :class="detail.user?.is_banned ? 'bg-[#0f7a5f]' : 'bg-[#a74233]'"
                @click="toggleBan"
              >
                {{ detail.user?.is_banned ? "解除封禁" : "封禁账号" }}
              </button>
            </div>
          </div>
        </div>

        <div class="grid gap-5 px-6 py-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div class="space-y-5">
            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <article class="rounded-2xl border border-[#dde5eb] bg-[#fbfcfd] p-4">
                <div class="text-xs tracking-[0.1em] text-[#6c7985]">当前积分</div>
                <div class="mt-2 text-2xl font-semibold text-[#17222b]">{{ numberText(detail.user?.credits) }}</div>
              </article>
              <article class="rounded-2xl border border-[#dde5eb] bg-[#fbfcfd] p-4">
                <div class="text-xs tracking-[0.1em] text-[#6c7985]">累计充值金额</div>
                <div class="mt-2 text-2xl font-semibold text-[#17222b]">¥{{ numberText(detail.summary?.total_paid_cny) }}</div>
              </article>
              <article class="rounded-2xl border border-[#dde5eb] bg-[#fbfcfd] p-4">
                <div class="text-xs tracking-[0.1em] text-[#6c7985]">累计充值积分</div>
                <div class="mt-2 text-2xl font-semibold text-[#17222b]">{{ numberText(detail.summary?.total_paid_credits) }}</div>
              </article>
              <article class="rounded-2xl border border-[#dde5eb] bg-[#fbfcfd] p-4">
                <div class="text-xs tracking-[0.1em] text-[#6c7985]">累计任务消耗</div>
                <div class="mt-2 text-2xl font-semibold text-[#17222b]">{{ numberText(detail.summary?.total_task_cost_credits) }}</div>
              </article>
            </div>

            <div class="grid gap-3 md:grid-cols-2">
              <div class="rounded-2xl border border-[#dde5eb] bg-[#fbfcfd] p-4">
                <div class="text-xs tracking-[0.1em] text-[#6c7985]">账户信息</div>
                <div class="mt-3 space-y-2 text-sm text-[#41505c]">
                  <div>昵称：{{ detail.user?.nickname || "-" }}</div>
                  <div>手机号：{{ detail.user?.phone || "-" }}</div>
                  <div>注册时间：{{ formatTime(detail.user?.created_at) }}</div>
                </div>
              </div>
              <div class="rounded-2xl border border-[#dde5eb] bg-[#fbfcfd] p-4">
                <div class="text-xs tracking-[0.1em] text-[#6c7985]">最近任务概况</div>
                <div class="mt-3 grid gap-2 text-sm text-[#41505c] sm:grid-cols-3">
                  <div class="rounded-xl bg-white px-3 py-3">
                    <div class="text-xs text-[#6c7985]">近 20 条</div>
                    <div class="mt-1 text-lg font-semibold text-[#17222b]">{{ recentTaskCount }}</div>
                  </div>
                  <div class="rounded-xl bg-white px-3 py-3">
                    <div class="text-xs text-[#6c7985]">已完成</div>
                    <div class="mt-1 text-lg font-semibold text-[#0f6d53]">{{ completedTaskCount }}</div>
                  </div>
                  <div class="rounded-xl bg-white px-3 py-3">
                    <div class="text-xs text-[#6c7985]">处理中</div>
                    <div class="mt-1 text-lg font-semibold text-[#9d6a12]">{{ activeTaskCount }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-[24px] border border-[#dde5eb] bg-[#fbfcfd] p-5">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-xs tracking-[0.1em] text-[#6c7985]">积分调整</div>
                <h3 class="mt-1 text-base font-semibold text-[#17222b]">直接做运营补偿或扣减</h3>
              </div>
              <span class="rounded-full bg-white px-3 py-1 text-xs text-[#5c6872]">实时生效</span>
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
              <button
                v-for="item in presetAdjustments"
                :key="item.value"
                class="rounded-full border border-[#cfd8df] bg-white px-3 py-1.5 text-xs text-[#40505c] transition hover:border-[#8ca597]"
                @click="pickDelta(item)"
              >
                {{ item.label }}
              </button>
            </div>
            <div class="mt-4 grid gap-3">
              <input
                v-model.number="delta"
                class="rounded-xl border border-[#ccd5dd] bg-white px-4 py-3 text-sm outline-none"
                placeholder="输入正负积分，例如 200 或 -200"
              />
              <input
                v-model.trim="reason"
                class="rounded-xl border border-[#ccd5dd] bg-white px-4 py-3 text-sm outline-none"
                placeholder="请输入运营备注，例如 首次投诉补偿 / 违规扣减"
              />
              <button class="rounded-xl bg-[#0f7a5f] px-4 py-3 text-sm text-white" @click="adjustCredits">确认调整</button>
            </div>
            <div class="mt-4 rounded-2xl border border-[#e2e8ee] bg-white px-4 py-3 text-xs leading-6 text-[#61707c]">
              建议写清来源与原因，方便后续对账和审计追踪。
            </div>
            <p v-if="hintText" class="mt-3 text-sm text-[#106c4f]">{{ hintText }}</p>
            <p v-if="errorText" class="mt-3 text-sm text-[#af3f33]">{{ errorText }}</p>
          </div>
        </div>
      </section>

      <section class="rounded-[28px] border border-[#d9dee4] bg-white p-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">Credit Timeline</div>
            <h3 class="mt-2 text-lg font-semibold text-[#17222b]">近期积分流水</h3>
          </div>
          <span class="rounded-full bg-[#eef3f7] px-3 py-1 text-xs text-[#5d6973]">最近 20 条</span>
        </div>
        <div class="mt-4 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
                <th class="px-2 py-2">时间</th>
                <th class="px-2 py-2">类型</th>
                <th class="px-2 py-2">变动</th>
                <th class="px-2 py-2">变动前</th>
                <th class="px-2 py-2">变动后</th>
                <th class="px-2 py-2">原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tx in detail.credit_transactions || []" :key="tx.id" class="border-b border-[#eef2f5]">
                <td class="px-2 py-3">{{ formatTime(tx.created_at) }}</td>
                <td class="px-2 py-3">
                  <span class="rounded-full bg-[#f2f6f9] px-2 py-1 text-xs text-[#44525d]">{{ mapTxType(tx.tx_type) }}</span>
                </td>
                <td class="px-2 py-3">
                  <span :class="Number(tx.delta) >= 0 ? 'text-[#106c4f]' : 'text-[#b14133]'">
                    {{ Number(tx.delta) >= 0 ? `+${tx.delta}` : tx.delta }}
                  </span>
                </td>
                <td class="px-2 py-3">{{ tx.balance_before }}</td>
                <td class="px-2 py-3">{{ tx.balance_after }}</td>
                <td class="px-2 py-3 text-[#4f5d69]">{{ tx.reason || "-" }}</td>
              </tr>
              <tr v-if="!detail.credit_transactions?.length">
                <td class="px-2 py-4 text-[#6a7781]" colspan="6">暂无积分流水</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-[28px] border border-[#d9dee4] bg-white p-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">Task Review</div>
            <h3 class="mt-2 text-lg font-semibold text-[#17222b]">近期任务与结果摘要</h3>
            <p class="mt-1 text-sm text-[#5d6973]">左侧挑选任务，右侧直接查看摘要、风险段落和结果预览。</p>
          </div>
          <button class="rounded-xl bg-[#edf2f6] px-4 py-2 text-sm text-[#344250]" @click="openTaskList">
            打开任务管理页
          </button>
        </div>

        <div class="mt-5 grid gap-5 xl:grid-cols-[0.98fr_1.02fr]">
          <div class="space-y-3">
            <button
              v-for="task in detail.tasks || []"
              :key="task.id"
              type="button"
              class="w-full rounded-[24px] border p-4 text-left transition"
              :class="selectedTask?.id === task.id ? 'border-[#0f7a5f] bg-[linear-gradient(160deg,#edf7f3,#ffffff)] shadow-[0_12px_24px_rgba(15,122,95,0.1)]' : 'border-[#e1e7ec] bg-[#fbfcfd] hover:border-[#a9bbc7]'"
              @click="selectTask(task)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-semibold text-[#16212b]">{{ mapTaskType(task.task_type) }}</span>
                    <span :class="statusClass(task.status)" class="inline-flex rounded-full border px-2 py-1 text-[11px]">
                      {{ mapStatus(task.status) }}
                    </span>
                  </div>
                  <div class="mt-2 flex flex-wrap gap-2 text-xs text-[#62707b]">
                    <span class="rounded-full bg-white px-2 py-1">{{ mapPlatform(task.platform) }}</span>
                    <span class="rounded-full bg-white px-2 py-1">{{ task.char_count || 0 }} 字符</span>
                    <span class="rounded-full bg-white px-2 py-1">{{ task.cost_credits || 0 }} 积分</span>
                    <span class="rounded-full bg-white px-2 py-1">{{ formatTime(task.created_at) }}</span>
                  </div>
                  <div class="mt-3 text-sm leading-6 text-[#485661]">
                    {{ resultSummary(task) }}
                  </div>
                </div>
                <div class="flex flex-col gap-2">
                  <button class="rounded-lg bg-white px-3 py-1.5 text-xs text-[#344250]" @click.stop="selectTask(task)">结果摘要</button>
                  <button class="rounded-lg bg-[#0f7a5f] px-3 py-1.5 text-xs text-white" @click.stop="openTaskDetail(task.id)">
                    任务详情
                  </button>
                </div>
              </div>
            </button>

            <div v-if="!detail.tasks?.length" class="rounded-[24px] border border-dashed border-[#d6dfe6] bg-[#fafcfd] px-5 py-8 text-sm text-[#61707b]">
              暂无近期任务记录
            </div>
          </div>

          <div class="rounded-[24px] border border-[#dde5eb] bg-[#fbfcfd] p-5">
            <template v-if="selectedTask">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">Selected Task</div>
                  <h4 class="mt-2 text-lg font-semibold text-[#17222b]">任务 #{{ selectedTask.id }}</h4>
                  <p class="mt-2 text-sm leading-6 text-[#4f5d68]">{{ resultSummary(selectedTask) }}</p>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button class="rounded-lg bg-white px-3 py-2 text-sm text-[#344250]" @click="openTaskDetail(selectedTask.id)">
                    打开详情页
                  </button>
                  <button
                    class="rounded-lg bg-[#0f7a5f] px-3 py-2 text-sm text-white disabled:opacity-50"
                    :disabled="selectedTask.status !== 'completed'"
                    @click="downloadResult(selectedTask.id)"
                  >
                    下载结果
                  </button>
                </div>
              </div>

              <div class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <article v-for="metric in resultMetrics(selectedTask)" :key="metric.label" class="rounded-2xl border border-[#dce3e9] bg-white p-4">
                  <div class="text-xs tracking-[0.1em] text-[#6d7a86]">{{ metric.label }}</div>
                  <div class="mt-2 text-lg font-semibold text-[#16222a]">{{ metric.value }}</div>
                </article>
              </div>

              <div class="mt-4 grid gap-2 text-sm text-[#41505c] sm:grid-cols-2">
                <div class="rounded-xl border border-[#e1e7ec] bg-white px-3 py-2">平台：{{ mapPlatform(selectedTask.platform) }}</div>
                <div class="rounded-xl border border-[#e1e7ec] bg-white px-3 py-2">更新时间：{{ formatTime(selectedTask.updated_at) }}</div>
                <div class="rounded-xl border border-[#e1e7ec] bg-white px-3 py-2 sm:col-span-2">
                  主文件：{{ selectedTask.source_filename || "-" }}
                </div>
                <div class="rounded-xl border border-[#e1e7ec] bg-white px-3 py-2 sm:col-span-2">
                  辅助报告：{{ selectedTask.report_path || "-" }}
                </div>
                <div class="rounded-xl border border-[#e1e7ec] bg-white px-3 py-2 sm:col-span-2">
                  结果文件：{{ selectedTask.output_path || "-" }}
                </div>
              </div>

              <section v-if="selectedTask.error_message" class="mt-4 rounded-2xl border border-[#f1cfc8] bg-[#fff4f1] p-4">
                <h5 class="text-sm font-semibold text-[#9c3a31]">失败原因</h5>
                <div class="mt-2 text-sm leading-6 text-[#9c3a31]">{{ selectedTask.error_message }}</div>
              </section>

              <section v-if="resultReportMetrics(selectedTask).length" class="mt-4 rounded-2xl border border-[#dce3e9] bg-white p-4">
                <h5 class="text-sm font-semibold text-[#1c2831]">辅助报告指标</h5>
                <div class="mt-3 grid gap-3 md:grid-cols-2">
                  <div v-for="metric in resultReportMetrics(selectedTask)" :key="metric.label" class="rounded-xl border border-[#e4eaf0] bg-[#fbfcfd] px-3 py-2 text-sm text-[#44525d]">
                    {{ metric.label }}：{{ metric.value }}{{ metric.unit || "" }}
                  </div>
                </div>
              </section>

              <section v-if="resultRiskParagraphs(selectedTask).length" class="mt-4 rounded-2xl border border-[#dce3e9] bg-white p-4">
                <h5 class="text-sm font-semibold text-[#1c2831]">高风险段落</h5>
                <div class="mt-3 space-y-3">
                  <div v-for="item in resultRiskParagraphs(selectedTask)" :key="`${item.index}-${item.score}`" class="rounded-xl border border-[#e4eaf0] bg-[#fbfcfd] p-3">
                    <div class="text-xs text-[#6b7884]">段落 {{ item.index }} · 风险 {{ item.score }}%</div>
                    <div class="mt-2 text-sm leading-6 text-[#31404b]">{{ item.excerpt }}</div>
                  </div>
                </div>
              </section>

              <section v-if="resultReviewPoints(selectedTask).length" class="mt-4 rounded-2xl border border-[#dce3e9] bg-white p-4">
                <h5 class="text-sm font-semibold text-[#1c2831]">复核建议</h5>
                <div class="mt-3 space-y-2">
                  <div v-for="point in resultReviewPoints(selectedTask)" :key="point" class="flex items-start gap-2 rounded-xl border border-[#e4eaf0] bg-[#fbfcfd] px-3 py-2">
                    <span class="mt-1 h-1.5 w-1.5 rounded-full bg-[#0f7a5f]"></span>
                    <span class="text-sm leading-6 text-[#3c4b56]">{{ point }}</span>
                  </div>
                </div>
              </section>

              <section v-if="resultOutputPreview(selectedTask)" class="mt-4 rounded-2xl border border-[#dce3e9] bg-white p-4">
                <h5 class="text-sm font-semibold text-[#1c2831]">结果预览</h5>
                <div class="mt-3 whitespace-pre-wrap rounded-xl border border-[#e4eaf0] bg-[#fbfcfd] p-3 text-sm leading-6 text-[#2f3d48]">
                  {{ resultOutputPreview(selectedTask) }}
                </div>
              </section>
            </template>

            <div v-else class="flex min-h-[280px] items-center justify-center rounded-[20px] border border-dashed border-[#d6dfe6] bg-white text-sm text-[#61707b]">
              选择左侧任务后，这里会显示结果摘要与运营处理信息。
            </div>
          </div>
        </div>
      </section>
    </div>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
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

const route = useRoute()
const router = useRouter()
const detail = ref({
  user: null,
  summary: {},
  credit_transactions: [],
  tasks: [],
})
const delta = ref(0)
const reason = ref("")
const hintText = ref("")
const errorText = ref("")
const selectedTaskId = ref(null)

const presetAdjustments = [
  { label: "+200 新客补偿", value: 200, reason: "新客补偿" },
  { label: "+500 投诉补偿", value: 500, reason: "投诉补偿" },
  { label: "-200 违规扣减", value: -200, reason: "违规扣减" },
  { label: "-500 人工回收", value: -500, reason: "人工回收" },
]

const selectedTask = computed(() => {
  const rows = detail.value.tasks || []
  if (!rows.length) {
    return null
  }
  return rows.find((item) => item.id === selectedTaskId.value) || rows[0]
})
const recentTaskCount = computed(() => (detail.value.tasks || []).length)
const completedTaskCount = computed(() => (detail.value.tasks || []).filter((item) => item.status === "completed").length)
const activeTaskCount = computed(() =>
  (detail.value.tasks || []).filter((item) => item.status === "pending" || item.status === "running").length
)

onMounted(loadDetail)

async function loadDetail() {
  const data = await adminHttp.get(`/admin/users/${route.params.id}/detail`)
  detail.value = data
  const currentTasks = data.tasks || []
  if (!currentTasks.some((item) => item.id === selectedTaskId.value)) {
    selectedTaskId.value = currentTasks[0]?.id || null
  }
}

async function adjustCredits() {
  if (!delta.value) {
    errorText.value = "调整值不能为 0"
    hintText.value = ""
    return
  }
  if (!reason.value) {
    errorText.value = "请输入调整原因"
    hintText.value = ""
    return
  }
  errorText.value = ""
  const data = await adminHttp.post(`/admin/users/${route.params.id}/adjust-credits`, {
    delta: delta.value,
    reason: reason.value,
  })
  hintText.value = `调整成功，当前积分 ${data.credits}`
  delta.value = 0
  reason.value = ""
  await loadDetail()
}

async function toggleBan() {
  const user = detail.value.user
  if (!user?.id) {
    return
  }
  const nextBanned = !user.is_banned
  const actionText = nextBanned ? "封禁" : "解除封禁"
  const confirmed = window.confirm(`确认${actionText}用户 ${user.phone || user.id} 吗？`)
  if (!confirmed) {
    return
  }
  errorText.value = ""
  const data = await adminHttp.post(`/admin/users/${user.id}/ban`, { is_banned: nextBanned })
  hintText.value = data.is_banned ? "该账号已封禁" : "该账号已解除封禁"
  await loadDetail()
}

function pickDelta(item) {
  delta.value = item.value
  reason.value = item.reason
  errorText.value = ""
}

function selectTask(task) {
  selectedTaskId.value = task.id
}

function openTaskList() {
  router.push("/admin/tasks")
}

function openTaskDetail(taskId) {
  router.push(`/admin/tasks?task_id=${taskId}`)
}

async function downloadResult(taskId) {
  const resp = await adminHttp.get(`/admin/tasks/${taskId}/download`, { responseType: "blob" })
  downloadAxiosBlobResponse(resp, `admin_task_${taskId}_result`)
}

function numberText(value) {
  if (typeof value !== "number") {
    return "0"
  }
  return Number(value).toLocaleString()
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function mapTxType(type) {
  const map = {
    init: "初始积分",
    task_consume: "任务扣减",
    task_refund: "失败退回",
    package_pay: "充值到账",
    referral_invite: "邀请奖励",
    referral_bonus: "注册福利",
    referral_first_pay: "首充奖励",
    referral_recurring: "持续返利",
    admin_adjust: "人工调整",
  }
  return map[type] || type || "-"
}

function mapTaskType(type) {
  const map = {
    aigc_detect: "AIGC 检测",
    dedup: "降重复率",
    rewrite: "降AIGC率",
  }
  return map[type] || type || "-"
}

function mapPlatform(platform) {
  const map = {
    cnki: "格物学术标准版",
    vip: "格物学术专业版",
    paperpass: "格物学术极速版",
  }
  return map[platform] || platform || "-"
}

function mapStatus(status) {
  const map = {
    pending: "排队中",
    running: "处理中",
    completed: "已完成",
    failed: "失败",
  }
  return map[status] || status || "-"
}

function statusClass(status) {
  if (status === "completed") {
    return "border-[#b8e7d5] bg-[#dbf5ea] text-[#106c4f]"
  }
  if (status === "failed") {
    return "border-[#f4c5c1] bg-[#ffe1df] text-[#9c2d2a]"
  }
  if (status === "running") {
    return "border-[#d7e5f5] bg-[#eef4ff] text-[#235f9f]"
  }
  return "border-[#f2dfb3] bg-[#fff2d8] text-[#8a5a10]"
}

function goBack() {
  router.push("/admin/users")
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
</script>
