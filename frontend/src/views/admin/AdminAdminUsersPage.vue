<template>
  <AdminShell title="管理员管理" subtitle="由超级管理员统一创建账号、配置权限、设置密码">
    <section v-if="!isSuperAdmin" class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <h3 class="scholar-subtitle">仅超级管理员可访问</h3>
        <p class="scholar-lead">当前账号没有管理员管理权限，请使用超级管理员账号登录。</p>
      </div>
    </section>

    <template v-else>
      <section class="scholar-grid md:grid-cols-3">
        <article class="scholar-stat">
          <div class="scholar-stat__label">管理员总数</div>
          <div class="scholar-stat__value" style="font-size: 26px">{{ summary.total }}</div>
        </article>
        <article class="scholar-stat">
          <div class="scholar-stat__label">启用账号</div>
          <div class="scholar-stat__value" style="font-size: 26px; color: var(--success)">{{ summary.active }}</div>
        </article>
        <article class="scholar-stat">
          <div class="scholar-stat__label">停用账号</div>
          <div class="scholar-stat__value" style="font-size: 26px; color: var(--danger)">{{ summary.inactive }}</div>
        </article>
      </section>

      <section class="scholar-panel">
        <div class="scholar-panel__header">
          <div class="scholar-kicker">创建管理员</div>
          <h3 class="scholar-subtitle">新增普通管理员账号</h3>
        </div>
        <div class="scholar-panel__body">
          <div class="scholar-grid md:grid-cols-[1fr_1fr_auto]">
            <label class="scholar-field">
              <span class="scholar-field__label">用户名</span>
              <input v-model.trim="createForm.username" class="scholar-input" placeholder="如: ops_editor" />
            </label>
            <label class="scholar-field">
              <span class="scholar-field__label">初始密码</span>
              <input v-model.trim="createForm.password" type="text" class="scholar-input" placeholder="至少8位" />
            </label>
            <div class="scholar-inline-actions" style="align-self: end">
              <button class="scholar-button scholar-button--secondary" type="button" @click="fillCreateRandomPassword">
                生成密码
              </button>
            </div>
          </div>

          <div class="scholar-inline-actions" style="margin-top: 16px">
            <label class="scholar-chip">
              <input v-model="createForm.is_active" type="checkbox" />
              账号启用
            </label>
            <button class="scholar-button scholar-button--ghost" type="button" @click="setCreateDefaultPermissions">
              默认权限
            </button>
            <button class="scholar-button scholar-button--ghost" type="button" @click="selectAllCreatePermissions">
              全选权限
            </button>
            <button class="scholar-button scholar-button--ghost" type="button" @click="clearCreatePermissions">
              清空权限
            </button>
          </div>

          <div class="scholar-grid md:grid-cols-2" style="margin-top: 16px">
            <article v-for="group in permissionGroups" :key="group.group" class="scholar-note">
              <div style="font-weight: 600; color: var(--ink)">{{ group.group }}</div>
              <div class="scholar-stack" style="margin-top: 10px">
                <label
                  v-for="item in group.items"
                  :key="item.key"
                  class="scholar-chip"
                  style="justify-content: flex-start"
                >
                  <input
                    :checked="createForm.permissions.includes(item.key)"
                    type="checkbox"
                    @change="toggleCreatePermission(item.key)"
                  />
                  <span>{{ item.label }}</span>
                </label>
              </div>
            </article>
          </div>

          <div class="scholar-inline-actions" style="margin-top: 18px">
            <button class="scholar-button" :disabled="savingCreate" @click="createAdmin">
              {{ savingCreate ? "创建中..." : "创建管理员" }}
            </button>
            <button class="scholar-button scholar-button--secondary" @click="loadAll">刷新列表</button>
          </div>
          <p v-if="hintText" class="scholar-note scholar-note--success" style="margin-top: 14px">{{ hintText }}</p>
          <p v-if="errorText" class="scholar-note scholar-note--danger" style="margin-top: 14px">{{ errorText }}</p>
        </div>
      </section>

      <section class="scholar-panel scholar-panel--soft">
        <div class="scholar-panel__body">
          <div class="scholar-grid md:grid-cols-[1.2fr_0.8fr_0.8fr_auto]">
            <label class="scholar-field">
              <span class="scholar-field__label">搜索用户名</span>
              <input v-model.trim="filters.keyword" class="scholar-input" placeholder="输入用户名关键字" />
            </label>
            <label class="scholar-field">
              <span class="scholar-field__label">角色</span>
              <select v-model="filters.role" class="scholar-select">
                <option value="">全部角色</option>
                <option value="super_admin">超级管理员</option>
                <option value="operator">普通管理员</option>
              </select>
            </label>
            <label class="scholar-field">
              <span class="scholar-field__label">账号状态</span>
              <select v-model="filters.status" class="scholar-select">
                <option value="all">全部状态</option>
                <option value="active">仅启用</option>
                <option value="inactive">仅停用</option>
              </select>
            </label>
            <div class="scholar-inline-actions" style="align-self: end">
              <button class="scholar-button scholar-button--secondary" type="button" @click="loadAll">查询</button>
              <button class="scholar-button scholar-button--ghost" type="button" @click="resetFilters">重置</button>
            </div>
          </div>
        </div>
      </section>

      <section class="scholar-panel">
        <div class="scholar-panel__header">
          <div class="scholar-kicker">管理员列表</div>
          <h3 class="scholar-subtitle">权限、状态与密码重置</h3>
        </div>
        <div class="scholar-panel__body">
          <div class="overflow-x-auto">
            <table class="scholar-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>用户名</th>
                  <th>角色</th>
                  <th>状态</th>
                  <th>权限摘要</th>
                  <th>最近登录</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rows" :key="row.id">
                  <td>{{ row.id }}</td>
                  <td>
                    <div class="text-sm font-semibold">{{ row.username }}</div>
                    <div v-if="row.id === currentAdminId" class="text-xs text-[var(--ink-faint)]">当前登录账号</div>
                  </td>
                  <td>{{ row.role }}</td>
                  <td>
                    <span class="scholar-badge" :class="row.is_active ? 'scholar-badge--success' : 'scholar-badge--danger'">
                      {{ row.is_active ? "启用" : "停用" }}
                    </span>
                  </td>
                  <td>
                    <div class="text-xs leading-6 text-[var(--ink-soft)]" :title="fullPermissionText(row)">
                      {{ permissionBrief(row) }}
                    </div>
                  </td>
                  <td>{{ formatTime(row.last_login) }}</td>
                  <td>{{ formatTime(row.created_at) }}</td>
                  <td>
                    <div class="scholar-inline-actions">
                      <button class="scholar-button scholar-button--secondary" @click="openEdit(row)">编辑</button>
                      <button
                        class="scholar-button scholar-button--ghost"
                        :disabled="row.role === 'super_admin' || row.id === currentAdminId"
                        @click="toggleStatus(row)"
                      >
                        {{ row.is_active ? "停用账号" : "启用账号" }}
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="rows.length === 0">
                  <td colspan="8">
                    <div class="scholar-empty">暂无管理员数据</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section v-if="editing" class="scholar-panel scholar-panel--soft">
        <div class="scholar-panel__body">
          <div class="scholar-kicker">编辑管理员</div>
          <h3 class="scholar-subtitle">{{ editing.username }}</h3>

          <div class="scholar-inline-actions" style="margin-top: 12px">
            <span class="scholar-pill">角色：{{ editing.role }}</span>
            <span class="scholar-pill">状态：{{ editing.is_active ? "启用" : "停用" }}</span>
            <button
              v-if="editing.role !== 'super_admin'"
              class="scholar-button scholar-button--ghost"
              type="button"
              @click="setEditDefaultPermissions"
            >
              默认权限
            </button>
            <button
              v-if="editing.role !== 'super_admin'"
              class="scholar-button scholar-button--ghost"
              type="button"
              @click="selectAllEditPermissions"
            >
              全选权限
            </button>
            <button
              v-if="editing.role !== 'super_admin'"
              class="scholar-button scholar-button--ghost"
              type="button"
              @click="clearEditPermissions"
            >
              清空权限
            </button>
          </div>

          <div v-if="editing.role === 'super_admin'" class="scholar-note" style="margin-top: 16px">
            超级管理员拥有全量权限，不支持修改权限集。
          </div>

          <div v-else class="scholar-grid md:grid-cols-2" style="margin-top: 16px">
            <article v-for="group in permissionGroups" :key="group.group" class="scholar-note">
              <div style="font-weight: 600; color: var(--ink)">{{ group.group }}</div>
              <div class="scholar-stack" style="margin-top: 10px">
                <label
                  v-for="item in group.items"
                  :key="item.key"
                  class="scholar-chip"
                  style="justify-content: flex-start"
                >
                  <input
                    :checked="editPermissions.includes(item.key)"
                    type="checkbox"
                    @change="toggleEditPermission(item.key)"
                  />
                  <span>{{ item.label }}</span>
                </label>
              </div>
            </article>
          </div>

          <div class="scholar-grid md:grid-cols-[1fr_auto]" style="margin-top: 16px">
            <label class="scholar-field">
              <span class="scholar-field__label">重置密码（至少8位）</span>
              <input v-model.trim="newPassword" type="text" class="scholar-input" placeholder="留空则不修改密码" />
            </label>
            <div class="scholar-inline-actions" style="align-self: end">
              <button class="scholar-button scholar-button--secondary" type="button" @click="fillEditRandomPassword">
                生成密码
              </button>
              <button class="scholar-button" :disabled="savingEdit" @click="saveEdit">
                {{ savingEdit ? "保存中..." : "保存设置" }}
              </button>
              <button class="scholar-button scholar-button--secondary" @click="closeEdit">取消</button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </AdminShell>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"

