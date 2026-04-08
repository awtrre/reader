<template>
  <div class="fixed inset-0 bg-neutral-900 text-neutral-100 flex overflow-hidden z-50 font-sans select-none">
    
    <div class="relative h-full flex-grow border-r border-neutral-800 bg-black flex items-center justify-center overflow-hidden" ref="readerMain">
      
      <div id="viewer" ref="viewer" class="w-full h-full"></div>
      <div
        v-if="showBars"
        class="absolute inset-0 z-30"
        @click.stop="showBars = false"
        @touchstart.prevent="showBars = false"
      ></div>

      <div
        v-if="showSelectionMenu"
        class="absolute z-50 bg-neutral-900 border border-neutral-800 shadow-2xl flex items-center font-mono text-xs tracking-widest animate-fade-in"
        :style="{ top: selectionMenuPos.y + 'px', left: selectionMenuPos.x + 'px', transform: 'translate(-50%, -100%)', marginTop: '-12px' }"
      >
        <button @click="copyText" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">COPY</button>
        <div class="w-px h-4 bg-neutral-800"></div>
        <button @click="searchInWiki" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">SEARCH</button>
        <div class="w-px h-4 bg-neutral-800"></div>
        <button v-if="!isSelectionOverlapping" @click="markAnnotation" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">MARK</button>
        <button v-else @click="deleteOverlappingAnnotation" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">DELETE</button>

        <div class="absolute left-1/2 bottom-0 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-transparent border-t-neutral-900"></div>
        <div class="absolute left-1/2 bottom-[-1px] transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-[7px] border-r-[7px] border-t-[7px] border-transparent border-t-neutral-800 -z-10"></div>
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

    <div v-if="showAnnotationPanel" class="fixed inset-0 z-50 flex flex-col justify-end animate-fade-in">
      <div class="absolute inset-0" @click="closeAnnotationPanel"></div>
      
      <div class="relative h-1/2 bg-neutral-900 border-t border-neutral-800 flex flex-col pointer-events-auto">
        <div class="flex justify-start gap-8 px-8 py-4 border-b border-neutral-800 text-xs font-mono tracking-widest bg-neutral-900">
           <button @click="copyText" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">COPY</button>
           <button @click="searchInWiki" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">SEARCH</button>
           <button v-if="!isSelectionOverlapping" @click="markAnnotation" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">MARK</button>
           <button v-else @click="deleteOverlappingAnnotation" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">DELETE</button>
        </div>
        <textarea 
          v-model="currentNoteText" 
          @input="syncNote"
          class="flex-1 bg-transparent p-8 outline-none text-neutral-300 resize-none" 
          placeholder="Write something..."
        ></textarea>
      </div>
    </div>

    <div v-if="showTocOverlay" class="fixed inset-0 bg-neutral-900 z-50 flex flex-col animate-fade-in">
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

    <div v-if="showWiki" class="fixed inset-0 z-50 flex flex-col justify-end animate-fade-in">
      <div class="absolute inset-0" @click="closeWiki"></div>
      
      <div class="relative h-1/2 bg-neutral-900 border-t border-neutral-800 flex flex-col pointer-events-auto">
        <div class="flex justify-start gap-8 px-8 py-4 border-b border-neutral-800 text-xs font-mono tracking-widest bg-neutral-900">
          <button @click="copyText" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">COPY</button>
          <button @click="switchToAnnotation" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">ANNOTATION</button>
          <button v-if="!isSelectionOverlapping" @click="markAnnotation" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">MARK</button>
          <button v-else @click="deleteOverlappingAnnotation" class="text-neutral-500 hover:text-neutral-100 transition-colors outline-none focus:outline-none">DELETE</button>
        </div>
        <div class="flex-1 overflow-y-auto p-8">
          <div class="wiki-content prose prose-neutral prose-invert max-w-none text-sm" v-html="wikiContent"></div>
        </div>
      </div>
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
let unitMap = [];
const backendApi = '/api';

// --- 界面控制状态 ---
const showBars = ref(false);
const showWiki = ref(false);
const showTocOverlay = ref(false);
const activeOverlayTab = ref('toc');

// --- 数据与分页状态 ---
const wikiContent = ref('');
const tocList = ref([]);
const currentPage = ref('-');
const totalPages = ref('-');
const inputPage = ref('-');
const currentFontSize = ref(100);
let isJumpLocked = false;

