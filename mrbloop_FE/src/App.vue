<script setup>
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from './composables/useAuth'
import logo from './assets/logo.png'

const router = useRouter()
const route = useRoute() // We need the route to check where we are
const { isMod, logout } = useAuth()

function handleLogout() {
  logout()
  router.push('/')
}
</script>

<template>
  <v-app>
    <v-app-bar 
      density="comfortable" 
      elevation="3"
      :class="{ 'mod-navbar-active': route.path.startsWith('/mod') && route.path !== '/mod/login' }"
    >
      <div class="nav-content-container d-flex align-center w-100 px-4">
        
        <div class="flex-1-1-0"></div>

        <div class="d-flex justify-center flex-1-1-0">
          <v-btn @click="router.push('/')" class="btn" rounded="large">
            <img :src="logo" alt="mrbloop" class="logo" />
          </v-btn>
        </div>

        <div class="d-flex justify-end ga-2 flex-1-1-0">
          <v-btn v-if="isMod" to="/mod" icon size="small" color="pink-lighten-1" class="btn"> 
            <v-icon size="small">mdi-cog</v-icon>
          </v-btn>
          
          <v-btn v-if="!isMod" to="/mod/login" icon size="small" class="btn">
            <v-icon size="small">mdi-login</v-icon>
          </v-btn>
          
          <v-btn v-if="isMod" icon size="small" @click="handleLogout" class="btn">
            <v-icon size="small">mdi-logout</v-icon>
          </v-btn>
        </div>

      </div>
    </v-app-bar>

    <v-main class="d-flex justify-center">
      <div class="layout-container w-100">
        <div class="mt-4">
          <router-view />
        </div>
      </div>
    </v-main>
  </v-app>
</template>

<style>
* {
  font-family: 'DM Sans', sans-serif;
}
</style>

<style scoped>
/* 1. Base layout (mobile first): take the full width with comfortable padding */
.layout-container,
.nav-content-container {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  transition: max-width 0.2s ease; /* Provides a smooth transition when resizing */
}

/* 2. Responsive breakpoints for normal pages (Home & ModLogin) */
@media (min-width: 600px) {
  .layout-container,
  .nav-content-container {
    max-width: 500px; /* Nicely compact for mobile/tablet */
  }
}

@media (min-width: 960px) {
  .layout-container,
  .nav-content-container {
    max-width: 550px; /* A bit wider on desktop, but stays a nice centered card */
  }
}

/* 3. Exception for the Dashboard: if we're on /mod, BUT NOT on /mod/login */
/* We use the dynamic class 'mod-navbar-active' already set up via the route */
.mod-navbar-active .nav-content-container,
:has(.mod-navbar-active) .layout-container {
  max-width: 1200px !important; /* Generous width for the datatables */
  padding-left: 24px;
  padding-right: 24px;
}

/* Extra tweaks for the home button and logo */
.home-btn {
  min-width: unset;
  padding: 0 8px;
}

.logo {
  height: 24px;
  width: auto;
  display: block;
}
.btn {
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.2px;
  text-transform: none;
  transition: transform 0.15s, box-shadow 0.2s;
}
.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.14) !important;
}
</style>