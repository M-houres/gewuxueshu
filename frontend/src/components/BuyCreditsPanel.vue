<template>
  <section class="scholar-panel">
    <div class="scholar-panel__header">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div class="scholar-kicker">Credits Packages</div>
          <h3 class="scholar-subtitle">积分套餐</h3>
          <p class="scholar-lead">
            充值页与后台套餐配置自动同步，支持微信支付、支付宝和联调模式。
          </p>
        </div>
        <span class="scholar-badge" :class="paymentTestMode ? 'scholar-badge--warn' : 'scholar-badge--info'">
          {{ paymentTipText }}
        </span>
      </div>
    </div>

    <div class="scholar-panel__body">
      <p v-if="paymentTestMode" class="scholar-note scholar-note--warn">
        当前为联调支付模式，二维码仅用于测试链路，不代表真实扣款。
      </p>

      <div class="scholar-option-grid md:grid-cols-2" style="margin-top: 18px">
        <button
          v-for="item in packages"
          :key="item.name"
          type="button"
          class="scholar-option-card"
          :disabled="loading"
          @click="openPay(item)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="text-base font-semibold text-[var(--ink)]">{{ item.name }}</div>
            <span v-if="item.badge" class="scholar-badge scholar-badge--success">{{ item.badge }}</span>
          </div>
          <div class="mt-3 text-sm leading-7 text-[var(--ink-soft)]">
            {{ packageDescription(item) }}
          </div>
          <div class="mt-5 flex items-end justify-between gap-3">
            <div class="text-3xl font-semibold text-[var(--ink)]">¥{{ Number(item.price).toFixed(2) }}</div>
            <div class="text-sm font-medium text-[var(--accent)]">
              {{ Number(item.credits).toLocaleString() }} 积分
            </div>
          </div>
        </button>
      </div>

      <p v-if="errorText" class="scholar-note scholar-note--danger" style="margin-top: 18px">
        {{ errorText }}
      </p>
      <p v-if="okText" class="scholar-note scholar-note--success" style="margin-top: 18px">
        {{ okText }}
      </p>
    </div>

    <div v-if="showModal" class="scholar-modal" @click.self="closeModal">
      <div class="scholar-modal__dialog">
        <div class="scholar-panel__header">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="scholar-kicker">Payment Order</div>
              <h3 class="scholar-subtitle">支付订单</h3>
              <p class="scholar-lead">
                {{ selectedPackage?.name || "-" }} / ¥{{ selectedPackage?.price || "-" }}
              </p>
            </div>
            <button class="scholar-button scholar-button--secondary" type="button" @click="closeModal">
              关闭
            </button>
          </div>
        </div>

        <div class="scholar-panel__body">
          <div class="scholar-inline-actions">
            <button
              v-for="p in providers"
              :key="p.value"
              type="button"
              class="scholar-chip"
              :class="{ 'is-active': provider === p.value }"
              @click="switchProvider(p.value)"
            >
              {{ p.label }}
            </button>
          </div>

          <div v-if="isGuest" class="scholar-note" style="margin-top: 18px">
            <div>游客可先查看套餐与支付方式，真正创建订单时再登录。</div>
            <div class="scholar-inline-actions" style="margin-top: 14px">
              <button class="scholar-button" type="button" @click="goLoginForOrder">登录后创建订单</button>
              <button class="scholar-button scholar-button--secondary" type="button" @click="closeModal">
                继续浏览
              </button>
            </div>
          </div>

          <div v-else class="scholar-grid scholar-grid--halves" style="margin-top: 18px; align-items: start">
            <div class="scholar-panel scholar-panel--soft">
              <div class="scholar-panel__body">
                <div class="scholar-stack">
                  <span class="scholar-pill">订单号：{{ orderNo || "-" }}</span>
                  <span class="scholar-badge" :class="orderStatusBadgeClass">{{ orderStatusText }}</span>
                  <span class="scholar-pill">剩余 {{ remainSeconds }} 秒</span>
                </div>
              </div>
            </div>

            <div class="scholar-panel scholar-panel--soft">
              <div class="scholar-panel__body">
                <div class="scholar-inline-actions" style="align-items: center">
                  <img
                    v-if="qrCodeDataUrl"
                    :src="qrCodeDataUrl"
                    alt="payment qrcode"
                    class="rounded-[20px] border border-[var(--line)] bg-white"
                    style="height: 180px; width: 180px"
                  />
                  <div class="scholar-stack">
                    <button class="scholar-button scholar-button--secondary" type="button" @click="refreshOrder">
                      刷新二维码
                    </button>
                    <button
                      v-if="paymentTestMode"
                      class="scholar-button"
                      type="button"
                      @click="mockPay"
                    >
                      模拟已支付
                    </button>
                  </div>
                </div>
              </div>
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

const orderStatusBadgeClass = computed(() => {
  const map = {
    created: "scholar-badge--warn",
    paid: "scholar-badge--success",
    closed: "scholar-badge--danger",
    refunded: "scholar-badge--info",
  }
  return map[orderStatus.value] || "scholar-badge--info"
})

const paymentTipText = computed(() =>
  paymentTestMode.value ? "联调支付模式" : "支持微信 / 支付宝"
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
  return "适合常规论文处理场景，可用于 AIGC 检测、降重复率和降 AIGC 率任务。"
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
