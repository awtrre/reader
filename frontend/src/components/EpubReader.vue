<template>
  <div class="fixed inset-0 bg-neutral-900 text-neutral-100 flex overflow-hidden z-50 font-sans">
    
    <div class="relative h-full flex-grow border-r border-neutral-800 bg-black flex items-center justify-center overflow-hidden" ref="readerMain">
      
      <div id="viewer" ref="viewer" class="w-full" :style="{ height: exactViewerHeight }"></div>
      
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
        <span>{{ isReading ? 'STOP' : 'READ' }}</span>
      </button>
    </div>

    <div 
      v-show="showBars" 
      class="absolute bottom-0 left-0 right-0 h-16 bg-neutral-900/95 backdrop-blur-md border-t border-neutral-800 flex justify-between items-center px-6 z-40 transition-transform duration-300 animate-fade-in"
    >
      <button @click="openTocOverlay" class="text-neutral-400 hover:text-white text-sm tracking-widest font-mono flex items-center gap-2 transition-colors">
        ☰
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
        <div class="w-16"></div> 
      </div>
      
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
import { ref, onMounted, onUnmounted,nextTick } from 'vue';
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
const currentLineHeightPx = ref(26); // 默认给个整数
const exactViewerHeight = ref('100dvh');

// --- TTS 引擎状态 ---
const isReading = ref(false);
let currentSpineIndex = 0;
let textNodes = [];
let currentNodeIndex = 0;
// ==========================================
// 终极版主题注入：绝对网格对齐
// ==========================================
const applyTheme = () => {
  if (!rendition) return;
  
  // 算出绝对的整数行高
  const baseSize = 16 * (currentFontSize.value / 100);
  const absoluteLineHeight = Math.floor(baseSize * 1.6);
  currentLineHeightPx.value = absoluteLineHeight;

  // 锁定容器完美高度
  const screenHeight = window.innerHeight; 
  const maxLines = Math.floor(screenHeight / absoluteLineHeight);
  exactViewerHeight.value = `${maxLines * absoluteLineHeight}px`;

  rendition.themes.default({
    // 基础内联元素
    'body, span, a, b, i, em, strong': {
      'background-color': '#000000 !important',
      'color': '#d4d4d4 !important',
      'line-height': `${absoluteLineHeight}px !important`,
    },

    // 核心块级元素：暴力抹杀一切异样！
    // 扩充了捕获范围：figcaption, .caption, .notes 统统拉入网格！
    'p, div, blockquote, ul, ol, li, pre, section, article, figcaption, .caption, .notes': {
      'line-height': `${absoluteLineHeight}px !important`,
      'margin-top': '0 !important', 
      'margin-bottom': `${absoluteLineHeight}px !important`, // 段后距完美 1 倍行高
      'padding': '0 !important' // 严禁内边距撑开！
    },

    // ==========================================
    // 新增：角标【1】的绝杀中和方案 (解决 vertical-align 导致的行高增加)
    // ==========================================
    'sup, sub': {
      // 1. 强制行高为 0！这样它绝不会增加父级行框的高度。
      'line-height': '0 !important', 
      // 2. 核心！将垂直对齐设为基线，废除浏览器的 super 抬高效果。
      'vertical-align': 'baseline !important', 
      // 3. 准备进行手工微调位置，不影响父级高度计算。
      'position': 'relative !important', 
      // 4. 标准的角标小字号。
      'font-size': '75% !important' 
    },
    'sup': {
      // 5. 手工微调：向上移动 0.5em，视觉上看起来是角标，但物理高度依然在 26px 网格内！
      'top': '-0.5em !important' 
    },
    'sub': {
      // 下标向下移动。
      'bottom': '-0.25em !important' 
    },
    // ==========================================

    // 标题
    'h1, h2, h3, h4, h5, h6': {
      'line-height': `${absoluteLineHeight * 2}px !important`,
      'margin-top': `${absoluteLineHeight}px !important`,
      'margin-bottom': `${absoluteLineHeight}px !important`,
      'padding': '0 !important'
    },

    // 图片与多媒体
    'img, svg, video': {
      'display': 'block !important', 
      'vertical-align': 'top !important',
      'margin': `0 auto ${absoluteLineHeight}px auto !important`, 
      'padding': '0 !important',
      'border': 'none !important',
      'max-width': '100% !important'
    },
    'figure, .image-wrap, .fig': {
      'margin': '0 !important', 
      'padding': '0 !important',
      'line-height': '0 !important' 
    },

    // 分割线 hr
    'hr': {
      'margin': `${absoluteLineHeight}px 0 !important`,
      'height': '1px !important',
      'border': 'none !important',
      'background-color': '#333333 !important'
    },

    '::selection': {
      'background': '#333333 !important'
    }
  });
};
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
 
