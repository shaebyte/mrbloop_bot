<script setup>
import { ref, watch } from 'vue'
import StatsEventsPage from './StatsEventsPage.vue'
import StatsPowerPage from './StatsPowerPage.vue'

const activeSubTab = ref('events')

const statsEventsRef = ref(null)
const statsPowerRef = ref(null)

watch(activeSubTab, (tab) => {
  if (tab === 'events') statsEventsRef.value?.fetchMatrix()
  if (tab === 'power') statsPowerRef.value?.fetchMatrix()
})
</script>

<template>
  <v-card flat>
    <template #title>
      <span class="d-block ml-1 mt-3 mb-3 text-blue-darken-2">Statistics</span>
    </template>

    <template #text>
      <v-tabs v-model="activeSubTab" color="blue-lighten-1" class="mb-4">
        <v-tab value="events">Events</v-tab>
        <v-tab value="power">Power</v-tab>
      </v-tabs>

      <v-tabs-window v-model="activeSubTab">
        <v-tabs-window-item value="events">
          <StatsEventsPage ref="statsEventsRef" />
        </v-tabs-window-item>

        <v-tabs-window-item value="power">
          <StatsPowerPage ref="statsPowerRef" />
        </v-tabs-window-item>
      </v-tabs-window>
    </template>
  </v-card>
</template>