import AdminShell from "../../components/AdminShell.vue"
import { adminHttp } from "../../lib/http"
import { getAdminInfo } from "../../lib/session"

const DEFAULT_OPERATOR_PERMISSIONS = [
  "dashboard:view",
  "users:view",
  "users:manage",
  "tasks:view",
  "orders:view",
  "orders:refund",
  "referrals:view",
  "logs:view",
  "credits:view",
  "algo:view",
]

const rows = ref([])
const catalog = ref([])
const summary = ref({ total: 0, active: 0, inactive: 0 })
const filters = ref({
  keyword: "",
  role: "",
  status: "all",
})
const createForm = ref({
  username: "",
  password: "",
  is_active: true,
  permissions: [...DEFAULT_OPERATOR_PERMISSIONS],
})
const editing = ref(null)
const editPermissions = ref([])
const newPassword = ref("")
const savingCreate = ref(false)
const savingEdit = ref(false)
const hintText = ref("")
const errorText = ref("")

const adminInfo = getAdminInfo()
const currentAdminId = Number(adminInfo?.id || 0)
const isSuperAdmin = computed(() => adminInfo?.role === "super_admin")
const permissionGroups = computed(() => {
  const grouped = new Map()
  for (const item of catalog.value) {
    const group = item.group || "其他"
    if (!grouped.has(group)) {
      grouped.set(group, [])
    }
    grouped.get(group).push(item)
  }
  return Array.from(grouped.entries()).map(([group, items]) => ({ group, items }))
})

