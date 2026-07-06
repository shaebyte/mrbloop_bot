<script setup>
import { ref, computed } from 'vue'
import api from '../api/allianceClient'
import { EVENT_TYPES, LEGIONS } from '../api/allianceConstants'
import ScreenshotThumbnails from '../components/ScreenshotThumbnails.vue'
import NameRefreshDialog from '../components/NameRefreshDialog.vue'
import { useScreenshotPicker } from '../composables/useScreenshotPicker'
import { useNameRefreshGuard } from '../composables/useNameRefreshGuard'

const eventType = ref(null)
const legion = ref(null)
const eventDate = ref(new Date().toISOString().slice(0, 10))
const totalAttendees = ref(null)

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
const showUnmatchedLines = ref(false)

// player_id -> included in submission (present list)
const included = ref({})
// player_id -> manually marked present despite no OCR match (absent list)
const manualPresent = ref({})

const includedCount = computed(
  () => Object.values(included.value).filter(Boolean).length +
    Object.values(manualPresent.value).filter(Boolean).length
)

const presentRows = computed(() => {
  if (!preview.value) return []
  return [...preview.value.matched].sort((a, b) => (a.alias ?? '').localeCompare(b.alias ?? ''))
})

const absentRows = computed(() => {
  if (!preview.value) return []
  return [...preview.value.members_not_found].sort((a, b) => (a.alias ?? '').localeCompare(b.alias ?? ''))
})

