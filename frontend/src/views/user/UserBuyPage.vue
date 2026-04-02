<template>
  <UserShell title="购买积分" subtitle="选择套餐并充值" :credits="userCredits" @buy="noop">
    <div class="space-y-4">
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5 text-sm text-[#4e5d68]">
        <div class="font-semibold text-[#1a2730]">游客模式说明</div>
        <div class="mt-2 leading-6">可先查看套餐与计费规则；真正创建支付订单时，系统才会要求登录。</div>
      </section>
      <BuyCreditsPanel @paid="afterPaid" />
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5 text-sm text-[#4e5d68]">
        <div>计费规则：AIGC检测 {{ rates.aigc_rate }} 积分/字符，降重 {{ rates.dedup_rate }} 积分/字符，降AIGC率 {{ rates.rewrite_rate }} 积分/字符。</div>
        <div class="mt-1">退款规则：任务失败自动退回对应积分。</div>
      </section>
    </div>
  </UserShell>
</template>

<script setup>
import { computed, onMounted, reactive } from "vue"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { userHttp } from "../../lib/http"
import { getUserToken } from "../../lib/session"

const { user, refreshUser } = useUserProfile()
const rates = reactive({
  aigc_rate: 1,
  dedup_rate: 2,
  rewrite_rate: 2,
})
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  return typeof value === "number" ? value : null
})

onMounted(async () => {
  const jobs = [loadRates()]
  if (getUserToken()) {
    jobs.push(refreshUser())
  }
  await Promise.all(jobs)
})

async function afterPaid() {
  if (getUserToken()) {
    await refreshUser()
  }
}

function noop() {}

async function loadRates() {
  try {
    const data = await userHttp.get("/tasks/rates")
    rates.aigc_rate = Number(data?.aigc_rate) || rates.aigc_rate
    rates.dedup_rate = Number(data?.dedup_rate) || rates.dedup_rate
    rates.rewrite_rate = Number(data?.rewrite_rate) || rates.rewrite_rate
  } catch {
    // fallback to defaults
  }
}
</script>
