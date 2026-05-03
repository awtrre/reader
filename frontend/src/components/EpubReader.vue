<template>
  <div class="fixed inset-0 bg-neutral-900 text-neutral-100 flex overflow-hidden z-50 font-sans select-none">
    
    <div class="relative h-full flex-grow border-r border-neutral-800 bg-black flex items-center justify-center overflow-hidden" ref="readerMain">
      <div ref="maskRef" class="mask"></div>
      <div id="viewer" ref="viewer" class="w-full h-full"></div>

      <div 
        v-show="isCurrentBookmarked && !isTurningPage"
        class="absolute top-1 left-1/2 -translate-x-1/2 z-10 pointer-events-none"
      >
        <svg class="w-6 h-8 text-neutral-300 drop-shadow-md" fill="currentColor" viewBox="0 0 24 32" xmlns="http://www.w3.org/2000/svg">
          <path d="M5 0 C3.895 0 3 0.895 3 2 v30 l9-7 l9 7 V2 C21 0.895 20.105 0 19 0 Z" />
        </svg>
      </div>

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

    <div v-show="showBars" class="absolute top-0 left-0 right-0 h-16 bg-neutral-900/95 backdrop-blur-md border-b border-neutral-800 flex justify-between items-center px-6 z-40 transition-transform duration-300 animate-fade-in">
      <button @click="$emit('close')" class="text-neutral-400 hover:text-white text-sm tracking-widest font-mono transition-colors z-10">
        ❮ BACK
      </button>

      <!-- 绝对居中的书签按钮 -->
      <button @click="toggleBookmark" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-neutral-400 hover:text-white transition-colors p-2">
        <!-- 书签已添加：实心白色 -->
        <svg v-if="isCurrentBookmarked" class="w-6 h-6 text-neutral-100" fill="currentColor" viewBox="0 0 24 24">
          <path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/>
        </svg>
        <!-- 书签未添加：空心灰色 -->
        <svg v-else class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M17 3H7c-1.1 0-1.99.9-1.99 2L5 21l7-3 7 3V5c0-1.1-.9-2-2-2zm0 15l-5-2.18L7 18V5h10v13z"/>
        </svg>
      </button>

      <button @click="toggleTTS" class="text-neutral-400 hover:text-white text-sm tracking-widest font-mono flex items-center gap-2 transition-colors z-10">
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

    <div v-show="showTocOverlay" class="fixed inset-0 bg-neutral-900 z-50 flex flex-col animate-fade-in">
      <div class="h-16 border-b border-neutral-800 flex justify-between items-center px-8">
        <button @click="showTocOverlay = false" class="text-neutral-500 hover:text-neutral-200 text-sm tracking-widest transition-colors font-mono">
          ✕ EXIT
        </button>
        <div class="flex gap-8 text-sm font-bold tracking-widest">
          <button @click="switchToTocTab" :class="activeOverlayTab === 'toc' ? 'text-neutral-100 border-b-2 border-neutral-100' : 'text-neutral-600 hover:text-neutral-400'" class="pb-1 transition-all">目录</button>
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
        <li v-for="bookmark in bookmarksList" :key="bookmark.id" 
            @click="jumpToBookmark(bookmark.unit)" 
            class="cursor-pointer border-b border-neutral-800 py-4 px-3 transition-colors hover:bg-neutral-800/50 group flex flex-col">
          
          <!-- 主要显示：书籍文本 (强制严格截断为2行) -->
          <div class="text-neutral-200 text-sm group-hover:text-white transition-colors mb-3"
               style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.25rem; max-height: 2.5rem;">
            {{ bookmark.text }}
          </div>
          
          <!-- 辅助显示：数字与日期 -->
          <div class="flex justify-between items-center text-[10px] text-neutral-600 font-mono">
            <span>{{ bookmark.unit }}</span>
            <span>{{ new Date(bookmark.time).toLocaleDateString() }}</span>
          </div>
        </li>
      </ul>

      <!-- 勾注列表 -->
      <ul v-show="activeOverlayTab === 'annotations'" class="h-full overflow-y-auto scrollbar-hide pr-2">
        <li v-for="anno in annotationsList" :key="anno.id" 
            @click="jumpToAnnotationPage(anno)" 
            class="cursor-pointer border-b border-neutral-800 py-4 px-3 transition-colors hover:bg-neutral-800/50 group flex flex-col">
          
          <div class="border-l-2 border-neutral-600 pl-3 group-hover:border-neutral-400 transition-colors mb-3">
            <!-- 勾画的原文 (强制严格截断为2行) -->
            <div class="text-neutral-200 text-sm group-hover:text-white transition-colors"
                 style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.25rem; max-height: 2.5rem;">
              {{ anno.text }}
            </div>
            <div v-if="anno.note" class="text-neutral-400 text-xs mt-2"
                 style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1rem; max-height: 2rem;">
              {{ anno.note }}
            </div>
          </div>

          <!-- 底部栏：左侧新增页码，右侧日期 -->
          <div class="flex justify-between items-center text-[10px] text-neutral-600 font-mono pl-3">
            <span>{{ getAnnoUnit(anno) }}</span>
            <span>{{ new Date(anno.created_at).toLocaleDateString() }}</span>
          </div>
        </li>
      </ul>

    </div>
    </div>

    <audio ref="ttsPlayer" @ended="handleAudioEnded" @error="handleAudioError" class="hidden"></audio>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick} from 'vue';
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
// 🪄 强制等待真实屏幕绘制的黑魔法 (Vue + Iframe 双重护盾版)
const waitForPaint = async (contents = null) => {
  // 1. 等待 Vue 自身的 DOM 队列彻底清空
  await nextTick(); 
  
  // 2. ⚡ 核心杀手锏：强制浏览器挂起主线程，立刻计算 iframe 的物理排版！
  // 读取 offsetHeight 会打断浏览器的惰性渲染，逼迫它把高亮元素的位置算死
  if (contents && contents.document) {
    void contents.document.documentElement.offsetHeight;
  } else {
    void document.documentElement.offsetHeight;
  }

  // 3. 等待排版结果真正输出到显示器像素上
  return new Promise(resolve => {
    const targetWindow = (contents && contents.window) ? contents.window : window;
    targetWindow.requestAnimationFrame(() => {
      targetWindow.requestAnimationFrame(resolve);
    });
  });
};
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
let hasScrolledToActiveToc = false;
const showTocOverlay = ref(false);
const activeOverlayTab = ref('toc');
const maskRef = ref(null);

