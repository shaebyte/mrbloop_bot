import { ref, computed, watch, onBeforeUnmount } from 'vue'

/** Shared "pick screenshots, preview them as thumbnails" state for the
 * attendance and member-power screenshot workflows. */
export function useScreenshotPicker() {
  const screenshots = ref([])
  const previewUrls = ref([])
  const fileInputEl = ref(null)

  watch(screenshots, (files) => {
    previewUrls.value.forEach((url) => URL.revokeObjectURL(url))
    previewUrls.value = (files ?? []).map((file) => URL.createObjectURL(file))
  })

  onBeforeUnmount(() => {
    previewUrls.value.forEach((url) => URL.revokeObjectURL(url))
  })

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

  function removeScreenshot(index) {
    screenshots.value = screenshots.value.filter((_, i) => i !== index)
  }

  function reset() {
    screenshots.value = []
  }

  const fileInputLabel = computed(() =>
    screenshots.value.length
      ? `${screenshots.value.length} screenshot(s) selected`
      : 'Add screenshots'
  )

  return {
    screenshots,
    previewUrls,
    fileInputEl,
    fileInputLabel,
    openFilePicker,
    onFileChange,
    removeScreenshot,
    reset,
  }
}
