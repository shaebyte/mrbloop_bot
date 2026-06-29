<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api/client'

const attempts = ref([])
const editing = ref(null)
const saveMsg = ref('')
const activeTab = ref('accounts')
const accStatus = ref('active')

// Accounts - data table server
const accounts = ref([])
const accTotal = ref(0)
const accLoading = ref(false)
const accSearch = ref('')
const accOptions = ref({ page: 1, itemsPerPage: 25 })

// Attempts - data table server
const attStatus = ref('all')
const attLoading = ref(false)
const attSearch = ref('')
const attOptions = ref({ page: 1, itemsPerPage: 25 })
const attTotal = ref(0)
const attempts_data = ref([])

const accHeaders = [
  { title: 'Player ID', key: 'player_id', width: '120px' },
  { title: 'Name', key: 'name', width: '140px' },
  { title: 'Status', key: 'blacklisted', width: '100px', sortable: false },
  { title: 'Info', key: 'comments', width: '140px', sortable: false },
  { title: '', key: 'actions', width: '140px', sortable: false },
]

const attHeaders = [
  { title: 'Player ID', key: 'player_id', width: '120px' },
  { title: 'Code', key: 'gift_code', width: '140px' },
  { title: 'Status', key: 'status', width: '100px', sortable: false },
  { title: 'Attempts', key: 'attempt_count', width: '80px', sortable: false },
  { title: 'Error', key: 'error_message', width: '140px', sortable: false },
  { title: 'Date', key: 'redeemed_at', width: '120px', sortable: false },
]

async function fetchAccounts({ page, itemsPerPage } = accOptions.value) {
  accLoading.value = true
  try {
    const { data } = await api.get('/accounts', {
      params: {
        page,
        limit: itemsPerPage,
        search: accSearch.value || undefined,
        status: accStatus.value,          // <-- add this
      },
    })
    accounts.value = data.items
    accTotal.value = data.total
  } catch (err) {
    console.error('fetchAccounts error:', err.response?.status, err.response?.data)
  } finally {
    accLoading.value = false
  }
}

async function fetchAttempts({ page, itemsPerPage } = attOptions.value) {
  attLoading.value = true
  try {
    const { data } = await api.get('/redeem-attempts', {
      params: {
        page,
        limit: itemsPerPage,
        search: attSearch.value || undefined,
        status: attStatus.value,
      },
    })
    attempts_data.value = data.items
    attTotal.value = data.total
  } catch (err) {
    console.error('fetchAttempts error:', err.response?.status, err.response?.data)
  } finally {
    attLoading.value = false
  }
}

onMounted(() => {
  fetchAttempts()
})

watch(accSearch, () => {
  accOptions.value = { ...accOptions.value, page: 1 }
  fetchAccounts({ ...accOptions.value, page: 1 })
})

watch(accStatus, () => {
  accOptions.value = { ...accOptions.value, page: 1 }
  fetchAccounts({ ...accOptions.value, page: 1 })
})

watch(attSearch, () => {
  attOptions.value = { ...attOptions.value, page: 1 }
  fetchAttempts({ ...attOptions.value, page: 1 })
})

watch(attStatus, () => {
  attOptions.value = { ...attOptions.value, page: 1 }
  fetchAttempts({ ...attOptions.value, page: 1 })
})

function startEdit(acc) {
  editing.value = { 
    player_id: acc.player_id, 
    name: acc.name, 
    comments: acc.comments ?? '',
    _original: { name: acc.name, comments: acc.comments ?? '' }
  }
}

function cancelEdit() {
  editing.value = null
}

function isDirty(item) {
  if (editing.value?.player_id !== item.player_id) return false
  return editing.value.name !== editing.value._original.name || 
         editing.value.comments !== editing.value._original.comments
}

async function saveEdit(acc) {
  await api.put(`/accounts/${acc.player_id}`, {
    name: editing.value.name,
    comments: editing.value.comments,
  })
  acc.name = editing.value.name
  acc.comments = editing.value.comments
  editing.value = null
  saveMsg.value = 'Successfully Saved'
  setTimeout(() => (saveMsg.value = ''), 2000)
}

async function toggleBlacklist(acc) {
  await api.put(`/accounts/${acc.player_id}`, { blacklisted: !acc.blacklisted })
  acc.blacklisted = !acc.blacklisted
}

</script>

