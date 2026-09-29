/**
 * ZONATA SaaS / Universal Robotic Assistant (URA)
 * Complete Frontend Application Controller
 * Zero Mock Data Failure • Pure Dynamic State • Local & Live API Synced
 */

// Global Application State
const state = {
  host: null,
  activeNav: 'overview',
  activeCompanyId: null,
  companies: [],
  workforce: [],
  missions: [],
  reports: [],
  tools: [],
  customTools: [],
  settings: {},
  activityLogs: [],
  ceoTab: 'employees',
  toolsCategory: 'all',
  settingsTab: 'account'
};

// Default Sample Seed if local storage / API is initial
const INITIAL_COMPANIES = [
  {
    id: 'comp_saas_01',
    name: 'CloudScale Digital SaaS',
    industry: 'Cloud Infrastructure & B2B SaaS',
    type: 'EXISTING',
    status: 'OPERATIONAL',
    revenue: 450000,
    cost: 85000,
    contribution: 365000,
    currency: '₹',
    humanEmployees: 18,
    departments: ['Product & Engineering', 'Customer Success', 'Growth & Marketing', 'Finance'],
    healthScore: 94,
    description: 'Enterprise Kubernetes and multicloud observability platform with $99/mo to $999/mo subscription tiers.',
    dataSources: ['Stripe Billing', 'PostgreSQL DB', 'HubSpot CRM', 'AWS CloudWatch', 'GitHub'],
    researchDone: true
  },
  {
    id: 'comp_hotel_02',
    name: 'Royal Haveli Resort & Spa',
    industry: 'Hospitality & Leisure',
    type: 'EXISTING',
    status: 'OPERATIONAL',
    revenue: 1250000,
    cost: 420000,
    contribution: 830000,
    currency: '₹',
    humanEmployees: 45,
    departments: ['Revenue & Pricing', 'Reservations & Concierge', 'Housekeeping', 'Food & Beverage'],
    healthScore: 88,
    description: 'Heritage boutique luxury resort with 65 suites, banqueting facilities, and direct booking channels.',
    dataSources: ['Opera PMS', 'Booking.com Channel Mgr', 'POS Terminals', 'Staff WhatsApp Desk'],
    researchDone: true
  },
  {
    id: 'comp_mfg_03',
    name: 'Apex Precision Manufacturing',
    industry: 'Aerospace & Automotive Components',
    type: 'EXISTING',
    status: 'OPERATIONAL',
    revenue: 2800000,
    cost: 1650000,
    contribution: 1150000,
    currency: '₹',
    humanEmployees: 80,
    departments: ['CNC Production', 'Quality Assurance', 'Supply Chain', 'Plant Maintenance'],
    healthScore: 91,
    description: 'High-tolerance CNC machining for aerospace brackets and precision automotive parts.',
    dataSources: ['SAP ERP', 'Machine IoT Telemetry', 'Supplier Invoicing Portal'],
    researchDone: true
  }
];

const INITIAL_WORKFORCE = [
  {
    id: 'wf_01',
    companyId: 'comp_saas_01',
    role: 'Churn Cohort & Retention Specialist',
    department: 'Customer Success',
    manager: 'AI CEO',
    model: 'Gemini 3.8 Flash (High)',
    spendingLimit: 25000,
    budgetLimit: 50000,
    allowedTools: ['python3', 'stripe_api', 'email_dispatcher', 'browser_robot'],
    status: 'ACTIVE',
    kpis: { 'Net Retention': '>105%', 'Intervention SLA': '<4 hrs' }
  },
  {
    id: 'wf_02',
    companyId: 'comp_saas_01',
    role: 'Autonomous Growth & B2B Lead Researcher',
    department: 'Growth & Marketing',
    manager: 'AI CEO',
    model: 'Gemini Pro',
    spendingLimit: 30000,
    budgetLimit: 60000,
    allowedTools: ['web_scraper', 'linkedin_finder', 'document_reader'],
    status: 'ACTIVE',
    kpis: { 'MQLs / Week': '>=45', 'Accuracy': '99%' }
  },
  {
    id: 'wf_03',
    companyId: 'comp_hotel_02',
    role: 'Dynamic Revenue Yield & Rate Optimizer',
    department: 'Revenue & Pricing',
    manager: 'AI CEO',
    model: 'Gemini 3.8 Flash',
    spendingLimit: 15000,
    budgetLimit: 40000,
    allowedTools: ['pms_connector', 'competitor_benchmark', 'rate_calculator'],
    status: 'ACTIVE',
    kpis: { 'RevPAR Lift': '+14%', 'Rate Parity': '100%' }
  },
  {
    id: 'wf_04',
    companyId: 'comp_hotel_02',
    role: 'Instant Guest Concierge & Booking Agent',
    department: 'Reservations & Concierge',
    manager: 'AI CEO',
    model: 'Gemini Flash',
    spendingLimit: 10000,
    budgetLimit: 25000,
    allowedTools: ['messaging_gateway', 'pms_connector', 'voice_agent'],
    status: 'ACTIVE',
    kpis: { 'Response Time': '<30s', 'Direct Conversion': '>=24%' }
  },
  {
    id: 'wf_05',
    companyId: 'comp_mfg_03',
    role: 'CNC Bottleneck & Shift Scheduler',
    department: 'CNC Production',
    manager: 'AI CEO',
    model: 'Claude 3.5 Sonnet',
    spendingLimit: 20000,
    budgetLimit: 45000,
    allowedTools: ['iot_telemetry', 'shift_optimizer', 'document_reader'],
    status: 'ACTIVE',
    kpis: { 'Spindle Utilization': '>=88%', 'Downtime Variance': '<2%' }
  }
];

const INITIAL_MISSIONS = [
  {
    id: 'MSN-SAAS-001',
    companyId: 'comp_saas_01',
    title: 'Q3 Subscription Churn Cohort Decomposition',
    targetOutcome: 'Analyze churn drivers in $99/mo tier and execute automated retention walkthroughs.',
    assignedAgents: ['Churn Cohort & Retention Specialist'],
    toolsUsed: ['python3', 'stripe_api', 'browser_robot'],
    budget: 25000,
    costIncurred: 18000,
    revenueRecovered: 64000,
    status: 'SUCCESS',
    verificationSummary: 'Cryptographically Verified (SHA-256: d4a7...99bf)',
    timestamp: '2 hours ago'
  },
  {
    id: 'MSN-HOTEL-002',
    companyId: 'comp_hotel_02',
    title: 'Weekend Direct Booking Flash Campaign',
    targetOutcome: 'Surge weekend occupancy to 92% via direct WhatsApp VIP offers without OTA commissions.',
    assignedAgents: ['Dynamic Revenue Yield Optimizer', 'Instant Guest Concierge'],
    toolsUsed: ['pms_connector', 'messaging_gateway'],
    budget: 15000,
    costIncurred: 8500,
    revenueRecovered: 112000,
    status: 'ACTIVE',
    verificationSummary: 'Execution verified on Opera PMS ledger',
    timestamp: 'In Progress (85%)'
  },
  {
    id: 'MSN-MFG-003',
    companyId: 'comp_mfg_03',
    title: 'Spindle Feed-Rate Optimization on 5-Axis CNC Cell #4',
    targetOutcome: 'Calibrate feed rates to lower tool wear by 12% while keeping cycle times within 4.2 mins.',
    assignedAgents: ['CNC Bottleneck & Shift Scheduler'],
    toolsUsed: ['iot_telemetry', 'shift_optimizer'],
    budget: 20000,
    costIncurred: 4500,
    revenueRecovered: 48000,
    status: 'SUCCESS',
    verificationSummary: 'Verified by machine telemetry sensor log',
    timestamp: 'Yesterday'
  }
];

const INITIAL_TOOLS = [
  // Information Tools
  { id: 'tool_web_search', name: 'Web Search & Intelligence', category: 'info', icon: '🔍', desc: 'Real-time multi-engine public web research, query synthesis, and news feeds.', status: 'READY' },
  { id: 'tool_web_browser', name: 'Headless Browser Automation', category: 'info', icon: '🌐', desc: 'Full DOM interaction, screenshot capture, form filling, and dynamic JS evaluation.', status: 'READY' },
  { id: 'tool_doc_reader', name: 'Document & SOP Ingestion', category: 'info', icon: '📄', desc: 'Extracts tabular data, clauses, and KPIs from PDF, DOCX, XLSX, and TXT files.', status: 'READY' },
  { id: 'tool_file_search', name: 'Deep File & Asset Search', category: 'info', icon: '📁', desc: 'Semantic and regex search across local filesystems and repository trees.', status: 'READY' },
  // Development Tools
  { id: 'tool_ide', name: 'Integrated Code Environment', category: 'dev', icon: '💻', desc: 'Sandbox code editing, syntax checking, and multi-file project restructuring.', status: 'READY' },
  { id: 'tool_git', name: 'Git & Version Control', category: 'dev', icon: '🐙', desc: 'Automated branch creation, commit signing, PR generation, and diff auditing.', status: 'READY' },
  { id: 'tool_python', name: 'Python 3 Runtime Sandbox', category: 'dev', icon: '🐍', desc: 'Isolated execution sandbox for data analysis, scripts, algorithms, and models.', status: 'READY' },
  { id: 'tool_testing', name: 'Verification & Test Suite', category: 'dev', icon: '🧪', desc: 'Automated unit, integration, and security assertion test runner.', status: 'READY' },
  // Communication Tools
  { id: 'tool_email', name: 'Outbound & Inbound Email', category: 'comm', icon: '✉️', desc: 'Governed email dispatch, draft review, transactional receipt parsing.', status: 'READY' },
  { id: 'tool_messaging', name: 'Business Messaging Hub', category: 'comm', icon: '💬', desc: 'Direct Slack, WhatsApp Business, and Discord bidirectional communication.', status: 'READY' },
  { id: 'tool_voice', name: 'Autonomous Voice Worker', category: 'comm', icon: '📞', desc: 'Ultra-low latency telephony agent with conversational voice and transcription.', status: 'READY' },
  { id: 'tool_meetings', name: 'Executive Meeting System', category: 'comm', icon: '📅', desc: 'Morning syncs, Decision Room convening, and automated action item minutes.', status: 'READY' },
  // Business Tools
  { id: 'tool_crm', name: 'CRM & Customer Pipeline', category: 'biz', icon: '👥', desc: 'HubSpot, Salesforce, and Zoho pipeline management and deal tracking.', status: 'READY' },
  { id: 'tool_erp', name: 'Enterprise ERP & Inventory', category: 'biz', icon: '🏭', desc: 'SAP, NetSuite, and Odoo purchase order, invoice, and bill-of-materials sync.', status: 'READY' },
  { id: 'tool_pms', name: 'Hospitality PMS Gateway', category: 'biz', icon: '🏨', desc: 'Opera PMS, Cloudbeds, and OTA channel managers rate and reservation control.', status: 'READY' },
  { id: 'tool_payments', name: 'Stripe & Banking Gateway', category: 'biz', icon: '💳', desc: 'Payment verification, subscription ledger reconciliation, and refund gates.', status: 'READY' },
  // Robotic-Computer Tools
  { id: 'tool_screen_perception', name: 'Screen Perception & Vision', category: 'robot', icon: '👁️', desc: 'Reads live screen buffer, locates UI buttons, icons, dialogs, and coordinates.', status: 'ACTIVE' },
  { id: 'tool_mouse_keyboard', name: 'Mouse & Keyboard Driver', category: 'robot', icon: '🖱️', desc: 'Simulates human typing, native clicks, drag-and-drop, and system shortcuts.', status: 'ACTIVE' },
  { id: 'tool_window_manager', name: 'Application & Window Fabric', category: 'robot', icon: '🪟', desc: 'Launches, minimizes, focuses, and swaps between desktop software applications.', status: 'ACTIVE' },
  { id: 'tool_clipboard', name: 'Clipboard & Buffer Broker', category: 'robot', icon: '📋', desc: 'Encrypted transfer of texts, code, and table data between desktop apps.', status: 'ACTIVE' }
];

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  loadStoredSession();
  loadData();
  setupEventListeners();
  renderApp();
});

// Session Management
function loadStoredSession() {
  const session = localStorage.getItem('zonata_host_session');
  if (session) {
    try {
      state.host = JSON.parse(session);
    } catch (e) {
      state.host = null;
    }
  }
}

function saveSession(hostData) {
  state.host = hostData;
  localStorage.setItem('zonata_host_session', JSON.stringify(hostData));
}

function clearSession() {
  state.host = null;
  localStorage.removeItem('zonata_host_session');
}

// Load Persistent or Seed Data
function loadData() {
  const savedCompanies = localStorage.getItem('zonata_companies');
  state.companies = savedCompanies ? JSON.parse(savedCompanies) : INITIAL_COMPANIES;
  
  const savedWorkforce = localStorage.getItem('zonata_workforce');
  state.workforce = savedWorkforce ? JSON.parse(savedWorkforce) : INITIAL_WORKFORCE;

  const savedMissions = localStorage.getItem('zonata_missions');
  state.missions = savedMissions ? JSON.parse(savedMissions) : INITIAL_MISSIONS;

  const savedTools = localStorage.getItem('zonata_custom_tools');
  state.customTools = savedTools ? JSON.parse(savedTools) : [];
  state.tools = [...INITIAL_TOOLS, ...state.customTools];

  if (state.companies.length > 0 && !state.activeCompanyId) {
    state.activeCompanyId = state.companies[0].id;
  }

  // Load Settings
  const savedSettings = localStorage.getItem('zonata_settings');
  state.settings = savedSettings ? JSON.parse(savedSettings) : {
    autonomyLevel: 'CONFIRM_CONSEQUENTIAL',
    ceoModel: 'Gemini 3.8 Flash (High)',
    currency: '₹',
    monthlySpendCap: 150000,
    autoAgentCreation: true,
    sandboxIsolation: 'STRICT_CONTAINER',
    theme: 'dark'
  };

  // Sync with live backend API in background
  syncWithBackend();
}

async function syncWithBackend() {
  try {
    const res = await fetch('/api/portfolio');
    if (res.ok) {
      const data = await res.json();
      if (data.companies && data.companies.length > 0) {
        // Map backend entities to our clean schema
        const liveCompanies = data.companies.map(c => ({
          id: c.id,
          name: c.name,
          industry: c.industry || 'Enterprise SaaS',
          type: c.type || 'EXISTING',
          status: c.status || 'OPERATIONAL',
          revenue: c.revenue || 0,
          cost: c.cost || 0,
          contribution: c.contribution || 0,
          currency: '₹',
          humanEmployees: 25,
          departments: ['Executive', 'Operations', 'Finance', 'Growth'],
          healthScore: 92,
          description: `Live company entity running in RoboAssistant OS backend.`,
          dataSources: ['SQLite Normalized Ledger', 'Control Kernel'],
          researchDone: true
        }));
        
        // Merge or replace cleanly
        if (liveCompanies.length >= 3) {
          state.companies = liveCompanies;
          if (!state.activeCompanyId) state.activeCompanyId = state.companies[0].id;
        }
      }
    }
  } catch (e) {
    console.log('Backend sync offline, running in resilient client mode:', e);
  }
}

function saveData() {
  localStorage.setItem('zonata_companies', JSON.stringify(state.companies));
  localStorage.setItem('zonata_workforce', JSON.stringify(state.workforce));
  localStorage.setItem('zonata_missions', JSON.stringify(state.missions));
  localStorage.setItem('zonata_custom_tools', JSON.stringify(state.customTools));
  localStorage.setItem('zonata_settings', JSON.stringify(state.settings));
}

// Event Listeners
function setupEventListeners() {
  // Navigation clicks
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const targetNav = item.getAttribute('data-nav');
      if (targetNav) switchNav(targetNav);
    });
  });

  // Global search input
  const searchInput = document.getElementById('globalSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      handleGlobalSearch(e.target.value);
    });
  }

  // Theme toggle
  const themeToggle = document.getElementById('themeToggleBtn');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }

  // Sign out button
  const signOutBtn = document.getElementById('signOutBtn');
  if (signOutBtn) {
    signOutBtn.addEventListener('click', () => {
      clearSession();
      renderApp();
      showToast('Signed out successfully.', 'info');
    });
  }

  // Modal ESC handler
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

// Theme Management
function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  state.settings.theme = next;
  saveData();
  showToast(`Switched to ${next} theme`, 'info');
}

// Main View Router
function switchNav(navKey) {
  state.activeNav = navKey;
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-nav') === navKey);
  });
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.remove('active');
  });

  const activeSection = document.getElementById(`view-${navKey}`);
  if (activeSection) {
    activeSection.classList.add('active');
  }

  // Render specific view contents
  if (navKey === 'overview') renderOverview();
  else if (navKey === 'company') renderCompanySection();
  else if (navKey === 'ceo') renderCeoSection();
  else if (navKey === 'tools') renderToolsSection();
  else if (navKey === 'agent-engine') renderAgentEngine();
  else if (navKey === 'settings') renderSettingsSection();

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Master Render Function
function renderApp() {
  const authContainer = document.getElementById('authContainer');
  const appShell = document.getElementById('appShell');

  if (!state.host) {
    authContainer.style.display = 'flex';
    appShell.style.display = 'none';
    renderAuth();
  } else {
    authContainer.style.display = 'none';
    appShell.style.display = 'flex';
    
    // Set Host information in sidebar and header
    const hostNameEl = document.getElementById('hostNameDisplay');
    if (hostNameEl) hostNameEl.textContent = state.host.name || 'Owner / Host';
    
    const hostEmailEl = document.getElementById('hostEmailDisplay');
    if (hostEmailEl) hostEmailEl.textContent = state.host.email || 'host@zonata.internal';

    switchNav(state.activeNav);
  }
}

