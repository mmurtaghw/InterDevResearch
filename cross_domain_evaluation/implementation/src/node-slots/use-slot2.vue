<template>
    <div style="height:calc(100vh);" @click="clearSelection">
        <div class="graph-container">
        <div class="multi-select-tip">
            <em>Hold <strong>Shift</strong> to multi-select nodes</em>
        </div>
        <!-- Add this near the root of your template, outside <RelationGraph> -->
            <div v-if="!hasData" class="empty-message-overlay">
            <h1 class="headline">No Books Found Yet</h1>
            <!-- <p class="subtext">Click <strong>Find Books</strong> and talk to <strong>Althena</strong> to begin building your library.</p> -->
            <p class="subtext">Talk to <strong>Althena</strong> to begin building your library.</p>
            </div>

        <!-- Relation Graph Component -->
        <RelationGraph 
            ref="graphRef" 
            :options="graphOptions" 
            @onNodeClick="handleNodeClick"
            @onLineClick="handleLineClick"
        >
            <template #node="{ node }">
                <div 
                    class="c-node-container" 
                    :class="{ 'c-node-selected': selectedNodes.includes(node.id) }"
                    @click.stop
                >
                    <div class="c-node-content">
                        <div class="c-node-header">
                            <i class="el-icon-user" /> Title: {{ node.data.title }}
                        </div>
                        <div class="c-node-info">Author: {{ node.data.author }}</div>
                        <div class="c-node-photo" v-if="node.data.pic">
                            <span>Photo:</span>
                            <img class="c-person-pic" :src="node.data.pic" />
                        </div>
                    </div>
                </div>
            </template>
        </RelationGraph>
        <!-- Display selected nodes -->
        <BookContainer class="book-container" :selectedNodes="selectedNodes" :selectedEdges="selectedEdges" />
        </div>
    </div>
  </template>
  
  
  <script lang="ts" setup>
import { ref, onMounted, onUnmounted, defineProps } from 'vue';
import type { RGOptions, RGJsonData, RelationGraphComponent } from 'relation-graph-vue3';
import RelationGraph from 'relation-graph-vue3';
import eventBus from '../utils/eventBus'; // Import event bus
import BookContainer from '../components/book-container.vue';

const graphRef = ref<RelationGraphComponent | null>(null);
const selectedNodes = ref<string[]>([]);
const selectedEdges = ref<{ id: string; from: string; to: string }[]>([]);
const graphData = ref<RGJsonData | null>(null);
const hasData = ref(false)


// Receive the method passed from App.vue
const props = defineProps({
    setSelectedBook_IDs: Function, // Method provided by App.vue
});

const graphOptions: RGOptions = {
    defaultExpandHolderPosition: 'top',
    defaultNodeBorderWidth: 1,
    defaultNodeColor: 'rgba(232, 232, 232, 1)',
    defaultNodeFontColor: 'rgba(62, 62, 62, 1)',
    defaultLineShape: 5,
    defaultNodeShape: 1,
    defaultLineWidth: 1,
    defaultShowLineLabel: false,
    maxZoom: 2,
    layouts: [
      {
        label: 'Center',
        layoutName: 'center',
        centerOffset_x: 0,
        centerOffset_y: 0,
        distance_coefficient: 1
      }
    ]
};

// Fetch graph data from backend
// const fetchGraphData = async () => {
//     try {
//         const response = await fetch("http://localhost:2600/books");
//         if (!response.ok) {
//             throw new Error(`HTTP error! Status: ${response.status}`);
//         }
//         graphData.value = await response.json();
//         showGraph();
//     } catch (error) {
//         console.error("Failed to fetch graph data:", error);
//     }
// };
const fetchGraphData = async () => {
  try {
    const response = await fetch("http://localhost:2600/books");
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    graphData.value = data;

    // Check if there are any nodes or lines
    const hasNodes = Array.isArray(data.nodes) && data.nodes.length > 0;
    const hasLines = Array.isArray(data.lines) && data.lines.length > 0;
    hasData.value = hasNodes || hasLines;

    showGraph();

  } catch (error) {
    console.error("Failed to fetch graph data:", error);
    hasData.value = false;
  }
};

