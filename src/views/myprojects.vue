<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import Form from '../components/Form.vue';

const router = useRouter();

const API_BASE = 'https://api.matita.net/subtitles-admin';

// ─── Token helpers ────────────────────────────────────────────────────────────

const getToken = () => localStorage.getItem('subtitles_token');

const setToken = (newToken) => {
  localStorage.setItem('subtitles_token', newToken);
  api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
};

// ─── Axios instance ───────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: API_BASE
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    const refreshed = response.headers['x-refresh-token'];
    if (refreshed) {
      setToken(refreshed);
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('subtitles_token');
      router.push('/home');
    }
    return Promise.reject(error);
  }
);

// ─── State ────────────────────────────────────────────────────────────────────

const profile = ref(null);
const projects = ref([]);
const users = ref([]);
const activeTab = ref('projects');
const loading = ref(false);
const projectsLoading = ref(false);

// Project form (create)
const showProjectForm = ref(false);

// Project detail modal
const showProjectModal = ref(false);
const projectModalMode = ref('view'); // 'view' | 'edit'
const selectedProject = ref(null);
const projectForm = ref({ name: '', data: '' });
const projectFormError = ref('');
const projectFormLoading = ref(false);
const deleteConfirmProjectId = ref(null);

const showVideoModal = ref(false);
const videoFile = ref(null);
const subtitles = ref([]);
const tranSubtitles = ref([]);
const loadingEdit = ref(false);

// User management
const showUserModal = ref(false);
const userModalMode = ref('view'); // 'view' | 'edit' | 'create'
const selectedUser = ref(null);
const userForm = ref({ username: '', email: '', password: '', confirmPassword: '', admin: false });
const userFormError = ref('');
const userFormLoading = ref(false);
const deleteConfirmUserId = ref(null);

// ─── Data Loading ──────────────────────────────────────────────────────────────

const loadProjects = async () => {
  projectsLoading.value = true;
  try {
    const res = await api.get('/projects');
    projects.value = res.data.filter(p => !p.is_deleted);
  } catch (err) {
    console.error('Error loading projects:', err);
  } finally {
    projectsLoading.value = false;
  }
};

const loadDashboard = async () => {
  loading.value = true;
  try {
    const profileRes = await api.get('/me');
    profile.value = profileRes.data;

    await loadProjects();

    if (profile.value.admin) {
      const usersRes = await api.get('/users');
      users.value = usersRes.data;
    }
  } catch (err) {
    console.error('Error loading dashboard:', err);
  } finally {
    loading.value = false;
  }
};

// ─── Projects ─────────────────────────────────────────────────────────────────

const openProjectDetail = async (project) => {
  // apre subito con i dati che ha, senza aspettare la GET
  selectedProject.value = { ...project };
  projectForm.value = { name: project.name, data: project.data || '' };
  projectModalMode.value = 'view';
  projectFormError.value = '';
  deleteConfirmProjectId.value = null;
  videoFile.value = null;
  showProjectModal.value = true;

  // aggiorna in background
  try {
    const res = await api.get(`/projects/${project.id}`);
    selectedProject.value = res.data;
    projectForm.value = { name: res.data.name, data: res.data.data || '' };
  } catch (err) {
    console.error('Could not refresh project detail:', err);
  }
};


const goToEditor = async () => {
  try {
    const parsedData = JSON.parse(selectedProject.value.data || '{}');
    tranSubtitles.value = parseSrtToArray(parsedData.srt1 || '');
    subtitles.value = parseSrtToArray(parsedData.srt2 || '');
    localStorage.setItem('subtitles', JSON.stringify(subtitles.value));
    localStorage.setItem('tranSubtitles', JSON.stringify(tranSubtitles.value));
    localStorage.setItem('currentProjectId', selectedProject.value.id)
    localStorage.setItem('currentProjectName', selectedProject.value.name)
    localStorage.setItem('currentProjectUserId', selectedProject.value.user_id)
    localStorage.setItem('currentProjectBackup', JSON.stringify(selectedProject.value)) // ← aggiungi questo
    router.push({
      name: 'video-player',
      state: {
        project: JSON.parse(JSON.stringify(selectedProject.value)), // ← passa il progetto completo
        projectId: selectedProject.value.id,
        projectName: selectedProject.value.name,
        projectUserId: selectedProject.value.user_id,
      }
    });
  } catch (err) {
    console.error('Error parsing SRT data:', err);
    tranSubtitles.value = [];
    subtitles.value = [];
  }
};

