<template>
  <div class="fixed inset-0 bg-neutral-900 text-neutral-100 flex overflow-hidden z-50 font-sans">
    
    <div class="relative h-full flex-grow border-r border-neutral-800 bg-black flex items-center justify-center overflow-hidden" ref="readerMain">
      
      <div id="viewer" ref="viewer" class="w-full h-full"></div>
      
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
const backendApi = '/api';

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
// 主题注入：适配 Paginated 模式的流式布局
// ==========================================
const applyTheme = () => {
  if (!rendition) return;
  
  rendition.themes.default({
    // 1. 地毯式颜色覆盖：把所有基础和内联标签的底色变黑，文字变灰
    'body, p, span, a, b, i, em, strong, div, blockquote, ul, ol, li, section, article': {
      'background-color': '#000000 !important',
      'color': '#d4d4d4 !important',
      'font-family': 'system-ui, -apple-system, sans-serif !important', 
    },    
    
    // 2. 标题特殊对待：颜色提亮为纯白，保留呼吸感间距
    'h1, h2, h3, h4, h5, h6': {
      'background-color': '#000000 !important',
      'color': '#ffffff !important',
      'line-height': '1.4 !important',
      'margin-top': '1.5em !important',
      'margin-bottom': '1em !important',
    },

    // 3. 段落排版约束：控制行高和首行缩进
    'p': {
      'line-height': '1.6 !important',
      'margin-top': '0 !important', 
      'margin-bottom': '1em !important',
    },

    // 4. 图片防御机制（防止撑破单页）
    'img, svg, video': {
      'display': 'block !important', 
      'margin': '1em auto !important', 
      'max-width': '100% !important',
      'max-height': '80vh !important' 
    },

    // 5. 选词高亮
    '::selection': {
      'background': '#333333 !important'
    }
  });
};
// ==========================================
// 1. 生命周期与初始化 (重构极简版)
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
  try {
    epubBook = ePub(`/api/static/books/${props.book.id}/`);

    // --- 1. 离线/在线进度拉取逻辑 (保持稳定) ---
    let savedCfi = null;
    let isReadyToSave = false;
    const progressCacheKey = `offline_progress_${props.book.id}`;
    const syncPendingKey = `sync_pending_${props.book.id}`;
    const needsSync = localStorage.getItem(syncPendingKey) === 'true';

    if (needsSync) {
      console.log("🔄 提交离线进度...");
      savedCfi = localStorage.getItem(progressCacheKey);
      try {
        await fetch(`/api/books/${props.book.id}/progress`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'user-token': localStorage.getItem('geek_token') || '',
            'guest-uuid': localStorage.getItem('guest_uuid') || ''
          },
          body: JSON.stringify({ cfi: savedCfi, percentage: 0 }) 
        });
        localStorage.removeItem(syncPendingKey);
      } catch (e) {
        console.warn("🕸️ 依然离线");
      }
    } else {
      try {
        const res = await fetch(`/api/books/${props.book.id}/progress`, {
          headers: {
            'user-token': localStorage.getItem('geek_token') || '',
            'guest-uuid': localStorage.getItem('guest_uuid') || ''
          }
        });
        if (res.ok) {
          const data = await res.json();
          savedCfi = data.cfi;
          if (savedCfi) localStorage.setItem(progressCacheKey, savedCfi);
        }
      } catch (error) {
        savedCfi = localStorage.getItem(progressCacheKey);
      }
    }

    if (savedCfi === 'null' || savedCfi === 'undefined') savedCfi = null;

    // --- 2. 阅读器渲染初始化 ---
    rendition = epubBook.renderTo(viewer.value, {
      width: '100%',
      height: '100%',
      flow: 'paginated', // 强制横向分页模式
      manager: 'default',
      spread: 'none',
      allowScriptedContent: true
    });

    // 🎨 应用极简黑白灰主题 (无需再写 hooks 拦截器)
    applyTheme();

    // --- 3. 🚀 极速渲染与一键空降 ---
    // 解析保存的坐标。格式为: "epubcfi(...)|__|unit-123" 或纯 "epubcfi(...)"
    let targetLocation = savedCfi;
    if (savedCfi && savedCfi.includes('|__|')) {
      targetLocation = savedCfi.split('|__|')[0]; // 直接取前面绝对精准的标准 CFI
    }

    // 因为后端固化了DOM，现在的 CFI 是完全精准的，直接 display 即可
    console.log("🪂 启动一键空降...");
    await rendition.display(targetLocation || undefined);

    // 揭开幕布
    if (viewer.value) viewer.value.classList.add('animate-fade-in');
    
    // 初始化页码展示
    generatePagination(); 
    
    setTimeout(() => {
      isReadyToSave = true;
      console.log("🚀 初始渲染彻底完成，极简进度雷达已启动！");
    }, 500);

    // --- 4. ⚡️ 极简进度雷达：监听翻页，寻找 unit-X ---
    rendition.on('relocated', (location) => {
      if (!location) return;
      if (!isReadyToSave) return; // 防治初始化虚假翻页

      try {
        const contents = rendition.getContents()[0];
        const iframeDoc = contents.document;
        
        // 核心突破：获取 Iframe 的屏幕绝对偏移量
        const iframe = iframeDoc.defaultView.frameElement;
        const iframeOffset = iframe.getBoundingClientRect().left; 
        const viewWidth = window.innerWidth;
        
        // 直接寻找后端注入的雷达信标
        const targets = Array.from(iframeDoc.querySelectorAll('.sync-anchor'));
        let foundElement = null;

        for (let el of targets) {
          const rect = el.getBoundingClientRect();
          const absoluteLeft = rect.left + iframeOffset;
          
          // 容错率 -10，寻找当前屏幕左侧第一个出现的信标
          if (absoluteLeft >= -10 && absoluteLeft < viewWidth) {
            foundElement = el;
            break; 
          }
        }

        if (foundElement) {
          const preciseId = foundElement.id; // 例如: unit-145
          const spineItem = epubBook.spine.get(location.start.index);
          
          // 🎯 1. 生成稳定的原生 CFI (用于下次一键空降)
          const preciseCfi = new ePub.CFI(foundElement, spineItem.cfiBase).toString();
          
          // 🎯 2. 计算绝对百分比进度
          const unitMatch = preciseId.match(/unit-(\d+)/);
          const total = props.book.total_units || 1; 
          let progress = 0;

          if (unitMatch) {
            const currentUnit = parseInt(unitMatch[1]);
            progress = currentUnit / total;
            
            // 更新 UI 的全局数字展示
            currentPage.value = currentUnit;
            totalPages.value = total;
            inputPage.value = currentUnit;
          } else {
            // 极端情况兜底
            progress = location.start.percentage || 0;
          }

          // 🎯 3. 缝合保存：CFI 用于跳转，ID 方便后续 TTS 调用
          const combinedCfi = `${preciseCfi}|__|${preciseId}`;
          console.log(`🎯 [雷达锁定] 单元: ${preciseId}, 进度: ${(progress*100).toFixed(2)}%`);
          
          saveProgressToBackend(combinedCfi, progress);
        } else {
          console.warn("⚠️ 视野内未发现预处理信标");
        }
      } catch (e) {
        console.error("💥 [雷达程序崩溃]:", e);
      }
    });

    // 绑定交互事件
    rendition.on('selected', handleSelection);
    setupIframeClick();

  } catch (err) {
    console.error("💥 阅读器初始化崩溃:", err);
  }
};
// ==========================================
// 2. 交互与布局控制 (极致简化版)
// ==========================================
// iframe 内部点击监听
const setupIframeClick = () => {
  rendition.on('click', (e) => {
    if (showTocOverlay.value || showWiki.value) {
      showTocOverlay.value = false;
      showWiki.value = false;
      return;
    }
    const width = window.innerWidth;
    if (e.clientX < width * 0.3) {
      rendition.prev(); // 原生上一页
    } else if (e.clientX > width * 0.7) {
      rendition.next(); // 原生下一页
    } else {
      showBars.value = !showBars.value;
    }
  });
};