onMounted(loadAll)

async function loadAll() {
  if (!isSuperAdmin.value) {
    return
  }
  try {
    const params = {}
    if (filters.value.keyword) {
      params.keyword = filters.value.keyword
    }
    if (filters.value.role) {
      params.role = filters.value.role
    }
    if (filters.value.status === "active") {
      params.is_active = true
    } else if (filters.value.status === "inactive") {
      params.is_active = false
    }
    const data = await adminHttp.get("/admin/admin-users", { params })
    rows.value = data.items || []
    catalog.value = data.permission_catalog || []
    summary.value = data.summary || calcSummary(rows.value)
  } catch (error) {
    errorText.value = error.message || "加载管理员列表失败"
  }
}

function calcSummary(items) {
  const total = items.length
  const active = items.filter((item) => item.is_active).length
  return {
    total,
    active,
    inactive: Math.max(total - active, 0),
  }
}

function toggleCreatePermission(key) {
  const current = new Set(createForm.value.permissions || [])
  if (current.has(key)) {
    current.delete(key)
  } else {
    current.add(key)
  }
  createForm.value.permissions = Array.from(current)
}

function toggleEditPermission(key) {
  const current = new Set(editPermissions.value || [])
  if (current.has(key)) {
    current.delete(key)
  } else {
    current.add(key)
  }
  editPermissions.value = Array.from(current)
}

function setCreateDefaultPermissions() {
  createForm.value.permissions = [...DEFAULT_OPERATOR_PERMISSIONS]
}

function selectAllCreatePermissions() {
  createForm.value.permissions = catalog.value.map((item) => item.key)
}

