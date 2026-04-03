<template>
  <UserShell title="购买积分" subtitle="前台套餐与后台配置实时同步，可直接选择方案完成充值。" :credits="userCredits" @buy="noop">
    <section class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <div class="scholar-kicker">Purchase Notes</div>
        <h3 class="scholar-subtitle">购买前说明</h3>
        <p class="scholar-lead">
          可以先查看套餐与计费口径，创建支付订单时再登录即可。支付成功后积分会自动到账，并同步刷新前台余额。
        </p>
      </div>
    </section>

    <BuyCreditsPanel @paid="afterPaid" />
  </UserShell>
</template>

<script setup>
import { computed, onMounted } from "vue"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { getUserToken } from "../../lib/session"

const { user, refreshUser } = useUserProfile()
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  return typeof value === "number" ? value : null
})

onMounted(async () => {
  if (!getUserToken()) return
  await refreshUser()
})

async function afterPaid() {
  if (getUserToken()) {
    await refreshUser()
  }
}

function noop() {}
</script>
