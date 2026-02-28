<template>
    <div class="summary-button-wrapper">
      <button class="summarize-button" @click="handleDelete">
        <span>Delete Graph</span>
      </button>
  
      <!-- ❌ Error Toast -->
      <transition name="fade">
        <div v-if="showErrorToast" class="toast-notification error">
          <span>❌ Failed to delete. Please try again.</span>
          <button class="close-btn" @click="showErrorToast = false">×</button>
        </div>
      </transition>
  
      <!-- ✅ Success Toast -->
      <transition name="fade">
        <div v-if="showSuccessToast" class="toast-notification success">
          <span>✅ Graph data deleted successfully.</span>
          <button class="close-btn" @click="showSuccessToast = false">×</button>
        </div>
      </transition>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  import axios from 'axios';
  import eventBus from '../utils/eventBus'; // Import event bus
  
  const showErrorToast = ref(false);
  const showSuccessToast = ref(false);
  const LOCAL_API_BASE = 'http://localhost:2600';
  
  const handleDelete = async () => {
    showErrorToast.value = false;
    showSuccessToast.value = false;
  
    try {
      const res = await axios.delete(`${LOCAL_API_BASE}/books`);
      if (res.status === 200) {
        showSuccessToast.value = true;
        eventBus.emit("refreshGraph");
        eventBus.emit("clearBookInfo");
        setTimeout(() => (showSuccessToast.value = false), 3000);
      } else {
        throw new Error('Unexpected response');
      }
    } catch (err) {
      console.error('Delete error:', err);
      showErrorToast.value = true;
      setTimeout(() => (showErrorToast.value = false), 3000);
    }
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
    background-color: #e84545;
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    box-shadow: 5px 5px 15px rgba(157, 41, 12, 0.2);
    transition: background-color 0.3s ease;
    box-sizing: border-box;
    text-align: left;
  
    width: fit-content;
    max-width: 100%;
  }
  
  .summarize-button:hover {
    background-color: #d23636;
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
  
  .toast-notification.success {
    background-color: #ecfdf5;
    color: #059669;
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
  