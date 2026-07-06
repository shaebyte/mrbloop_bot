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

// player_id -> included in submission, player_id -> editable power value
const included = ref({})
const power = ref({})
const includedCount = computed(() => Object.values(included.value).filter(Boolean).length)

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
    included.value = Object.fromEntries(data.matched.map((m) => [m.player_id, true]))
    power.value = Object.fromEntries(data.matched.map((m) => [m.player_id, m.power]))
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
    .map((m) => ({
      player_id: m.player_id,
      power: Number(power.value[m.player_id]),
      matched_by_name: m.matched_by_name,
    }))

  if (!entries.length) {
    errorMsg.value = 'No members selected'
    return
  }
  if (entries.some((e) => !Number.isFinite(e.power) || e.power <= 0)) {
    errorMsg.value = 'Every selected member needs a valid power value'
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
          <v-btn variant="outlined" color="blue-darken-2" @click="openFilePicker">
            <v-icon start>mdi-camera</v-icon>
            {{ fileInputLabel }}
          </v-btn>
          <v-btn color="blue-darken-2" :loading="loading" @click="runPreview">
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

      <!-- REVIEW MATCHED NAMES + POWER -->
      <div v-else-if="preview">
        <div class="d-flex ga-4 mt-3">
          <div style="flex: 1 1 0; min-width: 0">
            <p class="text-subtitle-2 mb-1 ml-4 text-info">Unmatched rows ({{ preview.unmatched_rows?.length ?? 0 }})</p>
            <v-list density="compact">
              <v-list-item v-for="(row, i) in preview.unmatched_rows" :key="i">
                {{ row }}
              </v-list-item>
            </v-list>
          </div>
          <div style="flex: 2 1 0; min-width: 0">
            <p class="text-subtitle-2 mb-1 ml-5 text-success">Matched players ({{ includedCount }})</p>
            <p class="text-caption text-grey-darken-1 mb-1 ml-5">Double check the player matching and power values, they may not always be true!</p>
            <div class="matched-table ml-2 mb-5">
              <div class="matched-row" v-for="m in preview.matched" :key="m.player_id">
                <div class="matched-name-cell">
                  <v-checkbox-btn v-model="included[m.player_id]" class="flex-grow-0" />
                  <span>{{ m.alias ?? m.player_id }} ({{ m.player_id }}) — OCR: "{{ m.matched_by_name }}"</span>
                </div>
                <div class="matched-power-cell">
                  <v-text-field
                    v-model="power[m.player_id]"
                    type="number"
                    min="1"
                    density="compact"
                    variant="plain"
                    hide-details
                    class="power-input"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <v-alert v-if="errorMsg" type="error" density="compact" closable class="mt-3" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>
        <div class="d-flex ga-2 mt-4 justify-end">
          <v-btn variant="text" @click="reset">Cancel</v-btn>
          <v-btn color="blue-darken-1" :loading="loading" @click="confirm">
            <v-icon start>mdi-check</v-icon>
            Confirm
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
.matched-table {
  display: grid;
  grid-template-columns: max-content 140px;
  column-gap: 36px;
  row-gap: 4px;
}

.matched-row {
  display: contents;
}

.matched-name-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  min-width: 0;
}

.matched-power-cell {
  width: 140px;
}

.power-input :deep(input) {
  text-align: right;
}
</style>
