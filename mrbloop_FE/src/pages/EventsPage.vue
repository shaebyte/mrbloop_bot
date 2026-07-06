<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/allianceClient'
import { EVENT_TYPES, LEGIONS } from '../api/allianceConstants'

const events = ref([])
const loading = ref(false)
const errorMsg = ref('')

const filterEventType = ref(null)
const filterLegion = ref(null)

const headers = [
  { title: 'Date', key: 'event_date', width: '110px' },
  { title: 'Type', key: 'event_type', width: '160px' },
  { title: 'Legion', key: 'legion', width: '100px' },
  { title: 'Attended', key: 'total_attendees', width: '110px' },
  { title: 'Listed', key: 'listed_attendees', width: '100px' },
  { title: '', key: 'actions', width: '60px', sortable: false },
]

const detail = ref(null)
const detailOpen = ref(false)

const members = ref([])
const addAlias = ref(null)

async function fetchMembers() {
  const { data } = await api.get('/members')
  members.value = data
}

async function fetchEvents() {
  loading.value = true
  try {
    const { data } = await api.get('/events', {
      params: {
        event_type: filterEventType.value || undefined,
        legion: filterLegion.value || undefined,
      },
    })
    events.value = data.map((e) => ({ ...e, listed_attendees: e.attendee_count }))
  } catch (err) {
    console.error('fetchEvents error:', err.response?.status, err.response?.data)
  } finally {
    loading.value = false
  }
}

async function openEvent(event) {
  const { data } = await api.get(`/events/${event.event_id}`)
  detail.value = data
  detailOpen.value = true
  if (!members.value.length) await fetchMembers()
}

async function deleteEvent(event) {
  if (!confirm(`Delete event ${event.event_type} (${event.event_date})?`)) return
  await api.delete(`/events/${event.event_id}`)
  events.value = events.value.filter((e) => e.event_id !== event.event_id)
}

async function addAttendee() {
  errorMsg.value = ''
  const playerId = addAlias.value
  if (!playerId) return
  try {
    await api.post(`/events/${detail.value.event_id}/attendance`, { player_id: playerId })
    addAlias.value = null
    await openEvent(detail.value)
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Could not add attendee'
  }
}

async function removeAttendee(playerId) {
  await api.delete(`/events/${detail.value.event_id}/attendance/${playerId}`)
  await openEvent(detail.value)
}

onMounted(fetchEvents)

defineExpose({ fetchEvents })
</script>

<template>
  <v-card flat>
    <template #title>
      <span class="d-block ml-1 mt-3 mb-3 bloop-blue">Events</span>
    </template>

    <v-alert v-if="errorMsg" type="error" density="compact" closable class="ma-3" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>

    <template #text>
      <div class="d-flex ga-3">
        <v-select
          v-model="filterEventType"
          :items="EVENT_TYPES"
          label="Event type"
          variant="outlined"
          clearable
          hide-details
          style="flex: 1 1 0; min-width: 160px"
          @update:model-value="fetchEvents"
        />
        <v-select
          v-model="filterLegion"
          :items="LEGIONS"
          label="Legion"
          variant="outlined"
          clearable
          hide-details
          style="flex: 1 1 0; min-width: 160px"
          @update:model-value="fetchEvents"
        />
      </div>
    </template>

    <div style="overflow-x: auto;">
      <v-data-table
        style="min-width: 500px;"
        :headers="headers"
        :items="events"
        :loading="loading"
      >
        <template #item.actions="{ item }">
          <v-btn icon="mdi-eye" size="small" variant="text" title="Open" @click="openEvent(item)" />
          <v-btn icon="mdi-delete" size="small" color="error" variant="text" title="Delete" @click="deleteEvent(item)" />
        </template>
      </v-data-table>
    </div>

    <v-dialog v-model="detailOpen" max-width="520">
      <v-card v-if="detail">
        <v-card-title class="mt-3 ml-2">{{ detail.event_type }} • {{ detail.legion }} • {{ detail.event_date }}</v-card-title>
        <v-card-subtitle class="ml-2 text-grey">Attended players: {{ detail.total_attendees }}</v-card-subtitle>
        <v-card-text>
          <div class="d-flex ga-2 mb-8">
            <v-autocomplete
              v-model="addAlias"
              :items="members"
              item-title="alias"
              item-value="player_id"
              label="Add players (alias)"
              variant="outlined"
              density="compact"
              hide-details
              @keyup.enter="addAttendee"
            />
            <v-btn color="blue-darken-2" @click="addAttendee">Add</v-btn>
          </div>

          <p class="mb-0 ml-1 text-grey" style="font-size: 0.875rem">Listed players: {{ detail.attendees?.length ?? 0 }}</p>
          <v-list density="compact" style="max-height: 320px; overflow-y: auto">
            <v-list-item v-for="a in detail.attendees" :key="a.player_id">
              <template #append>
                <v-btn icon="mdi-close" size="x-small" variant="text" @click="removeAttendee(a.player_id)" />
              </template>
              {{ a.alias ?? a.player_id }} ({{ a.player_id }})
            </v-list-item>
            <v-list-item v-if="!detail.attendees?.length">No attendees yet.</v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<style scoped>
.bloop-blue {
  color: #18a4ff;
}
</style>