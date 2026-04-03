<template>
  <AdminShell title="管理员管理" subtitle="由超级管理员统一创建账号、配置权限、设置密码">
    <section v-if="!isSuperAdmin" class="scholar-panel scholar-panel--soft">
      <div class="scholar-panel__body">
        <h3 class="scholar-subtitle">仅超级管理员可访问</h3>
        <p class="scholar-lead">当前账号没有管理员管理权限，请使用超级管理员账号登录。</p>
      </div>
    </section>

    <template v-else>
      <section class="scholar-panel">
        <div class="scholar-panel__header">
          <div class="scholar-kicker">创建管理员</div>
          <h3 class="scholar-subtitle">新增普通管理员账号</h3>
        </div>
        <div class="scholar-panel__body">
          <div class="scholar-grid md:grid-cols-2">
            <label class="scholar-field">
              <span class="scholar-field__label">用户名</span>
              <input v-model.trim="createForm.username" class="scholar-input" placeholder="如: ops_editor" />
            </label>
            <label class="scholar-field">
              <span class="scholar-field__label">初始密码</span>
              <input v-model.trim="createForm.password" type="password" class="scholar-input" placeholder="至少8位" />
            </label>
          </div>

          <div class="scholar-inline-actions" style="margin-top: 16px">
            <label class="scholar-chip">
              <input v-model="createForm.is_active" type="checkbox" />
              账号启用
            </label>
          </div>

          <div class="scholar-grid md:grid-cols-2" style="margin-top: 16px">
            <article v-for="group in permissionGroups" :key="group.group" class="scholar-note">
              <div style="font-weight: 600; color: var(--ink)">{{ group.group }}</div>
              <div class="scholar-stack" style="margin-top: 10px">
                <label v-for="item in group.items" :key="item.key" class="scholar-chip" style="justify-content: flex-start">
                  <input :checked="createForm.permissions.includes(item.key)" type="checkbox" @change="toggleCreatePermission(item.key)" />
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
                  <th>最近登录</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rows" :key="row.id">
                  <td>{{ row.id }}</td>
                  <td>{{ row.username }}</td>
                  <td>{{ row.role }}</td>
                  <td>
                    <span class="scholar-badge" :class="row.is_active ? 'scholar-badge--success' : 'scholar-badge--danger'">
                      {{ row.is_active ? "启用" : "停用" }}
                    </span>
                  </td>
                  <td>{{ formatTime(row.last_login) }}</td>
                  <td>{{ formatTime(row.created_at) }}</td>
                  <td>
                    <div class="scholar-inline-actions">
                      <button class="scholar-button scholar-button--secondary" @click="openEdit(row)">编辑权限</button>
                      <button
                        class="scholar-button scholar-button--ghost"
                        :disabled="row.role === 'super_admin'"
                        @click="toggleStatus(row)"
                      >
                        {{ row.is_active ? "停用账号" : "启用账号" }}
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="rows.length === 0">
                  <td colspan="7">
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

          <div v-if="editing.role === 'super_admin'" class="scholar-note" style="margin-top: 16px">
            超级管理员拥有全量权限，不支持修改权限集。
          </div>

          <div v-else class="scholar-grid md:grid-cols-2" style="margin-top: 16px">
            <article v-for="group in permissionGroups" :key="group.group" class="scholar-note">
              <div style="font-weight: 600; color: var(--ink)">{{ group.group }}</div>
              <div class="scholar-stack" style="margin-top: 10px">
                <label v-for="item in group.items" :key="item.key" class="scholar-chip" style="justify-content: flex-start">
                  <input :checked="editPermissions.includes(item.key)" type="checkbox" @change="toggleEditPermission(item.key)" />
                  <span>{{ item.label }}</span>
                </label>
              </div>
            </article>
          </div>

          <div class="scholar-grid md:grid-cols-[1fr_auto]" style="margin-top: 16px">
            <label class="scholar-field">
              <span class="scholar-field__label">重置密码（至少8位）</span>
              <input v-model.trim="newPassword" type="password" class="scholar-input" placeholder="留空则不修改密码" />
            </label>
            <div class="scholar-inline-actions" style="align-self: end">
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

const rows = ref([])
const catalog = ref([])
const createForm = ref({
  username: "",
  password: "",
  is_active: true,
  permissions: [],
})
const editing = ref(null)
const editPermissions = ref([])
const newPassword = ref("")
const savingCreate = ref(false)
const savingEdit = ref(false)
const hintText = ref("")
const errorText = ref("")

const adminInfo = getAdminInfo()
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
  const data = await adminHttp.get("/admin/admin-users")
  rows.value = data.items || []
  catalog.value = data.permission_catalog || []
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
  savingCreate.value = true
  try {
    await adminHttp.post("/admin/admin-users", createForm.value)
    hintText.value = "管理员创建成功"
    createForm.value = {
      username: "",
      password: "",
      is_active: true,
      permissions: [],
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
  const targetStatus = !row.is_active
  const ok = window.confirm(targetStatus ? "确认启用该管理员账号？" : "确认停用该管理员账号？")
  if (!ok) {
    return
  }
  await adminHttp.post(`/admin/admin-users/${row.id}/status`, {
    is_active: targetStatus,
  })
  await loadAll()
}

function formatTime(value) {
  return value ? String(value).slice(0, 19).replace("T", " ") : "-"
}
</script>
