<template>
  <UserShell title="降重复率" subtitle="上传正文与查重报告，优先处理高重复区域并保留文档结构。" :credits="userCredits" @buy="showBuy = !showBuy">
    <TaskSubmitPanel
      title="新建降重复率任务"
      hint="正文目前仅支持 Word 文档。上传全量查重报告后，系统会优先针对高重复段落处理。"
      action-text="开始降重"
      task-type="dedup"
      :cost-rate="dedupRate"
      :need-report="true"
      report-label="查重报告（可选）"
      paper-hint="为了尽量保留论文排版与样式，降重任务当前仅接收 .docx 原文。"
      report-hint="支持上传 .docx / .pdf 查重报告。后端会校验是否为全量报告结构。"
      report-help="不上传报告时按全文降重；上传全量报告时按命中段落优先处理。"
      :paper-accept="['.docx']"
      :report-accept="['.docx', '.pdf']"
      :credits="userCredits"
      @submitted="afterTaskSubmit"
      @go-history="goHistory"
    />

    <TaskRecentList
      title="近期降重记录"
      description="查看最近提交的降重任务，快速确认是否完成、失败或仍在排队。"
      :tasks="recentTasks"
      :guest="isGuest"
      empty-text="登录并提交降重任务后，这里会显示最近 5 条记录。"
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
const dedupRate = computed(() => Number(rates.value.dedup_rate) || 2)
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
    params: { page: 1, page_size: 5, task_type: "dedup" },
  })
  recentTasks.value = data.items || []
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/dedup")
  router.push(`/login?redirect=${redirect}`)
}
</script>
