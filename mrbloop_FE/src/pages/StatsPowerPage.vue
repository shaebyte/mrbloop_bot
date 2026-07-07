<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api/allianceClient'

const matrix = ref(null)
const loading = ref(false)

const filterDateFrom = ref(null)
const filterDateTo = ref(null)

const headers = computed(() => {
  if (!matrix.value) return []
  return [
    { title: 'Alias', key: 'alias', width: '140px' },
    ...matrix.value.dates.map((d) => ({
      title: d,
      key: d,
      sortable: false,
    })),
  ]
})

const items = computed(() => {
  if (!matrix.value) return []
  return matrix.value.members.map((m) => ({
    player_id: m.player_id,
    alias: m.alias,
    ...m.power,
  }))
})

async function fetchMatrix() {
  loading.value = true
  try {
    const { data } = await api.get('/stats/power-matrix', {
      params: {
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

defineExpose({ fetchMatrix })
</script>

<template>
  <div>
    <div class="d-flex ga-3 flex-wrap mt-3">
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
          v-for="d in matrix?.dates ?? []"
          #[`item.${d}`]="{ value }"
          :key="d"
        >
          <span v-if="value != null">{{ value.toLocaleString() }}</span>
          <span v-else class="text-medium-emphasis">—</span>
        </template>
      </v-data-table>
    </div>
  </div>
</template>

<style scoped>
:deep(.v-data-table th) {
  text-align: left;
  font-size: 0.9rem;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.6);
  padding: 8px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

:deep(.v-data-table td) {
  padding: 4px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.06);
}
</style>
