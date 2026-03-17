<template>
  <div class="p-8 pb-24">
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
      
      <div
        v-for="book in books"
        :key="book.id"
        class="relative group cursor-pointer aspect-[3/4] bg-neutral-800 rounded-sm hover:shadow-lg transition-all duration-300 border border-neutral-700 hover:border-neutral-500 overflow-hidden"
        @mousedown="startLongPress(book)"
        @mouseup="cancelLongPress"
        @mouseleave="cancelLongPress"
        @touchstart="startLongPress(book)"
        @touchend="cancelLongPress"
        @click="handleClick(book)"
      >
        <img v-if="book.cover" :src="book.cover" class="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
        
        <div v-else class="w-full h-full flex flex-col items-center justify-center p-4 text-center">
          <span class="font-serif text-lg text-neutral-300 line-clamp-3">{{ book.title }}</span>
          <span class="text-xs text-neutral-500 mt-2">{{ book.author }}</span>
        </div>

        <div class="absolute bottom-0 left-0 h-1 bg-neutral-500" :style="{ width: book.progress + '%' }"></div>
      </div>

      <div
        @click="triggerUpload"
        class="aspect-[3/4] border-2 border-dashed border-neutral-700 hover:border-neutral-400 rounded-sm flex flex-col items-center justify-center cursor-pointer text-neutral-600 hover:text-neutral-300 transition-colors"
      >
        <span class="text-4xl font-light mb-2">+</span>
        <span class="text-xs font-mono tracking-widest">IMPORT</span>
        <input type="file" ref="fileInput" class="hidden" accept=".epub,.pdf,.txt,.mobi,.azw3" @change="handleFileUpload" />
      </div>

    </div>

    <div v-if="showActionMenu" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50" @click="showActionMenu = false">
      <div class="bg-neutral-900 border border-neutral-700 p-6 rounded-sm shadow-2xl flex gap-4" @click.stop>
        <button @click="showBookDetails" class="px-6 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-sm border border-neutral-700 transition-colors">详情 (DETAILS)</button>
        <button @click="deleteBook" class="px-6 py-2 bg-neutral-200 hover:bg-white text-neutral-900 text-sm font-bold transition-colors">删除 (DELETE)</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  books: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['openReader']);

const fileInput = ref(null);
const showActionMenu = ref(false);
const selectedBook = ref(null);
let pressTimer = null;

// ==========================================
// 1. 长按与点击判定逻辑
// ==========================================
const startLongPress = (book) => {
  pressTimer = setTimeout(() => {
    selectedBook.value = book;
    showActionMenu.value = true;
    // 如果设备支持，触发轻微震动反馈
    if (navigator.vibrate) navigator.vibrate(50);
  }, 600); // 600毫秒视为长按
};

const cancelLongPress = () => {
  if (pressTimer) {
    clearTimeout(pressTimer);
    pressTimer = null;
  }
};

const handleClick = (book) => {
  if (showActionMenu.value) return; // 如果长按菜单已经弹出，则拦截点击事件
  emit('openReader', book);         // 否则，通知 App.vue 打开阅读器
};

// ==========================================
// 2. 导入与菜单操作
// ==========================================
const triggerUpload = () => {
  fileInput.value.click();
};

const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (file) {
    console.log(`🚀 准备将 ${file.name} 丢进炼金炉...`);
    // TODO: 后续在这里对接后端 API 进行文件上传
  }
};

const showBookDetails = () => {
  alert(`书名: ${selectedBook.value.title}\n作者: ${selectedBook.value.author}`);
  showActionMenu.value = false;
};

const deleteBook = () => {
  console.log(`🗑️ 已将 ${selectedBook.value.title} 彻底从宇宙中抹除！`);
  showActionMenu.value = false;
  // TODO: 后续在这里对接后端 API 进行删除
};
</script>
