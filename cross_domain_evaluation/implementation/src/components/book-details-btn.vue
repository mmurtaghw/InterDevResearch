<template>
    <div class="summary-button-wrapper">
      <button
        class="summarize-button"
        @click="handleDownload"
        :disabled="props.selectedNodes.length === 0"
      >
        <span>More Details</span>
      </button>
  
      <!-- ❌ Error Toast -->
      <transition name="fade">
        <div v-if="showErrorToast" class="toast-notification error">
          <span>❌ Some details can not be found. Please try again.</span>
          <button class="close-btn" @click="showErrorToast = false">×</button>
        </div>
      </transition>
    </div>
  </template>
  
  <script setup>
  import { ref, defineProps } from 'vue';
  import axios from 'axios';
  
  const props = defineProps({
    selectedNodes: {
      type: Array,
      required: true
    }
  });
  
  const showErrorToast = ref(false);
  
  // Local backend base URL (unchanged)
  const LOCAL_API_BASE = 'http://localhost:2600';
  
  /**
   * Safely extract a node id from either a primitive id or an object.
   */
  const getNodeId = (node) => {
    if (node && typeof node === 'object') return node.id ?? node.value ?? null;
    return node;
  };
  
  /**
   * Generic attribute fetcher using the existing backend endpoint.
   * Expects POST /books/node-attribute with payload { id, attribute }.
   */
  const fetchNodeAttribute = async (nodeId, attribute) => {
    try {
      const res = await axios.post(`${LOCAL_API_BASE}/books/node-attribute`, {
        id: nodeId,
        attribute
      });
      return res.data;
    } catch (err) {
      console.error(`Error fetching attribute "${attribute}" for node ${nodeId}:`, err);
      return null;
    }
  };
  
  /**
   * Fetch gutindex_id for a given selected node id.
   * Handles possible response shapes: string/number or object.
   */
  const fetchGutIndexId = async (nodeId) => {
    const data = await fetchNodeAttribute(nodeId, 'gutindex_id');
    if (data == null) return null;
    if (typeof data === 'string' || typeof data === 'number') return String(data);
    if (typeof data === 'object') {
      // Try common keys
      return data.gutindex_id ?? data.value ?? data.id ?? null;
    }
    return null;
  };
  
  /**
   * Build Gutenberg details URL from gutindex_id.
   */
  const buildDetailsUrl = (gid) =>
    `https://www.gutenberg.org/ebooks/${encodeURIComponent(gid)}`;
  
  /**
   * Open URL in a new browser tab.
   */
  const openInNewTab = (url) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };
  
  /**
   * On click: for each selected node, query gutindex_id via backend,
   * then open the corresponding Gutenberg details page in new tabs.
   * Show the existing error toast if some lookups fail.
   */
  const handleDownload = async () => {
    showErrorToast.value = false;
  
    try {
      const nodeIds = props.selectedNodes.map(getNodeId);
  
      const gids = await Promise.all(
        nodeIds.map((nid) => (nid != null ? fetchGutIndexId(nid) : Promise.resolve(null)))
      );
  
      const urls = gids.map((gid) => (gid ? buildDetailsUrl(gid) : null));
      const validUrls = urls.filter((u) => typeof u === 'string');
  
      validUrls.forEach((url) => openInNewTab(url));
  
      if (validUrls.length < nodeIds.length) {
        showToastWithTimeout();
      }
    } catch (err) {
      console.error('Details error:', err);
      showToastWithTimeout();
    }
  };
  
  /**
   * Show the error toast for 3 seconds.
   */
  const showToastWithTimeout = () => {
    showErrorToast.value = true;
    setTimeout(() => {
      showErrorToast.value = false;
    }, 3000);
  };
  </script>
  
  
  <style scoped>
  .summary-button-wrapper {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    width: 100%;
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
    background-color: var(--primary-color, #45a2e8);
    border: none;
    border-radius: var(--border-radius);
    cursor: pointer;
    box-shadow: 5px 5px 15px rgba(12, 73, 157, 0.2);
    transition: background-color 0.3s ease;
    box-sizing: border-box;
    text-align: left;
  
    width: fit-content;
    max-width: 100%;
  }
  
  .summarize-button:hover {
    background-color: #3689cb;
  }
  
  .summarize-button:disabled {
    background-color: #bcd9ee;
    color: #e2e8f0;
    cursor: not-allowed;
    box-shadow: none;
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
  