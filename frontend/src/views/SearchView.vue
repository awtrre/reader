<template>
  <div class="select-none">
    <div class="mb-6 border-b border-[#333] pb-2 flex justify-between items-end">
      <h2 class="text-sm tracking-[0.2em] text-neutral-400">SEARCH RESULTS</h2>
      <span class="text-xs text-neutral-600 font-mono">{{ results.length }} items found</span>
    </div>

    <div v-if="results.length === 0" class="text-center py-20 text-neutral-600 text-sm tracking-widest">
      NO MAGIC SCROLLS FOUND...
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 md:gap-8">
      <div
        v-for="book in results"
        :key="book.id"
        class="relative group cursor-pointer aspect-[3/4] border transition-all duration-300 flex flex-col justify-between p-5 md:p-6 overflow-hidden"
        :class="book.is_owned ? 'border-[#222] bg-[#1a1a1a] hover:border-neutral-500' : 'border-dashed border-[#555] bg-black/40 hover:border-neutral-300'"
        @click="handleClick(book)"
      >
        <img 
          v-if="book.cover && book.is_owned" 
          :src="book.cover" 
          class="absolute inset-0 w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-300 z-0"
          alt="cover"
        />

        <div class="flex-1 flex flex-col justify-between relative z-10">
          <div>
            <h2 class="font-serif text-base md:text-lg text-neutral-200 leading-snug line-clamp-4">{{ book.title }}</h2>
            <p class="text-[10px] md:text-xs text-neutral-500 mt-3 tracking-wider uppercase">{{ book.author }}</p>
          </div>
        </div>

        <div v-if="!book.is_owned" 
             class="absolute inset-0 z-30 bg-black/60 flex flex-col items-center justify-center backdrop-blur-[2px] transition-all duration-300 opacity-0 group-hover:opacity-100">
          <span class="text-4xl font-light text-white pb-2">+</span>
          <span class="text-[10px] tracking-widest text-white uppercase">Add to Shelf</span>
        </div>

        <div v-if="book.is_owned" class="absolute bottom-0 left-0 right-0 w-full bg-[#333]/80 h-[2px] z-20">
          <div class="bg-neutral-300 h-full transition-all duration-500" :style="{ width: book.progress + '%' }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

const props = defineProps({
  results: {
    type: Array,
    default: () => []
  }
});

// 通知 App.vue 打开阅读器，或者重新执行搜索刷新列表
const emit = defineEmits(['openReader', 'refreshSearch', 'refreshBookshelf']);

const handleClick = async (book) => {
  // 1. 如果这本书你还没拥有，点击就是加入书架！
  if (!book.is_owned) {
    try {
      await fetch(`/api/books/${book.id}/add_to_shelf`, {
        method: 'POST',
        headers: {
          'user-token': localStorage.getItem('geek_token') || '',
          'guest-uuid': localStorage.getItem('guest_uuid') || ''
        }
      });
      console.log(`✨ 成功将 ${book.title} 纳入麾下！`);
      // 告诉父组件：加入成功啦，刷新一下搜索结果和书架状态！
      emit('refreshSearch'); 
      emit('refreshBookshelf');
    } catch (e) {
      console.error("加入书架失败", e);
    }
    return;
  }

  // 2. 正常拥有的书，打开阅读
  emit('openReader', book);         
};
</script>
