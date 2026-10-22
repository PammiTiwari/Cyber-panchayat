<!-- Landing page for Cyber Panchayat application
     Serves as the public-facing homepage showcasing platform features and benefits.
     Contains hero section, service highlights, and links to login/register.
     No authentication required - accessible to all visitors. -->

<template>
  <div class="landing">
    <!-- Top navigation bar with branding and auth links -->
    <nav class="land-nav">
      <div class="land-brand">
        <div class="brand-icon">CP</div>
        <span class="brand-name">Cyber Panchayat</span>
      </div>
      <div class="nav-links">
        <a href="#home">Home</a>
        <a href="#services">Services</a>
        <a href="#about">About Us</a>
        <a href="#contact">Contact</a>
        <!-- Routed, not an anchor: the FAQ is its own public page, and it's the
             only help a visitor can read before creating an account. -->
        <router-link to="/faq">Help</router-link>
      </div>
      <div class="nav-actions">
        <router-link to="/login" class="btn-nav-login">Login</router-link>
        <router-link to="/register" class="btn-nav-register">Register</router-link>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero" id="home">
      <div class="hero-content">
        <div class="hero-left">
          <div class="hero-tag"><span class="hero-tag-dot"></span>Smart City Portal</div>
          <h1 class="hero-title">Together, We<br>Make Our City<br><span class="hero-accent gradient-text">Better</span></h1>
          <p class="hero-subtitle">Report civic issues, track resolutions, and connect with your community. Cyber Panchayat makes it easy to collaborate with local authorities.</p>
          <div class="hero-btns">
            <router-link to="/register" class="btn-hero-primary">Submit a Complaint</router-link>
            <router-link to="/track" class="btn-hero-outline">Track Complaint</router-link>
          </div>
        </div>
        <div class="hero-right">
          <svg viewBox="0 0 500 380" xmlns="http://www.w3.org/2000/svg" class="hero-svg">
            <!-- Sky gradient -->
            <defs>
              <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#E8EFFF"/>
                <stop offset="100%" stop-color="#FAFAFA"/>
              </linearGradient>
            </defs>
            <rect width="500" height="380" fill="url(#skyGrad)" rx="16"/>
            <!-- Sun -->
            <circle cx="400" cy="70" r="40" fill="#4D7CFF" opacity="0.18"/>
            <!-- Mountains -->
            <polygon points="0,280 120,140 240,280" fill="#94B2FF" opacity="0.4"/>
            <polygon points="100,280 220,120 340,280" fill="#6E94F2" opacity="0.45"/>
            <polygon points="250,280 370,150 490,280" fill="#3D63D6" opacity="0.5"/>
            <!-- Ground -->
            <rect x="0" y="280" width="500" height="100" fill="#E2E8F0" opacity="0.6"/>
            <!-- Buildings -->
            <rect x="30" y="190" width="50" height="90" fill="#0F172A" rx="2"/>
            <rect x="90" y="210" width="40" height="70" fill="#1E3A8A" rx="2"/>
            <rect x="140" y="200" width="35" height="80" fill="#0F172A" rx="2"/>
            <!-- Windows -->
            <rect x="38" y="198" width="8" height="8" fill="#4D7CFF" opacity="0.8"/>
            <rect x="50" y="198" width="8" height="8" fill="#4D7CFF" opacity="0.8"/>
            <rect x="62" y="198" width="8" height="8" fill="#4D7CFF" opacity="0.5"/>
            <rect x="38" y="215" width="8" height="8" fill="#4D7CFF" opacity="0.8"/>
            <rect x="50" y="215" width="8" height="8" fill="#4D7CFF" opacity="0.3"/>
            <rect x="62" y="215" width="8" height="8" fill="#4D7CFF" opacity="0.8"/>
            <!-- Road -->
            <rect x="0" y="310" width="500" height="20" fill="#CBD5E1" opacity="0.5"/>
            <rect x="60" y="317" width="30" height="4" fill="#fff" opacity="0.8" rx="2"/>
            <rect x="130" y="317" width="30" height="4" fill="#fff" opacity="0.8" rx="2"/>
            <rect x="200" y="317" width="30" height="4" fill="#fff" opacity="0.8" rx="2"/>
            <!-- City Hall -->
            <rect x="310" y="170" width="100" height="110" fill="#0F172A" rx="2"/>
            <polygon points="310,170 360,140 410,170" fill="#0F172A"/>
            <rect x="340" y="220" width="40" height="60" fill="#1E3A8A"/>
            <!-- Flag -->
            <line x1="360" y1="140" x2="360" y2="110" stroke="#94B2FF" stroke-width="2"/>
            <polygon points="360,110 385,120 360,130" fill="#0052FF" opacity="0.9"/>
            <!-- Windows city hall -->
            <rect x="320" y="180" width="16" height="14" fill="#4D7CFF" opacity="0.7" rx="1"/>
            <rect x="345" y="180" width="16" height="14" fill="#4D7CFF" opacity="0.7" rx="1"/>
            <rect x="370" y="180" width="16" height="14" fill="#4D7CFF" opacity="0.4" rx="1"/>
            <rect x="395" y="180" width="12" height="14" fill="#4D7CFF" opacity="0.7" rx="1"/>
            <!-- Tree -->
            <rect x="260" y="265" width="6" height="25" fill="#64748B" opacity="0.6"/>
            <circle cx="263" cy="255" r="18" fill="#0052FF" opacity="0.45"/>
            <rect x="460" y="265" width="6" height="25" fill="#64748B" opacity="0.6"/>
            <circle cx="463" cy="255" r="16" fill="#0052FF" opacity="0.4"/>
          </svg>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="how-it-works" id="services">
      <div class="section-container">
        <h2 class="section-title-lg">How It Works</h2>
        <p class="section-sub">Simple steps to resolve civic issues in your city</p>
        <div class="steps-grid">
          <div class="step-card">
            <div class="step-num">1</div>
            <h3>Submit</h3>
            <p>Report an issue with details and photos from anywhere, anytime</p>
          </div>
          <div class="step-card">
            <div class="step-num">2</div>
            <h3>Assign</h3>
            <p>We assign it to the right department for quick action</p>
          </div>
          <div class="step-card">
            <div class="step-num">3</div>
            <h3>Action</h3>
            <p>Officers take action and update status regularly</p>
          </div>
          <div class="step-card">
            <div class="step-num">4</div>
            <h3>Resolve</h3>
            <p>Issue resolved and you get notified instantly</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Contact -->
    <section class="land-contact" id="contact">
      <div class="section-container">
        <h2 class="section-title-lg">Contact Us</h2>
        <p class="section-sub">Have a question or need help? Reach out to the admin office.</p>
        <div class="contact-grid">
          <a v-if="stats.admin_email" :href="`mailto:${stats.admin_email}`" class="contact-card">
            <span class="contact-icon">✉️</span>
            <div>
              <div class="contact-label">Email</div>
              <div class="contact-value">{{ stats.admin_email }}</div>
            </div>
          </a>
          <a v-if="stats.admin_phone" :href="`tel:+91${stats.admin_phone}`" class="contact-card">
            <span class="contact-icon">📞</span>
            <div>
              <div class="contact-label">Phone</div>
              <div class="contact-value">{{ fmtPhone(stats.admin_phone) }}</div>
            </div>
          </a>
        </div>
      </div>
    </section>

    <!-- Stats -->
    <section class="land-stats">
      <div class="stats-container">
        <div class="stat-item">
          <div class="stat-big">{{ fmtNum(stats.total_complaints) }}</div>
          <div class="stat-lbl">Complaints</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-big">{{ fmtNum(stats.resolved) }}</div>
          <div class="stat-lbl">Resolved</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-big">{{ fmtNum(stats.in_progress) }}</div>
          <div class="stat-lbl">In Progress</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-big">{{ fmtNum(stats.departments) }}</div>
          <div class="stat-lbl">Departments</div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="land-footer">
      <div class="land-footer-links">
        <router-link to="/faq">Help &amp; FAQ</router-link>
        <span aria-hidden="true">·</span>
        <router-link to="/track">Track a Complaint</router-link>
        <span aria-hidden="true">·</span>
        <a href="#contact">Contact</a>
      </div>
      <p>&copy; 2026 Cyber Panchayat. Making cities better together.</p>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'

