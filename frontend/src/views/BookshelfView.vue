<template>
  <div>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 md:gap-8">

      <div
        v-for="book in books"
        :key="book.id"
        class="relative group cursor-pointer aspect-[3/4] border border-[#222] bg-[#1a1a1a] hover:border-neutral-500 transition-all duration-300 flex flex-col justify-between p-5 md:p-6 overflow-hidden"
        @mousedown="startLongPress(book)"
        @mouseup="cancelLongPress"
        @mouseleave="cancelLongPress"
        @touchstart="startLongPress(book)"
        @touchend="cancelLongPress"
        @click="handleClick(book)"
      >
        <img 
          v-if="book.cover" 
          :src="book.cover" 
          class="absolute inset-0 w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-300 z-0"
          alt="cover"
        />

        <div v-else class="flex-1 flex flex-col justify-between relative z-10">
          <div>
            <h2 class="font-serif text-base md:text-lg text-neutral-200 leading-snug line-clamp-4">{{ book.title }}</h2>
            <p class="text-[10px] md:text-xs text-neutral-500 mt-3 tracking-wider uppercase">{{ book.author }}</p>
          </div>
        </div>

        <div 
          v-if="book.progress && book.progress > 0" 
          class="absolute bottom-0 left-0 right-0 w-full bg-[#111] h-[3px] z-20"
        >
          <div 
            class="bg-neutral-600 h-full transition-all duration-500 ease-out" 
            :style="{ width: `${(book.progress * 100).toFixed(1)}%` }"
          ></div>
        </div>
      </div>

      <div
        @click="triggerUpload"
        class="aspect-[3/4] border border-dashed border-[#333] hover:border-neutral-400 text-neutral-600 hover:text-neutral-300 transition-all duration-300 flex flex-col items-center justify-center cursor-pointer"
      >
        <span class="text-3xl font-light mb-2">+</span>
        <span class="text-[10px] font-mono tracking-[0.2em] uppercase">Import</span>
        <input type="file" ref="fileInput" class="hidden" accept=".epub,.pdf,.txt,.mobi,.azw3" @change="handleFileUpload">
      </div>

    </div>

    <div v-if="showActionMenu" class="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-50">
      <div class="bg-[#111] border border-[#333] p-8 flex flex-col gap-4 shadow-2xl min-w-[280px]">
        <h3 class="text-neutral-400 text-xs tracking-widest uppercase mb-4 text-center border-b border-[#333] pb-4">Options</h3>
        <button @click="showBookDetails" class="px-6 py-3 bg-[#222] hover:bg-[#333] text-sm tracking-widest transition-colors">DETAILS</button>
        <button 
          v-if="selectedBook && selectedBook.is_uploader" 
          @click.stop="handleToggleVisibility" 
          class="px-6 py-3 text-sm tracking-widest transition-colors text-center"
          :class="selectedBook.is_public 
            ? 'bg-[#222] hover:bg-[#333] text-neutral-200 font-normal'
            : 'bg-neutral-200 hover:bg-white text-black font-bold'"
        >
          {{ selectedBook.is_public ? 'PRIVATE' : 'PUBLIC' }}
        </button>
        <button @click="deleteBook" class="px-6 py-3 bg-neutral-200 hover:bg-white text-black text-sm tracking-widest transition-colors font-bold">DELETE</button>
        <button @click="showActionMenu = false" class="px-6 py-3 mt-2 text-neutral-500 hover:text-white text-xs tracking-widest transition-colors">CANCEL</button>
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

// 加上了 refreshBookshelf，用于告诉父组件“书传完了，重新拉取一下列表”
const emit = defineEmits(['openReader', 'refreshBookshelf']);

const fileInput = ref(null);
const showActionMenu = ref(false);
const selectedBook = ref(null);
let pressTimer = null;

// ⚠️ 注意：这里改成你树莓派真实的 IP 和 FastAPI 端口 (如果是本地调试就用 127.0.0.1:8000)
const API_BASE = 'http://127.0.0.1:8000'; 

// ==========================================
// 1. 长按与点击判定逻辑
// ==========================================
const startLongPress = (book) => {
  pressTimer = setTimeout(() => {
    selectedBook.value = book;
    showActionMenu.value = true;
    if (navigator.vibrate) navigator.vibrate(50);
  }, 600); 
};

const cancelLongPress = () => {
  if (pressTimer) {
    clearTimeout(pressTimer);
    pressTimer = null;
  }
};

const handleClick = (book) => {
  if (showActionMenu.value) return; 
  emit('openReader', book);         
};

// ==========================================
// 2. 真·文件导入逻辑 (直连 FastAPI)
// ==========================================
const triggerUpload = () => {
  fileInput.value.click();
};

const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  console.log(`🚀 准备将 ${file.name} 送入后端大锅炉...`);

  const formData = new FormData();
  formData.append('file', file);

  try {
    // 🌟 核心修复：在这里加上 headers，亮出你的身份令牌！
    const response = await fetch('/api/books/upload', {
      method: 'POST',
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      },
      body: formData,
    });

    const result = await response.json();
    console.log('炼金炉反馈:', result.message);

    if (result.status === 'success' || result.status === 'processing') {
      emit('refreshBookshelf');
    }
  } catch (error) {
    console.error('💥 魔法通道崩塌，上传失败:', error);
  }

  event.target.value = null;
};
// ==========================================
// 3. 菜单操作逻辑
// ==========================================
const showBookDetails = () => {
  alert(`TITLE: ${selectedBook.value.title}\nAUTHOR: ${selectedBook.value.author}`);
  showActionMenu.value = false;
};

const deleteBook = async () => {
  if (!selectedBook.value) return;

  const bookId = selectedBook.value.id;
  const bookTitle = selectedBook.value.title;
  console.log(`🗑️ 准备彻底抹除: ${bookTitle}`);

  try {
    // 🌟 核心修复：向后端发送毁灭打击，并亮出身份令牌
    const response = await fetch(`/api/books/${bookId}`, {
      method: 'DELETE',
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      }
    });

    const result = await response.json();

    if (result.status === 'success') {
      console.log(`✨ 抹除成功: ${result.message}`);
      // 成功后，呼叫父组件重新拉取书架数据，书籍就会瞬间消失！
      emit('refreshBookshelf');
    } else {
      console.error('💥 抹除失败:', result.message);
      alert("删除失败：" + result.message);
    }
  } catch (error) {
    console.error('💥 魔法通道崩塌，删除请求失败:', error);
  } finally {
    // 无论成功还是失败，最后都要关闭操作菜单，并清空选中状态
    showActionMenu.value = false;
    selectedBook.value = null; 
  }
};

const handleToggleVisibility = async () => {
  if (!selectedBook.value) return;

  console.log(`[可见性切换] 正在处理书籍: ${selectedBook.value.title}`);

  try {
    const response = await fetch(`/api/books/${selectedBook.value.id}/toggle_visibility`, {
      method: 'PUT',
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      }
    });

    const data = await response.json();

    if (data.status === 'success') {
      // 🌟 核心修复：强制转换为 Boolean，触发 Vue 响应式 UI 变更！
      selectedBook.value.is_public = !!data.is_public;
      console.log(`✨ 状态已切换为: ${selectedBook.value.is_public ? 'PUBLIC' : 'PRIVATE'}`);

      // 通知外层 App.vue 重新拉取一次书架，保证绝对的后台同步
      emit('refreshBookshelf');
    } else {
      console.error('💥 权限不足或魔法中断:', data.detail);
      alert(data.detail);
    }
  } catch (error) {
    console.error('💥 网络请求失败:', error);
  }
};
</script>
