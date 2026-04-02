<template>
  <UserShell title="推广福利" subtitle="邀请码、邀请记录与奖励流水" :credits="userCredits" @buy="showBuy = !showBuy">
    <section v-if="isGuest" class="rounded-2xl border border-[#d9dee4] bg-white p-5">
      <h3 class="text-base font-semibold">游客模式</h3>
      <p class="mt-2 text-sm leading-6 text-[#556470]">你可以先了解推广能力与奖励方向；真正生成邀请码、邀请二维码和查看个人奖励流水时再登录。</p>
      <button class="mt-4 rounded-lg bg-[#0f7a5f] px-4 py-2 text-sm text-white" @click="goLogin">
        登录后启用推广功能
      </button>
    </section>

    <template v-else>
    <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <article class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="text-xs tracking-[0.1em] text-[#6c7985]">累计邀请人数</div>
        <div class="mt-2 text-3xl font-semibold text-[#17222b]">{{ referralCount }}</div>
        <div class="mt-2 text-sm text-[#5d6973]">已成功绑定的邀请关系数量</div>
      </article>
      <article class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="text-xs tracking-[0.1em] text-[#6c7985]">累计获得积分</div>
        <div class="mt-2 text-3xl font-semibold text-[#17222b]">{{ rewardCreditsTotal }}</div>
        <div class="mt-2 text-sm text-[#5d6973]">包含注册奖励、首充奖励和持续返利</div>
      </article>
      <article class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="text-xs tracking-[0.1em] text-[#6c7985]">完成首充人数</div>
        <div class="mt-2 text-3xl font-semibold text-[#17222b]">{{ firstPaidCount }}</div>
        <div class="mt-2 text-sm text-[#5d6973]">被邀请用户已完成首充的转化人数</div>
      </article>
      <article class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="text-xs tracking-[0.1em] text-[#6c7985]">最近通知</div>
        <div class="mt-2 text-3xl font-semibold text-[#17222b]">{{ notifications.length }}</div>
        <div class="mt-2 text-sm text-[#5d6973]">用于快速确认奖励是否已经到账</div>
      </article>
    </section>

    <div class="grid gap-4 xl:grid-cols-2">
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">我的邀请码</h3>
        <div class="mt-3 rounded-xl bg-[#f5f8fa] p-3 text-sm">
          <div>邀请码：<span class="font-semibold">{{ inviteInfo.invite_code || "-" }}</span></div>
          <div class="mt-2 break-all">邀请链接：{{ inviteInfo.invite_link || "-" }}</div>
        </div>
        <div class="mt-3 rounded-xl border border-[#e2e8ee] bg-[#f9fcff] p-3">
          <div class="text-sm text-[#4f5f6b]">推广二维码</div>
          <div class="mt-2 flex items-center gap-3">
            <img v-if="inviteInfo.qrcode_data_url" :src="inviteInfo.qrcode_data_url" class="h-28 w-28 rounded border border-[#dce4eb]" alt="invite qrcode" />
            <div v-else class="text-sm text-[#7a8793]">二维码加载中</div>
            <button class="rounded-lg bg-[#e8edf2] px-3 py-2 text-sm text-[#344250] disabled:opacity-60" :disabled="!inviteInfo.qrcode_data_url" @click="downloadQrcode">
              保存二维码
            </button>
          </div>
        </div>
        <div class="mt-3 flex gap-2">
          <button class="rounded-lg bg-[#0f7a5f] px-3 py-2 text-sm text-white" @click="copyLink">复制链接</button>
          <button class="rounded-lg bg-[#e8edf2] px-3 py-2 text-sm text-[#344250]" @click="loadAll">刷新数据</button>
        </div>
        <p v-if="hintText" class="mt-2 text-sm text-[#106c4f]">{{ hintText }}</p>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <h3 class="text-base font-semibold">奖励通知</h3>
        <div class="mt-3 max-h-64 space-y-2 overflow-auto text-sm">
          <div v-for="n in notifications" :key="n.id" class="rounded-lg bg-[#f5f8fb] p-3">
            <div class="font-medium">{{ n.title }}</div>
            <div class="mt-1 text-[#5c6873]">{{ n.content }}</div>
          </div>
          <div v-if="notifications.length === 0" class="text-[#5b6771]">暂无通知</div>
        </div>
      </section>
    </div>

    <section class="mt-4 rounded-2xl border border-[#d9dee4] bg-white p-5">
      <h3 class="text-base font-semibold">邀请记录</h3>
      <div class="mt-3 overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
              <th class="px-2 py-2">被邀请用户</th>
              <th class="px-2 py-2">状态</th>
              <th class="px-2 py-2">带来积分</th>
              <th class="px-2 py-2">注册时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in referrals" :key="item.invitee_id" class="border-b border-[#eef2f5]">
              <td class="px-2 py-2">{{ item.invitee_phone_masked }}</td>
              <td class="px-2 py-2">
                <span class="rounded-full bg-[#f2f6f9] px-2 py-1 text-xs text-[#44525d]">{{ mapReferralStatus(item.status) }}</span>
              </td>
              <td class="px-2 py-2">{{ item.reward_credits }}</td>
              <td class="px-2 py-2">{{ formatTime(item.created_at) }}</td>
            </tr>
            <tr v-if="referrals.length === 0">
              <td class="px-2 py-3 text-[#5b6771]" colspan="4">暂无邀请记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="mt-4 rounded-2xl border border-[#d9dee4] bg-white p-5">
      <h3 class="text-base font-semibold">推广奖励流水</h3>
      <div class="mt-3 overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-[#e1e6eb] text-left text-[#5a6671]">
              <th class="px-2 py-2">记录ID</th>
              <th class="px-2 py-2">角色</th>
              <th class="px-2 py-2">奖励类型</th>
              <th class="px-2 py-2">积分</th>
              <th class="px-2 py-2">状态</th>
              <th class="px-2 py-2">时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rewards" :key="item.id" class="border-b border-[#eef2f5]">
              <td class="px-2 py-2">{{ item.id }}</td>
              <td class="px-2 py-2">{{ mapRewardRole(item.role) }}</td>
              <td class="px-2 py-2">{{ mapRewardType(item.reward_type) }}</td>
              <td class="px-2 py-2">{{ item.credits }}</td>
              <td class="px-2 py-2">{{ mapRewardStatus(item.status) }}</td>
              <td class="px-2 py-2">{{ formatTime(item.created_at) }}</td>
            </tr>
            <tr v-if="rewards.length === 0">
              <td class="px-2 py-3 text-[#5b6771]" colspan="6">暂无奖励记录</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="mt-4">
      <BuyCreditsPanel v-if="showBuy" @paid="afterPaid" />
    </div>
    </template>
  </UserShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import BuyCreditsPanel from "../../components/BuyCreditsPanel.vue"
import UserShell from "../../components/UserShell.vue"
import { useUserProfile } from "../../composables/useUserProfile"
import { userHttp } from "../../lib/http"
import { ensureUserLogin } from "../../lib/requireLogin"
import { getUserToken } from "../../lib/session"

const showBuy = ref(false)
const router = useRouter()
const route = useRoute()
const hintText = ref("")
const inviteInfo = ref({})
const referrals = ref([])
const rewards = ref([])
const notifications = ref([])
const { user, refreshUser } = useUserProfile()
const isGuest = computed(() => !getUserToken())
const referralCount = computed(() => referrals.value.length)
const rewardCreditsTotal = computed(() =>
  rewards.value.reduce((sum, item) => sum + Number(item.credits || 0), 0)
)
const firstPaidCount = computed(() =>
  referrals.value.filter((item) => item.status === "first_paid").length
)
const userCredits = computed(() => {
  const value = user.value && user.value.credits
  if (typeof value === "number") {
    return value
  }
  return null
})

onMounted(async () => {
  if (getUserToken()) {
    await refreshUser()
    await loadAll()
  }
})

async function loadAll() {
  if (!getUserToken()) {
    // 游客点击刷新时引导登录
    ensureUserLogin(router, route, "/app/referral")
    inviteInfo.value = {}
    referrals.value = []
    rewards.value = []
    notifications.value = []
    return
  }
  const [codeData, qrcodeData, referralData, rewardData, notifyData] = await Promise.all([
    userHttp.get("/users/me/invite-code"),
    userHttp.get("/users/me/invite-qrcode"),
    userHttp.get("/users/me/referrals", { params: { page: 1, page_size: 20 } }),
    userHttp.get("/users/me/referral-rewards", { params: { page: 1, page_size: 20 } }),
    userHttp.get("/users/me/notifications", { params: { page: 1, page_size: 10 } }),
  ])
  inviteInfo.value = { ...codeData, ...qrcodeData }
  referrals.value = referralData.items || []
  rewards.value = rewardData.items || []
  notifications.value = notifyData.items || []
}

async function copyLink() {
  if (!ensureUserLogin(router, route, "/app/referral")) {
    return
  }
  if (!inviteInfo.value.invite_link) {
    return
  }
  await navigator.clipboard.writeText(inviteInfo.value.invite_link)
  hintText.value = "邀请链接已复制"
}

function downloadQrcode() {
  if (!inviteInfo.value.qrcode_data_url) {
    return
  }
  const a = document.createElement("a")
  a.href = inviteInfo.value.qrcode_data_url
  a.download = `invite_${inviteInfo.value.invite_code || "qrcode"}.png`
  a.click()
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}

function mapReferralStatus(status) {
  const map = {
    registered: "已注册",
    first_paid: "已首充",
  }
  return map[status] || status || "-"
}

function mapRewardRole(role) {
  const map = {
    邀请人奖励: "邀请人奖励",
    被邀请人福利: "被邀请人福利",
  }
  return map[role] || role || "-"
}

function mapRewardType(type) {
  const map = {
    register_invite: "邀请注册奖励",
    register_bonus: "被邀请注册福利",
    first_pay: "首充返佣",
    recurring_pay: "持续返利",
  }
  return map[type] || type || "-"
}

function mapRewardStatus(status) {
  const map = {
    sent: "已发放",
    pending: "待发放",
    failed: "失败",
  }
  return map[status] || status || "-"
}

async function afterPaid() {
  if (getUserToken()) {
    await refreshUser()
  }
}

function goLogin() {
  const redirect = encodeURIComponent(route.fullPath || "/app/referral")
  router.push(`/login?redirect=${redirect}`)
}
</script>
