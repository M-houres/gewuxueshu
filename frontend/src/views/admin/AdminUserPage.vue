<template>
  <AdminShell title="用户管理" subtitle="查询用户、封禁状态与积分调整。">
    <section class="scholar-panel">
      <div class="scholar-panel__header">
        <div class="scholar-kicker">用户搜索</div>
        <h3 class="scholar-subtitle">检索与筛选</h3>
      </div>

      <div class="scholar-panel__body">
        <div class="scholar-inline-actions">
          <input v-model.trim="keyword" class="scholar-input" style="max-width: 320px" placeholder="按手机号搜索" />
          <div class="scholar-inline-actions">
            <button
              v-for="item in statusFilters"
              :key="item.value || 'all'"
              type="button"
              class="scholar-chip"
              :class="{ 'is-active': activeStatusFilter === item.value }"
              @click="activeStatusFilter = item.value"
            >
              {{ item.label }}
            </button>
          </div>
          <button class="scholar-button" type="button" @click="loadData">查询</button>
        </div>

        <div class="scholar-grid md:grid-cols-3" style="margin-top: 18px">
          <div class="scholar-stat">
            <div class="scholar-stat__label">当前加载用户</div>
            <div class="scholar-stat__value" style="font-size: 26px">{{ rows.length }}</div>
          </div>
          <div class="scholar-stat">
            <div class="scholar-stat__label">正常用户</div>
            <div class="scholar-stat__value" style="font-size: 26px; color: var(--success)">{{ activeCount }}</div>
          </div>
          <div class="scholar-stat">
            <div class="scholar-stat__label">封禁用户</div>
            <div class="scholar-stat__value" style="font-size: 26px; color: var(--danger)">{{ bannedCount }}</div>
          </div>
        </div>

        <div class="overflow-x-auto" style="margin-top: 18px">
          <table class="scholar-table">
            <thead>
              <tr>
                <th>用户 ID</th>
                <th>手机号</th>
                <th>昵称</th>
                <th>积分</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in displayRows" :key="row.id">
                <td>{{ row.id }}</td>
                <td>{{ row.phone }}</td>
                <td>{{ row.nickname }}</td>
                <td>{{ row.credits }}</td>
                <td>
                  <span class="scholar-badge" :class="row.is_banned ? 'scholar-badge--danger' : 'scholar-badge--success'">
                    {{ row.is_banned ? "已封禁" : "正常" }}
                  </span>
                </td>
                <td>{{ formatTime(row.created_at) }}</td>
                <td>
                  <div class="scholar-inline-actions">
                    <button class="scholar-button scholar-button--secondary" type="button" @click="goDetail(row)">
                      查看详情
                    </button>
                    <button v-if="canManageUsers" class="scholar-button scholar-button--ghost" type="button" @click="toggleBan(row)">
                      {{ row.is_banned ? "解封" : "封禁" }}
                    </button>
                    <button v-if="canManageUsers" class="scholar-button" type="button" @click="openAdjust(row)">
                      调整积分
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="displayRows.length === 0">
                <td colspan="7">
                  <div class="scholar-empty">暂无用户数据</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section v-if="editing && canManageUsers" class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <div class="scholar-kicker">积分调整</div>
        <h3 class="scholar-subtitle">调整用户积分：{{ editing.phone }}</h3>
        <div class="scholar-grid md:grid-cols-3" style="margin-top: 18px">
          <input v-model.number="delta" class="scholar-input" placeholder="输入正负积分" />
          <input v-model.trim="reason" class="scholar-input" placeholder="调整原因" />
          <button class="scholar-button" type="button" @click="submitAdjust">确认调整</button>
        </div>
        <p v-if="hintText" class="scholar-note scholar-note--success" style="margin-top: 18px">{{ hintText }}</p>
        <p v-if="errorText" class="scholar-note scholar-note--danger" style="margin-top: 18px">{{ errorText }}</p>
      </div>
    </section>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"
import { adminHasPermission } from "../../lib/session"

const router = useRouter()
const rows = ref([])
const keyword = ref("")
const activeStatusFilter = ref("")
const editing = ref(null)
const delta = ref(0)
const reason = ref("")
const hintText = ref("")
const errorText = ref("")

const canManageUsers = computed(() => adminHasPermission("users:manage"))
const statusFilters = [
  { value: "", label: "全部状态" },
  { value: "active", label: "正常" },
  { value: "banned", label: "已封禁" },
]
const displayRows = computed(() => {
  if (!activeStatusFilter.value) return rows.value
  if (activeStatusFilter.value === "active") return rows.value.filter((row) => !row.is_banned)
  return rows.value.filter((row) => row.is_banned)
})
const activeCount = computed(() => rows.value.filter((row) => !row.is_banned).length)
const bannedCount = computed(() => rows.value.filter((row) => row.is_banned).length)

onMounted(loadData)

async function loadData() {
  const data = await adminHttp.get("/admin/users", {
    params: { page: 1, page_size: 50, q: keyword.value || undefined },
  })
  rows.value = data.items || []
}

function openAdjust(row) {
  editing.value = row
  delta.value = 0
  reason.value = ""
  hintText.value = ""
  errorText.value = ""
}

async function submitAdjust() {
  if (!editing.value) return
  if (!delta.value) {
    errorText.value = "调整值不能为 0"
    return
  }
  if (!reason.value) {
    errorText.value = "请输入调整原因"
    return
  }
  errorText.value = ""
  const data = await adminHttp.post(`/admin/users/${editing.value.id}/adjust-credits`, {
    delta: delta.value,
    reason: reason.value,
  })
  hintText.value = `已调整成功，当前积分 ${data.credits}`
  await loadData()
}

function goDetail(row) {
  router.push(`/admin/users/${row.id}`)
}

async function toggleBan(row) {
  const target = !row.is_banned
  const confirmed = window.confirm(target ? "确认封禁该用户吗？" : "确认解封该用户吗？")
  if (!confirmed) {
    return
  }
  await adminHttp.post(`/admin/users/${row.id}/ban`, { is_banned: target })
  await loadData()
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}
</script>
