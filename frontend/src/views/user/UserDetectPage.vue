<template>
  <UserShell title="AIGC 检测" subtitle="按目标平台提交正文，快速判断 AI 风险分布与高风险段落。" :credits="userCredits" @buy="showBuy = !showBuy">
    <TaskSubmitPanel
      title="新建 AIGC 检测任务"
      hint="先选择目标平台，再上传正文。游客可以先浏览页面，点击提交时再登录。"
      action-text="开始检测"
      task-type="aigc_detect"
      :cost-rate="detectRate"
      paper-hint="支持 .docx / .pdf / .txt。纯文本文件会在浏览器内直接估算字符数，Word 和 PDF 以后端解析为准。"
      :paper-accept="['.docx', '.pdf', '.txt']"
      :credits="userCredits"
      @submitted="afterTaskSubmit"
      @go-history="goHistory"
    />

    <TaskRecentList
      title="近期检测记录"
      description="优先展示最近提交的 AIGC 检测任务，便于快速回看状态和风险摘要。"
      :tasks="recentTasks"
      :guest="isGuest"
      empty-text="登录并提交检测任务后，这里会显示最近 5 条记录。"
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
const detectRate = computed(() => Number(rates.value.aigc_rate) || 1)
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
  router.push("/app/history")
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
    params: { page: 1, page_size: 5, task_type: "aigc_detect" },
  })
  recentTasks.value = data.items || []
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/detect")
  router.push(`/login?redirect=${redirect}`)
}
</script>
