<template>
  <div class="fixed inset-0 bg-neutral-900 text-neutral-100 flex overflow-hidden z-50 font-sans">
    
    <div class="relative h-full flex-grow border-r border-neutral-800" ref="readerMain">
      
      <div id="viewer" ref="viewer" class="h-full w-full"></div>
      
      <div class="absolute inset-0 grid grid-cols-[30%_40%_30%] z-10" @click="handleTouch">
        <div class="cursor-pointer"></div>
        <div class="cursor-pointer"></div>
        <div class="cursor-pointer"></div>
      </div>
    </div>

    <div 
      v-show="showBars" 
      class="absolute top-0 left-0 right-0 h-16 bg-neutral-900/95 backdrop-blur-md border-b border-neutral-800 flex justify-between items-center px-6 z-40 transition-transform duration-300 animate-fade-in"
    >
      <button @click="$emit('close')" class="text-neutral-400 hover:text-white text-sm tracking-widest font-mono transition-colors">
        ❮ BACK
      </button>
      <button @click="toggleTTS" class="text-neutral-400 hover:text-white text-sm tracking-widest font-mono flex items-center gap-2 transition-colors">
        <span>{{ isReading ? '⏹ STOP TTS' : '▶️ READ ALOUD' }}</span>
      </button>
    </div>

    <div 
      v-show="showBars" 
      class="absolute bottom-0 left-0 right-0 h-16 bg-neutral-900/95 backdrop-blur-md border-t border-neutral-800 flex justify-between items-center px-6 z-40 transition-transform duration-300 animate-fade-in"
    >
      <button @click="openTocOverlay" class="text-neutral-400 hover:text-white text-sm tracking-widest font-mono flex items-center gap-2 transition-colors">
        ☰ 章节
      </button>
      
      <div class="flex items-center gap-2 text-sm font-mono z-50">
        <input 
          v-model="inputPage" 
          @keyup.enter="jumpToTargetPage" 
          @focus="inputPage = ''" 
          @blur="inputPage = currentPage" 
          type="text" 
          class="w-12 text-center bg-neutral-800 text-neutral-200 border border-neutral-700 rounded-sm py-1 outline-none focus:border-neutral-400 focus:ring-1 focus:ring-neutral-400 transition-all relative z-50" 
        />
        <span class="text-neutral-600">/ {{ totalPages }}</span>
      </div>

      <button @click="cycleFontSize" class="text-neutral-400 hover:text-white text-lg font-serif px-4 transition-colors">
        Aa
      </button>
    </div>

    <div v-if="showTocOverlay" class="fixed inset-0 bg-neutral-950 z-50 flex flex-col animate-fade-in">
      <div class="h-16 border-b border-neutral-800 flex justify-between items-center px-8">
        <button @click="showTocOverlay = false" class="text-neutral-500 hover:text-neutral-200 text-sm tracking-widest transition-colors font-mono">
          ✕ EXIT
        </button>
        <div class="flex gap-8 text-sm font-bold tracking-widest">
          <button @click="activeOverlayTab = 'toc'" :class="activeOverlayTab === 'toc' ? 'text-neutral-100 border-b-2 border-neutral-100' : 'text-neutral-600 hover:text-neutral-400'" class="pb-1 transition-all">目录</button>
          <button @click="activeOverlayTab = 'highlights'" :class="activeOverlayTab === 'highlights' ? 'text-neutral-100 border-b-2 border-neutral-100' : 'text-neutral-600 hover:text-neutral-400'" class="pb-1 transition-all">勾画</button>
          <button @click="activeOverlayTab = 'notes'" :class="activeOverlayTab === 'notes' ? 'text-neutral-100 border-b-2 border-neutral-100' : 'text-neutral-600 hover:text-neutral-400'" class="pb-1 transition-all">批注</button>
        </div>
        <div class="w-16"></div> </div>
      
      <div class="flex-1 overflow-y-auto p-8 max-w-3xl mx-auto w-full scrollbar-hide">
        <ul v-if="activeOverlayTab === 'toc'" class="space-y-4">
          <li v-for="item in tocList" :key="item.id" @click="jumpToCfiAndClose(item.href)" class="text-neutral-400 hover:text-neutral-100 cursor-pointer border-b border-neutral-800 pb-2 transition-colors">
            {{ item.label }}
          </li>
        </ul>
        <div v-else class="text-center text-neutral-600 mt-20 font-mono text-sm">
          No data recorded yet.
        </div>
      </div>
    </div>

    <div 
      v-if="showWiki" 
      class="absolute right-0 w-1/2 h-full bg-neutral-950/95 backdrop-blur-sm p-8 overflow-y-auto transform transition-transform duration-300 border-l border-neutral-800 z-50 shadow-2xl"
    >
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-sm font-bold tracking-[0.3em] text-neutral-400">REFERENCE PORTAL</h3>
        <button @click="showWiki = false" class="text-xl text-neutral-600 hover:text-white transition-colors">×</button>
      </div>
      <div class="wiki-content prose prose-neutral prose-invert max-w-none" v-html="wikiContent"></div>
    </div>

    <audio ref="ttsPlayer" @ended="handleAudioEnded" @error="handleAudioError" class="hidden"></audio>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import ePub from 'epubjs';