const stats = ref({})

function fmtNum(n) {
  return typeof n === 'number' ? n.toLocaleString('en-IN') : '—'
}

function fmtPhone(p) {
  return p && p.length === 10 ? `+91 ${p.slice(0, 5)} ${p.slice(5)}` : p
}

onMounted(() => {
  api.get('/public-stats').then(res => { stats.value = res.data }).catch(() => {})
})
</script>

<style scoped>
/* ============================================================
   Landing — premium theme pass (styling only, structure kept)
   ============================================================ */
.landing {
  min-height: 100vh;
  background: var(--bg);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.landing ::selection { background: rgba(0,82,255,0.16); }

/* ---------- Navbar ---------- */
.land-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 3rem;
  background: rgba(255,255,255,0.72);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-bottom: 1px solid rgba(226,232,240,0.75);
  position: sticky; top: 0; z-index: 100;
}
.land-brand { display: flex; align-items: center; gap: 0.7rem; }
.brand-icon {
  width: 34px; height: 34px; background: var(--gradient-accent); color: #fff;
  border-radius: 11px; display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 0.68rem; letter-spacing: 0.04em;
  box-shadow: 0 4px 12px rgba(0,82,255,0.35), inset 0 1px 0 rgba(255,255,255,0.25);
}
.brand-name { font-family: var(--font-heading); font-weight: 400; font-size: 1.12rem; color: var(--text); letter-spacing: 0.01em; }
.nav-links { display: flex; gap: 2.1rem; }
.nav-links a { font-size: 0.875rem; font-weight: 500; color: var(--text-muted); transition: var(--transition); position: relative; }
.nav-links a::after {
  content: ''; position: absolute; left: 0; bottom: -6px; width: 0; height: 2px;
  border-radius: 2px; background: var(--gradient-accent); transition: width var(--transition);
}
.nav-links a:hover { color: var(--text); }
.nav-links a:hover::after { width: 100%; }
.nav-actions { display: flex; gap: 0.65rem; align-items: center; }
.btn-nav-login {
  padding: 0.5rem 1.15rem; font-size: 0.875rem; font-weight: 600;
  border: 1px solid var(--outline); border-radius: 10px; color: var(--text);
  transition: var(--transition);
}
.btn-nav-login:hover { border-color: var(--primary); color: var(--primary); background: var(--accent); }
.btn-nav-register {
  padding: 0.5rem 1.2rem; font-size: 0.875rem; font-weight: 600;
  background: var(--gradient-accent); color: #fff; border-radius: 10px;
  transition: var(--transition); box-shadow: 0 4px 12px rgba(0,82,255,0.28);
}
.btn-nav-register:hover { filter: brightness(1.07); transform: translateY(-1px); box-shadow: 0 8px 20px rgba(0,82,255,0.34); }

