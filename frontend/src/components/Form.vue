<template>
  <div class="project-form-container">
    <div class="main-form">
        <h1>Create your project now!</h1>
      <p>Project name</p>
      <div class="form-floating mb-3">
        <input type="text" class="form-control" placeholder="My project" v-model="projectName">
        <label>My project</label>
      </div>
      <p>Insert video source</p>
      <div class="dropzone" @dragover.prevent @drop.prevent="handleDrop" @click="$refs.videoDropInput.click()">
        <input
          type="file"
          ref="videoDropInput"
          accept="video/*"
          style="display: none"
          @change="handleFileInput"
        />
        <p v-if="!videoFile">Drop your video source here or <span class="browse-link">browse</span></p>
        <p v-else>Selected file: {{ videoFile.name }}</p>
      </div>

      <!-- Switch slider -->
      <div class="srt-toggle-row">
        <span class="srt-toggle-label" :class="{ active: !srtMode }">Auto generate subtitles</span>
        <label class="switch">
          <input type="checkbox" v-model="srtMode" />
          <span class="slider round"></span>
        </label>
        <span class="srt-toggle-label" :class="{ active: srtMode }">Upload SRT files</span>
      </div>

      <!-- AUTO MODE: language selects -->
      <div v-if="!srtMode">
        <p>Source language</p>
        <select class="form-select mb-3" v-model="sourceLanguage">
          <option value="auto" v-if="!isAzureMode" selected="selected">[Auto-detect]</option>
          <option value="" v-else>[Select source language]</option>
          <option value="de">German</option>
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="it">Italian</option>
        </select>
        <p>Target language</p>
        <select class="form-select mb-3" v-model="targetLanguage">
          <option value="">[Select the language]</option>
          <option value="de">German</option>
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="it">Italian</option>
        </select>
      </div>

      <!-- SRT MODE: dropzones -->
      <div v-else>
        <p>Source language SRT </p>
        <div
          class="dropzone srt-dropzone"
          :class="{ 'has-file': srtSourceFile }"
          @dragover.prevent
          @drop.prevent="handleSrtDrop($event, 'source')"
          @click="$refs.srtSourceInput.click()"
        >
          <input
            type="file"
            ref="srtSourceInput"
            accept=".srt"
            style="display: none"
            @change="handleSrtInput($event, 'source')"
          />
          <span class="srt-icon">📄</span>
          <p v-if="!srtSourceFile">Drop source <strong>.srt</strong> file here or <span class="browse-link">browse</span></p>
          <p v-else>✓ {{ srtSourceFile.name }}</p>
        </div>

        <p>Target language SRT</p>
        <div
          class="dropzone srt-dropzone"
          :class="{ 'has-file': srtTargetFile }"
          @dragover.prevent
          @drop.prevent="handleSrtDrop($event, 'target')"
          @click="$refs.srtTargetInput.click()"
        >
          <input
            type="file"
            ref="srtTargetInput"
            accept=".srt"
            style="display: none"
            @change="handleSrtInput($event, 'target')"
          />
          <span class="srt-icon">📄</span>
          <p v-if="!srtTargetFile">Drop target <strong>.srt</strong> file here or <span class="browse-link">browse</span></p>
          <p v-else>✓ {{ srtTargetFile.name }}</p>
        </div>
      </div>

      <button class="btn btn-lg btn-light fw-bold" @click="handleCreate">Create</button>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="progress-container">
        <h2>Processing your video...</h2>
        
        <div class="progress-section">
          <div class="progress-label">
            <span>Transcribing</span>
            <span class="progress-percent">{{ transcribingProgress }}%</span>
          </div>
          <div class="progress-bar-wrapper">
            <div class="progress-bar" :style="{ width: transcribingProgress + '%' }"></div>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-label">
            <span>Translating</span>
            <span class="progress-percent">{{ translatingProgress }}%</span>
          </div>
          <div class="progress-bar-wrapper">
            <div class="progress-bar" :style="{ width: translatingProgress + '%' }"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const props = defineProps({
  userId: {
    type: Number,
    required: true
  }
})

