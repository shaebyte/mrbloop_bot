<script setup>
import { ref, watch } from 'vue'
import MembersPage from '../pages/MembersPage.vue'
import RegistrationPage from '../pages/RegistrationPage.vue'
import EventsPage from '../pages/EventsPage.vue'
import StatsPage from '../pages/StatsPage.vue'

const activeTab = ref('registration')

const eventsPageRef = ref(null)
const membersPageRef = ref(null)

watch(activeTab, (tab) => {
  if (tab === 'events') eventsPageRef.value?.fetchEvents()
  if (tab === 'members') membersPageRef.value?.fetchMembers()
})
</script>

<template>
  <v-tabs v-model="activeTab" color="blue-lighten-1">
    <v-tab value="registration">
      <v-icon>mdi-camera</v-icon>
    </v-tab>
    <v-tab value="events">
      <v-icon>mdi-calendar</v-icon>
    </v-tab>
    <v-tab value="members">
      <v-icon>mdi-account-group</v-icon>
    </v-tab>
    <v-tab value="stats">
      <v-icon>mdi-chart-bar</v-icon>
    </v-tab>
  </v-tabs>

  <v-tabs-window v-model="activeTab">
    <v-tabs-window-item value="registration">
      <RegistrationPage />
    </v-tabs-window-item>

    <v-tabs-window-item value="events">
      <EventsPage ref="eventsPageRef" />
    </v-tabs-window-item>

    <v-tabs-window-item value="members">
      <MembersPage ref="membersPageRef" />
    </v-tabs-window-item>

    <v-tabs-window-item value="stats">
      <StatsPage />
    </v-tabs-window-item>
  </v-tabs-window>
</template>