/* ---------- Hero ---------- */
.hero {
  position: relative; overflow: hidden;
  padding: 6rem 3rem 6.5rem;
  background:
    radial-gradient(1100px 520px at 82% -8%, rgba(0,82,255,0.10), transparent 60%),
    radial-gradient(760px 420px at 8% 12%, rgba(77,124,255,0.10), transparent 55%),
    var(--bg);
}
.hero::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(15,23,42,0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15,23,42,0.035) 1px, transparent 1px);
  background-size: 48px 48px;
  -webkit-mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 78%);
  mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 78%);
}
.hero::after {
  content: ''; position: absolute; top: -140px; right: -120px;
  width: 420px; height: 420px; border-radius: 50%;
  background: var(--accent-secondary); opacity: 0.14; filter: blur(90px); pointer-events: none;
}
.hero-content {
  max-width: 1140px; margin: 0 auto; position: relative; z-index: 1;
  display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 3.5rem; align-items: center;
}
.hero-tag {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: rgba(255,255,255,0.8); color: var(--primary); border: 1px solid rgba(0,82,255,0.22);
  padding: 0.35rem 0.9rem; border-radius: 100px;
  font-family: var(--font-mono); font-size: 0.68rem; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase;
  box-shadow: 0 2px 10px rgba(0,82,255,0.08);
  margin-bottom: 1.4rem;
}
.hero-tag-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--primary); animation: pulse-dot 2s infinite; flex-shrink: 0; }
.hero-title { font-family: var(--font-heading); font-size: 3.5rem; font-weight: 400; line-height: 1.08; letter-spacing: -0.02em; color: var(--text); margin-bottom: 1.15rem; }
.hero-subtitle { font-size: 1.05rem; color: var(--text-muted); line-height: 1.75; margin-bottom: 2rem; max-width: 440px; }
.hero-btns { display: flex; gap: 0.9rem; flex-wrap: wrap; }
.btn-hero-primary {
  padding: 0.85rem 1.7rem; background: var(--gradient-accent); color: #fff;
  border-radius: 12px; font-size: 0.9rem; font-weight: 700; transition: var(--transition);
  box-shadow: 0 8px 22px rgba(0,82,255,0.30), inset 0 1px 0 rgba(255,255,255,0.22);
}
.btn-hero-primary:hover { filter: brightness(1.07); transform: translateY(-2px); box-shadow: 0 14px 30px rgba(0,82,255,0.36), inset 0 1px 0 rgba(255,255,255,0.22); }
.btn-hero-outline {
  padding: 0.85rem 1.7rem;
  border: 1px solid var(--outline); color: var(--text); background: rgba(255,255,255,0.7);
  border-radius: 12px; font-size: 0.9rem; font-weight: 700; transition: var(--transition);
  backdrop-filter: blur(4px);
}
.btn-hero-outline:hover { border-color: var(--primary); color: var(--primary); background: var(--accent); transform: translateY(-2px); }