// --- TTS 引擎状态 ---
const isReading = ref(false);
let currentSpineIndex = 0;
let textNodes = [];
let currentNodeIndex = 0;

// --- ✨选词与批注专属状态 ---
const showSelectionMenu = ref(false);
const isSelectionOverlapping = ref(false);
const selectionMenuPos = ref({ x: 0, y: 0 }); 
const currentSelection = ref({ cfi: null, text: '' });
const showAnnotationPanel = ref(false);
const currentNoteText = ref('');
const activeHighlightCfi = ref(null);
const annotationDataMap = {};
let lastClickTime = 0;   
let isPointerDown = false; 
let pendingSelection = null;
let uiWasOpen = false;   
let tapActionTimer = null;
let overlappingCfi = null;
let isGlobalShieldActive = false; // 护盾是否开启
let globalShieldTimer = null;     // 护盾倒计时器
let touchStartTime = 0;           // 记录按下瞬间的时间（用于判断长按）
let isDragging = false;

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
      '-webkit-touch-callout': 'none !important',
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
      'background': '#262626 !important', 
      'color': '#ffffff !important' // 确保被选中的文字保持纯白
    },
    // 6. ✨ 新增：高亮防覆盖机制
    '.custom-hl': {
      'pointer-events': 'auto !important',       // 保证它依然能被点击
      'user-select': 'none !important',          // 彻底禁止在这个高亮块上二次划词
      '-webkit-user-select': 'none !important'
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
          if (data.font_size) {           // ✨ 新增：读取并设置专属字号
            currentFontSize.value = data.font_size;
          }
        }
      } catch (error) {
        savedCfi = localStorage.getItem(progressCacheKey);
      }
    }

    if (savedCfi === 'null' || savedCfi === 'undefined') savedCfi = null;
    //  偷偷拉取这本魔法书的藏宝图 (unit_map.json)
    try {
      const mapRes = await fetch(`/api/static/books/${props.book.id}/unit_map.json`);
      if (mapRes.ok) {
        unitMap = await mapRes.json();
        console.log("🗺️ 藏宝图获取成功！包含章节数:", unitMap.length);
      }
    } catch (e) {
      console.warn("⚠️ 未找到藏宝图");
    }
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
    rendition.themes.fontSize(`${currentFontSize.value}%`);  // ✨ 确保在 display 渲染前，先设置好拿到的字号
    // --- ✨ 新增：注入 iframe 底层原生守卫 ---
    rendition.on('rendered', (e, iframe) => {
      const doc = iframe.document;

      doc.addEventListener('touchmove', () => { 
        isDragging = true; 
      }, { passive: true });
      
      doc.addEventListener('mousemove', () => { 
        isDragging = true; 
      }, { passive: true });

      doc.addEventListener('selectionchange', () => {
        const selection = iframe.window.getSelection();
        if (isPointerDown && Date.now() - touchStartTime < 300 && !isDragging) {
           if (selection && !selection.isCollapsed) {
               selection.removeAllRanges();
               return; // 瞬间拦截，不往下走了
           }
        }
        if (!selection || selection.isCollapsed || selection.toString().trim() === '') {
          // 这里太频繁了就不打日志了
          showSelectionMenu.value = false;
          pendingSelection = null;
        } else {
          showSelectionMenu.value = false; 
        }
      });

      const finalizeSelection = () => {
        isPointerDown = false;
        setTimeout(() => {
          if (pendingSelection) {
            selectionMenuPos.value = pendingSelection.pos;
            currentSelection.value = { ...pendingSelection };
            showSelectionMenu.value = true;
            pendingSelection = null;
          }
        }, 50); 
      };

      // 🚀 新增：光标拖拽结束侦测器
      const handleHandleDragEnd = () => {
        const selection = iframe.window.getSelection();
        // 如果手指离开时，原生选区还在，说明用户刚拉完光标！
        if (selection && !selection.isCollapsed && selection.toString().trim() !== '') {
          const contents = rendition.getContents()[0];
          if (contents) {
            try {
              const range = selection.getRangeAt(0);
              // 利用 epubjs 内部方法，把原生 range 重新转成你需要的 cfiRange
              const cfiRange = contents.cfiFromRange(range); 
              if (cfiRange) {
                // 主动喂给你的核心处理逻辑，重新计算坐标和文本！
                handleSelection(cfiRange, contents); 
              }
            } catch(err) {
              console.warn("光标转换失败", err);
            }
          }
        }
        finalizeSelection();
      };

      // ⚠️ 替换掉你原有的 touchend / mouseup 监听
      doc.addEventListener('touchend', handleHandleDragEnd);
      doc.addEventListener('mouseup', handleHandleDragEnd);
    });

