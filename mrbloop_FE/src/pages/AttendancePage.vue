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

// player_id -> included in submission
const included = ref({})
const includedCount = computed(() => Object.values(included.value).filter(Boolean).length)

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
  } catch (err) {
    errorMsg.value = err.response?.data?.detail ?? 'Preview failed'
  } finally {
    loading.value = false
  }
}

async function confirm() {
  errorMsg.value = ''
  const entries = preview.value.matched
    .filter((m) => included.value[m.player_id])
    .map((m) => ({ player_id: m.player_id, matched_by_name: m.matched_by_name }))

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

      <!-- REVIEW MATCHED NAMES -->
      <div v-else-if="preview">
        <div class="d-flex ga-4 mt-3">
          <div style="flex: 1 1 0; min-width: 0">
            <p class="text-subtitle-2 mb-1 ml-4 text-info">Unmatched lines ({{ preview.unmatched_lines?.length ?? 0 }})</p>
            <v-list density="compact">
              <v-list-item v-for="(line, i) in preview.unmatched_lines" :key="i">
                {{ line }}
              </v-list-item>
            </v-list>
          </div>
          <div style="flex: 1 1 0; min-width: 0">
            <p class="text-subtitle-2 mb-1 ml-5 text-success">Matched players ({{ includedCount }})</p>
            <p class="text-caption text-grey-darken-1 mb-1 ml-5">Double check the player matching, values may not always be true!</p>
            <v-alert v-if="preview.total_attendees - includedCount !== 0" type="warning" density="compact" variant="tonal" closable class="ma-3">
              {{ preview.total_attendees - includedCount }} attendees not matched
            </v-alert>
            <v-list density="compact">
              <v-list-item v-for="m in preview.matched" :key="m.player_id">
                <template #prepend>
                  <v-checkbox-btn v-model="included[m.player_id]" />
                </template>
                {{ m.alias ?? m.player_id }} ({{ m.player_id }}) — OCR: "{{ m.matched_by_name }}"
              </v-list-item>
            </v-list>
          </div>
        </div>

        <v-alert v-if="errorMsg" type="error" density="compact" closable class="mt-3" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>
        <div class="d-flex ga-2 mt-4 justify-end">
          <v-btn variant="text" @click="reset">Cancel</v-btn>
          <v-btn color="#18a4ff" :loading="loading" @click="confirm">
            <v-icon start>mdi-check</v-icon>
            Confirm
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
</style>