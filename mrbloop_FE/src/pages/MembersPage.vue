<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/allianceClient'

const members = ref([])
const loading = ref(false)
const search = ref('')
const saveMsg = ref('')
const errorMsg = ref('')

const editing = ref(null)
const creating = ref(false)
const newMember = ref({ player_id: '', alias: '', alliance_name: '' })

const refreshing = ref(false)
const refreshStatus = ref(null)
const lastRefresh = ref(null)
let refreshPoll = null

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatRelative(value) {
  if (!value) return 'never'
  const hours = (Date.now() - new Date(value).getTime()) / 3_600_000
  if (hours < 1) return 'less than an hour ago'
  if (hours < 24) return `${Math.floor(hours)} hours ago`
  return `${Math.floor(hours / 24)} days ago`
}

function staleColor(value) {
  if (!value) return 'warning'
  const hours = (Date.now() - new Date(value).getTime()) / 3_600_000
  return hours >= 24 ? 'warning' : 'grey-darken-1'
}

const headers = [
  { title: 'Player ID', key: 'player_id', width: '120px' },
  { title: 'Alias', key: 'alias', width: '140px' },
  { title: 'In-game name', key: 'ingame_name', width: '160px' },
  { title: 'Alliance', key: 'alliance_name', width: '120px' },
  { title: 'Server', key: 'server', width: '80px' },
  { title: 'Updated (UTC)', key: 'updated_at', width: '140px' },
  { title: '', key: 'actions', width: '110px', sortable: false },
]

function filteredMembers() {
  if (!search.value) return members.value
  const q = search.value.toLowerCase()
  return members.value.filter((m) =>
    m.player_id.toLowerCase().includes(q) ||
    m.alias?.toLowerCase().includes(q) ||
    m.ingame_name?.toLowerCase().includes(q)
  )
}

async function fetchMembers() {
  loading.value = true
  try {
    const { data } = await api.get('/members')
    members.value = data
  } catch (err) {
    console.error('fetchMembers error:', err.response?.status, err.response?.data)
  } finally {
    loading.value = false
  }
}

function startEdit(member) {
  editing.value = {
    player_id: member.player_id,
    alias: member.alias,
    alliance_name: member.alliance_name,
    _original: { alias: member.alias, alliance_name: member.alliance_name },
  }
}

function cancelEdit() {
  editing.value = null
}

function isDirty(item) {
  if (editing.value?.player_id !== item.player_id) return false
  return editing.value.alias !== editing.value._original.alias ||
    editing.value.alliance_name !== editing.value._original.alliance_name
}

async function saveEdit(member) {
  errorMsg.value = ''
  try {
    const { data } = await api.patch(`/members/${member.player_id}`, {
      alias: editing.value.alias,
      alliance_name: editing.value.alliance_name,
    })
    Object.assign(member, data)
    editing.value = null
    saveMsg.value = 'Successfully saved'
    setTimeout(() => (saveMsg.value = ''), 2000)
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Save failed'
  }
}

async function deleteMember(member) {
  if (!confirm(`Delete ${member.alias} (${member.player_id})?`)) return
  await api.delete(`/members/${member.player_id}`)
  members.value = members.value.filter((m) => m.player_id !== member.player_id)
}

async function createMember() {
  errorMsg.value = ''
  try {
    const { data } = await api.post('/members', newMember.value)
    members.value.push(data)
    creating.value = false
    newMember.value = { player_id: '', alias: '', alliance_name: '' }
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Create failed'
  }
}

async function fetchRefreshStatus() {
  const { data } = await api.get('/members/refresh-names/status')
  refreshStatus.value = data
  lastRefresh.value = data.last_refresh?.finished_at ?? null
}

async function startRefresh() {
  errorMsg.value = ''
  try {
    await api.post('/members/refresh-names')
    refreshing.value = true
    pollRefreshStatus()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Could not start refresh'
  }
}

function pollRefreshStatus() {
  clearInterval(refreshPoll)
  refreshPoll = setInterval(async () => {
    const { data } = await api.get('/members/refresh-names/status')
    refreshStatus.value = data
    if (!data.running) {
      clearInterval(refreshPoll)
      refreshing.value = false
      lastRefresh.value = data.last_refresh?.finished_at ?? null
      fetchMembers()
    }
  }, 1500)
}

