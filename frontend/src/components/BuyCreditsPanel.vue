<template>
  <section class="rounded-3xl border border-[#d9dee4] bg-white p-6 shadow-[0_14px_30px_rgba(23,35,48,0.08)]">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">积分套餐</h3>
      <span class="text-xs text-[#5b6771]">{{ paymentTipText }}</span>
    </div>
    <p
      v-if="paymentTestMode"
      class="mt-2 rounded-xl bg-[#fff3e8] px-3 py-2 text-xs leading-5 text-[#93521f]"
    >
      当前为联调支付模式，二维码仅用于测试链路，不代表真实扣款。
    </p>
    <div class="mt-4 grid gap-3 md:grid-cols-2">
      <button
        v-for="item in packages"
        :key="item.name"
        class="rounded-2xl border border-[#d8e0e7] bg-[linear-gradient(145deg,#f7fafc,#fdfdfc)] p-4 text-left transition hover:border-[#0f7a5f] hover:shadow-[0_10px_24px_rgba(20,38,52,0.1)]"
        :disabled="loading"
        @click="openPay(item)"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="text-base font-semibold">{{ item.name }}</div>
          <span
            v-if="item.badge"
            class="rounded-full bg-[#e8f4ef] px-2 py-1 text-[11px] tracking-[0.04em] text-[#0f6c53]"
          >
            {{ item.badge }}
          </span>
        </div>
        <div class="mt-2 min-h-[38px] text-xs leading-5 text-[#5c6974]">
          {{ packageDescription(item) }}
        </div>
        <div class="mt-3 flex items-center justify-between">
          <div class="text-sm font-semibold text-[#2f3f4a]">¥{{ Number(item.price).toFixed(2) }}</div>
          <div class="text-xs text-[#0f7a5f]">{{ Number(item.credits).toLocaleString() }} 积分</div>
        </div>
      </button>
    </div>
    <p v-if="errorText" class="mt-3 text-sm text-[#af3f33]">{{ errorText }}</p>
    <p v-if="okText" class="mt-3 text-sm text-[#106c4f]">{{ okText }}</p>

    <div
      v-if="showModal"
      class="fixed inset-0 z-40 flex items-center justify-center bg-black/35 p-4"
      @click.self="closeModal"
    >
      <div class="w-full max-w-lg rounded-2xl bg-white p-5 shadow-[0_18px_40px_rgba(0,0,0,0.16)]">
        <div class="flex items-center justify-between">
          <h4 class="text-base font-semibold">支付订单</h4>
          <button class="rounded bg-[#edf2f6] px-2 py-1 text-xs text-[#344250]" @click="closeModal">
            关闭
          </button>
        </div>
        <div class="mt-2 text-sm text-[#4f5f6b]">
          {{ selectedPackage?.name || "-" }} / ¥{{ selectedPackage?.price || "-" }}
        </div>
        <div class="mt-3 flex gap-2">
          <button
            v-for="p in providers"
            :key="p.value"
            class="rounded px-3 py-1.5 text-sm"
            :class="provider === p.value ? 'bg-[#0f7a5f] text-white' : 'bg-[#edf2f6] text-[#344250]'"
            @click="switchProvider(p.value)"
          >
            {{ p.label }}
          </button>
        </div>

        <div
          v-if="isGuest"
          class="mt-4 rounded-xl border border-[#dce4eb] bg-[#f8fbff] p-4 text-sm text-[#4f5f6b]"
        >
          <div>游客可以先看套餐和支付方式，真正创建订单时再登录。</div>
          <div class="mt-4 flex flex-wrap gap-2">
            <button class="rounded bg-[#0f7a5f] px-3 py-2 text-sm text-white" @click="goLoginForOrder">
              登录后创建订单
            </button>
            <button class="rounded bg-[#edf2f6] px-3 py-2 text-sm text-[#344250]" @click="closeModal">
              继续浏览
            </button>
          </div>
        </div>

        <div v-else class="mt-4 rounded-xl border border-[#dce4eb] bg-[#f8fbff] p-4">
          <div class="text-xs text-[#5f6d79]">订单号：{{ orderNo || "-" }}</div>
          <div class="mt-3 flex items-center gap-4">
            <img
              v-if="qrCodeDataUrl"
              :src="qrCodeDataUrl"
              class="h-40 w-40 rounded border border-[#dbe3ea]"
              alt="payment qrcode"
            />
            <div class="space-y-2 text-sm">
              <div>倒计时：{{ remainSeconds }} 秒</div>
              <div>状态：{{ orderStatusText }}</div>
              <button class="rounded bg-[#edf2f6] px-3 py-1.5 text-xs text-[#344250]" @click="refreshOrder">
                刷新二维码
              </button>
              <button
                v-if="paymentTestMode"
                class="rounded bg-[#0f7a5f] px-3 py-1.5 text-xs text-white"
                @click="mockPay"
              >
                模拟已支付
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { userHttp } from "../lib/http"
import { ensureUserLogin } from "../lib/requireLogin"
import { getUserToken } from "../lib/session"

