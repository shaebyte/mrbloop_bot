<script setup>
defineProps({
  modelValue: Boolean,
  refreshing: Boolean,
  refreshDone: Boolean,
  refreshStatus: Object,
})
defineEmits(['update:modelValue', 'continue', 'refresh'])
</script>

<template>
  <v-dialog :model-value="modelValue" max-width="420" @update:model-value="$emit('update:modelValue', $event)">
    <v-card>
      <v-card-title class="mt-3 ml-2 text-warning">Refresh required</v-card-title>
      <v-card-text>
        Names haven't been refreshed in a while. Run a refresh now for more accurate matching.
        <div v-if="refreshing" class="text-caption text-grey-darken-1 mt-6">
          Refreshing names ({{ refreshStatus?.processed ?? 0 }}/{{ refreshStatus?.total ?? 0 }})…
        </div>
        <div v-else-if="refreshDone" class="text-caption text-grey-darken-1 mt-6">
          Refreshing names done
        </div>
      </v-card-text>
      <v-card-actions class="justify-end mb-2 mr-2">
        <v-btn
          :variant="refreshDone ? 'tonal' : 'text'"
          :color="refreshDone ? 'warning' : 'grey-darken-1'"
          :disabled="refreshing"
          @click="$emit('continue')"
        >{{ refreshDone ? 'Continue' : 'Continue without' }}</v-btn>
        <v-btn variant="tonal" color="warning" :loading="refreshing" :disabled="refreshDone" @click="$emit('refresh')">Refresh now</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
