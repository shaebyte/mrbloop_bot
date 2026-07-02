import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('../views/HomeView.vue') },
    { path: '/mod/login', redirect: '/login' },
    { path: '/login', component: () => import('../views/LoginView.vue') },
    {
      path: '/mod',
      component: () => import('../views/ModDashboard.vue'),
      beforeEnter: () => {
        const { isAuthed, isAdmin } = useAuth()
        if (!isAuthed.value) return '/login'
        if (!isAdmin.value) return '/alliance'
      },
    },
    {
      path: '/alliance',
      component: () => import('../views/AllianceDashboard.vue'),
      beforeEnter: () => {
        const { isAuthed, isAdmin, isAlliance } = useAuth()
        if (!isAuthed.value) return '/login'
        if (!isAdmin.value && !isAlliance.value) return '/'
      },
    },
  ],
})

export default router
