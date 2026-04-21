<template>
  <Teleport to="body">
    <div 
      v-if="isGlobalShieldActive" 
      class="fixed inset-0 z-[99999] bg-transparent" 
      style="touch-action: none;"
      @click.stop.prevent
      @touchstart.stop.prevent
      @touchend.stop.prevent
    ></div>
  </Teleport>
  <div
    v-if="showSelectionMenu"
    class="absolute z-50 bg-neutral-900 border border-neutral-800 shadow-2xl flex items-center font-mono text-xs tracking-widest animate-fade-in"
    :style="{ 
      top: selectionMenuPos.y + 'px', 
      left: selectionMenuPos.x + 'px', 
      transform: selectionMenuPos.isFlipped ? 'translate(-50%, 0)' : 'translate(-50%, -100%)', 
      marginTop: selectionMenuPos.isFlipped ? '12px' : '-12px' 
    }"
  >
    <button @click="copyText" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">COPY</button>
    <div class="w-px h-4 bg-neutral-800"></div>
    <button @click="searchInWiki" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">SEARCH</button>
    <div class="w-px h-4 bg-neutral-800"></div>
    <button v-if="!isSelectionOverlapping" @click="markAnnotation" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">MARK</button>
    <button v-else @click="deleteOverlappingAnnotation" class="px-5 py-3 text-neutral-400 hover:text-white transition-colors">DELETE</button>

    <template v-if="!selectionMenuPos.isFlipped">
      <div class="absolute bottom-0 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-transparent border-t-neutral-900" :style="{ left: `calc(50% + ${selectionMenuPos.triangleOffset}px)` }"></div>
      <div class="absolute bottom-[-1px] transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-[7px] border-r-[7px] border-t-[7px] border-transparent border-t-neutral-800 -z-10" :style="{ left: `calc(50% + ${selectionMenuPos.triangleOffset}px)` }"></div>
    </template>
    
    <template v-else>
      <div class="absolute top-0 transform -translate-x-1/2 -translate-y-full w-0 h-0 border-l-[6px] border-r-[6px] border-b-[6px] border-transparent border-b-neutral-900" :style="{ left: `calc(50% + ${selectionMenuPos.triangleOffset}px)` }"></div>
      <div class="absolute top-[-1px] transform -translate-x-1/2 -translate-y-full w-0 h-0 border-l-[7px] border-r-[7px] border-b-[7px] border-transparent border-b-neutral-800 -z-10" :style="{ left: `calc(50% + ${selectionMenuPos.triangleOffset}px)` }"></div>
    </template>
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
</template>

<script setup>
import { ref, reactive } from 'vue';

// 接收父组件传来的 Epub 核心引擎，用于执行高亮的物理绘制
const props = defineProps({
  rendition: {
    type: Object,
    required: true
  },
  book_id: {          
    type: String,
    required: true
  }
});
const setRawAnnotations = (annotations) => {
  rawAnnotationsCache = annotations;
};
// 向父组件汇报特定事件（比如绘制高亮时需要拦截父组件的点击翻页）
const emit = defineEmits(['cancel-tap']);
const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent) || 
                 (navigator.maxTouchPoints > 0 && 'ontouchstart' in window);

// --- 状态封闭化：原 EpubReader 中的 UI 状态全部迁移至此 ---
const showSelectionMenu = ref(false);
const selectionMenuPos = ref({ x: 0, y: 0, isFlipped: false, triangleOffset: 0 });
const currentSelection = ref({ cfi: null, text: '', segments: [] });
const isSelectionOverlapping = ref(false);
const isLongPressTriggered = ref(false);
const showAnnotationPanel = ref(false);
const currentNoteText = ref('');
const showWiki = ref(false);
const wikiContent = ref('');

const annotationDataMap = reactive({});
const activeHighlightCfi = ref(null);
const tempHighlightCfi = ref(null);
const isGlobalShieldActive = ref(false);

let pendingSelection = null;
let overlappingCfi = null;
let panelOpenTime = 0;
let longPressTimer = null;
let noteSaveTimer = null;
let rawAnnotationsCache = [];
let renderTimer = null;