// Handle node click event
const handleNodeClick = (node, event) => {
    if (event?.stopPropagation) event.stopPropagation();

    const id = node.id;
    const title = node.data?.title;
    const gutindexId = node.data?.gutindex_id;

    if (!id || !title || gutindexId === undefined) return;

    // 多选处理
    if (event?.shiftKey) {
        if (selectedNodes.value.includes(id)) {
            selectedNodes.value = selectedNodes.value.filter(existingId => existingId !== id);
        } else {
            selectedNodes.value.push(id);
        }
    } else {
        selectedNodes.value = [id];
    }

    console.log("Selected Node ID:", id);
    console.log("Selected Nodes:", selectedNodes.value);

    // ✅ 直接传 ref 的 value（string[]）
    if (props.setSelectedBook_IDs) {
        props.setSelectedBook_IDs(selectedNodes.value);
    }

    selectedEdges.value = [];

};




const handleLineClick = (line, event) => {
    if (event?.stopPropagation) {
        event.stopPropagation();
    }
    
    if (!line || !line.id || !line.from || !line.to) {
        console.warn("Invalid line data:", line);
        return;
    }
    
    const lineId = line.id;
    const from = line.from;
    const to = line.to;
    
    if (event?.shiftKey) {
        if (selectedEdges.value.some(edge => edge.id === lineId)) {
            selectedEdges.value = selectedEdges.value.filter(edge => edge.id !== lineId);
        } else {
            selectedEdges.value = [...selectedEdges.value, { id: lineId, from, to }];
        }
    } else {
        selectedEdges.value = [{ id: lineId, from, to }];
    }
    selectedNodes.value = [];
    
};

const clearSelection = () => {
    selectedNodes.value = [];
};

onMounted(() => {
    fetchGraphData();
    eventBus.on("refreshGraph", fetchGraphData); // Listen for events and refresh the graph when notified
});

onUnmounted(() => {
    eventBus.off("refreshGraph", fetchGraphData); // Remove listener when component is unmounted to prevent memory leaks
});
const showGraph = async () => {
    if (!graphData.value) return;
    const graphInstance = graphRef.value?.getInstance();
    if (graphInstance) {
        await graphInstance.setJsonData(graphData.value);
        await graphInstance.moveToCenter();
        await graphInstance.zoomToFit();
    }
};

  </script>
  
  <style scoped lang="scss">
    // Modify default graph styles
  ::v-deep(.relation-graph) {
    .c-rg-line-checked-bg {
        stroke: rgba(0, 123, 255, 0.2);
    }
    .c-rg-line-text-checked {
        stroke: rgba(254, 50, 50, 0.2);
    }
    .rel-node-checked {
          box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.3);
      }
  }
    ::v-deep canvas {
    max-height: 100% !important;
    max-width: 100% !important;
    }

    .graph-container {
    flex: 1;
    display: flex;
    height: 100%;
    flex-direction: column;
    position: relative;
    overflow: hidden;
    background-color: white
}
.multi-select-tip {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: var(--font-size);
  color: var(--dark-grey);
  z-index: 10;
  font-style: italic;
}

  .c-selected-nodes,
  .c-selected-edges {
    position: absolute;
    top: 20px;
    right: 20px;
    z-index: 1000;
    background: rgba(255, 255, 255, 0.9);
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #ddd;
    box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);
    margin-top: 5px;
    font-size: var(--font-size-small);
  }
  
  .c-selected-edges ul {
    padding-left: 20px;
    margin: 0;
  }
  
  .c-node-container {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    cursor: pointer;
    text-align: left;
    padding: 10px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    width: auto;
    min-width: 150px;
    max-width: 300px;
  }
  
  .c-node-header {
    font-size: var(--font-size);
    font-weight: bold;
    padding-bottom: 5px;
    border-bottom: 1px solid #ddd;
  }
  
  .c-node-info {
    font-size: var(--font-size-medium);
    padding: 5px 0;
    border-bottom: 1px solid #ddd;
  }
  
  .c-node-photo {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: var(--font-size);
    margin-top: 5px;
  }
  
  .c-node-selected {
    transition: background-color 0.2s ease, outline 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 1);
    background-color: rgba(0, 123, 255, 0.2);
  }
  .empty-message-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 10;
  max-width: 600px;
  padding: 20px;
  pointer-events: none; /* Allows clicks to pass through */
}

.empty-message-overlay .headline {
  font-size: 28px;
  color: #666;
  margin-bottom: 10px;
  font-weight: 600;
}

.empty-message-overlay .subtext {
  font-size: 22px;
  color: #999;
  line-height: 1.6;
}
.book-container {
  position: absolute;
  top: 10px;
  left: 20px;
  z-index: 10;
  padding: 0px;
  user-select: none;
  height: 10px;
}



  </style>