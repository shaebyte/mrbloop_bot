import axios from 'axios'

const alliance = axios.create({ baseURL: `${import.meta.env.VITE_API_URL}/alliance` })

alliance.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('auth_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export default alliance