function clearCreatePermissions() {
  createForm.value.permissions = []
}

function setEditDefaultPermissions() {
  editPermissions.value = [...DEFAULT_OPERATOR_PERMISSIONS]
}

function selectAllEditPermissions() {
  editPermissions.value = catalog.value.map((item) => item.key)
}

function clearEditPermissions() {
  editPermissions.value = []
}

function fillCreateRandomPassword() {
  createForm.value.password = randomPassword()
}

function fillEditRandomPassword() {
  newPassword.value = randomPassword()
}

function randomPassword() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*"
  let out = ""
  for (let i = 0; i < 14; i += 1) {
    out += chars[Math.floor(Math.random() * chars.length)]
  }
  return out
}

async function createAdmin() {
  hintText.value = ""
  errorText.value = ""
  if (!createForm.value.username) {
    errorText.value = "请输入管理员用户名"
    return
  }
  if (!createForm.value.password || createForm.value.password.length < 8) {
    errorText.value = "初始密码至少 8 位"
    return
  }
  if (!Array.isArray(createForm.value.permissions) || createForm.value.permissions.length === 0) {
    errorText.value = "至少选择 1 项权限"
    return
  }
  savingCreate.value = true
  try {
    await adminHttp.post("/admin/admin-users", createForm.value)
    hintText.value = "管理员创建成功"
    createForm.value = {
      username: "",
      password: "",
      is_active: true,
      permissions: [...DEFAULT_OPERATOR_PERMISSIONS],
    }
    await loadAll()
  } catch (error) {
    errorText.value = error.message || "创建管理员失败"
  } finally {
    savingCreate.value = false
  }
}

function openEdit(row) {
  editing.value = row
  editPermissions.value = Array.isArray(row.permissions) ? [...row.permissions] : []
  newPassword.value = ""
  hintText.value = ""
  errorText.value = ""
}

function closeEdit() {
  editing.value = null
  editPermissions.value = []
  newPassword.value = ""
}

async function saveEdit() {
  if (!editing.value) {
    return
  }
  savingEdit.value = true
  hintText.value = ""
  errorText.value = ""
  try {
    if (editing.value.role !== "super_admin") {
      if (!Array.isArray(editPermissions.value) || editPermissions.value.length === 0) {
        throw new Error("至少选择 1 项权限")
      }
      await adminHttp.post(`/admin/admin-users/${editing.value.id}/permissions`, {
        permissions: editPermissions.value,
      })
    }
    if (newPassword.value) {
      if (newPassword.value.length < 8) {
        throw new Error("新密码至少 8 位")
      }
      await adminHttp.post(`/admin/admin-users/${editing.value.id}/password`, {
        password: newPassword.value,
      })
    }
    hintText.value = "管理员设置已更新"
    await loadAll()
    closeEdit()
  } catch (error) {
    errorText.value = error.message || "保存失败"
  } finally {
    savingEdit.value = false
  }
}

async function toggleStatus(row) {
  if (row.role === "super_admin") {
    return
  }
  if (row.id === currentAdminId) {
    errorText.value = "当前登录管理员账号不可自行停用"
    return
  }
  const targetStatus = !row.is_active
  const ok = window.confirm(targetStatus ? "确认启用该管理员账号？" : "确认停用该管理员账号？")
  if (!ok) {
    return
  }
  try {
    await adminHttp.post(`/admin/admin-users/${row.id}/status`, {
      is_active: targetStatus,
    })
    hintText.value = targetStatus ? "管理员账号已启用" : "管理员账号已停用"
    await loadAll()
  } catch (error) {
    errorText.value = error.message || "更新管理员状态失败"
  }
}

function resetFilters() {
  filters.value = {
    keyword: "",
    role: "",
    status: "all",
  }
  loadAll()
}

function permissionBrief(row) {
  if (row.role === "super_admin") {
    return "全量权限"
  }
  const list = Array.isArray(row.permissions) ? row.permissions : []
  if (list.length === 0) {
    return "未配置"
  }
  const head = list.slice(0, 3).join(" / ")
  return list.length > 3 ? `${list.length} 项: ${head} ...` : `${list.length} 项: ${head}`
}

function fullPermissionText(row) {
  if (row.role === "super_admin") {
    return "全量权限"
  }
  const list = Array.isArray(row.permissions) ? row.permissions : []
  return list.join(", ")
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}
</script>
