<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/allianceClient'
import { EVENT_TYPES, LEGIONS } from '../api/allianceConstants'

const stats = ref(null)
const loading = ref(false)

const filterEventType = ref(null)
const filterLegion = ref(null)
const filterDateFrom = ref(null)
const filterDateTo = ref(null)

const detail = ref(null)
const detailOpen = ref(false)

const headers = [
  { title: 'Alias', key: 'alias', width: '140px' },
  { title: 'Player ID', key: 'player_id', width: '120px' },
  { title: 'Attended', key: 'attended', width: '90px' },
  { title: 'Total events', key: 'total_events', width: '100px' },
  { title: '%', key: 'percentage', width: '80px' },
]

async function fetchStats() {
  loading.value = true
  try {
    const { data } = await api.get('/stats/attendance', {
      params: {
        event_type: filterEventType.value || undefined,
        legion: filterLegion.value || undefined,
        date_from: filterDateFrom.value || undefined,
        date_to: filterDateTo.value || undefined,
      },
    })
    stats.value = data
  } catch (err) {
    console.error('fetchStats error:', err.response?.status, err.response?.data)
  } finally {
    loading.value = false
  }
}

async function openMember(row) {
  const { data } = await api.get(`/stats/members/${row.player_id}`)
  detail.value = data
  detailOpen.value = true
}

onMounted(fetchStats)
</script>

<template>
  <v-card flat>
    <template #title>
      <span class="d-block ml-1 mt-3 mb-3 text-blue-darken-2">Statistics</span>
    </template>

    <template #text>
      <div class="d-flex ga-3 flex-wrap">
        <v-select
          v-model="filterEventType"
          :items="EVENT_TYPES"
          label="Event type"
          variant="outlined"
          clearable
          hide-details
          style="flex: 1 1 0; min-width: 160px"
          @update:model-value="fetchStats"
        />
        <v-select
          v-model="filterLegion"
          :items="LEGIONS"
          label="Legion"
          variant="outlined"
          clearable
          hide-details
          style="flex: 1 1 0; min-width: 160px"
          @update:model-value="fetchStats"
        />
        <v-text-field
          v-model="filterDateFrom"
          type="date"
          label="From"
          variant="outlined"
          hide-details
          style="flex: 1 1 0; min-width: 160px"
          @update:model-value="fetchStats"
        />
        <v-text-field
          v-model="filterDateTo"
          type="date"
          label="To"
          variant="outlined"
          hide-details
          style="flex: 1 1 0; min-width: 160px"
          @update:model-value="fetchStats"
        />
      </div>
    </template>

    <p v-if="stats" class="text-medium-emphasis px-4">
      {{ stats.total_events }} events in Total.
    </p>

    <div style="overflow-x: auto;">
      <v-data-table
        style="min-width: 500px;"
        :headers="headers"
        :items="stats?.members ?? []"
        :loading="loading"
        @click:row="(_, { item }) => openMember(item)"
      />
    </div>

    <v-dialog v-model="detailOpen" max-width="480">
      <v-card v-if="detail">
        <v-card-title>{{ detail.alias }} ({{ detail.player_id }})</v-card-title>
        <v-card-text>
          <p class="mb-2">Attended {{ detail.attended_total }} events total.</p>
          <p class="mb-2" v-for="(count, type) in detail.by_event_type" :key="type">
            {{ type }}: {{ count }}
          </p>
          <v-list density="compact">
            <v-list-item v-for="e in detail.events" :key="e.event_id">
              {{ e.event_type }} — {{ e.legion }} — {{ e.event_date }}
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="detailOpen = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>
