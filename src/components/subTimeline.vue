<script setup>
import { ref, computed, onMounted, onUnmounted, watch, inject } from 'vue'
import { AVWaveform } from 'vue-audio-visual'

const props = defineProps({
  duration: Number,
  videoRef: Object,
  subtitles: Array,
  tranSubtitles: Array,
  pixelsPerSecond: {
    type: Number,
    default: 80
  }
})

const emit = defineEmits(['update:subtitles', 'update:tranSubtitles', 'update:activeTrack'])

const timelineWrapper = ref(null)
const currentTime = ref(0)
const isPlaying = ref(false)
const videoSrc = ref('')
const waveformKey = ref(0)
const isDragging = ref(false)
const draggingSubtitle = ref(null)
const resizingSubtitle = ref(null)
const resizeEdge = ref(null) 
const dragStartX = ref(0)
const dragStartTime = ref(0)
const dragStartDuration = ref(0)
const subtitleType = ref(null)
const isClick = ref(true)
const snapshotSaved = ref(false)

const activeSidebarTrack = ref('tran')

const MIN_SUBTITLE_DURATION = 0.5

const onSubtitleSelect = inject('onSubtitleSelect', null)
const saveUndoSnapshot = inject('saveUndoSnapshot', null)

const toggleSidebarTrack = (track) => {
  activeSidebarTrack.value = track
  emit('update:activeTrack', track)
}

const getVideoSrc = () => {
  if (!props.videoRef) return ''
  const videoElement = props.videoRef.value || props.videoRef
  return videoElement.src || videoElement.currentSrc || ''
}

watch(() => props.videoRef, () => {
  videoSrc.value = getVideoSrc()
}, { immediate: true, deep: true })

watch(() => props.pixelsPerSecond, () => {
  waveformKey.value++
})

const parseSrtTimestamp = (timestampStr) => {
  if (!timestampStr) return 0
  const startTime = timestampStr.split('-->')[0].trim().replace(',', '.')
  const parts = startTime.split(':').map(Number)
  if (parts.length === 3) {
    return (parts[0] * 3600) + (parts[1] * 60) + parts[2]
  }
  return 0
}

const parseSrtDuration = (timestampStr) => {
  if (!timestampStr.includes('-->')) return 2
  const parts = timestampStr.split('-->').map(t => parseSrtTimestamp(t.trim()))
  return Math.max(0.1, parts[1] - parts[0])
}