const initReader = async () => {
  // 1. 获取进度
  const res = await fetch(`/api/books/${props.book.id}/progress`, {
    headers: {
      'user-token': localStorage.getItem('geek_token') || '',
      'guest-uuid': localStorage.getItem('guest_uuid') || ''
    }
  });
  const data = await res.json();
  const savedCfi = data.cfi;

  // 2. 初始化书籍
  epubBook = ePub(`/api/static/books/${props.book.id}.epub`);
  // ==========================================
  // 3. 恢复为稳定且清爽的滚动模式
  rendition = epubBook.renderTo(viewer.value, {
    width: '100%',
    height: '100%',
    flow: 'scrolled-doc', // ⬅️ 回到滚动模式
    manager: 'continuous'
  });
  // 第4步：再注册 Hook，劫持图片
  rendition.hooks.content.register((contents) => {
    const doc = contents.document;
    const mediaElements = doc.querySelectorAll('img, svg, video');

    const snapToGrid = (el) => {
      const lh = currentLineHeightPx.value || 26; 
      
      // 优先读取 HTML 原生属性 height，防止图片未加载时高度为 0
      let rawHeight = parseFloat(el.getAttribute('height')) || el.naturalHeight || el.clientHeight || lh * 10;
      if (!rawHeight || rawHeight === 0) return;

      // 四舍五入到最近的行高整数倍
      let snappedHeight = Math.round(rawHeight / lh) * lh;
      if (snappedHeight < lh) snappedHeight = lh;

      // 使用 cssText 进行霸道覆盖，确保绝对不留一丝死角
      el.style.cssText = `
        display: block !important;
        height: ${snappedHeight}px !important;
        width: auto !important;
        max-width: 100% !important;
        max-height: none !important;
        margin: 0 auto ${lh}px auto !important; /* 强制图片底部必须是 1 倍行高 */
        padding: 0 !important;
        border: none !important;
        box-sizing: border-box !important;
        vertical-align: top !important;
      `;
    };

    mediaElements.forEach(el => {
      if (el.tagName.toLowerCase() === 'img') {
        if (el.complete) snapToGrid(el);
        else el.onload = () => snapToGrid(el);
      } else {
        snapToGrid(el);
      }
    });
  });
// 5. 恢复你最开始的干净主题，并加入段落约束
  applyTheme();
 // 6. 🚀 执行渲染：文字出来后再跑分页，防止灰屏 
  rendition.display(savedCfi || undefined).then(() => {
    console.log("🪄 文字已加载，后台开始计算分页...");
    generatePagination(savedCfi);
  });

    // 监听选中事件
  rendition.on('selected', handleSelection);
  setupIframeClick();
};