// --- 数据与分页状态 ---
const tocList = ref([]);
const currentPage = ref('-');
const totalPages = ref('-');
const inputPage = ref('-');
const visibleUnitRange = ref({ start: -1, end: -1 });
const currentFontSize = ref(100);
const annotationsList = ref([]);
const bookmarksList = ref([]);
let isJumpLocked = false;
let isChangingFont = false;
const isTurningPage = ref(false);
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
  if (!rendition) return;

  // 1. 瞬间拉下黑幕，打断一切
  toggleMask(true, { type: 'local' });

  // 2. 锁住雷达和菜单
  if (!isJumpLocked) {
    isJumpLocked = true;
    selectionOverlayRef.value?.hideMenuOnly(); 
  }
  
  clearTimeout(resizeTimer);
  
  resizeTimer = setTimeout(async () => {
    try {
      await waitForPaint();

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

      // ✨ 核心修复 1：加上 await，强迫主线程等待划词组件算完坐标！
      const contents = rendition.getContents()[0];
      if (contents) {
        await selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(contents);
        // ✨ 核心修复 2：亲眼看着物理屏幕把带颜色的高亮画好
        await waitForPaint(contents); 
      }

      // ✨ 核心修复 3：在黑幕揭开前，提前解锁并强行扫雷！
      // 此时还在黑屏状态，我们让雷达在暗中重新扫描排版，
      // 这会让 visibleUnitRange 立刻更新，书签图标（isCurrentBookmarked）也会在黑暗中点亮。
      isJumpLocked = false;
      handleRelocated(); 
      
      // 等待 Vue 把书签图标的 DOM 状态更新完
      await nextTick(); 

    } catch (e) {
      console.warn("Resize error:", e);
      isJumpLocked = false;
    } finally {
      // 再次死等主窗口重绘
      await waitForPaint();

      // ✨ 最后：缓慢揭开黑幕。此时排版、高亮、书签图标全都是最终形态，绝对不闪！
      toggleMask(false, { type: 'local' });
      
      // 之前这里的 setTimeout 已经被我们拆解并提前到上面去执行了，直接删掉！
    }
  }, 600);
}

onMounted(() => {
  initReader();
  // 监听屏幕旋转或窗口大小调整
  window.addEventListener('resize', handleWindowResize);
});

