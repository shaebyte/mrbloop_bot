<script setup>
defineProps({
  urls: { type: Array, default: () => [] },
  size: { type: Number, default: 320 },
  removable: { type: Boolean, default: false },
})
defineEmits(['remove'])
</script>

<template>
  <div v-if="urls.length" class="d-flex ga-2 flex-wrap">
    <div
      v-for="(url, i) in urls"
      :key="i"
      class="position-relative flex-grow-0 flex-shrink-0"
      :style="{ width: size + 'px', height: size + 'px' }"
    >
      <v-img :src="url" contain class="rounded border" style="width: 100%; height: 100%" />
      <v-btn
        v-if="removable"
        icon="mdi-close"
        size="x-small"
        color="error"
        class="position-absolute"
        style="top: 5px; right: 5px"
        @click="$emit('remove', i)"
      />
    </div>
  </div>
</template>