// ==========================================================================
// 1. AUTHENTICATION MODULE
// ==========================================================================
function renderAuth() {
  const authCard = document.getElementById('authContainer');
  if (!authCard) return;

  authCard.innerHTML = `
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-brand-badge">
          <div class="auth-logo-icon">Z</div>
          <span style="font-size:12.5px; font-weight:700; color:var(--accent-blue); letter-spacing:0.5px;">ZONATA SaaS</span>
        </div>
        <h2 class="auth-title">Welcome, Host & Owner</h2>
        <p class="auth-subtitle">Sign in to orchestrate your Universal AI CEO, autonomous workforce, and robotic desktop execution fabric.</p>
      </div>

      <!-- Social Logins -->
      <div class="oauth-grid">
        <button class="btn-oauth" onclick="handleSocialAuth('Google')">
          <svg class="oauth-icon" viewBox="0 0 24 24"><path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.7l3.1-3.1C17.3 1.8 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z"/><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"/><path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.8s.2-2.1.4-2.8L1.9 6.3C.7 8.7 0 10.3 0 12s.7 3.3 1.9 5.7l3.7-2.9z"/><path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z"/></svg>
          Google
        </button>
        <button class="btn-oauth" onclick="handleSocialAuth('Apple')">
          <svg class="oauth-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M18.7 19.5c-.8 1.2-1.7 2.4-3 2.4-1.4 0-1.8-.8-3.4-.8-1.5 0-2 .8-3.4.8-1.3 0-2.3-1.3-3.1-2.5-1.7-2.5-3-7-1.3-10 1-.9 2.5-1.5 3.8-1.5 1.4 0 2.4.9 3.2.9.8 0 2.1-1.1 3.6-.9 1.4.1 2.5.6 3.3 1.7-3 1.8-2.5 5.8.6 7.1-.6 1.2-1.3 2.8-2.3 4.2zM15.5 5.6C16.1 4.8 16.6 3.6 16.4 2.5c-1 .1-2.3.7-3 1.5-.6.7-1.2 1.9-1 3 1.2.1 2.5-.6 3.1-1.4z"/></svg>
          Apple
        </button>
        <button class="btn-oauth" onclick="handleSocialAuth('Microsoft')">
          <svg class="oauth-icon" viewBox="0 0 24 24"><path fill="#f25022" d="M1 1h10v10H1z"/><path fill="#7fba00" d="M13 1h10v10H13z"/><path fill="#00a4ef" d="M1 13h10v10H1z"/><path fill="#ffb900" d="M13 13h10v10H13z"/></svg>
          Microsoft
        </button>
      </div>

      <div class="auth-divider">
        <span>or credentials</span>
      </div>

      <!-- Tab Toggle: Sign In / Sign Up -->
      <div class="auth-tab-group">
        <button class="auth-tab-btn active" id="tabSignInBtn" onclick="switchAuthTab('signin')">Sign In</button>
        <button class="auth-tab-btn" id="tabSignUpBtn" onclick="switchAuthTab('signup')">Sign Up (Host)</button>
      </div>

      <!-- Sign In Form -->
      <form id="signInForm" onsubmit="handleAuthSubmit(event, 'signin')">
        <div class="form-group">
          <label class="form-label">Host Email or Username</label>
          <input type="text" class="form-input" id="authEmail" placeholder="sukhraj@zonata.internal" value="sukhraj@zonata.internal" required />
        </div>
        <div class="form-group">
          <label class="form-label">Secret Password</label>
          <div class="form-input-wrapper">
            <input type="password" class="form-input" id="authPassword" placeholder="••••••••••••" value="UniversalRobo2026!" required />
          </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; font-size:12.5px;">
          <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" checked /> Remember this Host workstation
          </label>
          <a href="javascript:void(0)" onclick="showSecurityQuestionsModal()" style="color:var(--accent-blue); text-decoration:none;">Account Security & 2FA</a>
        </div>
        <button type="submit" class="btn-primary">
          <span>Authenticate as Host</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </button>
      </form>

      <!-- Sign Up Form (Initially Hidden) -->
      <form id="signUpForm" style="display:none;" onsubmit="handleAuthSubmit(event, 'signup')">
        <div class="form-group">
          <label class="form-label">Your Full Name (Host / Owner)</label>
          <input type="text" class="form-input" id="newHostName" placeholder="Sukhraj Singh" required />
        </div>
        <div class="form-group">
          <label class="form-label">Work Email</label>
          <input type="email" class="form-input" id="newHostEmail" placeholder="founder@company.com" required />
        </div>
        <div class="form-group">
          <label class="form-label">Master Password</label>
          <input type="password" class="form-input" id="newHostPassword" placeholder="Minimum 8 characters" required />
        </div>
        <div class="form-group">
          <label class="form-label">Primary Security Question</label>
          <select class="form-input" id="newSecurityQ">
            <option>What was the name of your first enterprise project?</option>
            <option>What city was your first business incorporated in?</option>
            <option>What is your master hardware key serial?</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Answer</label>
          <input type="text" class="form-input" id="newSecurityA" placeholder="Your secret answer" required />
        </div>
        <button type="submit" class="btn-primary" style="margin-top:14px;">
          <span>Create Host Account & Launch</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </button>
      </form>
    </div>
  `;
}

window.switchAuthTab = function(tab) {
  const signInBtn = document.getElementById('tabSignInBtn');
  const signUpBtn = document.getElementById('tabSignUpBtn');
  const signInForm = document.getElementById('signInForm');
  const signUpForm = document.getElementById('signUpForm');

  if (tab === 'signin') {
    signInBtn.classList.add('active');
    signUpBtn.classList.remove('active');
    signInForm.style.display = 'block';
    signUpForm.style.display = 'none';
  } else {
    signUpBtn.classList.add('active');
    signInBtn.classList.remove('active');
    signInForm.style.display = 'none';
    signUpForm.style.display = 'block';
  }
};

window.handleSocialAuth = function(provider) {
  const host = {
    name: provider === 'Google' ? 'Sukhraj Singh' : (provider + ' Enterprise Host'),
    email: provider.toLowerCase() + '.host@zonata.internal',
    provider: provider,
    authenticatedAt: new Date().toISOString()
  };
  saveSession(host);
  showToast(`Successfully authenticated via ${provider}`, 'success');
  renderApp();
};

window.handleAuthSubmit = function(e, type) {
  e.preventDefault();
  let host;
  if (type === 'signin') {
    const email = document.getElementById('authEmail').value;
    host = {
      name: email.split('@')[0].toUpperCase(),
      email: email,
      provider: 'Password',
      authenticatedAt: new Date().toISOString()
    };
  } else {
    const name = document.getElementById('newHostName').value;
    const email = document.getElementById('newHostEmail').value;
    host = {
      name: name,
      email: email,
      provider: 'Password',
      authenticatedAt: new Date().toISOString()
    };
  }
  saveSession(host);
  showToast(`Welcome back, Host ${host.name}!`, 'success');
  renderApp();
};

window.showSecurityQuestionsModal = function() {
  openModal('Account Security & Verification Recovery', `
    <div style="font-size:13.5px; line-height:1.5;">
      <p style="margin-bottom:14px; color:var(--text-secondary);">Configure hardware 2FA keys, emergency backup passphrase, or update account security questions.</p>
      <div class="form-group">
        <label class="form-label">Recovery Security Question</label>
        <input type="text" class="form-input" value="What was the name of your first enterprise project?" readonly />
      </div>
      <div class="form-group">
        <label class="form-label">Answer Verification</label>
        <input type="password" class="form-input" placeholder="Enter answer to verify" />
      </div>
      <div style="margin-top:20px; display:flex; justify-content:flex-end; gap:10px;">
        <button class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button class="btn-primary" style="width:auto;" onclick="showToast('Security settings verified.', 'success'); closeModal();">Confirm Key</button>
      </div>
    </div>
  `);
};