const closeProjectModal = () => {
  showProjectModal.value = false;
  selectedProject.value = null;
  deleteConfirmProjectId.value = null;
};

const updateProject = async () => {
  projectFormError.value = '';
  projectFormLoading.value = true;
  try {
    await api.patch(`/projects/${selectedProject.value.id}`, {
      name: projectForm.value.name,
      data: projectForm.value.data
    });
    closeProjectModal();
    loadProjects();
  } catch (err) {
    projectFormError.value = err.response?.data?.detail?.[0]?.msg || 'Error updating project';
  } finally {
    projectFormLoading.value = false;
  }
};

const confirmDeleteProject = (id) => {
  deleteConfirmProjectId.value = id;
};

const deleteProject = async () => {
  projectFormLoading.value = true;
  try {
    await api.delete(`/projects/${deleteConfirmProjectId.value}`);
    closeProjectModal();
    loadProjects();
  } catch {
    projectFormError.value = 'Error deleting project';
  } finally {
    projectFormLoading.value = false;
  }
};

const onProjectCreated = () => {
  showProjectForm.value = false;
  loadProjects();
};

const parseSrtToArray = (srtString) => {
  const blocchi = srtString.trim().split(/\r?\n\r?\n/);
  return blocchi.map(blocco => {
    const righe = blocco.split(/\r?\n/);
    if (righe.length >= 3) {
      return {
        timestamp: righe[1],
        testo: righe.slice(2).join(' ')
      };
    }
    return null;
  }).filter(Boolean);
};

// ─── Users ────────────────────────────────────────────────────────────────────

const openCreateUser = () => {
  userForm.value = { username: '', email: '', password: '', confirmPassword: '', admin: false };
  userFormError.value = '';
  userModalMode.value = 'create';
  selectedUser.value = null;
  showUserModal.value = true;
};

const openUserDetail = (user) => {
  selectedUser.value = { ...user };
  userForm.value = {
    username: user.username,
    email: user.email,
    password: '',
    admin: user.admin
  };
  userFormError.value = '';
  userModalMode.value = 'view';
  showUserModal.value = true;
};

const closeUserModal = () => {
  showUserModal.value = false;
  selectedUser.value = null;
  deleteConfirmUserId.value = null;
};

const createUser = async () => {
  userFormError.value = '';
  if (userForm.value.password !== userForm.value.confirmPassword) {
    userFormError.value = 'Passwords do not match';
    return;
  }
  userFormLoading.value = true;
  try {
    await api.post('/users', {
      username: userForm.value.username,
      email: userForm.value.email,
      password: userForm.value.password,
      admin: userForm.value.admin
    });
    closeUserModal();
    loadDashboard();
  } catch (err) {
    userFormError.value = err.response?.data?.detail?.[0]?.msg || 'Error creating user';
  } finally {
    userFormLoading.value = false;
  }
};

const updateUser = async () => {
  userFormError.value = '';
  userFormLoading.value = true;
  try {
    const payload = {
      username: userForm.value.username,
      email: userForm.value.email,
      admin: userForm.value.admin
    };
    if (userForm.value.password) payload.password = userForm.value.password;

    await api.patch(`/users/${selectedUser.value.id}`, payload);
    closeUserModal();
    loadDashboard();
  } catch (err) {
    userFormError.value = err.response?.data?.detail?.[0]?.msg || 'Error updating user';
  } finally {
    userFormLoading.value = false;
  }
};