const triggerTouchShield = () => {
  isGlobalShieldActive.value = true;
  // 450ms 刚好熬死所有的 CSS 动画时间和 iOS 幽灵点击延迟
  setTimeout(() => {
    isGlobalShieldActive.value = false;
  }, 450); 
};
// ✨ 新增：清理临时高亮的辅助函数
const clearTempHighlight = () => {
  if (tempHighlightCfi.value && props.rendition) {
    props.rendition.annotations.remove(tempHighlightCfi.value, 'highlight');
    tempHighlightCfi.value = null;
  }
};
// ✨ 修改：跨章渲染核心逻辑（加入防飘遮掩与强行截断动画）
const renderAnnotationsForCurrentChapter = (contents) => {
  if (!contents || !contents.document) return;
  // 🛡️ 战术 1：切断全局动画！
  // 注意：这段 style 是注入到 document (Vue 主文档) 的，而不是 iframe 中，彻底掐断高亮 SVG 的飞行动画
  let styleEl = document.getElementById('anti-fly-hl');
  if (!styleEl) {
    styleEl = document.createElement('style');
    styleEl.id = 'anti-fly-hl';
    document.head.appendChild(styleEl);
    styleEl.innerHTML = `
      .custom-hl, .temp-hl, .epubjs-hl { 
        transition: none !important; 
        animation: none !important; 
      }
      svg g[class*="hl"] rect {
        transition: none !important;
        animation: none !important;
      }
    `;
  }
  // 🛡️ 战术 2：先发制人，剥夺 Epub.js 的记忆！
  // 在排版挣扎期，立刻遍历清空 Epub.js 内部对所有高亮的记忆
  Object.keys(annotationDataMap).forEach(savedCfi => {
    if (props.rendition) {
      try {
        props.rendition.annotations.remove(savedCfi, 'highlight');
      } catch(e) {}
    }
  });

  // ✨ 核心修复：防抖锁！一巴掌拍死之前排队的定时器，防止网络请求和渲染事件并发导致高亮变亮（重叠）
  clearTimeout(renderTimer);

  // 🛡️ 战术 3：排版绝对死透后（200ms），重新精准落笔
  renderTimer = setTimeout(() => {
    rawAnnotationsCache.forEach(anno => {
      try {
        const startNode = contents.document.getElementById(anno.segments[0].nodeX);
        const endNode = contents.document.getElementById(anno.segments[anno.segments.length - 1].nodeX);

        if (startNode && endNode) {
          const range = contents.document.createRange();
          range.setStart(startNode.firstChild || startNode, anno.segments[0].startOffset);
          range.setEnd(endNode.firstChild || endNode, anno.segments[anno.segments.length - 1].endOffset);

          const cfi = contents.cfiFromRange(range);

          // 此时的 anno 已经是绝对最新状态（包含用户刚刚修改过的 note）
          // 在完全静止的 DOM 和绝对正确的坐标上，精准盖下唯一的章！
          injectExternalAnnotation(cfi, anno);
        }
      } catch (err) {
        // 节点不在当前章节，静默跳过
      }
    });
  }, 200); 
};
// --- 核心方法：提取选中坐标 (原封不动) ---
const extractSegments = (range, doc) => {
  const segmentsMap = {};
  let root = range.commonAncestorContainer;
  if (root.nodeType === 3) root = root.parentNode; 

  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let currentNode;

  while ((currentNode = walker.nextNode())) {
    if (!range.intersectsNode(currentNode)) continue;
    const targetEl = currentNode.parentElement ? currentNode.parentElement.closest('[id]') : null;
    if (!targetEl) continue;

    const nodeId = targetEl.id;
    const preRange = doc.createRange();
    preRange.selectNodeContents(targetEl);
    preRange.setEnd(currentNode, 0); 
    const prefixLen = preRange.toString().length;

    let start = currentNode === range.startContainer ? range.startOffset : 0;
    let end = currentNode === range.endContainer ? range.endOffset : currentNode.length;
    
    if (start === end) continue;

    const blockStart = prefixLen + start;
    const blockEnd = prefixLen + end;

    if (!segmentsMap[nodeId]) {
      segmentsMap[nodeId] = { nodeX: nodeId, startOffset: blockStart, endOffset: blockEnd };
    } else {
      segmentsMap[nodeId].startOffset = Math.min(segmentsMap[nodeId].startOffset, blockStart);
      segmentsMap[nodeId].endOffset = Math.max(segmentsMap[nodeId].endOffset, blockEnd);
    }
  }
  return Object.values(segmentsMap);
};

