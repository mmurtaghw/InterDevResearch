<template>
    <!-- Container for book information, shown only if there is at least one selection -->
    <div class="book-info-container" v-if="selectedNodes.length">
        <div class="book-function" ref="bookFunctionRef">
            <!-- <h2 class="panel-title">Book List Functions</h2> -->
            <div class="summary-button">
            <SummaryButton 
                :selectedNodes="selectedNodesRef"
                @summary-generated="onSummaryGenerated" />
            <DownloadButton :selectedNodes="selectedNodesRef" />
            <DetailsButton :selectedNodes="selectedNodesRef" />
            <DeleteGraphButton />
            </div>
        </div>

        <div class="info-panel" v-if="selectedNodes.length" ref="infoPanelRef">
        <div class="info-container" ref="infoContainerRef">
            <!-- Summary Button -->
            <div class="book-info" >
                <h2 class="panel-title">Selected Book Info</h2>
                <div class="info-box">
                <p><strong class="label">Title:</strong> {{ bookTitle }}</p>
                <p><strong class="label">Author:</strong> {{ bookAuthor }}</p>
                <p><strong class="label">ID:</strong> {{ bookID }}</p>
                <p><strong class="label">Categories:</strong></p>
                <ul class="category-list">
                    <li v-for="(category, index) in bookCategories.slice(0, 2)" :key="index">{{ category }}</li>
                </ul>
                <p><strong class="label">Quick Summary:</strong></p>
                <p>{{ bookQuickSummary }}</p>
                </div>
            </div>

        </div>
    
        <!-- Summary List -->
        <div class="summary-list-wrapper" :style="{ height: containerHeight + 'px' }">
            <h2 class="panel-title">Summary List</h2>
            <!-- <div class="fade-overlay top"></div>
            <div class="fade-overlay bottom"></div> -->
            <SummaryList
            ref="summaryListRef"
            @select="handleSummarySelect"
            />
        </div>
        </div>
    </div>

  </template>
  
  
  
  <script lang="ts" setup>
  import { defineProps, watch, ref, computed, toRef, onMounted,onBeforeUnmount, nextTick } from 'vue';
  import SummaryButton from '../components/summary-gen-btn.vue'; 
  import DownloadButton from '../components/book-download-btn.vue';
  import SummaryList from '../components/summary-list.vue'
  import DeleteGraphButton from '../components/delete-graph-btn.vue'
  import DetailsButton from '../components/book-details-btn.vue';
  import eventBus from '../utils/eventBus';

  const emit = defineEmits(['select-summary','close-info-panel']);
  
  const props = defineProps({
    selectedNodes: {
      type: Array as () => string[],
      required: true
    }
  });
  
  const selectedNodesRef = toRef(props, 'selectedNodes');
  
  const bookTitle = ref('');
  const bookAuthor = ref('');
  const bookID = ref('');
  const bookCategories = ref<string[]>([]);
  const bookQuickSummary = ref('');
  

    const bookFunctionRef = ref(null)
    const infoPanelRef = ref(null)

    function handleClickOutside(event: MouseEvent) {
    const target = event.target as Node

    const clickedInsideFunction = bookFunctionRef.value?.contains(target)
    const clickedInsideInfo = infoPanelRef.value?.contains(target)

    if (!clickedInsideFunction && !clickedInsideInfo) {
        emit('close-info-panel')  
    }
    }

  const currentSelectedId = computed(() => {
    return props.selectedNodes.length > 0
      ? props.selectedNodes[props.selectedNodes.length - 1]
      : null;
  });
  
  watch(currentSelectedId, async (id) => {
    if (!id) return;
  
    try {
      const [titleRes, authorRes, idRes, categoriesRes, tinySummaryRes] = await Promise.all([
        fetch('http://localhost:2600/books/node-attribute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, attribute: 'title' })
        }).then(res => res.json()),
        fetch('http://localhost:2600/books/node-attribute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, attribute: 'author' })
        }).then(res => res.json()),
        fetch('http://localhost:2600/books/node-attribute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, attribute: 'gutindex_id' })
        }).then(res => res.json()),
        fetch('http://localhost:2600/books/node-attribute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, attribute: 'subjects' })
        }).then(res => res.json()),
        fetch('http://localhost:2600/books/node-attribute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, attribute: 'tiny_summary' })
        }).then(res => res.json())
      ]);
     
      bookTitle.value = titleRes;
      bookAuthor.value = authorRes;
      bookID.value = idRes;
      bookCategories.value = categoriesRes;
      bookQuickSummary.value = tinySummaryRes;

    } catch (error) {
      console.error('Fail to get the attribute:', error);
      bookTitle.value = '';
      bookAuthor.value = '';
      bookID.value = '';
      bookCategories.value = '';
      bookQuickSummary.value = '';
    }
  }, { immediate: true });
  
  const summaryListRef = ref(null)
  
  function onSummaryGenerated() {
    console.log('🧪 summaryListRef.value =', summaryListRef.value)
  
    if (summaryListRef.value && summaryListRef.value.fetchSummaries) {
      summaryListRef.value.fetchSummaries();  
    } else {
      console.warn('⚠️ summaryListRef is null or fetchSummaries is not exposed!');
    }
  }
  
  function handleSummarySelect(summaryItem) {
    emit('select-summary', summaryItem)
  }
  
  const infoContainerRef = ref(null)
  const containerHeight = ref(0)
  
  const updateContainerHeight = () => {
    if (infoContainerRef.value) {
      containerHeight.value = infoContainerRef.value.offsetHeight
      console.log('📏 containerHeight =', containerHeight.value)
    }
  }
  
  onMounted(async () => {
  await nextTick();
  updateContainerHeight();
  window.addEventListener('resize', updateContainerHeight);
  document.addEventListener('click', handleClickOutside)
  
  eventBus.on('clearBookInfo', () => {
    bookTitle.value = '';
    bookAuthor.value = '';
    bookID.value = '';
    bookCategories.value = [];
    bookQuickSummary.value = '';
  });
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateContainerHeight);
  document.removeEventListener('click', handleClickOutside);
  eventBus.off('clearBookInfo'); // 
});
  watch(selectedNodesRef, async () => {
    await nextTick()
    updateContainerHeight()
  })
  </script>
  
  
  <style scoped>
  .book-info-container{

    background: transparent;
    box-sizing: border-box;
    display: flex;
  flex-direction: column;
  gap: 20px;
  }
  .info-panel {
    width: 100%;
    padding: 20px;

    display: flex;
    flex-direction: row;
    justify-content: space-between;
    gap:10px;
    box-sizing: border-box;
    height: auto;
    border-radius: 15px;

    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    box-shadow: 0 5px 24px rgba(0, 0, 0, 0.1);
  }
  .info-container {
    display: flex;
    flex-direction: column;
    height: 300px;
    width: 50%;
    justify-content: space-between;
  }
  
  .book.info {

  }
  
  .panel-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--primary-color);
    margin: 0;
  }
  
  .info-box {
    padding: 0;
    padding-left: 16px;
    font-size: 1rem;
    line-height: 1.6;
    color: #333;
  }
  
  .info-box p {
    margin: 2px 0;
    font-size: var(--font-size);
  }
  
  .label {
    font-weight: 500;
    
    color: var(--primary-color);
  }
  
  .summary-button {
    width: 100%;
    display: flex;
    justify-content: flex-start;
    gap: 16px;
    height: auto;
  }
  
  .summary-list-wrapper {
    flex: 1;
    padding-left: 32px;
    border-left: 1px solid #eee;
    overflow: hidden;
  }
  .fade-overlay {
  position: absolute;
  left: 0;
  width: calc(100% - 6px);;
  height: 40px;
  z-index: 1;
  pointer-events: none;
}
.fade-overlay.top {
  top: 0;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.3), transparent);
}
.fade-overlay.bottom {
  bottom: 0;
  background: linear-gradient(to top, rgba(255, 255, 255, 0.3), transparent);
}

.summary-list-wrapper {
  position: relative; 
  overflow: hidden;
  height: 300px;
  flex: 1;
  padding-left: 32px;
  border-left: 1px solid #eee;
}
.category-list {
  margin: 0;
  padding-left: 1em;
  font-size: var(--font-size);
}

.category-list li {
  list-style-type: disc;
  margin-left: 0.5em;
}

.book-function {
    display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
}

  </style>
  