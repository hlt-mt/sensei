<script setup>
import { onMounted, onUnmounted, ref, provide, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import subTimeline from '../components/subTimeline.vue'

const router = useRouter()

const videoUrl = ref('')
const videoFile = ref(null)

const currentProject = ref(null)
const isSaving = ref(false)

const showBackConfirm = ref(false)

const showVideoDropModal = ref(false)
const videoDropError = ref('')
const subtitles = ref([])
const tranSubtitles = ref([])
const videoPlayer = ref(null) 
const isPlaying = ref(false)
const zoomLevel = ref(1)
const waveformKey = ref(0)
const currentTime = ref(0)
const videoDuration = ref(0)
const pixelsPerSecond = ref(80)
const subtitlesScroll = ref(null)
const selectedSubtitleIndex = ref(-1)

// ─── Resizable panels ────────────────────────────────────────────────────────
const timelineHeightPct = ref(35)   // % altezza container
const sidebarWidthPct = ref(40)     // % larghezza content

const startResizeTimeline = (e) => {
  e.preventDefault()
  const container = document.querySelector('.container')
  const startY = e.clientY
  const startPct = timelineHeightPct.value
  const onMove = (ev) => {
    const delta = ((startY - ev.clientY) / container.clientHeight) * 100
    timelineHeightPct.value = Math.min(70, Math.max(15, startPct + delta))
  }
  const onUp = () => {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

const isDarkMode = ref(true)

const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value
  document.body.classList.toggle('light-mode', !isDarkMode.value)
}

const startResizeSidebar = (e) => {
  e.preventDefault()
  const content = document.querySelector('.content')
  const startX = e.clientX
  const startPct = sidebarWidthPct.value
  const onMove = (ev) => {
    const delta = ((ev.clientX - startX) / content.clientWidth) * 100
    sidebarWidthPct.value = Math.min(65, Math.max(20, startPct + delta))
  }
  const onUp = () => {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

const isPlayingSelectedSubtitle = ref(false)

const SERVICE_BASE = import.meta.env.VITE_SERVICE_BASE || 'https://api.matita.net/subtitles-admin'

// ─── Track availability ───────────────────────────────────────────────────────
const hasOriginal = computed(() => subtitles.value.length > 0)
const hasTranslation = computed(() => tranSubtitles.value.length > 0)

const expectedVideoName = computed(() => {
  if (!currentProject.value) return '';
  let d = currentProject.value.data;
  if (!d) return '';
  try { while (typeof d === 'string') { d = JSON.parse(d); } } catch (e) { return ''; }
  return d.videoName || (d.data && d.data.videoName) || '';
});

const projectName = computed(() => currentProject.value?.name || 'project')

watch(currentProject, (newVal) => {
  if (newVal && newVal.data && typeof newVal.data === 'string') {
    try {
      let d = newVal.data;
      while (typeof d === 'string' && d.startsWith('{')) { d = JSON.parse(d); }
      currentProject.value = { ...newVal, data: d };
    } catch (e) { console.warn("Errore parsing watcher dati", e); }
  }
}, { immediate: true, deep: true });

const activeSidebarTrack = ref('orig')

// ─── Auto-switch track if the active one is empty ────────────────────────────
watch([hasOriginal, hasTranslation], () => {
  if (activeSidebarTrack.value === 'orig' && !hasOriginal.value && hasTranslation.value) {
    activeSidebarTrack.value = 'tran'
  } else if (activeSidebarTrack.value === 'tran' && !hasTranslation.value && hasOriginal.value) {
    activeSidebarTrack.value = 'orig'
  }
}, { immediate: true })

const sidebarSubtitles = computed(() =>
  activeSidebarTrack.value === 'tran' ? tranSubtitles.value : subtitles.value
)

const undoStack = ref([])
const MAX_UNDO = 50

const saveUndoSnapshot = () => {
  const snapshot = {
    tranSubtitles: JSON.parse(JSON.stringify(tranSubtitles.value)),
    subtitles: JSON.parse(JSON.stringify(subtitles.value))
  }
  undoStack.value.push(snapshot)
  if (undoStack.value.length > MAX_UNDO) undoStack.value.shift()
}

const undo = () => {
  if (undoStack.value.length === 0) return
  const snapshot = undoStack.value.pop()
  tranSubtitles.value = snapshot.tranSubtitles
  subtitles.value = snapshot.subtitles
  localStorage.setItem('tranSubtitles', JSON.stringify(tranSubtitles.value))
  localStorage.setItem('subtitles', JSON.stringify(subtitles.value))
}

const canUndo = computed(() => undoStack.value.length > 0)

provide('saveUndoSnapshot', saveUndoSnapshot)

const showModal = ref(false)
const editingIndex = ref(-1)
const editForm = ref({ timestamp: '', testo: '' })

const calculatedWidth = computed(() => {
  if (videoDuration.value === 0) return 1200
  return Math.floor(videoDuration.value * pixelsPerSecond.value * zoomLevel.value)
})

provide('zoomLevel', zoomLevel)
provide('calculatedWidth', calculatedWidth)

const parseSrtTimestamp = (timestampStr) => {
  if (!timestampStr) return 0
  const startTime = timestampStr.split('-->')[0].trim().replace(',', '.')
  const parts = startTime.split(':').map(Number)
  if (parts.length === 3) return (parts[0] * 3600) + (parts[1] * 60) + parts[2]
  return 0
}

const parseSrtTimestampEnd = (timestampStr) => {
  if (!timestampStr || !timestampStr.includes('-->')) return 0
  const endTime = timestampStr.split('-->')[1].trim().replace(',', '.')
  const parts = endTime.split(':').map(Number)
  if (parts.length === 3) return (parts[0] * 3600) + (parts[1] * 60) + (parts[2] - 0.001)
  return 0
}

const formatSrtTimestamp = (seconds) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.round((seconds % 1) * 1000)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`
}

const buildTimestamp = (startSec, endSec) => `${formatSrtTimestamp(startSec)} --> ${formatSrtTimestamp(endSec)}`

const addSubtitleBetween = (index) => {
  saveUndoSnapshot()
  const DEFAULT_DURATION = 0.4
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  const prev = targetArray.value[index]
  const next = targetArray.value[index + 1]
  const newStart = parseSrtTimestampEnd(prev.timestamp)
  const newEnd = newStart + DEFAULT_DURATION
  if (next) {
    const nextStart = parseSrtTimestamp(next.timestamp)
    const nextEnd = parseSrtTimestampEnd(next.timestamp)
    if (newEnd > nextStart) {
      const adjustedNextStart = newEnd
      const adjustedNextEnd = Math.max(nextEnd, adjustedNextStart + 0.001)
      next.timestamp = buildTimestamp(adjustedNextStart, adjustedNextEnd)
    }
  }
  targetArray.value.splice(index + 1, 0, { timestamp: buildTimestamp(newStart, newEnd), testo: '' })
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
}

const addSubtitleAtStart = () => {
  saveUndoSnapshot()
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  const DEFAULT_DURATION = 0.5
  if (targetArray.value.length > 0) {
    const first = targetArray.value[0]
    const firstEnd = parseSrtTimestampEnd(first.timestamp)
    if (firstEnd > DEFAULT_DURATION) first.timestamp = buildTimestamp(DEFAULT_DURATION, firstEnd)
  }
  targetArray.value.unshift({ timestamp: buildTimestamp(0, DEFAULT_DURATION), testo: '' })
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
}

const addSubtitleAtEnd = () => {
  saveUndoSnapshot()
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  const DEFAULT_DURATION = 0.5
  const lastEnd = targetArray.value.length > 0
    ? parseSrtTimestampEnd(targetArray.value[targetArray.value.length - 1].timestamp) + 0.1
    : 0
  targetArray.value.push({ timestamp: buildTimestamp(lastEnd, lastEnd + DEFAULT_DURATION), testo: '' })
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
}

const duplicateSubtitleBetween = (index) => {
  saveUndoSnapshot()
  const DEFAULT_DURATION = 0.4
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  const prev = targetArray.value[index]
  const next = targetArray.value[index + 1]
  const newStart = parseSrtTimestampEnd(prev.timestamp)
  const newEnd = newStart + DEFAULT_DURATION
  if (next) {
    const nextStart = parseSrtTimestamp(next.timestamp)
    const nextEnd = parseSrtTimestampEnd(next.timestamp)
    if (newEnd > nextStart) {
      const adjustedNextStart = newEnd
      const adjustedNextEnd = Math.max(nextEnd, adjustedNextStart + 0.001)
      next.timestamp = buildTimestamp(adjustedNextStart, adjustedNextEnd)
    }
  }
  targetArray.value.splice(index + 1, 0, { timestamp: buildTimestamp(newStart, newEnd), testo: prev.testo })
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
}

const duplicateSubtitleAtStart = () => {
  saveUndoSnapshot()
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  const DEFAULT_DURATION = 0.5
  const sourceText = targetArray.value.length > 0 ? targetArray.value[0].testo : ''
  if (targetArray.value.length > 0) {
    const first = targetArray.value[0]
    const firstEnd = parseSrtTimestampEnd(first.timestamp)
    if (firstEnd > DEFAULT_DURATION) first.timestamp = buildTimestamp(DEFAULT_DURATION, firstEnd)
  }
  targetArray.value.unshift({ timestamp: buildTimestamp(0, DEFAULT_DURATION), testo: sourceText })
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
}

const duplicateSubtitleAtEnd = () => {
  saveUndoSnapshot()
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  const DEFAULT_DURATION = 0.5
  const sourceText = targetArray.value.length > 0
    ? targetArray.value[targetArray.value.length - 1].testo
    : ''
  const lastEnd = targetArray.value.length > 0
    ? parseSrtTimestampEnd(targetArray.value[targetArray.value.length - 1].timestamp) + 0.1
    : 0
  targetArray.value.push({ timestamp: buildTimestamp(lastEnd, lastEnd + DEFAULT_DURATION), testo: sourceText })
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
}

const mergeSubtitles = (index) => {
  saveUndoSnapshot()
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  const a = targetArray.value[index]
  const b = targetArray.value[index + 1]
  if (!a || !b) return
  const startSec = parseSrtTimestamp(a.timestamp)
  const endSec = parseSrtTimestampEnd(b.timestamp)
  const merged = {
    timestamp: buildTimestamp(startSec, endSec),
    testo: [a.testo, b.testo].filter(t => t.trim()).join(' ')
  }
  targetArray.value.splice(index, 2, merged)
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
  if (selectedSubtitleIndex.value === index + 1) selectedSubtitleIndex.value = index
  else if (selectedSubtitleIndex.value > index + 1) selectedSubtitleIndex.value--
}

const getActiveSubtitleIndex = () => {
  const arr = sidebarSubtitles.value
  if (!arr || arr.length === 0) return -1
  for (let i = 0; i < arr.length; i++) {
    const sub = arr[i]
    const start = parseSrtTimestamp(sub.timestamp)
    let duration = 2
    if (sub.timestamp.includes('-->')) {
      const parts = sub.timestamp.split('-->')
      const end = parseSrtTimestamp(parts[1].trim())
      duration = end - start
    }
    if (currentTime.value >= start && currentTime.value < start + duration) return i
  }
  return -1
}

const activeSubtitleText = computed(() => {
  const arr = activeSidebarTrack.value === 'tran' ? tranSubtitles.value : subtitles.value
  if (!arr || arr.length === 0) return ''
  for (let i = 0; i < arr.length; i++) {
    const sub = arr[i]
    const start = parseSrtTimestamp(sub.timestamp)
    const end = parseSrtTimestampEnd(sub.timestamp)
    if (currentTime.value >= start && currentTime.value < end) return sub.testo || ''
  }
  return ''
})

const sourceLanguage = computed(() => {
  if (!currentProject.value?.data) return ''
  let d = currentProject.value.data
  try { while (typeof d === 'string') d = JSON.parse(d) } catch (e) { return '' }
  return d.sourceLanguage || ''
})

const targetLanguage = computed(() => {
  if (!currentProject.value?.data) return ''
  let d = currentProject.value.data
  try { while (typeof d === 'string') d = JSON.parse(d) } catch (e) { return '' }
  return d.targetLanguage || ''
})

const DEFAULT_TIMELINE_PCT = 35 

const waveformHeight = computed(() => {
  if (timelineHeightPct.value <= DEFAULT_TIMELINE_PCT) return 60
  const extraPct = timelineHeightPct.value - DEFAULT_TIMELINE_PCT
  const extraPx = (window.innerHeight * extraPct / 100) * 0.8
  return Math.min(180, Math.floor(60 + extraPx))
})

const isEditingName = ref(false)
const editingName = ref('')

const startEditName = () => {
  editingName.value = projectName.value
  isEditingName.value = true
  nextTick(() => { document.getElementById('project-name-input')?.focus() })
}

const confirmEditName = async () => {
  if (!editingName.value.trim()) return
  currentProject.value = { ...currentProject.value, name: editingName.value.trim() }
  isEditingName.value = false
  await handleSave()
}

const cancelEditName = () => { isEditingName.value = false }

const handleExport = () => {
  const downloadSrt = (content, filename) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }
  handleSave()
  const pName = currentProject.value?.name || 'project'
  const today = new Date()
  const date = `${String(today.getDate()).padStart(2, '0')}-${String(today.getMonth() + 1).padStart(2, '0')}-${today.getFullYear()}`
  if (hasTranslation.value) downloadSrt(arrayToSrt(tranSubtitles.value), `${pName}_${targetLanguage.value}_${date}.srt`)
  if (hasOriginal.value) downloadSrt(arrayToSrt(subtitles.value), `${pName}_${sourceLanguage.value}_${date}.srt`)
}

const scrollSidebarToActive = () => {
  if (!subtitlesScroll.value || !isPlaying.value) return
  const activeIndex = getActiveSubtitleIndex()
  if (activeIndex < 0 || activeIndex < 3) return
  const container = subtitlesScroll.value
  const blocks = container.querySelectorAll('.subtitle-block')
  if (blocks[activeIndex]) {
    const block = blocks[activeIndex]
    const targetScroll = block.offsetTop - (container.clientHeight / 2) + (block.clientHeight / 2)
    container.scrollTo({ top: Math.max(0, targetScroll), behavior: 'smooth' })
  }
}

const isSubtitleActive = (index) => getActiveSubtitleIndex() === index

const checkSubtitleEnd = () => {
  if (selectedSubtitleIndex.value >= 0 && isPlayingSelectedSubtitle.value) {
    const arr = sidebarSubtitles.value
    const sub = arr[selectedSubtitleIndex.value]
    if (!sub) return
    const startTime = parseSrtTimestamp(sub.timestamp)
    const parts = sub.timestamp.split('-->')
    const endTime = parts.length > 1 ? parseSrtTimestamp(parts[1].trim()) : startTime + 2
    if (currentTime.value >= endTime) {
      videoPlayer.value.pause()
      selectedSubtitleIndex.value = -1
      isPlayingSelectedSubtitle.value = false
    }
  }
}

const stopAtTime = ref(null)
let rafId = null

const handleSidebarClick = (index) => {
  const arr = sidebarSubtitles.value
  if (!videoPlayer.value || !arr[index]) return
  const sub = arr[index]
  const parts = sub.timestamp.includes('-->')
    ? sub.timestamp.split('-->').map(t => parseSrtTimestamp(t.trim()))
    : [parseSrtTimestamp(sub.timestamp), parseSrtTimestamp(sub.timestamp) + 2]
  const start = parts[0]
  const duration = Math.max(0.1, parts[1] - parts[0])

  videoPlayer.value.currentTime = start
  stopAtTime.value = start + (duration - 0.001)
  selectedSubtitleIndex.value = index
  isPlayingSelectedSubtitle.value = false
}

const handleSubtitleSelect = (index) => {
  selectedSubtitleIndex.value = index
  isPlayingSelectedSubtitle.value = false

  const arr = sidebarSubtitles.value
  if (!videoPlayer.value || !arr[index]) return


  setTimeout(() => {
    isPlayingSelectedSubtitle.value = true
  }, 0)

  nextTick(() => {
    const container = subtitlesScroll.value
    const blocks = container?.querySelectorAll('.subtitle-block')
    if (blocks?.[index]) {
      const block = blocks[index]
      const targetScroll = block.offsetTop - (container.clientHeight / 2) + (block.clientHeight / 2)
      container.scrollTo({ top: Math.max(0, targetScroll), behavior: 'smooth' })
    }
  })
}
provide('onSubtitleSelect', handleSubtitleSelect)

const handleNativeFullscreen = () => {
  if (
    document.fullscreenElement === videoPlayer.value ||
    document.webkitFullscreenElement === videoPlayer.value
  ) {
    const exitFs = document.exitFullscreen || document.webkitExitFullscreen
    exitFs.call(document).then(() => {
      toggleFullscreen()
    }).catch(() => {
      toggleFullscreen()
    })
  }
}

const setupVideoSync = () => {
  if (videoPlayer.value) {
    videoPlayer.value.onloadedmetadata = () => { videoDuration.value = videoPlayer.value.duration }
    videoPlayer.value.ontimeupdate = () => {
      currentTime.value = videoPlayer.value.currentTime
      checkSubtitleEnd()
    }
    videoPlayer.value.onplay = () => {
        isPlaying.value = true
        if (selectedSubtitleIndex.value >= 0 && !isPlayingSelectedSubtitle.value) {
          isPlayingSelectedSubtitle.value = false
          selectedSubtitleIndex.value = -1
        }
      }
    videoPlayer.value.onpause = () => { isPlaying.value = false }

    videoPlayer.value.onfullscreenchange = handleNativeFullscreen
    videoPlayer.value.onwebkitfullscreenchange = handleNativeFullscreen
  }
}

const rafLoop = () => {
  if (videoPlayer.value) {
    currentTime.value = videoPlayer.value.currentTime
    if (stopAtTime.value !== null && videoPlayer.value.currentTime >= stopAtTime.value) {
      videoPlayer.value.pause()
      videoPlayer.value.currentTime = stopAtTime.value
      stopAtTime.value = null
    }
  }
  rafId = requestAnimationFrame(rafLoop)
}
const deleteSubtitle = (index) => {
  saveUndoSnapshot()
  const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
  targetArray.value.splice(index, 1)
  localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
  if (selectedSubtitleIndex.value === index) selectedSubtitleIndex.value = -1
  else if (selectedSubtitleIndex.value > index) selectedSubtitleIndex.value--
}

const openEditModal = (index) => {
  editingIndex.value = index
  const arr = sidebarSubtitles.value
  editForm.value = { timestamp: arr[index].timestamp, testo: arr[index].testo }
  showModal.value = true
  if (videoPlayer.value && !videoPlayer.value.paused) videoPlayer.value.pause()
}

const closeModal = () => {
  showModal.value = false
  editingIndex.value = -1
  editForm.value = { timestamp: '', testo: '' }
}

const saveEdit = () => {
  if (editingIndex.value >= 0) {
    saveUndoSnapshot()
    const targetArray = activeSidebarTrack.value === 'tran' ? tranSubtitles : subtitles
    targetArray.value[editingIndex.value] = { timestamp: editForm.value.timestamp, testo: editForm.value.testo }
    targetArray.value.sort((a, b) => parseSrtTimestamp(a.timestamp) - parseSrtTimestamp(b.timestamp))
    localStorage.setItem(activeSidebarTrack.value === 'tran' ? 'tranSubtitles' : 'subtitles', JSON.stringify(targetArray.value))
    closeModal()
  }
}

const handleBack = () => { showBackConfirm.value = true }

const clearProjectStorage = () => {
  localStorage.removeItem('subtitles')
  localStorage.removeItem('tranSubtitles')
  localStorage.removeItem('currentProjectId')
  localStorage.removeItem('currentProjectName')
  localStorage.removeItem('currentProjectUserId')
  localStorage.removeItem('currentProjectBackup')
}

const confirmBackSave = async () => {
  await handleSave()
  showBackConfirm.value = false
  clearProjectStorage()
  document.body.classList.remove('light-mode')
  isDarkMode.value = true
  router.push('/myprojects')
}

const confirmBackNoSave = () => {
  showBackConfirm.value = false
  clearProjectStorage()
  document.body.classList.remove('light-mode')
  isDarkMode.value = true
  router.push('/myprojects')
}

const handleKeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); undo() }
}

const arrayToSrt = (arr) => arr.map((sub, i) => 
  `${i + 1}\n${sub.timestamp}\n${sub.testo}`
).join('\n\n')

const apiFetch = async (url, options = {}) => {
  const token = localStorage.getItem('subtitles_token')
  if (!token) { router.push('/login'); return null }
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`, ...(options.headers || {}) }
  })
  const refreshedToken = res.headers.get('x-refresh-token')
  if (refreshedToken) localStorage.setItem('subtitles_token', refreshedToken)
  if (res.status === 401) { localStorage.removeItem('subtitles_token'); router.push('/login'); return null }
  return res
}

