<!--

This Vue component represents a chat interface with the following features:
- A header with a "Clear Chat" button to clear the chat history.
- A container to display chat messages, with support for Markdown formatting.
- An input field and a send button for users to send new messages.
- Automatic scrolling to the bottom of the chat messages when new messages are added.
- Loading state indication when waiting for AI response.

Data and Methods:
- `messages`: An array of chat messages.
- `newMessage`: The current message input by the user.
- `loading`: A boolean indicating if the AI is processing a response.
- `messagesContainer`: A reference to the chat messages container for scrolling.
- `HISTORY_KEY`: A constant key for storing chat history in localStorage.

Methods:
- `loadChatHistory`: Loads chat history from localStorage.
- `saveChatHistory`: Saves chat history to localStorage.
- `clearChatHistory`: Clears chat history from localStorage and resets the messages.
- `parseMarkdown`: Parses a text string into HTML using Markdown.
- `sendMessage`: Sends a new message, updates the chat with the AI response, and handles errors.
- `scrollToBottom`: Scrolls the chat messages container to the bottom.

Lifecycle Hooks:
- `onMounted`: Loads chat history when the component is mounted.

Styles:
- Scoped styles for the chat container, header, messages, input container, and buttons.
- Specific styles for user messages, Markdown content, and code blocks.
-->
<template>
    <div class="chat-container">
      <!-- Header -->
      <div class="chat-header">
        <h2 class="chat-title">Chat</h2>
        <div class="chat-actions">
          <button class="clear-button" @click="clearChatHistory">Clear Chat</button>
          <button class="export-button" @click="exportChatHistory">Export Chat</button>
        </div>
      </div>
  
      <!-- Chat messages with fade overlays -->
      <div class="chat-messages-wrapper">
        <div class="fade-overlay top"></div>
        <div class="fade-overlay bottom"></div>
  
        <div class="chat-messages" ref="messagesContainer">
          <div
            v-for="(message, index) in messages"
            :key="index"
            class="chat-message"
            :class="{ 'user-message': message.user }"
          >
            <div class="message-content" v-html="parseMarkdown(message.text)"></div>
          </div>
  
          <div v-if="loading" class="chat-message">
            <span>Athena is thinking...</span>
          </div>
        </div>
      </div>
  
      <!-- Input area -->
      <div class="chat-input-container">
        <!-- <p> {{ selectedNodes }}</p> -->
        <div class="function-prompt-button">
          <ToggleButton
            :isChecked="isChecked"
            :loading="loadingBooks"
            labelChecked="Find Books ×"
            labelUnchecked="Find Books"
            @toggle="toggleCheck"
          />
        </div>
  
        <div class="send-message-box">
          <input
            v-model="newMessage"
            @keyup.enter="sendMessage"
            placeholder="Type a message..."
            class="chat-input"
            :disabled="loading"
          />
          <button @click="sendMessage" class="send-button" :disabled="loading">
            <img v-if="!loading" src="./icon/icon-arrow.svg" alt="Send" class="send-icon" />
            <img
              v-else
              src="./icon/icon-stop.svg"  
              alt="Disabled"
              class="stop-icon"
            />
          </button>
        </div>
  
        <!-- <div class="ai-alert">AI may give you wrong answer. Be careful!</div> -->
      </div>
    </div>
  </template>
  


<script lang="ts" setup>
import { ref, nextTick, onMounted, defineProps  } from 'vue';
import axios from 'axios';
import { marked } from "marked";
import eventBus from '@/utils/eventBus'; // Import event bus
import ToggleButton from '@/components/toggle-btn.vue'; 

import { returnBooksNumber } from '@/utils/globalConfig'
import { get } from 'http';

console.log('Current returnBooksNumber:', returnBooksNumber.value)

const props = defineProps({
  selectedNodes: {
    type: Array,
    required: true
  },
  loadingBooks: {
    type: Boolean,
    default: false
  },
  displayMode: {
    type: String,
    required: true
  }
});
const emit = defineEmits(['update:loading']);

// const WelcomeMessage = "Hey there! I'm Athena, your assistant. To create your book graph, try clicking 'Find Books' and simply tell me what book you want to add.";
const WelcomeMessage = "Hey there! I'm Athena, your assistant. To create your book graph, simply tell me what book you want to add.";

const currentMode = ref(props.displayMode || 'chat'); // Default to 'chat' mode if not provided

