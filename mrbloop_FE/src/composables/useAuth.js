import { ref, computed } from 'vue'
import api from '../api/client'

const token = ref(localStorage.getItem('mod_token'))

export function useAuth() {
  const isMod = computed(() => !!token.value)

  async function login(password) {
    const { data } = await api.post('/auth/login', { password })
    token.value = data.token
    localStorage.setItem('mod_token', data.token)
  }

  function logout() {
    token.value = null
    localStorage.removeItem('mod_token')
  }

  return { isMod, login, logout }
}