const targetLanguage = ref('');
const router = useRouter()
let loading = ref(false)
const videoFile = ref(null)
const projectName = ref('')
let subtitles = []
let tranSubtitles = []

const transcribingProgress = ref(0)
const translatingProgress = ref(0)

// SRT mode toggle
const srtMode = ref(false)
const srtSourceFile = ref(null)
const srtTargetFile = ref(null)

const envValue = import.meta.env.VITE_REQUIRE_SOURCE_LANG
const isAzureMode = computed(() => envValue === 'true')
const sourceLanguage = ref(isAzureMode.value ? "" : "auto")

const WHISPER_BASE = import.meta.env.VITE_WHISPER_BASE;
const WHISPER_TOKEN = import.meta.env.VITE_WHISPER_TOKEN || '';

const SERVICE_BASE = import.meta.env.VITE_SERVICE_BASE || 'https://api.matita.net/subtitles-admin'

const endpointPost       = import.meta.env.VITE_ENDPOINT_POST       || '/conversion-start';
const endpointStatus     = import.meta.env.VITE_ENDPOINT_STATUS     || '/conversion-status';
const endpointOut        = import.meta.env.VITE_ENDPOINT_OUT        || '/conversion-out';
const endpointTranslated = import.meta.env.VITE_ENDPOINT_TRANSLATED || '/conversion-translated';

const apiConversionPost       = `${WHISPER_BASE}${endpointPost}`;
const apiConversionStatus     = `${WHISPER_BASE}${endpointStatus}`;
const apiConversionOut        = `${WHISPER_BASE}${endpointOut}`;
const apiConversionTranslated = `${WHISPER_BASE}${endpointTranslated}`;

const apiAudioPost   = `${WHISPER_BASE}/audio-extraction-start`;
const apiAudioStatus = `${WHISPER_BASE}/audio-extraction-status`; 
const apiAudioGet    = `${WHISPER_BASE}/audio-extraction-out`;


const tokenBearer = `Bearer ${WHISPER_TOKEN}`;

const apiAdmin = axios.create({ baseURL: SERVICE_BASE })

