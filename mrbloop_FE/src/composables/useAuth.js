import { ref, computed } from 'vue'
import api from '../api/client'

const token = ref(localStorage.getItem('auth_token'))

function decodeRole(rawToken) {
  try {
    const payload = rawToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(payload))
  } catch {
    return null
  }
}

export function useAuth() {
  const isAuthed = computed(() => !!token.value)
  const role = computed(() => (token.value ? decodeRole(token.value)?.role ?? null : null))
  const isAdmin = computed(() => role.value === 'admin')
  const isAlliance = computed(() => role.value === 'alliance')

  async function login(username, password) {
    const { data } = await api.post('/auth/login', { username, password })
    token.value = data.token
    localStorage.setItem('auth_token', data.token)
  }

  function logout() {
    token.value = null
    localStorage.removeItem('auth_token')
  }

  return { isAuthed, role, isAdmin, isAlliance, login, logout }
}