onMounted(() => {
  fetchMembers()
  fetchRefreshStatus()
})

defineExpose({ fetchMembers, fetchRefreshStatus })
</script>

<template>
  <v-card flat>
    <template #title>
      <span class="d-block ml-1 mt-3 mb-3 bloop-blue">Members</span>
    </template>
    <v-alert v-if="saveMsg" type="success" density="compact" closable class="ma-3" @click:close="saveMsg = ''">{{ saveMsg }}</v-alert>
    <v-alert v-if="errorMsg" type="error" density="compact" closable class="ma-3" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>

    <template #text>
      <v-text-field
        v-model="search"
        label="Search by Player ID, alias or in-game name…"
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        hide-details
        single-line
      />

      <div class="d-flex ga-3 align-center justify-end mt-6">
        <v-chip :color="staleColor(lastRefresh)" variant="tonal" size="small">
          <v-icon start size="small">mdi-clock-outline</v-icon>
          Refreshed names: {{ formatRelative(lastRefresh) }}
        </v-chip>
        <span v-if="refreshStatus?.running" class="text-caption text-grey-darken-1">
          Refreshing names ({{ refreshStatus?.processed ?? 0 }}/{{ refreshStatus?.total ?? 0 }})…
        </span>
        <v-btn
          color="blue-darken-3"
          :loading="refreshing" variant="outlined"
          @click="startRefresh"
        >
          <v-icon start>mdi-refresh</v-icon>
          Refresh run
        </v-btn>
        <v-btn color="blue-darken-2" @click="creating = true">
          <v-icon start>mdi-plus</v-icon>
            Add member
          </v-btn>
      </div>
    </template>

    <div style="overflow-x: auto;">
      <v-data-table
        style="min-width: 700px;"
        :headers="headers"
        :items="filteredMembers()"
        :loading="loading"
      >
        <template #item.alias="{ item }">
          <span v-if="editing?.player_id !== item.player_id">{{ item.alias }}</span>
          <v-text-field
            v-else
            v-model="editing.alias"
            density="compact"
            hide-details
            variant="underlined"
            style="width: 130px"
          />
        </template>

        <template #item.alliance_name="{ item }">
          <span v-if="editing?.player_id !== item.player_id">{{ item.alliance_name }}</span>
          <v-text-field
            v-else
            v-model="editing.alliance_name"
            density="compact"
            hide-details
            variant="underlined"
            style="width: 110px"
          />
        </template>

        <template #item.updated_at="{ item }">
          {{ formatDateTime(item.updated_at) }}
        </template>

        <template #item.actions="{ item }">
          <template v-if="editing?.player_id !== item.player_id">
            <v-btn icon="mdi-pencil" size="small" variant="text" title="Edit" @click="startEdit(item)" />
            <v-btn icon="mdi-delete" size="small" color="error" variant="text" title="Delete" @click="deleteMember(item)" />
          </template>
          <template v-else-if="!isDirty(item)">
            <v-btn icon="mdi-close-circle-outline" size="small" color="warning" variant="text" title="Cancel" @click="cancelEdit()" />
          </template>
          <template v-else>
            <v-btn icon="mdi-content-save" size="small" color="primary" variant="text" title="Save" @click="saveEdit(item)" />
            <v-btn icon="mdi-close-circle-outline" size="small" color="warning" variant="text" title="Cancel" @click="cancelEdit()" />
          </template>
        </template>
      </v-data-table>
    </div>

    <v-dialog v-model="creating" max-width="420">
      <v-card>
        <v-card-title class="ml-2 mt-3">Add member</v-card-title>
        <v-card-text class="pb-0">
          <v-text-field v-model="newMember.player_id" label="Player ID" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newMember.alias" label="Alias" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newMember.alliance_name" label="Alliance" variant="outlined" density="compact" />
        </v-card-text>
        <v-card-actions class="mr-2 mb-2">
          <v-spacer />
          <v-btn variant="text" @click="creating = false">Cancel</v-btn>
          <v-btn color="blue-darken-2" @click="createMember">Create</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<style scoped>
.bloop-blue {
  color: #18a4ff;
}

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