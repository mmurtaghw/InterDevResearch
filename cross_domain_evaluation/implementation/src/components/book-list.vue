<template>
    <div class="book-list">
        <div v-if="books.length === 0" class="empty-message-overlay">
            <h1 class="headline">No Books Found Yet</h1>
            <p class="subtext">
                Try using <strong>contextual search</strong> in the bar above.<br />
                Describe your interests and discover your next great read.
            </p>
        </div>
      <div 
        v-for="(book, index) in books" 
        :key="index" 
        class="book-item"
      >
      
        <img :src="book.pic" alt="cover" class="book-pic" />
  
        <div class="book-details">
          <h3 class="book-title">{{ book.title }}</h3>
          <p class="book-author">{{ book.author }}</p>
          <p class="book-id">ID: {{ book.id }}</p>
  
          <div class="book-links">
            <a :href="book.downloadLink" target="_blank">Download</a>
            <a :href="`https://www.gutenberg.org/ebooks/${book.id}`" target="_blank">View Details</a>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  defineProps<{
    books: {
      id: string;
      title: string;
      author: string;
      pic: string;
    }[]
  }>();
  </script>
  
  <style scoped>
.book-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 5px;
}

.book-item {
  display: flex;
  gap: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
  background-color: #fafafa;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
  transition: box-shadow 0.2s;
}

.book-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.book-pic {
  width: 90px;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
  flex-shrink: 0;
}

.book-details {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  flex: 1;
}

.book-title {
  margin: 0;
  font-size: var(--font-size);
  font-weight: 600;
}

.book-author,
.book-id {
  margin: 4px 0;
  font-size: var(--font-size-medium);
  color: #555;
}

.book-links {
  margin-top: 8px;
}

.book-links a {
  margin-right: 16px;
  color: #1a73e8;
  text-decoration: none;
  font-size: var(--font-size-medium);
  font-weight: 500;
}

.book-links a:hover {
  text-decoration: underline;
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
  user-select: none;
  pointer-events: none;
}

.empty-message-overlay .headline {
  font-size: 28px;
  color: #666;
  margin-bottom: 10px;
  font-weight: 600;
  pointer-events: none;
}

.empty-message-overlay .subtext {
  font-size: 22px;
  color: #999;
  line-height: 1.6;
  pointer-events: none;
}

  </style>
  