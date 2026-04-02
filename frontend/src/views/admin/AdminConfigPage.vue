<template>
  <AdminShell title="配置中心" subtitle="运营填写后即可生效，支持审计与就绪检查">
    <div class="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)_300px]">
      <section class="rounded-2xl border border-[#d9dee4] bg-white p-4">
        <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">配置导航</div>
        <div class="mt-3 space-y-2">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="w-full rounded-2xl border px-3 py-3 text-left transition"
            :class="activeTab === tab.key ? 'border-[#0f7a5f] bg-[linear-gradient(150deg,#edf7f3,#f8fcfb)]' : 'border-[#d6dee6] bg-white hover:border-[#9ab8ac]'"
            @click="activeTab = tab.key"
          >
            <div class="flex items-start justify-between gap-2">
              <div>
                <div class="text-sm font-semibold text-[#1f2c35]">{{ tab.label }}</div>
                <div class="mt-1 text-xs leading-5 text-[#5f6d79]">{{ tab.desc }}</div>
              </div>
              <span class="rounded-full px-2 py-1 text-[11px]" :class="chipClass(readinessMap[tab.key]?.status)">
                {{ readinessLabel(readinessMap[tab.key]?.status) }}
              </span>
            </div>
          </button>
        </div>
      </section>

      <section class="rounded-2xl border border-[#d9dee4] bg-white p-5">
        <div class="border-b border-[#e6ebef] pb-4">
          <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">{{ currentGuide.code }}</div>
          <h3 class="mt-2 text-xl font-semibold text-[#18242b]">{{ currentTab.label }}</h3>
          <p class="mt-2 text-sm leading-6 text-[#5b6771]">{{ currentGuide.lead }}</p>
          <p
            v-if="readinessMap[activeTab]?.message"
            class="mt-3 rounded-xl border border-[#dce4eb] bg-[#f8fbff] px-3 py-2 text-sm text-[#415160]"
          >
            当前状态：{{ readinessMap[activeTab]?.message }}
          </p>
        </div>

        <div class="mt-5 space-y-4">
          <template v-if="activeTab === 'llm'">
            <label class="inline-flex items-center gap-2 text-sm"><input v-model="forms.llm.enabled" type="checkbox" /> 启用大模型增强</label>
            <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <button
                v-for="item in llmProviders"
                :key="item.value"
                type="button"
                class="rounded-2xl border px-3 py-3 text-left text-sm transition"
                :class="forms.llm.provider === item.value ? 'border-[#0f7a5f] bg-[linear-gradient(150deg,#edf7f3,#f8fcfb)]' : 'border-[#d6dee6] bg-white hover:border-[#9ab8ac]'"
                @click="pickLlm(item.value)"
              >
                <div class="font-semibold text-[#21303a]">{{ item.label }}</div>
                <div class="mt-1 text-xs leading-5 text-[#5f6d79]">{{ item.desc }}</div>
              </button>
            </div>
            <div class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>模型名</span><input v-model="forms.llm.model" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>Base URL</span><input v-model="forms.llm.base_url" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>API Key</span><input v-model="forms.llm.api_key" type="password" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>超时（秒）</span><input v-model.number="forms.llm.timeout_seconds" type="number" min="5" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>最大输出 Tokens</span><input v-model.number="forms.llm.max_output_tokens" type="number" min="128" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>温度</span><input v-model.number="forms.llm.temperature" type="number" min="0" max="2" step="0.1" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
            </div>
          </template>

          <template v-else-if="activeTab === 'payment'">
            <label class="inline-flex items-center gap-2 text-sm"><input v-model="forms.payment.test_mode" type="checkbox" /> 联调模式（测试）</label>
            <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <button
                v-for="item in paymentProviders"
                :key="item.value"
                type="button"
                class="rounded-2xl border px-3 py-3 text-left text-sm transition"
                :class="forms.payment.provider === item.value ? 'border-[#0f7a5f] bg-[linear-gradient(150deg,#edf7f3,#f8fcfb)]' : 'border-[#d6dee6] bg-white hover:border-[#9ab8ac]'"
                @click="forms.payment.provider = item.value"
              >
                <div class="font-semibold text-[#21303a]">{{ item.label }}</div>
                <div class="mt-1 text-xs leading-5 text-[#5f6d79]">{{ item.desc }}</div>
              </button>
            </div>
            <p
              v-if="paymentProviderUnsupported"
              class="rounded-xl border border-[#f0d5cf] bg-[#fff6f3] px-3 py-2 text-sm text-[#9a4a3b]"
            >
              当前支付通道配置已过时，请切换为微信支付、支付宝或 Mock 联调。
            </p>
            <div v-if="isWechatPay" class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>AppID</span><input v-model="forms.payment.app_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>商户号</span><input v-model="forms.payment.merchant_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>商户证书序列号</span><input v-model="forms.payment.merchant_serial_no" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>APIv3 Key</span><input v-model="forms.payment.api_v3_key" type="password" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm md:col-span-2"><span>公网回调地址或域名</span><input v-model="forms.payment.notify_url" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="https://your.domain" /></label>
              <div class="rounded-xl border border-[#dce4eb] bg-[#f8fbff] px-3 py-2 text-xs leading-5 text-[#4f5d69] md:col-span-2">
                实际微信回调地址：{{ paymentNotifyPreview }}
              </div>
              <label class="space-y-1 text-sm md:col-span-2"><span>商户私钥 PEM</span><textarea v-model="forms.payment.merchant_private_key_pem" rows="4" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2"></textarea></label>
              <label class="space-y-1 text-sm"><span>微信支付公钥 ID</span><input v-model="forms.payment.wechatpay_public_key_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>微信支付公钥</span><textarea v-model="forms.payment.wechatpay_public_key" rows="4" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2"></textarea></label>
            </div>
            <div v-else-if="isAlipay" class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>支付宝 AppID</span><input v-model="forms.payment.app_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>支付宝网关</span><input v-model="forms.payment.gateway_url" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="https://openapi.alipay.com/gateway.do" /></label>
              <label class="space-y-1 text-sm md:col-span-2"><span>公网回调地址或域名</span><input v-model="forms.payment.notify_url" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="https://your.domain" /></label>
              <div class="rounded-xl border border-[#dce4eb] bg-[#f8fbff] px-3 py-2 text-xs leading-5 text-[#4f5d69] md:col-span-2">
                实际支付宝回调地址：{{ paymentNotifyPreview }}
              </div>
              <label class="space-y-1 text-sm md:col-span-2"><span>应用私钥 PEM</span><textarea v-model="forms.payment.app_private_key_pem" rows="4" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2"></textarea></label>
              <label class="space-y-1 text-sm md:col-span-2"><span>支付宝公钥 PEM</span><textarea v-model="forms.payment.alipay_public_key" rows="4" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2"></textarea></label>
            </div>
          </template>

          <template v-else-if="activeTab === 'billing'">
            <section class="rounded-2xl border border-[#dce4eb] bg-[#f8fbff] p-4">
              <div class="text-sm font-semibold text-[#1f2c35]">任务计费（按字符）</div>
              <div class="mt-1 text-xs leading-5 text-[#5f6d79]">计费口径：任务实际扣费 = 字符数 × 单价。建议按典型字数（1k/5k/8k）先做换算。</div>
              <div class="mt-3 grid gap-3 md:grid-cols-3">
                <label class="space-y-1 text-sm"><span>AIGC 单价</span><input v-model.number="forms.billing.aigc_rate" type="number" min="1" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
                <label class="space-y-1 text-sm"><span>降重单价</span><input v-model.number="forms.billing.dedup_rate" type="number" min="1" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
                <label class="space-y-1 text-sm"><span>降AIGC率单价</span><input v-model.number="forms.billing.rewrite_rate" type="number" min="1" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              </div>
            </section>

            <section class="rounded-2xl border border-[#dce4eb] bg-[#f8fbff] p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div class="text-sm font-semibold text-[#1f2c35]">充值套餐（前台展示）</div>
                  <div class="mt-1 text-xs leading-5 text-[#5f6d79]">运营只需要在这里配置套餐名称、价格、积分和简介，前台购买页会自动同步。</div>
                </div>
                <button class="rounded-lg bg-[#edf2f6] px-3 py-2 text-xs text-[#344250]" @click="addBillingPackage">
                  新增套餐
                </button>
              </div>
              <div class="mt-3 space-y-3">
                <article
                  v-for="(pkg, idx) in forms.billing.packages"
                  :key="`pkg-${idx}`"
                  class="rounded-2xl border border-[#d6dfe7] bg-white p-3"
                >
                  <div class="grid gap-3 md:grid-cols-6">
                    <label class="space-y-1 text-sm md:col-span-2">
                      <span>套餐名称</span>
                      <input v-model.trim="pkg.name" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="例如：标准包" />
                    </label>
                    <label class="space-y-1 text-sm">
                      <span>价格（元）</span>
                      <input v-model.number="pkg.price" type="number" min="0.01" step="0.01" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" />
                    </label>
                    <label class="space-y-1 text-sm">
                      <span>积分</span>
                      <input v-model.number="pkg.credits" type="number" min="1" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" />
                    </label>
                    <label class="space-y-1 text-sm">
                      <span>标签（可选）</span>
                      <input v-model.trim="pkg.badge" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="新手推荐" />
                    </label>
                    <div class="flex items-end justify-end">
                      <button
                        class="rounded-lg bg-[#edf2f6] px-3 py-2 text-xs text-[#344250] disabled:opacity-50"
                        :disabled="forms.billing.packages.length <= 1"
                        @click="removeBillingPackage(idx)"
                      >
                        删除
                      </button>
                    </div>
                    <label class="space-y-1 text-sm md:col-span-5">
                      <span>套餐介绍</span>
                      <input v-model.trim="pkg.description" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="给普通运营人员看的简介，前台会展示" />
                    </label>
                    <label class="inline-flex items-center gap-2 text-sm md:col-span-1">
                      <input v-model="pkg.enabled" type="checkbox" />
                      前台启用
                    </label>
                  </div>
                </article>
              </div>
            </section>
          </template>

          <template v-else-if="activeTab === 'login'">
            <div class="grid gap-3 md:grid-cols-4">
              <button
                v-for="item in smsProviders"
                :key="item.value"
                type="button"
                class="rounded-2xl border px-3 py-3 text-left text-sm transition"
                :class="forms.login.sms_provider === item.value ? 'border-[#0f7a5f] bg-[linear-gradient(150deg,#edf7f3,#f8fcfb)]' : 'border-[#d6dee6] bg-white hover:border-[#9ab8ac]'"
                @click="forms.login.sms_provider = item.value"
              >
                <div class="font-semibold text-[#21303a]">{{ item.label }}</div>
                <div class="mt-1 text-xs leading-5 text-[#5f6d79]">{{ item.desc }}</div>
              </button>
            </div>
            <label class="inline-flex items-center gap-2 text-sm"><input v-model="forms.login.debug_code_enabled" type="checkbox" /> 开发环境返回 debug_code</label>
            <div v-if="forms.login.sms_provider === 'custom_webhook'" class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>短信网关 URL</span><input v-model="forms.login.sms_gateway_url" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="https://your-sms-gateway.example.com/send" /></label>
              <label class="space-y-1 text-sm"><span>短信网关 API Key（可选）</span><input v-model="forms.login.sms_api_key" type="password" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>短信模板 ID / Code</span><input v-model="forms.login.sms_template_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>短信签名</span><input v-model="forms.login.sms_sign_name" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
            </div>
            <div v-else-if="forms.login.sms_provider === 'tencent_sms'" class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>SmsSdkAppId</span><input v-model="forms.login.sms_sdk_app_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>腾讯云 Region</span><input v-model="forms.login.sms_region" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="ap-guangzhou" /></label>
              <label class="space-y-1 text-sm"><span>短信模板 ID</span><input v-model="forms.login.sms_template_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>短信签名</span><input v-model="forms.login.sms_sign_name" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>SecretId</span><input v-model="forms.login.sms_access_key_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>SecretKey</span><input v-model="forms.login.sms_access_key_secret" type="password" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
            </div>
            <div v-else-if="forms.login.sms_provider === 'aliyun_sms'" class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>阿里云 RegionId</span><input v-model="forms.login.sms_aliyun_region_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" placeholder="cn-hangzhou" /></label>
              <label class="space-y-1 text-sm"><span>短信模板 CODE</span><input v-model="forms.login.sms_template_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>短信签名</span><input v-model="forms.login.sms_sign_name" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>AccessKeyId</span><input v-model="forms.login.sms_access_key_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm md:col-span-2"><span>AccessKeySecret</span><input v-model="forms.login.sms_access_key_secret" type="password" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
            </div>
            <div v-else class="rounded-xl border border-[#dce4eb] bg-[#f8fbff] px-3 py-3 text-sm text-[#4f5d69]">
              SMS login is disabled. Enable WeChat login or debug_code to keep at least one login path.
            </div>
            <label class="inline-flex items-center gap-2 text-sm"><input v-model="forms.login.wechat_login_enabled" type="checkbox" /> 启用微信扫码登录</label>
            <div v-if="forms.login.wechat_login_enabled" class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>微信 AppID</span><input v-model="forms.login.wechat_app_id" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>微信 AppSecret</span><input v-model="forms.login.wechat_app_secret" type="password" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm md:col-span-2"><span>微信回调地址</span><input v-model="forms.login.wechat_redirect_uri" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
            </div>
          </template>

          <template v-else-if="activeTab === 'referral'">
            <div class="grid gap-3 md:grid-cols-2">
              <label class="space-y-1 text-sm"><span>邀请人注册奖励</span><input v-model.number="forms.referral.register_inviter_credits" type="number" min="0" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>被邀请人注册福利</span><input v-model.number="forms.referral.register_invitee_bonus" type="number" min="0" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>首单返佣比例（%）</span><input v-model.number="referralFirstPayPct" type="number" min="0" max="100" step="0.01" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm"><span>复购返佣比例（%）</span><input v-model.number="referralRecurringPct" type="number" min="0" max="100" step="0.01" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
              <label class="space-y-1 text-sm md:col-span-2"><span>同 IP 24 小时注册上限</span><input v-model.number="forms.referral.ip_limit_24h" type="number" min="1" class="w-full rounded-xl border border-[#ccd5dd] px-3 py-2" /></label>
            </div>
          </template>
        </div>

        <div class="mt-5 flex flex-wrap gap-2 border-t border-[#e6ebef] pt-4">
          <button class="rounded-xl bg-[#0f7a5f] px-4 py-2 text-sm text-white disabled:opacity-60" :disabled="saving" @click="saveCurrent">{{ saving ? "保存中..." : `保存${currentTab.label}` }}</button>
          <button class="rounded-xl bg-[#edf2f6] px-4 py-2 text-sm text-[#344250]" @click="reloadCurrent">重新加载</button>
        </div>
        <p v-if="hintText" class="mt-3 text-sm text-[#106c4f]">{{ hintText }}</p>
        <p v-if="errorText" class="mt-3 text-sm text-[#af3f33]">{{ errorText }}</p>
      </section>

      <section class="space-y-4">
        <article class="rounded-2xl border border-[#d9dee4] bg-white p-4">
          <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">使用说明</div>
          <h4 class="mt-2 text-sm font-semibold text-[#1b2730]">{{ currentGuide.title }}</h4>
          <p class="mt-3 text-sm leading-6 text-[#596671]">{{ currentGuide.desc }}</p>
          <div class="mt-4 space-y-2">
            <div v-for="item in currentGuide.checklist" :key="item" class="rounded-xl border border-[#e3e8ed] bg-[#fbfcfd] px-3 py-2 text-sm leading-6 text-[#384853]">{{ item }}</div>
          </div>
        </article>
        <article class="rounded-2xl border border-[#d9dee4] bg-white p-4">
          <div class="text-[11px] uppercase tracking-[0.18em] text-[#73808b]">官方文档</div>
          <div class="mt-3 space-y-2">
            <a v-for="doc in currentGuide.docs" :key="doc.href" :href="doc.href" target="_blank" rel="noreferrer" class="block rounded-xl border border-[#e3e8ed] bg-[#fbfcfd] px-3 py-2 text-sm text-[#125f4b] underline underline-offset-4">{{ doc.label }}</a>
          </div>
        </article>
      </section>
    </div>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"

const tabs = [
  { key: "login", label: "登录配置", desc: "短信与微信登录" },
  { key: "payment", label: "支付配置", desc: "微信支付 / 支付宝" },
  { key: "billing", label: "计费规则", desc: "按字符扣费" },
  { key: "referral", label: "推广规则", desc: "奖励与返佣" },
  { key: "llm", label: "大模型配置", desc: "国内外主流模型" },
]

const llmProviders = [
  { value: "openai", label: "OpenAI", desc: "官方接口" },
  { value: "anthropic", label: "Anthropic", desc: "Claude Messages" },
  { value: "gemini", label: "Gemini", desc: "Google generateContent" },
  { value: "deepseek", label: "DeepSeek", desc: "官方兼容接口" },
  { value: "qwen", label: "通义千问", desc: "百炼兼容模式" },
  { value: "doubao", label: "豆包 / 方舟", desc: "Ark 兼容模式" },
  { value: "moonshot", label: "Kimi", desc: "Moonshot 官方接口" },
  { value: "zhipu", label: "智谱 GLM", desc: "智谱兼容接口" },
  { value: "custom_openai", label: "自定义兼容", desc: "手填 OpenAI 兼容网关" },
]

const llmPresets = {
  openai: { base_url: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  anthropic: { base_url: "https://api.anthropic.com/v1", model: "claude-3-5-sonnet-latest" },
  gemini: { base_url: "https://generativelanguage.googleapis.com/v1beta", model: "gemini-2.0-flash" },
  deepseek: { base_url: "https://api.deepseek.com", model: "deepseek-chat" },
  qwen: { base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus" },
  doubao: { base_url: "https://ark.cn-beijing.volces.com/api/v3", model: "" },
  moonshot: { base_url: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k" },
  zhipu: { base_url: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-flash" },
  custom_openai: { base_url: "", model: "" },
}

const paymentProviders = [
  { value: "wechatpay_v3", label: "微信支付 V3", desc: "官方 Native 收款" },
  { value: "alipay", label: "支付宝", desc: "官方预创建二维码" },
  { value: "mock", label: "Mock 联调", desc: "仅开发联调" },
]

const smsProviders = [
  { value: "custom_webhook", label: "自建短信", desc: "自有短信网关" },
  { value: "tencent_sms", label: "腾讯云短信", desc: "官方 API" },
  { value: "aliyun_sms", label: "阿里云短信", desc: "官方 API" },
  { value: "disabled", label: "关闭短信", desc: "仅微信或 debug" },
]

const defaultBillingPackages = [
  {
    name: "入门包",
    price: 9.9,
    credits: 10000,
    description: "适合单篇检测与初稿优化，低门槛启动。",
    badge: "新手推荐",
    enabled: true,
  },
  {
    name: "标准包",
    price: 39,
    credits: 50000,
    description: "适合毕业季高频使用，兼顾成本和处理量。",
    badge: "运营主推",
    enabled: true,
  },
  {
    name: "专业包",
    price: 128,
    credits: 200000,
    description: "适合团队批量处理，单位成本更优。",
    badge: "高性价比",
    enabled: true,
  },
  {
    name: "年费包",
    price: 388,
    credits: 1000000,
    description: "适合长期运营或机构使用，大额度稳定供给。",
    badge: "长期使用",
    enabled: true,
  },
]

const guideMap = {
  login: {
    code: "Access Setup",
    lead: "至少保证短信、微信扫码、debug_code 中一种可用。",
    title: "先打通登录链路",
    desc: "保存后前台登录页会立即按最新配置切换。",
    checklist: [
      "生产环境建议至少保留 1 个正式登录方式。",
      "微信扫码登录回调必须是公网 HTTPS。",
    ],
    docs: [
      { label: "微信开放平台 网站应用登录", href: "https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html" },
      { label: "腾讯云短信 SendSms", href: "https://cloud.tencent.com/document/product/382/55981" },
      { label: "阿里云短信 SendSms", href: "https://help.aliyun.com/zh/sms/developer-reference/api-dysmsapi-2017-05-25-sendsms" },
    ],
  },
  payment: {
    code: "Revenue Setup",
    lead: "关闭联调模式后才会走真实支付。正式支付必须依赖公网回调。",
    title: "真实收款必须可回调",
    desc: "本地前后端联调不等于真实收款，正式支付需要公网 HTTPS 域名。",
    checklist: [
      "微信支付需要商户号、商户私钥、APIv3 Key。",
      "支付宝需要应用私钥、支付宝公钥、AppID。",
    ],
    docs: [
      { label: "微信支付 Native 下单", href: "https://pay.wechatpay.cn/doc/v3/merchant/4012791898" },
      { label: "微信支付 回调通知", href: "https://pay.wechatpay.cn/doc/v3/merchant/4012071382" },
      { label: "支付宝预创建订单", href: "https://opendocs.alipay.com/apis/api_1/alipay.trade.precreate" },
      { label: "支付宝开放平台", href: "https://opendocs.alipay.com/open/00f0fa" },
    ],
  },
  billing: {
    code: "Pricing Setup",
    lead: "同时配置任务单价和充值套餐，前台会自动同步。",
    title: "定价直接影响转化",
    desc: "任务按字符计费，套餐按价格兑积分。运营填完即可上线生效。",
    checklist: [
      "三类单价必须都大于 0。",
      "至少启用 1 个套餐，并补充用户易懂的套餐介绍。",
    ],
    docs: [
      { label: "微信支付 开发文档", href: "https://pay.wechatpay.cn/doc/v3/merchant/4012791898" },
      { label: "支付宝 开发文档", href: "https://opendocs.alipay.com/apis/api_1/alipay.trade.precreate" },
    ],
  },
  referral: {
    code: "Growth Setup",
    lead: "推广规则要让运营看得懂奖励从哪里出、返到哪里去。",
    title: "返佣规则必须简单",
    desc: "保存后邀请码奖励和返佣会自动按这里执行。",
    checklist: [
      "先定注册奖励，再定首单和复购返佣。",
      "返佣比例按百分比理解。",
    ],
    docs: [{ label: "运营配置参考", href: "https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety" }],
  },
  llm: {
    code: "Model Setup",
    lead: "支持 OpenAI、Anthropic、Gemini、DeepSeek、Qwen、豆包、Kimi、智谱和自定义兼容接口。",
    title: "先选提供商，再填模型与密钥",
    desc: "保存后新任务直接按这里的模型参数调用。",
    checklist: [
      "Base URL 建议保持默认，除非你明确在用代理。",
      "模型名必须和所购通道一致。",
    ],
    docs: [
      { label: "OpenAI API", href: "https://platform.openai.com/docs/api-reference" },
      { label: "Anthropic Messages API", href: "https://docs.anthropic.com/en/api/messages-examples" },
      { label: "Google Gemini API", href: "https://ai.google.dev/gemini-api/docs/text-generation" },
      { label: "DeepSeek API", href: "https://api-docs.deepseek.com/api/create-chat-completion" },
      { label: "阿里云百炼 OpenAI 兼容", href: "https://help.aliyun.com/zh/model-studio/openai-compatible-api" },
      { label: "火山引擎 Ark OpenAI 兼容", href: "https://www.volcengine.com/docs/82379/1298454" },
      { label: "智谱 OpenAI SDK 兼容", href: "https://bigmodel.cn/dev/howuse/model" },
      { label: "Moonshot API", href: "https://platform.moonshot.cn/docs/api-reference" },
    ],
  },
}

const activeTab = ref("login")
const forms = ref({
  llm: { enabled: false, provider: "openai", base_url: "", model: "", api_key: "" },
  payment: { provider: "wechatpay_v3", test_mode: true, notify_url: "" },
  billing: { aigc_rate: 1, dedup_rate: 2, rewrite_rate: 2, packages: cloneBillingPackages() },
  login: {
    sms_provider: "custom_webhook",
    sms_api_key: "",
    sms_gateway_url: "",
    sms_template_id: "",
    sms_sign_name: "",
    sms_sdk_app_id: "",
    sms_region: "ap-guangzhou",
    sms_aliyun_region_id: "cn-hangzhou",
    sms_access_key_id: "",
    sms_access_key_secret: "",
    debug_code_enabled: false,
    wechat_login_enabled: false,
    wechat_app_id: "",
    wechat_app_secret: "",
    wechat_redirect_uri: "",
  },
  referral: {
    register_inviter_credits: 500,
    register_invitee_bonus: 500,
    first_pay_ratio: 0.1,
    recurring_ratio: 0.05,
    ip_limit_24h: 3,
  },
})

const readinessMap = ref({})
const hintText = ref("")
const errorText = ref("")
const saving = ref(false)
const referralFirstPayPct = ref(10)
const referralRecurringPct = ref(5)

const currentTab = computed(() => tabs.find((tab) => tab.key === activeTab.value) || tabs[0])
const currentGuide = computed(() => guideMap[activeTab.value] || guideMap.login)
const isWechatPay = computed(() => ["wechat", "wechatpay_v3"].includes(forms.value.payment.provider))
const isAlipay = computed(() => forms.value.payment.provider === "alipay")
const paymentProviderUnsupported = computed(() => {
  const provider = String(forms.value.payment.provider || "")
  return Boolean(provider) && !paymentProviders.some((item) => item.value === provider)
})
const paymentNotifyPreview = computed(() => resolvePaymentNotifyPreview())

onMounted(async () => {
  await Promise.all([loadAll(), loadReadiness()])
})

function chipClass(status) {
  if (status === "ready") return "bg-[#e8f5ef] text-[#106c4f]"
  if (status === "error") return "bg-[#fff0ee] text-[#b24439]"
  return "bg-[#eef2f5] text-[#5e6c78]"
}

function readinessLabel(status) {
  if (status === "ready") return "已就绪"
  if (status === "error") return "需补齐"
  return "待确认"
}

async function loadAll() {
  await Promise.all(tabs.map((tab) => loadTab(tab.key)))
}

async function loadTab(category) {
  const data = await adminHttp.get(`/admin/configs/${category}`)
  forms.value[category] = data.value || {}
  if (category === "billing") {
    forms.value.billing = normalizeBillingForm(forms.value.billing)
  }
  if (category === "login") {
    forms.value.login.sms_region = forms.value.login.sms_region || "ap-guangzhou"
    forms.value.login.sms_aliyun_region_id = forms.value.login.sms_aliyun_region_id || "cn-hangzhou"
  }
  if (category === "referral") {
    referralFirstPayPct.value = Number(((forms.value.referral.first_pay_ratio || 0) * 100).toFixed(2))
    referralRecurringPct.value = Number(((forms.value.referral.recurring_ratio || 0) * 100).toFixed(2))
  }
}

async function loadReadiness() {
  const data = await adminHttp.get("/admin/configs/readiness")
  const map = {}
  for (const item of data.items || []) {
    map[item.category] = item
  }
  readinessMap.value = map
}

async function reloadCurrent() {
  await Promise.all([loadTab(activeTab.value), loadReadiness()])
  hintText.value = "已重新加载当前板块配置。"
  errorText.value = ""
}

function pickLlm(provider) {
  const current = llmPresets[forms.value.llm.provider] || { base_url: "", model: "" }
  const next = llmPresets[provider] || { base_url: "", model: "" }
  if (!forms.value.llm.base_url || forms.value.llm.base_url === current.base_url) {
    forms.value.llm.base_url = next.base_url
  }
  if (!forms.value.llm.model || forms.value.llm.model === current.model) {
    forms.value.llm.model = next.model
  }
  forms.value.llm.provider = provider
}

function validateCurrent() {
  if (activeTab.value === "billing") {
    const { aigc_rate, dedup_rate, rewrite_rate, packages } = normalizeBillingForm(forms.value.billing)
    if (!(aigc_rate > 0) || !(dedup_rate > 0) || !(rewrite_rate > 0)) {
      return "计费单价必须大于 0"
    }
    if (!Array.isArray(packages) || packages.length === 0) {
      return "至少需要配置 1 个套餐"
    }
    if (!packages.some((pkg) => pkg.enabled)) {
      return "至少需要启用 1 个套餐"
    }
    const names = new Set()
    for (const pkg of packages) {
      if (!pkg.name) return "套餐名称不能为空"
      if (names.has(pkg.name)) return `套餐名称重复：${pkg.name}`
      names.add(pkg.name)
      if (!(Number(pkg.price) > 0)) return `套餐 ${pkg.name} 价格必须大于 0`
      if (!(Number(pkg.credits) > 0)) return `套餐 ${pkg.name} 积分必须大于 0`
    }
  }
  if (activeTab.value === "referral") {
    if (referralFirstPayPct.value < 0 || referralFirstPayPct.value > 100) {
      return "首单返佣比例必须在 0~100%"
    }
    if (referralRecurringPct.value < 0 || referralRecurringPct.value > 100) {
      return "复购返佣比例必须在 0~100%"
    }
  }
  if (activeTab.value === "payment" && isWechatPay.value && forms.value.payment.api_v3_key && String(forms.value.payment.api_v3_key).length !== 32) {
    return "微信支付 APIv3 Key 必须是 32 位"
  }
  if (activeTab.value === "payment" && isAlipay.value && forms.value.payment.app_private_key_pem && !forms.value.payment.alipay_public_key) {
    return "支付宝已填写应用私钥时，需要同时填写支付宝公钥"
  }
  if (activeTab.value === "payment" && !forms.value.payment.test_mode && forms.value.payment.provider === "mock") {
    return "关闭联调模式后不能选择 mock"
  }
  return ""
}

function payloadFor(category) {
  const payload = { ...(forms.value[category] || {}) }
  if (category === "referral") {
    payload.first_pay_ratio = Number((Number(referralFirstPayPct.value || 0) / 100).toFixed(4))
    payload.recurring_ratio = Number((Number(referralRecurringPct.value || 0) / 100).toFixed(4))
  }
  if (category === "billing") {
    const normalized = normalizeBillingForm(payload)
    payload.packages = normalized.packages.map((pkg) => ({
      name: pkg.name,
      price: Number(pkg.price),
      credits: Number(pkg.credits),
      description: pkg.description,
      badge: pkg.badge,
      enabled: Boolean(pkg.enabled),
    }))
  }
  if (category === "payment" && payload.provider === "alipay" && payload.app_private_key_pem) {
    payload.api_key = payload.app_private_key_pem
  }
  return payload
}

function cloneBillingPackages(packages = defaultBillingPackages) {
  return (Array.isArray(packages) ? packages : defaultBillingPackages).map((pkg) => ({
    name: String(pkg?.name || "").trim(),
    price: Number(pkg?.price || 0),
    credits: Number(pkg?.credits || 0),
    description: String(pkg?.description || "").trim(),
    badge: String(pkg?.badge || "").trim(),
    enabled: pkg?.enabled !== false,
  }))
}

function normalizeBillingForm(raw) {
  const source = raw && typeof raw === "object" ? raw : {}
  return {
    aigc_rate: Number(source.aigc_rate) || 1,
    dedup_rate: Number(source.dedup_rate) || 2,
    rewrite_rate: Number(source.rewrite_rate) || 2,
    packages: cloneBillingPackages(source.packages),
  }
}

function addBillingPackage() {
  if (!Array.isArray(forms.value.billing.packages)) {
    forms.value.billing.packages = []
  }
  forms.value.billing.packages.push({
    name: "",
    price: 9.9,
    credits: 10000,
    description: "",
    badge: "",
    enabled: true,
  })
}

function removeBillingPackage(index) {
  if (!Array.isArray(forms.value.billing.packages)) {
    return
  }
  forms.value.billing.packages.splice(index, 1)
}

function resolvePaymentNotifyPreview() {
  const notify = String(forms.value.payment.notify_url || "").trim()
  const provider = String(forms.value.payment.provider || "").toLowerCase()
  if (!notify) return "未填写"
  let base = notify
  try {
    const parsed = new URL(notify)
    const path = parsed.pathname || "/"
    if (path === "/" || path === "") {
      if (provider === "alipay") {
        base = notify.replace(/\/+$/, "") + "/api/v1/billing/notify/alipay"
      } else {
        base = notify.replace(/\/+$/, "") + "/api/v1/billing/notify/wechatpay"
      }
    }
    return base
  } catch {
    return "回调地址格式不合法"
  }
}

async function saveCurrent() {
  const checkError = validateCurrent()
  if (checkError) {
    errorText.value = checkError
    return
  }
  saving.value = true
  hintText.value = ""
  errorText.value = ""
  try {
    await adminHttp.post(`/admin/configs/${activeTab.value}`, payloadFor(activeTab.value))
    await Promise.all([loadTab(activeTab.value), loadReadiness()])
    hintText.value = `${currentTab.value.label}已保存并生效。`
  } catch (error) {
    errorText.value = error.message || "保存失败"
  } finally {
    saving.value = false
  }
}
</script>

