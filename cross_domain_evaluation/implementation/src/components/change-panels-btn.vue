<template>
  <div class="mode-switcher" v-show="isVisible">
    <el-radio-group v-model="currentMode" @change="handleModeChange">
      <el-radio-button label="all">All Panels</el-radio-button>
      <el-radio-button label="chat">Chat Only</el-radio-button>
      <el-radio-button label="graph">Graph Only</el-radio-button>
      <el-radio-button label="SS">SS</el-radio-button>
    </el-radio-group>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted } from 'vue';

const currentMode = ref('all');
const isVisible = ref(false);
let hideTimeout: number | null = null;

const emit = defineEmits(['update:mode']);

const handleModeChange = (value: string) => {
  emit('update:mode', value);
};


const handleKeyDown = (event: KeyboardEvent) => {

    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    showButton();
    }
};


const showButton = () => {
  isVisible.value = true;
  

  if (hideTimeout) {
    clearTimeout(hideTimeout);
  }
  
  // hide the button after 10 seconds
  hideTimeout = setTimeout(() => {
    isVisible.value = false;
  }, 8000);
};


onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});


onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
  if (hideTimeout) {
    clearTimeout(hideTimeout);
  }
});
</script>

<style scoped>
.mode-switcher {
  position: fixed;
  top: 20px;
  left: 20px;  
  z-index: 10000;
  opacity: 0;
  transform: translateY(-20px) scale(0.85);
  transition: all 0.3s ease;
  animation: fadeIn 0.3s ease forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.85);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(0.85);
  }
}


:deep(.el-radio-button__inner) {
  background-color: white;
  border-color: var(--el-border-color);
  color: var(--el-text-color-primary);
  border-radius: 10px;  
  margin: 0 2px;  
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: white;
  font-size: 10px;
}

:deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: 10px;
}

:deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 10px;
}
</style>