// 外层触控蒙版监听
const handleTouch = (event) => {
  const rect = readerMain.value.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const width = rect.width;

  if (showTocOverlay.value || showWiki.value) return;

  if (clickX < width * 0.3) {
    rendition.prev();
  } else if (clickX > width * 0.7) {
    rendition.next();
  } else {
    showBars.value = !showBars.value;
  }
};

const openTocOverlay = () => {
  showBars.value = false;
  showTocOverlay.value = true;
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
  
  rendition.annotations.add('highlight', cfiRange, {}, null, 'gray');
  contents.window.getSelection().removeAllRanges();
  summonReference(text);
};

const summonReference = async (query) => {
  showWiki.value = true;
  wikiContent.value = '<p class="text-neutral-500 font-mono text-center mt-10">⏳ Connecting to portal...</p>';
  
  setTimeout(() => {
    wikiContent.value = `
      <h1 class="text-2xl text-neutral-100 mb-4">${query}</h1>
      <p class="text-neutral-300 leading-relaxed">
        这是从后端拉取的 <strong>${query}</strong> 的解释。
      </p>
    `;
  }, 800);
};

// ==========================================
// 4. 分页与排版 (秒开极简版)
// ==========================================
let saveTimer = null;

const saveProgressToBackend = (cfi, progress) => {
  // 无论如何，先把最新进度刻印在本地 (这里的 cfi 已经是缝合好的 "epubcfi(...)|__|unit-X")
  localStorage.setItem(`offline_progress_${props.book.id}`, cfi);
  
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch(`/api/books/${props.book.id}/progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      },
      // 🐛 细节修复：后端 main.py 接收的是 "percent"，这里统一对齐
      body: JSON.stringify({ cfi: cfi, percent: progress }) 
    })
    .then(res => {
      if (res.ok) {
        // 🌐 联网保存成功，清理掉可能存在的"待同步"标记
        localStorage.removeItem(`sync_pending_${props.book.id}`);
      }
    })
    .catch(() => {
      // 📴 断网打上标记
      localStorage.setItem(`sync_pending_${props.book.id}`, 'true');
      console.log("📴 离线保存成功，已打上待同步标记！");
    });
  }, 2000);
};

// ⚡️ 初始化页码：直接白嫖后端的绝对真理数据，耗时 0 毫秒！
const generatePagination = () => {
  if (!epubBook) return;

  const total = props.book.total_units;
  totalPages.value = total || '???';

  // 初始渲染完成前，先用历史进度恢复底部栏的“当前页(单元)”数字
  if (total && props.book.progress) {
    currentPage.value = Math.max(1, Math.round(props.book.progress * total));
    inputPage.value = currentPage.value;
  }
};

// 🚀 极客空降法：按比例估算目标单元所在的章节
const jumpToTargetPage = () => {
  const targetUnit = parseInt(inputPage.value);
  const total = parseInt(totalPages.value);

  if (isNaN(targetUnit) || targetUnit < 1 || targetUnit > total) {
    inputPage.value = currentPage.value; // 非法输入弹回原位
    return;
  }
  
  // 我们无法直接用 ePub.js 跳转到某个自定义 ID，因为那需要先加载对应章节。
  // 完美解法：算出百分比 -> 算出目标章节 -> 空降到章节头部。
  const targetPercentage = targetUnit / total;
  const targetSpineIndex = Math.floor(targetPercentage * epubBook.spine.length);
  
  console.log(`🪂 正在跨越空间，空降至第 ${targetSpineIndex} 章节...`);
  
  // 飞跃到对应章节。用户落地后，雷达会自动扫描当前屏幕上的 unit-X 并更新页码。
  rendition.display(targetSpineIndex).then(() => {
    showBars.value = false; // 跳转后自动收起菜单栏，保持沉浸
  });
};

const cycleFontSize = () => {
  const sizes = [80, 100, 120, 140];
  const currentIndex = sizes.indexOf(currentFontSize.value);
  currentFontSize.value = sizes[(currentIndex + 1) % sizes.length];
  rendition.themes.fontSize(`${currentFontSize.value}%`);
  
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
// 5. TTS 赛博播音员
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
    const ttsApiUrl = `${backendApi}/tts/synthesize`;
    ttsPlayer.value.src = `${ttsApiUrl}?text=${encodeURIComponent(textToRead)}&voice=zh_CN-huayan-medium`;
    ttsPlayer.value.play();
    currentNodeIndex++;
  } else {
    jumpToNextChapter();
  }
};

const handleAudioEnded = () => {
  playNextSentence();
};

const handleAudioError = (e) => {
  console.error("TTS 音频流加载失败:", e);
  isReading.value = false;
};

const jumpToNextChapter = async () => {
  currentSpineIndex++;
  if (currentSpineIndex >= epubBook.spine.length) {
    isReading.value = false;
    return;
  }
  await rendition.display(epubBook.spine.get(currentSpineIndex).href);
  await extractAndPrepareText();
};
</script>

<style scoped>
#viewer {
  width: 100%;
  height: 100dvh; 
  /* 禁止文本跨列被截断 */
  column-fill: auto;
  opacity: 0;
}

.animate-fade-in {
  animation: fadeIn 0.2s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

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