async function runPreview() {
  errorMsg.value = ''
  confirmResult.value = null
  if (
    !eventType.value ||
    !legion.value ||
    !eventDate.value ||
    !screenshots.value.length ||
    !totalAttendees.value ||
    Number.isNaN(Number(totalAttendees.value))
  ) {
    errorMsg.value = 'Event type, legion, date, total amount of attendees and at least one screenshot are required'
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
  form.append('event_type', eventType.value)
  form.append('legion', legion.value)
  form.append('event_date', eventDate.value)
  form.append('total_attendees', totalAttendees.value)
  for (const file of screenshots.value) form.append('screenshots', file)

  loading.value = true
  try {
    const { data } = await api.post('/attendance/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    preview.value = data
    included.value = Object.fromEntries(data.matched.map((m) => [m.player_id, true]))
    manualPresent.value = {}
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Preview failed'
  } finally {
    loading.value = false
  }
}

async function confirm() {
  errorMsg.value = ''
  const entries = [
    ...preview.value.matched
      .filter((m) => included.value[m.player_id])
      .map((m) => ({ player_id: m.player_id, matched_by_name: m.matched_by_name })),
    ...preview.value.members_not_found
      .filter((m) => manualPresent.value[m.player_id])
      .map((m) => ({ player_id: m.player_id, matched_by_name: null })),
  ]

  if (!entries.length) {
    errorMsg.value = 'No members selected'
    return
  }

  loading.value = true
  try {
    const { data } = await api.post('/attendance/confirm', {
      event_type: preview.value.event_type,
      legion: preview.value.legion,
      event_date: preview.value.event_date,
      total_attendees: preview.value.total_attendees,
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
  totalAttendees.value = null
}
</script>

<template>
  <div>
    <div class="d-flex ga-3 flex-wrap mt-3">
        <v-select
          v-model="eventType"
          :items="EVENT_TYPES"
          label="Event type"
          variant="outlined"
          clearable
          :disabled="!!preview || !!confirmResult"
          style="flex: 1 1 0; min-width: 160px"
        />
        <v-select
          v-model="legion"
          :items="LEGIONS"
          label="Legion"
          variant="outlined"
          clearable
          :disabled="!!preview || !!confirmResult"
          style="flex: 1 1 0; min-width: 160px"
        />
        <v-text-field
          v-model="eventDate"
          type="date"
          label="Event date"
          variant="outlined"
          :disabled="!!preview || !!confirmResult"
          style="flex: 1 1 0; min-width: 160px"
        />
        <v-text-field
          v-model="totalAttendees"
          type="number"
          min="1"
          label="Attended"
          placeholder="Total amount of players attended(screenshot)"
          variant="outlined"
          required
          :rules="[(v) => (!!v && Number(v) > 0) || 'Required, must be a number']"
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
          <v-btn variant="outlined" color="#18a4ff" @click="openFilePicker">
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

      <!-- REVIEW: present / absent tables -->
      <div v-else-if="preview">
        <div class="d-flex ga-4 mt-3 flex-wrap align-start">
          <div style="flex: 1 1 320px; min-width: 0">
            <v-btn
              variant="text"
              size="small"
              :color="showUnmatchedLines ? 'blue-darken-1' : 'info'"
              @click="showUnmatchedLines = !showUnmatchedLines"
            >
              Unrecognized OCR rows ({{ preview.unmatched_lines?.length ?? 0 }})
              <v-icon end>{{ showUnmatchedLines ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
            </v-btn>
            <v-expand-transition>
              <v-list v-if="showUnmatchedLines" density="compact" class="mb-2">
                <v-list-item v-for="(line, i) in preview.unmatched_lines" :key="i">
                  {{ line }}
                </v-list-item>
              </v-list>
            </v-expand-transition>
          </div>

          <div style="flex: 1 1 320px; min-width: 0">
            <v-alert
              v-if="preview.total_attendees - includedCount !== 0"
              type="warning" density="compact" variant="tonal" closable
            >
              {{ preview.total_attendees - includedCount }} attendees not matched ({{ includedCount }} matched /{{ preview.total_attendees }} reported)
            </v-alert>
          </div>
        </div>

        <div class="d-flex ga-4 mt-3 flex-wrap">
          <div style="flex: 1 1 320px; min-width: 0">
            <p class="text-subtitle-2 mb-1 ml-1 text-success">Matched players ({{ presentRows.length }})</p>
            <p class="text-caption text-grey mb-1 ml-1">Double check the matching, values may not always be true!</p>
            <div style="overflow-x: auto;">
              <table class="attendance-table mt-2">
                <thead>
                  <tr>
                    <th>Alias</th>
                    <th>Matched by</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="m in presentRows" :key="m.player_id">
                    <td class="alias-cell">{{ m.alias ?? m.player_id }}</td>
                    <td class="match-cell">
                      <div class="match-cell-content">
                        <v-checkbox-btn v-model="included[m.player_id]" class="flex-grow-0" />
                        <span class="text-success">{{ m.matched_by_name }}</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div style="flex: 1 1 320px; min-width: 0">
            <p class="text-subtitle-2 mb-1 ml-1 text-grey-darken-1">Absent ({{ absentRows.length }})</p>
            <p class="text-caption text-grey-darken-1 mb-1 ml-1">Recognize a player that wasn't matched? Check them off.</p>
            <div style="overflow-x: auto;">
              <table class="attendance-table mt-2">
                <thead>
                  <tr>
                    <th>Alias</th>
                    <th>Ingame name</th>
                    <th>Present?</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="m in absentRows" :key="m.player_id">
                    <td class="alias-cell">{{ m.alias ?? m.player_id }}</td>
                    <td class="ingame-name-cell">{{ m.ingame_name }}</td>
                    <td class="match-cell">
                      <div class="match-cell-content">
                        <v-checkbox-btn v-model="manualPresent[m.player_id]" class="flex-grow-0" />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <v-alert v-if="errorMsg" type="error" density="compact" closable class="mt-3" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>
        <div class="d-flex ga-2 mt-4 justify-end">
          <v-btn variant="text" @click="reset">Cancel</v-btn>
          <v-btn color="#18a4ff" :loading="loading" @click="confirm">
            <v-icon start>mdi-check</v-icon>
            Confirm ({{ includedCount }})
          </v-btn>
        </div>

        <ScreenshotThumbnails :urls="previewUrls" :size="160" class="mt-4" />
      </div>

      <!-- CONFIRM RESULT -->
      <div v-else-if="confirmResult">
        <v-alert type="success" density="compact" closable class="mb-3">
          {{ confirmResult.added.length }} added, {{ confirmResult.already_registered.length }} already registered.
        </v-alert>
        <v-alert v-if="confirmResult.conflicts?.length" type="warning" density="compact" closable class="mb-3">
          Conflicts (already registered in another legion): {{ confirmResult.conflicts.map(c => c.alias).join(', ') }}
        </v-alert>
        <v-alert v-if="confirmResult.unknown_player_ids?.length" type="error" density="compact" closable class="mb-3">
          Unknown player IDs: {{ confirmResult.unknown_player_ids.join(', ') }}
        </v-alert>
        <v-btn color="bloop-blue" @click="reset">New upload</v-btn>
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
.bloop-blue {
  color: #18a4ff;
}

.attendance-table {
  width: 100%;
  min-width: 320px;
  border-collapse: collapse;
}

.attendance-table th {
  text-align: left;
  font-size: 0.9rem;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.6);
  padding: 8px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.attendance-table td {
  padding: 4px 12px;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.06);
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

.match-cell-content {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