// --- 3. 🚀 极速渲染与一键空降 (极简重构版) ---
let targetLocation = savedCfi;
let initialPageNumber = 0;

// 🎯 核心逻辑：仅识别 unit-X 格式。不再计算百分比，不再兼容旧分隔符
if (savedCfi && savedCfi.startsWith('unit-') && unitMap.length > 0) {
  const targetUnitId = parseInt(savedCfi.split('-')[1], 10);
  initialPageNumber = targetUnitId; 
  
  // 从地图中检索该单元所属的物理文件 (href)
  const mapItem = unitMap.find(m => targetUnitId >= m.start && targetUnitId <= m.end);
  if (mapItem) {
    // 拼接成 Epub.js 识别的锚点格式：chapter1.xhtml#unit-145
    targetLocation = `${mapItem.href}#${savedCfi}`;
  }
}

// ✨ 状态灌注：直接同步 UI，不再通过函数中转
currentPage.value = initialPageNumber;
inputPage.value = initialPageNumber;
totalPages.value = props.book.total_units || '-';

try {
  // 执行空降
  await rendition.display(targetLocation || undefined);
} catch (error) {
  console.warn("⚠️ 坐标失效，强制回滚至起点", error);
  localStorage.removeItem(`offline_progress_${props.book.id}`);
  await rendition.display(); 
}

// 动画与雷达激活
if (viewer.value) viewer.value.classList.add('animate-fade-in');

