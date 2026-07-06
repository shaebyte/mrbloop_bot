<script setup>
import { ref, computed } from 'vue'
import api from '../api/allianceClient'
import ScreenshotThumbnails from '../components/ScreenshotThumbnails.vue'
import NameRefreshDialog from '../components/NameRefreshDialog.vue'
import { useScreenshotPicker } from '../composables/useScreenshotPicker'
import { useNameRefreshGuard } from '../composables/useNameRefreshGuard'

const powerDate = ref(new Date().toISOString().slice(0, 10))

const {
  screenshots,
  previewUrls,
  fileInputEl,
  fileInputLabel,
  openFilePicker,
  onFileChange,
  removeScreenshot,
  reset: resetScreenshots,
} = useScreenshotPicker()

const {
  showConfirm: showRefreshConfirm,
  refreshing,
  refreshDone,
  refreshStatus,
  requestPreview,
  proceedNow,
  startRefresh,
} = useNameRefreshGuard()

const loading = ref(false)
const errorMsg = ref('')
const preview = ref(null)
const confirmResult = ref(null)
const showUnmatchedRows = ref(false)

// player_id -> editable power value (string, so an empty field is possible)
const power = ref({})

async function runPreview() {
  errorMsg.value = ''
  confirmResult.value = null
  if (!powerDate.value || !screenshots.value.length) {
    errorMsg.value = 'Date and at least one screenshot are required'
    return
  }

  await requestPreview(doPreview)
}

async function startRefreshFromDialog() {
  errorMsg.value = ''
  try {
    await startRefresh()
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Could not start refresh'
  }
}

