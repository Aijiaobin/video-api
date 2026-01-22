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
          path: 'roles',
          name: 'Roles',
          component: () => import('@/views/Roles.vue'),
          meta: { title: '角色权限' }
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

  // 未登录用户访问需要认证的页面，跳转到登录页
  if (to.meta.requiresAuth !== false && !userStore.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 已登录用户访问登录页，根据用户类型智能重定向
  if (to.path === '/login' && userStore.isLoggedIn) {
    // 管理员跳转到仪表盘，普通用户和VIP跳转到分享管理
    const redirectPath = userStore.isAdmin ? '/dashboard' : '/shares'
    next(redirectPath)
    return
  }

  // 页面级权限检查：非管理员用户访问管理员专属页面时重定向
  if (userStore.isLoggedIn && !userStore.isAdmin) {
    const adminOnlyPages = ['/dashboard', '/users', '/roles', '/versions', '/announcements', '/configs']
    if (adminOnlyPages.includes(to.path)) {
      // 非管理员访问管理员页面，重定向到分享管理
      next('/shares')
      return
    }
  }

  next()
})

export default router