onUnmounted(() => {
  // 1. 移除全局 Window 监听器
  window.removeEventListener('resize', handleWindowResize); 

  // 2. 🛑 掐断所有异步定时器，防止“幽灵回调”修改已销毁的组件状态
  clearTimeout(resizeTimer);
  clearTimeout(tapActionTimer);
  clearTimeout(saveTimer);

  // 3. 🎵 彻底释放 TTS 音频资源，防止后台继续缓冲或引发错误
  if (ttsPlayer.value) {
    ttsPlayer.value.pause();
    ttsPlayer.value.removeAttribute('src'); // 移除 src 切断音频流
    ttsPlayer.value.load(); // 强迫浏览器释放占用
  }

  // 4. 📚 销毁 Epub 实例并解绑事件
  if (rendition) {
    // 尽量解除挂载在 rendition 上的自定义事件总线
    rendition.off('rendered');
    rendition.off('relocated');
    rendition.off('selected');
    rendition.off('mousedown');
    rendition.off('mouseup');
    rendition.off('touchstart');
    rendition.off('touchend');
  }

  if (epubBook) {
    epubBook.destroy(); // 销毁 iframe 和底层实例 [cite: 2]
  }

  // 5. 🧹 终极防线：手动切断庞大对象的引用链，让浏览器的 GC (垃圾回收) 迅速介入
  epubBook = null;
  rendition = null;
  unitMap = [];
  textNodes = [];
});

const preciseDisplay = async (targetLocation) => {
  // 如果是空降，或者不带锚点的纯章节跳转，直接放行
  if (!targetLocation || typeof targetLocation !== 'string' || !targetLocation.includes('#')) {
    return rendition.display(targetLocation);
  }

  // 👇 如果是跨章跳跃到特定节点（href#unit-X 格式）
  const [baseHref, anchorId] = targetLocation.split('#');
  
  // 1. 先只加载章节的基础路径。这会强迫 epub.js 创建 iframe 并触发所有拦截钩子
  await rendition.display(baseHref);
  
  // 2. 命脉所在：干掉 setTimeout，使用事件驱动的 waitForPaint！
  // 等待浏览器完成当前帧的布局计算（Reflow）和重绘（Repaint），
  // 彻底让树莓派的渲染速度来主导节奏，无论多卡都能保证排版固化。
  await waitForPaint();
  
  // 3. 此时排版已是最终形态，再次执行带节点的精准空降，百发百中！
  return rendition.display(targetLocation);
};