apiAdmin.interceptors.request.use((config) => {
  const token = localStorage.getItem('subtitles_token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

apiAdmin.interceptors.response.use(
  (response) => {
    const refreshed = response.headers['x-refresh-token']
    if (refreshed) {
      localStorage.setItem('subtitles_token', refreshed)
    }
    return response
  },
  (error) => Promise.reject(error)
)

function isLogged() {
  return localStorage.getItem('isLogged') === 'true'
}

onMounted(() => {
  const pending = localStorage.getItem('pendingProject')
  if (pending && isLogged()) {
    const { savedProjectName, savedTargetLanguage } = JSON.parse(pending)
    projectName.value = savedProjectName || ''
    targetLanguage.value = savedTargetLanguage || ''
    localStorage.removeItem('pendingProject')
  }
})

function handleDrop(event) {
  const files = event.dataTransfer.files
  if (files.length > 0 && files[0].type.startsWith('video/')) {
    videoFile.value = files[0]
  } else {
    alert('Per favore trascina un file video valido.')
  }
}

function handleFileInput(event) {
  const files = event.target.files
  if (files.length > 0) {
    videoFile.value = files[0]
  }
}

// SRT drag & drop handlers
function handleSrtDrop(event, type) {
  const files = event.dataTransfer.files
  if (files.length > 0 && files[0].name.endsWith('.srt')) {
    if (type === 'source') srtSourceFile.value = files[0]
    else srtTargetFile.value = files[0]
  } else {
    alert('Per favore trascina un file .srt valido.')
  }
}

function handleSrtInput(event, type) {
  const files = event.target.files
  if (files.length > 0) {
    if (type === 'source') srtSourceFile.value = files[0]
    else srtTargetFile.value = files[0]
  }
}

// Parse SRT text into subtitles array
function parseSrt(srtText) {
  const blocchi = srtText.trim().split(/\r?\n\r?\n/)
  return blocchi.map(blocco => {
    const righe = blocco.split(/\r?\n/)
    if (righe.length >= 3) {
      return { timestamp: righe[1], testo: righe.slice(2).join('\n') }
    }
    return null
  }).filter(item => item !== null)
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = e => resolve(e.target.result)
    reader.onerror = () => reject(new Error('Errore lettura file'))
    reader.readAsText(file)
  })
}

function handleCreate() {
  if (srtMode.value) {
    // SRT mode: at least one file required
    if (!srtSourceFile.value && !srtTargetFile.value) {
      alert('Carica almeno un file SRT.')
      return
    }
    if (!projectName.value.trim()) {
      alert('Inserisci il nome del progetto.')
      return
    }
    if (!videoFile.value) {
      alert('Carica il file video.')
      return
    }
    if (!isLogged()) {
      localStorage.setItem('pendingProject', JSON.stringify({
        savedProjectName: projectName.value,
        savedTargetLanguage: targetLanguage.value,
        redirectAfterLogin: '/'
      }))
      router.push('/login')
      return
    }
    createProjectFromSrt()
    return
  }

  // Auto mode (original logic)
  if (!targetLanguage.value) {
    alert('Seleziona la lingua di destinazione.');
    return;
  }
  if (isAzureMode.value && !sourceLanguage.value) {
    alert('Seleziona la lingua sorgente.');
    return;
  }

  if (!isLogged()) {
    localStorage.setItem('pendingProject', JSON.stringify({
      savedProjectName: projectName.value,
      savedTargetLanguage: targetLanguage.value,
      redirectAfterLogin: '/'
    }))
    router.push('/login')
    return
  }
  createProject()
}

async function createProjectFromSrt() {
  try {
    loading.value = true

    let srt2 = '' // source SRT raw text
    let srt1 = '' // target SRT raw text

    if (srtSourceFile.value) {
      srt2 = await readFileAsText(srtSourceFile.value)
      subtitles = parseSrt(srt2)
      console.log('[NewProject SRT] Source subtitles parsed:', subtitles.length, 'blocchi')
    }

    if (srtTargetFile.value) {
      srt1 = await readFileAsText(srtTargetFile.value)
      tranSubtitles = parseSrt(srt1)
      console.log('[NewProject SRT] Target subtitles parsed:', tranSubtitles.length, 'blocchi')
    }

    const now = new Date().toISOString()
    const projectRes = await apiAdmin.post('/projects', {
      name: projectName.value,
      data: JSON.stringify({
        srt1,
        srt2,
        playhead: 0,
        videoName: videoFile.value.name,
        created_at: now,
        last_saved: now
      })
    })

    const createdProject = projectRes.data
    console.log('[NewProject SRT] Progetto salvato:', createdProject)

    loading.value = false

    localStorage.setItem('subtitles', JSON.stringify(subtitles))
    localStorage.setItem('tranSubtitles', JSON.stringify(tranSubtitles))
    localStorage.setItem('currentProjectId', createdProject.id)
    localStorage.setItem('currentProjectName', createdProject.name)
    localStorage.setItem('currentProjectUserId', createdProject.user_id)

    router.push({
      name: 'video-player',
      state: {
        videoFile: videoFile.value,
        project: createdProject,
        subtitles: subtitles,
        tranSubtitles: tranSubtitles
      }
    })

  } catch (error) {
    console.error('[NewProject SRT] Errore:', error.message)
    loading.value = false
    alert(`Errore: ${error.message}`)
  }
}

async function createProject() {
  if (!videoFile.value || !projectName.value.trim()) {
    alert('Controlla i campi obbligatori.');
    return;
  }

  try {
    loading.value = true;
    transcribingProgress.value = 0;
    translatingProgress.value = 0;

    console.log('[NewProject] Avvio creazione progetto:', {
      projectName: projectName.value,
      targetLanguage: targetLanguage.value,
      sourceLanguage: sourceLanguage.value,
      videoFile: videoFile.value?.name,
      videoSize: `${(videoFile.value?.size / 1024 / 1024).toFixed(2)} MB`,
      isAzureMode: isAzureMode.value,
      apiConversionPost
    });

    const params = {};
    if (targetLanguage.value) {
      params.target = targetLanguage.value;
    }
    if (isAzureMode.value) {
      params.source = sourceLanguage.value;
    }

    let audiofile = null;

    if (isAzureMode.value) {
      const audioFormData = new FormData();
      audioFormData.append('file', videoFile.value);

      const conversionToAudio = await axios.post(apiAudioPost, audioFormData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      const audioId = conversionToAudio.data.id;

      const maxAttemptsAudio = 3000;
      const pollIntervalAudio = 1000;
      let conversionCompletedAudio = false;
      let lastTokenRefreshAudio = Date.now();

      for (let attempt = 1; attempt <= maxAttemptsAudio; attempt++) {
        const statusResponseAudio = await axios.get(`${apiAudioStatus}?id=${audioId}`)

        if (Date.now() - lastTokenRefreshAudio > 10 * 60 * 1000) {
          try {
            await apiAdmin.get('/me');
            lastTokenRefreshAudio = Date.now();
            console.log('[NewProject] Token matita aggiornato (audio)');
          } catch (e) {
            console.warn('[NewProject] Keep-alive token fallito (audio):', e.message);
          }
        }

        const { state, error, stage, progress } = statusResponseAudio.data;
        console.log(`[NewProject] Audio Poll #${attempt} - status: "${state}" | stage: "${stage}" | progress: ${progress ?? 'n/a'}`);

        if (state === 'completed') {
          conversionCompletedAudio = true;
          console.log('[NewProject] Conversione Audio completata!');
          break;
        }

        if (state === 'failed' || status === 'error') {
          console.error('[NewProject] Conversione Audio fallita. Errore server:', error);
          throw new Error(error || 'Conversione audio fallita');
        }

        await new Promise(resolve => setTimeout(resolve, pollIntervalAudio));
      }

      if (!conversionCompletedAudio) {
        throw new Error('Timeout: conversione audio non completata');
      }

      audiofile = await axios.get(`${apiAudioGet}?id=${audioId}`, {
        responseType: 'blob'
      });

      console.log('[NewProject] Audio estratto:', audiofile.data);
    }

    const formData = new FormData();
    if (isAzureMode.value) {
      formData.append('audiofile', audiofile.data, 'audio.wav');
      formData.append('source', params.source);
      formData.append('target', params.target);
    } else {
      formData.append('file', videoFile.value);
    }

    console.log('[NewProject] Invio a:', apiConversionPost, '| Params:', params);

    const conversionJob = await axios.post(apiConversionPost, formData, {
      headers: {
        ...(isAzureMode.value ? {} : { 'Authorization': tokenBearer }),
        'Content-Type': 'multipart/form-data'
      },
      params
    });

    const jobId = isAzureMode.value
      ? conversionJob.data.data.id
      : conversionJob.data.id;
    
    console.log('[NewProject] Job avviato, ID:', jobId, '| Risposta completa:', conversionJob.data);

    const maxAttempts = 3000;
    const pollInterval = 1000;
    let conversionCompleted = false;
    let lastTokenRefresh = Date.now();

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
  const statusResponse = await axios.get(`${apiConversionStatus}?id=${jobId}`, {
    headers: isAzureMode.value ? {} : { 'Authorization': tokenBearer }
  });

  if (Date.now() - lastTokenRefresh > 10 * 60 * 1000) {
    try {
      await apiAdmin.get('/me');
      lastTokenRefresh = Date.now();
      console.log('[NewProject] Token matita aggiornato');
    } catch (e) {
      console.warn('[NewProject] Keep-alive token fallito:', e.message);
    }
  }

    const responseData = isAzureMode.value
    ? statusResponse.data.data
    : statusResponse.data;
  

  if (isAzureMode.value) {
    const { id, state, stage, progress} = responseData;
    console.log(`[NewProject] Poll #${attempt} - state: "${state}" | id: ${id} | stage: "${stage}" | progress: ${progress ?? 'n/a'}`);

    if (stage === 'transcribing') {
      transcribingProgress.value = Math.trunc(progress || 0);
    } else if (stage === 'translating') {
      transcribingProgress.value = 100;
      translatingProgress.value = Math.trunc(progress || 0);
    }

    if (state === 'ready') {
      transcribingProgress.value = 100;
      translatingProgress.value = 100;
      conversionCompleted = true;
      console.log('[NewProject] Conversione completata!');
      break;
    }

    if (state === 'fail' || state === 'unknown') {
      console.error('[NewProject] Conversione fallita. State:', state);
      throw new Error(`Conversione fallita: ${state}`);
    }

  } else {
    const { status, error, stage, progress } = responseData;
    console.log(`[NewProject] Poll #${attempt} - status: "${status}" | stage: "${stage}" | progress: ${progress ?? 'n/a'}`);

    if (stage === 'transcribing') {
      transcribingProgress.value = Math.trunc(progress || 0);
    } else if (stage === 'translating') {
      transcribingProgress.value = 100;
      translatingProgress.value = Math.trunc(progress || 0);
    }

    if (status === 'completed') {
      transcribingProgress.value = 100;
      translatingProgress.value = 100;
      conversionCompleted = true;
      console.log('[NewProject] Conversione completata!');
      break;
    }

    if (status === 'failed' || status === 'error') {
      console.error('[NewProject] Conversione fallita. Errore server:', error);
      throw new Error(error || 'Conversione fallita');
    }
  }

  await new Promise(resolve => setTimeout(resolve, pollInterval)); 
}

    if (!conversionCompleted) {
      console.error('[NewProject] Timeout raggiunto dopo', maxAttempts, 'tentativi');
      throw new Error('Timeout: conversione non completata');
    }

    if (!isAzureMode.value) {
      try {
        const sourceResponse = await axios.get(
          `${WHISPER_BASE}/conversion-lang?id=${jobId}`,
          { headers: { 'Authorization': tokenBearer } }
        );
        sourceLanguage.value = sourceResponse.data;
        console.log('[NewProject] Lingua sorgente rilevata:', sourceLanguage.value);
      } catch (e) {
        console.warn('[NewProject] Impossibile recuperare la lingua sorgente:', e.message);
      }
    }

    console.log('[NewProject] Recupero SRT originale da:', `${apiConversionOut}?id=${jobId}`);
    const originalResponse = await axios.get(`${apiConversionOut}?id=${jobId}`, {
      headers: isAzureMode.value ? {} : { 'Authorization': tokenBearer }
    });

    const rawOriginal = originalResponse.data;

        console.log('[NewProject] Recupero SRT tradotto da:', `${apiConversionTranslated}?id=${jobId}`);
        const translatedResponse = await axios.get(`${apiConversionTranslated}?id=${jobId}`, {
          headers: isAzureMode.value ? {} : { 'Authorization': tokenBearer }
        });
        const rawTranslated = translatedResponse.data;

        // Azure restituisce i due SRT invertiti, quindi li swappiamo
        const srt2 = isAzureMode.value ? rawTranslated : rawOriginal;
        const srt1 = isAzureMode.value ? rawOriginal   : rawTranslated;

        const blocchiOriginal = srt2.trim().split(/\r?\n\r?\n/);
          subtitles = blocchiOriginal.map(blocco => {
          const righe = blocco.split(/\r?\n/);
          if (righe.length >= 3) {
            return { timestamp: righe[1], testo: righe.slice(2).join('\n') };
          }
          return null;
        }).filter(item => item !== null);

        console.log(`[NewProject] SRT originale: ...`)

    const blocchiTradotti = srt1.trim().split(/\r?\n\r?\n/);
    tranSubtitles = blocchiTradotti.map(blocco => {
      const righe = blocco.split(/\r?\n/);
      if (righe.length >= 3) {
        return { timestamp: righe[1], testo: righe.slice(2).join('\n') };
      }
      return null;
    }).filter(item => item !== null);

    console.log(`[NewProject] SRT tradotto: ${tranSubtitles.length} blocchi. Primi 2:`, tranSubtitles.slice(0, 2));

    console.log('[NewProject] Salvataggio progetto su API admin...');
    const now = new Date().toISOString();
    const projectRes = await apiAdmin.post('/projects', {
        name: projectName.value,
        data: JSON.stringify({ 
          srt1, 
          srt2, 
          playhead: 0, 
          videoName: videoFile.value.name,
          sourceLanguage: sourceLanguage.value,
          targetLanguage: targetLanguage.value,
          created_at: now,
          last_saved: now
        })
      });

    const createdProject = projectRes.data;
    console.log('[NewProject] Progetto salvato:', createdProject);

    loading.value = false;

    localStorage.setItem('subtitles', JSON.stringify(subtitles))
    localStorage.setItem('tranSubtitles', JSON.stringify(tranSubtitles))
    localStorage.setItem('currentProjectId', createdProject.id)
    localStorage.setItem('currentProjectName', createdProject.name)
    localStorage.setItem('currentProjectUserId', createdProject.user_id)

    console.log('[NewProject] Redirect a video-player con progetto ID:', createdProject.id);

    router.push({
      name: 'video-player',
      state: {
        videoFile: videoFile.value,
        project: createdProject,
        subtitles: subtitles,
        tranSubtitles: tranSubtitles
      }
    });

  } catch (error) {
    console.error('[NewProject] Errore durante la creazione:', error.message);
    console.error('[NewProject] Response status:', error.response?.status);
    console.error('[NewProject] Response data:', error.response?.data);
    console.error('[NewProject] Stack trace:', error.stack);
    loading.value = false;
    alert(`Errore: ${error.message}`);
  }
}
</script>

<style scoped>
p {
  text-align: left;
  color: #e0e0e0;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.btn {
  background-color: #4a90e2;
  border-color: #4a90e2;
  width: 100%;
  color: white;
}

.btn:hover {
  background-color: #357abd;
  border-color: #357abd;
}

h1 {
  color: #ffffff;
  margin-bottom: 2rem;
  font-size: 1.8rem;
}

.main-form {
  padding: 2rem;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}

.dropzone {
  border: 2px dashed #4a90e2;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  margin-bottom: 1rem;
  color: #b0b0b0;
  background-color: #333333;
  cursor: pointer;
  transition: all 0.2s;
}

.dropzone:hover {
  border-color: #357abd;
  background-color: #3a3a3a;
}

.srt-dropzone {
  padding: 1.2rem 2rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.srt-dropzone.has-file {
  border-color: #4caf50;
  background-color: #1e3a1e;
  color: #81c784;
}

.srt-dropzone p {
  margin: 0;
  color: inherit;
}

.srt-icon {
  font-size: 1.4rem;
  flex-shrink: 0;
}

/* Toggle switch row */
.srt-toggle-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 1rem 0 1.25rem 0;
}

.srt-toggle-label {
  color: #666;
  font-size: 0.85rem;
  font-weight: 500;
  transition: color 0.2s;
}

.srt-toggle-label.active {
  color: #4a90e2;
}

/* iOS-style toggle */
.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: #444;
  transition: 0.3s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
}

