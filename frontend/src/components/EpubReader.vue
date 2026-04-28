<template>
  <div ref="maskRef" class="mask"></div>
  <div class="fixed inset-0 bg-neutral-900 text-neutral-100 flex overflow-hidden z-50 font-sans select-none">
    
    <div class="relative h-full flex-grow border-r border-neutral-800 bg-black flex items-center justify-center overflow-hidden" ref="readerMain">
      
      <div id="viewer" ref="viewer" class="w-full h-full"></div>

      <SelectionOverlay 
        ref="selectionOverlayRef" 
        v-if="rendition" 
        :rendition="rendition" 
        :book_id="props.book.id"
        @cancel-tap="clearTapTimer"
      />

      <div
        v-if="showBars"
        class="absolute inset-0 z-30"
        @click.stop="showBars = false"
        @touchstart.prevent="showBars = false"
      ></div>
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

    <div v-if="showTocOverlay" class="fixed inset-0 bg-neutral-900 z-50 flex flex-col animate-fade-in">
      <div class="h-16 border-b border-neutral-800 flex justify-between items-center px-8">
        <button @click="showTocOverlay = false" class="text-neutral-500 hover:text-neutral-200 text-sm tracking-widest transition-colors font-mono">
          ✕ EXIT
        </button>
        <div class="flex gap-8 text-sm font-bold tracking-widest">
          <button @click="activeOverlayTab = 'toc'" :class="activeOverlayTab === 'toc' ? 'text-neutral-100 border-b-2 border-neutral-100' : 'text-neutral-600 hover:text-neutral-400'" class="pb-1 transition-all">目录</button>
          <button @click="activeOverlayTab = 'bookmarks'" :class="activeOverlayTab === 'bookmarks' ? 'text-neutral-100 border-b-2 border-neutral-100' : 'text-neutral-600 hover:text-neutral-400'" class="pb-1 transition-all">书签</button>
          <button @click="loadAnnotationsTab" :class="activeOverlayTab === 'annotations' ? 'text-neutral-100 border-b-2 border-neutral-100' : 'text-neutral-600 hover:text-neutral-400'" class="pb-1 transition-all">勾注</button>
        </div>
        <div class="w-16"></div> 
      </div>
      
    <div class="flex-1 overflow-hidden p-8 max-w-3xl mx-auto w-full">
      
      <ul v-show="activeOverlayTab === 'toc'" class="h-full overflow-y-auto scrollbar-hide pr-2">
        <li v-for="item in tocList" :key="item.id" 
            :id="item.isActive ? 'active-toc-item' : ''"
            @click="jumpToCfiAndClose(item.href)" 
            class="cursor-pointer border-b border-neutral-800 transition-colors hover:bg-neutral-800/50 py-4 px-3"
            :class="item.isActive ? 'text-neutral-100 font-bold' : 'text-neutral-400 hover:text-neutral-100'">
          {{ item.label }}
        </li>
      </ul>

      <ul v-show="activeOverlayTab === 'bookmarks'" class="h-full overflow-y-auto scrollbar-hide pr-2">
        <div class="text-center text-neutral-600 mt-20 font-mono text-sm">
          No data recorded yet.
        </div>
      </ul>

      <ul v-show="activeOverlayTab === 'annotations'" class="h-full overflow-y-auto scrollbar-hide pr-2">
        <li v-for="anno in annotationsList" :key="anno.id" 
            @click="jumpToAnnotationPage(anno)" 
            class="cursor-pointer border-b border-neutral-800 py-4 px-3 transition-colors hover:bg-neutral-800/50 group">
          
          <div class="border-l-2 border-neutral-600 pl-3 group-hover:border-neutral-400 transition-colors">
            
            <div class="text-neutral-200 text-sm line-clamp-2 group-hover:text-white transition-colors">
              {{ anno.text }}
            </div>
            
            <div v-if="anno.note" class="text-neutral-400 text-xs line-clamp-2 mt-2">
              {{ anno.note }}
            </div>
            
          </div>

          <div class="text-[10px] text-neutral-600 mt-2 text-right font-mono">
            {{ new Date(anno.created_at).toLocaleDateString() }}
          </div>
          
        </li>
      </ul>

    </div>
    </div>

    <audio ref="ttsPlayer" @ended="handleAudioEnded" @error="handleAudioError" class="hidden"></audio>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import ePub from 'epubjs';
