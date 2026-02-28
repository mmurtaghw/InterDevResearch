<template>
  <div class="search-container">
    <div class="search-box">
      <input
        v-model="searchText"
        @keyup.enter="handleSearch"
        placeholder="Type to search..."
        class="search-input"
        :disabled="loading"
      />
      <button @click="handleSearch" class="search-button" :disabled="loading">
        <img v-if="!loading" src="../icon/icon-arrow.svg" alt="Search" class="search-icon" />
        <img
          v-else
          src="../icon/icon-stop.svg"
          alt="Disabled"
          class="stop-icon"
        />
      </button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, toHandlers } from 'vue';
import axios from 'axios';
import eventBus from '@/utils/eventBus';
import { returnBooksNumber } from '@/utils/globalConfig'

console.log('Current returnBooksNumber:', returnBooksNumber.value)

const searchText = ref('');
const loading = ref(false);


const props = defineProps({
  loading: Boolean,
  displayMode: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:loading', 'books-updated']);

const handleSearch = async () => {
  if (!searchText.value.trim() || loading.value) return;
  
  console.log('displayMode', props.displayMode);

  loading.value = true;
  emit('update:loading', true); 

  // semantic search mode
  if (props.displayMode == 'SS') {
    
    console.log(`[fetchBooks]Searching for books related to: "${searchText.value}"...`);

    try {
    const response = await fetch('/api/query_books_graph', {
        method: 'POST',
        headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162'
        },
        body: JSON.stringify({ query: searchText.value, n: returnBooksNumber.value, mode:'chat'})
    });
    

    const data = await response.json();
    const nodes = data.graph?.nodes || [];

    console.log('get json', data);

    const books = nodes.map((node: any) => ({
        id: node.data.gutindex_id,
        title: node.data.title,
        author: node.data.author,
        pic: node.data.pic,
        downloadLink: node.data.book_download || '', // Ensure download link is included
    }));

    console.log('Fetched books:', books);
    emit('books-updated', books);
    } catch (error) {
    console.error('Search failed:', error);
    } finally {
    loading.value = false;
    emit('update:loading', false);
    }
  } else {
    // graph mode
        try {
        console.log(`[getBookGraph]Fetching books related to: "${searchText.value}"...`);

        const response = await axios.post(
        "/api/query_books_graph",
        { 
            query: searchText.value, 
            n: returnBooksNumber.value,
            mode: 'graph' // Specify the mode for graph search
        },
        {
            headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162"
            }
        }
        );

        console.log("Books API Response:", response.data);

        const graph = response.data?.graph;
        if (graph) {
        const { lines, nodes, rootId } = graph;

        if (lines && nodes && rootId) {
            await axios.post("http://localhost:2600/books", 
            { lines, nodes, rootId }, 
            {
                headers: { "Content-Type": "application/json" }
            }
            );
            console.log("✅ Books data stored successfully.");
            eventBus.emit("refreshGraph");
        } else {
            console.error("❌ Invalid graph structure:", graph);
        }
        }

    } catch (error) {
        console.error("Error fetching or storing books:", error);
    } finally {
        loading.value = false;
        emit('update:loading', false);
        searchText.value = '';
    }
    }
};

// const getBookGraph = async () =>{
//     try {
//     console.log(`[getBookGraph]Fetching books related to: "${searchText.value}"...`);

//     const response = await axios.post(
//       "/api/query_books_graph",
//       { 
//         query: searchText.value, 
//         n: 4 
//       },
//       {
//         headers: {
//           "Content-Type": "application/json",
//           "Authorization": "Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162"
//         }
//       }
//     );

//     console.log("Books API Response:", response.data);

//     const graph = response.data?.graph;
//     if (graph) {
//       const { lines, nodes, rootId } = graph;

//       if (lines && nodes && rootId) {
//         await axios.post("http://localhost:2600/books", 
//           { lines, nodes, rootId }, 
//           {
//             headers: { "Content-Type": "application/json" }
//           }
//         );
//         console.log("✅ Books data stored successfully.");
//         eventBus.emit("refreshGraph");
//       } else {
//         console.error("❌ Invalid graph structure:", graph);
//       }
//     }

//   } catch (error) {
//     console.error("Error fetching or storing books:", error);
//   } finally {
//     loading.value = false;
//     emit('update:loading', false);
//     searchText.value = '';
//   }
// }


// const fetchBooks = async () => {
//   if (!searchText.value.trim() || loading.value) return;

//   loading.value = true;
//   emit('update:loading', true);

//   console.log(`[fetchBooks]Searching for books related to: "${searchText.value}"...`);

//   try {
//     const response = await fetch('/api/query_books_graph', {
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json',
//         'Authorization': 'Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162'
//       },
//       body: JSON.stringify({ query: searchText.value, n: 3})
//     });
    

//     const data = await response.json();
//     const nodes = data.graph?.nodes || [];

//     console.log('get json', data);

//     const books = nodes.map((node: any) => ({
//       id: node.gutindex_id,
//       title: node.data.title,
//       author: node.data.author,
//       pic: node.data.pic
//     }));

//     console.log('Fetched books:', books);
//     emit('books-updated', books);
//   } catch (error) {
//     console.error('Search failed:', error);
//   } finally {
//     loading.value = false;
//     emit('update:loading', false);
//   }
// };

</script>

<style scoped>
.search-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-sizing: border-box;
  width: 100%;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: white;
  padding: 10px;
  border-radius: 12px;
  box-sizing: border-box;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  border: 2px solid var(--light-grey);
}

.search-input {
  flex: 1;
  border: none;
  border-radius: 8px;
  font-size: var(--font-size);
  padding: 10px;
  outline: none;
  background: white;
  box-sizing: border-box;
}

.search-button {
  background-color: var(--primary-color);
  border: none;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 5px 5px 15px rgba(12, 73, 157, 0.1);
}

.search-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.search-icon,
.stop-icon {
  width: 24px;
  height: 24px;
}
</style>