<template>
  <div class="min-h-screen bg-neutral-900 text-neutral-100 font-sans selection:bg-neutral-600 flex flex-col relative pb-16">
    
    <HeaderBar 
      v-show="!currentReadingBook" 
      @command="handleGeekCommand" 
      :isGuest="isGuest" 
    />

    <main class="flex-1 overflow-y-auto scrollbar-hide">
      
      <BookshelfView 
        v-show="!currentReadingBook && activeTab === 'bookshelf'" 
        :books="bookshelf" 
        @openReader="openReader" 
      />
      
      <BookstoreView 
        v-show="!currentReadingBook && activeTab === 'bookstore'" 
      />
      
      <EpubReader 
        v-if="currentReadingBook" 
        :book="currentReadingBook" 
        @close="closeReader" 
      />

    </main>

    <nav v-show="!currentReadingBook" class="fixed bottom-0 left-0 right-0 h-16 border-t border-neutral-800 bg-neutral-900/90 backdrop-blur-sm flex justify-between items-center px-8 sm:px-16 z-40">
      <button 
        @click="activeTab = 'bookshelf'" 
        class="text-sm font-bold tracking-[0.3em] transition-colors duration-300"
        :class="activeTab === 'bookshelf' ? 'text-neutral-100' : 'text-neutral-600 hover:text-neutral-400'"
      >
        MY BOOKSHELF
      </button>

      <button 
        @click="activeTab = 'bookstore'" 
        class="text-sm font-bold tracking-[0.3em] transition-colors duration-300"
        :class="activeTab === 'bookstore' ? 'text-neutral-100' : 'text-neutral-600 hover:text-neutral-400'"
      >
        BOOKSTORE
      </button>
    </nav>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { v4 as uuidv4 } from 'uuid'; // 记得运行 npm install uuid

// 导入我们拆分出来的组件
import HeaderBar from './components/HeaderBar.vue';
import EpubReader from './components/EpubReader.vue';
import BookshelfView from './views/BookshelfView.vue';
import BookstoreView from './views/BookstoreView.vue';

// -------------------------------------------------------------
// 🧠 全局状态与路由控制
// -------------------------------------------------------------
const activeTab = ref('bookshelf'); // 控制底部导航切换 ('bookshelf' | 'bookstore')
const currentReadingBook = ref(null); // 如果有值，说明正在看书，全屏显示阅读器

const bookshelf = ref([]);
const isGuest = ref(true);

// -------------------------------------------------------------
// 🕵️‍♂️ 初始化与身份核验
// -------------------------------------------------------------
onMounted(() => {
  checkIdentity();
  fetchBookshelf();
});

const checkIdentity = () => {
  const token = localStorage.getItem('geek_token');
  if (token) {
    isGuest.value = false;
    return;
  }
  
  // 幽灵游客指纹烙印
  let guestUuid = localStorage.getItem('guest_uuid');
  if (!guestUuid) {
    guestUuid = uuidv4();
    localStorage.setItem('guest_uuid', guestUuid);
  }
  isGuest.value = true;
};

// -------------------------------------------------------------
// ⌨️ 极客命令处理 (/login, /logout 等)
// -------------------------------------------------------------
const handleGeekCommand = (query) => {
  const loginMatch = query.match(/^\/login\s+(\w+)\s+(.+)$/);
  
  if (loginMatch) {
    const username = loginMatch[1];
    const password = loginMatch[2];
    console.log(`🪄 收到登录指令！尝试唤醒魔法师：${username}`);
    // 模拟登录成功
    localStorage.setItem('geek_token', 'fake_token_123');
    isGuest.value = false; 
    fetchBookshelf();
    return;
  }

  if (query === '/logout') {
    console.log('🚪 断开连接，清空布局...');
    localStorage.removeItem('geek_token');
    isGuest.value = true;
    bookshelf.value = [];
    fetchBookshelf(); // 重新拉取游客空书架
    return;
  }

  console.log(`🔍 正在满世界寻找书籍：${query}`);
  // TODO: 后续在这里实现调用后端搜索接口的逻辑
};

// -------------------------------------------------------------
// 📚 书架数据拉取
// -------------------------------------------------------------
const fetchBookshelf = () => {
  // TODO: 后续替换为 axios 调用后端 API
  bookshelf.value = [
    { id: '1', title: 'The Pragmatic Programmer', author: 'David Thomas', progress: 35 },
    { id: '2', title: 'Dune', author: 'Frank Herbert', progress: 12 }
  ];
};

// -------------------------------------------------------------
// 📖 阅读器调度逻辑
// -------------------------------------------------------------
const openReader = (book) => {
  console.log(`📖 准备翻开: ${book.title}`);
  currentReadingBook.value = book;
};

const closeReader = () => {
  console.log(`📕 合上书籍，返回书架`);
  currentReadingBook.value = null;
};
</script>

<style>
/* 全局隐藏滚动条，保持极致的极简洁癖感 */
.scrollbar-hide::-webkit-scrollbar {
    display: none;
}
.scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
