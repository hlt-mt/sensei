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
        <div v-if="isAzureMode">
          <p>Source language</p>
          <select class="form-select mb-3" v-model="sourceLanguage">
            <option value="">Select source language</option>
            <option value="de">German</option>
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="it">Italian</option>
          </select>
        </div>
      <p>Target language</p>
      <select class="form-select mb-3" v-model="targetLanguage">
        <option value="">Select the language</option>
        <<option value="de">German</option>
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="it">Italian</option>
      </select>
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

const sourceLanguage = ref('')
const envValue = import.meta.env.VITE_REQUIRE_SOURCE_LANG
const isAzureMode = computed(() => envValue === 'true')

const WHISPER_BASE = import.meta.env.VITE_WHISPER_BASE;
const WHISPER_TOKEN = import.meta.env.VITE_WHISPER_TOKEN || '';

const apiConversionPost       = `${WHISPER_BASE}/conversion-start`;
const apiConversionStatus     = `${WHISPER_BASE}/conversion-status`;
const apiConversionOut        = `${WHISPER_BASE}/conversion-out`;

const endpointTranslated      = import.meta.env.VITE_ENDPOINT_TRANSLATED || '/conversion-translated';
const apiConversionTranslated = `${WHISPER_BASE}${endpointTranslated}`;

const tokenBearer = `Bearer ${WHISPER_TOKEN}`;

const API_BASE = 'https://api.matita.net/subtitles-admin'
const apiAdmin = axios.create({ baseURL: API_BASE })

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

function handleCreate() {
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

    const formData = new FormData();
    formData.append('file', videoFile.value);

    const params = {};
      if (targetLanguage.value) {
        params.translate_to = targetLanguage.value;
      }
      if (isAzureMode) {
        params.source = sourceLanguage.value;
      }

    console.log('[NewProject] Invio a:', apiConversionPost, '| Params:', params);

      const conversionJob = await axios.post(apiConversionPost, formData, {
        headers: {
          'Authorization': tokenBearer,
          'Content-Type': 'multipart/form-data'
        },
        params
      });

    const jobId = conversionJob.data.id;
    console.log('[NewProject] Job avviato, ID:', jobId, '| Risposta completa:', conversionJob.data);

    const maxAttempts = 3000;
    const pollInterval = 1000;
    let conversionCompleted = false;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const statusResponse = await axios.get(`${apiConversionStatus}?id=${jobId}`, {
        headers: { 'Authorization': tokenBearer }
      });

      const { status, error, stage, progress } = statusResponse.data;

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

      if (status === 'failed') {
        console.error('[NewProject] Conversione fallita. Errore server:', error);
        throw new Error(error || 'Conversione fallita');
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    if (!conversionCompleted) {
      console.error('[NewProject] Timeout raggiunto dopo', maxAttempts, 'tentativi');
      throw new Error('Timeout: conversione non completata');
    }

    // --- SRT ORIGINALE ---
    console.log('[NewProject] Recupero SRT originale da:', `${apiConversionOut}?id=${jobId}`);
    const originalResponse = await axios.get(`${apiConversionOut}?id=${jobId}`, {
      headers: { 'Authorization': tokenBearer }
    });

    const srt2 = originalResponse.data;

    const blocchiOriginal = srt2.trim().split(/\r?\n\r?\n/);
    subtitles = blocchiOriginal.map(blocco => {
      const righe = blocco.split(/\r?\n/);
      if (righe.length >= 3) {
        return { timestamp: righe[1], testo: righe.slice(2).join(' ') };
      }
      return null;
    }).filter(item => item !== null);

    console.log(`[NewProject] SRT originale: ${subtitles.length} blocchi. Primi 2:`, subtitles.slice(0, 2));

    // --- SRT TRADOTTO ---
    console.log('[NewProject] Recupero SRT tradotto da:', `${apiConversionTranslated}?id=${jobId}`);
    const translatedResponse = await axios.get(`${apiConversionTranslated}?id=${jobId}`, {
      headers: { 'Authorization': tokenBearer }
    });

    const srt1 = translatedResponse.data;

    const blocchiTradotti = srt1.trim().split(/\r?\n\r?\n/);
    tranSubtitles = blocchiTradotti.map(blocco => {
      const righe = blocco.split(/\r?\n/);
      if (righe.length >= 3) {
        return { timestamp: righe[1], testo: righe.slice(2).join(' ') };
      }
      return null;
    }).filter(item => item !== null);

    console.log(`[NewProject] SRT tradotto: ${tranSubtitles.length} blocchi. Primi 2:`, tranSubtitles.slice(0, 2));

    console.log('[NewProject] Salvataggio progetto su API admin...');
    const projectRes = await apiAdmin.post('/projects', {
      name: projectName.value,
      data: JSON.stringify({ srt1, srt2, playhead: 0, videoName: videoFile.value.name })
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