import SelectionOverlay from './SelectionOverlay.vue';
const selectionOverlayRef = ref(null);
const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent) || 
                 (navigator.maxTouchPoints > 0 && 'ontouchstart' in window);
const props = defineProps({
  book: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close']);
const clearTapTimer = () => {
  clearTimeout(tapActionTimer); // 兼顾电脑端（拆已有的炸弹）
  tapLock = true;               // 兼顾手机端（给接下来冒泡上来的事件上锁）
  
  // 400ms 后自动解锁，期间所有试图翻页或呼出上下栏的操作全部作废
  setTimeout(() => { tapLock = false; }, 400); 
};

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
const showTocOverlay = ref(false);
const activeOverlayTab = ref('toc');
const maskRef = ref(null);

// --- 数据与分页状态 ---
const tocList = ref([]);
const currentPage = ref('-');
const totalPages = ref('-');
const inputPage = ref('-');
const currentFontSize = ref(100);
const annotationsList = ref([]);
let isJumpLocked = false;
let resizeTimer = null;

// --- TTS 引擎状态 ---
const isReading = ref(false);
let currentSpineIndex = 0;
let textNodes = [];
let currentNodeIndex = 0;

// --- ✨选词与批注专属状态 ---
let isPointerDown = false; 
let uiWasOpen = false;   
let tapActionTimer = null;
let lastClickTime = 0;
let tapLock = false;

// ==========================================
// 主题注入：适配 Paginated 模式的流式布局
// ==========================================
const applyTheme = () => {
  if (!rendition) return;
  const themeBase = {
    // 注意：这里去掉了 user-select 属性！
    'body, p, span, a, b, i, em, strong, div, blockquote, ul, ol, li, section, article': {
      'background-color': '#000000 !important',
      'color': '#d4d4d4 !important',
      'font-family': 'system-ui, -apple-system, sans-serif !important', 
      '-webkit-touch-callout': 'none !important', // 禁止手机长按弹出图片保存等原生菜单
    },  
    'h1, h2, h3, h4, h5, h6': {
      'background-color': '#000000 !important',
      'color': '#ffffff !important',
      'line-height': '1.4 !important',
      'margin-top': '1.5em !important',
      'margin-bottom': '1em !important',
    },
    'p': {
      'line-height': '1.6 !important',
      'margin-top': '0 !important', 
      'margin-bottom': '1em !important',
    },
    'img, svg, video': {
      'display': 'inline-block !important', 
      'margin': '1em 0 !important', 
      'max-width': '100% !important',
      'max-height': '80vh !important' 
    },
    '::selection': {
      'background': '#262626 !important', 
      'color': '#ffffff !important' 
    },
    '.custom-hl': {
      'pointer-events': 'all !important', 
      'user-select': 'none !important', 
      '-webkit-user-select': 'none !important'
    }
  };
  if (!isMobile) {
    themeBase['body'] = {
      'user-select': 'none !important',
      '-webkit-user-select': 'none !important',
    };
  }
  // 第三步：把组装好的字典，正式注入给 Epub 阅读器
  rendition.themes.default(themeBase);
};
// ==========================================
// 1. 生命周期与初始化 (重构极简版)
// ==========================================
// === 新增：长宽比排版计算器 ===
const handleWindowResize = () => {
  if (!rendition || !maskRef.value) return;

  // 1. 瞬间黑屏：打断过渡，强刷重排，拉下遮罩，开启物理防误触
  const mask = maskRef.value;
  mask.style.transition = 'none';
  mask.offsetHeight; // 🪄 强刷重排黑魔法
  mask.style.opacity = '1';
  mask.style.pointerEvents = 'auto';

  // 2. 锁住雷达和菜单
  if (!isJumpLocked) {
    isJumpLocked = true;
    selectionOverlayRef.value?.hideMenuOnly(); 
  }
  
  clearTimeout(resizeTimer);
  
  // 3. 防抖执行重排与空降
  resizeTimer = setTimeout(async () => {
    try {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const targetSpread = (w >= 768 && (w / h) >= 1.25) ? 'auto' : 'none';
      if (rendition.settings.spread !== targetSpread) rendition.spread(targetSpread);

      rendition.resize();

      if (unitMap.length > 0 && currentPage.value !== '-') {
        const targetUnit = parseInt(currentPage.value);
        const mapItem = unitMap.find(m => targetUnit >= m.start && targetUnit <= m.end);
        await rendition.display(mapItem ? `${mapItem.href}#unit-${targetUnit}` : undefined);
      } else {
        await rendition.display(); 
      }
    } catch (e) {
      console.warn("Resize error:", e);
    } finally {
      // 4. 揭开遮罩：等下一帧 -> 等100ms绘制 -> 恢复动画 -> 揭开黑幕 -> 解锁雷达
      requestAnimationFrame(() => {
        setTimeout(() => {
          mask.style.transition = 'opacity 0.3s ease';
          mask.style.opacity = '0';
          mask.style.pointerEvents = 'none';
          
          setTimeout(() => { isJumpLocked = false; }, 300);
        }, 100); 
      });
    }
  }, 600); 
};
onMounted(() => {
  initReader();
  // 监听屏幕旋转或窗口大小调整
  window.addEventListener('resize', handleWindowResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize); // 打扫战场，移除监听
  if (epubBook) {
    epubBook.destroy(); // 销毁实例，释放内存 [cite: 2]
  }
});

// ✨ 核心修复：带 CSS 渲染缓冲的安全跳转包装器
const preciseDisplay = async (targetLocation) => {
  // 如果是空降，或者不带锚点的纯章节跳转，直接放行
  if (!targetLocation || typeof targetLocation !== 'string' || !targetLocation.includes('#')) {
    return rendition.display(targetLocation);
  }

  // 👇 如果是跨章跳跃到特定节点（href#unit-X 格式）
  const [baseHref, anchorId] = targetLocation.split('#');
  
  // 1. 先只加载章节的基础路径。这会强迫 epub.js 创建 iframe 并注入 applyTheme 的样式
  await rendition.display(baseHref);
  
  // 2. 命脉所在：强制等待 50 毫秒！
  // 给浏览器渲染引擎留出一丁点时间，让它把你的 line-height 和 margin 彻底应用并固化排版
  await new Promise(resolve => setTimeout(resolve, 50));
  
  // 3. 此时排版已是最终形态，再次执行带节点的精准空降，百发百中！
  return rendition.display(targetLocation);
};

const initReader = async () => {
  try {
    // 1. 实例化书籍
    epubBook = ePub(`/api/static/books/${props.book.id}/`); 

    // 2. 进度拉取逻辑
    let savedCfi = null;
    let isReadyToSave = false;
    const progressCacheKey = `offline_progress_${props.book.id}`;
    
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
        if (data.font_size) currentFontSize.value = data.font_size;
      }
    } catch (e) {
      // 联网失败则读取本地缓存 [cite: 5]
      savedCfi = localStorage.getItem(progressCacheKey);
    }

    // 拉取 unit_map.json (用于 unit-X 坐标的精准转换)
    try {
      const mapRes = await fetch(`/api/static/books/${props.book.id}/unit_map.json`);
      if (mapRes.ok) unitMap = await mapRes.json();
    } catch (e) { 
      console.warn("⚠️ 未找到 unit_map.json"); 
    }

    // 3. 阅读器渲染配置 [cite: 2]
    const w = window.innerWidth;
    const h = window.innerHeight;
    const initialSpread = (w >= 768 && (w / h) > 1.1) ? 'auto' : 'none';

    rendition = epubBook.renderTo(viewer.value, {
      width: '100%', 
      height: '100%', 
      flow: 'paginated', 
      manager: 'default',
      spread: initialSpread, 
      allowScriptedContent: true
    });

    applyTheme(); // 应用黑白灰主题
    rendition.themes.fontSize(`${currentFontSize.value}%`);

    rendition.hooks.content.register((contents) => {
      return new Promise((resolve) => {
        const doc = contents.document;

        // 1. 提前把高亮批注画上去
        selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(contents);

        // 2. 收集会导致排版变形的“延时炸弹”（字体和图片）
        const pendingTasks = [];
        if (doc.fonts && doc.fonts.ready) {
          pendingTasks.push(doc.fonts.ready);
        }
        const images = Array.from(doc.querySelectorAll('img'));
        images.forEach(img => {
          if (!img.complete) {
            pendingTasks.push(new Promise((imgResolve) => {
              img.onload = imgResolve;
              img.onerror = imgResolve;
            }));
          }
        });

        // 3. 所有排版炸弹排除，版面彻底固定，放行 Epub 引擎去计算最终坐标！
        Promise.all(pendingTasks).then(() => {
          resolve();
        });
      });
    });

    // 4. Iframe 内部事件拦截：交给子组件 SelectionOverlay 处理 [cite: 2]
    rendition.on('rendered', (e, iframe) => {
      const doc = iframe.document;
      // ✨ 新增防线：彻底禁用浏览器默认的拖拽行为（防止长按文字后被当成文件/文本拖走）
      doc.addEventListener('dragstart', (event) => {
        event.preventDefault();
      });
      // 这个可以保留，未来可能有用
      doc.addEventListener('selectionchange', () => {
        const selection = iframe.window.getSelection();
        if (!selection || selection.isCollapsed || selection.toString().trim() === '') {
          // selectionOverlayRef.value?.hideMenuOnly();
        }
      });

      // 📱 手机端专属：依靠系统原生长按划词，并延迟 150ms 抓取选区
      if (isMobile) {
        const finalizeSelection = () => {
          isPointerDown = false;
          // 给 iOS 系统的原生自动扩选留出 150ms 的时间
          setTimeout(() => {
            const contents = rendition.getContents()[0];
            if (!contents) return;

            const selection = contents.window.getSelection();
            
            // 判读此时此刻，屏幕上是否有完整、确定的原生蓝色选区？
            if (selection && !selection.isCollapsed && selection.toString().trim() !== '') {
              const range = selection.getRangeAt(0);
              const text = selection.toString().trim();
              
              try {
                // 主动出击：根据目前最终的 DOM 选区，生成 CFI 坐标
                const finalCfi = contents.cfiFromRange(range);
                selectionOverlayRef.value?.processSelection(finalCfi, text, range, contents, false);
              } catch (err) {
                console.warn("最新选区获取失败，降级使用缓存数据");
                selectionOverlayRef.value?.showPendingMenu();
              }
            } else {
              // 如果没选区，安全释放可能挂起的菜单
              selectionOverlayRef.value?.showPendingMenu();
            }
          }, 150); 
        };

        // 只有手机端才监听这两个抬手事件
        doc.addEventListener('touchend', finalizeSelection);
        doc.addEventListener('mouseup', finalizeSelection); 
      }
    });

    // 5. 计算初始空降位置
    let targetLocation = savedCfi;
    let initialPageNumber = 0;

    // 核心跳转逻辑：如果是 unit-X 格式，根据 map 映射到具体文件锚点
    if (savedCfi && savedCfi.startsWith('unit-') && unitMap.length > 0) {
      const targetUnitId = parseInt(savedCfi.split('-')[1], 10);
      initialPageNumber = targetUnitId; 
      const mapItem = unitMap.find(m => targetUnitId >= m.start && targetUnitId <= m.end);
      if (mapItem) targetLocation = `${mapItem.href}#${savedCfi}`;
    }

    // 同步 UI 状态
    currentPage.value = initialPageNumber;
    inputPage.value = initialPageNumber;
    totalPages.value = props.book.total_units ? props.book.total_units - 1 : '-';

    await loadSavedAnnotations(props.book.id, rendition); // 先拿批注数据
    await preciseDisplay(targetLocation || undefined);    // 使用安全空降！
    
    // ✨ 3. 此时 DOM 已经带着高亮加载完毕，揭开帷幕！
    requestAnimationFrame(() => {
      if (viewer.value) viewer.value.classList.add('animate-fade-in');
    });
    
    // 4. 延迟 500ms 激活雷达，防止初始化时的虚假跳转触发重复保存
    setTimeout(() => { isReadyToSave = true; }, 500);

    // 6. 进度雷达：监听翻页并寻找 unit-X 锚点 [cite: 2]
    rendition.on('relocated', (location) => {
      if (!location || !isReadyToSave || isJumpLocked) return;
      
      try {
        const contents = rendition.getContents()[0];
        const iframeDoc = contents.document;
        const iframe = iframeDoc.defaultView.frameElement;
        const iframeOffset = iframe.getBoundingClientRect().left; 
        const viewWidth = window.innerWidth;
        
        const targets = Array.from(iframeDoc.querySelectorAll('.sync-anchor'));
        let foundElement = targets.find(el => {
          const rect = el.getBoundingClientRect();
          const absoluteLeft = rect.left + iframeOffset;
          return absoluteLeft >= -10 && absoluteLeft < viewWidth;
        });

        if (foundElement) {
          const preciseId = foundElement.id; 
          const unitMatch = preciseId.match(/unit-(\d+)/);
          const total = props.book.total_units ? props.book.total_units - 1 : 1;

          if (unitMatch) {
            const currentUnit = parseInt(unitMatch[1]);
            currentPage.value = currentUnit;
            inputPage.value = currentUnit;
            saveProgressToBackend(preciseId, currentUnit / total); 
          }
        }
      } catch (e) {
        console.error("💥 雷达程序崩溃:", e);
      }
    });

    // 7. 绑定划词事件
    rendition.on('selected', (cfiRange, contents) => {
      const text = rendition.getRange(cfiRange).toString().trim();
      if (!text) return;
      const range = contents.window.getSelection().getRangeAt(0);
      // 调用解耦后的子组件进行坐标计算和菜单显示
      selectionOverlayRef.value?.processSelection(cfiRange, text, range, contents, true);
    });

    // 8. 绑定点击交互
    setupIframeClick();

  } catch (err) {
    console.error("💥 阅读器初始化失败:", err);
  }
};
// ==========================================
// 2. 交互与布局控制 (极致简化版)
// ==========================================
// iframe 内部点击监听 (全局护盾稳定版)
const setupIframeClick = () => {
  let startX = 0;
  let startY = 0;

  const recordStart = (e) => {
    isPointerDown = true;
    uiWasOpen = showBars.value || showTocOverlay.value || selectionOverlayRef.value?.isAnyUIOpen();
    selectionOverlayRef.value?.hideMenuOnly(); 

    const event = e.changedTouches ? e.changedTouches[0] : e;
    startX = event.clientX;
    startY = event.clientY;

    // 💻 电脑端专属：委托子组件处理长按接管
    if (!isMobile && !uiWasOpen) {
      selectionOverlayRef.value?.processPointerDown(e, startX, startY);
    }
  };

  const handlePointerUp = (e) => {
    isPointerDown = false; 

    // 💻 电脑端专属：询问是否长按
    if (!isMobile) {
      const isLongPress = selectionOverlayRef.value?.processPointerUp();
      if (isLongPress) return;
    }

    // 🛡️ 防线1：高亮绝对防御锁 (防止点开笔记时触发翻页)
    const isLongPress = selectionOverlayRef.value?.processPointerUp();
    if (tapLock) return;

    // 🛡️ 防线2：幽灵点击防抖
    const now = Date.now();
    if (now - lastClickTime < 300) return; 
    lastClickTime = now;

    const event = e.changedTouches ? e.changedTouches[0] : e;
    const endX = event.clientX;
    const endY = event.clientY;
    const deltaX = Math.abs(endX - startX);
    const deltaY = Math.abs(endY - startY);

    // 🛡️ 防线3：退出 UI 拦截
    if (uiWasOpen) {
      showBars.value = false;
      showTocOverlay.value = false;
      const contents = rendition.getContents()[0];
      selectionOverlayRef.value?.clearNativeSelection();
      return; 
    }

    // 🛡️ 防线4：滑动防误触
    if (deltaX > 10 || deltaY > 10) return;

    // 🛡️ 防线5：原生选区拦截
    const contents = rendition.getContents()[0];
    const selection = contents ? contents.window.getSelection() : null;
    if (selection && !selection.isCollapsed && selection.toString().trim().length > 0) return;

    // 终点：执行翻页
    clearTimeout(tapActionTimer);
    tapActionTimer = setTimeout(() => {
      // 1. 获取硬件级别的物理屏幕 X 坐标 (无视任何网页排版和滚动)
      const physicalX = event.screenX; 
      
      // 2. 获取浏览器窗口在屏幕上的左边缘绝对位置 (兼顾电脑端非全屏的窗口模式)
      const browserX = window.screenX || window.screenLeft || 0; 
      
      // 3. 算出手指在当前浏览器窗口内的【绝对横坐标】
      const absoluteX = physicalX - browserX; 
      
      // 4. 获取窗口总宽度
      const screenWidth = window.innerWidth;
      
      // 5. 按照绝对的三等分区域进行判断，彻底打通任督二脉！
      if (absoluteX < screenWidth * 0.3) {
        rendition.prev();
      } else if (absoluteX > screenWidth * 0.7) {
        rendition.next();
      } else {
        showBars.value = !showBars.value; 
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
  const rect = readerMain.value.getBoundingClientRect();
  const clickX = event.clientX - rect.left;
  const width = rect.width;
  if (showTocOverlay.value || selectionOverlayRef.value?.isAnyUIOpen()) return;
  if (clickX < width * 0.3) {
    rendition.prev();
  } else if (clickX > width * 0.7) {
    rendition.next();
  } else {
    showBars.value = !showBars.value;
  }
};

const openTocOverlay = async () => {
  showBars.value = false;
  showTocOverlay.value = true;
  if (activeOverlayTab.value === 'annotations') {
    loadAnnotationsTab();
  }

  const nav = await epubBook.loaded.navigation;
  const location = rendition.currentLocation();
  const currentEndCfi = location?.end?.cfi || location?.start?.cfi;
  const currentEndHref = location?.end?.href || location?.start?.href;
  const currentCfi = location?.start?.cfi;
  const currentHref = location?.start?.href;
  const cfiParser = new ePub.CFI();
  const contents = rendition.getContents()[0];

  const flattenToc = (items, level = 0) => {
    return items.reduce((acc, item) => {
      const indent = level > 0 ? '　'.repeat(level) : '';
      acc.push({
        ...item,
        label: indent + item.label,
        isActive: false // 预设未激活
      });
      if (item.subitems && item.subitems.length > 0) {
        acc.push(...flattenToc(item.subitems, level + 1));
      }
      return acc;
    }, []);
  };

  let flatList = flattenToc(nav.toc);

 // 1. 替换外层的 href 验证
  if (currentEndHref) {
    let activeIndex = -1;
    // 2. 替换 spine 的获取
    const currentSpineItem = epubBook.spine.get(currentEndHref);
    const currentIndex = currentSpineItem ? currentSpineItem.index : -1;

    if (currentIndex !== -1) {
      for (let i = 0; i < flatList.length; i++) {
        const item = flatList[i];
        const tocSpineItem = epubBook.spine.get(item.href);

        if (tocSpineItem) {
          if (tocSpineItem.index < currentIndex) {
            activeIndex = i;
          } else if (tocSpineItem.index === currentIndex) {
            let itemCfi = null;
            const hashIndex = item.href.indexOf('#');

            if (hashIndex !== -1 && contents) {
              const hashId = item.href.substring(hashIndex + 1);
              const targetNode = contents.document.getElementById(hashId);
              if (targetNode) itemCfi = contents.cfiFromNode(targetNode);
            }

            // 3. 替换精准坐标的比对：用屏幕底部的 endCfi 去比大小
            if (itemCfi && currentEndCfi) {
              if (cfiParser.compare(currentEndCfi, itemCfi) >= 0) activeIndex = i;
            } else {
              activeIndex = i;
            }
          } else {
            break; 
          }
        }
      }
    }

    if (activeIndex !== -1) {
      flatList[activeIndex].isActive = true;
    }
  }

  tocList.value = flatList;

  // ✨ 利用 nextTick 等待 DOM 渲染出高亮标记后，执行瞬间滚动
  // ✨ 利用 nextTick 等待 DOM 渲染后，执行位置归位
  import('vue').then(({ nextTick }) => {
    nextTick(() => {
      if (activeOverlayTab.value === 'toc') {
        // 如果是目录页，去寻找高亮的章节并滚动到中间
        const activeEl = document.getElementById('active-toc-item');
        if (activeEl) {
          activeEl.scrollIntoView({ behavior: 'instant', block: 'center' });
        }
      } else {
        // ✨ 核心修复：如果是勾注或书签页，强制把共用的滚动容器拉回最顶部！
        const scrollBox = document.querySelector('.overflow-y-auto');
        if (scrollBox) scrollBox.scrollTop = 0;
      }
    });
  });
};

const jumpToCfiAndClose = async (cfiOrHref) => {
  // 1. 关闭所有 UI 面板
  showBars.value = false;
  showTocOverlay.value = false;

  // 2. 借用黑幕逻辑
  const mask = maskRef.value;
  if (mask) {
    mask.style.transition = 'none';
    mask.offsetHeight; 
    mask.style.opacity = '1';
    mask.style.pointerEvents = 'auto';
  }
  isJumpLocked = true; // 🔒 锁住滚动雷达

  try {
    let target = cfiOrHref;
    let hashId = null;

    if (typeof target === 'string' && target.includes('#')) {
      const [base, hash] = target.split('#');
      hashId = decodeURIComponent(hash);
      target = `${base}#${hashId}`;
    }

    await rendition.display(target);

    if (hashId) {
      await new Promise(resolve => setTimeout(resolve, 50));
      const contents = rendition.getContents()[0];
      if (contents) {
        const targetNode = contents.document.getElementById(hashId);
        if (targetNode) {
          const preciseCfi = contents.cfiFromNode(targetNode);
          await rendition.display(preciseCfi); 
        }
      }
    }
  } catch (error) {
    console.error("跳转失败:", error);
  } finally {
    // 3. 揭开黑幕
    requestAnimationFrame(() => {
      setTimeout(() => {
        if (mask) {
          mask.style.transition = 'opacity 0.15s ease';
          mask.style.opacity = '0';
          mask.style.pointerEvents = 'none';
        }
        
        // 动画结束（150ms）后立马解锁进度雷达
        setTimeout(() => { 
          isJumpLocked = false; // 🔓 1. 解除雷达锁
          
          // ✨ 核心修复：锁解除后，DOM 已经彻底稳定。
          // 我们主动呼叫预置的雷达函数，扫描屏幕上的 unit-X 并保存进度！
          if (rendition.getContents().length > 0) {
            handleRelocated(); 
          }
          
        }, 150);
      }, 30); 
    });
  }
};

const loadAnnotationsTab = async () => {
  activeOverlayTab.value = 'annotations';
  import('vue').then(({ nextTick }) => {
    nextTick(() => {
      const scrollBox = document.querySelector('.overflow-y-auto');
      if (scrollBox) scrollBox.scrollTop = 0;
    });
  });
  try {
    // 假设你的后端按这个规范返回该书的所有勾画和批注
    const res = await fetch(`/api/books/${props.book.id}/annotations`, {
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      }
    });
    
    if (res.ok) {
      const resData = await res.json();
      if (resData.annotations && Array.isArray(resData.annotations)) {
        annotationsList.value = resData.annotations.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      } else {
        annotationsList.value = [];
      }
    }
  } catch (e) {
    console.warn("勾注数据拉取失败，尝试读取本地缓存", e);
    // 可选：如果断网，可以在这里降级读取 localStorage 的数据
  }
};

// 点击一条勾注时触发
const jumpToAnnotationPage = (anno) => {
  let targetUnit = null;

  // 1. 强力解包：对准后端的 nodeX 字段提取
  if (anno.segments) {
    try {
      const parsedSegments = typeof anno.segments === 'string' ? JSON.parse(anno.segments) : anno.segments;
      
      // 检查数组并且拿到第一个选中片段
      if (Array.isArray(parsedSegments) && parsedSegments.length > 0) {
        const firstSegment = parsedSegments[0];
        
        // 关键修复：你的后端定义的键名是 nodeX，值类似 "unit-123"
        if (firstSegment && firstSegment.nodeX) {
          const match = firstSegment.nodeX.match(/unit-(\d+)/);
          if (match) {
            targetUnit = match[1];
          }
        }
      }
    } catch (e) {
      console.error("解析勾注数据失败:", e);
    }
  }

  // 2. 核心闭环：走极客空降法
  if (targetUnit !== null) {
    inputPage.value = parseInt(targetUnit, 10);
    jumpToTargetPage(); 
    showTocOverlay.value = false;
  } else {
    // 如果点不动，能在控制台清晰看到到底传来了什么畸形数据
    console.warn("未能提取到页码，跳转失败！当前的数据是:", anno.segments);
  }
};
// ==========================================
// 3. 选词高亮与维基反代加载
// ==========================================
const loadSavedAnnotations = async (bookId, rendition) => {
  try {
    const res = await fetch(`/api/books/${bookId}/annotations`, {
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      }
    });
    const data = await res.json();
    if (data.status === 'success') {
      // ✨ 1. 把所有章节的原始批注数据交给子组件缓存起来
      selectionOverlayRef.value?.setRawAnnotations(data.annotations);
      
      // ✨ 2. 紧接着渲染当前（空降落地时）章节的批注
      const contents = rendition.getContents()[0];
      if (contents) {
        selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(contents);
      }
    }
  } catch (e) {
    console.error("拉取批注失败", e);
  }
};

const handleRelocated = (location) => {
  try {
    const contents = rendition.getContents()[0];
    if (!contents) return; // ✨ 加一行防崩溃检查

    const iframe = contents.document.defaultView.frameElement;
    const iframeOffset = iframe.getBoundingClientRect().left; 
    const targets = Array.from(contents.document.querySelectorAll('.sync-anchor'));
    
    let found = targets.find(el => {
      const rect = el.getBoundingClientRect();
      const absLeft = rect.left + iframeOffset;
      return absLeft >= -10 && absLeft < window.innerWidth;
    });

    if (found) {
      const unitMatch = found.id.match(/unit-(\d+)/);
      if (unitMatch) {
        const currentUnit = parseInt(unitMatch[1]);
        currentPage.value = currentUnit;
        inputPage.value = currentUnit;
        saveProgressToBackend(found.id, currentUnit / (props.book.total_units ? props.book.total_units - 1 : 1));
      }
    }
  } catch (e) { console.error("Radar Error", e); }
};

const handleSelection = (cfiRange, contents) => {
  if (showBars.value) {
    contents.window.getSelection().removeAllRanges();
    return;
  }
  const text = rendition.getRange(cfiRange).toString().trim();
  if (!text) return;
  const range = contents.window.getSelection().getRangeAt(0);
  // ✨ 转发给子组件处理
  selectionOverlayRef.value?.processSelection(cfiRange, text, range, contents, isPointerDown);
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
      isJumpLocked = true;
      if (viewer.value) viewer.value.style.opacity = '0'; // 隐身，掩盖二次刷新的动作

      preciseDisplay(`${mapItem.href}#${preciseId}`).then(() => {
        showBars.value = false;
        if (viewer.value) viewer.value.style.opacity = '1'; // 现身
        setTimeout(() => { isJumpLocked = false; }, 300);
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
      await preciseDisplay(`${mapItem.href}#${preciseId}`);
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

.mask {
  position: fixed;
  inset: 0;
  background-color: #000000;
  z-index: 9999;
  opacity: 0;
  pointer-events: none; /* 默认状态下允许点击穿透 */
  transition: opacity 0.3s ease; /* 默认带有淡出动画 */
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