<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const username = ref('')
const password = ref('')
const error = ref('')
const router = useRouter()
const { login, isAdmin } = useAuth()

async function submit() {
  error.value = ''
  try {
    await login(username.value, password.value)
    router.push(isAdmin.value ? '/mod' : '/alliance')
  } catch {
    error.value = 'Wrong username or password.'
  }
}
</script>

<template>
  <v-container>
    <v-row justify="center" class="pt-4">
      <v-col>
        <v-card rounded="xl" elevation="3">
          <v-card-text class="pl-10 pr-10">
            <h2 class="headline_two mb-4 text-center">Login</h2>
            <v-container class="py-1 mb-4">
              <v-text-field
                label="Username"
                v-model="username"
                density="comfortable"
                class="mb-4"
                @keyup.enter="submit"
                variant="outlined"
                hide-details
              />
              <v-text-field
                label="Password"
                v-model="password"
                type="password"
                density="comfortable"
                class="mb-4"
                @keyup.enter="submit"
                variant="outlined"
                hide-details
              />
              <v-btn
                block
                rounded="lg"
                size="large"
                variant="tonal"
                class="btn"
                color="#18a4ff"
                @click="submit"
              >Login</v-btn>
              <v-row v-if="error" no-gutters class="mt-2">
                <v-col>
                  <span class="msg-err">{{ error }}</span>
                </v-col>
              </v-row>
            </v-container>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.headline_two {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 32px;
  letter-spacing: 2px;
  line-height: 1;
}
.btn {
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.2px;
  text-transform: none;
  transition: transform 0.15s, box-shadow 0.2s;
}
.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.14) !important;
}
</style>