const confirmDeleteUser = (id) => {
  deleteConfirmUserId.value = id;
};

const deleteUser = async () => {
  userFormLoading.value = true;
  try {
    await api.delete(`/users/${deleteConfirmUserId.value}`);
    closeUserModal();
    loadDashboard();
  } catch {
    userFormError.value = 'Error deleting user';
  } finally {
    userFormLoading.value = false;
  }
};

const activeUsers = computed(() => users.value.filter(u => !u.is_deleted));
const deletedUsers = computed(() => users.value.filter(u => u.is_deleted));

// ─── Auth ─────────────────────────────────────────────────────────────────────

const logout = () => {
  localStorage.removeItem('subtitles_token');
  router.push('/home');
};

onMounted(loadDashboard);
</script>

<template>
  <div class="sensei-dashboard">

    <!-- Top Bar -->
    <header class="top-bar">
      <div class="logo">Sensei</div>
      <div class="top-actions">
        <span v-if="profile" class="user-badge">
          <span class="user-dot"></span>
          {{ profile.username }}
          <span v-if="profile.admin" class="admin-tag">Admin</span>
        </span>
        <button @click="logout" class="btn-logout">Logout</button>
      </div>
    </header>

    <div class="main-layout">

      <!-- Sidebar -->
      <aside class="sidebar">
        <nav>
          <button
            :class="['nav-btn', { active: activeTab === 'projects' }]"
            @click="activeTab = 'projects'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
              <path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h2.764c.958 0 1.76.56 2.311 1.184C7.985 3.648 8.48 4 9 4h4.5A1.5 1.5 0 0 1 15 5.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 12.5v-9z"/>
            </svg>
            Projects
          </button>
          <button
            v-if="profile?.admin"
            :class="['nav-btn', { active: activeTab === 'users' }]"
            @click="activeTab = 'users'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
              <path d="M15 14s1 0 1-1-1-4-5-4-5 3-5 4 1 1 1 1h8zm-7.978-1A.261.261 0 0 1 7 12.996c.001-.264.167-1.03.76-1.72C8.312 10.629 9.282 10 11 10c1.717 0 2.687.63 3.24 1.276.593.69.758 1.457.76 1.72l-.008.002-.014.002H7.022zM11 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm3-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM6.936 9.28a5.88 5.88 0 0 0-1.23-.247A7.35 7.35 0 0 0 5 9c-4 0-5 3-5 4 0 .667.333 1 1 1h4.216A2.238 2.238 0 0 1 5 13c0-1.01.377-2.042 1.09-2.904.243-.294.526-.569.846-.816zM4.92 10A5.493 5.493 0 0 0 4 13H1c0-.26.164-1.03.76-1.724.545-.636 1.492-1.256 3.16-1.275zM1.5 5.5a3 3 0 1 1 6 0 3 3 0 0 1-6 0zm3-2a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/>
            </svg>
            Users
            <span class="users-count">{{ users.length }}</span>
          </button>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="content">

        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Loading...</p>
        </div>

        <!-- ── PROJECTS TAB ─────────────────────────────────────────── -->
        <div v-else-if="activeTab === 'projects'" class="fade-in">
          <div class="header-section">
            <div>
              <h2 class="section-title">Your Projects</h2>
              <p class="section-sub">{{ projects.length }} project{{ projects.length === 1 ? '' : 's' }} found</p>
            </div>
            <button @click="showProjectForm = true" class="btn-primary">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
              </svg>
              New Project
            </button>
          </div>

          <!-- Modal Form New Project -->
          <!-- ↓ MODIFICA: aggiunto :userId="profile?.id" -->
          <div v-if="showProjectForm" class="modal-overlay" @click.self="showProjectForm = false">
            <div class="modal-content">
              <button class="btn-close-modal" @click="showProjectForm = false">×</button>
              <Form @project-created="onProjectCreated" :userId="profile?.id" />
            </div>
          </div>

          <!-- Projects loading -->
          <div v-if="projectsLoading" class="loading-state">
            <div class="spinner"></div>
            <p>Loading projects...</p>
          </div>

          <!-- Projects Grid -->
          <div v-else-if="projects.length > 0" class="projects-grid">
            <div v-for="p in projects" :key="p.id" class="project-card">
              <div class="project-thumbnail" @click="openProjectDetail(p)" title="View details">
                <div class="thumb-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M6.79 5.093A.5.5 0 0 0 6 5.5v5a.5.5 0 0 0 .79.407l3.5-2.5a.5.5 0 0 0 0-.814l-3.5-2.5z"/>
                    <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm15 0a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
                  </svg>
                </div>
                <div class="thumb-hover-overlay">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z"/>
                    <path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8zm8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z"/>
                  </svg>
                  <span>View Details</span>
                </div>
              </div>
              <div class="project-info">
                <h3 class="project-name">{{ p.name }}</h3>
                <p class="project-id">#{{ p.id }}</p>
                <p v-if="p.data" class="project-data">{{ p.data }}</p>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="empty-state">
            <svg xmlns="http://www.w3.org/2000/svg" width="56" height="56" fill="currentColor" viewBox="0 0 16 16">
              <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5v-2z"/>
            </svg>
            <h3>No projects found</h3>
            <p>Create your first project to get started</p>
            <button @click="showProjectForm = true" class="btn-primary">Create Project</button>
          </div>
        </div>

        <!-- ── USERS TAB (Admin only) ───────────────────────────────── -->
        <div v-else-if="activeTab === 'users' && profile?.admin" class="fade-in">
          <div class="header-section">
            <div>
              <h2 class="section-title">User Management</h2>
              <p class="section-sub">{{ activeUsers.length }} active, {{ deletedUsers.length }} deleted</p>
            </div>
            <button @click="openCreateUser" class="btn-primary">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
              </svg>
              Add User
            </button>
          </div>

          <!-- Users Table -->
          <div class="table-container">
            <table class="sensei-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="u in users"
                  :key="u.id"
                  :class="{ 'row-deleted': u.is_deleted }"
                >
                  <td class="td-id">#{{ u.id }}</td>
                  <td class="td-username">
                    <span class="avatar-mini">{{ u.username.charAt(0).toUpperCase() }}</span>
                    {{ u.username }}
                  </td>
                  <td>{{ u.email }}</td>
                  <td>
                    <span :class="['badge', u.admin ? 'b-admin' : 'b-user']">
                      {{ u.admin ? 'Admin' : 'User' }}
                    </span>
                  </td>
                  <td>
                    <span class="status-pill" :class="u.is_deleted ? 'st-deleted' : 'st-active'">
                      {{ u.is_deleted ? 'Inactive' : 'Active' }}
                    </span>
                  </td>
                  <td class="td-actions">
                    <button @click="openUserDetail(u)" class="btn-row-action" title="Details / Edit">
                      <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/>
                      </svg>
                      Manage
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </main>
    </div>

    <!-- ── PROJECT DETAIL MODAL ──────────────────────────────────────────── -->
    <div v-if="showProjectModal" class="modal-overlay" @click.self="closeProjectModal">
      <div class="modal-content modal-project">

        <div class="modal-header">
          <div class="modal-project-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" class="modal-project-icon">
              <path d="M6.79 5.093A.5.5 0 0 0 6 5.5v5a.5.5 0 0 0 .79.407l3.5-2.5a.5.5 0 0 0 0-.814l-3.5-2.5z"/>
              <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm15 0a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
            </svg>
            <div>
              <h3>{{ projectModalMode === 'edit' ? 'Edit Project' : selectedProject?.name }}</h3>
              <span class="modal-project-id">Project ID: #{{ selectedProject?.id }}</span>
            </div>
          </div>
          <button class="btn-close-modal" @click="closeProjectModal">×</button>
        </div>

        <!-- VIEW MODE -->
        <div v-if="projectModalMode === 'view'" class="modal-body">
          <div class="info-row">
            <span class="info-label">Project ID</span>
            <span class="info-val">#{{ selectedProject?.id }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Name</span>
            <span class="info-val-text">{{ selectedProject?.name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Owner ID</span>
            <span class="info-val">#{{ selectedProject?.user_id }}</span>
          </div>

          <div v-if="deleteConfirmProjectId === selectedProject?.id" class="delete-confirm-box">
            <p>Are you sure you want to delete <strong>{{ selectedProject?.name }}</strong>?</p>
            <div class="confirm-actions">
              <button @click="deleteConfirmProjectId = null" class="btn-secondary">Cancel</button>
              <button @click="deleteProject" :disabled="projectFormLoading" class="btn-danger">
                {{ projectFormLoading ? 'Deleting...' : 'Delete' }}
              </button>
            </div>
          </div>

          <div class="modal-footer">
            <button
              v-if="deleteConfirmProjectId !== selectedProject?.id"
              @click="confirmDeleteProject(selectedProject?.id)"
              class="btn-danger"
            >
              Delete Project
            </button>
            <button @click="goToEditor" class="btn-primary">
              Edit Project
            </button>
          </div>
        </div>



<!-- EDIT MODE — rinomina progetto -->
<div v-else-if="projectModalMode === 'edit'" class="modal-body">
  <div v-if="projectFormError" class="form-error">{{ projectFormError }}</div>
  <div class="form-group">
    <label>Project Name</label>
    <input v-model="projectForm.name" type="text" placeholder="Enter project name" class="form-input" />
  </div>
  <div class="modal-footer">
    <button @click="projectModalMode = 'view'" class="btn-secondary">Cancel</button>
    <button @click="updateProject" :disabled="projectFormLoading" class="btn-primary">
      {{ projectFormLoading ? 'Saving...' : 'Save Changes' }}
    </button>
  </div>
</div>

      </div>
    </div>

    <!-- ── USER MODAL ─────────────────────────────────────────────────────── -->
    <div v-if="showUserModal" class="modal-overlay" @click.self="closeUserModal">
      <div class="modal-content modal-user">

        <div class="modal-header">
          <h3 v-if="userModalMode === 'create'">New User</h3>
          <h3 v-else-if="userModalMode === 'edit'">Edit User</h3>
          <div v-else class="modal-view-header">
            <span class="avatar-large">{{ selectedUser?.username?.charAt(0).toUpperCase() }}</span>
            <div>
              <h3>{{ selectedUser?.username }}</h3>
              <p class="modal-email">{{ selectedUser?.email }}</p>
            </div>
          </div>
          <button class="btn-close-modal" @click="closeUserModal">×</button>
        </div>

        <!-- VIEW MODE -->
        <div v-if="userModalMode === 'view'" class="modal-body">
          <div class="info-row">
            <span class="info-label">ID</span>
            <span class="info-val">#{{ selectedUser?.id }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Role</span>
            <span :class="['badge', selectedUser?.admin ? 'b-admin' : 'b-user']">
              {{ selectedUser?.admin ? 'Admin' : 'User' }}
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">Status</span>
            <span class="status-pill" :class="selectedUser?.is_deleted ? 'st-deleted' : 'st-active'">
              {{ selectedUser?.is_deleted ? 'Inactive' : 'Active' }}
            </span>
          </div>

          <div v-if="deleteConfirmUserId === selectedUser?.id" class="delete-confirm-box">
            <p>Are you sure you want to delete <strong>{{ selectedUser?.username }}</strong>?</p>
            <div class="confirm-actions">
              <button @click="deleteConfirmUserId = null" class="btn-secondary">Cancel</button>
              <button @click="deleteUser" :disabled="userFormLoading" class="btn-danger">
                {{ userFormLoading ? 'Deleting...' : 'Delete' }}
              </button>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="confirmDeleteUser(selectedUser?.id)" class="btn-danger" v-if="deleteConfirmUserId !== selectedUser?.id">
              Delete User
            </button>
            <button @click="userModalMode = 'edit'" class="btn-primary">
              Edit
            </button>
          </div>
        </div>

        <!-- EDIT / CREATE FORM -->
        <div v-else class="modal-body">
          <div v-if="userFormError" class="form-error">{{ userFormError }}</div>

          <div class="form-group">
            <label>Username</label>
            <input v-model="userForm.username" type="text" placeholder="Min. 3 characters" class="form-input" />
          </div>

          <div class="form-group">
            <label>Email</label>
            <input v-model="userForm.email" type="email" placeholder="email@example.com" class="form-input" />
          </div>

          <div class="form-group">
            <label>{{ userModalMode === 'create' ? 'Password' : 'New Password (leave blank to keep current)' }}</label>
            <input v-model="userForm.password" type="password" placeholder="••••••••" class="form-input" />
          </div>

          <div v-if="userModalMode === 'create'" class="form-group">
            <label>Confirm Password</label>
            <input
              v-model="userForm.confirmPassword"
              type="password"
              placeholder="••••••••"
              class="form-input"
              :class="{ 'input-error': userForm.confirmPassword && userForm.password !== userForm.confirmPassword }"
            />
            <span v-if="userForm.confirmPassword && userForm.password !== userForm.confirmPassword" class="field-error">
              Passwords do not match
            </span>
            <span v-if="userForm.confirmPassword && userForm.password === userForm.confirmPassword && userForm.password" class="field-ok">
              ✓ Passwords match
            </span>
          </div>

          <div class="form-group form-group-inline">
            <label class="toggle-label">
              <span>Admin Account</span>
              <div class="toggle-wrapper">
                <input type="checkbox" v-model="userForm.admin" class="toggle-input" />
                <div class="toggle-track" :class="{ 'toggle-on': userForm.admin }">
                  <div class="toggle-thumb"></div>
                </div>
              </div>
            </label>
          </div>

          <div class="modal-footer">
            <button @click="userModalMode === 'create' ? closeUserModal() : userModalMode = 'view'" class="btn-secondary">
              Cancel
            </button>
            <button
              @click="userModalMode === 'create' ? createUser() : updateUser()"
              :disabled="userFormLoading"
              class="btn-primary"
            >
              {{ userFormLoading ? 'Saving...' : (userModalMode === 'create' ? 'Create User' : 'Save Changes') }}
            </button>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
/* ── Base ──────────────────────────────────────────────────────────────────── */
.sensei-dashboard {
  background-color: #0f1117;
  color: #e2e8f0;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* ── Top Bar ───────────────────────────────────────────────────────────────── */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 36px;
  background: #0a0c12;
  border-bottom: 1px solid #1e2330;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #fff;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 14px;
}

.user-dot {
  width: 8px;
  height: 8px;
  background: #22c55e;
  border-radius: 50%;
  display: inline-block;
}

.admin-tag {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 4px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.btn-logout {
  background: transparent;
  border: 1px solid #2d3748;
  color: #94a3b8;
  padding: 7px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: 0.2s;
}

.btn-logout:hover {
  border-color: #4a5568;
  color: #e2e8f0;
}

/* ── Layout ────────────────────────────────────────────────────────────────── */
.main-layout {
  display: flex;
  min-height: calc(100vh - 54px);
}

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: #0a0c12;
  border-right: 1px solid #1e2330;
  padding: 28px 14px;
}

.nav-btn {
  width: 100%;
  background: transparent;
  border: none;
  color: #64748b;
  text-align: left;
  padding: 10px 14px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.2s;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 500;
}

.nav-btn:hover {
  background: #1e2330;
  color: #e2e8f0;
}

.nav-btn.active {
  background: #1e2942;
  color: #60a5fa;
}

.users-count {
  margin-left: auto;
  background: #1e2330;
  color: #64748b;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 10px;
  font-weight: 600;
}

.nav-btn.active .users-count {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

/* ── Content ───────────────────────────────────────────────────────────────── */
.content {
  flex-grow: 1;
  padding: 36px 48px;
  overflow-y: auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28px;
}

.section-title {
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: #f8fafc;
}

.section-sub {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

/* ── Buttons ───────────────────────────────────────────────────────────────── */
.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 9px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: 0.2s;
  white-space: nowrap;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: #94a3b8;
  border: 1px solid #2d3748;
  padding: 8px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.2s;
}

.btn-secondary:hover {
  border-color: #4a5568;
  color: #e2e8f0;
}

.btn-danger {
  background: transparent;
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.4);
  padding: 8px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.2s;
}

.btn-danger:hover {
  background: rgba(248, 113, 113, 0.1);
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── Project Card ──────────────────────────────────────────────────────────── */
.project-thumbnail {
  width: 100%;
  aspect-ratio: 16/9;
  background: linear-gradient(135deg, #1e2742 0%, #151924 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #1e2330;
  position: relative;
  cursor: pointer;
  overflow: hidden;
}

.thumb-icon {
  color: #3b82f6;
  transition: 0.25s;
}

.thumb-hover-overlay {
  position: absolute;
  inset: 0;
  background: rgba(59, 130, 246, 0.15);
  backdrop-filter: blur(2px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #93c5fd;
  font-size: 13px;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.2s;
}

.project-thumbnail:hover .thumb-hover-overlay {
  opacity: 1;
}

.project-thumbnail:hover .thumb-icon {
  opacity: 0;
}

/* ── Project Modal ─────────────────────────────────────────────────────────── */
.modal-project {
  max-width: 480px;
}

.modal-project-title {
  display: flex;
  align-items: center;
  gap: 14px;
}

.modal-project-icon {
  color: #3b82f6;
  flex-shrink: 0;
}

.modal-project-title h3 {
  margin: 0 0 3px 0;
  font-size: 17px;
  color: #f1f5f9;
}

.modal-project-id {
  font-size: 12px;
  color: #475569;
  font-family: monospace;
}

.info-val-text {
  font-size: 14px;
  color: #cbd5e1;
  text-align: right;
  max-width: 60%;
  word-break: break-word;
}

.info-val-data {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
  background: #0f1117;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #1e2330;
}

.form-textarea {
  resize: vertical;
  min-height: 90px;
  font-family: monospace;
  font-size: 13px;
  line-height: 1.5;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 20px;
}

.project-card {
  background: #151924;
  border: 1px solid #1e2330;
  border-radius: 12px;
  overflow: hidden;
  transition: 0.25s;
}

.project-card:hover {
  transform: translateY(-3px);
  border-color: #3b82f6;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.1);
}

.project-info {
  padding: 16px;
}

.project-name {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 6px 0;
  color: #f1f5f9;
}

.project-id {
  font-size: 11px;
  color: #475569;
  margin: 0 0 6px 0;
}

.project-data {
  font-size: 12px;
  color: #64748b;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Empty State ───────────────────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #475569;
}

.empty-state svg {
  margin-bottom: 20px;
  opacity: 0.3;
}

.empty-state h3 {
  font-size: 22px;
  margin: 0 0 10px 0;
  color: #94a3b8;
}

.empty-state p {
  margin: 0 0 24px 0;
  font-size: 14px;
}

/* ── Users Table ───────────────────────────────────────────────────────────── */
.table-container {
  background: #151924;
  border: 1px solid #1e2330;
  border-radius: 12px;
  overflow: hidden;
}

.sensei-table {
  width: 100%;
  border-collapse: collapse;
}

.sensei-table th {
  background: #0f1117;
  padding: 12px 16px;
  text-align: left;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  border-bottom: 1px solid #1e2330;
}

.sensei-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #1a2030;
  font-size: 14px;
  vertical-align: middle;
}

.sensei-table tr:last-child td {
  border-bottom: none;
}

.sensei-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.row-deleted td {
  opacity: 0.45;
}

.td-id {
  color: #475569;
  font-size: 12px;
  font-family: monospace;
}

.td-username {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 500;
  color: #e2e8f0;
}

.avatar-mini {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.td-actions {
  text-align: right;
}

.btn-row-action {
  background: transparent;
  border: 1px solid #2d3748;
  color: #94a3b8;
  padding: 5px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: 0.2s;
}

.btn-row-action:hover {
  border-color: #3b82f6;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.06);
}

/* ── Badges & Pills ────────────────────────────────────────────────────────── */
.badge {
  padding: 3px 10px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.b-admin {
  background: rgba(34, 197, 94, 0.12);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.b-user {
  background: rgba(148, 163, 184, 0.08);
  color: #94a3b8;
  border: 1px solid #2d3748;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.status-pill::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.st-active {
  background: rgba(34, 197, 94, 0.08);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.st-active::before { background: #22c55e; }

.st-deleted {
  background: rgba(248, 113, 113, 0.08);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.2);
}

.st-deleted::before { background: #ef4444; }

/* ── Modal ─────────────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.15s ease;
}

.modal-content {
  background: #151924;
  border: 1px solid #1e2330;
  border-radius: 14px;
  padding: 28px;
  max-width: 520px;
  width: 90%;
  position: relative;
  animation: slideUp 0.25s ease;
}

.modal-user {
  max-width: 460px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #1e2330;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #f1f5f9;
}

.modal-view-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.modal-view-header h3 {
  margin: 0 0 3px 0;
  font-size: 18px;
}

.modal-email {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.avatar-large {
  width: 46px;
  height: 46px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.btn-close-modal {
  background: transparent;
  border: none;
  color: #475569;
  font-size: 26px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  margin-left: auto;
  transition: 0.2s;
}

.btn-close-modal:hover { color: #e2e8f0; }

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #1a2030;
}

.info-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.info-val {
  font-size: 14px;
  color: #94a3b8;
  font-family: monospace;
}

.delete-confirm-box {
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
  padding: 14px 16px;
}

.delete-confirm-box p {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #fca5a5;
}

.confirm-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-input {
  background: #0f1117;
  border: 1px solid #2d3748;
  border-radius: 8px;
  color: #e2e8f0;
  padding: 10px 14px;
  font-size: 14px;
  transition: 0.2s;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input::placeholder {
  color: #334155;
}

.form-group-inline {
  flex-direction: row;
  align-items: center;
}

.toggle-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  cursor: pointer;
  font-size: 14px;
  color: #94a3b8;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
}

.toggle-wrapper {
  position: relative;
}

.toggle-input {
  display: none;
}

.toggle-track {
  width: 42px;
  height: 24px;
  background: #2d3748;
  border-radius: 12px;
  position: relative;
  transition: 0.25s;
  cursor: pointer;
}

.toggle-track.toggle-on {
  background: #3b82f6;
}

.toggle-thumb {
  width: 18px;
  height: 18px;
  background: white;
  border-radius: 50%;
  position: absolute;
  top: 3px;
  left: 3px;
  transition: 0.25s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.toggle-track.toggle-on .toggle-thumb {
  transform: translateX(18px);
}

.form-error {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #fca5a5;
}

.input-error {
  border-color: rgba(239, 68, 68, 0.6) !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.08) !important;
}

.field-error {
  font-size: 12px;
  color: #f87171;
  margin-top: 2px;
}

.field-ok {
  font-size: 12px;
  color: #4ade80;
  margin-top: 2px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid #1e2330;
  margin-top: 4px;
}

/* ── Loading ───────────────────────────────────────────────────────────────── */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px;
  gap: 16px;
  color: #475569;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #1e2330;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.fade-in {
  animation: fadeIn 0.35s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0);   }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0);    }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>