async function doPreview() {
  const form = new FormData()
  form.append('power_date', powerDate.value)
  for (const file of screenshots.value) form.append('screenshots', file)

  loading.value = true
  try {
    const { data } = await api.post('/power/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    preview.value = data
    power.value = Object.fromEntries(data.matched.map((m) => [m.player_id, String(m.power)]))
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Preview failed'
  } finally {
    loading.value = false
  }
}

// One alphabetically sorted list covering every am_members row: matched
// entries carry their OCR text, members_not_found get a blank manual entry.
const rows = computed(() => {
  if (!preview.value) return []
  const matched = preview.value.matched.map((m) => ({ ...m, hasMatch: true }))
  const notFound = preview.value.members_not_found.map((m) => ({ ...m, hasMatch: false }))
  return [...matched, ...notFound].sort((a, b) => (a.alias ?? '').localeCompare(b.alias ?? ''))
})

function validPower(playerId) {
  const raw = power.value[playerId]
  const n = Number(raw)
  return raw !== undefined && raw !== '' && Number.isFinite(n) && n > 0
}

const filledCount = computed(() => rows.value.filter((r) => validPower(r.player_id)).length)

async function confirm() {
  errorMsg.value = ''
  const entries = rows.value
    .filter((r) => validPower(r.player_id))
    .map((r) => ({
      player_id: r.player_id,
      power: Number(power.value[r.player_id]),
      matched_by_name: r.hasMatch ? r.matched_by_name : null,
    }))

  if (!entries.length) {
    errorMsg.value = 'No power values filled in'
    return
  }

  loading.value = true
  try {
    const { data } = await api.post('/power/confirm', {
      power_date: preview.value.power_date,
      entries,
    })
    confirmResult.value = data
    preview.value = null
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Confirm failed'
  } finally {
    loading.value = false
  }
}

function reset() {
  preview.value = null
  confirmResult.value = null
  resetScreenshots()
}
</script>

<template>
  <div>
    <div class="d-flex ga-3 flex-wrap mt-3">
      <v-text-field
        v-model="powerDate"
        type="date"
        label="Date"
        variant="outlined"
        :disabled="!!preview || !!confirmResult"
        style="flex: 1 1 0; min-width: 160px"
      />
    </div>

    <div v-if="!preview && !confirmResult">
      <input
        ref="fileInputEl"
        type="file"
        multiple
        accept="image/*"
        class="d-none"
        @change="onFileChange"
      />

      <div class="d-flex ga-3 align-center justify-end mt-1">
        <v-btn variant="outlined" color="blue-darken-1" @click="openFilePicker">
          <v-icon start>mdi-camera</v-icon>
          {{ fileInputLabel }}
        </v-btn>
        <v-btn color="blue-darken-1" :loading="loading" @click="runPreview">
          <v-icon start>mdi-magnify</v-icon>
          Preview
        </v-btn>
      </div>

      <v-alert v-if="errorMsg" type="error" density="compact" closable class="mt-6" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>

      <ScreenshotThumbnails
        :urls="previewUrls"
        :size="320"
        removable
        class="mt-6"
        @remove="removeScreenshot"
      />
    </div>

    <!-- REVIEW: unified member table -->
    <div v-else-if="preview">
      <v-btn
        variant="text"
        size="small"
        class="mt-3"
        :color="showUnmatchedRows ? 'blue-lighten-1' : 'blue-lighten-1'"
        @click="showUnmatchedRows = !showUnmatchedRows"
      >
        Unrecognized OCR rows ({{ preview.unmatched_rows?.length ?? 0 }})
        <v-icon end>{{ showUnmatchedRows ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </v-btn>

      <v-expand-transition>
        <v-list v-if="showUnmatchedRows" density="compact" class="mb-2">
          <v-list-item v-for="(row, i) in preview.unmatched_rows" :key="i">
            {{ row }}
          </v-list-item>
        </v-list>
      </v-expand-transition>

      <p class="text-caption mt-2 mb-2 ml-3">
        {{ filledCount }} / {{ rows.length }} members have a power value. Rows without a scan match are highlighted — fill them in manually.
      </p>

      <div style="overflow-x: auto;">
        <table class="member-power-table">
          <thead>
            <tr>
              <th>Alias</th>
              <th>Ingame name</th>
              <th>Match</th>
              <th>Power</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.player_id" :class="{ 'no-match-row': !r.hasMatch }">
              <td class="alias-cell">{{ r.alias ?? r.player_id }}</td>
              <td class="ingame-name-cell">{{ r.ingame_name }}</td>
              <td class="match-cell">
                <span v-if="r.hasMatch" class="text-success">
                  <!-- <v-icon size="medium" color="success">mdi-check-circle-outline</v-icon> -->
                  {{ r.matched_by_name }}
                </span>
                <span v-else class="text-warning">
                  <v-icon size="medium" color="warning">mdi-alert-circle-outline</v-icon>
                  No match found
                </span>
              </td>
              <td class="power-cell">
                <v-text-field
                  v-model="power[r.player_id]"
                  type="number"
                  min="1"
                  density="compact"
                  variant="plain"
                  hide-details
                  placeholder="Manual input"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <v-alert v-if="errorMsg" type="error" density="compact" closable class="mt-3" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>
      <div class="d-flex ga-2 mt-4 justify-end">
        <v-btn variant="text" @click="reset">Cancel</v-btn>
        <v-btn color="blue-darken-1" :loading="loading" @click="confirm">
          <v-icon start>mdi-check</v-icon>
          Confirm ({{ filledCount }})
        </v-btn>
      </div>

      <ScreenshotThumbnails :urls="previewUrls" :size="160" class="mt-4" />
    </div>

    <!-- CONFIRM RESULT -->
    <div v-else-if="confirmResult">
      <v-alert type="success" density="compact" closable class="mb-3">
        {{ confirmResult.added.length }} added, {{ confirmResult.updated.length }} updated.
      </v-alert>
      <v-alert v-if="confirmResult.unknown_player_ids?.length" type="error" density="compact" closable class="mb-3">
        Unknown player IDs: {{ confirmResult.unknown_player_ids.join(', ') }}
      </v-alert>
      <v-btn color="blue-darken-1" @click="reset">New upload</v-btn>
    </div>

    <NameRefreshDialog
      v-model="showRefreshConfirm"
      :refreshing="refreshing"
      :refresh-done="refreshDone"
      :refresh-status="refreshStatus"
      @continue="proceedNow"
      @refresh="startRefreshFromDialog"
    />
  </div>
</template>

<style scoped>
.member-power-table {
  width: 100%;
  min-width: 640px;
  border-collapse: collapse;
}

.member-power-table th {
  text-align: left;
  font-size: 0.9rem;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.6);
  padding: 8px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.member-power-table td {
  padding: 4px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.06);
}

.no-match-row {
  background: rgba(var(--v-theme-warning), 0.08);
}

.alias-cell {
  white-space: nowrap;
}

.ingame-name-cell {
  white-space: nowrap;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.match-cell {
  font-size: 0.85rem;
}

.power-cell {
  width: 160px;
}

.bloop-blue {
  color: #18a4ff;
}

.bloop-pink {
  color: #fc3dab;
}

</style>