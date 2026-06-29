import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'

import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'

const vuetify = createVuetify({
  icons: {
    defaultSet: 'mdi',
  },
})

createApp(App).use(router).use(vuetify).mount('#app')