const emit = defineEmits(["paid"])
const router = useRouter()
const route = useRoute()

const packages = ref([])
const loading = ref(false)
const errorText = ref("")
const okText = ref("")
const paymentTestMode = ref(false)
const supportedProviderValues = ref([])

const showModal = ref(false)
const selectedPackage = ref(null)
const provider = ref("mock")
const orderNo = ref("")
const qrCodeDataUrl = ref("")
const remainSeconds = ref(0)
const orderStatus = ref("created")

let countdownTimer = null
let pollTimer = null

const isGuest = computed(() => !getUserToken())
const allProviders = [
  { value: "mock", label: "测试支付" },
  { value: "wechat", label: "微信支付" },
  { value: "alipay", label: "支付宝" },
]
const providers = computed(() => {
  if (supportedProviderValues.value.length > 0) {
    return allProviders.filter((item) => supportedProviderValues.value.includes(item.value))
  }
  return paymentTestMode.value ? [allProviders[0]] : allProviders.slice(1)
})

const orderStatusText = computed(() => {
  const map = {
    created: "待支付",
    paid: "已支付",
    closed: "已过期",
    refunded: "已退款",
  }
  return map[orderStatus.value] || orderStatus.value
})

const paymentTipText = computed(() =>
  paymentTestMode.value ? "联调支付模式（模拟）" : "支持微信 / 支付宝"
)

onMounted(loadPackages)
onUnmounted(stopTimers)

async function loadPackages() {
  const data = await userHttp.get("/billing/packages")
  packages.value = data.items || []
  if (typeof data.payment_test_mode === "boolean") {
    paymentTestMode.value = data.payment_test_mode
  }
  if (Array.isArray(data.supported_providers)) {
    supportedProviderValues.value = data.supported_providers
  }
  const defaultProvider = providers.value[0]?.value
  if (defaultProvider) {
    provider.value = defaultProvider
  }
}

function packageDescription(item) {
  const text = String(item?.description || "").trim()
  if (text) {
    return text
  }
  return "适合常规论文处理场景，可用于AIGC检测、降重复率和降AIGC率任务。"
}

async function openPay(item) {
  errorText.value = ""
  selectedPackage.value = item
  provider.value = providers.value[0]?.value || "mock"
  orderNo.value = ""
  qrCodeDataUrl.value = ""
  remainSeconds.value = 0
  orderStatus.value = "created"
  showModal.value = true
  stopTimers()
  if (isGuest.value) {
    return
  }
  await createOrder()
}

async function switchProvider(nextProvider) {
  if (provider.value === nextProvider) return
  provider.value = nextProvider
  if (isGuest.value) {
    return
  }
  await createOrder()
}

async function refreshOrder() {
  if (!ensureUserLogin(router, route, "/app/buy")) {
    return
  }
  await createOrder()
}

async function createOrder() {
  if (!selectedPackage.value) return
  loading.value = true
  errorText.value = ""
  try {
    const data = await userHttp.post("/billing/create-order", {
      package_name: selectedPackage.value.name,
      provider: provider.value,
    })
    orderNo.value = data.order_no
    qrCodeDataUrl.value = data.qrcode_data_url
    remainSeconds.value = Number(data.expire_seconds || 300)
    orderStatus.value = data.status || "created"
    startTimers()
  } catch (error) {
    errorText.value = error.message || "创建订单失败"
  } finally {
    loading.value = false
  }
}

function startTimers() {
  stopTimers()
  countdownTimer = setInterval(() => {
    remainSeconds.value -= 1
    if (remainSeconds.value <= 0) {
      remainSeconds.value = 0
      stopTimers()
      orderStatus.value = "closed"
    }
  }, 1000)
  pollTimer = setInterval(checkOrderStatus, 3000)
}

function stopTimers() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function checkOrderStatus() {
  if (!orderNo.value) return
  try {
    const data = await userHttp.get(`/billing/order-status/${orderNo.value}`)
    orderStatus.value = data.status || "created"
    const remain = Number(data.remain_seconds)
    if (Number.isFinite(remain) && remain >= 0) {
      remainSeconds.value = remain
    }
    if (orderStatus.value === "paid") {
      onPaySuccess(data)
    }
    if (orderStatus.value === "closed") {
      stopTimers()
    }
  } catch {
    // Ignore polling failures to avoid interrupting the checkout flow.
  }
}

async function mockPay() {
  if (!ensureUserLogin(router, route, "/app/buy")) {
    errorText.value = "请先登录后再支付"
    return
  }
  if (!orderNo.value) return
  try {
    const data = await userHttp.post(`/billing/order-pay/${orderNo.value}`)
    onPaySuccess(data)
  } catch (error) {
    errorText.value = error.message || "支付失败"
  }
}

function onPaySuccess(data) {
  stopTimers()
  orderStatus.value = "paid"
  showModal.value = false
  okText.value = `支付成功，订单号 ${orderNo.value}`
  emit("paid", data)
}

function closeModal() {
  showModal.value = false
  stopTimers()
}

function goLoginForOrder() {
  ensureUserLogin(router, route, "/app/buy")
}
</script>