const setSelectionLayerActive = (isActive) => {
  if (!props.rendition) return;
  const contents = props.rendition.getContents()[0];
  if (!contents) return;

  const doc = contents.document;
  let styleEl = doc.getElementById('magic-selection-layer');

  if (!styleEl) {
    styleEl = doc.createElement('style');
    styleEl.id = 'magic-selection-layer';
    doc.head.appendChild(styleEl);
  }

  if (isActive) {
    // 🔓 揭开图层：让所有东西都变 text，但保护已有高亮 custom-hl 防误触
    styleEl.innerHTML = `
      * { 
        user-select: text !important; 
        -webkit-user-select: text !important; 
      }
      .custom-hl { 
        user-select: none !important; 
        -webkit-user-select: none !important; 
      }
    `;
  } else {
    // 🔒 盖上图层：全局封死，进入翻页模式
    styleEl.innerHTML = `
      * { 
        user-select: none !important; 
        -webkit-user-select: none !important; 
      }
    `;
  }
};

// 工具函数：坐标转选区 (完全采用你的无缝衔接逻辑)
const selectWordAtPoint = (x, y) => {
  const contents = props.rendition.getContents()[0];
  if (!contents) return;
  
  const doc = contents.document;
  const win = contents.window;
  let range;

  if (doc.caretRangeFromPoint) {
    range = doc.caretRangeFromPoint(x, y);
  } else if (doc.caretPositionFromPoint) {
    const pos = doc.caretPositionFromPoint(x, y);
    if (pos) {
      range = doc.createRange();
      range.setStart(pos.offsetNode, pos.offset);
      range.setEnd(pos.offsetNode, pos.offset);
    }
  }

  if (range) {
    const selection = win.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    
    // 技巧：向后扩选一个字，让用户立刻看到蓝块反馈
    try {
      win.getSelection().modify('extend', 'forward', 'character');
    } catch(e) {}
  }
};
const getRangeAtPoint = (doc, x, y) => {
  if (doc.caretRangeFromPoint) return doc.caretRangeFromPoint(x, y);
  if (doc.caretPositionFromPoint) {
    const pos = doc.caretPositionFromPoint(x, y);
    if (pos) {
      const range = doc.createRange();
      range.setStart(pos.offsetNode, pos.offset);
      range.setEnd(pos.offsetNode, pos.offset);
      return range;
    }
  }
  return null;
};
const processPointerDown = (e, x, y) => {
  isLongPressTriggered.value = false;
  if (e.target && e.target.classList && e.target.classList.contains('custom-hl')) return;
  // ✨ 新增防线：如果起手点按的是图片、SVG等非纯文本元素，直接拦截，不开启长按定时器
  if (e.target) {
    const tagName = e.target.tagName ? e.target.tagName.toLowerCase() : '';
    // SVG 内部可能会点到 path，所以用 closest 向上查找最稳妥
    if (tagName === 'img' || tagName === 'image' || e.target.closest('svg, img, video')) {
      return; 
    }
  }
  const contents = props.rendition.getContents()[0];
  if (!contents) return;
  const doc = contents.document;
  const win = contents.window;

  longPressTimer = setTimeout(() => {
    isLongPressTriggered.value = true;
    setSelectionLayerActive(true); // 🔓 揭开图层

    const startRange = getRangeAtPoint(doc, x, y);
    if (startRange) {
      const selection = win.getSelection();
      selection.removeAllRanges();
      selection.addRange(startRange);
      try { selection.modify('extend', 'forward', 'character'); } catch(err) {}

      const onMove = (moveEvt) => {
        if (!isLongPressTriggered.value) return;
        const moveX = moveEvt.clientX || (moveEvt.touches && moveEvt.touches[0].clientX);
        const moveY = moveEvt.clientY || (moveEvt.touches && moveEvt.touches[0].clientY);

        const currentRange = getRangeAtPoint(doc, moveX, moveY);
        // 🚀 回滚核心：删除了所有的 nodeType 限制，直接让浏览器接管跨段落、跨区块的选区蔓延！
        if (currentRange && selection.setBaseAndExtent) {
          selection.setBaseAndExtent(
            startRange.startContainer, startRange.startOffset,
            currentRange.startContainer, currentRange.startOffset
          );
        }
      };

      const onUp = () => {
        isLongPressTriggered.value = false; // ✨ 修复 1：抬手后立刻重置内部长按状态
        doc.removeEventListener('mousemove', onMove);
        doc.removeEventListener('touchmove', onMove);
        doc.removeEventListener('mouseup', onUp);
        doc.removeEventListener('touchend', onUp);
        
        // 💻 电脑端专属：抬手后延迟 150ms 结算选区并呼出菜单
        if (!isMobile) {
          setTimeout(() => {
            const currentSelection = win.getSelection();
            if (currentSelection && !currentSelection.isCollapsed && currentSelection.toString().trim() !== '') {
              const range = currentSelection.getRangeAt(0);
              const text = currentSelection.toString().trim();
              try {
                const finalCfi = contents.cfiFromRange(range);
                processSelection(finalCfi, text, range, contents, false);
              } catch (err) {
                console.warn("选区获取失败，尝试降级");
                showPendingMenu();
              }
            } else {
              // ✨ 修复 2：核心兜底。如果选区为空（例如在空白处长按松手），必须把保护图层盖回去！
              setSelectionLayerActive(false);
              clearNativeSelection();
            }
          }, 150);
        } else {
          // 📱 手机端兜底：即使交给了 EpubReader 处理，也顺手盖上图层保证安全
          setSelectionLayerActive(false);
        }
      };

      doc.addEventListener('mousemove', onMove);
      doc.addEventListener('touchmove', onMove);
      doc.addEventListener('mouseup', onUp);
      doc.addEventListener('touchend', onUp);
    }

    if (navigator.vibrate) navigator.vibrate(40);
  }, 300); 
};

