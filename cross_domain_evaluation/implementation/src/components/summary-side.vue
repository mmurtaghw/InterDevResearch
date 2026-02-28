<template>
    <transition name="slide">
      <div class="side-panel" v-if="summary">
        <div class="panel-header">
          <h3 class="panel-title">{{ summary.summary_title }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>
        <div class="panel-content-wrapper">
          <div class="fade-overlay top"></div>
          <div class="fade-overlay bottom"></div>
          <div class="panel-content" v-html="formattedSummary"></div>
        </div>
      </div>
    </transition>
  </template>
  
  <script setup>
  import { computed } from 'vue'
  import { marked } from 'marked'
  
  const props = defineProps({
    summary: Object
  })
  defineEmits(['close'])
  
  const formattedSummary = computed(() => {
    if (!props.summary?.summary) return ''
    
    // 替换单个 \n 为 markdown 段落分隔 \n\n
    const markdownText = props.summary.summary.replace(/\n/g, '\n\n')
    return marked.parse(markdownText)
  })
  </script>
  <style scoped>
  .side-panel {
    position: fixed;
    top: 0;
    left: 0;
    width: 600px;
    height: 100%;
    background-color: #fff;
    border-right: 1px solid #e5e5e5;
    box-shadow: 4px 0 12px rgba(0, 0, 0, 0.08);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    padding: 24px;
    box-sizing: border-box;
  }
  
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  
  .panel-title {
    font-size: 20px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0;
  }
  
  .close-btn {
    font-size: 24px;
    border: none;
    background: none;
    cursor: pointer;
    color: #888;
  }
  
  .panel-content-wrapper {
    position: relative;
    flex: 1;
    overflow: hidden;
  }
  
  .panel-content {
    height: 100%;
    overflow-y: auto;
    padding-right: 8px;
    padding-bottom: 24px;
    font-size: 15px;
    line-height: 1.6;
    color: #333;
  }
  
  /* 滚动条样式 */
  .panel-content::-webkit-scrollbar {
    width: 6px;
  }
  .panel-content::-webkit-scrollbar-thumb {
    background-color: #ccc;
    border-radius: 3px;
  }
  
  /* 渐变遮罩层 */
  .fade-overlay {
    position: absolute;
    left: 0;
    width: 100%;
    height: 40px;
    pointer-events: none;
    z-index: 2;
  }
  .fade-overlay.top {
    top: 0;
    background: linear-gradient(to bottom, white, rgba(255, 255, 255, 0));
  }
  .fade-overlay.bottom {
    bottom: 0;
    background: linear-gradient(to top, white, rgba(255, 255, 255, 0));
  }
  
  /* Markdown 样式 */
  .panel-content h1,
  .panel-content h2,
  .panel-content h3 {
    margin: 16px 0 8px;
    font-weight: 600;
  }
  .panel-content p {
    margin: 10px 0;
  }
  .panel-content ul {
    margin-left: 20px;
    list-style-type: disc;
  }
  </style>
  