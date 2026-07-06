<script setup>
</script>

<template>
  <v-card-title class="bloop-pink mt-3 ml-2">About Registration</v-card-title>
  <v-card-text>
    <p class="text-medium-emphasis">
      Registration uses OCR (Optical Character Recognition), a technology that converts screenshot
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
      <v-icon class="mr-2 bloop-pink">mdi-clock-outline</v-icon>
      <span class="text-subtitle-1 font-weight-medium">How it works</span>
    </div>
    <ol class="about-steps">
      <li>Select the event type and legion.</li>
      <li>Select the date.</li>
      <li>Enter the maximum number of players for this round.</li>
      <li>Add the screenshots.</li>
      <li>
        Refresh in-game names for better matching.
        <span class="d-block text-caption text-medium-emphasis">This update may take a moment.</span>
      </li>
      <li>
        Review the scan.
        <span class="d-block text-caption text-medium-emphasis">"Unmatched lines" are scanned text that didn't match any player in the database.</span>
      </li>
      <li>Check the matched players</li>
      <li>(De)select what's correct, then click <strong>Confirm</strong>.</li>
    </ol>

    <v-divider class="my-4" />

    <div class="d-flex align-center mb-2">
      <v-icon class="mr-2 bloop-pink">mdi-magnify</v-icon>
      <span class="text-subtitle-1 font-weight-medium">Handling unmatched players</span>
    </div>
    <ol class="about-steps" start="9">
      <li>Go to the <strong>Events</strong> tab for an overview of all registered events.</li>
      <li>
        Click the eye icon next to an event, then use the dropdown to add players who attended but weren't matched.
        <span class="d-block text-caption text-medium-emphasis">"Attended players" vs. "listed players" acts as a helpful reminder.</span>
      </li>
    </ol>

    <v-divider class="my-4" />

    <div class="d-flex align-center mb-2">
      <v-icon class="mr-2 bloop-pink">mdi-chart-bar</v-icon>
      <span class="text-subtitle-1 font-weight-medium">Statistics</span>
    </div>
    <p class="text-medium-emphasis mb-0">
      Find an overview of players per event and legion in the Statistics section.
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