const handleSave = async () => {
  if (!currentProject.value || !currentProject.value.id) { console.warn('handleSave: nessun progetto o ID mancante'); return; }
  if (isSaving.value) return;
  isSaving.value = true;
  const srt1 = arrayToSrt(tranSubtitles.value);
  const srt2 = arrayToSrt(subtitles.value);
  try {
    let currentData = {};
    try { let d = currentProject.value.data; while (typeof d === 'string') { d = JSON.parse(d); } currentData = d; } catch (e) { currentData = {}; }
    const res = await apiFetch(
      `${SERVICE_BASE}/projects/${currentProject.value.id}`,
      { method: 'PATCH', body: JSON.stringify({ name: currentProject.value.name, data: JSON.stringify({ ...currentData, srt1, srt2, playhead: currentTime.value, last_saved: new Date().toISOString() }) }) }
    );
    if (!res) return;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) { console.error('Save error:', err); } finally { isSaving.value = false; }
}

const trimSubtitlesToDuration = () => {
  if (!videoDuration.value || videoDuration.value === 0) return
  const filter = (arr) => arr.filter(sub => parseSrtTimestamp(sub.timestamp) < videoDuration.value)
  const filteredSubs = filter(subtitles.value)
  const filteredTran = filter(tranSubtitles.value)
  if (filteredSubs.length !== subtitles.value.length) { subtitles.value = filteredSubs; localStorage.setItem('subtitles', JSON.stringify(subtitles.value)) }
  if (filteredTran.length !== tranSubtitles.value.length) { tranSubtitles.value = filteredTran; localStorage.setItem('tranSubtitles', JSON.stringify(tranSubtitles.value)) }
}

