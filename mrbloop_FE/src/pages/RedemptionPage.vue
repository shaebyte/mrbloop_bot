<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api/client'

const attStatus = ref('all')
const attLoading = ref(false)
const attSearch = ref('')
const attOptions = ref({ page: 1, itemsPerPage: 25 })
const attTotal = ref(0)
const attempts_data = ref([])

const attHeaders = [
  { title: 'Player ID', key: 'player_id', width: '120px' },
  { title: 'Code', key: 'gift_code', width: '140px' },
  { title: 'Status', key: 'status', width: '100px', sortable: false },
  { title: 'Attempts', key: 'attempt_count', width: '80px', sortable: false },
  { title: 'Error', key: 'error_message', width: '140px', sortable: false },
  { title: 'Date', key: 'redeemed_at', width: '120px', sortable: false },
]

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

watch(attSearch, () => {
  attOptions.value = { ...attOptions.value, page: 1 }
  fetchAttempts({ ...attOptions.value, page: 1 })
})

watch(attStatus, () => {
  attOptions.value = { ...attOptions.value, page: 1 }
  fetchAttempts({ ...attOptions.value, page: 1 })
})
</script>

<template>
  <v-card flat>
    <template #title>
      <span class="d-block ml-1 mt-3 mb-3 text-color">Redemption</span>
    </template>

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
          color="text-color"
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
</template>

<style scoped>
.text-color {
  color: #fc3dab;
}
</style>