<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api/allianceClient'
import { EVENT_TYPES } from '../api/allianceConstants'

const ALL = 'ALL'
const EVENT_TYPE_OPTIONS = [ALL, ...EVENT_TYPES]
const EVENT_ABBR = { 'Swordland': 'SL', 'Tri-Alliance Clash': 'TAC' }
const LEGION_COLOR = { 'Legion 1': 'primary', 'Legion 2': 'secondary' }

function daysAgo(days) {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}

const matrix = ref(null)
const loading = ref(false)

const filterEventType = ref(ALL)
const filterDateFrom = ref(daysAgo(60))
const filterDateTo = ref(null)

const headers = computed(() => {
  if (!matrix.value) return []
  return [
    { title: 'Alias', key: 'alias', width: '140px' },
    { title: 'Attended', key: 'attended', width: '90px' },
    { title: 'Total events', key: 'total_events', width: '100px' },
    ...matrix.value.sessions.map((s) => ({
      title: `${EVENT_ABBR[s.event_type] ?? s.event_type} ${s.event_date}`,
      key: s.event_type + '|' + s.event_date,
      sortable: false,
    })),
  ]
})

const items = computed(() => {
  if (!matrix.value) return []
  const total = matrix.value.sessions.length
  return matrix.value.members.map((m) => ({
    player_id: m.player_id,
    alias: m.alias,
    attended: Object.values(m.attendance).filter(Boolean).length,
    total_events: total,
    ...m.attendance,
  }))
})

async function fetchMatrix() {
  loading.value = true
  try {
    const { data } = await api.get('/stats/matrix', {
      params: {
        event_type: filterEventType.value === ALL ? undefined : filterEventType.value,
        date_from: filterDateFrom.value || undefined,
        date_to: filterDateTo.value || undefined,
      },
    })
    matrix.value = data
  } catch (err) {
    console.error('fetchMatrix error:', err.response?.status, err.response?.data)
  } finally {
    loading.value = false
  }
}

onMounted(fetchMatrix)
</script>

<template>
  <div>
    <div class="d-flex ga-3 flex-wrap mt-3">
      <v-select
        v-model="filterEventType"
        :items="EVENT_TYPE_OPTIONS"
        label="Event type"
        variant="outlined"
        hide-details
        style="flex: 1 1 0; min-width: 160px"
        @update:model-value="fetchMatrix"
      />
      <v-text-field
        v-model="filterDateFrom"
        type="date"
        label="From"
        variant="outlined"
        hide-details
        style="flex: 1 1 0; min-width: 160px"
        @update:model-value="fetchMatrix"
      />
      <v-text-field
        v-model="filterDateTo"
        type="date"
        label="To"
        variant="outlined"
        hide-details
        style="flex: 1 1 0; min-width: 160px"
        @update:model-value="fetchMatrix"
      />
    </div>

    <div style="overflow-x: auto;" class="mt-4">
      <v-data-table
        style="min-width: 500px;"
        :headers="headers"
        :items="items"
        :loading="loading"
      >
        <template
          v-for="s in matrix?.sessions ?? []"
          #[`item.${s.event_type}|${s.event_date}`]="{ value }"
          :key="s.event_type + s.event_date"
        >
          <v-chip v-if="value" size="small" :color="LEGION_COLOR[value] ?? 'primary'" variant="tonal">
            {{ value }}
          </v-chip>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
      </v-data-table>
    </div>
  </div>
</template>