watch(videoDuration, (val) => { if (val > 0) trimSubtitlesToDuration() })

let autosaveInterval = null

watch(currentTime, () => { scrollSidebarToActive() })
watch(activeSidebarTrack, () => { selectedSubtitleIndex.value = -1 })

const handleVideoDropModal = (event) => {
  const files = event.dataTransfer.files
  if (files.length > 0) loadVideoFile(files[0])
}

const handleVideoSelectModal = (event) => {
  const file = event.target.files[0]
  if (file) loadVideoFile(file)
}

const loadVideoFile = (file) => {
  videoDropError.value = '';
  if (expectedVideoName.value && file.name !== expectedVideoName.value) {
    videoDropError.value = `Errore: il file selezionato (${file.name}) non corrisponde al video originale del progetto: "${expectedVideoName.value}".`;
    return;
  }
  videoFile.value = file
  videoUrl.value = URL.createObjectURL(file)
  showVideoDropModal.value = false
  nextTick(() => {
    setupVideoSync()
    const savedPlayhead = currentProject.value?.data?.playhead
    if (savedPlayhead && savedPlayhead > 0 && videoPlayer.value) {
      videoPlayer.value.addEventListener('loadedmetadata', () => { videoPlayer.value.currentTime = savedPlayhead }, { once: true })
    }
  })
}