<template>
  <v-tabs v-model="activeTab" color="pink-lighten-1">
    <v-tab value="accounts">
      <v-icon>mdi-account-group</v-icon>
    </v-tab>
    <v-tab value="attempts">
      <v-icon>mdi-ticket-confirmation</v-icon>
    </v-tab>
  </v-tabs>

  <v-tabs-window v-model="activeTab">

    <!-- ACCOUNTS TAB -->
    <v-tabs-window-item value="accounts">
      <v-card flat>
        <v-alert v-if="saveMsg" type="success" density="compact" class="ma-3">
          {{ saveMsg }}
        </v-alert>

        <template #text>
          <v-text-field 
            v-model="accSearch"
            label="Search by Player ID or Name…"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            hide-details
            single-line
          />
          <!-- Status filter -->
           <div class="d-flex justify-end mt-3">
            <v-btn-toggle 
              v-model="accStatus"
              mandatory
              density="compact"
              variant="outlined"
              class="mt-3"
              color="pink-lighten-1"
            >
              <v-btn value="active">Active</v-btn>
              <v-btn value="banned">Banned</v-btn>
              <v-btn value="all">All</v-btn>
            </v-btn-toggle>
          </div>
        </template>

        <div style="overflow-x: auto;">
        <v-data-table-server
          style="min-width: 600px;"
          :headers="accHeaders"
          :items="accounts"
          :items-length="accTotal"
          :loading="accLoading"
          :items-per-page="accOptions.itemsPerPage"
          @update:options="(opts) => { accOptions = opts; fetchAccounts(opts) }"
        >
          <template #item.name="{ item }">
            <span v-if="editing?.player_id !== item.player_id">{{ item.name }}</span>
            <v-text-field
              v-else
              v-model="editing.name"
              density="compact"
              hide-details
              variant="underlined"
              style="width: 120px"
            />
          </template>

          <template #item.blacklisted="{ item }">
            <span :style="{ color: item.blacklisted ? 'rgb(var(--v-theme-error))' : 'rgb(var(--v-theme-success))' }">
              {{ item.blacklisted ? 'Banned' : 'Active' }}
            </span>
          </template>

          <template #item.comments="{ item }">
            <span v-if="editing?.player_id !== item.player_id">{{ item.comments }}</span>
            <v-text-field
              v-else
              v-model="editing.comments"
              density="compact"
              hide-details
              variant="underlined"
              style="width: 140px"
            />
          </template>

          <template #item.actions="{ item }">
            <template v-if="editing?.player_id !== item.player_id">
              <!-- Niet in edit mode: ban/unban + pencil -->
              <v-btn
                :icon="item.blacklisted ? 'mdi-play' : 'mdi-stop'"
                :color="item.blacklisted ? 'success' : 'error'"
                size="small" variant="text"
                :title="item.blacklisted ? 'Unban' : 'Ban'"
                @click="toggleBlacklist(item)"
              />
              <v-btn
                icon="mdi-pencil"
                size="small" variant="text"
                title="Edit"
                @click="startEdit(item)"
              />
            </template>
            <template v-else-if="!isDirty(item)">
              <!-- Edit mode, niets gewijzigd: ban/unban + cancel -->
              <v-btn
                :icon="item.blacklisted ? 'mdi-play' : 'mdi-stop'"
                :color="item.blacklisted ? 'success' : 'error'"
                size="small" variant="text"
                :title="item.blacklisted ? 'Unban' : 'Ban'"
                @click="toggleBlacklist(item)"
              />
              <v-btn
                icon="mdi-close-circle-outline"
                size="small" color="warning" variant="text"
                title="Cancel"
                @click="cancelEdit()"
              />
            </template>
            <template v-else>
              <!-- Edit mode + dirty: alleen save + cancel -->
              <v-btn
                icon="mdi-content-save"
                size="small" color="primary" variant="text"
                title="Save"
                @click="saveEdit(item)"
              />
              <v-btn
                icon="mdi-close-circle-outline"
                size="small" color="warning" variant="text"
                title="Cancel"
                @click="cancelEdit()"
              />
            </template>
          </template>
        </v-data-table-server>
        </div>
      </v-card>
    </v-tabs-window-item>

    <!-- ATTEMPTS TAB -->
    <v-tabs-window-item value="attempts">
      <v-card flat>
        <template #text>
          <v-text-field
            v-model="attSearch"
            label="Search by Player ID or code…"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            hide-details
            single-line
          />
          <div class="d-flex justify-end mt-3">
            <v-btn-toggle
              v-model="attStatus"
              mandatory
              density="compact"
              variant="outlined"
              class="mt-3"
              color="pink-lighten-1"
            >
              <v-btn value="success">Success</v-btn>
              <v-btn value="failed">Failed</v-btn>
              <v-btn value="all">All</v-btn>
            </v-btn-toggle>
          </div>
        </template>

        <div style="overflow-x: auto;">
          <v-data-table-server
            style="min-width: 600px;"
            :headers="attHeaders"
            :items="attempts_data"
            :items-length="attTotal"
            :loading="attLoading"
            :items-per-page="attOptions.itemsPerPage"
            @update:options="(opts) => { attOptions = opts; fetchAttempts(opts) }"
          >
            <template #item.status="{ item }">
              <span :style="{ color: item.status === 'success' ? 'rgb(var(--v-theme-success))' : 'rgb(var(--v-theme-error))' }">
                {{ item.status }}
              </span>
            </template>
          </v-data-table-server>
        </div>
      </v-card>
    </v-tabs-window-item>
  </v-tabs-window>
</template>