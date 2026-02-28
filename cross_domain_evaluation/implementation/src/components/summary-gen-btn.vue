<template>
    <div class="summary-button-wrapper">
      <button
        class="summarize-button"
        @click="handleSummarize"
        :disabled="loading || props.selectedNodes.length === 0"
      >
        <svg
          v-if="loading"
          class="spinner"
          viewBox="0 0 50 50"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle
            class="path"
            cx="25"
            cy="25"
            r="20"
            fill="none"
            stroke-width="5"
          />
        </svg>
        <span>{{ loading ? "Summarizing..." : "Summarize" }}</span>
        
      </button>
  
      <!-- ✅ Notification toast -->
      <transition name="fade">
        <div
          v-if="showToast"
          class="toast-notification"
        >
          <span>✅ Summary saved as: <strong>{{ summaryTitle }}</strong></span>
          <button class="close-btn" @click="showToast = false">×</button>
        </div>
      </transition>
    </div>
  </template>
  
  
  
  <script setup>
  import { ref, defineProps } from 'vue';
  import axios from 'axios';
  
  const props = defineProps({
    selectedNodes: {
      type: Array,
      required: true
    }
  });

  const emit = defineEmits(['summary-generated'])
  
  const loading = ref(false);
  const summaryTitle = ref(null);
  const error = ref(null);
  
  const LOCAL_API_BASE = 'http://localhost:2600';
  
  const fetchGutIndexId = async (id) => {
    try {
      const res = await axios.post(`${LOCAL_API_BASE}/books/node-attribute`, {
        id,
        attribute: 'gutindex_id'
      });
      console.log(res.data);
      return res.data;
    } catch (err) {
      console.error(`Error fetching gutindex_id for node ${id}:`, err);
      return null;
    }
  };
  
  const handleSummarize = async () => {
    loading.value = true;
    error.value = null;
    summaryTitle.value = null;
  
    try {
      const ids = await Promise.all(
        props.selectedNodes.map((id) => fetchGutIndexId(id)) 
      );
  
      const gutindexIds = ids.filter((id) => id !== null);
  
      if (gutindexIds.length === 0) {
        error.value = 'No valid gutindex_id found.';
        loading.value = false;
        return;
      }
      else{
        console.log("🔗 This is the summary gen using gutindex_ids:", gutindexIds);
      }
  
      const remoteRes = await axios.post(
        '/api/create_summary',
        { gutindex_ids: gutindexIds },
        {
          headers: {
            Authorization: 'Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162',
            'Content-Type': 'application/json'
          }
        }
      );

      console.log(remoteRes);
  
      const summaryText = remoteRes.data.summary;
      const summaryTitleText = remoteRes.data.title;
      
      const localRes = await axios.post(`${LOCAL_API_BASE}/summary`, {
        summary: summaryText,
        summary_title: summaryTitleText
      });
      
      summaryTitle.value = localRes.data.summary_title;

        // Emit the event to notify the parent component
      emit('summary-generated');
      showToastWithTimeout();


    } catch (err) {
      console.error('Error during summarization:', err);
      error.value = 'Something went wrong during summarization.';
    } finally {
      loading.value = false;
    }
  };
  const showToast = ref(false);

const showToastWithTimeout = () => {
  showToast.value = true;
  setTimeout(() => {
    showToast.value = false;
  }, 3000);
};
  </script>
  
  
<style scoped>
.summary-button-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  width: auto;
  font-family: 'Noto Sans', sans-serif;
  
}

.summarize-button {
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;

  padding: 10px 20px;
  font-size: 18px;
  font-weight: 500;
  color: #fcfcfc;
  background-color: var(--primary-color);
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  box-shadow: 5px 5px 15px rgba(12, 73, 157, 0.2);
  transition: background-color 0.3s ease;
  box-sizing: border-box;
  text-align: left;

  width: fit-content;
  max-width: 100%;
}


.summarize-button:hover {
  background-color: var(--primary-color);
}

.summarize-button:disabled {
  background-color: #bcd9ee;
  color: #e2e8f0;
  cursor: not-allowed;
  box-shadow: none;
}

.spinner {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

.spinner .path {
  stroke: white;
  stroke-linecap: round;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

.summary-message {
  font-size: 0.95rem;
  margin-top: 6px;
}

.summary-message.success {
  color: #16a34a;
}

.summary-message.error {
  color: #dc2626;
}

.toast-notification {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: #e6f9ec;
  color: #16a34a;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 999;
  max-width: 300px;
}

.toast-notification strong {
  font-weight: bold;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 16px;
  color: #16a34a;
  cursor: pointer;
  margin-left: auto;
}

/* Fade in/out animation */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

</style>