setTimeout(() => {
  isReadyToSave = true; // 落地 500ms 后才允许雷达扫描存档，防止初始化跳变
  console.log("🚀 渲染彻底完成，雷达已锁定精准信标");
}, 500);

    // --- 4. ⚡️ 极简进度雷达：监听翻页，寻找 unit-X ---
    rendition.on('relocated', (location) => {
      if (!location) return;
      if (!isReadyToSave) return; // 防治初始化虚假翻页
      if (isJumpLocked) {         // 🛡️ 500ms 盾生效，拦截跳转后的余震/二次触发
        console.log("🛡️ 500ms盾生效中，已拦截二次提交");
        return;
      }

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
          
          // 🎯 1. 计算绝对百分比进度
          const unitMatch = preciseId.match(/unit-(\d+)/);
          const total = props.book.total_units || 1; 
          let progress = 0;

          if (unitMatch) {
            const currentUnit = parseInt(unitMatch[1]);
            progress = currentUnit / total;
            
            currentPage.value = currentUnit;
            totalPages.value = total;
            inputPage.value = currentUnit;
          } else {
            progress = location.start.percentage || 0;
          }

          // 🎯 2. 极致瘦身：只存 unit-xxxx！彻底抛弃原生 CFI
          console.log(`🎯 [雷达锁定] 绝对单元: ${preciseId}, 进度: ${(progress*100).toFixed(2)}%`);
          
          // 直接将 "unit-145" 传给后端和本地，清爽无比！
          saveProgressToBackend(preciseId, progress); 
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
const activateGlobalShield = (duration = 400) => {
  isGlobalShieldActive = true;
  clearTimeout(globalShieldTimer); // 重新计算时间，防止多次连续触发导致时间错乱
  globalShieldTimer = setTimeout(() => {
    isGlobalShieldActive = false;
  }, duration);
};
// iframe 内部点击监听
const setupIframeClick = () => {
  let startX = 0;
  let startY = 0;

  const recordStart = (e) => {
    if (isGlobalShieldActive) return; // 🛡️ 护盾开启时，彻底无视按压
    touchStartTime = Date.now(); // ⏱️ 记录按下时间
    isDragging = false;
    isPointerDown = true;
    pendingSelection = null;

    // ⚡ 修复 1：在清空任何 UI 前，先拍一张“快照”
    // 如果手指按下去的时候，屏幕上有任何菜单/面板，就标记为 true
    uiWasOpen = showBars.value || showSelectionMenu.value || showTocOverlay.value || showWiki.value || showAnnotationPanel.value;

    showSelectionMenu.value = false; 

    const event = e.changedTouches ? e.changedTouches[0] : e;
    startX = event.clientX;
    startY = event.clientY;
  };

  const handlePointerUp = (e) => {
    const costTime = Date.now() - touchStartTime;
    if (isGlobalShieldActive) return;
    isPointerDown = false; 
    if (pendingSelection) {
      setTimeout(() => {
        if (pendingSelection) {
          selectionMenuPos.value = pendingSelection.pos;
          currentSelection.value = { ...pendingSelection };
          showSelectionMenu.value = true;
          pendingSelection = null;
        }
      }, 50);
    }
    const now = Date.now();
    if (now - lastClickTime < 300) {
      return; 
    }
    lastClickTime = now;

    const event = e.changedTouches ? e.changedTouches[0] : e;
    const endX = event.clientX;
    const endY = event.clientY;
    const deltaX = Math.abs(endX - startX);
    const deltaY = Math.abs(endY - startY);


    // 🛡️ 拦截器 1：使用刚拍好的“快照”来判断！
    // 如果按下瞬间有 UI 挡着，说明用户的核心诉求是“退出 UI”，绝对不许翻页！
    if (uiWasOpen) {
      showBars.value = false;
      showTocOverlay.value = false;
      showWiki.value = false;
      showAnnotationPanel.value = false;
      
      const contents = rendition.getContents()[0];
      if (contents) contents.window.getSelection().removeAllRanges();
      return; 
    }

    if (deltaX > 10 || deltaY > 10) {
      return;
    }

    const contents = rendition.getContents()[0];
    const selection = contents ? contents.window.getSelection() : null;
    if (costTime < 400) {
      if (selection) selection.removeAllRanges();
    } else {
      if (selection && !selection.isCollapsed && selection.toString().trim().length > 0) {
        return; 
      }
    }
    // ⚡ 修复 2：给“翻页/呼出菜单”加上 80ms 的生死时速延迟！
    // 为什么？为了让 Epub.js 有时间去触发“点击了高亮块”的事件
    clearTimeout(tapActionTimer);
    tapActionTimer = setTimeout(() => {
      const screenWidth = window.innerWidth;
      const realX = endX % screenWidth; 
      let isPageTurned = false; 

      if (realX < screenWidth * 0.3) {
        rendition.prev();
        isPageTurned = true;
      } else if (realX > screenWidth * 0.7) {
        rendition.next();
        isPageTurned = true;
      } else {
        showBars.value = !showBars.value;
      }

      if (isPageTurned) {
        activateGlobalShield(400);
      }
    }, 80); 
  };

  rendition.on('mousedown', recordStart);
  rendition.on('mouseup', handlePointerUp);
  rendition.on('touchstart', recordStart);
  rendition.on('touchend', handlePointerUp);
};

// 外层触控蒙版监听
const handleTouch = (event) => {
  if (isGlobalShieldActive) return;
  const rect = readerMain.value.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const width = rect.width;
  if (showTocOverlay.value || showWiki.value) return;
  let isPageTurned = false;
  if (clickX < width * 0.3) {
    rendition.prev();
    isPageTurned = true;
  } else if (clickX > width * 0.7) {
    rendition.next();
    isPageTurned = true;
  } else {
    showBars.value = !showBars.value;
  }
  if (isPageTurned) {
    activateGlobalShield(400);
  }
};

const openTocOverlay = () => {
  showBars.value = false;
  showTocOverlay.value = true;
  epubBook.loaded.navigation.then(nav => {
    // 定义一个递归辅助函数来展平目录
    const flattenToc = (items, level = 0) => {
      return items.reduce((acc, item) => {
        const indent = level > 0 ? '　'.repeat(level) : '';
        acc.push({
          ...item,
          label: indent + item.label // 修改显示文案
        });
        if (item.subitems && item.subitems.length > 0) {
          acc.push(...flattenToc(item.subitems, level + 1));
        }
        return acc;
      }, []);
    };
    tocList.value = flattenToc(nav.toc);
  });
};

const jumpToCfiAndClose = (cfiOrHref) => {
  rendition.display(cfiOrHref);
  showTocOverlay.value = false;
};

// ==========================================
// 3. 选词高亮与维基反代加载
// ==========================================
// ⚡ 核心提取引擎：将选区拆解为 [{nodeX, start, end}, ...] 的标准数组
const extractSegments = (range, doc) => {
  const segmentsMap = {};
  
  // 🐛 核心修复1：解决同段落划线时，祖先节点为纯文本导致无法遍历的 Bug
  let root = range.commonAncestorContainer;
  if (root.nodeType === 3) {
    root = root.parentNode; // 强行提升到包裹它的 HTML 标签（如 <p> 或 <div>）
  }

  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let currentNode;

  while ((currentNode = walker.nextNode())) {
    // 只处理在选区内的文本节点
    if (!range.intersectsNode(currentNode)) continue;

    // 🎯 完美复刻你原本的提取逻辑：向上寻找最近的 [id]
    const targetEl = currentNode.parentElement ? currentNode.parentElement.closest('[id]') : null;
    if (!targetEl) continue;

    const nodeId = targetEl.id;

    // 📏 完全使用你最开始写的克隆 Range 算长度法
    const preRange = doc.createRange();
    preRange.selectNodeContents(targetEl);
    // 把截断点设为当前小文本节点的头部
    preRange.setEnd(currentNode, 0); 
    const prefixLen = preRange.toString().length;

    // 计算选区在这个特定文本节点上的起止点
    let start = currentNode === range.startContainer ? range.startOffset : 0;
    let end = currentNode === range.endContainer ? range.endOffset : currentNode.length;
    
    // 过滤掉选区边缘的空截断
    if (start === end) continue;

    // 绝对偏移量 = 前面所有兄弟文本的长度 + 自己内部的偏移量
    const blockStart = prefixLen + start;
    const blockEnd = prefixLen + end;

    // 存入或自动合并跨标签的段落数据
    if (!segmentsMap[nodeId]) {
      segmentsMap[nodeId] = { nodeX: nodeId, startOffset: blockStart, endOffset: blockEnd };
    } else {
      segmentsMap[nodeId].startOffset = Math.min(segmentsMap[nodeId].startOffset, blockStart);
      segmentsMap[nodeId].endOffset = Math.max(segmentsMap[nodeId].endOffset, blockEnd);
    }
  }
  
  return Object.values(segmentsMap);
};

const handleSelection = (cfiRange, contents) => {
  
  if (isGlobalShieldActive) {
    contents.window.getSelection().removeAllRanges();
    return;
  }
  
  const costTime = Date.now() - touchStartTime;
  if (costTime < 400 && !isDragging) {
    contents.window.getSelection().removeAllRanges();
    return;
  }

  if (showBars.value) {
    contents.window.getSelection().removeAllRanges();
    return;
  }
  
  const text = rendition.getRange(cfiRange).toString().trim();
  if (!text) return;

  const range = contents.window.getSelection().getRangeAt(0);
  
  // 1. ✨ 用新引擎提取当前选区的精准坐标组
  const currentSegments = extractSegments(range, contents.document);

  // 2. ✨ 纯数据碰撞检测 (取代之前的 DOM 检测)
  isSelectionOverlapping.value = false;
  overlappingCfi = null;

  for (const [savedCfi, savedData] of Object.entries(annotationDataMap)) {
    // 只要有任意一段 nodeX 相同，且线段有交集，就算作碰撞！
    const isOverlap = currentSegments.some(currSeg => {
      return savedData.segments.some(savedSeg => {
        if (currSeg.nodeX !== savedSeg.nodeX) return false;
        // 核心数学：两线段相交的条件是 max(起点) < min(终点)
        return Math.max(currSeg.startOffset, savedSeg.startOffset) < Math.min(currSeg.endOffset, savedSeg.endOffset);
      });
    });

    if (isOverlap) {
      isSelectionOverlapping.value = true;
      overlappingCfi = savedCfi;
      break;
    }
  }

  // 计算菜单弹出的物理位置 (保持不变)
  const rect = range.getBoundingClientRect();
  const iframe = contents.document.defaultView.frameElement;
  const iframeRect = iframe.getBoundingClientRect();
  const pos = { 
    x: rect.left + iframeRect.left + (rect.width / 2), 
    y: rect.top + iframeRect.top 
  };

  // 3. ✨ 组装全新的纯净数据包
  const selectionData = {
    cfi: cfiRange, // cfi 仅作给 epubjs 绘图用的身份证
    text: text, 
    pos: pos, 
    segments: currentSegments // 👈 存入刚刚提取的精美数组！
  };

  if (isPointerDown) {
    pendingSelection = selectionData;
  } else {
    selectionMenuPos.value = pos;
    currentSelection.value = selectionData;
    showSelectionMenu.value = true;
  }
};

const closeSelection = () => {
  showSelectionMenu.value = false;
  if (rendition) {
    const contents = rendition.getContents()[0];
    if (contents) contents.window.getSelection().removeAllRanges(); // 取消原生的蓝色选区
  }
};
const clearNativeSelection = () => {
  if (rendition) {
    const contents = rendition.getContents()[0];
    if (contents) contents.window.getSelection().removeAllRanges();
  }
};
const closeWiki = () => {
  showWiki.value = false;
  clearNativeSelection(); // ✨ 退出 Wiki 时，清除原生的蓝色高亮
};

const closeAnnotationPanel = () => {
  showAnnotationPanel.value = false;
  clearNativeSelection(); // ✨ 退出 批注面板 时，也清除蓝色高亮
  // TODO: 后续可在这里触发后端保存接口
};

const deleteOverlappingAnnotation = () => {
  if (overlappingCfi) {
    rendition.annotations.remove(overlappingCfi, 'highlight');
    delete annotationDataMap[overlappingCfi];
    
    isSelectionOverlapping.value = false;
    overlappingCfi = null;
    activeHighlightCfi.value = null; 
    
    currentNoteText.value = ''; 
    
    showSelectionMenu.value = false; 
    showAnnotationPanel.value = false; 
    clearNativeSelection(); 
  }
};

const syncNote = () => {
  // ✨ 核心机制：只要还没 MARK，只要你敲下第一个字母，系统立刻自动帮你执行 MARK！
  // 这样底层的蓝色高亮会瞬间变成灰色的持久高亮，完美实现“打字即标记”
  if (!isSelectionOverlapping.value) {
    markAnnotation(); 
  }
  
  // 此时绝对已经是已 MARK 状态了，安全地实时同步笔记文本
  if (overlappingCfi && annotationDataMap[overlappingCfi]) {
    annotationDataMap[overlappingCfi].note = currentNoteText.value;
  }
};
const copyText = () => {
  if (currentSelection.value && currentSelection.value.text) {
    navigator.clipboard.writeText(currentSelection.value.text);
    if (!showWiki.value && !showAnnotationPanel.value) {
      showSelectionMenu.value = false;
      clearNativeSelection(); // 复制完，选单和高亮全消失
    }
  }
};

const searchInWiki = () => {
  if (currentSelection.value && currentSelection.value.text) {
    showSelectionMenu.value = false; // 仅仅关闭浮动选项框
    showAnnotationPanel.value = false; 
    summonReference(currentSelection.value.text);
    // 🎯 注意：这里故意不调用 clearNativeSelection()，所以蓝色高亮会完美保留！
  }
};

const switchToAnnotation = () => {
  showSelectionMenu.value = false; // 仅仅关闭浮动选项框
  showWiki.value = false;
  currentNoteText.value = isSelectionOverlapping.value && overlappingCfi ? (annotationDataMap[overlappingCfi]?.note || '') : '';
  showAnnotationPanel.value = true;
  // 🎯 注意：这里也不调用 clearNativeSelection()，保留蓝色高亮
};


const markAnnotation = () => {
  const cfi = currentSelection.value.cfi;
  
  if (!annotationDataMap[cfi]) {
    annotationDataMap[cfi] = {
      text: currentSelection.value.text,
      segments: currentSelection.value.segments, 
      note: currentNoteText.value 
    };
  } else {
    annotationDataMap[cfi].note = currentNoteText.value;
  }

  isSelectionOverlapping.value = true;
  overlappingCfi = cfi;
  activeHighlightCfi.value = cfi;

  rendition.annotations.add(
    'highlight', 
    cfi, 
    {}, 
    (e) => {
      const contents = rendition.getContents()[0];
      const selection = contents ? contents.window.getSelection() : null;
      if (selection && !selection.isCollapsed && selection.toString().trim().length > 0) return;

      clearTimeout(tapActionTimer);
      isSelectionOverlapping.value = true;
      overlappingCfi = cfi;
      activeHighlightCfi.value = cfi;
      currentSelection.value = { 
        text: annotationDataMap[cfi].text, 
        cfi: cfi,
        segments: annotationDataMap[cfi].segments
      };

      currentNoteText.value = annotationDataMap[cfi].note || '';     
      showAnnotationPanel.value = true;
    }, 
    'custom-hl', 
    { "fill": "#808080", "fill-opacity": "0.3", "mix-blend-mode": "multiply" } 
  );
  
  showSelectionMenu.value = false; // 隐藏小浮窗
  clearNativeSelection(); // 🎯 MARK 之后，取消原生的蓝色选区，让底下的灰色专属高亮无缝显现出来！
};

// --- ✨ 3. 升级：标准化的关闭动作 ---

const copyActiveAnnotation = () => {
  const data = annotationDataMap[activeHighlightCfi.value];
  if (data) {
    navigator.clipboard.writeText(data.text);
    // 可选：加个轻微反馈
  }
};

const searchActiveAnnotation = () => {
  const data = annotationDataMap[activeHighlightCfi.value];
  if (data) {
    showAnnotationPanel.value = false; // 关闭批注栏
    summonReference(data.text);        // 弹起维基半屏
  }
};

const deleteAnnotation = () => {
  rendition.annotations.remove(activeHighlightCfi.value, 'highlight');
  delete annotationDataMap[activeHighlightCfi.value]; // 🧹 打扫卫生
  showAnnotationPanel.value = false;
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

// 🚀 极客空降法 (精简版)
const jumpToTargetPage = () => {
  const targetUnit = parseInt(inputPage.value);
  const total = parseInt(totalPages.value);

  if (isNaN(targetUnit) || targetUnit < 0 || targetUnit > total) {
    inputPage.value = currentPage.value;
    return;
  }
  
  if (unitMap.length > 0) {
    const mapItem = unitMap.find(m => targetUnit >= m.start && targetUnit <= m.end);
    if (mapItem) {
      const preciseId = `unit-${targetUnit}`; // 只保留 unit-X 格式
      const progress = targetUnit / total;
      saveProgressToBackend(preciseId, progress); 
      currentPage.value = targetUnit;
      rendition.display(`${mapItem.href}#${preciseId}`).then(() => {
        showBars.value = false;
        isJumpLocked = true;
        setTimeout(() => { isJumpLocked = false; }, 500);
      });
    }
  }
};

const cycleFontSize = async () => {
  const sizes = [80, 100, 120, 140];
  const currentIndex = sizes.indexOf(currentFontSize.value);
  currentFontSize.value = sizes[(currentIndex + 1) % sizes.length];
  if (viewer.value) {  // 1. ✨ 开启蒙版隐身效果，并锁住雷达探测
    viewer.value.style.transition = 'opacity 0.2s';
    viewer.value.style.opacity = '0';
  }
  isJumpLocked = true; 
  rendition.themes.fontSize(`${currentFontSize.value}%`);   // 2. ✨ 更改 Epub 内部字号
  const targetUnit = currentPage.value;  // 3. ✨ 精确打击：利用你的 map 机制，找到当前所在的位置并强制空降
  if (unitMap.length > 0 && targetUnit !== '-') {
    const mapItem = unitMap.find(m => targetUnit >= m.start && targetUnit <= m.end);
    if (mapItem) {
      const preciseId = `unit-${targetUnit}`;
      await rendition.display(`${mapItem.href}#${preciseId}`);
    }
  }
  setTimeout(() => {   // 4. ✨ 等待渲染稳固后，解除蒙版，解锁雷达
    if (viewer.value) viewer.value.style.opacity = '1';
    isJumpLocked = false;
  }, 300);
  fetch(`/api/books/${props.book.id}/prefs`, {  // 5. ✨ 将最新字号保存给后端（路径改为这本特定的书）
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