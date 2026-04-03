import { createRouter, createWebHistory } from 'vue-router'

import { resolveAdminRedirect, resolveUserRedirect } from '../lib/redirect'
import { adminHasPermission, getAdminInfo, getAdminToken, getUserToken } from '../lib/session'

const AdminLoginPage = () => import('../views/admin/AdminLoginPage.vue')
const AdminOrderPage = () => import('../views/admin/AdminOrderPage.vue')
const AdminReferralPage = () => import('../views/admin/AdminReferralPage.vue')
const AdminTaskPage = () => import('../views/admin/AdminTaskPage.vue')
const AdminUserPage = () => import('../views/admin/AdminUserPage.vue')
const AdminUserDetailPage = () => import('../views/admin/AdminUserDetailPage.vue')
const AdminDashboardPage = () => import('../views/admin/AdminDashboardPage.vue')
const AdminAlgoPackagePage = () => import('../views/admin/AdminAlgoPackagePage.vue')
const AdminConfigPage = () => import('../views/admin/AdminConfigPage.vue')
const AdminLogsPage = () => import('../views/admin/AdminLogsPage.vue')
const AdminAdminUsersPage = () => import('../views/admin/AdminAdminUsersPage.vue')
const LoginPage = () => import('../views/user/LoginPage.vue')
const RegisterPage = () => import('../views/user/RegisterPage.vue')
const UserBuyPage = () => import('../views/user/UserBuyPage.vue')
const UserProfilePage = () => import('../views/user/UserProfilePage.vue')
const UserDetectPage = () => import('../views/user/UserDetectPage.vue')
const UserReferralPage = () => import('../views/user/UserReferralPage.vue')
const UserRewritePage = () => import('../views/user/UserRewritePage.vue')
const UserDedupPage = () => import('../views/user/UserDedupPage.vue')

const adminEntryRoutes = [
  { path: '/admin/dashboard', permission: 'dashboard:view' },
  { path: '/admin/users', permission: 'users:view' },
  { path: '/admin/tasks', permission: 'tasks:view' },
  { path: '/admin/orders', permission: 'orders:view' },
  { path: '/admin/referrals', permission: 'referrals:view' },
  { path: '/admin/logs', permission: 'logs:view' },
  { path: '/admin/algo-packages', permission: 'algo:view' },
  { path: '/admin/configs', permission: 'configs:view' },
  { path: '/admin/admin-users', permission: 'admins:view' },
]

function firstAccessibleAdminRoute() {
  for (const item of adminEntryRoutes) {
    if (adminHasPermission(item.permission)) {
      return item.path
    }
  }
  return '/admin/login'
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/app/detect' },
    { path: '/login', component: LoginPage },
    { path: '/register', component: RegisterPage },
    { path: '/detect', redirect: '/app/detect' },
    { path: '/dedup', redirect: '/app/dedup' },
    { path: '/rewrite', redirect: '/app/rewrite' },
    { path: '/history', redirect: '/app/profile?tab=history' },
    { path: '/buy', redirect: '/app/buy' },
    { path: '/credits', redirect: '/app/profile?tab=credits' },
    { path: '/profile', redirect: '/app/profile' },
    { path: '/referral', redirect: '/app/referral' },
    { path: '/app/history', redirect: '/app/profile?tab=history' },
    { path: '/app/credits', redirect: '/app/profile?tab=credits' },
    { path: '/app/detect', component: UserDetectPage, meta: { auth: 'user', title: 'AIGC检测' } },
    { path: '/app/dedup', component: UserDedupPage, meta: { auth: 'user', title: '降重复率' } },
    { path: '/app/rewrite', component: UserRewritePage, meta: { auth: 'user', title: '降AIGC率' } },
    { path: '/app/referral', component: UserReferralPage, meta: { auth: 'user', title: '推广福利' } },
    { path: '/app/buy', component: UserBuyPage, meta: { auth: 'user', title: '购买积分' } },
    { path: '/app/profile', component: UserProfilePage, meta: { auth: 'user', title: '个人中心' } },
    { path: '/admin', redirect: '/admin/dashboard' },
    { path: '/admin/login', component: AdminLoginPage },
    { path: '/admin/dashboard', component: AdminDashboardPage, meta: { auth: 'admin', title: '后台总览', adminPermission: 'dashboard:view' } },
    { path: '/admin/users', component: AdminUserPage, meta: { auth: 'admin', title: '用户管理', adminPermission: 'users:view' } },
    { path: '/admin/users/:id', component: AdminUserDetailPage, meta: { auth: 'admin', title: '用户详情', adminPermission: 'users:view' } },
    { path: '/admin/tasks', component: AdminTaskPage, meta: { auth: 'admin', title: '任务管理', adminPermission: 'tasks:view' } },
    { path: '/admin/orders', component: AdminOrderPage, meta: { auth: 'admin', title: '订单管理', adminPermission: 'orders:view' } },
    { path: '/admin/algo-packages', component: AdminAlgoPackagePage, meta: { auth: 'admin', title: '算法包管理', adminPermission: 'algo:view' } },
    { path: '/admin/referrals', component: AdminReferralPage, meta: { auth: 'admin', title: '推广管理', adminPermission: 'referrals:view' } },
    { path: '/admin/configs', component: AdminConfigPage, meta: { auth: 'admin', title: '配置中心', adminPermission: 'configs:view' } },
    { path: '/admin/logs', component: AdminLogsPage, meta: { auth: 'admin', title: '系统日志', adminPermission: 'logs:view' } },
    { path: '/admin/admin-users', component: AdminAdminUsersPage, meta: { auth: 'admin', title: '管理员管理', adminPermission: 'admins:view' } },
  ],
})

router.beforeEach((to) => {
  if ((to.path === '/login' || to.path === '/register') && getUserToken()) {
    return resolveUserRedirect(to.query.redirect, '/app/detect')
  }
  if (to.path === '/admin/login' && getAdminToken()) {
    const fallback = firstAccessibleAdminRoute()
    return resolveAdminRedirect(to.query.redirect, fallback)
  }
  if (to.meta.auth === 'admin' && !getAdminToken()) {
    const redirect = encodeURIComponent(to.fullPath || '/admin/dashboard')
    return `/admin/login?redirect=${redirect}`
  }
  if (to.meta.auth === 'admin') {
    const admin = getAdminInfo()
    if (!admin) {
      return '/admin/login'
    }
    const requiredPermission = to.meta.adminPermission
    if (requiredPermission && !adminHasPermission(requiredPermission)) {
      const fallback = firstAccessibleAdminRoute()
      return fallback === '/admin/login' ? '/admin/login' : fallback
    }
  }
  return true
})

export default router
