<template>
    <div class="app-container">
        <ChangePanelsBtn v-model:mode="displayMode" />
        
        <SidePanel
            v-if="selectedSummary"
            :summary="selectedSummary"
            @close="closePanel"
        />
        
        <!-- Chat Section -->
        <div v-if="showChat" 
             class="chat-section"
             :class="{ 'full-width': displayMode === 'chat' }"
             v-show="showChat">
            <Chat :selectedNodes="selectedNodes" v-model:loading="loadingFromChat" :displayMode="displayMode" />
        </div>

        <div v-if="showGraph" 
             class="books-section"
             :class="{ 'full-width': displayMode === 'graph' }"
             v-show="showGraph">

            <!-- Relation Graph -->
            <div class="content-section">
                <div v-if="loadingFromChat" class="graph-overlay">
                    <div class="spinner"></div> 
                    <div class="loading-text">Loading...</div>
                </div>
                <div class="info-section floating" v-if="selectedNodes.length > 0">
                    <Info :selectedNodes="selectedNodes" @select-summary="handleSelectSummary"/>
                    <!-- <Info :selectedNodes="selectedNodes" @select-summary="handleSelectSummary" @close-info-panel="selectedNodes = []"/> -->
                </div>
                <Slot2Demo :setSelectedBook_IDs="setSelectedBook_IDs" />
            </div>

            <!-- Selected Book Information -->
            <!-- <div class="info-section" v-if="selectedNodes.length > 0">
                <Info :selectedNodes="selectedNodes" @select-summary="handleSelectSummary" />
            </div> -->
            <div 
                v-if="['graph'].includes(displayMode)" 
                class="search-section"
                >
                <SearchBar 
                    @books-updated="books = $event"
                    v-model:loading="loadingFromChat"
                    :displayMode="displayMode"
                />
            </div>
        </div>
        
        <div v-if="showSemanticSearch" 
             class="books-section"
             :class="{ 'full-width': displayMode === 'SS' }"
             v-show="showSemanticSearch">
            <!-- Book List -->
            <div 
                v-if="['SS'].includes(displayMode)" 
                class="search-section"
                >
                <SearchBar 
                    @books-updated="books = $event"
                    v-model:loading="loadingFromChat"
                    :displayMode="displayMode"
                />
            </div>
            <div 
            class="books-list-section"
            >
                <div v-if="loadingFromChat" class="graph-overlay">
                    <div class="spinner"></div> 
                    <div class="loading-text">Loading...</div>
                </div>
                <BookList :books="books" :displayMode="displayMode" />
            </div>
        </div>
    </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue';
import Chat from './chat.vue';
import Slot2Demo from './node-slots/use-slot2.vue';
import Info from './node-slots/info.vue';
import SidePanel from './components/summary-side.vue';
import ChangePanelsBtn from './components/change-panels-btn.vue';
import SearchBar from './components/search-bar.vue';
import BookList from './components/book-list.vue';
import { log } from 'console';


const displayMode = ref('all');
const loadingFromChat = ref(false);

const showChat = computed(() => ['all', 'chat'].includes(displayMode.value));
const showGraph = computed(() => ['all', 'graph'].includes(displayMode.value));
const showSemanticSearch = computed(() => ['SS'].includes(displayMode.value));

const selectedNodes = ref<string[]>([]);

const selectedSummary = ref<any>(null);

const books = ref([]);

const setSelectedBook_IDs = (ids: string[]) => {
  selectedNodes.value = ids;
};

const handleSelectSummary = (summary: any) => {
  selectedSummary.value = summary;
};
const closePanel = () => {
  selectedSummary.value = null;
};
// const handleSearch = (searchText) => {
//   console.log('Search text:', searchText);
// };

// const handleSearch = async (queryText: string) => {
//   try {
//     const response = await fetch('/api/query_books_graph', {
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json',
//         'Authorization': 'Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162'
//       },
//       body: JSON.stringify({ query: queryText, n: 1 })
//     });

//     const data = await response.json();
//     const nodes = data.graph?.nodes || [];

//     console.log('Fetched nodes:', nodes);
    
//     books.value = nodes.map((node: any) => ({
//       id: node.id,
//       title: node.data.title,
//       author: node.data.author,
//       pic: node.data.pic
//     }));
//   } catch (err) {
//     console.error('Fetch failed:', err);
//   }
// };

</script>

<style scoped>
/* Main Layout */
.app-container {
    display: flex;
    height: calc(100vh - 10px);; 
    min-height: 600px;
    width: 100%; 
    gap: 10px;
    padding: 5px;
    box-sizing: border-box;
    background: var(--secondary-color);
}

/* .chat-section,
.books-section {
    transition: all 0.2s ease-in-out;
} */


.chat-section {
    flex-basis: 25%;
    width: 40%;
    height: 100%; 
    border-radius: 15px;
    background: white;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 15px;
    box-sizing: border-box; 
}


.full-width {
    flex-basis: 100% !important;
    width: 100% !important;
    max-width: 2000px !important;  
    margin: 0 auto !important;     
}


.chat-section::-webkit-scrollbar {
    width: 8px;
}

.chat-section::-webkit-scrollbar-thumb {
    background: #ccc;
    border-radius: 10px;
}

.chat-section::-webkit-scrollbar-thumb:hover {
    background: #aaa;
    
}

/* Books Display Section (includes relation graph + book details) */
.books-section {
    flex-grow: 1;
    height: 100%;
    width: 60%;
    display: flex;
    gap: 10px;
    flex-direction: column;
    overflow: hidden;
    box-sizing: border-box;
}

/* Relation Graph Section */
.content-section {
    flex-grow: 1;
    display: flex;
    height: 100%; 
    flex-direction: column;
    position: relative;
    padding: 15px;
    border-radius: 15px;
    overflow: hidden;
    box-sizing: border-box; 
    background-color: white;
}


/* Book Information Section */
.info-section {
    height: auto;

    background: white;
    padding: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    border-radius: 15px;
}

.info-section.floating {
  position: absolute;
  bottom: 16px;
  left: 16px;
  z-index: 900;               
  max-width: 60vw;            
  max-height: 60vh;  
  height: auto;         
  overflow: visible;             
  padding: 12px;
  border-radius: 12px;
  background-color: transparent;
  


  
  pointer-events: auto;
}
.search-section {
    height: auto;
    background: white;
    padding: 10px;
    display: flex;
    align-items: center;

    box-sizing: border-box;
    border-radius: 15px;
}
.books-list-section {
  position: relative; 
  background: white;
  padding: 10px;
  display: flex;
  flex-direction: column;
  overflow: auto;
  border-radius: 15px;
  box-sizing: border-box;
  flex: 1;
}
.graph-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(240, 240, 240, 0.4);
  backdrop-filter: blur(6px); 
  -webkit-backdrop-filter: blur(6px);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  font-size: 1.2rem;
  font-weight: bold;
  color: #444;
  pointer-events: all;
  border-radius: 15px;
  user-select: none;
  pointer-events: all;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 5px solid #ccc;
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 5px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.loading-text {
  font-size: 20px;
  color: #555;
}


</style>
<style>
body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  box-sizing: border-box;

}
html {
    background-color: var(--secondary-color);
    box-sizing: border-box;
    padding: 5px;

}
</style>