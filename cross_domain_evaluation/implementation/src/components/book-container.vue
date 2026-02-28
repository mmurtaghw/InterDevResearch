<template>
    <div class="book-container">
      <div v-if="nodeTitles.length || edgeTitles.length" class="file-selected">
        <img src="../icon/icon-file.svg" alt="Folder Icon" class="icon" />
        <span class="text">
          Selected:
          <em v-if="nodeTitles.length">{{ nodeTitles.join(', ') }}</em>
          <span v-if="nodeTitles.length && edgeTitles.length"> & </span>
          <em v-if="edgeTitles.length">
            <span v-for="(edge, index) in edgeTitles" :key="index">
              {{ edge.fromTitle }} - {{ edge.toTitle }}:
              <br />
              <span v-if="edge.reasons.length">
              <span v-for="(reason, i) in edge.reasons" :key="i">
                {{ reason }}<br />
                </span>
              </span>
              <span v-else>No reason</span>
              <span v-if="index < edgeTitles.length - 1">, </span>
            </span>
          </em>
        </span>
      </div>
      <div v-else class="file-unselected">
        <img src="../icon/icon-file.svg" alt="Folder Icon" class="icon" />
      </div>
    </div>
</template>
  
  <script setup lang="ts">
  import { defineProps, watch, ref } from 'vue'
  import axios from 'axios'
  
  const props = defineProps({
    selectedNodes: {
      type: Array as () => string[],
      default: () => []
    },
    selectedEdges: {
      type: Array as () => { id: string; from: string; to: string }[],
      default: () => []
    }
  })
  
  const nodeTitles = ref<string[]>([])
  const edgeTitles = ref<
    { fromTitle: string; toTitle: string; reasons: string[] }[]
  >([])
  
  const fetchTitle = async (id: string): Promise<string> => {
    try {
      const res = await axios.post('http://localhost:2600/books/node-attribute', {
        id,
        attribute: 'title'
      })
      return res.data
    } catch (e) {
      console.error(`Failed to fetch title for id ${id}`, e)
      return id
    }
  }
  
  const fetchReasons = async (from: string, to: string): Promise<string[]> => {
    try {
      const res = await axios.post('http://localhost:2600/books/reasons-between', {
        from,
        to
      })
      return res.data.reasons || []
    } catch (e) {
      console.error(`Failed to fetch reasons between ${from} and ${to}`, e)
      return []
    }
  }
  
  watch(
    () => props.selectedNodes,
    async (newNodes) => {
      nodeTitles.value = await Promise.all(newNodes.map(id => fetchTitle(id)))
    },
    { immediate: true }
  )
  
  watch(
    () => props.selectedEdges,
    async (newEdges) => {
      const titles = await Promise.all(newEdges.map(async edge => {
        const fromTitle = await fetchTitle(edge.from)
        const toTitle = await fetchTitle(edge.to)
        const reasons = await fetchReasons(edge.from, edge.to)
        return { fromTitle, toTitle, reasons }
      }))
      edgeTitles.value = titles
    },
    { immediate: true }
  )
  </script>
  
  
  
  <style scoped>
.book-container {
  position: absolute;
  left: 20px; 
  bottom: 10px; 
  z-index: 1000; 
}
  
  .file-selected {
    display: flex;
    align-items: center;
    background-color: var(--primary-color);
    padding: 10px 15px 10px 10px;
    border-radius: 15px;
    color: white;
    font-size: 14px;
    font-weight: bold;
    box-shadow: 0 4px 10px rgba(59, 130, 246, 0.4);
    max-width: 100%;
    flex-wrap: wrap;        
    white-space: normal;    
    overflow: visible;      
    text-overflow: clip;    
    
  }
  
  .file-selected .icon {
    width: 30px;
    height: 30px;
    margin-right: 10px;
    border-radius: 15px;
  }
  
  .file-unselected {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 50px;
    height: 50px;
    background-color: var(--primary-color);
    border-radius: 15px;
    box-shadow: 0 4px 10px rgba(59, 130, 246, 0.4);
  }
  
  .file-unselected .icon {
    width: 30px;
    height: 30px;
  }
  </style>
  