<template>
  <UserShell title="降AIGC率" subtitle="在保留论点前提下降低AIGC风险表达" :credits="userCredits" @buy="showBuy = !showBuy">
    <div class="space-y-4">
      <TaskSubmitPanel
        title="新建降AIGC率任务"
        hint="主文件仅支持 Word 文档。可选上传全文 AIGC 检测报告，用于优先降低高风险段落的AIGC表达。"
        action-text="开始降AIGC率"
        task-type="rewrite"
        :cost-rate="rewriteRate"
        :need-report="true"
        report-label="AIGC检测报告（可选）"
        paper-hint="降AIGC率任务会尽量保留论文结构与版式，因此原文仅接受 .docx。"
        report-hint="支持上传 .docx / .pdf AIGC 报告。后端会校验是否为全文检测报告。"
        report-help="不上传报告时按全文处理；上传全文报告时优先处理高 AI 风险段落。"
        :paper-accept="['.docx']"
        :report-accept="['.docx', '.pdf']"
        :credits="userCredits"
        @submitted="afterTaskSubmit"
        @go-history="goHistory"
      />
      <TaskRecentList
        title="近期降AIGC率记录"
        description="查看最近提交的降AIGC率任务，确认结果是否已生成。"
        :tasks="recentTasks"
        :guest="isGuest"
        empty-text="登录并提交降AIGC率任务后，这里会显示最近 5 条记录。"
        @history="goHistory"
        @login="goLogin"
      />
      <BuyCreditsPanel v-if="showBuy" @paid="afterPaid" />
    </div>
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
    params: { page: 1, page_size: 5, task_type: "rewrite" },
  })
  recentTasks.value = data.items || []
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/rewrite")
  router.push(`/login?redirect=${redirect}`)
}
</script>