/* Reframe the illustration as a premium product-preview card */
.hero-right {
  position: relative;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 2.6rem 1.6rem 1.6rem;
  box-shadow: 0 30px 60px -20px rgba(15,23,42,0.28), 0 12px 24px -12px rgba(15,23,42,0.14);
  transition: transform 0.5s cubic-bezier(0.16,1,0.3,1), box-shadow 0.5s cubic-bezier(0.16,1,0.3,1);
}
.hero-right::before {
  content: ''; position: absolute; top: 14px; left: 18px;
  width: 46px; height: 8px; border-radius: 100px;
  background:
    radial-gradient(circle 4px at 4px 4px, #F87171 60%, transparent 62%),
    radial-gradient(circle 4px at 21px 4px, #FBBF24 60%, transparent 62%),
    radial-gradient(circle 4px at 38px 4px, #34D399 60%, transparent 62%);
}
.hero-right::after {
  content: ''; position: absolute; top: 12px; right: 16px; left: 76px; height: 12px;
  border-radius: 100px; background: var(--stone);
}
.hero-right:hover { transform: translateY(-4px); box-shadow: 0 40px 70px -20px rgba(15,23,42,0.32), 0 16px 30px -12px rgba(15,23,42,0.16); }
.hero-svg { width: 100%; display: block; border-radius: var(--radius-lg); border: 1px solid var(--border); }

/* ---------- Section shell ---------- */
.section-container { max-width: 1140px; margin: 0 auto; }
.section-title-lg { font-family: var(--font-heading); font-size: 2.3rem; font-weight: 400; color: var(--text); text-align: center; letter-spacing: -0.015em; margin-bottom: 0.6rem; }
.section-sub { text-align: center; color: var(--text-muted); font-size: 0.98rem; margin-bottom: 3.25rem; }

/* ---------- How it works ---------- */
.how-it-works {
  position: relative;
  padding: 6rem 3rem;
  background: linear-gradient(180deg, var(--card), #FDFDFE);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.steps-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; position: relative; }
.steps-grid::before {
  content: ''; position: absolute; top: 44px; left: 12.5%; right: 12.5%; height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0,82,255,0.25) 15%, rgba(77,124,255,0.4), rgba(0,82,255,0.25) 85%, transparent);
}
.step-card {
  position: relative; z-index: 1;
  text-align: center; padding: 2rem 1.35rem 1.75rem;
  border: 1px solid var(--border); border-radius: var(--radius-lg);
  background: var(--card);
  box-shadow: 0 1px 2px rgba(15,23,42,0.04);
  transition: var(--transition);
}
.step-card:hover { box-shadow: 0 20px 40px -18px rgba(15,23,42,0.22); transform: translateY(-4px); border-color: rgba(0,82,255,0.28); }
.step-num {
  width: 50px; height: 50px;
  background: var(--gradient-accent); color: #fff;
  border-radius: 15px; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 1.15rem; font-weight: 700; margin: 0 auto 1rem;
  box-shadow: 0 8px 18px rgba(0,82,255,0.32), 0 0 0 6px rgba(0,82,255,0.08), inset 0 1px 0 rgba(255,255,255,0.25);
}
.step-card h3 { font-family: var(--font-heading); font-size: 1.1rem; font-weight: 400; color: var(--text); margin-bottom: 0.5rem; }
.step-card p { font-size: 0.85rem; color: var(--text-muted); line-height: 1.65; }

/* ---------- Stats — inverted contrast section ---------- */
.land-stats {
  position: relative; overflow: hidden;
  padding: 4.5rem 3rem;
  background:
    radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px) 0 0 / 28px 28px,
    linear-gradient(135deg, #0B1220, #111f3a);
}
.land-stats::before {
  content: ''; position: absolute; top: -120px; left: 50%; transform: translateX(-50%);
  width: 680px; height: 320px; border-radius: 50%;
  background: rgba(77,124,255,0.22); filter: blur(120px); pointer-events: none;
}
.stats-container { position: relative; max-width: 960px; margin: 0 auto; display: flex; align-items: stretch; justify-content: center; gap: 0; }
.stat-item { text-align: center; flex: 1; padding: 0.75rem 1.5rem; transition: transform var(--transition); }
.stat-item:hover { transform: translateY(-3px); }
.stat-big {
  font-family: var(--font-heading); font-size: 2.5rem; font-weight: 400; line-height: 1.1;
  background: linear-gradient(180deg, #fff, #C7D6FF);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.stat-lbl { font-family: var(--font-mono); font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent-secondary); font-weight: 500; margin-top: 0.5rem; }
.stat-divider { width: 1px; align-self: center; height: 54px; background: linear-gradient(180deg, transparent, rgba(255,255,255,0.18), transparent); flex-shrink: 0; }

/* ---------- Contact ---------- */
.land-contact { padding: 6rem 3rem; background: var(--bg); }
.contact-grid { display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; }
.contact-card {
  display: flex; align-items: center; gap: 1rem;
  padding: 1.4rem 1.9rem; min-width: 280px;
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-lg);
  box-shadow: 0 1px 2px rgba(15,23,42,0.04);
  transition: var(--transition);
}
.contact-card:hover { border-color: rgba(0,82,255,0.28); box-shadow: 0 18px 36px -18px rgba(15,23,42,0.22); transform: translateY(-3px); }
.contact-icon {
  width: 46px; height: 46px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--accent), #DCE7FF);
  border: 1px solid rgba(0,82,255,0.15);
  border-radius: 13px;
  display: flex; align-items: center; justify-content: center; font-size: 1.25rem;
}
.contact-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-muted); }
.contact-value { font-size: 0.98rem; font-weight: 600; color: var(--text); margin-top: 0.15rem; }

/* ---------- Footer ---------- */
.land-footer { padding: 2.25rem 3rem; background: var(--card); text-align: center; color: var(--text-muted); font-size: 0.85rem; border-top: 1px solid var(--border); }
.land-footer-links { display: flex; flex-wrap: wrap; gap: 0.7rem; justify-content: center; margin-bottom: 0.7rem; }
.land-footer-links a { color: var(--text-muted); text-decoration: none; font-weight: 600; transition: color var(--transition); }
.land-footer-links a:hover { color: var(--primary); }

/* ---------- Responsive ---------- */
@media (max-width: 900px) {
  .hero { padding: 4.5rem 1.75rem 5rem; }
  .hero-content { grid-template-columns: 1fr; gap: 2.5rem; }
  .hero-right { display: none; }
  .hero-title { font-size: 2.7rem; }
  .how-it-works, .land-contact { padding: 4.5rem 1.75rem; }
  .steps-grid { grid-template-columns: repeat(2, 1fr); gap: 1.75rem 1.5rem; }
  .steps-grid::before { display: none; }
  .stats-container { flex-wrap: wrap; gap: 1.5rem 0; }
  .stat-item { flex-basis: 50%; }
}
@media (max-width: 480px) {
  .land-nav { padding: 0.85rem 1.25rem; }
  .nav-links { display: none; }
  .hero { padding: 3.5rem 1.25rem 4rem; }
  .hero-title { font-size: 2.15rem; }
  .how-it-works, .land-stats, .land-contact, .land-footer { padding-left: 1.25rem; padding-right: 1.25rem; }
  .steps-grid { grid-template-columns: 1fr; }
  .stat-item { flex-basis: 100%; }
  .stat-divider { display: none; }
}
</style>