const processPointerUp = () => {
  clearTimeout(longPressTimer); 
  const wasTriggered = isLongPressTriggered.value;
  isLongPressTriggered.value = false; // ✨ 修复 3：确保从外部调用抬手事件时，状态也被彻底重置
  return wasTriggered; // 返回 true 说明刚才是在长按划线，EpubReader 必须 return 终止翻页
};
// 重新闭环：清空选区的同时，一定要把玻璃盖回去！
const clearNativeSelection = () => {
  if (props.rendition) {
    const contents = props.rendition.getContents()[0];
    if (contents) {
      contents.window.getSelection().removeAllRanges();
      // 💻 电脑端专属：重新盖上玻璃
      if (!isMobile) {
        setSelectionLayerActive(false); 
      }
    }
  }
};
// --- 对外暴露的通信接口 1：处理原生选区 ---
const processSelection = (cfiRange, text, range, contents, isPointerDownFlag) => {
  const currentSegments = extractSegments(range, contents.document);
  isSelectionOverlapping.value = false;
  overlappingCfi = null;

  // 1. 碰撞检测 (判断是否划到了已有的高亮上)
  for (const [savedCfi, savedData] of Object.entries(annotationDataMap)) {
    const isOverlap = currentSegments.some(currSeg => {
      return savedData.segments.some(savedSeg => {
        if (currSeg.nodeX !== savedSeg.nodeX) return false;
        return Math.max(currSeg.startOffset, savedSeg.startOffset) < Math.min(currSeg.endOffset, savedSeg.endOffset);
      });
    });
    if (isOverlap) {
      isSelectionOverlapping.value = true;
      overlappingCfi = savedCfi;
      break;
    }
  }
  // 2. 计算物理位置 (用于决定菜单弹出的坐标)
  
  // 🚀 核心重构：完全信任浏览器的 DOM 阅读顺序，只过滤手机端幽灵节点
  const rects = Array.from(range.getClientRects()).filter(r => r.width > 2 && r.height > 2);
  let targetRect = range.getBoundingClientRect(); // 兜底

  if (rects.length > 0) {
    // rects[0] 绝对是高亮部分的物理起点
    const firstTop = rects[0].top;
    let minLeft = rects[0].left;
    let maxRight = rects[0].right;

    // 顺藤摸瓜，只拼合“第一行”的文字碎片
    for (let i = 1; i < rects.length; i++) {
      const currentRect = rects[i];
      const prevRect = rects[i - 1];

      // 判定“第一行结束”的两个铁证：
      // 1. Y 轴发生断层 (相差 > 10px，说明掉到下一行，或者跳到另一栏了)
      const isYChanged = Math.abs(currentRect.top - firstTop) > 10;
      // 2. X 轴发生倒退 (当前字的左边缘，比上一个字的左边缘还要靠左，说明发生“回车”了。留 5px 容差防抖)
      const isXReversed = currentRect.left < prevRect.left - 5;

      if (isYChanged || isXReversed) {
        break; // 第一行到此为止，切断！
      }

      // 如果还在同一行，扩充第一行的包围盒
      minLeft = Math.min(minLeft, currentRect.left);
      maxRight = Math.max(maxRight, currentRect.right);
    }

    targetRect = {
      top: rects[0].top,
      bottom: rects[0].bottom,
      left: minLeft,
      right: maxRight,
      width: maxRight - minLeft
    };
  }
  
  const iframe = contents.document.defaultView.frameElement;
  const iframeRect = iframe.getBoundingClientRect();
  
  // 基准点：现在绝对能精准锁定在“第一行高亮部分”的正中心
  const baseX = targetRect.left + iframeRect.left + (targetRect.width / 2);
  const baseY = targetRect.top + iframeRect.top;
  const bottomY = targetRect.bottom + iframeRect.top; 

  // --- 以下边缘限位与小三角偏移逻辑保持不变 ---
  const menuWidth = 280; 
  const halfWidth = menuWidth / 2;
  const screenWidth = window.innerWidth;

  const clampedX = Math.max(halfWidth + 10, Math.min(baseX, screenWidth - halfWidth - 10));
  
  let triangleOffset = baseX - clampedX;
  const maxTriangleOffset = halfWidth - 20; 
  triangleOffset = Math.max(-maxTriangleOffset, Math.min(triangleOffset, maxTriangleOffset));

  const isFlipped = baseY < 60; 
  const finalY = isFlipped ? bottomY : baseY; 

  const pos = { 
    x: clampedX, 
    y: finalY, 
    isFlipped: isFlipped,
    triangleOffset: triangleOffset
  };
  const selectionData = { cfi: cfiRange, text: text, pos: pos, segments: currentSegments };

  // 3. 核心分发逻辑
  if (isPointerDownFlag) {
    // 拖拽中：只挂起数据，千万不要清空选区
    pendingSelection = selectionData;
  } else {
    // 💡 拖拽结束，手指抬起，准备显示菜单
    selectionMenuPos.value = pos;
    currentSelection.value = selectionData;

    // ✨ 狸猫换太子：绘制“临时高亮”底色
    props.rendition.annotations.add(
      'highlight', cfiRange, {}, null, 'temp-hl', 
      { "fill": "#ffffff", "fill-opacity": "0.15" } 
    );
    tempHighlightCfi.value = cfiRange;

    // 瞬间清空原生选区（蓝条）
    contents.window.getSelection().removeAllRanges();

    // 🔒 核心修复：菜单马上要出来了，赶紧把“玻璃”盖回去！
    // 这样用户在菜单显示期间，怎么乱划都不会再触发选词了
    if (!isMobile) {
      setSelectionLayerActive(false);
    }

    // 弹出自定义极简菜单
    showSelectionMenu.value = true;
  }
};
// --- 对外暴露的通信接口 2：释放挂起的选区 ---
const showPendingMenu = () => {
  if (pendingSelection) {
    triggerTouchShield();
    selectionMenuPos.value = pendingSelection.pos;
    currentSelection.value = { ...pendingSelection };
    
    // ✨ 拖拽结束释放选区时的狸猫换太子
    props.rendition.annotations.add(
      'highlight', pendingSelection.cfi, {}, null, 'temp-hl', 
      { "fill": "#525252", "fill-opacity": "0.4" } 
    );
    tempHighlightCfi.value = pendingSelection.cfi;
    clearNativeSelection(); // 强制逼退 iOS 菜单

    showSelectionMenu.value = true;
    pendingSelection = null;
  }
};

