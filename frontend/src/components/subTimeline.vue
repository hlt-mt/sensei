<script setup>
import { ref, computed, onMounted, onUnmounted, watch, inject, nextTick } from 'vue'
import WaveSurfer from 'wavesurfer.js'

const props = defineProps({
  duration: Number,
  videoRef: Object,
  subtitles: Array,
  tranSubtitles: Array,
  pixelsPerSecond: {
    type: Number,
    default: 80
  },
  activeTrack: {
    type: String,
    default: null
  },
  waveformHeight: { 
    type: Number, 
    default: 60 
  } 
})

const emit = defineEmits(['update:subtitles', 'update:tranSubtitles', 'update:activeTrack'])

const timelineWrapper = ref(null)
const currentTime = ref(0)
const isPlaying = ref(false)
const videoSrc = ref('')
const waveformKey = ref(0)
const isDragging = ref(false)
const playheadDragStartX = ref(0)
const isPlayheadActuallyDragging = ref(false)
const PLAYHEAD_DRAG_THRESHOLD = 5
const draggingSubtitle = ref(null)
const resizingSubtitle = ref(null)
const resizeEdge = ref(null) 
const dragStartX = ref(0)
const dragStartTime = ref(0)
const dragStartDuration = ref(0)
const subtitleType = ref(null)
const isClick = ref(true)
const snapshotSaved = ref(false)
const wavesurferInstance = ref(null)
const waveformContainer = ref(null)

// ─── Minimap refs ─────────────────────────────────────────────────────────────
const minimap = ref(null)
const isDraggingMinimap = ref(false)
const minimapDragStartX = ref(0)
const minimapDragStartScroll = ref(0)
const minimapScrollTick = ref(0)

const stopAtTime = ref(null)

// ─── Track availability ───────────────────────────────────────────────────────
const hasOriginal = computed(() => props.subtitles && props.subtitles.length > 0)
const hasTranslation = computed(() => props.tranSubtitles && props.tranSubtitles.length > 0)

const origTop = computed(() => `${props.waveformHeight + 10}px`)
const tranTop = computed(() =>
  hasOriginal.value
    ? `${props.waveformHeight + 10 + TRACK_HEIGHT}px`
    : `${props.waveformHeight + 10}px`
)

const trackAreaHeight = computed(() => {
  const wh = props.waveformHeight + 10
  if (hasOriginal.value && hasTranslation.value) return `${wh + TRACK_HEIGHT * 2}px`
  if (hasOriginal.value || hasTranslation.value) return `${wh + TRACK_HEIGHT}px`
  return `${wh}px`
})

const totalWidth = computed(() => (props.duration || 0) * props.pixelsPerSecond)

// ─── Minimap thumb — dipende da minimapScrollTick per reagire allo scroll ─────
const thumbStyle = computed(() => {
  minimapScrollTick.value // dipendenza reattiva sullo scroll
  if (!timelineWrapper.value || !minimap.value || totalWidth.value === 0) {
    return { left: '0px', width: '20%' }
  }
  const containerWidth = timelineWrapper.value.clientWidth
  const scrollLeft = timelineWrapper.value.scrollLeft
  const minimapWidth = minimap.value.clientWidth
  const ratio = Math.min(1, containerWidth / totalWidth.value)
  const thumbW = Math.max(16, minimapWidth * ratio)
  const maxScroll = totalWidth.value - containerWidth
  const scrollFraction = maxScroll > 0 ? scrollLeft / maxScroll : 0
  const maxThumbLeft = minimapWidth - thumbW
  const thumbL = scrollFraction * maxThumbLeft
  return {
    left: `${thumbL}px`,
    width: `${thumbW}px`
  }
})

