<template>
    <div class="tooltip-wrapper">
      <button 
          type="button"
          @click="handleClick"
          class="check-button" 
          :class="{ 'checked': isChecked }" 
          :disabled="loading"
      >
          <!-- Dynamically load the icon based on isChecked -->
          <img 
              :src="getIconSrc()" 
              alt="Book Icon" 
              class="icon" 
              :class="{ 'checked-icon': isChecked }"
          />
          <!-- Show "Loading..." text if loading, otherwise display button label -->
          <span v-if="loading">Loading...</span>
          <span v-else>{{ isChecked ? labelChecked : labelUnchecked }}</span>
      </button>
  
      <!-- Tooltip with bold "always" -->
      <div class="tooltip" role="tooltip">
        If Athena <strong>always</strong> fails to find books, please toggle on this button and ask again.
        <span class="tooltip-arrow" aria-hidden="true"></span>
      </div>
    </div>
  </template>
  
  
  <script>
  import iconBook from '../icon/icon-book.svg'
  import iconBookOff from '../icon/icon-book-off.svg'
  
  export default {
    props: {
      isChecked: Boolean, // Controls button state
      loading: Boolean,   // Controls loading state
      labelChecked: {
        type: String,
        default: 'Added'
      },
      labelUnchecked: {
        type: String,
        default: 'Find Books'
      }
    },
    methods: {
      handleClick() {
        if (this.loading) return // Prevent click while loading
        this.$emit('toggle')     // Emit toggle event to parent
      },
      getIconSrc() {
        return this.isChecked ? iconBook : iconBookOff
      }
    }
  }
  </script>
  
  <!-- Global styles placeholder -->
  <style>
  </style>
  
  <!-- Scoped styles for this component -->
  <style scoped>
  /* Wrapper to position the tooltip relative to the button */
  .tooltip-wrapper {
    position: relative;
    display: inline-block;
    isolation: isolate; /* Prevent stacking context issues */
  }
  
  /* Base styles for the button */
  .check-button {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 100px;
    max-width: 100%;
    height: var(--button-height);
    padding: var(--padding-vertical) calc(var(--padding-horizontal) * 1);
    gap: 8px;
    font-size: var(--font-size);
    font-weight: var(--font-medium);
    text-align: center;
    white-space: nowrap;
    
    background-color: var(--secondary-color);
    color: var(--primary-color);
    border: 2px solid var(--primary-color);
    border-radius: var(--border-radius);
    box-shadow: 5px 5px 10px var(--shadow-color);
    box-sizing: border-box;
    
    transition: all 0.3s ease;
  }
  
  /* Checked state */
  .check-button.checked {
    background-color: var(--primary-color);
    color: var(--text-color);
  }
  
  /* Disabled state */
  .check-button:disabled {
    background-color: gray;
    border-color: gray;
    color: #b0b0b0;
    cursor: not-allowed;
    box-shadow: none;
  }
  
  /* Icon styles */
  :deep(.icon) {
    width: 20px;
    max-height: 100%;
    flex-shrink: 0;
    overflow: hidden;
    transition: transform 0.3s ease;
  }
  
  /* Icon scaling when checked */
  .check-button.checked .icon {
    transform: scale(1.1);
  }
  
  /* Tooltip container */
  .tooltip {
  position: absolute;
  z-index: 2000; /* bring tooltip on top of overlays */
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);

  /* Width fix */
  width: 150px;        /* fixed width for consistent layout */
  
  white-space: normal;     /* allow wrapping */
  overflow-wrap: anywhere; /* prevent breaking layout */

  /* Visuals */
  padding: 12px 14px;
  border-radius: 10px;
  background: #111827;     /* solid dark background, no gradient */
  color: #fff;
  font-size: 13px;
  line-height: 1.5;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);

  /* Animation */
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.15s ease, visibility 0.15s ease, transform 0.15s ease;
}

.tooltip-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  width: 10px;
  height: 10px;
  background: #111827;
  transform: translateX(-50%) rotate(45deg);
}

  
  /* Show tooltip on hover or focus */
  .tooltip-wrapper:hover .tooltip,
  .tooltip-wrapper:focus-within .tooltip {
    opacity: 1;
    visibility: visible;
    transform: translateX(-50%) translateY(-2px);
  }
  </style>
  