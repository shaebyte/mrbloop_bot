<script setup>
import { ref } from 'vue'
import AccountsPage from '../pages/AccountsPage.vue'
import RedemptionPage from '../pages/RedemptionPage.vue'

const activeTab = ref('accounts')
</script>

<template>
  <v-tabs v-model="activeTab" color="#fc3dab">
    <v-tab value="accounts">
      <v-icon>mdi-account-group</v-icon>
    </v-tab>
    <v-tab value="attempts">
      <v-icon>mdi-ticket-confirmation</v-icon>
    </v-tab>
  </v-tabs>

  <v-tabs-window v-model="activeTab">
    <v-tabs-window-item value="accounts">
      <AccountsPage />
    </v-tabs-window-item>

    <v-tabs-window-item value="attempts">
      <RedemptionPage />
    </v-tabs-window-item>
  </v-tabs-window>
</template>
