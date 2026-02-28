// src/globalConfig.js
import { ref } from 'vue'

// Default: 6 (production)
export const returnBooksNumber = ref(6)

// Choose mode at startup
const mode = prompt('Select mode: test or release').toLowerCase()

if (mode === 'test') {
  returnBooksNumber.value = 3
  console.log('Running in TEST mode, returnBooksNumber = 3')
} else {
  returnBooksNumber.value = 6
  console.log('Running in RELEASE mode, returnBooksNumber = 6')
}
