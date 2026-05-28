<template>
  <header class="top-bar">
    <div class="logo">
      <img src="/FBK_colour_transp.png" alt="FBK Logo" class="logo_photo">
      Sensei
    </div>
  </header>
  <div class="main-layout">
    <Form class="form"/>
  </div>
  
</template>

<script setup>
  import Form from '../components/Form.vue';
</script>
<style>
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

.logo_photo{
  height: 40px;
  width: 40px;
  margin-right: 12px;
}
.main-layout{
    align-items: center;
    justify-content: center;
    display: flex;
    flex-direction: column;
    height: 100vh;
}
.form {
  background: #151924;
  border: 1px solid #1e2330;
  border-radius: 14px;
  padding: 28px;
  max-width: 520px;
  width: 90%;
  position: relative;
  animation: slideUp 0.25s ease;
}
</style>