const messages = ref([{ text: WelcomeMessage, user: false }]);
const newMessage = ref('');
const loading = ref(false);
const messagesContainer = ref(null);
const HISTORY_KEY = "chat_history";
const isChecked = ref(false);
const loadingBooks = ref(false); 



const isSecondChecked = ref(false);
const loadingSecond = ref(false);

// Load chat history
const loadChatHistory = () => {
    try {
        const history = localStorage.getItem(HISTORY_KEY);
        if (history) {
            messages.value = JSON.parse(history);
        }
    } catch (error) {
        console.error("Failed to load chat history:", error);
    }
};

const setSelectedBooks = (books: SelectedBookInfo[]) => {
  selectedBooks.value = books;
};


const toggleCheck = () => {
  if (!loading.value) {
    isChecked.value = !isChecked.value;
  }
};

const toggleSecondCheck = () => {
  if (!loading.value) {
    isSecondChecked.value = !isSecondChecked.value;
    console.log("Second toggle button clicked. Current state:", isSecondChecked.value);
  }
};

// Save chat history
const saveChatHistory = () => {
    try {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.value));
    } catch (error) {
        console.error("Failed to save chat history:", error);
    }
};

// Clear chat history
const clearChatHistory = () => {
    if (confirm("Are you sure you want to clear the chat history?")) {
        localStorage.removeItem(HISTORY_KEY);
        messages.value = [{ text: WelcomeMessage, user: false }];
    }
};
//export chat history
const exportChatHistory = () => {
  try {
    const chatData = messages.value.map(msg => {
      const role = msg.user ? 'User' : 'AI';
      return `${role}: ${msg.text}`;
    }).join('\n\n'); 

    const blob = new Blob([chatData], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `chat-history-${new Date().toISOString().slice(0, 19)}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    console.log("✅ Chat history exported.");
  } catch (error) {
    console.error("❌ Failed to export chat history:", error);
  }
};


// Markdown
const parseMarkdown = (text) => {
    return marked(text);
};

// TODO: we need add mode in this
const queryBooksGraph = async (queryText) => {
  if (!queryText.trim()) return;

  try {
    console.log(`Fetching books related to: "${queryText}"...`);

    //TODO add mode
    

    let modeTemp = 'graph'; // Default mode, can be changed based on currentMode
    if(props.displayMode ==='chat')
    {
        modeTemp = 'chat';
    }
    else{
        modeTemp = 'graph'
    }

    console.log("Current mode:", currentMode.value, "Mode for query:", modeTemp);

    const response = await axios.post(
      "/api/query_books_graph",
      { query: queryText, n: returnBooksNumber.value, mode: modeTemp },
      {
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162"
        }
      }
    );

    console.log("Books API Response:", response.data);


    if (response.data?.explanation) {
      messages.value.push({ text: response.data.explanation, user: false });
    }

    const graph = response.data?.graph;
    if (graph) {
      const { lines, nodes, rootId } = graph;

      if (lines && nodes && rootId) {
        await axios.post("http://localhost:2600/books", { lines, nodes, rootId }, {
          headers: { "Content-Type": "application/json" }
        });
        console.log("✅ Books data stored successfully.");
        eventBus.emit("refreshGraph");

        if (props.displayMode === "chat") {
            const books = (graph.nodes || [])
                .map((node) => {
                const d = node?.data || {};
                const title = d.title?.trim?.() || "";
                const author = d.author?.trim?.() || "";
                const url = d.book_download?.trim?.() || "";
                const gid = d.gutindex_id ?? d.gutIndex_id ?? d.gut_index_id;

                // skip if no title, gid or url
                if (!title || !gid || !url) return null;

                // clickable title linking to Gutenberg detail page
                // ID is shown right after the title, but not part of the link
                const titleWithId =
                    `<a href="https://www.gutenberg.org/ebooks/${gid}" target="_blank" rel="noopener noreferrer">${title}</a>` +
                    ` (ID: ${gid})`;

                // author part
                const authorPart = author ? ` by ${author}` : "";

                // separate Download link
                const downloadLink = ` <a href="${url}" target="_blank" rel="noopener noreferrer">Download</a>`;

                return `- ${titleWithId}${authorPart}${downloadLink}`;
                })
                .filter(Boolean);


            if (books.length > 0) {
                const markdownList = `### 📚 Book Recommendations\n${books.join("\n")}`;
                messages.value.push({ text: markdownList, user: false });
            }
        }

      } else {
        console.error("❌ Invalid graph structure:", graph);
      }
    }

  } catch (error) {
    console.error("Error fetching or storing books:", error);
    messages.value.push({ text: "Sorry, something went wrong while fetching books.", user: false });
  } finally {
    saveChatHistory();
    loading.value = false;
    emit('update:loading', false);
    await nextTick();
    scrollToBottom();
  }
};


