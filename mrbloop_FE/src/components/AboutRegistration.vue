<script setup>
</script>

<template>
  <v-card-title class="bloop-pink mt-3 ml-2">About Registration</v-card-title>
  <v-card-text>
    <p class="text-medium-emphasis">
      Registration uses Optical Character Recognition - OCR, a technology that converts screenshot
      images into digital text so player names can be matched automatically.
    </p>

    <v-divider class="my-4" />

    <!-- <div class="d-flex align-center mb-2">
      <v-icon class="mr-2 bloop-pink">mdi-alert</v-icon>
      <span class="text-subtitle-1 font-weight-medium">Before you trust the scan</span>
    </div> -->
    <v-alert type="warning" variant="tonal" density="comfortable">
      <strong>OCR is a guess, not a guarantee.</strong>
      <ul class="mt-1 about-warning-list">
        <li>Rarely 100% flawless, always double-check matched lines.</li>
        <li>Character-based scripts (Arabic, Chinese, Korean, Japanese, etc.) are never recognized and cannot be matched.</li>
      </ul>
    </v-alert>

    <v-divider class="my-4" />

    <div class="d-flex align-center mb-2">
      <v-icon class="mr-2 bloop-pink">mdi-help-circle-outline</v-icon>
      <span class="text-subtitle-1 font-weight-medium">How it works</span>
    </div>
    <ol class="about-steps">
      <li>Select the event type, legion, date and enter the maximum number of players.</li>
      <li>Add the screenshots.</li>
      <li>
        Refresh in-game names for better matching if the popup appears.
        <span class="d-block text-caption text-medium-emphasis">This update may take a moment.</span>
      </li>
      <li>
        Review the scan.
        <span class="d-block text-caption text-medium-emphasis">"Unmatched lines" are scanned text that didn't match any player in the database.</span>
      </li>
      <li>Check the matched players.</li>
      <li>(De)select what's (in)correct.</li>
      <li>Add remaining players who attended but weren't matched.</li>
      <li>When done, click <strong>Confirm</strong>. 
        <span class="d-block text-caption text-medium-emphasis">Event will be created and the players will be included.</span>
      </li>
    </ol>

    <v-divider class="my-4" />

    <div class="d-flex align-center mb-2">
      <v-icon class="mr-2 bloop-pink">mdi-calendar-check</v-icon>
      <span class="text-subtitle-1 font-weight-medium">Events</span>
    </div>
    <p class="text-medium-emphasis mb-0">
      Find an overview of all events in the Calendar section.
    </p>

    <v-divider class="my-4" />

    <div class="d-flex align-center mb-2">
      <v-icon class="mr-2 bloop-pink">mdi-chart-bar</v-icon>
      <span class="text-subtitle-1 font-weight-medium">Statistics</span>
    </div>
    <p class="text-medium-emphasis mb-0">
      Find an overview of players per event and legion in the Statistics section. And their individualpower increase over time.
      <br> 
    </p>
  </v-card-text>
</template>

<style scoped>
.bloop-pink {
  color: #fc3dab;
}

.bloop-blue {
  color: #18a4ff;
}

.about-steps {
  margin: 0;
  padding-left: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.about-steps li::marker {
  font-weight: 600;
}

.about-warning-list {
  padding-left: 0.1rem;
  list-style-position: inside;
}
</style>
