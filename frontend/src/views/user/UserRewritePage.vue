<template>
  <UserShell title="降AIGC率" subtitle="在尽量保留论点与结构的前提下，降低表达中的 AI 痕迹。" :credits="userCredits" @buy="showBuy = !showBuy">
    <TaskSubmitPanel
      title="新建降AIGC率任务"
      hint="降 AIGC 率任务采用四步流程：选平台、上传正文、可选上传检测报告、提交确认。"
      action-text="开始优化"
      task-type="rewrite"
      :cost-rate="rewriteRate"
      :need-report="true"
      report-label="AIGC 检测报告（可选）"
      paper-hint="为了尽量保留论文结构与排版，降 AIGC 率任务当前仅接收 .docx 原文。"
      report-hint="支持上传 .docx / .pdf AIGC 报告。后端会校验是否为全量检测报告。"
      report-help="不上传报告时按全文处理；上传报告时优先处理高 AI 风险段落。"
      :paper-accept="['.docx']"
      :report-accept="['.docx', '.pdf']"
      :credits="userCredits"
      @submitted="afterTaskSubmit"
      @go-history="goHistory"
    />

    <TaskRecentList
      title="近期降AIGC率记录"
      description="查看最近提交的任务，确认结果是否生成、是否需要二次人工修订。"
      :tasks="recentTasks"
      :guest="isGuest"
      empty-text="提交降 AIGC 率任务后，这里会展示最近 5 条记录。"
      @history="goHistory"
      @login="goLogin"
    />

    <BuyCreditsPanel v-if="showBuy" @paid="afterPaid" />
  </UserShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import TaskRecentList from "../../components/TaskRecentList.vue"
import TaskSubmitPanel from "../../components/TaskSubmitPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { userHttp } from "../../lib/http"
import { getUserToken } from "../../lib/session"

const router = useRouter()
const route = useRoute()
const showBuy = ref(false)
const rates = ref({ aigc_rate: 1, dedup_rate: 2, rewrite_rate: 2 })
const recentTasks = ref([])
const { user, refreshUser } = useUserProfile()
const rewriteRate = computed(() => Number(rates.value.rewrite_rate) || 2)
const isGuest = computed(() => !getUserToken())
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  if (typeof value === "number") {
    return value
  }
  return null
})

onMounted(async () => {
  const jobs = [loadRates()]
  if (getUserToken()) {
    jobs.push(refreshUser(), loadRecentTasks())
  }
  await Promise.all(jobs)
})

function goHistory() {
  router.push("/app/profile?tab=history")
}

async function afterTaskSubmit() {
  await Promise.all([refreshUser(), loadRecentTasks()])
}

async function afterPaid() {
  await refreshUser()
}

async function loadRates() {
  try {
    const data = await userHttp.get("/tasks/rates")
    rates.value = data || rates.value
  } catch {
    // fallback to defaults
  }
}

async function loadRecentTasks() {
  if (!getUserToken()) {
    recentTasks.value = []
    return
  }
  const data = await userHttp.get("/tasks/my", {
    params: { page: 1, page_size: 5, task_type: "rewrite" },
  })
  recentTasks.value = data.items || []
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/rewrite")
  router.push(`/login?redirect=${redirect}`)
}
</script>