onMounted(() => {
  const stored = localStorage.getItem('subtitles')
  if (stored) subtitles.value = JSON.parse(stored)
  const storedTran = localStorage.getItem('tranSubtitles')
  if (storedTran) tranSubtitles.value = JSON.parse(storedTran)

  // ─── Set default track based on which arrays are populated ─────────────────
  if (!hasOriginal.value && hasTranslation.value) {
    activeSidebarTrack.value = 'tran'
  } else {
    activeSidebarTrack.value = 'orig'
  }

  const projectFromState = history.state?.project
  const backupId = localStorage.getItem('currentProjectId')

  if (projectFromState) {
    let cleanData = projectFromState.data;
    try {
      while (typeof cleanData === 'string' && cleanData.trim().startsWith('{')) cleanData = JSON.parse(cleanData);
    } catch (e) { console.error("Errore parsing dati in onMounted", e); }
    currentProject.value = { ...projectFromState, data: cleanData };
    localStorage.setItem('currentProjectBackup', JSON.stringify(currentProject.value))
    localStorage.setItem('currentProjectId', projectFromState.id)
    localStorage.setItem('currentProjectName', projectFromState.name)
  } else if (backupId) {
    const fullBackup = localStorage.getItem('currentProjectBackup')
    if (fullBackup) currentProject.value = JSON.parse(fullBackup)
  }

  const file = history.state?.videoFile || null
  if (file) {
    videoFile.value = file
    videoUrl.value = URL.createObjectURL(file)
    nextTick(() => { setupVideoSync() })
  } else {
    showVideoDropModal.value = true
  }
 rafId = requestAnimationFrame(rafLoop)
  autosaveInterval = setInterval(handleSave, 5 * 60 * 1000)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId) 
  if (videoUrl.value) URL.revokeObjectURL(videoUrl.value)
  if (autosaveInterval) clearInterval(autosaveInterval)
  window.removeEventListener('keydown', handleKeydown)
})

const restartVideo = () => { if (videoPlayer.value) { videoPlayer.value.currentTime = 0; videoPlayer.value.pause() } }
const togglePlay = () => { 
  if (videoPlayer.value) { 
    if (videoPlayer.value.paused) {
      isPlayingSelectedSubtitle.value = false
      selectedSubtitleIndex.value = -1
      videoPlayer.value.play()
    } else {
      videoPlayer.value.pause()
    }
  } 
}
const endVideo = () => { if (videoPlayer.value) { videoPlayer.value.currentTime = videoPlayer.value.duration; videoPlayer.value.pause();}};
const zoomOut = () => { zoomLevel.value = Math.max(0.5, zoomLevel.value - 0.25); pixelsPerSecond.value = 80 * zoomLevel.value; waveformKey.value++ }
const zoomIn = () => { zoomLevel.value = Math.min(5, zoomLevel.value + 0.25); pixelsPerSecond.value = 80 * zoomLevel.value; waveformKey.value++ }
const onZoomSlider = (e) => {
  zoomLevel.value = parseFloat(e.target.value)
  pixelsPerSecond.value = 80 * zoomLevel.value
  waveformKey.value++
}
const toggleFullscreen = () => {
  if (!videoPlayer.value) return

  if (!document.fullscreenElement) {
    const videoBox = videoPlayer.value.closest('.video-box')
    if (videoBox) {
      videoBox.requestFullscreen()
    } else {
      videoPlayer.value.requestFullscreen()
    }
  } else {
    document.exitFullscreen()
  }
}

watch(videoPlayer, (newPlayer) => { if (newPlayer) setupVideoSync() })
</script>

