import { ref, onBeforeUnmount } from 'vue'
import api from '../api/allianceClient'

/** Shared "warn if member names are stale before OCR matching" flow, used by
 * both the attendance and member-power preview steps. */
export function useNameRefreshGuard() {
  const showConfirm = ref(false)
  const refreshing = ref(false)
  const refreshDone = ref(false)
  const refreshStatus = ref(null)
  let poll = null
  let pendingProceed = null

  onBeforeUnmount(() => clearInterval(poll))

  /** Call before running a preview. Runs `proceed` immediately if the
   * cooldown hasn't elapsed yet, otherwise opens the confirm dialog. */
  async function requestPreview(proceed) {
    pendingProceed = proceed
    const { data } = await api.get('/members/refresh-names/status')
    if (data.cooldown_left > 0) {
      proceedNow()
      return
    }
    refreshDone.value = false
    showConfirm.value = true
  }

  function proceedNow() {
    showConfirm.value = false
    const proceed = pendingProceed
    pendingProceed = null
    proceed?.()
  }

  async function startRefresh() {
    await api.post('/members/refresh-names')
    refreshing.value = true
    refreshDone.value = false
    clearInterval(poll)
    poll = setInterval(async () => {
      const { data } = await api.get('/members/refresh-names/status')
      refreshStatus.value = data
      if (!data.running) {
        clearInterval(poll)
        refreshing.value = false
        refreshDone.value = true
      }
    }, 1500)
  }

  return {
    showConfirm,
    refreshing,
    refreshDone,
    refreshStatus,
    requestPreview,
    proceedNow,
    startRefresh,
  }
}
