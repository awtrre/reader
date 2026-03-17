<template>
  <header class="p-6 flex justify-center border-b border-neutral-800 shadow-sm shadow-black/50 shrink-0">
    <div class="relative w-full max-w-3xl">
      <span class="absolute left-4 top-3 text-neutral-500">❯</span>
      <input
        v-model="query"
        @keyup.enter="submitCommand"
        type="text"
        placeholder="Search books, or type /login <user> <pass> ..."
        class="w-full bg-neutral-950 border border-neutral-800 rounded-sm pl-10 pr-4 py-3 text-neutral-200 focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 outline-none transition-all font-mono text-sm"
      />
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue';

// 接收父组件传递的状态（比如是否是游客，未来可用于改变 placeholder 或 UI）
const props = defineProps({
  isGuest: Boolean
});

// 定义可以向父组件发送的事件
const emit = defineEmits(['command']);

const query = ref('');

const submitCommand = () => {
  const trimmedQuery = query.value.trim();
  if (!trimmedQuery) return;
  
  // 发送给 App.vue 处理
  emit('command', trimmedQuery);
  query.value = ''; // 提交后清空输入框
};
</script>
