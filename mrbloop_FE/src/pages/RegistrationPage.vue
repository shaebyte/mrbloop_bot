<script setup>
import { ref } from 'vue'
import AttendancePageV2 from './AttendancePageV2.vue'
import MemberpowerPageV2 from './MemberpowerPageV2.vue'
import AboutRegistration from '../components/AboutRegistration.vue'

const activeSubTab = ref('attendance')
const infoDialog = ref(false)
</script>

<template>
  <v-card flat>
    <template #title>
      <div class="d-flex align-center justify-space-between">
        <span class="d-block ml-1 mt-3 mb-3 bloop-blue">Registration</span>
        <v-btn icon="mdi-information-outline" variant="text" color="#fc3dab" @click="infoDialog = true" />
      </div>
    </template>

    <v-dialog v-model="infoDialog" max-width="500">
      <v-card>
        <AboutRegistration />
        <v-card-actions>
          <v-spacer />
          <v-btn color="#fc3dab" variant="text" @click="infoDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <template #text>
      <v-tabs v-model="activeSubTab" color="blue-darken-1" class="mb-4">
        <v-tab value="attendance">Event attendance</v-tab>
        <v-tab value="member-power">Member power</v-tab>
      </v-tabs>

      <v-tabs-window v-model="activeSubTab">
        <v-tabs-window-item value="attendance">
          <AttendancePageV2 />
        </v-tabs-window-item>

        <v-tabs-window-item value="member-power">
          <MemberpowerPageV2 />
        </v-tabs-window-item>
      </v-tabs-window>
    </template>
  </v-card>
</template>

<style scoped>
.bloop-blue {
  color: #18a4ff;
}
</style>
