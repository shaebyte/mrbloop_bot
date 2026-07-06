<script setup>
import { ref } from 'vue'
import AttendancePage from './AttendancePage.vue'
import MemberpowerPage from './MemberpowerPage.vue'

const activeSubTab = ref('attendance')
</script>

<template>
  <v-card flat>
    <template #title>
      <span class="d-block ml-1 mt-3 mb-3 text-blue-darken-2">Registration</span>
    </template>

    <template #text>
      <v-tabs v-model="activeSubTab" color="blue-lighten-1" class="mb-4">
        <v-tab value="attendance">Event attendance</v-tab>
        <v-tab value="member-power">Member power</v-tab>
      </v-tabs>

      <v-tabs-window v-model="activeSubTab">
        <v-tabs-window-item value="attendance">
          <AttendancePage />
        </v-tabs-window-item>

        <v-tabs-window-item value="member-power">
          <MemberpowerPage />
        </v-tabs-window-item>
      </v-tabs-window>
    </template>
  </v-card>
</template>