const props = defineProps({
  book: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close']);

// --- DOM 引用 ---
const viewer = ref(null);
const readerMain = ref(null);
const ttsPlayer = ref(null);

// --- 核心实例 ---
let epubBook = null;
let rendition = null;
const backendApi = '/api'; // 指向 Nginx 的后端代理

// --- 界面控制状态 ---
const showBars = ref(false);
const showWiki = ref(false);
const showTocOverlay = ref(false);
const activeOverlayTab = ref('toc');

// --- 数据与分页状态 ---
const wikiContent = ref('');
const tocList = ref([]);
const currentPage = ref(1);
const totalPages = ref('???');
const inputPage = ref('1');
const currentFontSize = ref(100);

// --- TTS 引擎状态 ---
const isReading = ref(false);
let currentSpineIndex = 0;
let textNodes = [];
let currentNodeIndex = 0;

// ==========================================
// 1. 生命周期与初始化
// ==========================================
onMounted(() => {
  initReader();
});

onUnmounted(() => {
  if (epubBook) {
    epubBook.destroy();
  }
});

const initReader = () => {
  // 假定后端可以直接通过书籍 ID 提供 EPUB 文件流
  epubBook = ePub(`${backendApi}/books/${props.book.id}.epub`); 

  rendition = epubBook.renderTo(viewer.value, {
    width: '100%',
    height: '100%',
    flow: 'scrolled-doc', // 滚动流模式，适合极简阅读
    manager: 'continuous',
  });

  rendition.display();

  // 监听选中文本，触发高亮与字典/维基
  rendition.on('selected', handleSelection);
  
  // 生成虚拟页码
  generatePagination();
};

// ==========================================
// 2. 交互与布局控制
// ==========================================
const handleTouch = (event) => {
  const rect = readerMain.value.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const width = rect.width;

  // 屏蔽点击穿透导致的意外翻页
  if (showTocOverlay.value || showWiki.value) return;

  if (clickX < width * 0.3) {
    rendition.prev();
  } else if (clickX > width * 0.7) {
    rendition.next();
  } else {
    // 点击中间区域，切换菜单显示状态
    showBars.value = !showBars.value;
  }
};

const openTocOverlay = () => {
  showBars.value = false;
  showTocOverlay.value = true;
  // 获取书籍目录
  epubBook.loaded.navigation.then(nav => {
    tocList.value = nav.toc;
  });
};

const jumpToCfiAndClose = (cfiOrHref) => {
  rendition.display(cfiOrHref);
  showTocOverlay.value = false;
};

// ==========================================
// 3. 选词高亮与维基反代加载
// ==========================================
const handleSelection = (cfiRange, contents) => {
  const text = rendition.getRange(cfiRange).toString();
  if (!text) return;
  
  // 添加极简灰色高亮
  rendition.annotations.add('highlight', cfiRange, {}, null, 'gray');
  // 清除浏览器默认的蓝色选中背景
  contents.window.getSelection().removeAllRanges();
  
  summonReference(text);
};

const summonReference = async (query) => {
  showWiki.value = true;
  wikiContent.value = '<p class="text-neutral-500 font-mono text-center mt-10">⏳ Connecting to external portal...</p>';
  
  // 模拟请求后端的 SOCKS5 代理接口
  setTimeout(() => {
    wikiContent.value = `
      <h1 class="text-2xl text-neutral-100 mb-4">${query}</h1>
      <p class="text-neutral-300 leading-relaxed">
        这是从后端反代服务器拉取的 <strong>${query}</strong> 的解释。
        极简主题 CSS 已自动应用，与整体禁欲系风格保持一致。
      </p>
    `;
  }, 800);
};

// ==========================================
// 4. 分页与排版 (计算虚拟页码)
// ==========================================
const generatePagination = async () => {
  if (!epubBook) return;
  // 每 1600 字符算作一页
  await epubBook.locations.generate(1600);
  totalPages.value = epubBook.locations.total;

  rendition.on('relocated', (location) => {
    let rawPage = epubBook.locations.percentageFromCfi(location.start.cfi);
    currentPage.value = Math.round(rawPage * totalPages.value) || 1;
    inputPage.value = currentPage.value;
  });
};

const jumpToTargetPage = () => {
  const target = parseInt(inputPage.value);
  if (isNaN(target) || target < 1 || target > totalPages.value) {
    inputPage.value = currentPage.value; // 非法输入则回退
    return;
  }
  const cfi = epubBook.locations.cfiFromPercentage(target / totalPages.value);
  rendition.display(cfi);
};

const cycleFontSize = () => {
  const sizes = [80, 100, 120, 140];
  const currentIndex = sizes.indexOf(currentFontSize.value);
  currentFontSize.value = sizes[(currentIndex + 1) % sizes.length];
  rendition.themes.fontSize(`${currentFontSize.value}%`);
  // 注意：真实环境中字号改变需要重新调用 epubBook.locations.generate() 重新分页
};

// ==========================================
// 5. TTS 赛博播音员 (无缝分句与跨章)
// ==========================================
const toggleTTS = async () => {
  if (isReading.value) {
    ttsPlayer.value.pause();
    isReading.value = false;
    return;
  }
  
  isReading.value = true;
  const currentLocation = rendition.currentLocation();
  if (!currentLocation) return;
  
  currentSpineIndex = currentLocation.start.index;
  await extractAndPrepareText();
};

const extractAndPrepareText = async () => {
  const spineItem = epubBook.spine.get(currentSpineIndex);
  await spineItem.load(epubBook.load.bind(epubBook));
  const chapterText = spineItem.document.body.textContent || spineItem.document.body.innerText;
  
  // 极简分句法：按标点符号切分句子，避免单次音频流过长
  textNodes = chapterText
    .replace(/\s+/g, ' ')
    .split(/(?<=[。！？!?])/)
    .map(t => t.trim())
    .filter(t => t.length > 0);
    
  currentNodeIndex = 0;
  playNextSentence();
};

const playNextSentence = () => {
  if (!isReading.value) return;

  if (currentNodeIndex < textNodes.length) {
    const textToRead = textNodes[currentNodeIndex];
    // 调用后端 TTS 接口流式合成语音
    const ttsApiUrl = `${backendApi}/tts/synthesize`;
    ttsPlayer.value.src = `${ttsApiUrl}?text=${encodeURIComponent(textToRead)}&voice=zh_CN-huayan-medium`;
    ttsPlayer.value.play();
    currentNodeIndex++;
  } else {
    // 当前章节读完，触发跃迁前往下一章
    jumpToNextChapter();
  }
};

const handleAudioEnded = () => {
  // 一句播完，无缝衔接下一句
  playNextSentence();
};

const handleAudioError = (e) => {
  console.error("TTS 音频流加载失败:", e);
  isReading.value = false;
};

const jumpToNextChapter = async () => {
  currentSpineIndex++;
  if (currentSpineIndex >= epubBook.spine.length) {
    isReading.value = false; // 全书终
    return;
  }
  // 视觉上也同步翻到下一章
  await rendition.display(epubBook.spine.get(currentSpineIndex).href);
  await extractAndPrepareText();
};
</script>

<style scoped>
/* 极简淡入动画 */
.animate-fade-in {
  animation: fadeIn 0.2s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 隐藏滚动条 */
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

/* 覆盖维基百科返回内容的样式，使其符合深色主题 */
.wiki-content :deep(a) { 
  color: #a3a3a3; 
  text-decoration: underline; 
}
.wiki-content :deep(p) { 
  color: #d4d4d4; 
  margin-bottom: 1em;
}
.wiki-content :deep(h1), 
.wiki-content :deep(h2), 
.wiki-content :deep(h3) { 
  color: #f5f5f5; 
  font-weight: bold; 
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}
</style>
