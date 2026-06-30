<script setup>
import { ref, onMounted, computed } from 'vue'
import giftImg from '../assets/gift.png'
import mrbloopImg from '../assets/mrbloop-webp.webp'
import api from '../api/client'

const searchId = ref('')
const found = ref(null)
const isBlacklisted = ref(false)
const showError = ref(false)
const isFound = computed(() => !!found.value && found.value !== false && !isNewlyCreated.value)

const validating = ref(false)
const validated = ref(null)
const validateMsg = ref('')

const creating = ref(false)
const createAlert = ref(false)
const createMsg = ref('')
const isNewlyCreated = ref(false)

const codes = ref([])
const codesLoading = ref(true)

onMounted(async () => {
  new Image().src = mrbloopImg
  try {
    const { data } = await api.get('/gift-codes/live')
    codes.value = data.data.giftCodes
  } catch (e) {
    console.error('Failed to load gift codes', e)
  } finally {
    codesLoading.value = false
  }
})

function reset() {
  found.value = null
  validated.value = null
  validateMsg.value = ''
  isBlacklisted.value = false
  createAlert.value = false
  createMsg.value = ''
  showError.value = false
  isNewlyCreated.value = false
}

async function search() {
  reset()
  if (!searchId.value.trim()) {
    showError.value = true
    return
  }
  found.value = false

  try {
    const { data } = await api.get(`/accounts/${searchId.value.trim()}`)
    if (data.blacklisted) {
      isBlacklisted.value = true
    } else {
      found.value = data
    }
  } catch {
    await validatePlayer()
  }
}

const stoveLvLabel = (lv) => {
  const map = { 35: 'TG1', 40: 'TG2', 45: 'TG3', 50: 'TG4', 55: 'TG5', 60: 'TG6', 65: 'TG7', 70: 'TG8' }
  return map[lv] ?? `Level ${lv}`
}

async function validatePlayer() {
  validated.value = null
  validateMsg.value = ''
  validating.value = true

  try {
    const { data } = await api.get(`/accounts/validate/${searchId.value.trim()}`)
    validated.value = data
  } catch (e) {
    validateMsg.value = 'Player not found in game.'
  } finally {
    validating.value = false
  }
}

async function create() {
  if (!validated.value) return
  creating.value = true
  createMsg.value = ''

  try {
    await api.post('/accounts', {
      player_id: searchId.value.trim(),
      name: validated.value.nickname,
    })
    createMsg.value = "You've been added to the list."
    createAlert.value = true
    isNewlyCreated.value = true
    found.value = {
      player_id: searchId.value.trim(),
      name: validated.value.nickname,
    }
    validated.value = null
  } catch (e) {
    createMsg.value = e.response?.data?.detail ?? 'Something went wrong.'
  } finally {
    creating.value = false
  }
}

async function copyCode(code) {
  navigator.clipboard.writeText(code)
}
</script>