const hideMenuOnly = () => {
  showSelectionMenu.value = false;
  pendingSelection = null;
  clearTempHighlight();
};
// --- 对外暴露的通信接口 3：一键闭合与状态探针 ---
const closeAll = () => {
  showSelectionMenu.value = false;
  showAnnotationPanel.value = false;
  showWiki.value = false;
  pendingSelection = null;
  clearNativeSelection();
  clearTempHighlight();
  currentNoteText.value = '';
};

const isAnyUIOpen = () => {
  return showSelectionMenu.value || showAnnotationPanel.value || showWiki.value;
};

// --- 内部逻辑层 (完全复用原代码) ---
const closeWiki = () => {
  showWiki.value = false;
  clearNativeSelection(); 
  clearTempHighlight();
};

const closeAnnotationPanel = () => {
  if (Date.now() - panelOpenTime < 400) return;
  triggerTouchShield();
  showAnnotationPanel.value = false;
  clearNativeSelection(); 
  clearTempHighlight();
  currentNoteText.value = '';
};

const deleteOverlappingAnnotation = () => {
  if (overlappingCfi) {
    const data = annotationDataMap[overlappingCfi];
    rawAnnotationsCache = rawAnnotationsCache.filter(
      anno => JSON.stringify(anno.segments) !== JSON.stringify(data.segments)
    );
    // 👉 核心修改 1：先把本地清理逻辑放到前面，瞬间让高亮和菜单消失！
    props.rendition.annotations.remove(overlappingCfi, 'highlight');
    delete annotationDataMap[overlappingCfi];
    isSelectionOverlapping.value = false;
    overlappingCfi = null;
    activeHighlightCfi.value = null; 
    currentNoteText.value = ''; 
    
    showSelectionMenu.value = false; 
    showAnnotationPanel.value = false; 
    showWiki.value = false;
    clearNativeSelection(); 
    clearTempHighlight();
    // 👉 核心修改 2：把 fetch 放到最后默默执行，去掉 await
    fetch(`/api/books/${props.book_id}/annotations/delete`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'user-token': localStorage.getItem('geek_token') || '',
        'guest-uuid': localStorage.getItem('guest_uuid') || ''
      },
      body: JSON.stringify({ segments: data.segments, text: data.text })
    }).catch(e => {
      console.error("后端删除失败", e); 
    });
  }
};