<template>
  <div class="wrapper">
    <header class="header fixed-top p-3 d-flex justify-content-between align-items-center">
      <div class="logo">Sensei</div>

      <div style="position: absolute; left: 50%; transform: translateX(-50%);">
        <input
          v-if="isEditingName"
          id="project-name-input"
          v-model="editingName"
          @blur="confirmEditName"
          @keyup.enter="confirmEditName"
          @keyup.escape="cancelEditName"
          style="background: transparent; border: none; border-bottom: 1px solid #4a90e2; color: #f1f5f9; font-size: 0.85rem; text-align: center; outline: none; width: 200px;"
        />
        <h6
          v-else
          @click="startEditName"
          class="project-name"
          :class="{ 'project-name-light': !isDarkMode }"
          title="Click to rename"
        >
          {{ projectName }}
        </h6>
      </div>

      <nav class="nav">
        <button class="btn-undo" @click="undo" :disabled="isSaving">
          <svg  xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-return-left" viewBox="0 0 16 16">
              <path fill-rule="evenodd" d="M14.5 1.5a.5.5 0 0 1 .5.5v4.8a2.5 2.5 0 0 1-2.5 2.5H2.707l3.347 3.346a.5.5 0 0 1-.708.708l-4.2-4.2a.5.5 0 0 1 0-.708l4-4a.5.5 0 1 1 .708.708L2.707 8.3H12.5A1.5 1.5 0 0 0 14 6.8V2a.5.5 0 0 1 .5-.5"/>
          </svg>
          Undo
        </button>
        
        <button class="btn-save" @click="handleSave" :disabled="isSaving">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="currentColor" viewBox="0 0 16 16">
            <path d="M2 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H9.5a1 1 0 0 0-1 1v7.293l2.646-2.647a.5.5 0 0 1 .708.708l-3.5 3.5a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L7.5 9.293V2a2 2 0 0 1 2-2H14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h2.5a.5.5 0 0 1 0 1z"/>
          </svg>
          {{ isSaving ? 'Saving...' : 'Save' }}
        </button>

        <button class="btn-back" @click="handleBack">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-house" viewBox="0 0 16 16">
            <path d="M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM13 7.207V13.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5V7.207l5-5z"/>
          </svg>
          Home
        </button>

        <button class="btn-export" @click="handleExport">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="currentColor" viewBox="0 0 16 16">
            <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
            <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
          </svg>
          Export SRT
        </button>
      </nav>
    </header>

    <div class="container" :style="`grid-template-rows: calc(${100 - timelineHeightPct}% - 3px) 6px ${timelineHeightPct}%`">
      <div class="content" :style="`grid-template-columns: ${sidebarWidthPct}% ${100 - sidebarWidthPct}%`">
        <div class="sidebar">

          <!-- Track switcher: shown only if BOTH tracks exist -->
          <div v-if="hasOriginal && hasTranslation" class="track-switcher">
            <button
              class="track-btn"
              :class="{ active: activeSidebarTrack === 'tran' }"
              @click="activeSidebarTrack = 'tran'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" fill="currentColor" viewBox="0 0 16 16">
                <path d="M4.545 6.714 4.11 8H3l1.862-5h1.284L8 8H6.833l-.435-1.286zm1.634-.736L5.5 3.956h-.049l-.679 2.022z"/>
                <path d="M0 2a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v3h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-3H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h2.5v-2A2 2 0 0 1 6.5 6H9V2a1 1 0 0 0-1-1z"/>
              </svg>
              Translation
            </button>
            <button
              class="track-btn"
              :class="{ active: activeSidebarTrack === 'orig' }"
              @click="activeSidebarTrack = 'orig'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" fill="currentColor" viewBox="0 0 16 16">
                <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/>
                <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/>
              </svg>
              Original
            </button>
          </div>

          <!-- Badge when only one track exists -->
          <div v-else class="sidebar-track-badge" :class="activeSidebarTrack === 'tran' ? 'badge-tran' : 'badge-orig'">
            <svg v-if="activeSidebarTrack === 'tran'" xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="currentColor" viewBox="0 0 16 16">
              <path d="M4.545 6.714 4.11 8H3l1.862-5h1.284L8 8H6.833l-.435-1.286zm1.634-.736L5.5 3.956h-.049l-.679 2.022z"/>
              <path d="M0 2a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v3h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-3H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h2.5v-2A2 2 0 0 1 6.5 6H9V2a1 1 0 0 0-1-1z"/>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="currentColor" viewBox="0 0 16 16">
              <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/>
              <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/>
            </svg>
            {{ activeSidebarTrack === 'tran' ? 'Track 1 · Translation' : 'Track 2 · Original' }}
          </div>

          <div class="subtitles-scroll" ref="subtitlesScroll">

            <div class="subtitle-separator subtitle-separator--edge">
              <div class="separator-line"></div>
              <div class="separator-actions">
                <button class="btn-sep btn-add" @click.stop="addSubtitleAtStart">+ ADD</button>
                <button class="btn-sep btn-duplicate" @click.stop="duplicateSubtitleAtStart">⧉ DUPLICATE</button>
              </div>
              <div class="separator-line"></div>
            </div>

            <template v-for="(subtitle, index) in sidebarSubtitles" :key="index">
              <div
                class="subtitle-block"
                :class="{ 'subtitle-block-active': isSubtitleActive(index) }"
                @click="handleSidebarClick(index)"
              >
                <span class="timestamp">{{ subtitle.timestamp }}</span>
                <p class="testo">{{ subtitle.testo }}</p>
                <div class="block-actions">
                  <button class="btn-delete" @click.stop="deleteSubtitle(index)" title="Elimina sottotitolo">Delete</button>
                  <button class="btn-edit" @click.stop="openEditModal(index)">Edit</button>
                </div>
              </div>

              <div v-if="index < sidebarSubtitles.length - 1" class="subtitle-separator">
                <div class="separator-line"></div>
                <div class="separator-actions">
                  <button class="btn-sep btn-add" @click.stop="addSubtitleBetween(index)">+ ADD</button>
                  <button class="btn-sep btn-duplicate" @click.stop="duplicateSubtitleBetween(index)">⧉ DUPLICATE</button>
                  <button class="btn-sep btn-merge" @click.stop="mergeSubtitles(index)">⊕ MERGE</button>
                </div>
                <div class="separator-line"></div>
              </div>
            </template>

            <div class="subtitle-separator subtitle-separator--edge">
              <div class="separator-line"></div>
              <div class="separator-actions">
                <button class="btn-sep btn-add" @click.stop="addSubtitleAtEnd">+ ADD</button>
                <button class="btn-sep btn-duplicate" @click.stop="duplicateSubtitleAtEnd">⧉ DUPLICATE</button>
              </div>
              <div class="separator-line"></div>
            </div>

          </div>
        </div>

        <div class="resize-handle-v" @mousedown="startResizeSidebar"></div>

        <div class="video-area">
          <div class="video-box">
            <video ref="videoPlayer" v-if="videoUrl" :src="videoUrl" controls controlslist="nofullscreen nodownload" disablepictureinpicture></video>
            <div v-if="activeSubtitleText" class="subtitle-overlay">
              <span class="subtitle-text">{{ activeSubtitleText }}</span>
            </div>
          </div>
          <div class="video-commands">
            <svg @click="restartVideo" xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="currentColor" class="bi bi-skip-start-fill" viewBox="0 0 16 16"><path d="M4 4a.5.5 0 0 1 1 0v3.248l6.267-3.636c.54-.313 1.232.066 1.232.696v7.384c0 .63-.692 1.01-1.232.697L5 8.753V12a.5.5 0 0 1-1 0z"/></svg>
            <svg @click="togglePlay" v-if="!isPlaying" xmlns="http://www.w3.org/2000/svg" width="30" height="30" fill="currentColor" class="bi bi-play-fill" viewBox="0 0 16 16"><path d="m11.596 8.697-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393"/></svg>
            <svg @click="togglePlay" v-else xmlns="http://www.w3.org/2000/svg" width="30" height="30" fill="currentColor" class="bi bi-pause-fill" viewBox="0 0 16 16"><path d="M5.5 3.5A1.5 1.5 0 0 1 7 5v6a1.5 1.5 0 0 1-3 0V5a1.5 1.5 0 0 1 1.5-1.5m5 0A1.5 1.5 0 0 1 12 5v6a1.5 1.5 0 0 1-3 0V5a1.5 1.5 0 0 1 1.5-1.5"/></svg>
            <svg @click="endVideo" xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="currentColor" class="bi bi-skip-end-fill" viewBox="0 0 16 16"><path d="M12.5 4a.5.5 0 0 0-1 0v3.248L5.233 3.612C4.693 3.3 4 3.678 4 4.308v7.384c0 .63.692 1.01 1.233.697L11.5 8.753V12a.5.5 0 0 0 1 0z"/></svg>
            <span class="fullscreenSVG">
              <svg @click="toggleFullscreen"  xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-arrows-fullscreen" viewBox="0 0 16 16">
              <path fill-rule="evenodd" d="M5.828 10.172a.5.5 0 0 0-.707 0l-4.096 4.096V11.5a.5.5 0 0 0-1 0v3.975a.5.5 0 0 0 .5.5H4.5a.5.5 0 0 0 0-1H1.732l4.096-4.096a.5.5 0 0 0 0-.707m4.344 0a.5.5 0 0 1 .707 0l4.096 4.096V11.5a.5.5 1 1 1 1 0v3.975a.5.5 0 0 1-.5.5H11.5a.5.5 0 0 1 0-1h2.768l-4.096-4.096a.5.5 0 0 1 0-.707m0-4.344a.5.5 0 0 0 .707 0l4.096-4.096V4.5a.5.5 1 0 0 1 0V.525a.5.5 0 0 0-.5-.5H11.5a.5.5 0 0 0 0 1h2.768l-4.096 4.096a.5.5 0 0 0 0 .707m-4.344 0a.5.5 0 0 1-.707 0L1.025 1.732V4.5a.5.5 0 0 1-1 0V.525a.5.5 0 0 1 .5-.5H4.5a.5.5 0 0 1 0 1H1.732l4.096 4.096a.5.5 0 0 1 0 .707"/>
              </svg>
            </span> 
          </div>
        </div>
      </div>

      <div class="resize-handle-h" @mousedown="startResizeTimeline"></div>

      <div class="timeline">
        <div class="time-row">
          <div class="name zoomIcons">
          <svg @click="zoomOut" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-zoom-out" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M6.5 12a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11M13 6.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0"/><path d="M10.344 11.742q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1 6.5 6.5 0 0 1-1.398 1.4z"/><path fill-rule="evenodd" d="M3 6.5a.5.5 0 0 1 .5-.5h6a.5.5 0 0 1 0 1h-6a.5.5 0 0 1-.5-.5"/>
          </svg>
          <input
            type="range"
            class="zoom-slider"
            min="0.5"
            max="5"
            step="0.25"
            :value="zoomLevel"
            @input="onZoomSlider"
          />
          <svg @click="zoomIn" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-zoom-in" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M6.5 12a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11M13 6.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0"/><path d="M10.344 11.742q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1 6.5 6.5 0 0 1-1.398 1.4z"/><path fill-rule="evenodd" d="M6.5 3a.5.5 0 0 1 .5.5V6h2.5a.5.5 0 0 1 0 1H7v2.5a.5.5 0 0 1-1 0V7H3.5a.5.5 0 0 1 0-1H6V3.5a.5.5 0 0 1 .5-.5"/>
          </svg>
        </div>
          <div class="track">
            <subTimeline
              v-if="videoDuration > 0"
              :duration="videoDuration"
              :videoRef="videoPlayer"
              v-model:subtitles="subtitles"
              v-model:tranSubtitles="tranSubtitles"
              v-model:pixelsPerSecond="pixelsPerSecond"
              :activeTrack="activeSidebarTrack"
              :waveformHeight="waveformHeight"
              @update:activeTrack="activeSidebarTrack = $event"
            />
          </div>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h4>Edit Subtitle</h4>
          <button class="btn-close" @click="closeModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="timestamp">Timestamp</label>
            <input id="timestamp" v-model="editForm.timestamp" type="text" class="form-control" placeholder="00:00:01,000 --> 00:00:03,000" />
          </div>
          <div class="form-group">
            <label for="testo">Text</label>
            <textarea id="testo" v-model="editForm.testo" class="form-control" rows="4" placeholder="Inserisci il testo del sottotitolo"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeModal">Cancel</button>
          <button class="btn btn-primary" @click="saveEdit">Save</button>
        </div>
      </div>
    </div>
  </div>

  <!-- MODAL BLOCCANTE DROP VIDEO -->
  <div v-if="showVideoDropModal" class="video-drop-overlay">
    <div class="video-drop-box">
      <button class="video-drop-close" @click="() => { clearProjectStorage(); router.push('/myprojects') }" title="Back to projects">&times;</button>
      <div class="video-drop-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" viewBox="0 0 16 16">
          <path d="M6.79 5.093A.5.5 0 0 0 6 5.5v5a.5.5 0 0 0 .79.407l3.5-2.5a.5.5 0 0 0 0-.814l-3.5-2.5z"/>
          <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm15 0a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
        </svg>
      </div>
      <h2>Load your video</h2>
      <p>The video file is not stored on our servers.<br>Drop the original file to start editing.</p>
      <div v-if="expectedVideoName" class="expected-file-box">
        <small>Expected file:</small>
        <div class="file-name-badge">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16" style="margin-right: 6px;">
            <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0zM9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1zM11 8H5a.5.5 0 0 1 0-1h6a.5.5 0 0 1 0 1zm0 2H5a.5.5 0 0 1 0-1h6a.5.5 0 0 1 0 1zm-6 2h3a.5.5 0 0 1 0 1H5a.5.5 0 0 1 0-1z"/>
          </svg>
          {{ expectedVideoName }}
        </div>
      </div>
      <div
        class="video-drop-zone"
        :class="{ 'has-error': videoDropError }"
        @dragover.prevent
        @drop.prevent="handleVideoDropModal"
        @click="$refs.videoDropInput.click()"
      >
        <input ref="videoDropInput" type="file" accept="video/*" style="display:none" @change="handleVideoSelectModal" />
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" viewBox="0 0 16 16">
          <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
          <path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/>
        </svg>
        <span>Drop video here or click to browse</span>
      </div>
      <p v-if="videoDropError" class="video-drop-error">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" style="margin-right: 5px; vertical-align: text-bottom;">
          <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
          <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995z"/>
        </svg>
        {{ videoDropError }}
      </p>
    </div>
  </div>

  <!-- Modal conferma back -->
  <div v-if="showBackConfirm" class="modal-overlay">
    <div class="modal-content" style="max-width:380px; text-align:center;">
      <div class="modal-body" style="padding:2rem;">
        <h4 style="margin:0 0 12px 0; color:#f1f5f9;">Save before leaving?</h4>
        <p style="color:#64748b; font-size:0.9rem; margin:0 0 24px 0;">Do you want to save your changes before going back?</p>
        <div style="display:flex; gap:12px; justify-content:center;">
          <button class="btn btn-secondary" @click="confirmBackNoSave">Leave without saving</button>
          <button class="btn btn-primary" @click="confirmBackSave" :disabled="isSaving">
            {{ isSaving ? 'Saving...' : 'Save & Leave' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrapper { 
  min-height: 100vh; width: 100%; background-color: #1c2331; color: #fff;
  text-shadow: 0 0.05rem 0.1rem rgba(0, 0, 0, 0.5); display: grid;
  grid-template-rows: 55px 1fr; grid-template-areas: "header" "container"; overflow: hidden;
}
.header { grid-area: header; background-color: #1c2331; height: 50px; }
.logo {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #f8f9fa;
}
.nav { display: flex; gap: 1rem; }

.btn-save {
  display: flex; align-items: center; gap: 6px; padding: 6px 18px;
  background: #3b82f6; color: #f8f9fa; border: none; border-radius: 5px;
  font-weight: 700; font-size: 0.9rem; cursor: pointer; transition: all 0.2s ease; letter-spacing: 0.03em;
}
.btn-save:hover { background: #3b82f6; transform: translateY(-1px); box-shadow: 0 4px 10px rgba(31, 118, 240, 0.4); }
.btn-save:active { transform: translateY(0); }

.container {
  grid-area: container; display: grid; grid-template-rows: 65% 35%;
  min-width: 100%; height: calc(100vh);; overflow: hidden; gap: 0;
}
.content {
  background-color: #1c2331;
  display: flex;          
  width: 100%;
  overflow: hidden;
  height: 100%;
  align-items: stretch;
  max-height: 100%;
}

.sidebar { flex: 0 0 v-bind(sidebarWidthPct + '%'); background-color: #1c2331; display: flex; flex-direction: column; overflow: hidden; height: 100%; }

/* Track switcher (shown when both tracks exist) */
.track-switcher {
  display: flex; flex-shrink: 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.track-btn {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 5px;
  padding: 7px 8px; background: transparent; border: none; border-bottom: 2px solid transparent;
  color: #555; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; cursor: pointer; transition: all 0.2s ease;
}
.track-btn:hover { color: #94a3b8; background: rgba(255,255,255,0.04); }
.track-btn.active { color: rgba(31, 125, 240, 0.918); border-bottom-color: rgba(31, 125, 240, 0.918); background: rgba(31, 125, 240, 0.07); }
.track-btn:last-child.active { color: #8e49a0; border-bottom-color: #8e49a0; background: rgba(0, 204, 153, 0.07); }

.sidebar-track-badge {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
  flex-shrink: 0; border-bottom: 1px solid rgba(255,255,255,0.06);
}

.expected-file-box {
  margin-bottom: 20px; background: rgba(74, 144, 226, 0.1);
  padding: 10px; border-radius: 8px; border: 1px dashed #4a90e2;
}
.expected-file-box small { display: block; color: #b0b0b0; margin-bottom: 4px; }

.video-drop-close {
  position: absolute; top: 16px; right: 16px; background: transparent;
  border: 1px solid #2d3748; color: #64748b; border-radius: 6px; width: 32px; height: 32px;
  font-size: 1.2rem; cursor: pointer; display: flex; align-items: center; justify-content: center;
  line-height: 1; transition: all 0.2s ease;
}
.video-drop-close:hover { border-color: #4a5568; color: #e2e8f0; background: rgba(255, 255, 255, 0.05); }

.file-name-badge { color: #4a90e2; font-weight: 600; font-family: monospace; word-break: break-all; }

.video-drop-error {
  color: #ff4d4d; background: rgba(255, 77, 77, 0.1); padding: 10px;
  border-radius: 6px; margin-top: 15px; font-size: 0.9rem; border-left: 4px solid #ff4d4d;
}
.video-drop-zone.has-error { border-color: #ff4d4d !important; background: rgba(255, 77, 77, 0.05) !important; color: #ff4d4d; }

.btn-export {
  display: flex; align-items: center; gap: 6px; padding: 6px 18px;
  background: rgba(59, 131, 246, 0.2); color: #3b82f6; border: 1px solid #3b82f6;
  border-radius: 5px; font-weight: 700; font-size: 0.9rem; cursor: pointer;
  transition: all 0.2s ease; letter-spacing: 0.03em;
}
.btn-export:hover { background: rgba(59, 131, 246, 0.42); color: #fff; border-color: #3b82f6; transform: translateY(-1px); box-shadow: 0 4px 10px rgba(0, 79, 170, 0.3); }

.badge-tran { color: rgba(31, 125, 240, 0.918); background: rgba(31, 125, 240, 0.12); }
.badge-orig { color: #713481; background: rgba(0, 170, 140, 0.12); }

.subtitles-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; padding-right: 0.5rem; min-height: 0; scroll-behavior: smooth; }

.subtitle-block {
  display: flex; flex-direction: column; padding: 0.3px; margin-bottom: 0;
  background: #151a24; border-left: 4px solid #3b82f6;
  border-radius: 4px; transition: all 0.3s ease; cursor: pointer;
}
.badge-orig ~ .subtitles-scroll .subtitle-block { border-left-color: #00aa8c; }
.subtitle-block:hover { background: #353841; }
.subtitle-block-active { background: #3a4a5a !important; box-shadow: 0 0 8px #3b82f6; transform: scale(1.02); border-radius: 4px; }

.timestamp { display: block; font-weight: bold; color: #dddcdc; font-size: 0.85rem; margin-bottom: 4px; margin-left: 5px; flex-shrink: 0; }
.subtitle-block-active .timestamp { color: #ffffff;}
.testo { margin: 0 0 6px 5px; color: #fff; line-height: 1.4; font-size: 0.9rem; word-break: break-word; white-space: pre-line; }
.block-actions { display: flex; justify-content: flex-end; gap: 6px; flex-shrink: 0; margin-top: 2px; }
.btn-delete, .btn-edit { padding: 3px 10px; border: none; border-radius: 4px; font-size: 0.72rem; font-weight: 600; cursor: pointer; transition: all 0.2s ease; line-height: 1.5; }
.btn-delete { background: rgba(255, 0, 0, 0.549); color: #ffd5d5; }
.btn-delete:hover { background: rgba(210, 40, 40, 1); color: #fff; transform: translateY(-1px); }
.btn-edit { background: #37474f ;color: #ffffff; }
.btn-edit:hover { background: #455a64; color: #fff; transform: translateY(-1px); }
.subtitle-block-active .btn-edit { background: #263136; color: #fff; }
.subtitle-block-active .btn-edit:hover { background: #455a64; color: #fff; }

.subtitle-separator { display: flex; align-items: center; gap: 6px; padding: 2px 4px; opacity: 0.6; transition: opacity 0.2s ease; }
.subtitle-separator:hover { opacity: 1; }
.separator-line { flex: 1; height: 1px; background: rgba(255, 255, 255, 0.12); }
.separator-actions { display: flex; gap: 4px; flex-shrink: 0; }
.btn-sep { padding: 1px 8px; font-size: 0.68rem; font-weight: 600; border: none; border-radius: 3px; cursor: pointer; line-height: 1.6; letter-spacing: 0.02em; transition: all 0.15s ease; white-space: nowrap; }
.btn-add { background: rgba(49, 57, 65, 0.5); color: #fafafa; border: 1px solid rgba(31, 125, 240, 0.918); }
.btn-add:hover { background: rgba(49, 57, 65, 0.9); color: #fff; box-shadow: 0 2px 6px rgba(31, 125, 240, 0.4); }
.btn-duplicate { background: rgba(49, 57, 65, 0.5); color: #fafafa; border: 1px solid rgba(139, 92, 246, 0.6); }
.btn-duplicate:hover { background: rgba(49, 57, 65, 0.8); color: #fff; box-shadow: 0 2px 6px rgba(139, 92, 246, 0.4); }
.btn-merge { background: rgba(49, 57, 65, 0.4); color: #fafafa; border: 1px solid rgba(0, 204, 153, 0.55); }
.btn-merge:hover { background: rgba(49, 57, 65, 0.8); color: #fff; box-shadow: 0 2px 6px rgba(0, 204, 153, 0.4); }

.video-area { flex: 1;background-color: #1c2331; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; overflow: hidden; }
.video-box { width: 90%; height: 90%; max-height: 90%; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.video-box video { width: 100%; height: 100%; max-width: 100%; max-height: 100%; display: block; object-fit: contain; }
/* Fullscreen: the video-box becomes the fullscreen root */
.video-box:fullscreen {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  width: 100vw;
  height: 100vh;
}

.video-box:fullscreen video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-box:fullscreen .subtitle-overlay {
  position: fixed;
  bottom: 48px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2147483647;
  pointer-events: none;
}

.video-box:fullscreen .subtitle-text {
  font-size: 1.4rem;
  padding: 10px 24px;
}
.subtitle-overlay { position: absolute; bottom: 35px; left: 50%; transform: translateX(-50%); max-width: 80%; text-align: center; pointer-events: none; z-index: 10; }
.subtitle-text { display: inline-block; background: rgba(0, 0, 0, 0.8); color: #fff; padding: 8px 16px; border-radius: 4px; font-size: 0.9rem; line-height: 1.4; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5); backdrop-filter: blur(4px); white-space: pre-line; }
.timeline { background-color: #171819; overflow-x: auto; overflow-y: hidden; z-index: 1; }
.zoomIcons { cursor: pointer; background-color: #19202d;}
.fullscreenSVG{
  position: absolute;
  right: 60px;
}

.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
.modal-content { background: #2a2d31; border-radius: 8px; width: 90%; max-width: 600px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5); }
.modal-header { padding: 1.5rem; border-bottom: 1px solid #3a3d41; display: flex; justify-content: space-between; align-items: center; }
.modal-header h4 { margin: 0; color: rgba(31, 125, 240, 0.918); }
.btn-close { background: none; border: none; color: #fff; font-size: 2rem; cursor: pointer; line-height: 1; padding: 0; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease; }
.btn-close:hover { color: rgba(31, 125, 240, 0.918); transform: rotate(90deg); }
.modal-body { padding: 1.5rem; }
.form-group { margin-bottom: 1.5rem; }
.form-group label { display: block; margin-bottom: 0.5rem; color: rgba(31, 125, 240, 0.918); font-weight: bold; font-size: 0.9rem; }
.form-control { width: 100%; padding: 0.75rem; background: #1a1d21; border: 1px solid #3a3d41; border-radius: 4px; color: #fff; font-size: 0.9rem; font-family: inherit; transition: all 0.2s ease; }
.form-control:focus { outline: none; border-color: rgba(31, 125, 240, 0.918); box-shadow: 0 0 0 3px rgba(31, 125, 240, 0.2); }
textarea.form-control { resize: vertical; min-height: 100px; }
.modal-footer { padding: 1.5rem; border-top: 1px solid #3a3d41; display: flex; justify-content: flex-end; gap: 1rem; }
.btn { padding: 0.5rem 1.5rem; border: none; border-radius: 4px; font-size: 0.9rem; font-weight: bold; cursor: pointer; transition: all 0.2s ease; }
.btn-secondary { background: #3a3d41; color: #fff; }
.btn-secondary:hover { background: #4a4d51; }
.btn-primary { background: rgba(31, 125, 240, 0.918); color: #fff; }
.btn-primary:hover { background: rgba(31, 125, 240, 1); transform: translateY(-1px); box-shadow: 0 4px 8px rgba(31, 125, 240, 0.3); }

.btn-theme {
  display: flex; align-items: center; gap: 6px; padding: 6px 18px;
  background: transparent; color: #94a3b8; border: 1px solid #2d3748; border-radius: 5px;
  font-weight: 700; font-size: 0.9rem; cursor: pointer; transition: all 0.2s ease; letter-spacing: 0.03em;
}
.btn-theme:hover { border-color: #4a5568; color: #e2e8f0; }

.project-name {
  margin: 0;
  color: #94a3b8;
  font-size: 0.85rem;
  cursor: pointer;
}

.project-name-light {
  color: #1e293b !important;
}
.video-drop-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.92);
  display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(6px);
}
.video-drop-box {
  background: #1e2128; border: 1px solid #2d3748; border-radius: 16px;
  padding: 48px 40px; max-width: 480px; width: 90%; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 16px; position: relative;
}
.video-drop-icon { color: rgba(31, 125, 240, 0.918); }
.video-drop-box h2 { margin: 0; font-size: 1.5rem; color: #f1f5f9; font-weight: 700; }
.video-drop-box p { margin: 0; font-size: 0.9rem; color: #64748b; line-height: 1.6; }
.video-drop-zone {
  width: 100%; border: 2px dashed #2d3748; border-radius: 12px; padding: 36px 20px;
  cursor: pointer; transition: all 0.2s; background: #0f1117;
  display: flex; flex-direction: column; align-items: center; gap: 12px; color: #475569; margin-top: 8px;
}
.video-drop-zone:hover { border-color: rgba(31, 125, 240, 0.918); background: rgba(31, 125, 240, 0.06); color: #93c5fd; }
.video-drop-zone span { font-size: 0.9rem; font-weight: 500; }
.video-drop-error { color: #f87171; font-size: 0.85rem; margin: 0; }

.btn-back {
  display: flex; align-items: center; gap: 6px; padding: 6px 18px;
  background: transparent; color: #94a3b8; border: 1px ; border-radius: 5px;
  font-weight: 700; font-size: 0.9rem; cursor: pointer; transition: all 0.2s ease; letter-spacing: 0.03em;
}
.btn-back:hover { border-color: #4a5568; color: #e2e8f0; }

.btn-undo {
  display: flex; align-items: center; gap: 6px; padding: 6px 18px;
  background: transparent; color: #3b82f6; border: 1px solid #3b82f6; border-radius: 5px;
  font-weight: 700; font-size: 0.9rem; cursor: pointer; transition: all 0.2s ease; letter-spacing: 0.03em;
}
.btn-undo:hover { border-color: #2f7af4; color: #2f7af4; }

.resize-handle-h {
  height: 6px;
  cursor: ns-resize;
  background: transparent;
  position: relative;
  z-index: 10;
  flex-shrink: 0;
  transition: background 0.15s;
}
.resize-handle-h::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 40px;
  height: 3px;
  border-radius: 2px;
  background: rgba(255,255,255,0.15);
  transition: background 0.15s;
}
.resize-handle-h:hover,
.resize-handle-h:active {
  background: rgba(31, 125, 240, 0.15);
}
.resize-handle-h:hover::after,
.resize-handle-h:active::after {
  background: rgba(31, 125, 240, 0.8);
}

.resize-handle-v {
  width: 6px;
  cursor: ew-resize;
  background: transparent;
  position: relative;
  z-index: 10;
  flex-shrink: 0;
  transition: background 0.15s;
}
.resize-handle-v::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 3px;
  height: 40px;
  border-radius: 2px;
  background: rgba(255,255,255,0.15);
  transition: background 0.15s;
}
.resize-handle-v:hover,
.resize-handle-v:active {
  background: rgba(31, 125, 240, 0.15);
}
.resize-handle-v:hover::after,
.resize-handle-v:active::after {
  background: rgba(31, 125, 240, 0.8);
}

.zoom-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 120px;
  height: 4px;
  border-radius: 2px;
  background: #2d3748;
  outline: none;
  cursor: pointer;
  transition: background 0.2s;
}
.zoom-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  box-shadow: 0 0 4px rgba(59, 130, 246, 0.5);
  transition: background 0.2s, box-shadow 0.2s;
}
.zoom-slider::-webkit-slider-thumb:hover {
  background: #60a5fa;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.7);
}
.zoom-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: none;
}
:deep(video::-webkit-media-controls-fullscreen-button) {
  display: none;
}
:deep(video::-webkit-media-controls-picture-in-picture-button) {
  display: none;
}
</style>