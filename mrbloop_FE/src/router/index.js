import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('../views/HomeView.vue') },
    { path: '/mod/login', component: () => import('../views/ModLogin.vue') },
    {
      path: '/mod',
      component: () => import('../views/ModDashboard.vue'),
      beforeEnter: () => {
        if (!localStorage.getItem('mod_token')) return '/mod/login'
      },
    },
  ],
})

export default router
