<template>
  <div class="h-screen overflow-y-auto bg-[#111111] text-neutral-200 font-sans selection:bg-neutral-600 selection:text-white">
    
    <div v-show="!currentReadingBook" class="max-w-6xl mx-auto px-6 md:px-12 flex flex-col min-h-screen">
      
      <header class="flex flex-col md:flex-row items-center justify-between py-12 gap-6 relative">
        
        <div class="flex-1 flex justify-start">
        </div>
        
        <h1 
          @click="resetToHome"
          class="text-2xl md:text-4xl font-light tracking-[0.5em] text-center flex-1 text-neutral-100 cursor-pointer hover:text-white transition-colors duration-300"
        >
          S U L I B R A R Y
        </h1>
        
        <div class="flex-1 flex justify-end items-center gap-4 w-full md:w-auto">
          <button
            @click="toggleTab"
            class="text-[10px] md:text-xs font-bold tracking-[0.2em] text-neutral-500 hover:text-neutral-100 transition-colors duration-300 whitespace-nowrap uppercase"
          >
            {{ activeTab === 'bookstore' ? 'BOOKSHELF' : 'BOOKSTORE' }}
          </button>

          <input
            v-show="activeTab !== 'bookstore'"
            v-model="searchQuery"
            @keyup.enter="executeCommand"
            type="text"
            placeholder="/login or search..."
            class="w-full md:w-48 lg:w-64 bg-transparent border-b border-neutral-800 pb-1 text-xs md:text-sm text-neutral-300 focus:outline-none focus:border-neutral-500 transition-colors placeholder:text-neutral-700 tracking-wide"
          />
        </div>
      </header>

      <main class="flex-1 pb-16 pt-4">
        <BookshelfView
          v-show="activeTab === 'bookshelf'"
          :books="bookshelf"
          @openReader="openReader"
          @refreshBookshelf="fetchBookshelf"
        />

        <BookstoreView
          v-show="activeTab === 'bookstore'"
        />

        <SearchView
          v-show="activeTab === 'search'"
          :results="searchResults"
          @openReader="openReader"
          @refreshSearch="executeCommand"
          @refreshBookshelf="fetchBookshelf"
        />
      </main>
    </div>

    <EpubReader
      v-if="currentReadingBook"
      :book="currentReadingBook"
      @close="closeReader"
    />

  </div>
</template>
<script setup>
import { ref, onMounted,watch } from 'vue';
import { v4 as uuidv4 } from 'uuid';

import EpubReader from './components/EpubReader.vue';
import BookshelfView from './views/BookshelfView.vue';
import BookstoreView from './views/BookstoreView.vue';
import SearchView from './views/SearchView.vue';

const activeTab = ref('bookshelf'); 
const currentReadingBook = ref(null);
const bookshelf = ref([]);
const searchResults = ref([]);
const isGuest = ref(true);
const searchQuery = ref('');

// ✨ 引擎点火：当网页一打开，立刻执行身份核验和拉取书架！
onMounted(() => {
  checkIdentity();
  fetchBookshelf();
});

const toggleTab = () => {
  if (activeTab.value === 'bookstore') {
    activeTab.value = 'bookshelf';
    fetchBookshelf(); // 回到书架时，顺便刷新一下最新数据
  } else {
    // 无论当前是 bookshelf 还是 search 状态，只要点这个按钮，就去 bookstore
    activeTab.value = 'bookstore';
  }
};

const checkIdentity = () => {
  const token = localStorage.getItem('geek_token');
  if (token) {
    isGuest.value = false;
    return;
  }
  let guestUuid = localStorage.getItem('guest_uuid');
  if (!guestUuid) {
    guestUuid = uuidv4();
    localStorage.setItem('guest_uuid', guestUuid);
  }
  isGuest.value = true;
};

// 修复回车触发逻辑
const executeCommand = async () => { // 加上 async
  const query = searchQuery.value.trim();
  if (!query) return;

  const loginMatch = query.match(/^\/login\s+(\w+)\s+(.+)$/);

  if (loginMatch) {
    const username = loginMatch[1];
    const password = loginMatch[2];
    
    try {
      // 🔮 向后端发起真正的契约绑定请求 [cite: 4]
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        localStorage.setItem('geek_token', data.token); // 存储后端返回的真实 Token
        isGuest.value = false;
        await fetchBookshelf(); // 立即切换到正式账号的书架
        searchQuery.value = '';
        console.log(`✨ 欢迎回来，${username}！`);
      }
    } catch (e) {
      console.error("身份校验失败:", e);
    }
    return;
  }

  if (query === '/logout') {
    localStorage.removeItem('geek_token');
    isGuest.value = true;
    // 👻 登出后，fetchBookshelf 会因为没有 token 而自动回退到 guest-uuid 对应的匿名书架
    await fetchBookshelf(); 
    searchQuery.value = '';
    console.log('🚪 已切回游客模式，匿名书架已找回。');
    return;
  }
  // ... 其他搜索逻辑
  try {
    const response = await fetch(`/api/books/search?q=${encodeURIComponent(query)}`, {
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      }
    });
    const data = await response.json();
    if (data.status === 'success') {
      searchResults.value = data.books; 
      activeTab.value = 'search'; // ✨ 自动切换到搜索视图！
    }
  } catch (error) {
    console.error('💥 搜索魔法阵失效:', error);
  }
};
// ✨ 核心修复：增加返回主页的逻辑
const resetToHome = () => {
  activeTab.value = 'bookshelf';  // 强制切回书架状态
  searchQuery.value = '';         // 清空搜索框里的文字
  fetchBookshelf();               // 重新向后端请求最新书架数据
};
// ✨ 当搜索框被清空时，自动切回书架
watch(searchQuery, (newVal) => {
  if (newVal === '') {
    activeTab.value = 'bookshelf';
    searchResults.value = []; // 清空之前的搜索缓存
  }
});

const API_BASE = 'http://127.0.0.1:8000'; // 替换成你树莓派的实际 IP 和端口

const fetchBookshelf = async () => {
  try {
    const response = await fetch('/api/books', {
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      }
    });
    const data = await response.json();
    if (data.status === 'success') {
      bookshelf.value = data.books;
    }
  } catch (error) {
    console.error('🕸️ 呼叫后端数据库失败:', error);
    bookshelf.value = [];
  }
};
const openReader = (book) => {
  currentReadingBook.value = book;
};

const closeReader = () => {
  currentReadingBook.value = null;
};
</script>

<style>
/* ========== 自定义滚动条样式 ========== */

/* 1. 针对 Firefox 浏览器的简单支持 */
* {
  scrollbar-width: thin;
  scrollbar-color: #333333 transparent;
}

/* 2. 针对 Webkit 内核 (Chrome, Edge, Safari) */
/* 整个滚动条的宽度 */
::-webkit-scrollbar {
  width: 8px; /* 比默认的细一点，显得更精致 */
}

/* 滚动条的轨道（滑块背后的那条沟） */
::-webkit-scrollbar-track {
  background: transparent; /* 设为透明，完美融入你的深色背景 */
}

/* 滚动条的滑块本体 */
::-webkit-scrollbar-thumb {
  background-color: #333333; /* 平时是低调的深灰色 */
  border-radius: 9999px; /* 极端的圆角，让它两头是圆的 */
  border: 2px solid transparent; /* 加个透明边框... */
  background-clip: padding-box; /* ...配合这句，可以让滑块不紧贴屏幕边缘 */
}

/* 鼠标悬停在滑块上时的效果 */
::-webkit-scrollbar-thumb:hover {
  background-color: #404040; /* 变亮一点点，提供交互反馈 */
}
</style>