const getGutindexIds = async (nodeIds: string[]): Promise<string[]> => {
  const gutindexIds: string[] = [];

  for (const id of nodeIds) {
    try {
      const res = await axios.post("http://localhost:2600/books/node-attribute", {
        id,
        attribute: "gutindex_id"
      }, {
        headers: { "Content-Type": "application/json" }
      });

      gutindexIds.push(res.data);  // Assuming the response is the gutindex_id
    } catch (error) {
      console.error(`❌ Failed to fetch gutindex_id for node ${id}:`, error?.response?.data || error.message);
    }
  }

  return gutindexIds;
};


//TODO add mode This is the main function to send messages
// const sendMessage = async () => {
//   if (!newMessage.value.trim() || loading.value) return;

//   messages.value.push({ text: newMessage.value, user: true });

//   const currentQuery = newMessage.value;
//   newMessage.value = '';
//   loading.value = true;
//   emit('update:loading', true);


//   await nextTick();
//   scrollToBottom();

//   if (isChecked.value) {
//       await queryBooksGraph(currentQuery);
//       isChecked.value = false;  // Reset the toggle state after book adding
//       return;
//   }

//   try {
//     const apiPayload = messages.value.map(msg => ({
//       role: msg.user ? "user" : "assistant",
//       text: msg.text
//     }));

    
//     const gutindex_ids = await getGutindexIds(props.selectedNodes);

//     console.log("Sending API Request with Prompt:", JSON.stringify(apiPayload, null, 2));
//     console.log("🔗 This is the context chat using gutindex_ids:", gutindex_ids);  

//     const response = await axios.post("/api/context_chat", {
//       gutindex_ids,
//       messages: apiPayload 
//     }, {
//       headers: {
//         "Content-Type": "application/json",
//         "Authorization": "Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162"
//       }
//     });

//     console.log("API Response:", response.data);

//     if (response.data) {
//       messages.value.push({ text: response.data, user: false });
//     } else {
//       messages.value.push({ text: "AI response is empty or invalid.", user: false });
//     }



//   } catch (error) {
//     console.error("Error communicating with AI:", error);
//     messages.value.push({ text: "Sorry, something went wrong.", user: false });
//   } finally {
//     saveChatHistory();
//     loading.value = false;
//     emit('update:loading', false);

//     await nextTick();
//     scrollToBottom();
//   }
// };

const sendMessage = async () => {
  if (!newMessage.value.trim() || loading.value) return;

  messages.value.push({ text: newMessage.value, user: true });

  const currentQuery = newMessage.value;
  newMessage.value = '';
  loading.value = true;
  emit('update:loading', true);


  await nextTick();
  scrollToBottom();


    if (isChecked.value) {
      await queryBooksGraph(currentQuery);
      isChecked.value = false;  // Reset the toggle state after book adding
      return;
    }
    else{

        // check if the current mode is 'getbooks'
        const getRoute = await axios.post("/api/classify_route", {
            message: currentQuery
            }, {
            headers: {
                "Content-Type": "application/json",
                "Authorization": "Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162"
            }
        });
    
        console.log("getRoute:", getRoute.data);
    
        if (getRoute.data.route === "query_books_graph") {
            await queryBooksGraph(currentQuery);
            return;
        }
    }


  try {
    const apiPayload = messages.value.map(msg => ({
      role: msg.user ? "user" : "assistant",
      text: msg.text
    }));

    
    const gutindex_ids = await getGutindexIds(props.selectedNodes);

    console.log("Sending API Request with Prompt:", JSON.stringify(apiPayload, null, 2));
    console.log("🔗 This is the context chat using gutindex_ids:", gutindex_ids);  

    const response = await axios.post("/api/context_chat", {
      gutindex_ids,
      messages: apiPayload 
    }, {
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer 1b995a9c-1cd7-4123-adfe-f5a4d0ef7162"
      }
    });

    console.log("API Response:", response.data);

    if (response.data) {
      messages.value.push({ text: response.data, user: false });
    } else {
      messages.value.push({ text: "AI response is empty or invalid.", user: false });
    }



  } catch (error) {
    console.error("Error communicating with AI:", error);
    messages.value.push({ text: "Sorry, something went wrong.", user: false });
  } finally {
    saveChatHistory();
    loading.value = false;
    emit('update:loading', false);

    await nextTick();
    scrollToBottom();
  }
};

