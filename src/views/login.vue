<script setup>
import { ref } from 'vue';
import axios from 'axios';
import { useRouter } from 'vue-router';

const router = useRouter();
const apiLogin = 'https://api.matita.net/subtitles-admin/login';

const username = ref('');
const password = ref('');
const loading = ref(false);
const errorMsg = ref('');

const handleLogin = async () => {
  loading.value = true;
  errorMsg.value = '';

  try {
    const params = new URLSearchParams();
    params.append('username', username.value);
    params.append('password', password.value);

    const response = await axios.post(apiLogin, params);

    const token = response.data.access_token;
    localStorage.setItem('subtitles_token', token);

    // ─── Segna l'utente come loggato ────────────────────────────────────────
    localStorage.setItem('isLogged', 'true');

    // ─── Gestisci redirect post-login ───────────────────────────────────────
    // Home.vue salva 'redirectAfterLogin' quando Workspace viene cliccato da non loggato
    const redirect = localStorage.getItem('redirectAfterLogin');
    if (redirect) {
      localStorage.removeItem('redirectAfterLogin');
      router.push(redirect);
    } else {
      router.push('/myprojects');
    }

  } catch (err) {
    if (err.response) {
      errorMsg.value = err.response.status === 401
        ? "Credenziali errate. Riprova."
        : "Errore del server: " + (err.response.data.detail || "Riprova");
    } else {
      errorMsg.value = "Impossibile connettersi al server.";
    }
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="sensei-wrapper">
    <header class="position-absolute top-0 start-0 end-0 p-3 d-flex justify-content-between align-items-center">
      <h1 class="mb-0">Sensei</h1>
    </header>

    <main class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
          <h1>Bentornato!</h1>
          <p class="subtitle">Accedi alla community di Sensei Subtitles</p>
        </div>

        <form @submit.prevent="handleLogin" class="auth-form">
          <div class="input-group">
            <label>Username</label>
            <input 
              v-model="username" 
              type="text" 
              placeholder="Il tuo username" 
              required 
            />
          </div>

          <div class="input-group">
            <label>Password</label>
            <input 
              v-model="password" 
              type="password" 
              placeholder="••••••••" 
              required 
            />
          </div>

          <button type="submit" :disabled="loading" class="btn-submit">
            {{ loading ? 'Accesso in corso...' : 'Log in' }}
          </button>

          <Transition name="fade">
            <p v-if="errorMsg" class="error-text">{{ errorMsg }}</p>
          </Transition>
        </form>

        
      </div>
    </main>
  </div>
</template>

<style scoped>
:root {
  --bg-dark: #111418;
  --card-bg: #1a1d23;
  --input-bg: #ffffff;
  --primary-blue: #3b82f6;
  --text-muted: #94a3b8;
}

.sensei-wrapper {
  min-height: 100vh;
  background-color: #111418; 
  color: #ffffff;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  display: flex;
  flex-direction: column;
}

.top-header {
  padding: 20px 40px;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.glass-btn:hover {
  transform: scale(1.05);
  background: rgba(255, 255, 255, 0.2) !important;
  box-shadow: 0 8px 25px rgba(255, 255, 255, 0.4);
}

.auth-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.auth-card {
  background-color: #1a1d23; 
  width: 100%;
  max-width: 440px;
  padding: 48px 40px;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-header h1 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}

.subtitle {
  color: #94a3b8;
  font-size: 14px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-size: 13px;
  color: #94a3b8;
}

.input-group input {
  width: 100%;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #2d3748;
  background-color: #ffffff; 
  color: #1a1d23;
  font-size: 15px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.input-group input:focus {
  outline: none;
  border-color: #3b82f6;
}

.btn-submit {
  width: 100%;
  padding: 14px;
  background-color: #3b82f6; 
  color: white;
  border: none;
  border-radius: 25px; 
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 10px;
  transition: background-color 0.2s;
}

.btn-submit:hover {
  background-color: #2563eb;
}

.btn-submit:disabled {
  background-color: #4b5563;
  cursor: not-allowed;
}

.auth-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
}

.auth-footer a {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
}

.auth-footer a:hover {
  text-decoration: underline;
}

.error-text {
  color: #ef4444;
  font-size: 13px;
  text-align: center;
  margin-top: 10px;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>