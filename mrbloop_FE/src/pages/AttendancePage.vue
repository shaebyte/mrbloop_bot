<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import api from '../api/allianceClient'
import { EVENT_TYPES, LEGIONS } from '../api/allianceConstants'

const eventType = ref(null)
const legion = ref(null)
const eventDate = ref(new Date().toISOString().slice(0, 10))
const screenshots = ref([])

const previewUrls = ref([])

watch(screenshots, (files) => {
  previewUrls.value.forEach((url) => URL.revokeObjectURL(url))
  previewUrls.value = (files ?? []).map((file) => URL.createObjectURL(file))
})

onBeforeUnmount(() => {
  previewUrls.value.forEach((url) => URL.revokeObjectURL(url))
})

const fileInputEl = ref(null)

function openFilePicker() {
  fileInputEl.value?.click()
}

function onFileChange(e) {
  addFiles(Array.from(e.target.files || []))
  e.target.value = '' // allow re-selecting the same file(s) later
}

function addFiles(files) {
  if (!files) return
  const arr = Array.isArray(files) ? files : [files]
  if (arr.length) screenshots.value = [...screenshots.value, ...arr]
}

const fileInputLabel = computed(() =>
  screenshots.value.length
    ? `${screenshots.value.length} screenshot(s) selected`
    : 'Add screenshots'
)

function removeScreenshot(index) {
  screenshots.value = screenshots.value.filter((_, i) => i !== index)
}

const loading = ref(false)
const errorMsg = ref('')
const preview = ref(null)
const confirmResult = ref(null)

// player_id -> included in submission
const included = ref({})

async function runPreview() {
  errorMsg.value = ''
  confirmResult.value = null
  if (!eventType.value || !legion.value || !eventDate.value || !screenshots.value.length) {
    errorMsg.value = 'Event type, legion, date and at least one screenshot are required'
    return
  }

  const form = new FormData()
  form.append('event_type', eventType.value)
  form.append('legion', legion.value)
  form.append('event_date', eventDate.value)
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
  screenshots.value = []
}
</script>

<template>
  <v-card flat>
    <template #title>
      <span class="d-block ml-1 mt-3 mb-3 text-blue-darken-2">Attendance</span>
    </template>

    <template #text>
      <div class="d-flex ga-3 flex-wrap">
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

        <div v-if="previewUrls.length" class="d-flex ga-2 flex-wrap mt-6">
          <div
            v-for="(url, i) in previewUrls"
            :key="i"
            class="position-relative flex-grow-0 flex-shrink-0"
            style="width: 320px; height: 320px"
          >
            <v-img :src="url" contain class="rounded border" style="width: 100%; height: 100%" />
            <v-btn
              icon="mdi-close"
              size="x-small"
              color="error"
              class="position-absolute"
              style="top: 5px; right: 5px"
              @click="removeScreenshot(i)"
            />
          </div>
        </div>
      </div>

      <!-- REVIEW MATCHED NAMES -->
      <div v-else-if="preview">
        <p class="text-medium-emphasis mb-3">
          {{ preview.lines_read }} lines read, {{ preview.matched.length }} matched.
        </p>

        <v-list density="compact">
          <v-list-item v-for="m in preview.matched" :key="m.player_id">
            <template #prepend>
              <v-checkbox-btn v-model="included[m.player_id]" />
            </template>
            {{ m.alias ?? m.player_id }} ({{ m.player_id }}) — OCR: "{{ m.matched_by_name }}"
          </v-list-item>
        </v-list>

        <v-alert v-if="preview.unmatched_lines?.length" type="warning" density="compact" variant="tonal" closable class="mt-3">
          Unmatched lines: {{ preview.unmatched_lines.join(', ') }}
        </v-alert>
        <v-alert v-if="preview.members_not_found?.length" type="info" density="compact" variant="tonal" closable class="mt-2">
          Members not found in screenshots: {{ preview.members_not_found.length }}
        </v-alert>

        <v-alert v-if="errorMsg" type="error" density="compact" closable class="mt-3" @click:close="errorMsg = ''">{{ errorMsg }}</v-alert>

        <div v-if="previewUrls.length" class="d-flex ga-2 flex-wrap mt-4">
          <v-img
            v-for="(url, i) in previewUrls"
            :key="i"
            :src="url"
            contain
            class="rounded border flex-grow-0 flex-shrink-0"
            style="width: 160px; height: 160px"
          />
        </div>

        <div class="d-flex ga-2 mt-4 justify-end">
          <v-btn variant="text" @click="reset">Cancel</v-btn>
          <v-btn color="blue-lighten-1" :loading="loading" @click="confirm">
            <v-icon start>mdi-check</v-icon>
            Confirm
          </v-btn>
        </div>
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
        <v-btn color="pink-lighten-1" @click="reset">New upload</v-btn>
      </div>
    </template>
  </v-card>
</template>
