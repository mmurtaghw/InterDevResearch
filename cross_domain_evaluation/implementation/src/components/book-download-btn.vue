<template>
    <div class="summary-button-wrapper">
      <button
        class="summarize-button"
        @click="handleDownload"
        :disabled="props.selectedNodes.length === 0"
      >
        <span>Download Books</span>
      </button>
  
      <!-- ❌ Error Toast -->
      <transition name="fade">
        <div v-if="showErrorToast" class="toast-notification error">
          <span>❌ Some downloads failed. Please try again.</span>
          <button class="close-btn" @click="showErrorToast = false">×</button>
        </div>
      </transition>
    </div>
  </template>
  
  <script setup>
  // Import Vue composition API and axios
  import { ref, defineProps } from 'vue';
  import axios from 'axios';
  
  // Receive props from parent
  const props = defineProps({
    selectedNodes: {
      type: Array,
      required: true
    }
  });
  
  // State for showing error toast
  const showErrorToast = ref(false);
  
  const LOCAL_API_BASE = 'http://localhost:2600';
  
  // Fetch download URL for a node
  const fetchDownloadUrl = async (id) => {
    try {
      const res = await axios.post(`${LOCAL_API_BASE}/books/node-attribute`, {
        id,
        attribute: 'book_download'
      });
      return res.data;
    } catch (err) {
      console.error(`Error fetching book_download for node ${id}:`, err);
      return null;
    }
  };
  
  // Open a new tab with the download URL
  const openInNewTab = (url) => {
    window.open(url, '_blank');
  };
  
  // Handle download when button is clicked
  const handleDownload = async () => {
    showErrorToast.value = false;
  
    try {
      const urls = await Promise.all(
        props.selectedNodes.map(id => fetchDownloadUrl(id))
      );
  
      const validUrls = urls.filter(url => url && typeof url === 'string');
  
      validUrls.forEach(url => openInNewTab(url));
  
      // If some downloads failed, show error toast
      if (validUrls.length < props.selectedNodes.length) {
        showToastWithTimeout();
      }
  
    } catch (err) {
      console.error('Download error:', err);
      showToastWithTimeout();
    }
  };
  
  // Show error toast for 3 seconds
  const showToastWithTimeout = () => {
    showErrorToast.value = true;
    setTimeout(() => {
      showErrorToast.value = false;
    }, 3000);
  };
  </script>
  
  <style scoped>
  .summary-button-wrapper {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    width: 100%;
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
    background-color: var(--primary-color, #45a2e8);
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
    background-color: #3689cb;
  }
  
  .summarize-button:disabled {
    background-color: #bcd9ee;
    color: #e2e8f0;
    cursor: not-allowed;
    box-shadow: none;
  }
  
  .toast-notification {
    position: fixed;
    bottom: 20px;
    right: 20px;
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
  
  .toast-notification.error {
    background-color: #fdecea;
    color: #dc2626;
  }
  
  .close-btn {
    background: transparent;
    border: none;
    font-size: 16px;
    cursor: pointer;
    margin-left: auto;
  }
  
  .fade-enter-active,
  .fade-leave-active {
    transition: opacity 0.5s ease;
  }
  .fade-enter-from,
  .fade-leave-to {
    opacity: 0;
  }
  </style>
  