const initReader = async () => {
  toggleMask(true, { type: 'global' });
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
      const savedFont = localStorage.getItem(`offline_font_size_${props.book.id}`);
      if (savedFont) currentFontSize.value = parseInt(savedFont, 10);
    }
    
    try {
      const bookmarkRes = await fetch(`/api/books/${props.book.id}/bookmarks`, {
        headers: {
          'user-token': localStorage.getItem('geek_token') || '',
          'guest-uuid': localStorage.getItem('guest_uuid') || ''
        }
      });
      if (bookmarkRes.ok) {
        const bookmarkData = await bookmarkRes.json();
        if (bookmarkData.bookmarks && Array.isArray(bookmarkData.bookmarks)) {
          bookmarksList.value = bookmarkData.bookmarks;
          localStorage.setItem(`offline_bookmarks_${props.book.id}`, JSON.stringify(bookmarksList.value));
        }
      } else {
        throw new Error('云端接口异常');
      }
    } catch (e) {
      console.warn("书签同步失败，降级使用本地缓存", e);
      const savedBookmarks = localStorage.getItem(`offline_bookmarks_${props.book.id}`);
      if (savedBookmarks) {
        try { bookmarksList.value = JSON.parse(savedBookmarks); } catch (err) {}
      }
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
      // ✨ 注意：这里加上 async，让整个钩子内部变成异步流水线
      return new Promise(async (resolve) => {
        const doc = contents.document;

        // 1. 触发 Vue 子组件渲染高亮（加个 await 防止它内部也有异步逻辑）
        await selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(contents);
        
        // ✨ 2. 核心补丁：死等 Vue 真正把节点塞进 iframe 的身体里！
        await nextTick();

        // 3. 收集图片和字体炸弹 (保留你原本的逻辑)
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

        // 4. 等待所有字体/图片加载完毕
        await Promise.all(pendingTasks);

        // ✨ 5. 终极护盾：在这里直接扣留 Epub.js 的放行条！
        // 等 iframe 的物理帧真正把高亮画出颜色后，才允许 Epub.js 宣布"渲染完成"
        const targetWindow = contents.window;
        targetWindow.requestAnimationFrame(() => {
          targetWindow.requestAnimationFrame(resolve); 
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

    // ✨ 核心修复：完全抄作业！把初次渲染封装成和跳页一样的异步大招
    const performInitJumpAndRender = async () => {
      // 1. 底层引擎加载章节和位置
      await preciseDisplay(targetLocation || undefined);
      
      // ✨ 2. 强行核对并渲染高亮，亲眼看着物理屏幕把带颜色的高亮画好
      const contents = rendition.getContents()[0];
      if (contents) {
        await selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(contents);
        await waitForPaint(contents); 
      }
      
      await waitForPaint();
    };
    
    await performInitJumpAndRender();

    // 4. 缓慢揭开黑幕
    toggleMask(false, { type: 'global' });
    
    isReadyToSave = true;
    
    // ✨ 黑幕揭开瞬间，立刻同步雷达
    handleRelocated();

    // 6. 进度雷达：监听翻页并寻找 unit-X 锚点
    rendition.on('relocated', (location) => {
      if (!location || !isReadyToSave || isJumpLocked) return;
      
      try {
        const contents = rendition.getContents()[0];
        const iframeDoc = contents.document;
        const iframe = iframeDoc.defaultView.frameElement;
        const iframeOffset = iframe.getBoundingClientRect().left; 
        const viewWidth = window.innerWidth;
        
        const targets = Array.from(iframeDoc.querySelectorAll('.sync-anchor'));
        
        // 1. 过滤出所有“尚未超出屏幕右侧”的锚点
        const candidateAnchors = targets.filter(el => {
          const absoluteLeft = el.getBoundingClientRect().left + iframeOffset;
          // 5px 极小右侧容错，保证刚好贴边的字不被错误丢弃
          return absoluteLeft < viewWidth + 5; 
        });

        if (candidateAnchors.length > 0) {
          // 2. 屏幕上（或跨越屏幕）的最后一个段落，必然是候选数组里的最后一个
          const lastAnchor = candidateAnchors[candidateAnchors.length - 1];
          
          // 3. 寻找屏幕内真正“完整出现”的首个锚点
          const visibleOnScreen = candidateAnchors.filter(el => {
            const absoluteLeft = el.getBoundingClientRect().left + iframeOffset;
            // 5px 极小左侧容错，专门拯救 -0.001px 的浏览器浮点数渲染偏差
            return absoluteLeft >= -5; 
          });

          // ✨ 4. 核心防御逻辑：
          // 如果屏幕内确实有新段落，取第一个；
          // 如果当前页被一个“超长段落”占满（完全没有新锚点），就自动 Fallback 到那个正在跨页的段落（lastAnchor）
          const firstAnchor = visibleOnScreen.length > 0 ? visibleOnScreen[0] : lastAnchor;

          const firstUnitMatch = firstAnchor.id.match(/unit-(\d+)/);
          const lastUnitMatch = lastAnchor.id.match(/unit-(\d+)/);

          if (firstUnitMatch && lastUnitMatch) {
            const currentUnit = parseInt(firstUnitMatch[1]);
            const lastUnit = parseInt(lastUnitMatch[1]);

            // 同步单点页码和可见区间
            currentPage.value = currentUnit;
            inputPage.value = currentUnit;
            visibleUnitRange.value = { start: currentUnit, end: lastUnit }; 

            const total = props.book.total_units ? props.book.total_units - 1 : 1;
            saveProgressToBackend(firstAnchor.id, currentUnit / total); 
          }
        }
      } catch (e) {
        console.error("💥 雷达程序崩溃:", e);
      } finally {
        // ✨ 必须在这里加上重置！新页面排版落稳了，把书签放出来
        isTurningPage.value = false;
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
        turnPage('prev'); // 替换 isTurningPage.value = true; rendition.prev();
      } else if (absoluteX > screenWidth * 0.7) {
        turnPage('next'); // 替换 isTurningPage.value = true; rendition.next();
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
    turnPage('prev'); // 替换
  } else if (clickX > width * 0.7) {
    turnPage('next'); // 替换
  } else {
    showBars.value = !showBars.value;
  }
};

const openTocOverlay = async () => {
  hasScrolledToActiveToc = false;
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
  nextTick(() => {
    if (activeOverlayTab.value === 'toc') {
      if (!hasScrolledToActiveToc) {
        const activeEl = document.getElementById('active-toc-item');
        if (activeEl) {
          activeEl.scrollIntoView({ behavior: 'instant', block: 'center' });
          hasScrolledToActiveToc = true; 
        }
      }
    } else {
      const scrollBox = document.querySelector('.overflow-y-auto');
      if (scrollBox) scrollBox.scrollTop = 0;
    }
  });
};

const jumpToCfiAndClose = async (cfiOrHref) => {
  showBars.value = false;
  showTocOverlay.value = false;

  // ✨ 先让主线程有空把面板隐藏掉
  await nextTick(); 

  toggleMask(true, { type: 'global' });
  isJumpLocked = true; 

  await waitForPaint();

  try {
    let target = cfiOrHref;
    let hashId = null;

    if (typeof target === 'string' && target.includes('#')) {
      const [base, hash] = target.split('#');
      hashId = decodeURIComponent(hash);
      target = `${base}#${hashId}`;
    }

    const performJumpAndRender = async () => {
      await rendition.display(target);
      if (hashId) {
        await waitForPaint();
        const tempContents = rendition.getContents()[0];
        if (tempContents) {
          const targetNode = tempContents.document.getElementById(hashId);
          if (targetNode) {
            const preciseCfi = tempContents.cfiFromNode(targetNode);
            await rendition.display(preciseCfi); 
          }
        }
      }
      
      // ✨ 核心补丁：目录跳完之后，强行触发一次高亮渲染，并在黑幕下死等它画完！
      const finalContents = rendition.getContents()[0];
      if (finalContents) {
        await selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(finalContents);
        await waitForPaint(finalContents); // 必须等待 iframe 涂上颜色
      }
    };
      
    await performJumpAndRender();

  } catch (error) {
    console.error("跳转失败:", error);
  } finally {
    // 5. 缓慢揭开黑幕
    toggleMask(false, { type: 'global' });
    isJumpLocked = false; 
    
    if (rendition.getContents().length > 0) {
      handleRelocated(); 
      
      if (currentPage.value !== '-') {
        const preciseId = `unit-${currentPage.value}`;
        const total = props.book.total_units ? props.book.total_units - 1 : 1;
        saveProgressToBackend(preciseId, currentPage.value / total, true); 
      }
    }
  } 
};

const loadAnnotationsTab = async () => {
  // 1. 瞬间切换 UI 并置顶。由于我们在 initReader 已经给 annotationsList.value 赋过初值，
  // 此时面板会瞬间渲染出已有的旧数据，没有任何白屏等待。
  activeOverlayTab.value = 'annotations';
  nextTick(() => {
    const scrollBox = document.querySelector('.overflow-y-auto');
    if (scrollBox) scrollBox.scrollTop = 0;
  });

  // 2. 后台静默发起网络请求，拉取最新批注数据
  try {
    const res = await fetch(`/api/books/${props.book.id}/annotations`, {
      headers: {
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      }
    });
    
    if (res.ok) {
      const resData = await res.json();
      if (resData.annotations && Array.isArray(resData.annotations)) {
        // ✨ 3. 拿到最新数据后，直接覆盖响应式变量。
        // Vue 会自动对比差异（Diff）并更新变动的部分，用户视觉上是无缝的。
        annotationsList.value = resData.annotations.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        // 顺手把最新数据同步给划词组件，防止后续渲染高亮时用错旧数据
        selectionOverlayRef.value?.setRawAnnotations(resData.annotations);
      }
    }
  } catch (e) {
    console.warn("最新勾注数据同步失败，继续使用本地缓存", e);
  }
};

const switchToTocTab = () => {
  activeOverlayTab.value = 'toc';
  
  if (!hasScrolledToActiveToc) {
    nextTick(() => {
      const activeEl = document.getElementById('active-toc-item');
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'instant', block: 'center' });
        hasScrolledToActiveToc = true; 
      }
    });
  }
};
// 从勾注的 segments 数据中提取当前页码 (Unit 数字)
const getAnnoUnit = (anno) => {
  if (!anno.segments) return '';
  try {
    const parsedSegments = typeof anno.segments === 'string' ? JSON.parse(anno.segments) : anno.segments;
    if (Array.isArray(parsedSegments) && parsedSegments.length > 0) {
      const firstSegment = parsedSegments[0];
      if (firstSegment && firstSegment.nodeX) {
        const match = firstSegment.nodeX.match(/unit-(\d+)/);
        return match ? match[1] : '';
      }
    }
  } catch (e) {
    console.warn("解析勾注页码失败", e);
  }
  return '';
};
// 点击一条勾注时触发
const jumpToAnnotationPage = async (anno) => {
  let targetUnit = null;
  if (anno.segments) {
    try {
      const parsedSegments = typeof anno.segments === 'string' ? JSON.parse(anno.segments) : anno.segments;
      if (Array.isArray(parsedSegments) && parsedSegments.length > 0) {
        const firstSegment = parsedSegments[0];
        if (firstSegment && firstSegment.nodeX) {
          const match = firstSegment.nodeX.match(/unit-(\d+)/);
          if (match) targetUnit = match[1];
        }
      }
    } catch (e) {
      console.error("解析勾注数据失败:", e);
    }
  }

  if (targetUnit !== null) {
    inputPage.value = parseInt(targetUnit, 10);
    
    showTocOverlay.value = false; // 1. 瞬间隐藏面板
    await nextTick();             // 2. 释放主线程
    await jumpToTargetPage();     // 3. ✨ 闭环：死等渲染完毕
  } else {
    console.warn("未能提取到页码，跳转失败！当前的数据是:", anno.segments);
  }
};


// 计算当前页是否已经被加为书签，用于点亮顶部栏图标
const isCurrentBookmarked = computed(() => {
  if (visibleUnitRange.value.start === -1) return false;

  return bookmarksList.value.some(b => {
    // 兼容旧数据，强转出纯数字
    const bUnit = parseInt(String(b.unit).split('-')[0], 10);
    // 判断：只要这个书签落在了当前屏幕首尾范围之内，书签就悬浮显示！
    return bUnit >= visibleUnitRange.value.start && bUnit <= visibleUnitRange.value.end;
  });
});

// 切换书签操作：有则删，无则加
const toggleBookmark = () => {
  if (currentPage.value === '-') return;
  
  const existingIndexes = bookmarksList.value.reduce((acc, b, index) => {
    const bUnit = parseInt(String(b.unit).split('-')[0], 10);
    if (bUnit >= visibleUnitRange.value.start && bUnit <= visibleUnitRange.value.end) {
      acc.push(index);
    }
    return acc;
  }, []);

  if (existingIndexes.length > 0) {
    // 1. 删除：逆序遍历删除
    existingIndexes.reverse().forEach(idx => {
      const targetBookmark = bookmarksList.value[idx];
      bookmarksList.value.splice(idx, 1); // 瞬间从界面消失
      
      // ✨ 异步发送删除请求给后端
      fetch(`/api/books/${props.book.id}/bookmarks/${targetBookmark.id}`, {
        method: 'DELETE',
        headers: {
          'user-token': localStorage.getItem('geek_token') || '',
          'guest-uuid': localStorage.getItem('guest_uuid') || ''
        }
      }).catch(e => console.warn("书签云端删除失败", e));
    });
  } else {
    // 2. 添加：抓取文本并生成新书签
    let snippet = '...';
    try {
      const loc = rendition.currentLocation();
      if (loc && loc.start?.cfi && loc.end?.cfi) {
        const startRange = rendition.getRange(loc.start.cfi);
        const endRange = rendition.getRange(loc.end.cfi);
        if (startRange && endRange) {
          const contents = rendition.getContents()[0];
          const fullScreenRange = contents.document.createRange();
          fullScreenRange.setStart(startRange.startContainer, startRange.startOffset);
          fullScreenRange.setEnd(endRange.startContainer, endRange.startOffset);
          const cleanText = fullScreenRange.toString().trim().replace(/\s+/g, ' ');
          if (cleanText) {
            snippet = cleanText.length > 80 ? cleanText.substring(0, 80) + '...' : cleanText;
          }
        }
      }
    } catch(e) {
      console.warn("抓取文字或页面范围失败", e);
    }

    const newBookmark = {
      id: Date.now(), // 毫秒时间戳作为 ID
      unit: currentPage.value,
      time: Date.now(),
      text: snippet
    };
    bookmarksList.value.unshift(newBookmark); // 瞬间点亮书签图标

    // ✨ 异步发送保存请求给后端
    fetch(`/api/books/${props.book.id}/bookmarks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      },
      body: JSON.stringify(newBookmark)
    }).catch(e => console.warn("书签云端保存失败", e));
  }
  
  // 无论增删，兜底更新本地缓存
  localStorage.setItem(`offline_bookmarks_${props.book.id}`, JSON.stringify(bookmarksList.value));
};

// 点击列表跳转并关闭面板
const jumpToBookmark = async (unitRange) => {
  const startUnit = String(unitRange).split('-')[0];
  inputPage.value = parseInt(startUnit, 10);
  
  showTocOverlay.value = false;
  await nextTick();    
  await jumpToTargetPage();
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
      // ✨ 修改点 1：在这里提前给列表赋值，并做好时间排序
      if (data.annotations && Array.isArray(data.annotations)) {
        annotationsList.value = data.annotations.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      } else {
        annotationsList.value = [];
      }

      // 1. 把所有章节的原始批注数据交给子组件缓存起来
      selectionOverlayRef.value?.setRawAnnotations(data.annotations);
      
      // 2. 紧接着渲染当前（空降落地时）章节的批注
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
    if (!contents) return;

    const iframe = contents.document.defaultView.frameElement;
    const iframeOffset = iframe.getBoundingClientRect().left; 
    const targets = Array.from(contents.document.querySelectorAll('.sync-anchor'));
    
    const visibleAnchors = targets.filter(el => {
      const rect = el.getBoundingClientRect();
      const absLeft = rect.left + iframeOffset;
      return absLeft >= -10 && absLeft < window.innerWidth + 10;
    });

    if (visibleAnchors.length > 0) {
      const firstMatch = visibleAnchors[0].id.match(/unit-(\d+)/);
      const lastMatch = visibleAnchors[visibleAnchors.length - 1].id.match(/unit-(\d+)/);

      if (firstMatch && lastMatch) {
        const firstUnit = parseInt(firstMatch[1]);
        const lastUnit = parseInt(lastMatch[1]);

        // ✨ 核心修复：视觉黏性逻辑
        // 拿到当前的页码，判断它是否还在屏幕的“视野范围内”
        let targetUnit = currentPage.value;
        
        // 如果当前还没页码（刚进书），或者当前页码彻底不在屏幕上了（用户真实翻页了）
        // 我们才把页码更新为屏幕上的第一个 unit
        if (targetUnit === '-' || targetUnit < firstUnit || targetUnit > lastUnit) {
          targetUnit = firstUnit;
        }

        // 同步所有状态为最终决定的 targetUnit
        currentPage.value = targetUnit;
        inputPage.value = targetUnit;
        visibleUnitRange.value = { start: firstUnit, end: lastUnit }; 

        // 上报进度时，也精准上报 targetUnit，而不是盲目上报 visibleAnchors[0]
        const total = props.book.total_units ? props.book.total_units - 1 : 1;
        saveProgressToBackend(`unit-${targetUnit}`, targetUnit / total); 
      }
    }
  } catch (e) {
    console.error("Radar Error", e); 
  } 
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

// 🎭 终极黑幕调度器 (默认有动画)
const toggleMask = (visible, options = {}) => {
  const mask = maskRef.value;
  if (!mask) return;

  const type = options.type || 'local';
  const animate = options.animate !== undefined ? options.animate : true; // 默认带动画

  if (type === 'global') {
    mask.style.position = 'fixed';
    mask.style.zIndex = '9999'; 
  } else {
    mask.style.position = 'absolute';
    mask.style.zIndex = '25';   
  }

  if (visible) {
    mask.style.transition = 'none';
    mask.offsetHeight; 
    mask.style.opacity = '1';
    mask.style.pointerEvents = 'auto';
  } else {
    mask.style.transition = animate ? 'opacity 0.2s ease' : 'none';
    mask.offsetHeight;
    mask.style.opacity = '0';
    mask.style.pointerEvents = 'none';
  }
};

const saveProgressToBackend = (cfi, progress, immediate = false) => {
  localStorage.setItem(`offline_font_size_${props.book.id}`, currentFontSize.value);
  
  clearTimeout(saveTimer);

  // 1. 将原有的 fetch 逻辑打包成一个独立动作
  const sendFetch = () => {
    fetch(`/api/books/${props.book.id}/progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      },
      // ✨ 重点在这里：补充 font_size
      body: JSON.stringify({ cfi: cfi, percent: progress, font_size: currentFontSize.value }) 
    })
    .then(res => {
      if (res.ok) localStorage.removeItem(`sync_pending_${props.book.id}`);
    })
    .catch(() => {
      localStorage.setItem(`sync_pending_${props.book.id}`, 'true');
    });
  };

  // 2. 如果开启了强制开关，立刻执行！否则走常规的 2 秒静默倒计时
  if (immediate) {
    sendFetch();
  } else {
    saveTimer = setTimeout(sendFetch, 2000);
  }
};

// 🚀 极客空降法 (精简版)
const jumpToTargetPage = async () => {
  const targetUnit = parseInt(inputPage.value);
  const total = parseInt(totalPages.value);
  
  // 1. 拦截不合法输入
  if (isNaN(targetUnit) || targetUnit < 0 || targetUnit > total) {
    inputPage.value = currentPage.value;
    return;
  }
  
  // 2. 查找映射，找不到直接退出（避免深层嵌套）
  const mapItem = unitMap.find(m => targetUnit >= m.start && targetUnit <= m.end);
  if (!mapItem) return;
  
  const preciseId = `unit-${targetUnit}`; 
  saveProgressToBackend(preciseId, targetUnit / total, true);
  currentPage.value = targetUnit;
  isJumpLocked = true;
  
  // 3. 瞬间拉下物理黑幕
  toggleMask(true, { type: 'global' });
  
  // ✨ 4. 绝对死等：强迫浏览器把黑幕渲染到物理屏幕上
  await waitForPaint();

  // ✨ 5. 去掉原来的 Promise.all 倒计时，改成顺序严格执行
  await preciseDisplay(`${mapItem.href}#${preciseId}`);

  // ✨ 6. 核心补丁：无论是不是跨章跳跃，强行命令组件重新核对并渲染一次高亮！
  const contents = rendition.getContents()[0];
  if (contents) {
    await selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(contents);
    await waitForPaint(contents); // 死等 iframe 内部物理重绘完毕
  }

  showBars.value = false;

  // 7. 再次死等主窗口重绘
  await waitForPaint();

  //8. 缓慢揭开黑幕
  toggleMask(false, { type: 'global' });
  
  isJumpLocked = false;
  handleRelocated();
};

const turnPage = async (direction) => {
  isTurningPage.value = true;
  let isCrossChapter = false;

  // 1. 🔍 预判：基于藏宝图和当前屏幕视野，判断是否即将跨章
  if (unitMap.length > 0 && visibleUnitRange.value.start !== -1) {
    const currentMapItem = unitMap.find(m => visibleUnitRange.value.start >= m.start && visibleUnitRange.value.start <= m.end);
    if (currentMapItem) {
      // 如果下一页，且当前屏幕已经包含了本章最后一个 unit
      if (direction === 'next' && visibleUnitRange.value.end >= currentMapItem.end) {
        isCrossChapter = true;
      } 
      // 如果上一页，且当前屏幕包含了本章第一个 unit
      else if (direction === 'prev' && visibleUnitRange.value.start <= currentMapItem.start) {
        isCrossChapter = true;
      }
    }
  }

  // 2. 🎬 跨章前夕：瞬间拉下局部黑幕并锁死雷达
  if (isCrossChapter) {
    isJumpLocked = true;
    toggleMask(true, { type: 'local', animate: false }); // 纯硬切黑幕，不干扰全局
    await waitForPaint();
  }

  // 3. ⚡ 执行物理翻页
  if (direction === 'next') {
    await rendition.next();
  } else {
    await rendition.prev();
  }

  // 4. 落地核验：如果是跨章，死等高亮画完再揭幕
  if (isCrossChapter) {
    const contents = rendition.getContents()[0];
    if (contents) {
      await selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(contents);
      await waitForPaint(contents); // 核心：死等 iframe 内部把颜色填好
    }
    toggleMask(false, { type: 'local' }); // 缓慢揭开黑幕
    isJumpLocked = false;
    handleRelocated(); // 黑幕揭开瞬间，立刻同步雷达
  }
  
  // 注意：isTurningPage 会在你的 handleRelocated 触发的 'relocated' 事件回调中被安全重置为 false
};

const cycleFontSize = async () => {
  if (isChangingFont) return;
  isChangingFont = true;

  try {
    const sizes = [80, 100, 120, 140];
    const currentIndex = sizes.indexOf(currentFontSize.value);
    currentFontSize.value = sizes[(currentIndex + 1) % sizes.length];

    isJumpLocked = true; 

    // 1. 瞬间拉下局部黑幕 (无动画秒切)
    toggleMask(true, { type: 'local', animate: false });
    await waitForPaint();

    // 2. 注入新字号 (这会导致异步的 CSS 重排)
    rendition.themes.fontSize(`${currentFontSize.value}%`);   
    
    // 3. ✨ 强制同步排版 (Synchronous Reflow)
    // 彻底干掉定时器！强迫浏览器立刻停下所有动作算排版。
    const tempContents = rendition.getContents()[0];
    if (tempContents) {
      void tempContents.document.documentElement.offsetHeight; 
    }

    // 4. 精准恢复当前位置
    const targetUnit = currentPage.value;  
    if (unitMap.length > 0 && targetUnit !== '-') {
      const mapItem = unitMap.find(m => targetUnit >= m.start && targetUnit <= m.end);
      if (mapItem) {
        const preciseId = `unit-${targetUnit}`;
        
        await preciseDisplay(`${mapItem.href}#${preciseId}`);
        
        const finalContents = rendition.getContents()[0];
        if (finalContents) {
          await selectionOverlayRef.value?.renderAnnotationsForCurrentChapter(finalContents);
          await waitForPaint(finalContents); 
        }
      }
    }

    isJumpLocked = false;
    handleRelocated(); 

    // 6. 瞬间揭开局部黑幕 (无动画，纯硬切，完美不闪)
    toggleMask(false, { type: 'local', animate: false });

    // 7. 保存进度
    if (currentPage.value !== '-') {
      const total = props.book.total_units ? props.book.total_units - 1 : 1;
      saveProgressToBackend(`unit-${currentPage.value}`, currentPage.value / total, true);
    }

  } catch (e) {
    console.error("切换字号失败:", e);
    isJumpLocked = false;
    toggleMask(false, { type: 'local', animate: false });
  } finally {
    isChangingFont = false;
  }
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
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.mask {
  position: absolute;
  inset: 0;
  background-color: #000000;
  z-index: 25;
  opacity: 1;
  pointer-events: auto; /* 默认状态下允许点击穿透 */
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