// Scroll to the bottom of the chat messages
const scrollToBottom = () => {
    nextTick(() => {
        if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        }
    });
};

onMounted(() => {
    loadChatHistory();
});
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  width: 100%;
  box-sizing: border-box;
  padding: 10px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  box-sizing: border-box;
}

.chat-title {
  font-size: 20px;
  font-weight: 600;
  color: #222;
  box-sizing: border-box;
}

.chat-actions {
  display: flex;
  gap: 10px;
  box-sizing: border-box;
}

.clear-button {
  background-color: #dd5353;
  color: white;
  border-radius: 24px;
  padding: 6px 16px;
  font-size: 14px;
  border: none;
  box-shadow: 0 4px 10px rgba(221, 83, 83, 0.2);
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
  box-sizing: border-box;
}
.clear-button:hover {
  background-color: #c53030;
}

.export-button {
  background-color: #17367a;
  color: white;
  border-radius: 24px;
  padding: 6px 16px;
  font-size: 14px;
  border: none;
  box-shadow: 0 4px 10px rgba(83, 83, 221, 0.2);
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
  box-sizing: border-box;

}

.export-button:hover {
  background-color: #0f265a;
}


.chat-messages-wrapper {
  position: relative;
  flex: 1;
  overflow: hidden;
  margin: 5px 0;
  box-sizing: border-box;
  
}

.chat-messages {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  box-sizing: border-box;
  scroll-behavior: smooth;
}

.fade-overlay {
  position: absolute;
  left: 0;
  width: 100%;
  height: 40px;
  z-index: 1;
  pointer-events: none;
  box-sizing: border-box;
}
.fade-overlay.top {
  top: 0;
  background: linear-gradient(to bottom, white, transparent);
}
.fade-overlay.bottom {
  bottom: 0;
  background: linear-gradient(to top, white, transparent);
}


.chat-message {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 16px;
  background-color: white;
  color: #333;
  align-self: flex-start;
  font-size: 15px;
  line-height: 1.5;
}

.user-message {
  background-color: var(--primary-color);
  color: white;
  align-self: flex-end;
  border-top-right-radius: 4px;
}


.message-content h1,
.message-content h2,
.message-content h3 {
  margin: 8px 0;
  font-weight: 600;
}
.message-content ul {
  margin-left: 20px;
}
.message-content code {
  background: white;
  padding: 2px 5px;
  border-radius: 3px;
}
.message-content pre {
  background: white;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}

/* 输入区域 */
.chat-input-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-sizing: border-box;
  
}

.function-prompt-button {
    z-index: 1000;
  display: flex;
  gap: 10px;
}

.send-message-box {
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

.chat-input {
  flex: 1;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  padding: 10px;
  outline: none;
  background:white;
  box-sizing: border-box;
  
}

.send-button {
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
.send-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.ai-alert {
  font-size: 12px;
  text-align: center;
  color: rgba(0, 0, 0, 0.6);
  font-style: italic;
}



/* Chat messages container styles */
.chat-messages {
    flex-grow: 1;
    width: 100%;
    overflow-y: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px; 
    box-sizing: border-box;

}

/* Default message style (AI/System messages) */
.chat-message {
    max-width: 80%;
    padding: 12px 16px;
    border-radius: 18px;
    font-size: var(--font-size);
    line-height: 1.2;
    word-wrap: break-word;
    transition: all 0.3s ease-in-out;
    align-self: flex-start; 
    color: #333;
    position: relative; 
}

/* User messages (aligned to the right) */
.user-message {
    align-self: flex-end;
    background-color: var(--primary-color); 
    color: white;
    border-top-right-radius: 5px;
}





/* Markdown content */
.message-content {
    white-space: normal;
    margin: auto;
    padding: auto;
}


.message-content h1 {
    font-size: 1.4em;
    margin: 5px 0;
}


.message-content code {
    background-color: #f4f4f4;
    padding: 2px 5px;
    border-radius: 3px;
}


.message-content pre {
    background-color: #eee;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
}


</style>