const formatTimestampToSrt = (startTime, duration) => {
  const formatSrtTime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 1000)
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`
  }
  const endTime = startTime + duration
  return `${formatSrtTime(startTime)} --> ${formatSrtTime(endTime)}`
}

const updateSubtitleTimestamp = (subId, newStart, newDuration, type) => {
  const isTran = type === 'tran'
  const updatedSubs = isTran ? [...props.tranSubtitles] : [...props.subtitles]
  const subToUpdate = updatedSubs[subId]
  if (subToUpdate) {
    subToUpdate.timestamp = formatTimestampToSrt(newStart, newDuration)
    if (isTran) {
      emit('update:tranSubtitles', updatedSubs)
    } else {
      emit('update:subtitles', updatedSubs)
    }
  }
}

const processedSubtitles = computed(() => {
  if (!props.subtitles || props.subtitles.length === 0) return []
  return props.subtitles.map((sub, index) => {
    const start = parseSrtTimestamp(sub.timestamp)
    const duration = parseSrtDuration(sub.timestamp)
    return {
      id: index,
      start, 
      duration,
      text: sub.testo || sub.text || '',
      originalTimestamp: sub.timestamp
    }
  })
})

const processedTranSubtitles = computed(() => {
  if (!props.tranSubtitles || props.tranSubtitles.length === 0) return []
  return props.tranSubtitles.map((sub, index) => {
    const start = parseSrtTimestamp(sub.timestamp)
    const duration = parseSrtDuration(sub.timestamp)
    return {
      id: index,
      start, 
      duration,
      text: sub.testo || sub.text || '',
      originalTimestamp: sub.timestamp
    }
  })
})

const isSubtitleActive = (sub) => {
  const time = currentTime.value
  return time >= sub.start && time <= (sub.start + sub.duration)
}

const handleSubtitleClick = (sub, type) => {
  if (!isClick.value) return
  if (props.videoRef) {
    const videoElement = props.videoRef.value || props.videoRef
    videoElement.currentTime = sub.start
    videoElement.pause()
    if (onSubtitleSelect) {
      onSubtitleSelect(sub.id)
    }
  }
}

const updateProgress = () => {
  if (!props.videoRef) return
  const videoElement = props.videoRef.value || props.videoRef
  currentTime.value = videoElement.currentTime
  isPlaying.value = !videoElement.paused
}

watch(currentTime, (newVal) => {
  if (!timelineWrapper.value) return
  const container = timelineWrapper.value
  const playheadPosition = newVal * props.pixelsPerSecond

  const PAGE_WIDTH = 1150   
  const SCROLL_STEP = 1140  

  const pageIndex = Math.floor(playheadPosition / PAGE_WIDTH)
  const targetScroll = pageIndex * SCROLL_STEP

  if (container.scrollLeft !== targetScroll) {
    container.scrollTo({
      left: targetScroll,
      behavior: 'smooth'
    })
  }
})

watch(() => props.pixelsPerSecond, () => {
  if (timelineWrapper.value && props.videoRef) {
    const playheadPosition = currentTime.value * props.pixelsPerSecond
    const offset = 200
    timelineWrapper.value.scrollTo({
      left: Math.max(0, playheadPosition - offset),
      behavior: 'smooth'
    })
  }
})

const dynamicStep = computed(() => {
  if (props.pixelsPerSecond < 30) return 30
  if (props.pixelsPerSecond < 60) return 10
  return 5
})

const timeMarkers = computed(() => {
  const markers = []
  for (let i = 0; i <= (props.duration || 0); i += dynamicStep.value) {
    markers.push(i)
  }
  return markers
})

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const handleSubtitleMouseDown = (event, sub, edge = null, type = null) => {
  event.preventDefault()
  event.stopPropagation()
  isClick.value = true
  subtitleType.value = type
  snapshotSaved.value = false
  if (edge && edge !== 'tran' && edge !== 'orig') {
    resizingSubtitle.value = sub
    resizeEdge.value = edge
    dragStartDuration.value = sub.duration
  } else if (!edge || edge === 'tran' || edge === 'orig') {
    draggingSubtitle.value = sub
    dragStartDuration.value = sub.duration
  }
  dragStartX.value = event.clientX
  dragStartTime.value = sub.start
  document.body.style.cursor = (edge && edge !== 'tran' && edge !== 'orig') ? 'ew-resize' : 'grabbing'
  document.body.style.userSelect = 'none'
}

const handlePlayheadMouseDown = (event) => {
  event.preventDefault()
  isDragging.value = true
  document.body.style.cursor = 'grabbing'
  document.body.style.userSelect = 'none'
}

const handleMouseMove = (event) => {
  if (isDragging.value && !draggingSubtitle.value && !resizingSubtitle.value) {
    if (!props.videoRef || !timelineWrapper.value) return
    const videoElement = props.videoRef.value || props.videoRef
    const rect = timelineWrapper.value.getBoundingClientRect()
    const clickX = event.clientX - rect.left + timelineWrapper.value.scrollLeft
    const newTime = Math.max(0, Math.min(clickX / props.pixelsPerSecond, props.duration))
    videoElement.currentTime = newTime
    return
  }

  const isTran = subtitleType.value === 'tran'
  const currentData = isTran ? processedTranSubtitles.value : processedSubtitles.value
  const currentList = isTran ? [...props.tranSubtitles] : [...props.subtitles]
  const deltaX = event.clientX - dragStartX.value
  const deltaTime = deltaX / props.pixelsPerSecond

  if (draggingSubtitle.value) {
    if (!snapshotSaved.value && Math.abs(deltaX) > 2) {
      if (saveUndoSnapshot) saveUndoSnapshot()
      snapshotSaved.value = true
    }
    isClick.value = false
    const subId = draggingSubtitle.value.id
    const duration = dragStartDuration.value
    let newStart = dragStartTime.value + deltaTime
    let newEnd = newStart + duration

    currentData.forEach((s) => {
      if (s.id === subId) return
      if (dragStartTime.value + duration <= s.start + 0.001) {
        const minPossibleStartOfNext = s.start + s.duration - MIN_SUBTITLE_DURATION
        if (newEnd > s.start) {
          newEnd = Math.min(newEnd, minPossibleStartOfNext)
          newStart = newEnd - duration
          if (newEnd > s.start) {
            currentList[s.id].timestamp = formatTimestampToSrt(newEnd, (s.start + s.duration) - newEnd)
          }
        }
      }
      if (dragStartTime.value >= s.start + s.duration - 0.001) {
        const maxPossibleEndOfPrev = s.start + MIN_SUBTITLE_DURATION
        if (newStart < s.start + s.duration) {
          newStart = Math.max(newStart, maxPossibleEndOfPrev)
          newEnd = newStart + duration
          if (newStart < s.start + s.duration) {
            currentList[s.id].timestamp = formatTimestampToSrt(s.start, newStart - s.start)
          }
        }
      }
    })

    newStart = Math.max(0, Math.min(newStart, (props.duration || 0) - duration))
    currentList[subId].timestamp = formatTimestampToSrt(newStart, duration)
    emit(isTran ? 'update:tranSubtitles' : 'update:subtitles', currentList)
  }

  if (resizingSubtitle.value) {
    if (!snapshotSaved.value && Math.abs(deltaX) > 2) {
      if (saveUndoSnapshot) saveUndoSnapshot()
      snapshotSaved.value = true
    }
    isClick.value = false
    const subId = resizingSubtitle.value.id
    if (resizeEdge.value === 'right') {
      let newEnd = resizingSubtitle.value.start + Math.max(MIN_SUBTITLE_DURATION, dragStartDuration.value + deltaTime)
      currentData.forEach(s => {
        if (s.id === subId) return
        if (s.start >= resizingSubtitle.value.start + dragStartDuration.value - 0.001) {
          const limit = s.start + s.duration - MIN_SUBTITLE_DURATION
          newEnd = Math.min(newEnd, limit)
          if (newEnd > s.start) {
            currentList[s.id].timestamp = formatTimestampToSrt(newEnd, (s.start + s.duration) - newEnd)
          }
        }
      })
      currentList[subId].timestamp = formatTimestampToSrt(resizingSubtitle.value.start, newEnd - resizingSubtitle.value.start)
    } else {
      let newStart = Math.min(dragStartTime.value + deltaTime, (dragStartTime.value + dragStartDuration.value) - MIN_SUBTITLE_DURATION)
      newStart = Math.max(0, newStart)
      currentData.forEach(s => {
        if (s.id === subId) return
        if (s.start + s.duration <= dragStartTime.value + 0.001) {
          const limit = s.start + MIN_SUBTITLE_DURATION
          newStart = Math.max(newStart, limit)
          if (newStart < s.start + s.duration) {
            currentList[s.id].timestamp = formatTimestampToSrt(s.start, newStart - s.start)
          }
        }
      })
      currentList[subId].timestamp = formatTimestampToSrt(newStart, (dragStartTime.value + dragStartDuration.value) - newStart)
    }
    emit(isTran ? 'update:tranSubtitles' : 'update:subtitles', currentList)
  }
}

const handleMouseUp = () => {
  if (isDragging.value || draggingSubtitle.value || resizingSubtitle.value) {
    isDragging.value = false
    draggingSubtitle.value = null
    resizingSubtitle.value = null
    resizeEdge.value = null
    subtitleType.value = null
    snapshotSaved.value = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }
}

const waveformWidth = computed(() => {
  return (props.duration || 0) * props.pixelsPerSecond
})

onMounted(() => {
  if (props.videoRef) {
    const videoElement = props.videoRef.value || props.videoRef
    videoElement.addEventListener('timeupdate', updateProgress)
    videoElement.addEventListener('play', updateProgress)
    videoElement.addEventListener('pause', updateProgress)
    videoElement.addEventListener('loadedmetadata', () => {
      videoSrc.value = getVideoSrc()
    })
    videoSrc.value = getVideoSrc()
  }
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
})

onUnmounted(() => {
  if (props.videoRef) {
    const videoElement = props.videoRef.value || props.videoRef
    videoElement.removeEventListener('timeupdate', updateProgress)
    videoElement.removeEventListener('play', updateProgress)
    videoElement.removeEventListener('pause', updateProgress)
  }
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})
</script>

<template>
  <div class="container">
    <div class="left">
      <div class="waveform-label">Waveform</div>

      <div class="track-label">
        <span>Translated</span>
        <button
          class="eye-btn"
          :class="{ 'eye-btn-active': activeSidebarTrack === 'tran' }"
          :title="activeSidebarTrack === 'tran' ? 'Showing Track 1 in sidebar' : 'Show Track 1 in sidebar'"
          @click="toggleSidebarTrack('tran')"
        >
          <svg v-if="activeSidebarTrack === 'tran'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/>
            <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.247.248-.517.486z"/>
            <path d="M11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829"/>
            <path d="M3.35 5.47q-.27.238-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z"/>
          </svg>
        </button>
      </div>

    
      <div class="track-label">
        <span>Original</span>
        <button
          class="eye-btn"
          :class="{ 'eye-btn-active': activeSidebarTrack === 'orig' }"
          :title="activeSidebarTrack === 'orig' ? 'Showing Track 2 in sidebar' : 'Show Track 2 in sidebar'"
          @click="toggleSidebarTrack('orig')"
        >
    
          <svg v-if="activeSidebarTrack === 'orig'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/>
            <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/>
          </svg>
      
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.247.248-.517.486z"/>
            <path d="M11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829"/>
            <path d="M3.35 5.47q-.27.238-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="timeline-wrapper" ref="timelineWrapper">
      <div 
        class="ruler" 
        :style="{ width: (duration * pixelsPerSecond) + 'px' }"
      >
        <div 
          v-for="time in timeMarkers" 
          :key="time" 
          class="marker-group"
          :style="{ left: (time * pixelsPerSecond) + 'px' }"
        >
          <span class="time-label">{{ formatTime(time) }}</span>
          <div class="tick-major"></div>
        </div>
      </div>

      <div class="track-area" :style="{ width: (duration * pixelsPerSecond) + 'px' }">
        <div 
          class="playhead" 
          :style="{ transform: `translateX(${currentTime * pixelsPerSecond}px)` }"
          @mousedown="handlePlayheadMouseDown"
        >
          <div class="playhead-line"></div>
        </div>

        <div 
          ref="waveformContainer" 
          class="waveform-track"
          :style="{ width: waveformWidth + 'px' }"
        >
          <AVWaveform
            v-if="videoSrc"
            :key="`${videoSrc}-${waveformKey}`" 
            :src="videoSrc"
            :canv-width="waveformWidth"
            :playtime="false"
            :playtime-line-width="0"
            :canv-height="60"
            :line-width="3"
            :line-space="2"
            :line-color="'#60a5fa'"
            :audio-controls="false"
            :noplayed-line-width="0"
          />
          <div v-else class="waveform-placeholder">
            Caricamento video...
          </div>
        </div>

 
        <div 
          v-for="sub in processedTranSubtitles" 
          :key="'tran-' + sub.id"
          class="sub-block sub-block-tran"
          :class="{ 
            'sub-block-active': isSubtitleActive(sub),
            'sub-block-dragging': draggingSubtitle?.id === sub.id || resizingSubtitle?.id === sub.id,
            'sub-block-sidebar-active': activeSidebarTrack === 'tran'
          }"
          :style="{ 
            position: 'absolute',
            left: '0px',
            top: '70px',
            width: (sub.duration * pixelsPerSecond) + 'px',
            transform: `translateX(${sub.start * pixelsPerSecond}px)` 
          }"
          :title="sub.originalTimestamp"
          @click="handleSubtitleClick(sub, 'tran')"
          @mousedown="(e) => handleSubtitleMouseDown(e, sub, null, 'tran')"
        >
          <div 
            class="resize-handle resize-handle-left"
            @mousedown.stop="(e) => handleSubtitleMouseDown(e, sub, 'left', 'tran')"
          ></div>
          <span class="sub-block-text">{{ sub.text }}</span>
          <div 
            class="resize-handle resize-handle-right"
            @mousedown.stop="(e) => handleSubtitleMouseDown(e, sub, 'right', 'tran')"
          ></div>
        </div>

        <div 
          v-for="sub in processedSubtitles" 
          :key="'orig-' + sub.id"
          class="sub-block sub-block-orig"
          :class="{ 
            'sub-block-dragging': draggingSubtitle?.id === sub.id || resizingSubtitle?.id === sub.id,
            'sub-block-sidebar-active': activeSidebarTrack === 'orig'
          }"
          :style="{ 
            position: 'absolute',
            left: '0px',
            top: '130px',
            width: (sub.duration * pixelsPerSecond) + 'px',
            transform: `translateX(${sub.start * pixelsPerSecond}px)` 
          }"
          :title="sub.originalTimestamp"
          @click="handleSubtitleClick(sub, 'orig')"
          @mousedown="(e) => handleSubtitleMouseDown(e, sub, null, 'orig')"
        >
          <div 
            class="resize-handle resize-handle-left"
            @mousedown.stop="(e) => handleSubtitleMouseDown(e, sub, 'left', 'orig')"
          ></div>
          <span class="sub-block-text">{{ sub.text }}</span>
          <div 
            class="resize-handle resize-handle-right"
            @mousedown.stop="(e) => handleSubtitleMouseDown(e, sub, 'right', 'orig')"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  display: grid;
  grid-template-columns: 10% 90%;
  width: 100%;
  height: 100%;
}

.left {
  padding-top: 30px;
  display: grid;
  grid-template-rows: 60px 60px 60px;
  align-items: center;
}

.waveform-label {
  font-size: 11px;
  color: #888;
  padding-left: 6px;
}

.track-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px;
  font-size: 11px;
  color: #888;
}

.track-label span {
  flex: 1;
}

.eye-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  padding: 3px;
  border-radius: 4px;
  cursor: pointer;
  color: #555;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.eye-btn:hover {
  color: #aaa;
  background: rgba(255, 255, 255, 0.08);
}

.eye-btn-active {
  color: rgba(18, 83, 163, 0.918) !important;
}

.eye-btn-active:hover {
  color: rgba(18, 83, 163, 1) !important;
  background: rgba(18, 83, 163, 0.15) !important;
}

.timeline-wrapper {
  width: 100%;
  overflow-x: auto;
  background: #111;
  border-top: 1px solid #333;
  position: relative;
  scrollbar-width: thin;
  scrollbar-color: #444 #111;
  scroll-behavior: smooth;
}

.ruler {
  height: 30px;
  position: relative;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
}

.marker-group {
  position: absolute;
  top: 0;
  height: 100%;
}

.time-label {
  position: absolute;
  top: 2px;
  left: 4px;
  font-size: 10px;
  color: #888;
  font-family: monospace;
}

.tick-major {
  position: absolute;
  bottom: 0;
  width: 1px;
  height: 8px;
  background: #555;
}

.track-area {
  height: 200px;
  position: relative;
  background: #141414;
  background-image: linear-gradient(to right, #222 1px, transparent 1px);
  background-size: v-bind('pixelsPerSecond + "px"') 100%;
  display: grid;
  grid-template-rows: 60px 60px 60px;
}

.waveform-track {
  position: absolute;
  top: 0;
  left: 0;
  height: 60px;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  pointer-events: none;
  user-select: none;
  overflow: hidden;
}

.waveform-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  font-size: 12px;
}

.waveform-track :deep(canvas) {
  display: block !important;
  width: 100% !important;
  height: 60px !important;
  background: transparent !important;
}

.waveform-track :deep(audio) {
  display: none !important;
}

.playhead {
  position: absolute;
  top: -30px;
  left: 0;
  z-index: 100;
  pointer-events: all;
  cursor: grab;
}

.playhead:active {
  cursor: grabbing;
}

.playhead-line {
  width: 2px;
  height: 230px;
  background: #ff4500;
  box-shadow: 0 0 5px rgba(255, 69, 0, 0.5);
}

.sub-block {
  height: 40px;
  border-radius: 4px;
  padding: 4px 8px;
  overflow: hidden;
  color: white;
  font-size: 11px;
  cursor: grab;
  z-index: 5;
  display: flex;
  align-items: center;
  box-sizing: border-box;
  transition: background 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  position: relative;
  user-select: none;
}

.sub-block-tran {
  background: rgba(0, 120, 215, 0.5);
  border: 1px solid #0078d7;
}

.sub-block-tran:hover {
  background: rgba(0, 120, 215, 0.8);
}


.sub-block-orig {
  background: rgba(0, 170, 140, 0.45);
  border: 1px solid #00aa8c;
}

.sub-block-orig:hover {
  background: rgba(0, 170, 140, 0.75);
}

.sub-block-sidebar-active {
  border-width: 2px;
  filter: brightness(1.15);
}

.sub-block-dragging {
  cursor: grabbing;
  opacity: 0.8;
  z-index: 15;
}

.sub-block-active {
  border-color: #8025f7 !important;
  box-shadow: 0 0 10px rgba(137, 41, 234, 0.6);
  z-index: 10;
}

.sub-block-text {
  white-space: nowrap;
  text-overflow: ellipsis;
  display: block;
  overflow: hidden;
  flex: 1;
  pointer-events: none;
}

.resize-handle {
  position: absolute;
  top: 0;
  width: 8px;
  height: 100%;
  cursor: ew-resize;
  z-index: 10;
  opacity: 0;
  transition: opacity 0.2s;
}

.resize-handle-left {
  left: 0;
  background: linear-gradient(to right, rgba(255,255,255,0.3), transparent);
}

.resize-handle-right {
  right: 0;
  background: linear-gradient(to left, rgba(255,255,255,0.3), transparent);
}

.sub-block:hover .resize-handle {
  opacity: 1;
}
</style>