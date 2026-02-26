<template>
  <div class="redirect-screen">
    <div class="spinner"></div>
    <p>Verifica accesso in corso...</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const router = useRouter();

onMounted(async () => {
  const token = localStorage.getItem('subtitles_token');

  // Se non c'è il token, vai direttamente al login senza chiamare l'API
  if (!token) {
    router.replace('/login');
    return;
  }

  try {
    // Chiamata GET all'endpoint richiesto
    const response = await axios.get('https://api.matita.net/subtitles-admin/me', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });

    if (response.status === 200) {
      // Se l'API dice OK, vai ai progetti
      router.replace('/myprojects');
    } else {
      // Qualsiasi altro stato, torna al login
      router.replace('/login');
    }
  } catch (error) {
    // Se il token è scaduto o l'API dà errore (es. 401), pulisci e vai al login
    console.error("Sessione non valida:", error);
    localStorage.removeItem('subtitles_token'); 
    router.replace('/login');
  }
});
</script>

<style scoped>
.redirect-screen {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: #111418; /* Sfondo scuro coerente con il tuo stile */
  color: white;
  font-family: sans-serif;
}

.spinner {
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-left-color: #3b82f6;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>