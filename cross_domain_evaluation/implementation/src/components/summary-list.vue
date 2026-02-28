<template>
  
      <div class="summary-list">
        <div
          v-for="(item, index) in summaries"
          :key="index"
          class="summary-item"
          :class="{ active: selectedIndex === index }"
          @click="handleClick(item, index)"
        >
          <div class="item-left">
            <svg
              class="icon"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5V3h6v2M9 5h6"
              />
            </svg>
            <span>{{ item.summary_title }}</span>
          </div>
  
          <button
            class="delete-button"
            @click.stop="confirmDelete(item.summary_title)"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              stroke="currentColor"
              fill="none"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

  
    <div v-if="deleteTarget" class="modal">
      <div class="modal-content">
        <p>
          Confirm delete <strong>{{ deleteTarget }}</strong> ?
        </p>
        <div class="modal-actions">
          <button @click="performDelete">Yes</button>
          <button @click="deleteTarget = null">No</button>
        </div>
      </div>
    </div>
  </template>



<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits(['select'])

const summaries = ref([])
const selectedIndex = ref(null)
const deleteTarget = ref(null)

const fetchSummaries = async () => {
  try {
    const response = await axios.get('http://localhost:2600/summary')
    summaries.value = response.data
  } catch (error) {
    console.error('Failed to fetch summaries:', error)
  }
}

const handleClick = (item, index) => {
  selectedIndex.value = index
  console.log('Title:', item.summary_title)
  console.log('Content:', item.summary)
  emit('select', item)
}

const confirmDelete = (title) => {
  deleteTarget.value = title
}

const performDelete = async () => {
  try {
    await axios.delete(`http://localhost:2600/summary/${encodeURIComponent(deleteTarget.value)}`)
    deleteTarget.value = null
    fetchSummaries()
  } catch (error) {
    console.error('Failed to delete summary:', error)
    alert('Delete failed. Please try again.')
  }
}

onMounted(fetchSummaries)

defineExpose({ fetchSummaries })
</script>

  
  <style scoped>
.summary-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  max-height: 100%;
  
  overflow-y: auto;
  box-sizing: border-box;

  scrollbar-width: thin;
  scrollbar-color: rgba(100, 100, 100, 0.3) transparent;
}

.summary-list::-webkit-scrollbar {
  width: 6px;
}

.summary-list::-webkit-scrollbar-track {
  background: transparent;
}

.summary-list::-webkit-scrollbar-thumb {
  background-color: rgba(100, 100, 100, 0.3);
  border-radius: 3px;
  transition: background-color 0.3s;
}

.summary-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(100, 100, 100, 0.5);
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background-color: #e6f2fb;
  border: 2px solid var(--primary-color);
  border-radius: 16px;
  color: var(--primary-color);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 8px rgba(0, 119, 204, 0.1);
}

.summary-item:hover {
  background-color: #d2eafd;
}

.summary-item.active {
  background-color: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.summary-item.active .icon {
  color: white;
}

.summary-item.active .delete-button {
  color: white;
}
.summary-item.active .delete-button:hover {
  color: #eca4a9; 
}

.item-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.icon {
  width: 20px;
  height: 20px;
  color: var(--primary-color);
}

.delete-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--primary-color);
  cursor: pointer;
  transition: color 0.2s;
}

.delete-button:hover {
  color: #ff4d4f;
}


.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1100;
}
.modal-content {
  background: white;
  padding: 1.5rem 2rem;
  border-radius: 8px;
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.2);
  text-align: center;
}
.modal-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}
.modal-actions button {
  padding: 0.4rem 1.2rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}
.modal-actions button:first-child {
  background-color: #d63636;
  color: white;
}
.modal-actions button:last-child {
  background-color: #f0f0f0;
}

</style>