const syncNote = () => {
  // 如果是全新的划线（还没保存过），直接走 markAnnotation 的全套逻辑
  if (!isSelectionOverlapping.value) {
    markAnnotation();
    return;
  }
  
  if (overlappingCfi && annotationDataMap[overlappingCfi]) {
    // 1. 更新本地缓存（保证前端 UI 不卡顿）
    annotationDataMap[overlappingCfi].note = currentNoteText.value;
    const targetSegs = JSON.stringify(annotationDataMap[overlappingCfi].segments);
    const cacheIndex = rawAnnotationsCache.findIndex(
      anno => JSON.stringify(anno.segments) === targetSegs
    );
    if (cacheIndex !== -1) {
      rawAnnotationsCache[cacheIndex].note = currentNoteText.value;
    }
    
    // 2. ✨ 新增：静默同步到后端（停止打字 800ms 后自动触发更新）
    clearTimeout(noteSaveTimer);
    noteSaveTimer = setTimeout(async () => {
      const payload = {
        text: annotationDataMap[overlappingCfi].text,
        segments: annotationDataMap[overlappingCfi].segments,
        note: currentNoteText.value // 把最新的文字发过去
      };
      
      try {
        await fetch(`/api/books/${props.book_id}/annotations`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'user-token': localStorage.getItem('geek_token') || '',
            'guest-uuid': localStorage.getItem('guest_uuid') || ''
          },
          body: JSON.stringify(payload)
        });
      } catch (e) {
        console.error("批注静默保存失败", e);
      }
    }, 800);
  }
};

const copyText = () => {
  if (currentSelection.value && currentSelection.value.text) {
    navigator.clipboard.writeText(currentSelection.value.text);
    if (!showWiki.value && !showAnnotationPanel.value) {
      showSelectionMenu.value = false;
      clearNativeSelection(); 
      clearTempHighlight();
    }
  }
};