<template>
  <v-container>
    <!-- Subscribe -->
    <v-row justify="center" no-gutters>
      <v-col cols="12">
        <v-card class="subscribe-card" rounded="xl" elevation="3">
          <v-card-text class="text-center pa-10">

            <!-- Gift -->
            <div class="gift-wrap mb-0">
              <div class="gift-glow"></div>
              <img
                :src="giftImg"
                alt="Gift"
                class="gift"
              />
            </div>

            <h1 class="headline mb-6">HEY YOU!</h1>

            <p class="subtext mb-8">
              Let <span class="highlight-name">mrbloop</span> redeem the<br />
              Kingshot gift codes for you.
            </p>

            <!-- Player ID input -->
            <v-text-field
              v-model="searchId"
              label="Enter your player ID"
              variant="outlined"
              rounded="lg"
              density="comfortable"
              inputmode="numeric"
              :error-messages="showError ? 'Please enter a valid player ID.' : ''"
              class="mb-2"
              @keyup.enter="search"
              @input="searchId = searchId.replace(/\D/g, ''); reset()"
              hide-details="auto"
            />

            <!-- Search button -->
            <v-btn
              v-show="!validated && !isBlacklisted && !createAlert" block
              rounded="lg"
              size="large"
              variant="tonal"
              class="btn mt-4"
              :color="isFound ? 'success' : '#18a4ff'"
              :loading="validating"
              @click="search"
            >
              <v-icon v-if="isFound" icon="mdi-check" start></v-icon>
              {{ isFound ? "You're already on the list!" : "Let's do this!" }}
            </v-btn>

            <!-- Found in DB -->
            <v-row v-if="isFound && !createAlert" no-gutters align="center" justify="center" class="mt-10">
              <v-col cols="auto" class="d-flex align-center mr-4">
                <v-icon icon="mdi-identifier" size="x-large" color="#fc3dab" class="mr-2" />
                {{ found.player_id }}
              </v-col>
              <v-col cols="auto" class="d-flex align-center">
                <v-icon icon="mdi-account-outline" size="large" color="#fc3dab" class="mr-2" />
                {{ found.name }}
              </v-col>
            </v-row>

            <!-- Success alert after create -->
            <v-row v-if="createAlert" no-gutters class="mt-5">
              <v-col>
                <v-alert
                  type="success"
                  density="compact"
                  closable
                  @click:close="createAlert = false"
                >
                  {{ createMsg }}
                </v-alert>
                  <p v-if="isNewlyCreated" class="foottext text-left mt-5 px-2 text-center">
                    You're on the list now for automatic redemption of future gift codes! 
                    <span class="highlight-name">mrbloop</span> will not redeem current available giftcodes (see here below).
                  </p>
              </v-col>
            </v-row>

            <!-- Blacklisted message -->
            <v-row v-if="isBlacklisted" no-gutters align="center" class="mt-10">
              <!-- Left column: Image -->
              <v-col cols="3">
                <v-img
                  :src="mrbloopImg"
                  alt="Mr Bloopbot"
                  max-width="80"
                  contain
                />
              </v-col>

              <!-- Right column: Text -->
              <v-col cols="9" class="d-flex flex-column">
                <span class="subtext text-left d-block" style="color: #18a4ff;">
                  Well well, looks like you've been granted exclusive access to our elite club: Exclusion.
                </span>
              </v-col>
            </v-row>

            <!-- Validate error -->
            <v-row v-if="validateMsg" no-gutters align="center" class="mt-6">
              <v-col cols="auto" class="d-flex align-center">
                <v-icon icon="mdi-alert-circle" size="large" color="red" class="mr-2" />
                <span class="msg-err">{{ validateMsg }}</span>
              </v-col>
            </v-row>

            <!-- Validated: show game info + confirm -->
            <template v-if="validated">
              <v-row no-gutters align="center" class="mt-10 " >
                <v-col cols="5" class="d-flex justify-end align-center pe-4">
                  <v-avatar size="48">
                    <v-img :src="validated.avatar_image" />
                  </v-avatar>
                </v-col>
                <v-col class="text-start" >
                  <div class="text-h6 font-weight-medium">{{ validated.nickname }}</div>
                  <div class="text-caption text-medium-emphasis">
                    Kingdom {{ validated.kid }} · {{ stoveLvLabel(validated.stove_lv) }}
                  </div>
                </v-col>
              </v-row>

              <v-row no-gutters class="mt-6">
                <v-col cols="12">
                  <v-btn
                    block
                    rounded="lg"
                    size="large"
                    variant="tonal"
                    color="success"
                    class="btn"
                    :loading="creating"
                    @click="create"
                  >
                    Confirm
                  </v-btn>
                </v-col>
                <v-col cols="12" class="mt-2">
                  <v-btn
                    block
                    rounded="lg"
                    size="large"
                    variant="tonal"
                    color="#999999"
                    class="btn"
                    @click="validated = null"
                  >
                    Cancel
                  </v-btn>
                </v-col>
              </v-row>

              <p v-if="createMsg && !createAlert" class="msg-err mt-2">{{ createMsg }}</p>
            </template>

          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Gift Codes -->
    <v-row justify="center" class="pt-4">
      <v-col>
        <v-card rounded="xl" elevation="3">
          <v-card-text class="pa-1">
            <h2 class="headline_two mb-4 text-center">Gift Codes</h2>
            <p v-if="codesLoading" class="text-center">Loading...</p>
            <template v-else-if="codes.length">
              <v-container class="py-1 mb-5">
                <v-row v-for="c in codes" :key="c.id" align="center" no-gutters class="mb-1">
                  <v-col cols="7" class="text-right">
                    {{ c.code }}
                  </v-col>
                  <v-col cols="5" class="pl-2">
                    <v-btn
                      icon
                      size="small"
                      variant="text"
                      @click="copyCode(c.code)"
                    >
                      <v-icon icon="mdi-content-copy" size="x-small" color="grey-lighten-1"/>
                    </v-btn>
                  </v-col>
                </v-row>
                <v-row no-gutters align="center" class="mt-5">
                  <v-col cols="12" class="text-center">
                    <span class="foottext text-caption text-medium-emphasis">Redeem gift codes at</span>
                    <v-btn
                      href="https://ks-giftcode.centurygame.com/"
                      target="_blank"
                      rel="noopener noreferrer"
                      variant="text"
                      size="small"
                      color="#18a4ff"
                    >
                      Kingshot
                    </v-btn>
                  </v-col>
                </v-row>
              </v-container>
            </template>
            <p v-else class="text-center">No gift codes found.</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500&display=swap');

.subscribe-card {
  animation: fadeUp 0.5s ease both;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.gift-wrap {
  position: relative;
  display: inline-block;
}

.gift-glow {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(251, 146, 60, 0.18) 0%, transparent 70%);
}

.gift {
  width: 80px;
  height: 80px;
  object-fit: contain;
  filter: drop-shadow(0 6px 16px rgba(251, 146, 60, 0.3));
  animation: floating 3s ease-in-out infinite;
}

@keyframes floating {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-7px); }
}

.headline {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 64px;
  letter-spacing: 2px;
  line-height: 1;
}

.headline_two {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 32px;
  letter-spacing: 2px;
  line-height: 1;
}

.subtext {
  font-size: 15px;
  color: #666;
  line-height: 1.6;
}
.foottext {
  font-size: 12px;
  color: #666;
  line-height: 1.6;
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

.highlight-name {
  color: #fc3dab; /* Replace this with your desired color (e.g. 'red', 'blue', or a hex code) */
  font-weight: bold; /* Optional: also makes the name bold right away */
}
</style>