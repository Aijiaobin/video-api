import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/dashboard'
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '仪表盘' }
        },
        {
          path: 'users',
          name: 'Users',
          component: () => import('@/views/Users.vue'),
          meta: { title: '用户管理' }
        },
        {
          path: 'versions',
          name: 'Versions',
          component: () => import('@/views/Versions.vue'),
          meta: { title: '版本管理' }
        },
        {
          path: 'shares',
          name: 'Shares',
          component: () => import('@/views/Shares.vue'),
          meta: { title: '分享管理' }
        },
        {
          path: 'announcements',
          name: 'Announcements',
          component: () => import('@/views/Announcements.vue'),
          meta: { title: '公告管理' }
        },
        {
          path: 'configs',
          name: 'Configs',
          component: () => import('@/views/Configs.vue'),
          meta: { title: '系统配置' }
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard'
    }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth !== false && !userStore.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router