input:checked + .slider {
  background-color: #4a90e2;
}

input:checked + .slider:before {
  transform: translateX(22px);
}

.slider.round {
  border-radius: 26px;
}

.slider.round:before {
  border-radius: 50%;
}

.form-select {
  background-color: #333333;
  color: #e0e0e0;
  border: 1px solid #4a4a4a;
}

.form-select option {
  background-color: #2a2a2a;
  color: #e0e0e0;
}

.loading-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.progress-container {
  background: rgba(42, 42, 42, 0.7);
  padding: 3rem;
  border-radius: 12px;
  min-width: 500px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(74, 74, 74, 0.5);
}

.progress-container h2 {
  color: #ffffff;
  margin-bottom: 2rem;
  text-align: center;
  font-size: 1.5rem;
}

.progress-section {
  margin-bottom: 2rem;
}

.progress-section:last-child {
  margin-bottom: 0;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  color: #e0e0e0;
  font-weight: 500;
}

.progress-percent {
  color: #4a90e2;
  font-weight: 600;
}

.progress-bar-wrapper {
  width: 100%;
  height: 24px;
  background-color: #333333;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #4a4a4a;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4a90e2, #357abd);
  border-radius: 12px;
  transition: width 0.3s ease;
  box-shadow: 0 0 10px rgba(74, 144, 226, 0.5);
}
</style>