const searchInWiki = () => {
  if (currentSelection.value && currentSelection.value.text) {
    showSelectionMenu.value = false; 
    showAnnotationPanel.value = false; 
    summonReference(currentSelection.value.text);
  }
};

const switchToAnnotation = () => {
  triggerTouchShield();
  showSelectionMenu.value = false; 
  showWiki.value = false;
  currentNoteText.value = isSelectionOverlapping.value && overlappingCfi ? (annotationDataMap[overlappingCfi]?.note || '') : '';
  showAnnotationPanel.value = true;
};

const markAnnotation = () => {
  triggerTouchShield();
  const cfi = currentSelection.value.cfi;
  
  clearTempHighlight();
  if (!showAnnotationPanel.value) {
    currentNoteText.value = '';
  }
  
  const payload = {
    text: currentSelection.value.text,
    segments: currentSelection.value.segments, 
    note: currentNoteText.value 
  };
  rawAnnotationsCache.push(payload);

  // 👉 核心修改 1：立刻更新本地数据，供后续交互使用
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

  // 👉 核心修改 2：立刻在阅读器上画出最终高亮块，不让用户等！
  props.rendition.annotations.add(
    'highlight', cfi, {}, 
    (e) => {
      triggerTouchShield();
      const contents = props.rendition.getContents()[0];
      const selection = contents ? contents.window.getSelection() : null;
      if (selection && !selection.isCollapsed && selection.toString().trim().length > 0) return;

      emit('cancel-tap'); 
      
      isSelectionOverlapping.value = true;
      overlappingCfi = cfi;
      activeHighlightCfi.value = cfi;
      currentSelection.value = { 
        text: annotationDataMap[cfi].text, cfi: cfi, segments: annotationDataMap[cfi].segments
      };

      currentNoteText.value = annotationDataMap[cfi].note || '';     
      showAnnotationPanel.value = true;
      panelOpenTime = Date.now();
    }, 
    'custom-hl', 
    { "fill": "#ffffff", "fill-opacity": "0.22" } 
  );
  
  showSelectionMenu.value = false; 
  clearNativeSelection(); 

  // 👉 核心修改 3：最后再把请求扔给后端持久化，去掉 await
  fetch(`/api/books/${props.book_id}/annotations`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'user-token': localStorage.getItem('geek_token') || '',
      'guest-uuid': localStorage.getItem('guest_uuid') || ''
    },
    body: JSON.stringify(payload)
  }).catch(e => {
    console.error("同步至后端失败", e);
  });
};

const summonReference = async (query) => {
  triggerTouchShield();
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

const injectExternalAnnotation = (cfi, annoData) => {
  // 1. 存入本地 Map 供交互使用
  annotationDataMap[cfi] = {
    text: annoData.text,
    segments: annoData.segments,
    note: annoData.note
  };

  // 2. 在阅读器上画出高亮块，并绑定点击拦截逻辑
  props.rendition.annotations.add(
    'highlight', 
    cfi, 
    {}, 
    (e) => {
      // 这是点击已存在的高亮块时触发的事件
      triggerTouchShield();
      const contents = props.rendition.getContents()[0];
      const selection = contents ? contents.window.getSelection() : null;
      if (selection && !selection.isCollapsed && selection.toString().trim().length > 0) return;

      emit('cancel-tap'); // 通知父级掐断翻页定时器
      
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
      panelOpenTime = Date.now();
    }, 
    'custom-hl', 
    { "fill": "#ffffff", "fill-opacity": "0.22" } 
  );
};

// 暴露供父组件调用的武器库
defineExpose({
  processSelection,
  showPendingMenu,
  closeAll,
  isAnyUIOpen,
  hideMenuOnly,
  processPointerDown,
  processPointerUp,
  clearNativeSelection,
  setSelectionLayerActive,
  injectExternalAnnotation,
  setRawAnnotations,
  renderAnnotationsForCurrentChapter 
});
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.2s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.wiki-content :deep(a) { color: #a3a3a3; text-decoration: underline; }
.wiki-content :deep(p) { color: #d4d4d4; margin-bottom: 1em; }
.wiki-content :deep(h1), 
.wiki-content :deep(h2), 
.wiki-content :deep(h3) { 
  color: #f5f5f5; font-weight: bold; margin-top: 1.5em; margin-bottom: 0.5em;
}
</style>