// ─── Minimap handlers ─────────────────────────────────────────────────────────
const handleMinimapMouseDown = (event) => {
  if (!timelineWrapper.value || !minimap.value) return
  event.preventDefault()

  const rect = minimap.value.getBoundingClientRect()
  const minimapWidth = minimap.value.clientWidth
  const containerWidth = timelineWrapper.value.clientWidth
  const ratio = Math.min(1, containerWidth / totalWidth.value)
  const thumbW = Math.max(16, minimapWidth * ratio)
  const clickX = event.clientX - rect.left

  // Salta subito alla posizione cliccata, centrando il thumb
  const maxThumbLeft = minimapWidth - thumbW
  const targetThumbLeft = Math.max(0, Math.min(clickX - thumbW / 2, maxThumbLeft))
  const maxScroll = totalWidth.value - containerWidth
  const newScroll = maxThumbLeft > 0 ? (targetThumbLeft / maxThumbLeft) * maxScroll : 0
  timelineWrapper.value.scrollLeft = newScroll

  isDraggingMinimap.value = true
  minimapDragStartX.value = event.clientX
  minimapDragStartScroll.value = timelineWrapper.value.scrollLeft
  document.body.style.cursor = 'grabbing'
  document.body.style.userSelect = 'none'
}

const handleMinimapMouseMove = (event) => {
  if (!isDraggingMinimap.value || !timelineWrapper.value || !minimap.value) return
  const minimapWidth = minimap.value.clientWidth
  const containerWidth = timelineWrapper.value.clientWidth
  const ratio = Math.min(1, containerWidth / totalWidth.value)
  const thumbW = Math.max(16, minimapWidth * ratio)
  const maxThumbLeft = minimapWidth - thumbW
  const maxScroll = totalWidth.value - containerWidth

  const deltaX = event.clientX - minimapDragStartX.value
  const scrollDelta = maxThumbLeft > 0 ? (deltaX / maxThumbLeft) * maxScroll : 0
  timelineWrapper.value.scrollLeft = Math.max(
    0,
    Math.min(minimapDragStartScroll.value + scrollDelta, maxScroll)
  )
}