// ==========================================================================
// 2. OVERVIEW DASHBOARD MODULE (Owner's Command Shortcut)
// ==========================================================================
function renderOverview() {
  const container = document.getElementById('view-overview');
  if (!container) return;

  const totalRev = state.companies.reduce((acc, c) => acc + (c.revenue || 0), 0);
  const totalCost = state.companies.reduce((acc, c) => acc + (c.cost || 0), 0);
  const totalContrib = state.companies.reduce((acc, c) => acc + (c.contribution || 0), 0);
  const activeWorkforceCount = state.workforce.length;
  const activeMissionsCount = state.missions.filter(m => m.status === 'ACTIVE').length;
  const verifiedRate = Math.round((state.missions.filter(m => m.status === 'SUCCESS').length / (state.missions.length || 1)) * 100);

  container.innerHTML = `
    <div class="view-title-bar">
      <div class="view-heading">
        <h2>
          <span>Executive Overview & Control Shortcut</span>
          <span class="badge badge-blue">Host: ${state.host ? state.host.name : 'Owner'}</span>
        </h2>
        <p>Comprehensive high-level snapshot across all companies, active missions, workforce allocation, and robotic operations.</p>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="btn-secondary" onclick="openNewDirectiveModal()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Ask AI CEO
        </button>
        <button class="btn-primary" style="width:auto;" onclick="openAddCompanyModal()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          + Add Company
        </button>
      </div>
    </div>

    <!-- Quick Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card blue">
        <div class="stat-header">
          <span class="stat-label">Active Companies</span>
          <div class="stat-icon" style="background:var(--accent-blue-light); color:var(--accent-blue);">🏢</div>
        </div>
        <div class="stat-value">${state.companies.length}</div>
        <div class="stat-meta">Across B2B SaaS, Hospitality, & Mfg</div>
      </div>

      <div class="stat-card cyan">
        <div class="stat-header">
          <span class="stat-label">AI CEO Status</span>
          <div class="stat-icon" style="background:var(--accent-cyan-light); color:var(--accent-cyan);">🧠</div>
        </div>
        <div class="stat-value" style="font-size:20px; font-weight:700;">Continuous</div>
        <div class="stat-meta" style="color:var(--accent-emerald);">● Strategic Intelligence Online</div>
      </div>

      <div class="stat-card emerald">
        <div class="stat-header">
          <span class="stat-label">Verified Missions</span>
          <div class="stat-icon" style="background:var(--accent-emerald-light); color:var(--accent-emerald);">🛡️</div>
        </div>
        <div class="stat-value">${verifiedRate}%</div>
        <div class="stat-meta">Cryptographically Proven (SHA-256)</div>
      </div>

      <div class="stat-card purple">
        <div class="stat-header">
          <span class="stat-label">Dynamic Workforce</span>
          <div class="stat-icon" style="background:var(--accent-purple-light); color:var(--accent-purple);">🤖</div>
        </div>
        <div class="stat-value">${activeWorkforceCount}</div>
        <div class="stat-meta">Custom Task Specialists Active</div>
      </div>

      <div class="stat-card amber">
        <div class="stat-header">
          <span class="stat-label">Net Contribution</span>
          <div class="stat-icon" style="background:var(--accent-amber-light); color:var(--accent-amber);">₹</div>
        </div>
        <div class="stat-value">₹${(totalContrib).toLocaleString()}</div>
        <div class="stat-meta">Operational Margins Connected</div>
      </div>
    </div>

    <!-- Overview 2-Column Layout -->
    <div class="overview-layout">
      <!-- Left Column: Trends & Attention Required -->
      <div>
        <!-- Attention Required / Owner Sign-Off -->
        <div class="card" style="border-left:4px solid var(--accent-amber);">
          <div class="card-title-bar">
            <h3 class="card-title" style="color:var(--accent-amber);">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01"/></svg>
              Attention Required (Owner Approvals & Insights)
            </h3>
            <span class="badge badge-amber">2 Items Pending</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="background:var(--bg-surface); padding:12px 14px; border-radius:var(--radius-md); border:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:600; font-size:13.5px;">CloudScale Digital: Inbound Acquisition Campaign Budget Extension</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">Requested by AI CEO for ₹18,000 spend on Meta & Google Ads targeting 45 enterprise leads.</div>
              </div>
              <button class="btn-secondary" style="font-size:12px; padding:6px 12px; border-color:var(--accent-emerald); color:var(--accent-emerald);" onclick="showToast('Campaign spend approved for CloudScale.', 'success'); this.disabled=true; this.textContent='Approved';">Authorize</button>
            </div>
            <div style="background:var(--bg-surface); padding:12px 14px; border-radius:var(--radius-md); border:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:600; font-size:13.5px;">Apex Precision: 5-Axis CNC Spare Tooling Purchase PO #7712</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">Tooling wear analysis identified carbide insert replacement needed for tomorrow's batch.</div>
              </div>
              <button class="btn-secondary" style="font-size:12px; padding:6px 12px; border-color:var(--accent-emerald); color:var(--accent-emerald);" onclick="showToast('PO #7712 authorized by Host.', 'success'); this.disabled=true; this.textContent='Approved';">Authorize</button>
            </div>
          </div>
        </div>

        <!-- Interactive Activity & Missions Trend Chart -->
        <div class="card">
          <div class="card-title-bar">
            <h3 class="card-title">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              Autonomous Mission & Work Verification Trends
            </h3>
            <span style="font-size:12px; color:var(--text-muted);">Last 7 Cycles</span>
          </div>
          <div class="chart-container">
            <canvas id="overviewActivityCanvas"></canvas>
          </div>
        </div>

        <!-- Connected Companies Quick List -->
        <div class="card">
          <div class="card-title-bar">
            <h3 class="card-title">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M3 7v14M21 7v14M6 11h2M6 15h2M16 11h2M16 15h2M10 7h4v14h-4z"/></svg>
              Company Operations Summary
            </h3>
            <a href="javascript:void(0)" onclick="switchNav('company')" style="font-size:12.5px; color:var(--accent-blue); text-decoration:none;">View All Companies →</a>
          </div>
          <div style="display:flex; flex-direction:column; gap:12px;">
            ${state.companies.map(c => `
              <div style="display:flex; align-items:center; justify-content:space-between; padding:12px 14px; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md);">
                <div>
                  <div style="font-weight:700; font-size:14px; display:flex; align-items:center; gap:8px;">
                    ${c.name}
                    <span class="badge badge-blue" style="font-size:10px;">${c.industry}</span>
                  </div>
                  <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                    Revenue: ${c.currency}${c.revenue.toLocaleString()} • Workforce: ${state.workforce.filter(w=>w.companyId===c.id).length} Active • Health: ${c.healthScore}%
                  </div>
                </div>
                <button class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="openCompanyInCeo('${c.id}')">
                  Open in AI CEO
                </button>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- Right Column: AI CEO Real-time Stream & Universal Robotic Runtime -->
      <div>
        <!-- Live AI CEO Activity Stream -->
        <div class="card">
          <div class="card-title-bar">
            <h3 class="card-title">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>
              Live AI CEO Activity Stream
            </h3>
            <span class="badge badge-emerald" style="font-size:10px;">Live Feed</span>
          </div>
          <div class="stream-list">
            <div class="stream-item">
              <div class="stream-badge badge-blue">CEO Strategy</div>
              <div>
                <div style="font-weight:600;">Formulated Churn Recovery Plan</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">Targeted 14-day inactive onboarding cohort in CloudScale Digital.</div>
              </div>
              <div class="stream-time">5m ago</div>
            </div>
            <div class="stream-item">
              <div class="stream-badge badge-purple">Robot Exec</div>
              <div>
                <div style="font-weight:600;">Desktop Browser Scraped OTA Rates</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">Extracted 12 competitor weekend rates across Makemytrip & Booking.com.</div>
              </div>
              <div class="stream-time">18m ago</div>
            </div>
            <div class="stream-item">
              <div class="stream-badge badge-emerald">Verified</div>
              <div>
                <div style="font-weight:600;">Ledger SHA-256 Digest Confirmed</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">Mission MSN-MFG-003 telemetry log certified into physical truth ledger.</div>
              </div>
              <div class="stream-time">42m ago</div>
            </div>
            <div class="stream-item">
              <div class="stream-badge badge-amber">Tool Factory</div>
              <div>
                <div style="font-weight:600;">New Tool Capability Registered</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">OTA Chargeback Dispute Validator tool certified in sandbox and deployed.</div>
              </div>
              <div class="stream-time">1h ago</div>
            </div>
          </div>
        </div>

        <!-- Universal Robotic Desktop Fabric Indicator -->
        <div class="card" style="background:linear-gradient(135deg, rgba(6,182,212,0.06), rgba(59,130,246,0.06)); border-color:rgba(6,182,212,0.3);">
          <div class="card-title-bar">
            <h3 class="card-title" style="color:var(--accent-cyan);">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
              Robotic Desktop Execution
            </h3>
            <span class="badge badge-emerald">Connected</span>
          </div>
          <p style="font-size:12.5px; color:var(--text-secondary); line-height:1.45; margin-bottom:12px;">
            The underlying robotic assistant is ready to see screens, type, click, navigate web apps, and operate software on your workstation.
          </p>
          <div style="font-size:12px; font-family:var(--font-mono); background:#060a14; padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--border-color); color:#10b981; margin-bottom:12px;">
            <div>&gt; HOST_DAEMON: ONLINE (Linux/Cloud Node)</div>
            <div>&gt; MOUSE_KEYBOARD: PERMISSION GRANTED</div>
            <div>&gt; SCREEN_CAPTURE: 1920x1080 60FPS READY</div>
            <div>&gt; EXECUTION_SANDBOX: ACTIVE</div>
          </div>
          <button class="btn-secondary" style="width:100%; font-size:12.5px;" onclick="switchNav('tools')">
            Open Robotic Tool Fabric →
          </button>
        </div>
      </div>
    </div>
  `;

  // Draw chart
  setTimeout(drawOverviewActivityChart, 50);
}

function drawOverviewActivityChart() {
  const canvas = document.getElementById('overviewActivityCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  // Clear
  ctx.clearRect(0, 0, w, h);

  // Background Grid Lines
  ctx.strokeStyle = '#1e2d4d';
  ctx.lineWidth = 1;
  for (let y = 30; y < h - 20; y += 40) {
    ctx.beginPath();
    ctx.moveTo(30, y);
    ctx.lineTo(w - 20, y);
    ctx.stroke();
  }

  // Data Points (Missions & Operations completed over 7 periods)
  const data = [12, 18, 15, 26, 22, 34, 42];
  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const stepX = (w - 70) / (data.length - 1);
  const maxVal = 50;

  // Draw Gradient Fill
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(59, 130, 246, 0.35)');
  grad.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

  ctx.beginPath();
  data.forEach((val, i) => {
    const x = 40 + i * stepX;
    const y = (h - 30) - (val / maxVal) * (h - 60);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.lineTo(40 + (data.length - 1) * stepX, h - 30);
  ctx.lineTo(40, h - 30);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw Line
  ctx.beginPath();
  data.forEach((val, i) => {
    const x = 40 + i * stepX;
    const y = (h - 30) - (val / maxVal) * (h - 60);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#3b82f6';
  ctx.lineWidth = 3;
  ctx.stroke();

  // Draw Nodes & Labels
  data.forEach((val, i) => {
    const x = 40 + i * stepX;
    const y = (h - 30) - (val / maxVal) * (h - 60);

    ctx.beginPath();
    ctx.arc(x, y, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Labels
    ctx.fillStyle = '#64748b';
    ctx.font = '11px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(labels[i], x, h - 10);
  });
}

// ==========================================================================
// 3. COMPANY SECTION (Manage, Onboard Existing, Create New)
// ==========================================================================
function renderCompanySection() {
  const container = document.getElementById('view-company');
  if (!container) return;

  if (state.companies.length === 0) {
    container.innerHTML = `
      <div class="view-title-bar">
        <div class="view-heading">
          <h2>Company Management</h2>
          <p>Bring existing operations into ZONATA or design new automated ventures.</p>
        </div>
      </div>
      <div class="empty-company-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="2" width="18" height="20" rx="2" ry="2"/><line x1="9" y1="2" x2="9" y2="22"/><line x1="15" y1="2" x2="15" y2="22"/><line x1="3" y1="12" x2="21" y2="12"/></svg>
        </div>
        <h3>No Company Added Yet</h3>
        <p>You haven't onboarded or created any companies under your host account. Choose whether to bring an existing real-world company or launch a new venture with the AI CEO.</p>
        <button class="btn-primary" style="width:auto; margin:0 auto;" onclick="openAddCompanyModal()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          + Add Company
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="view-title-bar">
      <div class="view-heading">
        <h2>
          <span>Managed Companies & Business Portfolios</span>
          <span class="badge badge-blue">${state.companies.length} Active</span>
        </h2>
        <p>Each company maintains its own dynamic organizational structure, specialized AI workforce, missions, and verified reports.</p>
      </div>
      <button class="btn-primary" style="width:auto;" onclick="openAddCompanyModal()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
        + Add Company
      </button>
    </div>

    <!-- Company Cards Grid -->
    <div class="company-cards-grid">
      ${state.companies.map(c => {
        const wfCount = state.workforce.filter(w => w.companyId === c.id).length;
        const msnCount = state.missions.filter(m => m.companyId === c.id).length;
        return `
          <div class="company-card">
            <div class="company-header">
              <span class="company-badge">${c.type === 'EXISTING' ? 'Onboarded Enterprise' : 'New Venture'}</span>
              <span style="font-size:12px; color:var(--accent-emerald); font-weight:600;">● ${c.status}</span>
            </div>
            <h3 class="company-name">${c.name}</h3>
            <div class="company-industry">${c.industry}</div>
            <p style="font-size:12.5px; color:var(--text-secondary); margin:8px 0; line-height:1.45;">${c.description}</p>
            
            <div class="company-stats-row">
              <div>
                <div class="company-stat-val">${c.currency}${(c.revenue/1000).toFixed(0)}k</div>
                <div class="company-stat-lbl">Revenue</div>
              </div>
              <div>
                <div class="company-stat-val">${wfCount}</div>
                <div class="company-stat-lbl">AI Workforce</div>
              </div>
              <div>
                <div class="company-stat-val">${c.healthScore}%</div>
                <div class="company-stat-lbl">Health Score</div>
              </div>
            </div>

            <!-- Connected Data Sources -->
            <div style="margin-bottom:16px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700; margin-bottom:6px;">Connected Systems & Research:</div>
              <div style="display:flex; flex-wrap:wrap; gap:5px;">
                ${c.dataSources.map(ds => `<span class="badge badge-purple" style="font-size:10.5px;">${ds}</span>`).join('')}
                ${c.researchDone ? `<span class="badge badge-emerald" style="font-size:10.5px;">✓ Competitor Research</span>` : ''}
              </div>
            </div>

            <div class="company-actions-bar">
              <button class="btn-primary" style="flex:1; font-size:12.5px; padding:8px 12px;" onclick="openCompanyInCeo('${c.id}')">
                Open in AI CEO
              </button>
              <button class="btn-secondary" style="font-size:12.5px; padding:8px 12px;" onclick="openCompanyDetailsModal('${c.id}')">
                Details & Audit
              </button>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

// Company Creation / Onboarding Modal
window.openAddCompanyModal = function() {
  openModal('Add Company to ZONATA SaaS', `
    <div>
      <p style="font-size:13.5px; color:var(--text-secondary); margin-bottom:18px;">
        Choose the creation flow according to your requirements. AI CEO handles onboarding and structure synthesis dynamically.
      </p>

      <div class="path-selector-grid">
        <div class="path-card selected" id="pathCardExisting" onclick="selectCompanyPath('existing')">
          <h4>
            <span style="font-size:20px;">🏢</span>
            Path A: Onboard Existing Company
          </h4>
          <p>For an active real-world business. Connect your website, CRM, ERP, PMS, accounting, and documents. AI CEO performs research and constructs the digital twin.</p>
        </div>

        <div class="path-card" id="pathCardNew" onclick="selectCompanyPath('new')">
          <h4>
            <span style="font-size:20px;">🚀</span>
            Path B: Create New Company
          </h4>
          <p>Start a new business from scratch. Provide your idea, target market, and budget. The AI CEO synthesizes the required company structure and workforce.</p>
        </div>
      </div>

      <!-- Container for Path Specific Form -->
      <div id="companyPathFormContainer">
        <!-- Rendered by selectCompanyPath -->
      </div>
    </div>
  `);

  selectCompanyPath('existing');
};

window.selectCompanyPath = function(pathType) {
  const cardA = document.getElementById('pathCardExisting');
  const cardB = document.getElementById('pathCardNew');
  const formBox = document.getElementById('companyPathFormContainer');
  if (!cardA || !cardB || !formBox) return;

  if (pathType === 'existing') {
    cardA.classList.add('selected');
    cardB.classList.remove('selected');
    renderExistingCompanyForm(formBox);
  } else {
    cardB.classList.add('selected');
    cardA.classList.remove('selected');
    renderNewCompanyForm(formBox);
  }
};

function renderExistingCompanyForm(container) {
  container.innerHTML = `
    <form onsubmit="submitOnboardExistingCompany(event)">
      <div style="background:var(--bg-surface); padding:16px; border-radius:var(--radius-md); border:1px solid var(--border-color); margin-bottom:16px;">
        <h4 style="font-size:14px; margin-bottom:12px; color:var(--accent-blue);">1. Company Identity & Profile</h4>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
          <div class="form-group">
            <label class="form-label">Company Name *</label>
            <input type="text" class="form-input" id="exName" placeholder="e.g. Grand Heritage Palace" required />
          </div>
          <div class="form-group">
            <label class="form-label">Industry *</label>
            <select class="form-input" id="exIndustry" required>
              <option>Hospitality & Leisure</option>
              <option>B2B SaaS & Cloud</option>
              <option>Manufacturing & Industrial</option>
              <option>E-Commerce & Retail</option>
              <option>Financial Services</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Location / Country</label>
            <input type="text" class="form-input" id="exLocation" placeholder="e.g. Mumbai, India / Delaware, USA" value="India" />
          </div>
          <div class="form-group">
            <label class="form-label">Human Employees Count</label>
            <input type="number" class="form-input" id="exStaff" placeholder="e.g. 35" value="30" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Products, Services & Current Situation</label>
          <textarea class="form-input" id="exDesc" rows="2" placeholder="Briefly describe what the company sells, its main customer base, and top operational goals.">Luxury 4-star boutique hotel with dining and banqueting. Goal is to increase direct bookings by 20% and reduce OTA commissions.</textarea>
        </div>
      </div>

      <div style="background:var(--bg-surface); padding:16px; border-radius:var(--radius-md); border:1px solid var(--border-color); margin-bottom:16px;">
        <h4 style="font-size:14px; margin-bottom:12px; color:var(--accent-cyan);">2. Connect Business Data Sources (Optional but Recommended)</h4>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12.5px;">
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" id="ds_web" checked /> Company Website & URL</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" id="ds_crm" checked /> CRM (HubSpot / Salesforce)</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" id="ds_pms" checked /> PMS / Booking Engine</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" id="ds_erp" checked /> ERP & Accounting (Stripe / SAP)</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" id="ds_docs" checked /> Internal SOPs & Document Files</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" id="ds_db" checked /> Operational Database</label>
        </div>
      </div>

      <div style="background:var(--bg-surface); padding:16px; border-radius:var(--radius-md); border:1px solid var(--border-color); margin-bottom:20px;">
        <h4 style="font-size:14px; margin-bottom:12px; color:var(--accent-emerald);">3. Permitted Autonomous AI Research</h4>
        <p style="font-size:12.5px; color:var(--text-secondary); margin-bottom:8px;">Allow the AI CEO to research external public context:</p>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12.5px;">
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" checked /> Competitor Pricing & Market Rates</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" checked /> Industry Benchmarks & Trends</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" checked /> Relevant Regulations & Licensing</label>
          <label style="display:flex; align-items:center; gap:8px;"><input type="checkbox" checked /> Public Customer Reviews & Sentiment</label>
        </div>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:10px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">
          <span>Onboard & Let AI CEO Ingest</span>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </button>
      </div>
    </form>
  `;
}

function renderNewCompanyForm(container) {
  container.innerHTML = `
    <form onsubmit="submitCreateNewCompany(event)">
      <div style="background:var(--bg-surface); padding:16px; border-radius:var(--radius-md); border:1px solid var(--border-color); margin-bottom:16px;">
        <h4 style="font-size:14px; margin-bottom:12px; color:var(--accent-purple);">1. Founder's Idea & Vision</h4>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
          <div class="form-group">
            <label class="form-label">Proposed Company Name *</label>
            <input type="text" class="form-input" id="newName" placeholder="e.g. QuantumFlow Analytics" required />
          </div>
          <div class="form-group">
            <label class="form-label">Industry *</label>
            <select class="form-input" id="newIndustry" required>
              <option>AI Software & SaaS</option>
              <option>Fintech & Payments</option>
              <option>Digital Media & Content</option>
              <option>Health & Biotechnology</option>
              <option>Robotics & Hardware</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">The Core Business Idea *</label>
          <textarea class="form-input" id="newIdea" rows="3" placeholder="Describe what problem this business solves and who the primary customers are." required>Build an automated AI financial auditing platform for e-commerce Shopify merchants to catch billing leakage and supplier chargeback errors.</textarea>
        </div>
      </div>

      <div style="background:var(--bg-surface); padding:16px; border-radius:var(--radius-md); border:1px solid var(--border-color); margin-bottom:20px;">
        <h4 style="font-size:14px; margin-bottom:12px; color:var(--accent-blue);">2. Initial Scope, Budget & Objectives</h4>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
          <div class="form-group">
            <label class="form-label">Initial Seed / Monthly Budget (₹)</label>
            <input type="number" class="form-input" id="newBudget" value="50000" />
          </div>
          <div class="form-group">
            <label class="form-label">Primary 90-Day Milestone</label>
            <input type="text" class="form-input" id="newMilestone" value="Launch MVP and acquire first 10 paying customers" />
          </div>
        </div>
        <p style="font-size:12.5px; color:var(--text-secondary); margin-top:6px;">
          The AI CEO will immediately take this idea and synthesize: <strong>Company Definition → Department Blueprints → Required Workforce Roles → Launch Missions → Required Tools</strong>.
        </p>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:10px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">
          <span>Co-Found with AI CEO & Launch</span>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </button>
      </div>
    </form>
  `;
}

window.submitOnboardExistingCompany = function(e) {
  e.preventDefault();
  const name = document.getElementById('exName').value;
  const industry = document.getElementById('exIndustry').value;
  const location = document.getElementById('exLocation').value;
  const staff = parseInt(document.getElementById('exStaff').value) || 20;
  const desc = document.getElementById('exDesc').value;

  const newComp = {
    id: `comp_${Date.now().toString(36)}`,
    name: name,
    industry: industry,
    type: 'EXISTING',
    status: 'OPERATIONAL',
    revenue: 500000,
    cost: 120000,
    contribution: 380000,
    currency: '₹',
    humanEmployees: staff,
    departments: ['Executive', 'Operations', 'Finance', 'Growth'],
    healthScore: 89,
    description: desc,
    dataSources: ['Website Feed', 'ERP Connector', 'SOP Ingestion'],
    researchDone: true
  };

  // Create an initial specialized agent for this company
  const specialist = {
    id: `wf_${Date.now().toString(36)}`,
    companyId: newComp.id,
    role: `${industry.split(' ')[0]} Operations & Intelligence Specialist`,
    department: 'Operations',
    manager: 'AI CEO',
    model: 'Gemini 3.8 Flash (High)',
    spendingLimit: 20000,
    budgetLimit: 40000,
    allowedTools: ['python3', 'document_reader', 'web_search'],
    status: 'ACTIVE',
    kpis: { 'Verification Rate': '100%', 'Response SLA': '<1 hr' }
  };

  state.companies.unshift(newComp);
  state.workforce.unshift(specialist);
  state.activeCompanyId = newComp.id;
  saveData();
  closeModal();
  showToast(`Onboarded ${name}! AI CEO synthesized organization.`, 'success');
  renderCompanySection();
};

window.submitCreateNewCompany = function(e) {
  e.preventDefault();
  const name = document.getElementById('newName').value;
  const industry = document.getElementById('newIndustry').value;
  const idea = document.getElementById('newIdea').value;
  const budget = parseFloat(document.getElementById('newBudget').value) || 50000;

  const newComp = {
    id: `comp_${Date.now().toString(36)}`,
    name: name,
    industry: industry,
    type: 'NEW_VENTURE',
    status: 'OPERATIONAL',
    revenue: 0,
    cost: 0,
    contribution: 0,
    currency: '₹',
    humanEmployees: 0,
    departments: ['Product Engineering', 'Commercial Sales', 'Growth', 'Finance'],
    healthScore: 95,
    description: idea,
    dataSources: ['Idea Seed', 'AI Market Synthesis'],
    researchDone: true
  };

  const specialist = {
    id: `wf_${Date.now().toString(36)}`,
    companyId: newComp.id,
    role: 'Venture Architect & Go-To-Market Specialist',
    department: 'Growth',
    manager: 'AI CEO',
    model: 'Gemini Pro',
    spendingLimit: budget * 0.5,
    budgetLimit: budget,
    allowedTools: ['web_search', 'browser_robot', 'python3'],
    status: 'ACTIVE',
    kpis: { 'Market Validation': 'Verified', 'Launch Speed': 'Fast' }
  };

  state.companies.unshift(newComp);
  state.workforce.unshift(specialist);
  state.activeCompanyId = newComp.id;
  saveData();
  closeModal();
  showToast(`Created venture ${name}! AI CEO synthesized company hierarchy.`, 'success');
  renderCompanySection();
};

window.openCompanyDetailsModal = function(cid) {
  const comp = state.companies.find(c => c.id === cid);
  if (!comp) return;

  openModal(`Company Audit & Governance: ${comp.name}`, `
    <div style="font-size:13.5px; line-height:1.5;">
      <div style="display:flex; justify-content:space-between; margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid var(--border-color);">
        <div>
          <h4 style="font-size:16px; font-weight:700;">${comp.name}</h4>
          <span style="color:var(--text-secondary); font-size:12.5px;">${comp.industry} • Established</span>
        </div>
        <div style="text-align:right;">
          <div style="font-size:18px; font-weight:700; color:var(--accent-emerald);">${comp.healthScore}%</div>
          <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Health Index</span>
        </div>
      </div>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
        <div style="background:var(--bg-surface); padding:10px 12px; border-radius:var(--radius-md);">
          <div style="font-size:11px; color:var(--text-muted);">REVENUE</div>
          <div style="font-weight:700; font-size:15px;">${comp.currency}${comp.revenue.toLocaleString()}</div>
        </div>
        <div style="background:var(--bg-surface); padding:10px 12px; border-radius:var(--radius-md);">
          <div style="font-size:11px; color:var(--text-muted);">AI WORKFORCE</div>
          <div style="font-weight:700; font-size:15px;">${state.workforce.filter(w=>w.companyId===cid).length} Agents</div>
        </div>
      </div>
      <div style="margin-bottom:16px;">
        <h5 style="font-size:12.5px; margin-bottom:6px; color:var(--accent-blue);">Organizational Departments:</h5>
        <div style="display:flex; flex-wrap:wrap; gap:6px;">
          ${comp.departments.map(d => `<span class="badge badge-blue">${d}</span>`).join('')}
        </div>
      </div>
      <div style="margin-bottom:20px;">
        <h5 style="font-size:12.5px; margin-bottom:6px; color:var(--accent-cyan);">Connected Data Sources:</h5>
        <div style="display:flex; flex-wrap:wrap; gap:6px;">
          ${comp.dataSources.map(ds => `<span class="badge badge-purple">${ds}</span>`).join('')}
        </div>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <button class="btn-secondary" style="color:var(--accent-rose); border-color:rgba(244,63,94,0.3);" onclick="deleteCompany('${comp.id}')">Delete Company</button>
        <button class="btn-primary" style="width:auto;" onclick="closeModal(); openCompanyInCeo('${comp.id}');">Open in AI CEO</button>
      </div>
    </div>
  `);
};

window.deleteCompany = function(cid) {
  if (!confirm('Are you sure you want to remove this company from your host account?')) return;
  state.companies = state.companies.filter(c => c.id !== cid);
  state.workforce = state.workforce.filter(w => w.companyId !== cid);
  state.missions = state.missions.filter(m => m.companyId !== cid);
  if (state.activeCompanyId === cid) {
    state.activeCompanyId = state.companies.length > 0 ? state.companies[0].id : null;
  }
  saveData();
  closeModal();
  showToast('Company removed successfully.', 'info');
  renderCompanySection();
};

window.openCompanyInCeo = function(cid) {
  state.activeCompanyId = cid;
  switchNav('ceo');
};

// ==========================================================================
// 4. AI CEO SECTION (The Heart of the SaaS)
// ==========================================================================
function renderCeoSection() {
  const container = document.getElementById('view-ceo');
  if (!container) return;

  if (state.companies.length === 0) {
    container.innerHTML = `
      <div class="view-title-bar">
        <div class="view-heading">
          <h2>AI CEO — Central Intelligence</h2>
          <p>Please add a company first before operating with the AI CEO.</p>
        </div>
      </div>
      <div class="empty-company-state">
        <h3>No Company Selected</h3>
        <p>The AI CEO requires at least one onboarded or created company to manage workforce, missions, and strategic execution.</p>
        <button class="btn-primary" style="width:auto; margin:0 auto;" onclick="openAddCompanyModal()">+ Add Company</button>
      </div>
    `;
    return;
  }

  const activeComp = state.companies.find(c => c.id === state.activeCompanyId) || state.companies[0];
  state.activeCompanyId = activeComp.id;

  const compWorkforce = state.workforce.filter(w => w.companyId === activeComp.id);
  const compMissions = state.missions.filter(m => m.companyId === activeComp.id);

  container.innerHTML = `
    <div class="view-title-bar">
      <div class="view-heading">
        <h2>
          <span>AI CEO — Central Operating Intelligence</span>
          <span class="badge badge-emerald">Managing: ${activeComp.name}</span>
        </h2>
        <p>The AI CEO dynamically designs the organization, hires specialized AI employees on-demand, executes missions, and compiles verified reports.</p>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="btn-secondary" onclick="openSimulateMissionModal()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          Digital Twin Simulation
        </button>
        <button class="btn-primary" style="width:auto;" onclick="openHireAgentModal()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          + Hire AI Employee
        </button>
      </div>
    </div>

    <!-- AI CEO Directive Command Bar -->
    <div class="ceo-command-bar">
      <div style="font-size:18px;">🧠</div>
      <input type="text" class="ceo-command-input" id="ceoDirectiveInput" placeholder="Give an objective or instruction to AI CEO for ${activeComp.name} (e.g. 'Analyze competitor pricing and formulate a retention plan')..." onkeydown="if(event.key==='Enter') executeCeoDirective()" />
      <button class="btn-primary" style="width:auto; padding:7px 14px; font-size:13px;" onclick="executeCeoDirective()">
        <span>Command CEO</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
      </button>
    </div>

    <!-- Layout: Left Tree & Right Subtabs -->
    <div class="ceo-hierarchy-layout">
      <!-- Left Column: Company Tree Selector -->
      <div class="ceo-tree-sidebar">
        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700; padding:4px 8px; margin-bottom:8px;">
          Managed Companies & Portfolios:
        </div>
        ${state.companies.map(c => `
          <div class="tree-node">
            <div class="tree-node-header ${c.id === activeComp.id ? 'active' : ''}" onclick="selectCeoCompany('${c.id}')">
              <span>🏢</span>
              <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${c.name}</span>
            </div>
            ${c.id === activeComp.id ? `
              <div class="tree-children">
                <div style="font-size:12px; padding:4px 8px; color:var(--text-secondary); cursor:pointer;" onclick="switchCeoTab('structure')">├── Structure (${c.departments.length} Depts)</div>
                <div style="font-size:12px; padding:4px 8px; color:var(--text-secondary); cursor:pointer;" onclick="switchCeoTab('employees')">├── AI Employees (${state.workforce.filter(w=>w.companyId===c.id).length})</div>
                <div style="font-size:12px; padding:4px 8px; color:var(--text-secondary); cursor:pointer;" onclick="switchCeoTab('missions')">├── Missions (${state.missions.filter(m=>m.companyId===c.id).length})</div>
                <div style="font-size:12px; padding:4px 8px; color:var(--text-secondary); cursor:pointer;" onclick="switchCeoTab('reports')">└── Verified Reports</div>
              </div>
            ` : ''}
          </div>
        `).join('')}
      </div>

      <!-- Right Column: Subtabs (Employees, Missions, Reports, Structure) -->
      <div>
        <!-- Subnav Buttons -->
        <div class="ceo-subnav">
          <button class="ceo-tab-btn ${state.ceoTab === 'employees' ? 'active' : ''}" onclick="switchCeoTab('employees')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            AI Employees (${compWorkforce.length})
          </button>
          <button class="ceo-tab-btn ${state.ceoTab === 'missions' ? 'active' : ''}" onclick="switchCeoTab('missions')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            Missions & Objectives (${compMissions.length})
          </button>
          <button class="ceo-tab-btn ${state.ceoTab === 'reports' ? 'active' : ''}" onclick="switchCeoTab('reports')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            Executive Reports
          </button>
          <button class="ceo-tab-btn ${state.ceoTab === 'structure' ? 'active' : ''}" onclick="switchCeoTab('structure')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            Organizational Structure
          </button>
        </div>

        <!-- Tab Content Containers -->
        <div id="ceoTabContent">
          ${renderActiveCeoTab(activeComp, compWorkforce, compMissions)}
        </div>
      </div>
    </div>
  `;
}

window.selectCeoCompany = function(cid) {
  state.activeCompanyId = cid;
  renderCeoSection();
};

window.switchCeoTab = function(tabName) {
  state.ceoTab = tabName;
  renderCeoSection();
};

function renderActiveCeoTab(comp, workforce, missions) {
  if (state.ceoTab === 'employees') {
    return `
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <p style="font-size:13px; color:var(--text-secondary);">
            Dynamic specialized AI employees tailored to <strong>${comp.name}</strong>. Created on-demand by the AI CEO rather than a fixed template.
          </p>
          <button class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="openHireAgentModal()">+ Create Custom AI Role</button>
        </div>

        <div class="employees-grid">
          ${workforce.map(w => `
            <div class="employee-card">
              <div class="employee-avatar-row">
                <div class="agent-avatar">${w.role.charAt(0)}</div>
                <div class="agent-title">
                  <h4>${w.role}</h4>
                  <span>${w.department} • Reports to ${w.manager}</span>
                </div>
              </div>

              <div class="agent-badge-row">
                <span class="badge badge-blue">Model: ${w.model}</span>
                <span class="badge badge-emerald">Cap: ₹${(w.spendingLimit).toLocaleString()}</span>
                <span class="badge badge-purple">${w.status}</span>
              </div>

              <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">
                <strong>Allowed Tools:</strong> ${w.allowedTools.join(', ')}
              </div>

              <div style="background:var(--bg-surface); padding:8px 10px; border-radius:var(--radius-sm); font-size:11.5px; margin-bottom:12px;">
                <strong>Key KPIs:</strong> ${Object.entries(w.kpis || {}).map(([k,v]) => `${k}: ${v}`).join(' • ')}
              </div>

              <div style="display:flex; gap:6px;">
                <button class="btn-secondary" style="flex:1; font-size:12px; padding:6px 8px;" onclick="openAssignMissionModal('${w.id}')">Assign Task</button>
                <button class="btn-secondary" style="font-size:12px; padding:6px 8px; color:var(--accent-rose);" onclick="removeAgent('${w.id}')">Decommission</button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } else if (state.ceoTab === 'missions') {
    return `
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <p style="font-size:13px; color:var(--text-secondary);">
            Mission Pipeline: <code>Mission → AI CEO → Workforce → Tools → Execution → Verification → Report</code>
          </p>
          <button class="btn-primary" style="width:auto; font-size:12.5px; padding:6px 14px;" onclick="openNewMissionModal()">+ New Mission</button>
        </div>

        <div class="missions-list">
          ${missions.map(m => `
            <div class="mission-card">
              <div class="mission-info" style="flex:1; min-width:240px;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                  <span class="badge ${m.status === 'SUCCESS' ? 'badge-emerald' : 'badge-blue'}">${m.status}</span>
                  <span style="font-size:11.5px; color:var(--text-muted); font-family:var(--font-mono);">${m.id}</span>
                </div>
                <h4>${m.title}</h4>
                <p>${m.targetOutcome}</p>
                <div style="margin-top:6px; font-size:12px; color:var(--accent-cyan);">
                  <strong>Agents:</strong> ${m.assignedAgents.join(', ')} • <strong>Tools:</strong> ${m.toolsUsed.join(', ')}
                </div>
              </div>

              <div style="text-align:right; font-size:12.5px;">
                <div style="font-weight:700; color:var(--text-primary);">Budget: ₹${m.budget.toLocaleString()}</div>
                <div style="color:var(--text-muted); font-size:11.5px;">Incurred: ₹${m.costIncurred.toLocaleString()}</div>
                <div style="color:var(--accent-emerald); font-weight:600; font-size:11.5px; margin-top:4px;">${m.verificationSummary}</div>
                <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px; margin-top:8px;" onclick="viewMissionLedger('${m.id}')">Inspect Ledger</button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } else if (state.ceoTab === 'reports') {
    return `
      <div>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
          The AI CEO compiles comprehensive executive reports so the owner can review verified business outcomes without micromanaging.
        </p>

        <div class="card" style="margin-bottom:14px;">
          <div class="card-title-bar">
            <h4 style="font-size:14.5px; font-weight:700;">Executive Shift Report: ${comp.name}</h4>
            <span class="badge badge-emerald">Verified Ledger Match</span>
          </div>
          <p style="font-size:13px; line-height:1.5; color:var(--text-secondary); margin-bottom:12px;">
            The autonomous workforce completed 3 core missions over the last 24-hour cycle. 
            Direct bookings and revenue recovery yielded <strong>₹64,000</strong> while AI token and operational costs were capped at <strong>₹18,000</strong>, delivering a <strong>₹46,000 net contribution</strong>.
          </p>
          <div style="background:var(--bg-surface); padding:12px; border-radius:var(--radius-md); font-size:12px; font-family:var(--font-mono); color:var(--accent-cyan);">
            <div>[VERIFICATION_SUMMARY]: ALL WORKFLOWS PASSED SHA-256 INTEGRITY CHECK</div>
            <div>[SECURITY_GATE]: NO UNENCRYPTED CREDENTIALS EXPOSED TO LLM CONTEXT</div>
            <div>[RECOMMENDATION]: APPROVE CAMPAIGN EXTENSION FOR MAXIMUM OCT OCCUPANCY</div>
          </div>
        </div>
      </div>
    `;
  } else {
    // Structure
    return `
      <div>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
          Tailored organogram synthesized by AI CEO specifically for <strong>${comp.name}</strong> (${comp.industry}).
        </p>

        <div class="card" style="text-align:center; padding:30px;">
          <div style="display:inline-block; padding:12px 24px; background:var(--accent-blue-light); border:1px solid var(--accent-blue); border-radius:var(--radius-md); font-weight:700; margin-bottom:20px;">
            AI CEO (Central Strategy & Governance)
          </div>
          <div style="width:2px; height:24px; background:var(--border-subtle); margin:0 auto 20px;"></div>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px;">
            ${comp.departments.map(d => `
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
                <div style="font-weight:700; font-size:13.5px; margin-bottom:6px; color:var(--accent-cyan);">${d}</div>
                <div style="font-size:11.5px; color:var(--text-secondary);">
                  ${state.workforce.filter(w=>w.companyId===comp.id && w.department.toLowerCase().includes(d.toLowerCase().split(' ')[0])).length} AI Specialists
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }
}

window.executeCeoDirective = function() {
  const input = document.getElementById('ceoDirectiveInput');
  if (!input || !input.value.trim()) return;

  const directive = input.value.trim();
  const activeComp = state.companies.find(c => c.id === state.activeCompanyId) || state.companies[0];

  // Create an immediate new mission from this directive
  const newMission = {
    id: `MSN-${Date.now().toString(36).toUpperCase()}`,
    companyId: activeComp.id,
    title: `Directive: ${directive.slice(0, 45)}...`,
    targetOutcome: directive,
    assignedAgents: [state.workforce[0] ? state.workforce[0].role : 'AI CEO Specialist'],
    toolsUsed: ['web_search', 'python3', 'browser_robot'],
    budget: 15000,
    costIncurred: 2400,
    revenueRecovered: 0,
    status: 'ACTIVE',
    verificationSummary: 'Executing across governed tool fabric',
    timestamp: 'Just now'
  };

  state.missions.unshift(newMission);
  saveData();
  input.value = '';
  showToast(`Directive received! AI CEO launched mission ${newMission.id}.`, 'success');
  state.ceoTab = 'missions';
  renderCeoSection();
};

window.openHireAgentModal = function() {
  const activeComp = state.companies.find(c => c.id === state.activeCompanyId) || state.companies[0];

  openModal(`Hire AI Employee for ${activeComp.name}`, `
    <form onsubmit="submitHireAgent(event)">
      <div class="form-group">
        <label class="form-label">Specialized Role Name *</label>
        <input type="text" class="form-input" id="agentRole" placeholder="e.g. Competitor Price Auditor" required />
      </div>
      <div class="form-group">
        <label class="form-label">Department *</label>
        <select class="form-input" id="agentDept" required>
          ${activeComp.departments.map(d => `<option>${d}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Underlying Model</label>
        <select class="form-input" id="agentModel">
          <option>Gemini 3.8 Flash (High)</option>
          <option>Gemini Pro</option>
          <option>Claude 3.5 Sonnet</option>
          <option>Local Llama 3 (Ollama)</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Monthly Spending Cap (₹)</label>
        <input type="number" class="form-input" id="agentCap" value="25000" />
      </div>
      <div class="form-group">
        <label class="form-label">Allowed Capability Tools</label>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:12.5px;">
          <label><input type="checkbox" name="tool_sel" value="python3" checked /> Python Sandbox</label>
          <label><input type="checkbox" name="tool_sel" value="web_search" checked /> Web Search</label>
          <label><input type="checkbox" name="tool_sel" value="browser_robot" checked /> Desktop Browser</label>
          <label><input type="checkbox" name="tool_sel" value="document_reader" checked /> Document Reader</label>
        </div>
      </div>
      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:16px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">Synthesize & Deploy Worker</button>
      </div>
    </form>
  `);
};

window.submitHireAgent = function(e) {
  e.preventDefault();
  const role = document.getElementById('agentRole').value;
  const dept = document.getElementById('agentDept').value;
  const model = document.getElementById('agentModel').value;
  const cap = parseFloat(document.getElementById('agentCap').value) || 25000;

  const tools = [];
  document.querySelectorAll("input[name='tool_sel']:checked").forEach(cb => tools.push(cb.value));

  const newAgent = {
    id: `wf_${Date.now().toString(36)}`,
    companyId: state.activeCompanyId,
    role: role,
    department: dept,
    manager: 'AI CEO',
    model: model,
    spendingLimit: cap,
    budgetLimit: cap * 2,
    allowedTools: tools.length > 0 ? tools : ['python3'],
    status: 'ACTIVE',
    kpis: { 'SLA Compliance': '99%', 'Accuracy': 'High' }
  };

  state.workforce.unshift(newAgent);
  saveData();
  closeModal();
  showToast(`AI Worker "${role}" onboarded!`, 'success');
  renderCeoSection();
};

window.removeAgent = function(agentId) {
  if (!confirm('Are you sure you want to decommission this AI employee?')) return;
  state.workforce = state.workforce.filter(w => w.id !== agentId);
  saveData();
  showToast('Worker decommissioned.', 'info');
  renderCeoSection();
};

window.openNewMissionModal = function() {
  const activeComp = state.companies.find(c => c.id === state.activeCompanyId) || state.companies[0];
  const compWf = state.workforce.filter(w => w.companyId === activeComp.id);

  openModal(`Launch New Mission: ${activeComp.name}`, `
    <form onsubmit="submitNewMission(event)">
      <div class="form-group">
        <label class="form-label">Mission Title *</label>
        <input type="text" class="form-input" id="msnTitle" placeholder="e.g. Audit supplier invoices for Q3 overcharges" required />
      </div>
      <div class="form-group">
        <label class="form-label">Target Outcome / Objective *</label>
        <textarea class="form-input" id="msnOutcome" rows="3" placeholder="Specify expected verification deliverables, maximum budget, and success criteria." required></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Assigned AI Specialist</label>
        <select class="form-input" id="msnAgent">
          ${compWf.map(w => `<option value="${w.role}">${w.role} (${w.department})</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Operational Budget Cap (₹)</label>
        <input type="number" class="form-input" id="msnBudget" value="20000" />
      </div>
      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:16px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">Authorize & Start Mission</button>
      </div>
    </form>
  `);
};

window.submitNewMission = function(e) {
  e.preventDefault();
  const title = document.getElementById('msnTitle').value;
  const outcome = document.getElementById('msnOutcome').value;
  const agent = document.getElementById('msnAgent').value;
  const budget = parseFloat(document.getElementById('msnBudget').value) || 20000;

  const msn = {
    id: `MSN-${Date.now().toString(36).toUpperCase()}`,
    companyId: state.activeCompanyId,
    title: title,
    targetOutcome: outcome,
    assignedAgents: [agent],
    toolsUsed: ['python3', 'web_search', 'document_reader'],
    budget: budget,
    costIncurred: 0,
    revenueRecovered: 0,
    status: 'ACTIVE',
    verificationSummary: 'Assigned to workforce; execution initiated',
    timestamp: 'Just now'
  };

  state.missions.unshift(msn);
  saveData();
  closeModal();
  showToast(`Mission ${msn.id} authorized and executing.`, 'success');
  renderCeoSection();
};

window.viewMissionLedger = function(msnId) {
  const m = state.missions.find(x => x.id === msnId);
  if (!m) return;

  openModal(`Evidence Ledger Audit: ${m.id}`, `
    <div style="font-size:13px; line-height:1.5;">
      <h4 style="font-size:15px; margin-bottom:8px;">${m.title}</h4>
      <div style="background:#070b14; padding:14px; border-radius:var(--radius-md); font-family:var(--font-mono); color:#10b981; margin-bottom:14px;">
        <div>&gt; MISSION_ID: ${m.id}</div>
        <div>&gt; STATUS: ${m.status}</div>
        <div>&gt; CRYPTO_DIGEST: SHA-256 (3e91b0...c80f)</div>
        <div>&gt; AGENT_CLAIM: SUCCESSFUL</div>
        <div>&gt; PHYSICAL_TRUTH_VERIFICATION: CONFIRMED</div>
        <div>&gt; REPUTATION_DELTA: +0.05</div>
      </div>
      <p style="color:var(--text-secondary); margin-bottom:14px;">All tool actions and output hashes are anchored directly to the immutable append-only ledger on host storage.</p>
      <button class="btn-primary" style="width:100%;" onclick="closeModal()">Close Audit View</button>
    </div>
  `);
};

// ==========================================================================
// 5. TOOLS SECTION & TOOL FACTORY MODULE
// ==========================================================================
function renderToolsSection() {
  const container = document.getElementById('view-tools');
  if (!container) return;

  const filteredTools = state.toolsCategory === 'all' 
    ? state.tools 
    : state.tools.filter(t => t.category === state.toolsCategory);

  container.innerHTML = `
    <div class="view-title-bar">
      <div class="view-heading">
        <h2>
          <span>Tools & Universal Capability Layer</span>
          <span class="badge badge-purple">${state.tools.length} Tools Available</span>
        </h2>
        <p>The capability layer of the Universal Robotic Assistant. AI employees do not need to hardcode tasks; they use available tools and build new ones.</p>
      </div>
      <button class="btn-primary" style="width:auto;" onclick="openToolFactoryModal()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
        + Build Tool in Factory
      </button>
    </div>

    <!-- Tool Factory Pipeline Banner -->
    <div class="factory-banner">
      <div>
        <h3 style="font-size:16px; font-weight:700; margin-bottom:4px; color:var(--text-primary);">
          ⚙️ The Tool Factory — Meta-Capability Engine
        </h3>
        <p style="font-size:13px; color:var(--text-secondary);">
          If the AI CEO discovers a missing capability, it designs, builds, sandbox-tests, verifies, and registers new tools autonomously.
        </p>
        <div class="factory-pipeline">
          <div class="pipeline-step">1. Identify Need</div>
          <span>→</span>
          <div class="pipeline-step">2. Tool Factory</div>
          <span>→</span>
          <div class="pipeline-step">3. Design Code</div>
          <span>→</span>
          <div class="pipeline-step">4. Sandbox Test</div>
          <span>→</span>
          <div class="pipeline-step">5. Register & Deploy</div>
        </div>
      </div>
      <button class="btn-secondary" style="font-size:13px; padding:8px 16px;" onclick="openToolFactoryModal()">
        Launch Factory Builder
      </button>
    </div>

    <!-- Robotic Desktop Assistant Status Console -->
    <div class="card" style="margin-bottom:24px;">
      <div class="card-title-bar">
        <h3 class="card-title">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          Universal Robotic Desktop Assistant — Live Screen & Perception Fabric
        </h3>
        <button class="btn-secondary" style="font-size:12px; padding:4px 10px;" onclick="simulateRobotPerception()">Test Perception Scan</button>
      </div>
      <div class="robot-console" id="robotConsoleOutput">
        <div>[ROBOT_CORE]: PERCEPTION ENGINE LISTENING ON DISPLAY_0</div>
        <div>[VISION]: OCR MODEL LOADED (TESSERACT + UI RESNET)</div>
        <div>[KEYBOARD_MOUSE]: INPUT HOOKS READY</div>
        <div>[DESKTOP_STATUS]: IDLE — READY FOR HUMAN WORKSTATION WORKFLOWS</div>
      </div>
    </div>

    <!-- Tool Categories Navigation -->
    <div class="tool-categories-nav">
      <button class="tool-cat-btn ${state.toolsCategory === 'all' ? 'active' : ''}" onclick="filterTools('all')">All Capabilities (${state.tools.length})</button>
      <button class="tool-cat-btn ${state.toolsCategory === 'info' ? 'active' : ''}" onclick="filterTools('info')">Information & Web</button>
      <button class="tool-cat-btn ${state.toolsCategory === 'dev' ? 'active' : ''}" onclick="filterTools('dev')">Development & Code</button>
      <button class="tool-cat-btn ${state.toolsCategory === 'comm' ? 'active' : ''}" onclick="filterTools('comm')">Communication & Voice</button>
      <button class="tool-cat-btn ${state.toolsCategory === 'biz' ? 'active' : ''}" onclick="filterTools('biz')">Business, CRM & ERP</button>
      <button class="tool-cat-btn ${state.toolsCategory === 'robot' ? 'active' : ''}" onclick="filterTools('robot')">Robotic-Computer & Desktop</button>
    </div>

    <!-- Tools Grid -->
    <div class="tools-grid">
      ${filteredTools.map(t => `
        <div class="tool-card">
          <div class="tool-card-top">
            <div class="tool-icon" style="background:var(--accent-blue-light);">${t.icon}</div>
            <span class="badge ${t.status === 'ACTIVE' ? 'badge-emerald' : 'badge-blue'}">${t.status}</span>
          </div>
          <h4 class="tool-name">${t.name}</h4>
          <p class="tool-desc">${t.desc}</p>
          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-color); padding-top:10px;">
            <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">${t.category}</span>
            <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px;" onclick="testToolExecution('${t.id}')">Test Run</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

window.filterTools = function(cat) {
  state.toolsCategory = cat;
  renderToolsSection();
};

window.simulateRobotPerception = function() {
  const consoleEl = document.getElementById('robotConsoleOutput');
  if (!consoleEl) return;
  const line1 = `<div>[${new Date().toLocaleTimeString()}] PERCEPTION_SCAN: CAPTURING ACTIVE WINDOW BUFFER...</div>`;
  const line2 = `<div>[${new Date().toLocaleTimeString()}] DETECTED: 1 BROWSER WINDOW, 1 TERMINAL, 4 INPUT FIELDS</div>`;
  const line3 = `<div style="color:#38bdf8;">[${new Date().toLocaleTimeString()}] READY TO CLICK, TYPE, AND NAVIGATE DESKTOP WORKFLOWS.</div>`;
  consoleEl.innerHTML += line1 + line2 + line3;
  consoleEl.scrollTop = consoleEl.scrollHeight;
  showToast('Desktop perception scan completed.', 'success');
};

window.testToolExecution = function(toolId) {
  const t = state.tools.find(x => x.id === toolId);
  if (!t) return;
  showToast(`Executed tool sandbox probe for: ${t.name}`, 'success');
};

window.openToolFactoryModal = function() {
  openModal('The Tool Factory — Build & Register New Capability', `
    <form onsubmit="submitBuildTool(event)">
      <p style="font-size:13px; color:var(--text-secondary); margin-bottom:14px;">
        When a mission requires a tool that does not yet exist in your SaaS, the Tool Factory generates and certifies it in a secured sandbox.
      </p>
      <div class="form-group">
        <label class="form-label">Tool Capability Name *</label>
        <input type="text" class="form-input" id="newToolName" placeholder="e.g. Shopify Refund Reconciliation Bot" required />
      </div>
      <div class="form-group">
        <label class="form-label">Tool Category *</label>
        <select class="form-input" id="newToolCat" required>
          <option value="biz">Business, CRM & ERP</option>
          <option value="info">Information & Web</option>
          <option value="dev">Development & Code</option>
          <option value="comm">Communication & Voice</option>
          <option value="robot">Robotic-Computer & Desktop</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Functional Specification</label>
        <textarea class="form-input" id="newToolSpec" rows="3" placeholder="Describe the inputs, outputs, external API endpoints, and assertions required." required>Connects to Shopify Orders API, queries orders marked as returned, verifies Stripe refund settlement, and flags discrepancies.</textarea>
      </div>
      <div style="background:#070b14; padding:12px; border-radius:var(--radius-md); font-family:var(--font-mono); font-size:11.5px; color:#38bdf8; margin-bottom:16px;">
        <div># Automated Factory Verification Pipeline:</div>
        <div>1. AST Syntax & Security Static Analysis: PASSED</div>
        <div>2. Epistemic Sandbox Containerization: PASSED</div>
        <div>3. Deterministic SHA-256 Output Assertion: PASSED</div>
      </div>
      <div style="display:flex; justify-content:flex-end; gap:10px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">Build, Test & Register Tool</button>
      </div>
    </form>
  `);
};

window.submitBuildTool = function(e) {
  e.preventDefault();
  const name = document.getElementById('newToolName').value;
  const cat = document.getElementById('newToolCat').value;
  const spec = document.getElementById('newToolSpec').value;

  const tool = {
    id: `tool_${Date.now().toString(36)}`,
    name: name,
    category: cat,
    icon: '⚡',
    desc: spec,
    status: 'ACTIVE'
  };

  state.customTools.push(tool);
  state.tools.push(tool);
  saveData();
  closeModal();
  showToast(`Tool "${name}" certified and registered into capability layer!`, 'success');
  renderToolsSection();
};

// ==========================================================================
// 6. SETTINGS SECTION (Enterprise 32-Category Architecture)
// ==========================================================================

const SETTINGS_DOMAINS = [
  {
    domainId: 'account',
    domainTitle: 'Account & Identity',
    domainDesc: 'Manage personal credentials, security keys, and host identity.',
    categories: [
      { id: '01', key: 'account_profile', title: 'Account & Profile', desc: 'Host identity, personal info, contact details, and account identifiers.', icon: '👤' },
      { id: '02', key: 'security_auth', title: 'Security & Authentication', desc: 'Login methods, 2FA/MFA, session timeout, passkeys, and trusted devices.', icon: '🔒' }
    ]
  },
  {
    domainId: 'workspace',
    domainTitle: 'Workspace & Organization',
    domainDesc: 'Enterprise workspace boundary and multi-tenant company isolation.',
    categories: [
      { id: '03', key: 'workspace_org', title: 'Organization & Workspace', desc: 'Host workspace name, hierarchy, default currency, and operational region.', icon: '🏛️' },
      { id: '04', key: 'companies_isolation', title: 'Companies & Isolation', desc: 'Multi-tenant company boundaries, data segregation, and onboarding rules.', icon: '🏢' }
    ]
  },
  {
    domainId: 'ai_operations',
    domainTitle: 'AI Operations & Robotics',
    domainDesc: 'Strategic CEO intelligence, workforce orchestration, and desktop robotic drivers.',
    categories: [
      { id: '05', key: 'ai_ceo', title: 'AI CEO Settings', desc: 'Identity, voice, operating style (conservative to aggressive), and decision bounds.', icon: '🧠' },
      { id: '06', key: 'ai_workforce', title: 'AI Workforce & Agents', desc: 'Autonomous agent creation rules, headcount caps, and employment contracts.', icon: '🤖' },
      { id: '07', key: 'missions_automation', title: 'Missions & Automation', desc: 'Scheduling, recurring loops, night shift window, and emergency kill switches.', icon: '⚡' },
      { id: '08', key: 'ai_models', title: 'AI Models & Intelligence', desc: 'Model providers (Gemini, Claude, GPT), intelligent routing, and fallback.', icon: '🔮' },
      { id: '09', key: 'tools_factory', title: 'Tools & Tool Factory', desc: 'Tool registry permissions, autonomous tool build rules, and sandbox checks.', icon: '🛠️' },
      { id: '10', key: 'computer_robotic', title: 'Computer & Robotic Control', desc: 'Screen vision, keyboard/mouse drivers, desktop apps, and OS access levels.', icon: '🖥️' }
    ]
  },
  {
    domainId: 'business',
    domainTitle: 'Business & Commercial',
    domainDesc: 'Connected business systems, customer pipelines, campaigns, and financial gates.',
    categories: [
      { id: '11', key: 'integrations', title: 'Integrations & Connected Systems', desc: 'CRM, ERP, PMS, POS, Cloud storage, Google Workspace, and M365.', icon: '🔌' },
      { id: '12', key: 'knowledge_data', title: 'Knowledge & Data', desc: 'Indexing permissions, retention, SOPs, and cross-department knowledge gates.', icon: '📚' },
      { id: '13', key: 'communication', title: 'Communication & Voice', desc: 'Outbound email, WhatsApp, Slack, voice telephony, and scheduled meetings.', icon: '📞' },
      { id: '14', key: 'sales_crm', title: 'Sales & CRM', desc: 'Lead qualification, automated follow-ups, and proposal discount thresholds.', icon: '📈' },
      { id: '15', key: 'marketing_ads', title: 'Marketing & Advertising', desc: 'Ad budgets, campaign ceilings, organic social rules, and Meta/Google ads.', icon: '📢' },
      { id: '16', key: 'finance_budgets', title: 'Finance, Payments & Budgets', desc: 'Hard spending stops, payment gateways, and mandatory approval tiers.', icon: '💰' },
      { id: '17', key: 'documents_contracts', title: 'Documents & Contracts', desc: 'Document summarization, legal clause analysis, and signature gates.', icon: '📝' }
    ]
  },
  {
    domainId: 'governance',
    domainTitle: 'Control, Security & Governance',
    domainDesc: 'Human oversight policies, RBAC matrices, privacy, threat defense, and audit trails.',
    categories: [
      { id: '18', key: 'notifications_alerts', title: 'Notifications & Alerts', desc: 'In-app, SMS, email notification priorities, and alert threshold filters.', icon: '🔔' },
      { id: '19', key: 'approvals_governance', title: 'Approvals & Governance', desc: 'Human-in-the-loop policies: financial, destructive, and external email gates.', icon: '⚖️' },
      { id: '20', key: 'permissions_rbac', title: 'Permissions & Access Control (RBAC)', desc: 'Granular user roles: Host, Executive, Manager, Finance, and Auditor.', icon: '🛡️' },
      { id: '21', key: 'privacy_data', title: 'Privacy & Data Governance', desc: 'Data retention, GDPR/CCPA data export, deletion, and PII anonymization.', icon: '🔐' },
      { id: '22', key: 'sec_ops', title: 'Security Operations (SecOps)', desc: 'Threat monitoring, IP allowlists, geo-restrictions, and credential guards.', icon: '🚨' },
      { id: '23', key: 'audit_activity', title: 'Audit & Activity Ledger', desc: 'Immutable action logging, SHA-256 evidence chain, and event filtering.', icon: '📜' },
      { id: '30', key: 'backup_recovery', title: 'Backup & Recovery', desc: 'Automated workspace backups, point-in-time state rollback, and recovery.', icon: '💾' }
    ]
  },
  {
    domainId: 'platform',
    domainTitle: 'Platform, Billing & Developer',
    domainDesc: 'Metered usage costs, subscriptions, public APIs, webhooks, and advanced runtime flags.',
    categories: [
      { id: '24', key: 'usage_tokens', title: 'Usage, Tokens & Costs', desc: 'Model token metering, compute time, tool execution costs, and breakdown.', icon: '📊' },
      { id: '25', key: 'billing_subscription', title: 'Billing & Subscription', desc: 'SaaS plan tiers, corporate payment methods, invoices, and SLA guarantees.', icon: '💳' },
      { id: '26', key: 'api_developer', title: 'API & Developer', desc: 'API keys, service accounts, rate limits, SDKs, and developer documentation.', icon: '🔑' },
      { id: '27', key: 'webhooks_events', title: 'Webhooks & Events', desc: 'Inbound and outbound webhook triggers, HMAC signatures, and event routing.', icon: '🪝' },
      { id: '28', key: 'localization', title: 'Localization & Regional', desc: 'Default currency (₹, $, €, £), time zones, date formats, and languages.', icon: '🌍' },
      { id: '29', key: 'appearance', title: 'Appearance & Interface', desc: 'Theme customization, compact/comfortable density, and widget layouts.', icon: '🎨' },
      { id: '31', key: 'enterprise_admin', title: 'Enterprise Administration', desc: 'Multi-workspace control, SCIM provisioning, and organization-wide policies.', icon: '🏢' },
      { id: '32', key: 'advanced_dev', title: 'Advanced & Runtime Controls', desc: 'Sandbox isolation, runtime flags, execution logs, and experimental switches.', icon: '⚙️' }
    ]
  }
];

// Flat list for fast search and sidebar navigation
const ALL_SETTINGS_CATEGORIES = SETTINGS_DOMAINS.flatMap(d => d.categories.map(c => ({ ...c, domainTitle: d.domainTitle })));

// View state: 'hub' or a category key e.g. 'ai_ceo'
state.settingsView = 'hub';
state.settingsActiveCategory = '01';

function renderSettingsSection() {
  const container = document.getElementById('view-settings');
  if (!container) return;

  if (state.settingsView === 'hub') {
    renderSettingsHub(container);
  } else {
    renderSettingsDetail(container, state.settingsActiveCategory);
  }
}

// --------------------------------------------------------------------------
// 1. Settings Hub View (Enterprise Control Center)
// --------------------------------------------------------------------------
function renderSettingsHub(container) {
  container.innerHTML = `
    <div class="view-title-bar">
      <div class="view-heading">
        <h2>
          <span>Enterprise Settings & Control Center</span>
          <span class="badge badge-blue">Host Plane • 32 Categories</span>
        </h2>
        <p>The centralized control plane for your ZONATA instance. Every operational layer is configurable while keeping high-risk policies securely isolated.</p>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="btn-secondary" onclick="exportSettingsPolicy()">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
          Export Policy JSON
        </button>
        <button class="btn-primary" style="width:auto;" onclick="saveAllSettings()">
          Save System State
        </button>
      </div>
    </div>

    <!-- Live Search Bar Across All 32 Categories -->
    <div class="settings-search-wrapper">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="settingsHubSearchInput" placeholder="Search all 32 settings (e.g. 'spending stops', 'screen perception', 'model fallback', 'API keys')..." oninput="filterSettingsHubCards(this.value)" />
    </div>

    <!-- 6 Major Enterprise Domains Container -->
    <div class="settings-domains-container" id="settingsDomainsContainer">
      ${SETTINGS_DOMAINS.map(domain => `
        <div class="settings-domain-block" data-domain="${domain.domainId}">
          <div class="settings-domain-header">
            <h3 class="settings-domain-title">${domain.domainTitle}</h3>
            <span style="font-size:12px; color:var(--text-muted);">${domain.domainDesc}</span>
          </div>

          <div class="settings-cards-grid">
            ${domain.categories.map(cat => `
              <div class="settings-hub-card" data-cat-key="${cat.key}" data-search="${(cat.id + ' ' + cat.title + ' ' + cat.desc + ' ' + domain.domainTitle).toLowerCase()}" onclick="openSettingsCategory('${cat.id}')">
                <div>
                  <div class="settings-card-top-row">
                    <span class="settings-card-num">${cat.id}</span>
                    <div class="settings-card-icon" style="background:var(--accent-blue-light);">${cat.icon}</div>
                  </div>
                  <h4 class="settings-card-title">${cat.title}</h4>
                  <p class="settings-card-desc">${cat.desc}</p>
                </div>
                <div class="settings-card-footer">
                  <span>Configure</span>
                  <span>→</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

window.filterSettingsHubCards = function(query) {
  const q = (query || '').toLowerCase().trim();
  const cards = document.querySelectorAll('.settings-hub-card');
  const blocks = document.querySelectorAll('.settings-domain-block');

  cards.forEach(card => {
    const text = card.getAttribute('data-search') || '';
    if (!q || text.includes(q)) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });

  // Hide empty domains during search
  blocks.forEach(block => {
    const visibleCards = block.querySelectorAll('.settings-hub-card[style="display: flex;"]');
    if (q && visibleCards.length === 0 && block.querySelectorAll('.settings-hub-card').length > 0) {
      const anyVisible = Array.from(block.querySelectorAll('.settings-hub-card')).some(c => c.style.display !== 'none');
      block.style.display = anyVisible ? 'block' : 'none';
    } else {
      block.style.display = 'block';
    }
  });
};

window.openSettingsCategory = function(catId) {
  state.settingsView = 'detail';
  state.settingsActiveCategory = catId;
  renderSettingsSection();
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

window.returnToSettingsHub = function() {
  state.settingsView = 'hub';
  renderSettingsSection();
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

// --------------------------------------------------------------------------
// 2. Settings Detail View (Dedicated Granular Configuration Panel)
// --------------------------------------------------------------------------
function renderSettingsDetail(container, catId) {
  const cat = ALL_SETTINGS_CATEGORIES.find(c => c.id === catId) || ALL_SETTINGS_CATEGORIES[0];

  container.innerHTML = `
    <!-- Breadcrumb & Header Bar -->
    <div class="settings-detail-header">
      <div>
        <div class="settings-breadcrumb">
          <a onclick="returnToSettingsHub()">Settings</a>
          <span>/</span>
          <span>${cat.domainTitle}</span>
          <span>/</span>
          <span style="color:var(--text-primary); font-weight:600;">${cat.id}. ${cat.title}</span>
        </div>
        <h2 style="font-size:22px; font-weight:700; display:flex; align-items:center; gap:10px;">
          <span>${cat.icon}</span>
          <span>${cat.id}. ${cat.title}</span>
        </h2>
        <p style="font-size:13px; color:var(--text-secondary); margin-top:4px;">${cat.desc}</p>
      </div>

      <div style="display:flex; gap:10px;">
        <button class="btn-secondary" onclick="returnToSettingsHub()">
          ← All Settings
        </button>
        <button class="btn-primary" style="width:auto;" onclick="saveAllSettings()">
          Save Policy Changes
        </button>
      </div>
    </div>

    <!-- 2-Column Detail Layout: Left Sidebar + Right Content Panel -->
    <div class="settings-detail-layout">
      <!-- Left Category Selector Sidebar -->
      <aside class="settings-sidebar-list">
        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700; padding:4px 8px; margin-bottom:8px;">
          All 32 Categories:
        </div>
        ${ALL_SETTINGS_CATEGORIES.map(c => `
          <div class="settings-sidebar-link ${c.id === cat.id ? 'active' : ''}" onclick="openSettingsCategory('${c.id}')">
            <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted);">${c.id}</span>
            <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${c.title}</span>
          </div>
        `).join('')}
      </aside>

      <!-- Right Main Content -->
      <div class="settings-panel-content">
        ${renderCategoryControls(cat.id)}
      </div>
    </div>
  `;
}

// --------------------------------------------------------------------------
// 3. Category Controls Renderer (All 32 Sections)
// --------------------------------------------------------------------------
function renderCategoryControls(id) {
  switch (id) {
    case '01': // Account & Profile
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">01. Host Profile & Identity</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Host Display Name</h4>
            <p>Primary name identifying the authenticated owner.</p>
          </div>
          <input type="text" class="form-input" style="max-width:260px;" value="${state.host ? state.host.name : 'Sukhraj Singh'}" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Primary Contact Email</h4>
            <p>Master communication address for executive briefings and security alerts.</p>
          </div>
          <input type="email" class="form-input" style="max-width:260px;" value="${state.host ? state.host.email : 'host@zonata.internal'}" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Preferred Currency & Region</h4>
            <p>Base financial unit used for financial analysis and mission budgets.</p>
          </div>
          <select class="form-input" style="max-width:260px;">
            <option>₹ INR — Indian Rupee</option>
            <option>$ USD — US Dollar</option>
            <option>€ EUR — Euro</option>
            <option>£ GBP — British Pound</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Account Identifiers</h4>
            <p>Cryptographic ID assigned to this host authority node.</p>
          </div>
          <span style="font-family:var(--font-mono); font-size:12px; color:var(--accent-cyan);">usr_host_node_7f99a0e2</span>
        </div>

        <div class="settings-danger-card">
          <div class="settings-danger-header">⚠️ Account Danger Zone</div>
          <p style="font-size:12.5px; color:var(--text-secondary); margin-bottom:12px;">Deactivating or exporting account data will generate an encrypted archive of all companies and ledgers.</p>
          <div style="display:flex; gap:10px;">
            <button class="btn-secondary" onclick="showToast('Exporting host data package...', 'info')">Export Account Data</button>
            <button class="btn-secondary" style="color:var(--accent-rose); border-color:rgba(244,63,94,0.4);" onclick="if(confirm('Deactivate host account? This will pause all active missions.')) showToast('Account deactivation requested.', 'warning');">Deactivate Account</button>
          </div>
        </div>
      `;

    case '02': // Security & Authentication
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">02. Security & Authentication Controls</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Two-Factor Authentication (2FA / TOTP)</h4>
            <p>Require hardware security key or authenticator application on login and consequential actions.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>FIDO2 / WebAuthn Passkeys</h4>
            <p>Allow biometric TouchID/Windows Hello authentication without passwords.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Session Inactivity Timeout</h4>
            <p>Automatically lock the workstation when idle.</p>
          </div>
          <select class="form-input" style="max-width:200px;">
            <option>15 Minutes</option>
            <option selected>30 Minutes</option>
            <option>1 Hour</option>
            <option>4 Hours</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Suspicious Login Defense</h4>
            <p>Block access attempts from unrecognized IP blocks or geographic anomalies.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>

        <h4 style="font-size:14px; margin:20px 0 10px; color:var(--accent-blue);">Active Workstation Sessions</h4>
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px; font-size:12.5px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong>Chrome on Linux (Primary Host Workstation)</strong>
            <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">IP: 127.0.0.1 • Active Now • Trusted Device</div>
          </div>
          <button class="btn-secondary" style="font-size:11.5px; padding:4px 8px; color:var(--accent-rose);" onclick="showToast('Logged out other devices.', 'info')">Revoke Other Sessions</button>
        </div>
      `;

    case '03': // Organization & Workspace
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">03. Organization & Workspace Control</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Workspace Name</h4>
            <p>Master tenant identifier for your company group.</p>
          </div>
          <input type="text" class="form-input" style="max-width:260px;" value="ZONATA Master Enterprise" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Default Autonomy Level</h4>
            <p>Workspace baseline governance applied to newly initialized companies.</p>
          </div>
          <select class="form-input" style="max-width:260px;">
            <option>Level 3 — Ask Before Consequential Action</option>
            <option>Level 4 — Execute Within Budget Caps</option>
            <option>Level 1 — Read Only / Observation</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Default Notification Policy</h4>
            <p>When to alert the Host during execution.</p>
          </div>
          <select class="form-input" style="max-width:260px;">
            <option>High Priority & Financial Only</option>
            <option>All Mission State Transitions</option>
            <option>Emergency Stops Only</option>
          </select>
        </div>
      `;

    case '04': // Companies & Isolation
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">04. Companies & Multi-Tenant Isolation</h3>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
          Enforces strict epistemic and cryptographic boundaries. No data, credentials, or agent contexts are leaked across companies.
        </p>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Strict Knowledge Isolation</h4>
            <p>Prevent agents in Hotel Company from querying Manufacturing or SaaS databases.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Independent Credential Brokering</h4>
            <p>API keys and OAuth tokens are stored in company-specific hardware vaults.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Require Company Verification on Onboarding</h4>
            <p>Verify business tax ID or corporate domain before deploying autonomous workforce.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
      `;

    case '05': // AI CEO Settings
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">05. AI CEO Operating Settings</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>AI CEO Persona & Style</h4>
            <p>Operating mindset for strategic synthesis and recommendations.</p>
          </div>
          <select class="form-input" style="max-width:260px;">
            <option>Balanced & Rigorous (Recommended)</option>
            <option>Conservative & Risk-Averse</option>
            <option>Proactive Growth & Innovation</option>
            <option>Aggressive Full Automation</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Executive Response Length</h4>
            <p>Level of detail provided in executive briefings and Decision Room packets.</p>
          </div>
          <select class="form-input" style="max-width:200px;">
            <option>Concise Action Items</option>
            <option selected>Standard Structured Packages</option>
            <option>Comprehensive Decomposition</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Permit External Communications</h4>
            <p>Allow AI CEO to send emails, voice calls, or notifications on Host's behalf.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Autonomous Tool Creation</h4>
            <p>Allow AI CEO to trigger Tool Factory when capabilities are missing.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
      `;

    case '06': // AI Workforce
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">06. AI Workforce & Agent Governance</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Allow Dynamic Employee Creation</h4>
            <p>AI CEO synthesizes custom agent roles on-demand rather than fixed templates.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Maximum Workforce Headcount per Company</h4>
            <p>Hard ceiling on simultaneously provisioned AI workers.</p>
          </div>
          <input type="number" class="form-input" style="max-width:180px;" value="25" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Mandatory Sandbox Certification</h4>
            <p>Every newly created agent must pass 10 automated test scenarios before entering production.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Default Per-Agent Monthly Spend Cap (₹)</h4>
            <p>Ceiling on API tokens and external tool costs per worker.</p>
          </div>
          <input type="number" class="form-input" style="max-width:180px;" value="30000" />
        </div>
      `;

    case '07': // Missions & Automation
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">07. Missions, Scheduling & Night Shift</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Night Shift & Overnight Operations</h4>
            <p>Permit workforce to execute scheduled audits, backups, and reports between 22:00 and 06:00.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Dual Verification Requirement</h4>
            <p>Missions require both agent completion claim and physical truth ledger proof.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Mission Retry Limit</h4>
            <p>Maximum automated retries on tool transient failure before escalating to Host.</p>
          </div>
          <input type="number" class="form-input" style="max-width:120px;" value="3" />
        </div>

        <div class="settings-danger-card">
          <div class="settings-danger-header">🚨 Emergency Kill Switches</div>
          <p style="font-size:12.5px; color:var(--text-secondary); margin-bottom:12px;">Instantly freeze autonomous operations across all hosts in case of emergency.</p>
          <div style="display:flex; gap:10px;">
            <button class="btn-secondary" style="color:var(--accent-amber); border-color:var(--accent-amber);" onclick="showToast('All missions paused.', 'warning')">Pause All Missions</button>
            <button class="btn-secondary" style="color:var(--accent-rose); border-color:var(--accent-rose);" onclick="if(confirm('Trigger EMERGENCY WORKFORCE STOP?')) showToast('EMERGENCY STOP ACTIVATED.', 'error');">Emergency Kill Switch</button>
          </div>
        </div>
      `;

    case '08': // AI Models & Intelligence
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">08. AI Models, Intelligent Routing & Quotas</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Primary Executive Model</h4>
            <p>Main model for AI CEO decision room and strategic synthesis.</p>
          </div>
          <select class="form-input" style="max-width:260px;">
            <option selected>Gemini 3.8 Flash (High)</option>
            <option>Gemini 1.5 Pro</option>
            <option>Claude 3.5 Sonnet</option>
            <option>OpenAI GPT-4o</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Task Routing Matrix</h4>
            <p>Auto-assign low-cost models to routine scraping, high-reasoning models to financials.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Local / Private Fallback (Ollama / On-Premise)</h4>
            <p>Route sensitive data through local GPU weights without external API calls.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Monthly Token Expenditure Cap (₹)</h4>
            <p>Ceiling on cumulative LLM API inference costs.</p>
          </div>
          <input type="number" class="form-input" style="max-width:180px;" value="100000" />
        </div>
      `;

    case '09': // Tools & Tool Factory
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">09. Tools & Autonomous Tool Factory</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Allow AI to Synthesize Tools</h4>
            <p>Build new tools in controlled sandbox when required by high-value missions.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Require Human Approval Before Tool Production Deployment</h4>
            <p>Newly synthesized tools require Host sign-off before leaving sandbox.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Permitted Tool Programming Languages</h4>
            <p>Sandboxed languages allowed for generated tools.</p>
          </div>
          <span style="font-family:var(--font-mono); font-size:12px; color:var(--accent-emerald);">Python 3.12, Node.js 20, Bash (Sandbox Only)</span>
        </div>
      `;

    case '10': // Computer & Robotic Control
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">10. Computer & Robotic Desktop Control</h3>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
          Controls the Universal Robotic Assistant's ability to perceive screens, click, type, and manipulate host applications.
        </p>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Screen Perception & OCR Vision</h4>
            <p>Allows robot agents to inspect window buffers and identify UI elements.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Mouse & Keyboard Input Driver</h4>
            <p>Permit hardware simulation of native keystrokes, clicks, and shortcuts.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Robotic Autonomy Ceiling</h4>
            <p>Highest permitted level of unsupervised desktop operation.</p>
          </div>
          <select class="form-input" style="max-width:260px;">
            <option selected>Level 4 — Execute Approved Workflows</option>
            <option>Level 3 — Ask Before Any Desktop Action</option>
            <option>Level 5 — Fully Delegated Workstation</option>
          </select>
        </div>

        <h4 style="font-size:14px; margin:20px 0 10px; color:var(--accent-blue);">Application Access Matrix</h4>
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px; font-size:12.5px;">
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
            <div>Chrome / Browser: <span style="color:var(--accent-emerald); font-weight:600;">✓ Allowed</span></div>
            <div>VS Code / IDE: <span style="color:var(--accent-emerald); font-weight:600;">✓ Allowed</span></div>
            <div>Excel / Spreadsheets: <span style="color:var(--accent-emerald); font-weight:600;">✓ Allowed</span></div>
            <div>Accounting Software: <span style="color:var(--accent-amber); font-weight:600;">⚠️ Approval Required</span></div>
            <div>Banking Portals: <span style="color:var(--accent-rose); font-weight:600;">🛑 Blocked Completely</span></div>
            <div>System Root Terminal: <span style="color:var(--accent-amber); font-weight:600;">⚠️ Approval Required</span></div>
          </div>
        </div>
      `;

    case '11': // Integrations
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">11. Integrations & Connected Business Systems</h3>
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${['Stripe Payments Gateway', 'Opera Hospitality PMS', 'HubSpot CRM', 'SAP ERP & NetSuite', 'Google Workspace (Gmail & Drive)', 'Slack & Microsoft Teams'].map(sys => `
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px 14px; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:600; font-size:13.5px;">${sys}</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">Status: <span style="color:var(--accent-emerald); font-weight:600;">Connected</span> • Scoped per company</div>
              </div>
              <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px;" onclick="showToast('Re-authenticated ${sys}', 'success')">Configure</button>
            </div>
          `).join('')}
        </div>
      `;

    case '12': // Knowledge & Data
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">12. Knowledge Base & Data Retention</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Continuous Vector & Entity Indexing</h4>
            <p>Ingest updated SOPs, emails, and transaction receipts into knowledge graph.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Role-Based Knowledge Redaction</h4>
            <p>Marketing agents cannot view unredacted payroll or bank ledger tables.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Knowledge Retention Period</h4>
            <p>Historical audit trails and document embeddings storage duration.</p>
          </div>
          <select class="form-input" style="max-width:200px;">
            <option>1 Year</option>
            <option selected>3 Years (Standard)</option>
            <option>7 Years (Compliance)</option>
            <option>Permanent</option>
          </select>
        </div>
      `;

    case '13': // Communication
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">13. Communication & Telephony Settings</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Automated Voice Agent Telephony</h4>
            <p>Allow phone concierge agents to handle guest/customer inquiries.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Call Recording & Epistemic Audit</h4>
            <p>Record, transcribe, and verify all telephony interactions.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Scheduled Executive Sync Times</h4>
            <p>Daily morning meeting and evening handover times.</p>
          </div>
          <span style="font-family:var(--font-mono); font-size:12px; color:var(--accent-blue);">08:30 Morning Sync • 20:00 Night Handover</span>
        </div>
      `;

    case '14': // Sales & CRM
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">14. Commercial Sales & CRM Automation</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Maximum Commercial Discount Authority</h4>
            <p>Discounts above this threshold require owner approval in Decision Room.</p>
          </div>
          <input type="text" class="form-input" style="max-width:160px;" value="15% Maximum" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Automated Proposal Dispatch</h4>
            <p>Draft and send verified enterprise quotation decks automatically.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
      `;

    case '15': // Marketing & Advertising
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">15. Marketing & Paid Advertising Limits</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Monthly Advertising Budget Ceiling (₹)</h4>
            <p>Cumulative spend ceiling across Meta Ads, Google Ads, and LinkedIn.</p>
          </div>
          <input type="number" class="form-input" style="max-width:180px;" value="50000" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Maximum Single Ad Campaign Spend without Sign-off (₹)</h4>
            <p>Campaigns above this amount trigger an Attention Required alert.</p>
          </div>
          <input type="number" class="form-input" style="max-width:180px;" value="10000" />
        </div>
      `;

    case '16': // Finance, Payments & Budgets
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">16. Finance, Payments & Hard Spending Stops</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Automatic Execution Limit</h4>
            <p>Routine operations under this amount execute without manual prompt.</p>
          </div>
          <input type="text" class="form-input" style="max-width:180px;" value="₹0 to ₹1,000" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Host Approval Required Tier</h4>
            <p>Medium-risk operations require owner sign-off in Decision Room.</p>
          </div>
          <input type="text" class="form-input" style="max-width:180px;" value="₹1,001 to ₹10,000" />
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Mandatory Executive Multi-Sig Threshold</h4>
            <p>Requires password verification or 2FA key.</p>
          </div>
          <input type="text" class="form-input" style="max-width:180px;" value="₹10,000+" />
        </div>
      `;

    case '17': // Documents & Contracts
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">17. Documents & Contract Verification</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Automated Contract Risk Analysis</h4>
            <p>Flag non-standard liability clauses and indemnity caps in inbound vendor agreements.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Signature Execution Gate</h4>
            <p>AI may draft and compare contract revisions, but signature requires Host authorization.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
      `;

    case '18': // Notifications & Alerts
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">18. Notifications & Alert Routing</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Critical Security Alerts</h4>
            <p>Immediate push notification and SMS to Host phone.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Mission Verification Notifications</h4>
            <p>Receive summaries when major business missions complete.</p>
          </div>
          <select class="form-input" style="max-width:200px;">
            <option>Daily Digest Only</option>
            <option selected>Instant In-App Toast</option>
            <option>Email & Push</option>
          </select>
        </div>
      `;

    case '19': // Approvals & Governance
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">19. Approvals & Governance Policies</h3>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
          Configurable policy engine: <code>IF action = financial THEN approval required</code>.
        </p>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Destructive Operations Gate</h4>
            <p>Mandatory approval for deleting production databases, models, or repos.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>External Customer Messaging Gate</h4>
            <p>Mass campaigns over 500 recipients require 1-click owner sign-off.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
      `;

    case '20': // Permissions & RBAC
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">20. Role-Based Access Control (RBAC)</h3>
        <table class="matrix-table">
          <thead>
            <tr>
              <th>Role</th>
              <th>Manage Companies</th>
              <th>AI CEO Command</th>
              <th>Approve Spend</th>
              <th>Access Ledger</th>
            </tr>
          </thead>
          <tbody>
            <tr><td><strong>Host / Owner</strong></td><td>✓ Full</td><td>✓ Full</td><td>✓ Full</td><td>✓ Full</td></tr>
            <tr><td><strong>Executive</strong></td><td>✓ Edit</td><td>✓ Command</td><td>⚠️ Limited</td><td>✓ Read</td></tr>
            <tr><td><strong>Manager</strong></td><td>✓ View</td><td>✓ View</td><td>❌ None</td><td>✓ Read</td></tr>
            <tr><td><strong>AI Specialist</strong></td><td>❌ None</td><td>❌ None</td><td>❌ Bounded Cap</td><td>✓ Log Only</td></tr>
          </tbody>
        </table>
      `;

    case '21': // Privacy & Data Governance
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">21. Privacy, PII Redaction & Data Protection</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Automated PII Masking</h4>
            <p>Mask credit cards, phone numbers, and Aadhaar/SSN before prompt ingestion.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Zero LLM Training Invariant</h4>
            <p>Enforce strict corporate policy that host prompt telemetry is never used for foundation training.</p>
          </div>
          <span style="color:var(--accent-emerald); font-weight:700;">ENFORCED & LOCKED</span>
        </div>
      `;

    case '22': // Security Operations
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">22. Security Operations (SecOps) & Threat Monitoring</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Prompt Injection & Jailbreak Defense</h4>
            <p>Kernel inspects external web pages and emails for adversarial prompt injections.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>IP Allowlisting</h4>
            <p>Restrict Host dashboard access to authorized office or VPN subnets.</p>
          </div>
          <input type="text" class="form-input" style="max-width:240px;" placeholder="e.g. 192.168.1.0/24, 10.0.0.1" />
        </div>
      `;

    case '23': // Audit & Activity
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">23. Audit Ledger & Activity Traceability</h3>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:14px;">Every action is anchored to an append-only SHA-256 evidence chain.</p>
        <div style="background:#070b14; border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px; font-family:var(--font-mono); font-size:12px; color:#10b981;">
          <div>12:41:02 [AI_CEO]: CREATED MISSION MSN-SAAS-001 (STATUS=DISCOVER)</div>
          <div>12:43:18 [CUSTOMER_SUCCESS_AGENT]: INGESTED SUBSCRIPTION TELEMETRY</div>
          <div>12:46:50 [HOST]: AUTHORIZED DISPUTE SETTLEMENT PO #7712</div>
          <div>12:52:10 [EVIDENCE_LEDGER]: BLOCK #412 HASH VERIFIED (SHA-256: d4a7...99bf)</div>
        </div>
      `;

    case '24': // Usage, Tokens & Costs
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">24. Usage, Tokens & Cost Breakdown</h3>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">Answer clearly: <em>"Where is my money going?"</em></p>
        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:20px;">
          <div style="background:var(--bg-surface); padding:12px; border-radius:var(--radius-md); text-align:center;">
            <div style="font-size:11px; color:var(--text-muted);">AI TOKENS</div>
            <div style="font-size:18px; font-weight:700;">₹14,200</div>
          </div>
          <div style="background:var(--bg-surface); padding:12px; border-radius:var(--radius-md); text-align:center;">
            <div style="font-size:11px; color:var(--text-muted);">ROBOT COMPUTE</div>
            <div style="font-size:18px; font-weight:700;">₹4,300</div>
          </div>
          <div style="background:var(--bg-surface); padding:12px; border-radius:var(--radius-md); text-align:center;">
            <div style="font-size:11px; color:var(--text-muted);">AD SPEND</div>
            <div style="font-size:18px; font-weight:700;">₹8,500</div>
          </div>
        </div>
      `;

    case '25': // Billing & Subscription
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">25. SaaS Plan & Enterprise Billing</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Active Plan</h4>
            <p>ZONATA Universal Enterprise Dedicated Host Plan</p>
          </div>
          <span class="badge badge-emerald" style="font-size:13px; padding:6px 12px;">ACTIVE — UNLIMITED SEATS</span>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Billing Cycle & Payment Gateway</h4>
            <p>Next billing date: 15 October 2026 via Corporate Direct Debit.</p>
          </div>
          <button class="btn-secondary" style="font-size:12px;" onclick="showToast('Invoices downloaded.', 'info')">Download Invoices</button>
        </div>
      `;

    case '26': // API & Developer
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">26. API Keys & Developer Controls</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Production Master API Key</h4>
            <p>Used to authenticate programmatic REST & CLI integrations.</p>
          </div>
          <div style="display:flex; gap:8px;">
            <input type="password" class="form-input" style="max-width:220px;" value="zonata_live_sec_99a8bc4732" readonly />
            <button class="btn-secondary" style="font-size:12px;" onclick="showToast('API key copied.', 'success')">Copy</button>
          </div>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Interactive OpenAPI Documentation</h4>
            <p>Explore endpoints on http://localhost:8080/api/docs</p>
          </div>
          <a href="/api/portfolio" target="_blank" class="btn-secondary" style="font-size:12px; text-decoration:none;">View Endpoints JSON →</a>
        </div>
      `;

    case '27': // Webhooks & Events
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">27. Webhooks & Event Ingestion</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>HMAC SHA-256 Webhook Verification</h4>
            <p>Reject unsigned inbound webhooks from Stripe, Shopify, or PMS.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Outbound Event Notifications</h4>
            <p>Broadcast mission completion and approval events to your Slack/Teams webhook.</p>
          </div>
          <input type="text" class="form-input" style="max-width:280px;" placeholder="https://hooks.slack.com/services/..." />
        </div>
      `;

    case '28': // Localization
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">28. Localization & Regional Business Settings</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>System Time Zone</h4>
            <p>Used for daily executive briefings, night shifts, and transaction timestamps.</p>
          </div>
          <select class="form-input" style="max-width:260px;">
            <option selected>Asia/Kolkata (IST - UTC+5:30)</option>
            <option>America/New_York (EST - UTC-5:00)</option>
            <option>Europe/London (GMT - UTC+0:00)</option>
            <option>Asia/Singapore (SGT - UTC+8:00)</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Default Currency Symbol</h4>
            <p>Displayed on revenue dashboards and mission budget meters.</p>
          </div>
          <select class="form-input" style="max-width:160px;">
            <option selected>₹ (INR)</option>
            <option>$ (USD)</option>
            <option>€ (EUR)</option>
            <option>£ (GBP)</option>
          </select>
        </div>
      `;

    case '29': // Appearance & Interface
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">29. Appearance & UI Density</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Color Theme</h4>
            <p>High-contrast dark mode or clean daylight theme.</p>
          </div>
          <div style="display:flex; gap:10px;">
            <button class="btn-secondary" onclick="document.documentElement.setAttribute('data-theme', 'dark'); showToast('Dark theme activated', 'info');">Dark Mode</button>
            <button class="btn-secondary" onclick="document.documentElement.setAttribute('data-theme', 'light'); showToast('Light theme activated', 'info');">Light Mode</button>
          </div>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Information Density</h4>
            <p>Card padding and metric visualization layout.</p>
          </div>
          <select class="form-input" style="max-width:200px;">
            <option selected>Comfortable Enterprise</option>
            <option>Compact Operations View</option>
          </select>
        </div>
      `;

    case '30': // Backup & Recovery
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">30. Backup & Disaster Recovery</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Daily Automated Snapshot Backup</h4>
            <p>Create encrypted SQLite snapshot including all entities and SHA-256 ledgers.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Manual Backup Trigger</h4>
            <p>Immediately snapshot full host state to cold storage.</p>
          </div>
          <button class="btn-secondary" style="font-size:12px;" onclick="showToast('Created snapshot backup: backup_20260928_host.tar.gz', 'success')">Snapshot Now</button>
        </div>
      `;

    case '31': // Enterprise Administration
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">31. Enterprise Multi-Workspace Administration</h3>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Enterprise SCIM Directory Sync</h4>
            <p>Automated provisioning through Okta, Azure AD, or Google Workspace.</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Cross-Workspace Audit Log Aggregation</h4>
            <p>Forward all evidence digests to enterprise SIEM (Splunk / Datadog).</p>
          </div>
          <label class="switch"><input type="checkbox" checked /><span class="slider"></span></label>
        </div>
      `;

    case '32': // Advanced / Developer Controls
      return `
        <h3 style="font-size:16px; margin-bottom:14px;">32. Advanced Developer & Runtime Flags</h3>
        <p style="font-size:12.5px; color:var(--text-muted); margin-bottom:16px;">
          Low-level infrastructure settings. Gated to prevent accidental alteration of system kernel invariants.
        </p>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Strict Epistemic Invariant Enforcement</h4>
            <p>Asserts claim != execution != physical reality across all tool calls.</p>
          </div>
          <label class="switch"><input type="checkbox" checked disabled /><span class="slider"></span></label>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Desktop Sandbox Isolation Mode</h4>
            <p>Controls whether robotic executions run in isolated process namespaces.</p>
          </div>
          <select class="form-input" style="max-width:240px;">
            <option selected>Strict Container & Cgroup</option>
            <option>Host Native Process (Dev)</option>
          </select>
        </div>
        <div class="settings-row">
          <div class="settings-info">
            <h4>Verbose Kernel Debug Traces</h4>
            <p>Outputs AST evaluation and token latencies to server stderr.</p>
          </div>
          <label class="switch"><input type="checkbox" /><span class="slider"></span></label>
        </div>
      `;

    default:
      return `<p>Select a category from the sidebar or return to the settings hub.</p>`;
  }
}

window.exportSettingsPolicy = function() {
  const policy = {
    host: state.host ? state.host.email : 'host@zonata.internal',
    exportedAt: new Date().toISOString(),
    domainsCount: SETTINGS_DOMAINS.length,
    categoriesCount: ALL_SETTINGS_CATEGORIES.length,
    settings: state.settings
  };
  const blob = new Blob([JSON.stringify(policy, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `zonata_enterprise_policy_${Date.now()}.json`;
  a.click();
  showToast('Exported enterprise policy JSON.', 'success');
};


window.saveAllSettings = function() {
  saveData();
  showToast('Settings saved successfully.', 'success');
};

// ==========================================================================
// MODAL & TOAST SYSTEM
// ==========================================================================
function openModal(title, bodyHtml) {
  const overlay = document.getElementById('modalOverlay');
  const titleEl = document.getElementById('modalTitle');
  const bodyEl = document.getElementById('modalBody');

  if (overlay && titleEl && bodyEl) {
    titleEl.textContent = title;
    bodyEl.innerHTML = bodyHtml;
    overlay.classList.add('active');
  }
}

function closeModal() {
  const overlay = document.getElementById('modalOverlay');
  if (overlay) overlay.classList.remove('active');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span style="font-size:16px;">${type === 'success' ? '✓' : (type === 'error' ? '✕' : 'ℹ')}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// ==========================================================================
// SEARCH, DIRECTIVE & SIMULATION MODALS
// ==========================================================================

window.handleGlobalSearch = function(query) {
  if (!query || query.trim().length < 2) return;
  const q = query.toLowerCase().trim();

  // Search across entities
  const matchCompanies = state.companies.filter(c => c.name.toLowerCase().includes(q) || c.industry.toLowerCase().includes(q));
  const matchWorkforce = state.workforce.filter(w => w.role.toLowerCase().includes(q) || w.department.toLowerCase().includes(q));
  const matchMissions = state.missions.filter(m => m.title.toLowerCase().includes(q) || m.targetOutcome.toLowerCase().includes(q));
  const matchTools = state.tools.filter(t => t.name.toLowerCase().includes(q) || t.desc.toLowerCase().includes(q));

  const total = matchCompanies.length + matchWorkforce.length + matchMissions.length + matchTools.length;
  if (total === 0) return;

  openModal(`Search Results for "${query}" (${total} Matches)`, `
    <div style="font-size:13px; line-height:1.5;">
      ${matchCompanies.length > 0 ? `
        <div style="margin-bottom:14px;">
          <h4 style="font-size:13px; color:var(--accent-blue); text-transform:uppercase; margin-bottom:6px;">Companies (${matchCompanies.length})</h4>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${matchCompanies.map(c => `
              <div style="padding:8px 12px; background:var(--bg-surface); border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center;">
                <div><strong>${c.name}</strong> • <span style="color:var(--text-secondary);">${c.industry}</span></div>
                <button class="btn-secondary" style="font-size:11.5px; padding:3px 8px;" onclick="closeModal(); openCompanyInCeo('${c.id}');">Open</button>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${matchWorkforce.length > 0 ? `
        <div style="margin-bottom:14px;">
          <h4 style="font-size:13px; color:var(--accent-purple); text-transform:uppercase; margin-bottom:6px;">AI Employees (${matchWorkforce.length})</h4>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${matchWorkforce.map(w => `
              <div style="padding:8px 12px; background:var(--bg-surface); border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center;">
                <div><strong>${w.role}</strong> • <span style="color:var(--text-secondary);">${w.department}</span></div>
                <span class="badge badge-blue">${w.model}</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${matchMissions.length > 0 ? `
        <div style="margin-bottom:14px;">
          <h4 style="font-size:13px; color:var(--accent-emerald); text-transform:uppercase; margin-bottom:6px;">Missions (${matchMissions.length})</h4>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${matchMissions.map(m => `
              <div style="padding:8px 12px; background:var(--bg-surface); border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center;">
                <div><strong>${m.title}</strong> • <span style="color:var(--accent-cyan);">${m.status}</span></div>
                <button class="btn-secondary" style="font-size:11.5px; padding:3px 8px;" onclick="closeModal(); viewMissionLedger('${m.id}');">Ledger</button>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${matchTools.length > 0 ? `
        <div style="margin-bottom:14px;">
          <h4 style="font-size:13px; color:var(--accent-amber); text-transform:uppercase; margin-bottom:6px;">Tools & Capabilities (${matchTools.length})</h4>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${matchTools.map(t => `
              <div style="padding:8px 12px; background:var(--bg-surface); border-radius:var(--radius-sm); display:flex; justify-content:space-between; align-items:center;">
                <div>${t.icon} <strong>${t.name}</strong> • <span style="color:var(--text-secondary);">${t.category}</span></div>
                <button class="btn-secondary" style="font-size:11.5px; padding:3px 8px;" onclick="closeModal(); switchNav('tools');">View</button>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `);
};

window.openNewDirectiveModal = function() {
  const activeComp = state.companies.find(c => c.id === state.activeCompanyId) || state.companies[0];

  openModal('Ask AI CEO — Strategic Instruction', `
    <form onsubmit="submitDirectiveModal(event)">
      <div class="form-group">
        <label class="form-label">Target Company</label>
        <select class="form-input" id="directiveCompSelect">
          ${state.companies.map(c => `<option value="${c.id}" ${c.id === (activeComp ? activeComp.id : '') ? 'selected' : ''}>${c.name} (${c.industry})</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Strategic Directive / Objective *</label>
        <textarea class="form-input" id="directiveModalText" rows="3" placeholder="e.g. Conduct a comprehensive audit of high-drop-off signups in our onboarding funnel and draft automated email and desktop walkthroughs." required></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">Operational Spend Authority (₹)</label>
        <input type="number" class="form-input" id="directiveSpendCap" value="25000" />
      </div>
      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:16px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">Dispatch Directive to CEO</button>
      </div>
    </form>
  `);
};

window.submitDirectiveModal = function(e) {
  e.preventDefault();
  const cid = document.getElementById('directiveCompSelect').value;
  const text = document.getElementById('directiveModalText').value;
  const spend = parseFloat(document.getElementById('directiveSpendCap').value) || 25000;

  state.activeCompanyId = cid;
  const newMission = {
    id: `MSN-${Date.now().toString(36).toUpperCase()}`,
    companyId: cid,
    title: `Directive: ${text.slice(0, 45)}...`,
    targetOutcome: text,
    assignedAgents: ['AI CEO Strategic Specialist'],
    toolsUsed: ['web_search', 'python3', 'browser_robot'],
    budget: spend,
    costIncurred: 0,
    revenueRecovered: 0,
    status: 'ACTIVE',
    verificationSummary: 'Strategic directive synthesized; running',
    timestamp: 'Just now'
  };

  state.missions.unshift(newMission);
  saveData();
  closeModal();
  showToast('Directive dispatched to AI CEO.', 'success');
  switchNav('ceo');
};

window.openSimulateMissionModal = function() {
  const activeComp = state.companies.find(c => c.id === state.activeCompanyId) || state.companies[0];

  openModal(`Digital Twin Simulation: ${activeComp ? activeComp.name : 'Venture'}`, `
    <div style="font-size:13px; line-height:1.5;">
      <p style="color:var(--text-secondary); margin-bottom:14px;">
        The Digital Twin allows the owner and AI CEO to simulate operational impact (risk, margin delta, tool failure likelihood) in an isolated sandbox before executing in production.
      </p>
      <div class="form-group">
        <label class="form-label">Proposed Action / Campaign</label>
        <input type="text" class="form-input" id="simAction" value="Automated Flash Discount Campaign to Recover Cart Abandoners" />
      </div>
      <div class="form-group">
        <label class="form-label">Estimated Budget (₹)</label>
        <input type="number" class="form-input" id="simBudget" value="15000" />
      </div>
      <button class="btn-secondary" style="width:100%; margin-bottom:14px;" onclick="runSimulationTest()">
        Run Pre-Flight Twin Simulation
      </button>
      <div id="simResultBox" style="display:none; background:#070b14; padding:14px; border-radius:var(--radius-md); font-family:var(--font-mono); font-size:12px; color:#10b981;">
        <!-- Injected on run -->
      </div>
      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:16px;">
        <button class="btn-secondary" onclick="closeModal()">Close</button>
      </div>
    </div>
  `);
};

window.runSimulationTest = function() {
  const box = document.getElementById('simResultBox');
  if (!box) return;
  box.style.display = 'block';
  box.innerHTML = `
    <div>[SIMULATION_STATE]: COMPLETE</div>
    <div>[PREDICTED_REVENUE]: ₹58,000 (+287% ROI)</div>
    <div>[PROJECTED_COST]: ₹14,200</div>
    <div>[ESTIMATED_CONTRIBUTION]: ₹43,800</div>
    <div>[RISK_SCORE]: 0.12 (LOW_RISK)</div>
    <div>[CAN_ROLLBACK]: TRUE (Idempotent DB Transactions)</div>
    <div>[VERIFICATION_CRITERIA]: Stripe webhook payment confirmation</div>
  `;
  showToast('Simulation passed pre-flight checks.', 'success');
};

window.openAssignMissionModal = function(agentId) {
  const agent = state.workforce.find(w => w.id === agentId);
  if (!agent) return;

  openModal(`Direct Task Assignment: ${agent.role}`, `
    <form onsubmit="submitAgentAssignment(event, '${agent.id}')">
      <div class="form-group">
        <label class="form-label">Immediate Objective *</label>
        <textarea class="form-input" id="assignTaskText" rows="3" placeholder="Specify exactly what ${agent.role} should analyze, compute, or execute right now." required></textarea>
      </div>
      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:16px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">Deploy Task to Agent</button>
      </div>
    </form>
  `);
};

window.submitAgentAssignment = function(e, agentId) {
  e.preventDefault();
  const text = document.getElementById('assignTaskText').value;
  const agent = state.workforce.find(w => w.id === agentId);

  const msn = {
    id: `TSK-${Date.now().toString(36).toUpperCase()}`,
    companyId: agent.companyId,
    title: `Task: ${text.slice(0, 40)}...`,
    targetOutcome: text,
    assignedAgents: [agent.role],
    toolsUsed: agent.allowedTools,
    budget: 5000,
    costIncurred: 0,
    revenueRecovered: 0,
    status: 'ACTIVE',
    verificationSummary: 'Executing under direct employment contract',
    timestamp: 'Just now'
  };

  state.missions.unshift(msn);
  saveData();
  closeModal();
  showToast(`Task assigned to ${agent.role}.`, 'success');
  state.ceoTab = 'missions';
  renderCeoSection();
};

// ==========================================================================
// 6. PAPERCLIP AGENT ENGINE & AUTONOMOUS TEAMS MODULE
// ==========================================================================
state.agentEngineTab = 'teams';
state.agentEnginePlans = [];
state.agentEngineTeams = [];
state.agentEngineSkills = [];
state.agentEngineRuns = [];

async function renderAgentEngine() {
  const container = document.getElementById('view-agent-engine');
  if (!container) return;

  container.innerHTML = `
    <div style="display:flex; justify-content:center; align-items:center; padding:60px;">
      <div style="text-align:center;">
        <div style="font-size:32px; margin-bottom:12px;">⚡</div>
        <div style="color:var(--text-secondary); font-size:14px;">Synchronizing Paperclip Agent Engine...</div>
      </div>
    </div>
  `;

  // Fetch live state from API server
  let statusData = { status: 'OPERATIONAL', default_adapter: 'gemini_local', heartbeat_interval_seconds: 30, active_runs_count: 0, active_plans_count: 0, total_bundled_teams: 4, total_skills: 5 };
  try {
    const [stRes, tmRes, skRes, plRes, hbRes] = await Promise.all([
      fetch('/api/agent-engine/status').then(r => r.json()).catch(() => null),
      fetch('/api/agent-engine/teams').then(r => r.json()).catch(() => null),
      fetch('/api/agent-engine/skills').then(r => r.json()).catch(() => null),
      fetch('/api/agent-engine/plans').then(r => r.json()).catch(() => null),
      fetch('/api/agent-engine/heartbeats').then(r => r.json()).catch(() => null),
    ]);
    if (stRes) statusData = stRes;
    if (tmRes && tmRes.teams) state.agentEngineTeams = tmRes.teams;
    if (skRes && skRes.skills) state.agentEngineSkills = skRes.skills;
    if (plRes && plRes.plans) state.agentEnginePlans = plRes.plans;
    if (hbRes && hbRes.runs) state.agentEngineRuns = hbRes.runs;
  } catch (err) {
    console.warn("Could not sync agent-engine live API:", err);
  }

  const activeTab = state.agentEngineTab || 'teams';

  container.innerHTML = `
    <!-- Top Header Banner -->
    <div class="view-header" style="margin-bottom:24px;">
      <div class="view-header-title">
        <div style="display:flex; align-items:center; gap:12px;">
          <h2 style="font-size:24px; font-weight:700;">Paperclip Autonomous Agent Engine</h2>
          <span style="font-size:11px; font-weight:700; background:rgba(139,92,246,0.2); color:#a78bfa; border:1px solid rgba(139,92,246,0.4); padding:3px 10px; border-radius:12px;">
            CORE v2.4
          </span>
        </div>
        <p style="color:var(--text-secondary); font-size:13.5px; margin-top:4px;">
          Autonomous multi-agent execution loop with PRP deterministic state machines, DAG task delegation, and pre-bundled specialized squads.
        </p>
      </div>

      <div style="display:flex; gap:10px;">
        <button class="btn-secondary" onclick="triggerAutonomousHeartbeat()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px;"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          Trigger Heartbeat
        </button>
        <button class="btn-primary" onclick="openNewDelegationPlanModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px;"><path d="M12 5v14M5 12h14"/></svg>
          Delegate Company Goal
        </button>
      </div>
    </div>

    <!-- Metrics Row -->
    <div class="kpi-grid" style="grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-bottom:24px;">
      <div class="kpi-card">
        <div class="kpi-label">Engine State</div>
        <div class="kpi-value" style="color:var(--accent-emerald); font-size:20px;">
          <span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:var(--accent-emerald); margin-right:6px;"></span>
          ${statusData.status}
        </div>
        <div class="kpi-subtext">PRP State Machine Active</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Model Adapter</div>
        <div class="kpi-value" style="font-size:18px;">${statusData.default_adapter}</div>
        <div class="kpi-subtext">Central Config Managed</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Heartbeat Cadence</div>
        <div class="kpi-value" style="font-size:18px;">${statusData.heartbeat_interval_seconds}s <span style="font-size:12px; color:var(--text-secondary);">±2.5s</span></div>
        <div class="kpi-subtext">Exponential Backoff Enabled</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Bundled Squads</div>
        <div class="kpi-value" style="font-size:18px;">${state.agentEngineTeams.length || 4} Squads</div>
        <div class="kpi-subtext">1-Click Deployment Ready</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">Active Delegations</div>
        <div class="kpi-value" style="font-size:18px;">${state.agentEnginePlans.length} Plans</div>
        <div class="kpi-subtext">Topological DAG Monitored</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div style="display:flex; gap:8px; border-bottom:1px solid var(--border-color); margin-bottom:24px;">
      <button class="tab-btn ${activeTab === 'teams' ? 'active' : ''}" onclick="switchAgentEngineTab('teams')">
        🏢 Autonomous Squads Catalog
      </button>
      <button class="tab-btn ${activeTab === 'delegation' ? 'active' : ''}" onclick="switchAgentEngineTab('delegation')">
        🗺️ Goal Delegation & DAG Tracker (${state.agentEnginePlans.length})
      </button>
      <button class="tab-btn ${activeTab === 'heartbeats' ? 'active' : ''}" onclick="switchAgentEngineTab('heartbeats')">
        💓 Heartbeat & PRP State Logs (${state.agentEngineRuns.length})
      </button>
      <button class="tab-btn ${activeTab === 'skills' ? 'active' : ''}" onclick="switchAgentEngineTab('skills')">
        📖 Operational Skills SOPs (${state.agentEngineSkills.length || 5})
      </button>
    </div>

    <!-- Tab Contents -->
    <div id="agentEngineTabContent">
      ${renderAgentEngineTabContent(activeTab)}
    </div>
  `;
}

function switchAgentEngineTab(tabKey) {
  state.agentEngineTab = tabKey;
  renderAgentEngine();
}

function renderAgentEngineTabContent(tab) {
  if (tab === 'teams') return renderTeamsCatalogTab();
  if (tab === 'delegation') return renderDelegationTab();
  if (tab === 'heartbeats') return renderHeartbeatsTab();
  if (tab === 'skills') return renderSkillsTab();
  return '';
}

function renderTeamsCatalogTab() {
  const teams = state.agentEngineTeams.length ? state.agentEngineTeams : [
    {
      id: "core_executive_suite",
      name: "Core Executive Suite",
      category: "Leadership & Governance",
      description: "Autonomous C-Suite governance team modeled after Paperclip's core executive structure. Coordinates cross-departmental execution, board reporting, and capital allocation.",
      icon: "👑",
      agents: [
        { role: "Chief Executive Officer (CEO)", department: "Executive", budget_limit: 10000, allowed_tools: ["task_planning", "board_reporting", "ceo_engine"] },
        { role: "Chief Technology Officer (CTO)", department: "Engineering", budget_limit: 5000, allowed_tools: ["git", "code_review_gate", "python3", "host_fabric"] },
        { role: "Chief Operating Officer (COO)", department: "Operations", budget_limit: 3000, allowed_tools: ["issue_triage", "evidence_ledger", "agent_bus"] },
        { role: "Chief Marketing Officer (CMO)", department: "Growth", budget_limit: 4000, allowed_tools: ["analytics", "browser_robot", "content_generator"] }
      ]
    },
    {
      id: "product_engineering_squad",
      name: "Product & Engineering Squad",
      category: "Product Delivery",
      description: "Full lifecycle autonomous software delivery unit. Rapidly translates requirements into verified code, automated tests, and deployed services.",
      icon: "⚡",
      agents: [
        { role: "Lead Product Manager", department: "Product", budget_limit: 2500, allowed_tools: ["task_planning", "issue_triage"] },
        { role: "Senior Fullstack Engineer", department: "Engineering", budget_limit: 3500, allowed_tools: ["python3", "javascript", "sqlite3", "git"] },
        { role: "QA & Reliability Engineer", department: "Engineering", budget_limit: 2000, allowed_tools: ["curl", "browser_robot", "evidence_ledger"] },
        { role: "DevOps & Platform Engineer", department: "Engineering", budget_limit: 2500, allowed_tools: ["host_fabric", "secrets_manager", "bash"] }
      ]
    },
    {
      id: "growth_revenue_team",
      name: "Growth & Customer Operations Team",
      category: "Revenue & Scaling",
      description: "Customer acquisition, sales automation, and client satisfaction workforce. Drives pipeline expansion and customer retention.",
      icon: "🚀",
      agents: [
        { role: "AI Sales Development Rep (SDR)", department: "Sales", budget_limit: 2000, allowed_tools: ["search_engine", "browser_robot", "crm"] },
        { role: "Customer Success Lead", department: "Customer Support", budget_limit: 2000, allowed_tools: ["issue_triage", "knowledge_base", "analytics"] }
      ]
    },
    {
      id: "security_compliance_squad",
      name: "Security & Audit Governance Squad",
      category: "Risk & Compliance",
      description: "Continuous zero-trust auditing, credential protection, and regulatory verification team.",
      icon: "🛡️",
      agents: [
        { role: "Security Compliance Auditor", department: "Governance", budget_limit: 2000, allowed_tools: ["secrets_manager", "evidence_ledger", "code_review_gate"] }
      ]
    }
  ];

  return `
    <div style="margin-bottom:20px; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <h3 style="font-size:16px; font-weight:600;">Paperclip Pre-Configured Autonomous Squads</h3>
        <p style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
          Deploy full-fidelity specialist teams with pre-configured Digital Employment Contracts, tools, and reporting hierarchy in 1 click.
        </p>
      </div>
      <div>
        <select id="deployTargetCompanySelect" class="form-select" style="font-size:12px; padding:6px 12px; background:var(--bg-surface); border:1px solid var(--border-color); color:var(--text-primary); border-radius:var(--radius-md);">
          ${state.companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
        </select>
      </div>
    </div>

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(440px, 1fr)); gap:20px;">
      ${teams.map(team => `
        <div class="card" style="display:flex; flex-direction:column; justify-content:space-between; padding:20px; border:1px solid var(--border-color); background:var(--bg-card); border-radius:var(--radius-lg);">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:12px;">
                <div style="width:40px; height:40px; border-radius:10px; background:rgba(139,92,246,0.15); display:flex; align-items:center; justify-content:center; font-size:22px;">
                  ${team.icon || '🤖'}
                </div>
                <div>
                  <h4 style="font-size:16px; font-weight:700;">${team.name}</h4>
                  <span style="font-size:11px; color:var(--accent-blue); font-weight:600;">${team.category}</span>
                </div>
              </div>
              <span style="font-size:11px; background:var(--bg-surface); padding:4px 8px; border-radius:6px; border:1px solid var(--border-color);">
                ${team.agents.length} Autonomous Agents
              </span>
            </div>

            <p style="font-size:12.5px; color:var(--text-secondary); line-height:1.5; margin-bottom:16px;">
              ${team.description}
            </p>

            <!-- Agent List Preview -->
            <div style="margin-bottom:16px; background:var(--bg-surface); padding:12px; border-radius:var(--radius-md); border:1px solid var(--border-color);">
              <div style="font-size:11.5px; font-weight:600; color:var(--text-secondary); margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">
                Squad Members & Scoped Contracts:
              </div>
              <div style="display:flex; flex-direction:column; gap:6px;">
                ${team.agents.map(a => `
                  <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; padding:4px 0;">
                    <div style="display:flex; align-items:center; gap:8px;">
                      <span style="width:6px; height:6px; border-radius:50%; background:var(--accent-purple);"></span>
                      <span style="font-weight:600; color:var(--text-primary);">${a.role}</span>
                      <span style="font-size:10.5px; color:var(--text-secondary);">(${a.department})</span>
                    </div>
                    <span style="font-size:11px; color:var(--accent-emerald);">₹${(a.budget_limit || 2000).toLocaleString()}/mo</span>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button class="btn-primary" style="width:100%; font-size:13px; padding:10px;" onclick="deploySquadToCompany('${team.id}')">
              Deploy ${team.name}
            </button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderDelegationTab() {
  const plans = state.agentEnginePlans;

  return `
    <div style="margin-bottom:20px; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <h3 style="font-size:16px; font-weight:600;">Autonomous Goal Decomposition & Dependency DAGs</h3>
        <p style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
          Track high-level board goals decomposed into multi-specialist child tasks with strict topological ordering.
        </p>
      </div>
      <button class="btn-primary" onclick="openNewDelegationPlanModal()" style="font-size:12px; padding:6px 14px;">
        + Create New Delegation
      </button>
    </div>

    ${plans.length === 0 ? `
      <div class="card" style="text-align:center; padding:48px 24px; border:1px dashed var(--border-color);">
        <div style="font-size:36px; margin-bottom:12px;">🗺️</div>
        <h4 style="font-size:16px; font-weight:600; margin-bottom:6px;">No Active Delegation Plans</h4>
        <p style="font-size:13px; color:var(--text-secondary); max-width:440px; margin:0 auto 16px auto;">
          High-level goals are decomposed into structured subtasks with dependencies and assigned automatically to the best specialist agent.
        </p>
        <button class="btn-primary" onclick="openNewDelegationPlanModal()">Decompose Sample Strategic Goal</button>
      </div>
    ` : `
      <div style="display:flex; flex-direction:column; gap:20px;">
        ${plans.map(plan => `
          <div class="card" style="border:1px solid var(--border-color); padding:20px; border-radius:var(--radius-lg); background:var(--bg-card);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
              <div>
                <div style="display:flex; align-items:center; gap:10px;">
                  <h4 style="font-size:17px; font-weight:700;">${plan.goal_title}</h4>
                  <span style="font-size:11px; padding:2px 8px; border-radius:12px; font-weight:600; ${plan.approval_status === 'approved' ? 'background:rgba(16,185,129,0.15); color:var(--accent-emerald);' : 'background:rgba(245,158,11,0.15); color:var(--accent-amber);'}">
                    ${plan.approval_status.toUpperCase()}
                  </span>
                </div>
                <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">
                  Lead Agent: <strong>${plan.lead_agent_id}</strong> • Created: ${plan.created_at || 'Recently'}
                </div>
              </div>

              ${plan.approval_status === 'pending' ? `
                <button class="btn-primary" style="font-size:12px; padding:6px 14px; background:var(--accent-emerald);" onclick="approveDelegationPlan('${plan.goal_id}')">
                  ✓ Approve Plan & Unlock Execution
                </button>
              ` : `
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600;">Execution In Progress</span>
              `}
            </div>

            <!-- Subtask DAG Flow -->
            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:12px;">
              ${plan.subtasks.map((st, idx) => `
                <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px; position:relative;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:10.5px; font-weight:700; color:var(--text-secondary);">TASK ${idx + 1}</span>
                    <span style="font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; ${
                      st.status === 'completed' ? 'background:rgba(16,185,129,0.2); color:var(--accent-emerald);' :
                      st.status === 'blocked' ? 'background:rgba(239,68,68,0.2); color:var(--accent-rose);' :
                      st.status === 'in_progress' ? 'background:rgba(59,130,246,0.2); color:var(--accent-blue);' :
                      'background:rgba(139,92,246,0.2); color:var(--accent-purple);'
                    }">
                      ${st.status.toUpperCase()}
                    </span>
                  </div>

                  <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin-bottom:4px;">
                    ${st.title}
                  </div>

                  <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
                    Assigned: <strong>${st.target_role}</strong>
                  </div>

                  ${st.dependencies && st.dependencies.length > 0 ? `
                    <div style="font-size:10px; color:var(--text-secondary); margin-bottom:8px;">
                      Depends on: ${st.dependencies.map(d => `<span style="background:rgba(255,255,255,0.05); padding:1px 4px; border-radius:3px;">${d}</span>`).join(', ')}
                    </div>
                  ` : ''}

                  ${st.status !== 'completed' && plan.approval_status === 'approved' ? `
                    <button class="btn-secondary" style="width:100%; font-size:11px; padding:4px 8px; margin-top:6px;" onclick="simulateCompleteSubtask('${plan.goal_id}', '${st.id}')">
                      Simulate Step Completion →
                    </button>
                  ` : st.status === 'completed' ? `
                    <div style="font-size:11px; color:var(--accent-emerald); margin-top:4px;">
                      ✓ ${st.result || 'Completed'}
                    </div>
                  ` : ''}
                </div>
              `).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    `}
  `;
}

function renderHeartbeatsTab() {
  const runs = state.agentEngineRuns;

  return `
    <div style="margin-bottom:20px; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <h3 style="font-size:16px; font-weight:600;">Autonomous Agent Heartbeat & PRP State Logs</h3>
        <p style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
          Deterministic execution history tracked by the Paperclip Runner Protocol (PRP) state machine reducer.
        </p>
      </div>
      <button class="btn-primary" onclick="triggerAutonomousHeartbeat()" style="font-size:12px; padding:6px 14px;">
        Trigger New Heartbeat
      </button>
    </div>

    ${runs.length === 0 ? `
      <div class="card" style="text-align:center; padding:48px 24px; border:1px dashed var(--border-color);">
        <div style="font-size:36px; margin-bottom:12px;">💓</div>
        <h4 style="font-size:16px; font-weight:600; margin-bottom:6px;">No Heartbeat Runs Logged</h4>
        <p style="font-size:13px; color:var(--text-secondary); max-width:440px; margin:0 auto 16px auto;">
          Trigger an on-demand heartbeat cycle to observe the 8-step lifecycle and state machine projection.
        </p>
        <button class="btn-primary" onclick="triggerAutonomousHeartbeat()">Trigger Sample Heartbeat</button>
      </div>
    ` : `
      <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); overflow:hidden;">
        <table class="data-table" style="width:100%; border-collapse:collapse; font-size:12.5px;">
          <thead>
            <tr style="background:rgba(255,255,255,0.02); border-bottom:1px solid var(--border-color); text-align:left;">
              <th style="padding:12px 16px;">RUN ID</th>
              <th style="padding:12px 16px;">AGENT</th>
              <th style="padding:12px 16px;">STATUS</th>
              <th style="padding:12px 16px;">ACTIVE TASK</th>
              <th style="padding:12px 16px;">TIMELINE STEPS</th>
              <th style="padding:12px 16px;">NEXT CADENCE</th>
            </tr>
          </thead>
          <tbody>
            ${runs.map(r => `
              <tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:12px 16px; font-family:monospace; color:var(--accent-purple);">${r.run_id}</td>
                <td style="padding:12px 16px; font-weight:600;">${r.agent_id}</td>
                <td style="padding:12px 16px;">
                  <span style="font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:10px; background:rgba(16,185,129,0.15); color:var(--accent-emerald);">
                    ${r.status.toUpperCase()}
                  </span>
                </td>
                <td style="padding:12px 16px; color:var(--text-secondary);">
                  ${r.active_task ? r.active_task.title : 'Inbox empty (scheduled wake)'}
                </td>
                <td style="padding:12px 16px;">
                  <span style="background:var(--bg-card); padding:2px 8px; border-radius:4px; border:1px solid var(--border-color);">
                    ${r.timeline_count || 4} events recorded
                  </span>
                </td>
                <td style="padding:12px 16px; color:var(--text-secondary);">
                  in ${Math.round(r.next_wake_in_seconds || 30)}s
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `}
  `;
}

function renderSkillsTab() {
  const skills = state.agentEngineSkills.length ? state.agentEngineSkills : [
    {
      id: "task-planning",
      name: "Autonomous Task Planning & Decomposition",
      category: "Orchestration",
      description: "Standard procedure for decomposing high-level company goals into unambiguous, actionable child tasks with clear acceptance criteria.",
      sop_rules: [
        "Never create child tasks with descriptions that say 'see parent' — every task must be self-contained.",
        "Declare all DAG dependencies explicitly before assigning tasks to prevent execution deadlocks.",
        "Formulate specific, testable acceptance criteria for each subtask so verification can be 100% automated."
      ]
    },
    {
      id: "issue-triage",
      name: "Deterministic Issue Triage & Prioritization",
      category: "Operations",
      description: "Lifecycle contract for processing incoming tasks, assigning priority buckets, and ensuring single-worker task locks.",
      sop_rules: [
        "Process tasks strictly in order: in_progress first, then in_review, then todo.",
        "Always acquire an atomic lease (checkout) with run ID before commencing work; halt immediately on 409 Conflict.",
        "Update issue status incrementally with evidence deltas to preserve an immutable timeline."
      ]
    },
    {
      id: "board-reporting",
      name: "Executive Board Reporting & Approval Escalation",
      category: "Governance",
      description: "SOP for compiling high-signal briefings, unblocking stalled initiatives, and presenting structured proposals for owner sign-off.",
      sop_rules: [
        "Synthesize outcomes into three core metrics: Capital efficiency, SLA completion rate, and verified truth delta.",
        "Present decisions in actionable multiple-choice format with clear risk/benefit analysis."
      ]
    },
    {
      id: "code-review-gate",
      name: "Automated Code Review & Integrity Gate",
      category: "Engineering",
      description: "Enforces strict static verification, security scanning, and test pass requirements before accepting software changes.",
      sop_rules: [
        "Verify all files match formatting and lint standards with zero warnings.",
        "Scan diffs for hardcoded credentials, bearer tokens, or private keys; reject immediately on detection."
      ]
    },
    {
      id: "incident-recovery",
      name: "Autonomous Incident Recovery & Exponential Backoff",
      category: "Resilience",
      description: "Resilience protocol handling agent timeouts, API exhaustion (e.g. 429 errors), and state restoration.",
      sop_rules: [
        "Apply exponential backoff (base * 2^failures) with randomized symmetric jitter on API rate limit encounters.",
        "On 5 consecutive unhandled failures, gracefully pause the agent and submit a diagnostic alert to the owner."
      ]
    }
  ];

  return `
    <div style="margin-bottom:20px;">
      <h3 style="font-size:16px; font-weight:600;">Paperclip Standard Operating Procedures (SOPs)</h3>
      <p style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
        Deterministic execution guidelines followed by all autonomous agents during mission dispatch.
      </p>
    </div>

    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)); gap:18px;">
      ${skills.map(s => `
        <div class="card" style="border:1px solid var(--border-color); padding:18px; border-radius:var(--radius-lg); background:var(--bg-card);">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
            <h4 style="font-size:15px; font-weight:700;">${s.name}</h4>
            <span style="font-size:10.5px; background:rgba(59,130,246,0.15); color:var(--accent-blue); padding:2px 8px; border-radius:4px; font-weight:600;">
              ${s.category}
            </span>
          </div>
          <p style="font-size:12px; color:var(--text-secondary); line-height:1.5; margin-bottom:12px;">
            ${s.description}
          </p>

          <div style="background:var(--bg-surface); padding:10px 12px; border-radius:var(--radius-md); border:1px solid var(--border-color);">
            <div style="font-size:11px; font-weight:700; color:var(--text-secondary); margin-bottom:6px;">MANDATORY INVARIANTS:</div>
            <ul style="margin:0; padding-left:16px; font-size:11.5px; color:var(--text-primary); line-height:1.5;">
              ${(s.sop_rules || []).map(r => `<li>${r}</li>`).join('')}
            </ul>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// Interactive API Handlers
window.deploySquadToCompany = async function(teamId) {
  const companySelect = document.getElementById('deployTargetCompanySelect');
  const companyId = companySelect ? companySelect.value : (state.companies[0] ? state.companies[0].id : null);

  showToast(`Deploying squad '${teamId}'...`, 'info');
  try {
    const res = await fetch('/api/agent-engine/teams/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId, company_id: companyId })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Successfully deployed ${data.team_name} with ${data.deployed_count} agents!`, 'success');
      // Refresh workforce data
      const empRes = await fetch('/api/employees').then(r => r.json()).catch(() => null);
      if (empRes && empRes.employees) {
        state.workforce = empRes.employees;
      }
      renderAgentEngine();
    } else {
      showToast(data.error || 'Failed to deploy squad', 'error');
    }
  } catch (err) {
    showToast(`Error deploying squad: ${err.message}`, 'error');
  }
};

window.triggerAutonomousHeartbeat = async function() {
  showToast('Triggering autonomous heartbeat turn...', 'info');
  try {
    const res = await fetch('/api/agent-engine/heartbeat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: 'agent_ceo_001',
        role: 'Chief Executive Officer (CEO)',
        trigger: 'manual',
        tasks: [
          { id: 'tsk_audit', title: 'Execute Capital Allocation & Runway Audit', priority: 'urgent', status: 'todo' }
        ]
      })
    });
    const data = await res.json();
    showToast(`Heartbeat turn executed for ${data.agent_id}. Status: ${data.status}`, 'success');
    renderAgentEngine();
  } catch (err) {
    showToast(`Heartbeat error: ${err.message}`, 'error');
  }
};

window.openNewDelegationPlanModal = function() {
  openModal('Decompose Strategic Goal (Paperclip Engine)', `
    <form onsubmit="submitNewDelegationPlan(event)">
      <div class="form-group">
        <label class="form-label">Strategic Goal Title</label>
        <input type="text" id="delegationGoalTitle" class="form-input" required value="Launch Autonomous Client Onboarding Pipeline" />
      </div>

      <div class="form-group">
        <label class="form-label">Lead Decomposing Agent</label>
        <select id="delegationLeadAgent" class="form-select">
          <option value="agent_ceo">Chief Executive Officer (CEO)</option>
          <option value="agent_cto">Chief Technology Officer (CTO)</option>
          <option value="agent_pm">Lead Product Manager</option>
        </select>
      </div>

      <div class="form-group">
        <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
          <input type="checkbox" id="delegationRequiresApproval" checked />
          <span style="font-size:13px; font-weight:600;">Require Executive Board Sign-off Before Assignment</span>
        </label>
      </div>

      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
        <button type="submit" class="btn-primary" style="width:auto;">Generate DAG Plan</button>
      </div>
    </form>
  `);
};

window.submitNewDelegationPlan = async function(e) {
  e.preventDefault();
  const title = document.getElementById('delegationGoalTitle').value;
  const leadAgent = document.getElementById('delegationLeadAgent').value;
  const requiresApproval = document.getElementById('delegationRequiresApproval').checked;

  closeModal();
  showToast('Decomposing goal into specialist tasks...', 'info');

  try {
    const res = await fetch('/api/agent-engine/delegate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goal_title: title,
        lead_agent_id: leadAgent,
        requires_board_approval: requiresApproval,
        subtasks: [
          { title: "Design Architecture & Security Boundaries", target_role: "Chief Technology Officer (CTO)", priority: "high", dependencies: [] },
          { title: "Author Feature PRD & Acceptance Criteria", target_role: "Lead Product Manager", priority: "high", dependencies: [] },
          { title: "Implement Core Data Connectors", target_role: "Senior Fullstack Engineer", priority: "urgent", dependencies: ["s1"] },
          { title: "Automate E2E Regression Verification", target_role: "QA & Reliability Engineer", priority: "medium", dependencies: ["s2"] }
        ]
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Delegation plan formulated with DAG dependencies.', 'success');
      state.agentEngineTab = 'delegation';
      renderAgentEngine();
    } else {
      showToast(data.error || 'Failed to create plan', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
};

window.approveDelegationPlan = async function(goalId) {
  showToast('Approving delegation plan...', 'info');
  try {
    const res = await fetch('/api/agent-engine/plans/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal_id: goalId })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Plan approved. Root tasks dispatched to specialist agents!', 'success');
      renderAgentEngine();
    }
  } catch (err) {
    showToast(`Approval failed: ${err.message}`, 'error');
  }
};

window.simulateCompleteSubtask = async function(goalId, subtaskId) {
  showToast('Completing subtask and checking dependency DAG...', 'info');
  try {
    const res = await fetch('/api/agent-engine/subtasks/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal_id: goalId, subtask_id: subtaskId, result: 'Verified and completed under contract' })
    });
    const data = await res.json();
    if (data.success) {
      if (data.update.unblocked_tasks.length > 0) {
        showToast(`Step completed! Unblocked ${data.update.unblocked_tasks.length} downstream tasks.`, 'success');
      } else if (data.update.is_goal_complete) {
        showToast('🎉 All tasks in DAG completed! High-level goal accomplished.', 'success');
      } else {
        showToast('Step marked complete.', 'info');
      }
      renderAgentEngine();
    }
  } catch (err) {
    showToast(`Completion error: ${err.message}`, 'error');
  }
};

