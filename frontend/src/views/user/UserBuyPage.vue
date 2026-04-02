<template>
  <UserShell title="购买积分" subtitle="前台套餐与后台计费规则实时同步，游客也可先浏览支付方案。" :credits="userCredits" @buy="noop">
    <section class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <div class="scholar-kicker">Purchase Notes</div>
        <h3 class="scholar-subtitle">购买前说明</h3>
        <p class="scholar-lead">
          游客可以先查看套餐与计费口径，真正创建支付订单时系统会要求登录。支付成功后积分会自动到账，并同步刷新到前台余额。
        </p>
      </div>
    </section>

    <BuyCreditsPanel @paid="afterPaid" />

    <section class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <div class="scholar-kicker">Billing Rules</div>
        <h3 class="scholar-subtitle">当前计费规则</h3>
        <div class="scholar-grid md:grid-cols-3" style="margin-top: 18px">
          <div class="scholar-stat">
            <div class="scholar-stat__label">AIGC 检测</div>
            <div class="scholar-stat__value" style="font-size: 26px">{{ rates.aigc_rate }}</div>
            <div class="scholar-stat__hint">积分 / 字符</div>
          </div>
          <div class="scholar-stat">
            <div class="scholar-stat__label">降重复率</div>
            <div class="scholar-stat__value" style="font-size: 26px">{{ rates.dedup_rate }}</div>
            <div class="scholar-stat__hint">积分 / 字符</div>
          </div>
          <div class="scholar-stat">
            <div class="scholar-stat__label">降 AIGC 率</div>
            <div class="scholar-stat__value" style="font-size: 26px">{{ rates.rewrite_rate }}</div>
            <div class="scholar-stat__hint">积分 / 字符</div>
          </div>
        </div>
        <p class="scholar-note" style="margin-top: 18px">
          任务失败会自动退回对应积分，实际扣费以任务最终解析出的字符数为准。
        </p>
      </div>
    </section>
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