// ==========================================
// 最终版安全翻页
// ==========================================
const doSafeScroll = (direction) => { 
  const scrollContainer = rendition.manager.container;
  if (!scrollContainer) return;

  // 跨章加载检测保持不变
  const maxScroll = scrollContainer.scrollHeight - scrollContainer.clientHeight;
  if (direction === 1 && scrollContainer.scrollTop >= maxScroll - 5) {
    rendition.next(); 
    return;
  }
  if (direction === -1 && scrollContainer.scrollTop <= 5) {
    rendition.prev(); 
    return;
  }

  // 因为我们在 applyTheme 里把容器高度精确锁死了，这里直接获取
  const jumpStep = scrollContainer.clientHeight;

  // 使用绝对坐标平滑跳转
  const targetScrollTop = scrollContainer.scrollTop + (direction * jumpStep);
  scrollContainer.scrollTo({ top: targetScrollTop, left: 0 });
};
// ==========================================
// 2. 交互与布局控制
// ==========================================
// 替换原来的 setupIframeClick
const setupIframeClick = () => {
  rendition.on('click', (e) => {
    if (showTocOverlay.value || showWiki.value) {
      showTocOverlay.value = false;
      showWiki.value = false;
      return;
    }

    if (e.clientX < window.innerWidth * 0.3) {
      // 向上/前翻页
      doSafeScroll(-1);
    } else if (e.clientX > window.innerWidth * 0.7) {
      // 向下/后翻页
      doSafeScroll(1);
    } else {
      showBars.value = !showBars.value;
    }
  });
};

// 替换原来的 handleTouch
const handleTouch = (event) => {
  const rect = readerMain.value.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const width = rect.width;

  if (showTocOverlay.value || showWiki.value) return;

  if (clickX < width * 0.3) {
    // 替换掉原来的 rendition.prev()，使用安全滚动
    doSafeScroll(-1);
  } else if (clickX > width * 0.7) {
    // 替换掉原来的 rendition.next()，使用安全滚动
    doSafeScroll(1);
  } else {
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
// 4. 分页与排版 (计算虚拟页码 - 原始版)
// ==========================================
// 增加一个防抖计时器，避免滚动太快把数据库点爆
let saveTimer = null;

const saveProgressToBackend = (cfi, progress) => {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch(`/api/books/${props.book.id}/progress`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'user-token': localStorage.getItem('geek_token') || '', // 注入身份 [cite: 4]
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      },
      body: JSON.stringify({ 
        cfi: cfi, 
        percentage: progress 
      })
    });
  }, 2000); 
};

const generatePagination = async (savedCfi) => {
  if (!epubBook) return;

  // 1. 后台开始生成虚拟页码 (不阻塞主界面)
  await epubBook.locations.generate(600);
  totalPages.value = epubBook.locations.total;

  // 2. 计算完成后，强制校准一次当前页码
  // 如果没有 savedCfi，就拿当前正在显示的位置算
  const currentCfi = savedCfi || (rendition.currentLocation()?.start?.cfi);
  if (currentCfi) {
    const progress = epubBook.locations.percentageFromCfi(currentCfi);
    currentPage.value = Math.round(progress * totalPages.value) || 1;
    inputPage.value = currentPage.value;
  }

  // 3. 监听位置变动 (每次滚动结束都会触发)
  rendition.on('relocated', (location) => {
    const cfi = location.start.cfi;
    const progress = epubBook.locations.percentageFromCfi(cfi);
    
    // 更新本地页码显示状态
    currentPage.value = Math.round(progress * totalPages.value) || 1;
    inputPage.value = currentPage.value;

    // 核心：调用防抖存盘函数，把位置记在服务器的 library.db 里 [cite: 5]
    saveProgressToBackend(cfi, progress);
  });
};

const jumpToTargetPage = () => {
  const target = parseInt(inputPage.value);
  if (isNaN(target) || target < 1 || target > totalPages.value) {
    inputPage.value = currentPage.value;
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
  
  // ✨ 新增：同步保存字号到后端用户偏好 (layout_prefs) [cite: 5]
  fetch('/api/user/prefs', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'user-token': localStorage.getItem('geek_token') || '',
      'guest-uuid': localStorage.getItem('guest_uuid') || ''
    },
    body: JSON.stringify({ font_size: currentFontSize.value })
  });
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
/* 确保 viewer 占满屏幕即可 */
#viewer {
  width: 100%;
  /* 修复 1：使用 dvh 获取真实的移动端可视高度，保留 vh 作为旧设备兜底 */
  height: 100dvh; 
}
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