const handleMinimapMouseUp = () => {
  if (!isDraggingMinimap.value) return
  isDraggingMinimap.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

const isLightMode = ref(document.body.classList.contains('light-mode'))

const themeObserver = new MutationObserver(() => {
  isLightMode.value = document.body.classList.contains('light-mode')
})

const initWaveSurfer = () => {
  if (!videoSrc.value || !waveformContainer.value) return
  if (wavesurferInstance.value) {
    wavesurferInstance.value.destroy()
    wavesurferInstance.value = null
  }
  wavesurferInstance.value = WaveSurfer.create({
    container: waveformContainer.value,
    waveColor: '#86868b',
    progressColor: '#86868b',
    barWidth: 3,
    barGap: 2,
    barRadius: 2,
    height: props.waveformHeight,
    width: waveformWidth.value,
    backend: 'MediaElement',
    media: props.videoRef?.value || props.videoRef,
    interact: false,
    normalize: true,
  })
}

onMounted(() => {
  themeObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
})

onUnmounted(() => {
  themeObserver.disconnect()
})

const waveformColor = ref('#fefefe')
const playheadColor = computed(() => isLightMode.value ? '#cc0000' : '#ff4500')
const playheadShadow = computed(() => isLightMode.value ? '0 0 6px rgba(180,0,0,0.8)' : '0 0 5px rgba(255,69,0,0.5)')

const TRACK_HEIGHT = 50 

const leftGridRows = computed(() => {
  const wh = props.waveformHeight
  if (hasOriginal.value && hasTranslation.value) return `${wh}px ${TRACK_HEIGHT}px ${TRACK_HEIGHT}px`
  if (hasOriginal.value || hasTranslation.value) return `${wh}px ${TRACK_HEIGHT}px`
  return `${wh}px`
})

const formatPlayheadTime = (seconds) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`
}

const activeDragSub = computed(() => {
  if (draggingSubtitle.value) {
    const list = subtitleType.value === 'tran' ? processedTranSubtitles.value : processedSubtitles.value
    return list.find(s => s.id === draggingSubtitle.value.id) ?? null
  }
  if (resizingSubtitle.value) {
    const list = subtitleType.value === 'tran' ? processedTranSubtitles.value : processedSubtitles.value
    return list.find(s => s.id === resizingSubtitle.value.id) ?? null
  }
  return null
})

const activeSidebarTrack = ref(
  props.activeTrack ?? (!props.subtitles?.length && props.tranSubtitles?.length ? 'tran' : 'orig')
)

watch(() => props.activeTrack, (val) => {
  if (val && val !== activeSidebarTrack.value) {
    activeSidebarTrack.value = val
  }
})

watch([hasOriginal, hasTranslation], () => {
  if (activeSidebarTrack.value === 'orig' && !hasOriginal.value && hasTranslation.value) {
    activeSidebarTrack.value = 'tran'
    emit('update:activeTrack', 'tran')
  } else if (activeSidebarTrack.value === 'tran' && !hasTranslation.value && hasOriginal.value) {
    activeSidebarTrack.value = 'orig'
    emit('update:activeTrack', 'orig')
  }
}, { immediate: true })

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

watch(videoSrc, (val) => {
  if (val) {
    nextTick(() => initWaveSurfer())
  }
})

watch(() => props.pixelsPerSecond, () => {
  if (wavesurferInstance.value) {
    wavesurferInstance.value.destroy()
    wavesurferInstance.value = null
  }
  initWaveSurfer()
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
  return time >= sub.start && time < (sub.start + sub.duration)
}

const handleSubtitleClick = (sub, type) => {
  if (!isClick.value) return
  if (props.videoRef) {
    const videoElement = props.videoRef.value || props.videoRef
    videoElement.currentTime = sub.start
    stopAtTime.value = sub.start + (sub.duration - 0.001)                        
    if (onSubtitleSelect) {
      onSubtitleSelect(sub.id)
    }
  }
}

let rafId = null

const updateProgress = () => {
  if (!props.videoRef) return
  const videoElement = props.videoRef.value || props.videoRef
  currentTime.value = videoElement.currentTime
  isPlaying.value = !videoElement.paused
}

const startRaf = () => {
  const loop = () => {
    updateProgress()
    rafId = requestAnimationFrame(loop)
  }
  rafId = requestAnimationFrame(loop)
}

const stopRaf = () => {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
}

let scrollCooldown = false

watch(currentTime, (newVal) => {
  if (!timelineWrapper.value || !isPlaying.value) return
  const container = timelineWrapper.value
  const containerWidth = container.clientWidth
  const playheadPosition = newVal * props.pixelsPerSecond

  const visibleStart = container.scrollLeft
  const visibleEnd = visibleStart + containerWidth
  const margin = containerWidth * 0.15

  if (playheadPosition > visibleEnd - margin && !scrollCooldown) {
    scrollCooldown = true
    container.scrollTo({
      left: playheadPosition - margin,
      behavior: 'smooth'
    })
    minimapScrollTick.value++
    setTimeout(() => { scrollCooldown = false }, 1000)
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

const debounce = (fn, delay) => {
  let timer = null
  return (...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

watch(() => props.waveformHeight, debounce(() => {
  initWaveSurfer()
}, 600))

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
  playheadDragStartX.value = event.clientX
  isPlayheadActuallyDragging.value = false
  document.body.style.cursor = 'grabbing'
  document.body.style.userSelect = 'none'
  stopAtTime.value = null
}

const handleMouseMove = (event) => {
  if (isDragging.value && !draggingSubtitle.value && !resizingSubtitle.value) {
    if (!props.videoRef || !timelineWrapper.value) return
    const videoElement = props.videoRef.value || props.videoRef
    const rect = timelineWrapper.value.getBoundingClientRect()
    const clickX = event.clientX - rect.left + timelineWrapper.value.scrollLeft
    const newTime = Math.max(0, Math.min(clickX / props.pixelsPerSecond, props.duration))
    videoElement.currentTime = newTime

    const container = timelineWrapper.value
    const containerWidth = container.clientWidth
    const playheadPosition = newTime * props.pixelsPerSecond
    const visibleStart = container.scrollLeft
    const visibleEnd = visibleStart + containerWidth

    if ((playheadPosition < visibleStart || playheadPosition > visibleEnd) && !scrollCooldown) {
      scrollCooldown = true
      container.scrollTo({
        left: Math.max(0, playheadPosition - containerWidth * 0.5),
        behavior: 'smooth'
      })
      setTimeout(() => { scrollCooldown = false }, 1000) 
    }
    stopAtTime.value = null
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
    isPlayheadActuallyDragging.value = false
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

    const loop = () => {
      if (props.videoRef) {
        const el = props.videoRef.value || props.videoRef
        currentTime.value = el.currentTime
        isPlaying.value = !el.paused

        if (stopAtTime.value !== null && el.currentTime >= stopAtTime.value) {
          el.pause()
          el.currentTime = stopAtTime.value   
          stopAtTime.value = null             
        }
      }
      rafId = requestAnimationFrame(loop)
    }
    rafId = requestAnimationFrame(loop)

    videoElement.addEventListener('seeked', () => {
      if (isDragging.value) return
      if (timelineWrapper.value) {
        const container = timelineWrapper.value
        const containerWidth = container.clientWidth
        const playheadPosition = videoElement.currentTime * props.pixelsPerSecond
        container.scrollTo({
          left: Math.max(0, playheadPosition - containerWidth * 0.3),
          behavior: 'instant'
        })
      }
    })

    videoElement.addEventListener('loadedmetadata', () => {
      videoSrc.value = getVideoSrc()
    })
    videoSrc.value = getVideoSrc()
  }

  // Listener scroll per aggiornare il thumb del minimap
  nextTick(() => {
    if (timelineWrapper.value) {
      timelineWrapper.value.addEventListener('scroll', () => {
        minimapScrollTick.value++
      })
    }
  })

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
  document.addEventListener('mousemove', handleMinimapMouseMove)
  document.addEventListener('mouseup', handleMinimapMouseUp)
})

onUnmounted(() => {
  stopRaf()
  if (wavesurferInstance.value) wavesurferInstance.value.destroy()
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
  document.removeEventListener('mousemove', handleMinimapMouseMove)
  document.removeEventListener('mouseup', handleMinimapMouseUp)
})
</script>

<template>
  <div class="container">
    <!-- Colonna sinistra: label tracce -->
    <div class="left" :style="{ gridTemplateRows: leftGridRows }">
      <div class="waveform-label">Waveform</div>

      <div v-if="hasOriginal" class="track-label">
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

      <div v-if="hasTranslation" class="track-label">
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
    </div>

    <!-- Colonna destra: minimap fisso + timeline scrollabile -->
    <div class="timeline-column">

      <!-- MINIMAP — fuori dal wrapper scrollabile, occupa sempre tutta la larghezza -->
      <div
        class="minimap"
        ref="minimap"
        @mousedown="handleMinimapMouseDown"
      >
        <template v-if="hasOriginal">
          <div
            v-for="sub in processedSubtitles"
            :key="'mm-orig-' + sub.id"
            class="minimap-seg minimap-seg-orig"
            :style="{
              left: ((sub.start / (duration || 1)) * 100) + '%',
              width: Math.max(0.2, (sub.duration / (duration || 1)) * 100) + '%'
            }"
          />
        </template>
        <template v-if="hasTranslation">
          <div
            v-for="sub in processedTranSubtitles"
            :key="'mm-tran-' + sub.id"
            class="minimap-seg minimap-seg-tran"
            :style="{
              left: ((sub.start / (duration || 1)) * 100) + '%',
              width: Math.max(0.2, (sub.duration / (duration || 1)) * 100) + '%'
            }"
          />
        </template>
        <!-- Playhead nel minimap -->
        <div
          class="minimap-playhead"
          :style="{ left: ((currentTime / (duration || 1)) * 100) + '%' }"
        />
        <!-- Thumb trascinabile -->
        <div
          class="minimap-thumb"
          :class="{ 'minimap-thumb-dragging': isDraggingMinimap }"
          :style="thumbStyle"
        />
      </div>

      <!-- TIMELINE SCROLLABILE -->
      <div class="timeline-wrapper" ref="timelineWrapper">
        <div 
          class="ruler" 
          :style="{ width: (duration * pixelsPerSecond) + 'px' }"
        >
          <div
            v-if="isDragging"
            class="playhead-tooltip"
            :style="{ left: (currentTime * pixelsPerSecond) + 'px' }"
          >
            {{ formatPlayheadTime(currentTime) }}
          </div>
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

        <div class="track-area" :style="{ width: (duration * pixelsPerSecond) + 'px', height: trackAreaHeight }">
          <div
            v-if="activeDragSub"
            class="subtitle-drag-tooltip"
            :style="{
              left: ((activeDragSub.start + activeDragSub.duration / 2) * pixelsPerSecond) + 'px',
              top: subtitleType === 'tran' ? tranTop : origTop
            }"
          >
            {{ formatPlayheadTime(activeDragSub.start) }} &#8594; {{ formatPlayheadTime(activeDragSub.start + activeDragSub.duration) }}
          </div>
          <div 
            class="playhead" 
            :style="{ transform: `translateX(${currentTime * pixelsPerSecond}px)` }"
            @mousedown="handlePlayheadMouseDown"
          >
            <div class="playhead-line" :style="{ 
              height: `calc(${trackAreaHeight} + 30px)`,
              background: playheadColor,
              boxShadow: playheadShadow
            }"></div>
          </div>

          <div
            ref="waveformContainer"
            class="waveform-track"
            :style="{ width: waveformWidth + 'px', height: waveformHeight + 'px' }"
          >
            <div v-if="!videoSrc" class="waveform-placeholder">
              Caricamento video...
            </div>
          </div>

          <!-- Original track -->
          <template v-if="hasOriginal">
            <div 
              v-for="sub in processedSubtitles" 
              :key="'orig-' + sub.id"
              class="sub-block sub-block-orig"
              :class="{ 
                'sub-block-dragging': draggingSubtitle?.id === sub.id || resizingSubtitle?.id === sub.id,
                'sub-block-sidebar-active': activeSidebarTrack === 'orig',
                'sub-block-active': isSubtitleActive(sub),
                'sub-block-orig-active': isSubtitleActive(sub),
              }"
              :style="{ 
                position: 'absolute',
                left: '0px',
                top: origTop,
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
          </template>
          
          <!-- Translated track -->
          <template v-if="hasTranslation">
            <div 
              v-for="sub in processedTranSubtitles" 
              :key="'tran-' + sub.id"
              class="sub-block sub-block-tran"
              :class="{ 
                'sub-block-active': isSubtitleActive(sub),
                'sub-block-dragging': draggingSubtitle?.id === sub.id || resizingSubtitle?.id === sub.id,
                'sub-block-sidebar-active': activeSidebarTrack === 'tran',
                'sub-block-tran-active': isSubtitleActive(sub),
              }"
              :style="{ 
                position: 'absolute',
                left: '0px',
                top: tranTop,
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
          </template>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* ─── Layout principale ──────────────────────────────────────────────────────── */
.container {
  display: grid;
  grid-template-columns: 10% 90%;
  width: 100%;
  height: 100%;
}

/* Colonna sinistra: label tracce */
.left {
  padding-top: 52px; /* 30px originali + 22px altezza minimap */
  display: grid;
  align-items: center;
}

/* Colonna destra: flex verticale — minimap sopra, timeline sotto */
.timeline-column {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

/* ─── Minimap ────────────────────────────────────────────────────────────────── */
.minimap {
  position: relative;          /* NON sticky, NON fixed — è fuori dallo scroll */
  width: 100%;
  height: 22px;
  flex-shrink: 0;
  background: #0d1017;
  border-bottom: 1px solid #2a2f3a;
  cursor: crosshair;
  user-select: none;
  overflow: hidden;
}

.minimap-seg {
  position: absolute;
  pointer-events: none;
  border-radius: 1px;
  min-width: 2px;
}

.minimap-seg-orig {
  top: 4px;
  height: 6px;
  background: rgba(142, 73, 160, 0.85);
}

.minimap-seg-tran {
  top: 13px;
  height: 6px;
  background: rgba(59, 131, 246, 0.85);
}

.minimap-playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1.5px;
  transform: translateX(-50%);
  background: v-bind(playheadColor);
  pointer-events: none;
  z-index: 3;
}

.minimap-thumb {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 2px;
  pointer-events: none;
  z-index: 2;
  box-sizing: border-box;
  transition: background 0.1s;
}

.minimap-thumb-dragging {
  background: rgba(255, 255, 255, 0.15) !important;
}

.minimap:active .minimap-thumb {
  background: rgba(255, 255, 255, 0.13);
}

/* ─── Timeline scrollabile ───────────────────────────────────────────────────── */
.timeline-wrapper {
  flex: 1;
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  background-color: #1c2331;
  border-top: 1px solid #333;
  position: relative;
  scrollbar-width: thin;
  scrollbar-color: #444 #111;
}

/* ─── Righello ───────────────────────────────────────────────────────────────── */
.ruler {
  height: 30px;
  position: relative;
  background-color: #1c2331;
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

/* ─── Track area ─────────────────────────────────────────────────────────────── */
.track-area {
  position: relative;
  background-color: #1c2331;
  background-image: linear-gradient(to right, #222 1px, transparent 1px);
  background-size: v-bind('pixelsPerSecond + "px"') 100%;
}

.waveform-track {
  position: absolute;
  top: 0;
  left: 0;
  background-color: #1c2331;
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
  height: v-bind('waveformHeight + "px"') !important;
  background: transparent !important;
}

.waveform-track :deep(audio) {
  display: none !important;
}

.waveform-track :deep(wave) {
  overflow: hidden !important;
}

/* ─── Playhead ───────────────────────────────────────────────────────────────── */
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
  background: #ff4500;
  box-shadow: 0 0 5px rgba(255, 69, 0, 0.5);
}

/* ─── Tooltip ────────────────────────────────────────────────────────────────── */
.playhead-tooltip {
  position: absolute;
  top: 4px;
  transform: translateX(-50%);
  background: #1e1e1e;
  border: 1px solid #555;
  color: #e0e0e0;
  font-size: 11px;
  font-family: monospace;
  padding: 3px 7px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0,0,0,0.5);
  z-index: 200;
}

.subtitle-drag-tooltip {
  position: absolute;
  transform: translate(-50%, -100%);
  margin-top: -4px;
  background: #1e1e1e;
  border: 1px solid #555;
  color: #e0e0e0;
  font-size: 11px;
  font-family: monospace;
  padding: 3px 7px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  z-index: 200;
}

/* ─── Label tracce ───────────────────────────────────────────────────────────── */
.waveform-label {
  font-size: 14px;
  color: #b0afaf;
  padding-left: 6px;
}

.track-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px;
  font-size: 14px;
  color: #b0afaf;
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

/* ─── Blocchi subtitle ───────────────────────────────────────────────────────── */
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
  background: rgba(59, 131, 246, 0.5);
  border: 1px solid #3b82f6;
}

.sub-block-tran:hover {
  background: rgba(59, 131, 246, 0.83);
}

.sub-block-orig {
  background: rgba(142, 73, 160, 0.45);
  border: 1px solid #8e49a0;
}

.sub-block-orig:hover {
  background: rgba(142, 73, 160, 0.75);
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

.sub-block-orig-active {
  background: rgba(181, 83, 206, 0.75);
}

.sub-block-tran-active {
  background: rgba(83, 148, 253, 0.83);
}

.sub-block-text {
  white-space: nowrap;
  text-overflow: ellipsis;
  display: block;
  overflow: hidden;
  flex: 1;
  pointer-events: none;
  font-size: 12px;
}

/* ─── Resize handle ──────────────────────────────────────────────────────────── */
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