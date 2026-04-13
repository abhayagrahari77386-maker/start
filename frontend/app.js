/**
 * 🎭 Voice Clone AI — Frontend Application
 * Handles file uploads, chat, and API communication
 */

// ── State ────────────────────────────────────────────────
const API_BASE = window.location.origin;
let sessionId = localStorage.getItem('vc_session_id') || generateId();
let chatMode = 'text'; // 'text' or 'full'
let isSetupComplete = false;
let isProcessing = false;
let voiceFile = null;
let faceFile = null;

localStorage.setItem('vc_session_id', sessionId);

// ── Initialization ───────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    setupUploadZones();
    setupChatInput();
});

// ── Utility ──────────────────────────────────────────────
function generateId() {
    return 'vc_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function getCurrentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── Health Check ─────────────────────────────────────────
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        const data = await res.json();

        document.getElementById('dotGemini').classList.toggle('active', data.apis.gemini);
        document.getElementById('dotElevenlabs').classList.toggle('active', data.apis.elevenlabs);
        document.getElementById('dotSync').classList.toggle('active', data.apis.sync);

        if (!data.apis.gemini || !data.apis.elevenlabs) {
            showToast('⚠️ Some API keys are missing. Check your .env file.', 'warning');
        }
    } catch (e) {
        showToast('❌ Backend server not reachable. Start the server first.', 'error');
    }
}

// ── File Upload Handling ─────────────────────────────────
function setupUploadZones() {
    // Voice upload
    const voiceZone = document.getElementById('voiceUploadZone');
    const voiceInput = document.getElementById('voiceFileInput');

    voiceInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            voiceFile = e.target.files[0];
            voiceZone.classList.add('has-file');
            const nameEl = document.getElementById('voiceFileName');
            nameEl.querySelector('span').textContent = voiceFile.name;
            nameEl.style.display = 'flex';
            document.getElementById('voiceStatus').textContent = '✅ Ready';
            document.getElementById('voiceStatus').className = 'value ready';
            checkSetupReady();
        }
    });

    setupDragDrop(voiceZone, voiceInput);

    // Face upload
    const faceZone = document.getElementById('faceUploadZone');
    const faceInput = document.getElementById('faceFileInput');

    faceInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            faceFile = e.target.files[0];
            faceZone.classList.add('has-file');
            const nameEl = document.getElementById('faceFileName');
            nameEl.querySelector('span').textContent = faceFile.name;
            nameEl.style.display = 'flex';

            // Show face preview
            const reader = new FileReader();
            reader.onload = (ev) => {
                const img = document.getElementById('avatarImage');
                img.src = ev.target.result;
                img.style.display = 'block';
                document.getElementById('avatarPlaceholder').style.display = 'none';
            };
            reader.readAsDataURL(faceFile);

            document.getElementById('faceStatus').textContent = '✅ Ready';
            document.getElementById('faceStatus').className = 'value ready';
            checkSetupReady();
        }
    });

    setupDragDrop(faceZone, faceInput);
}

function setupDragDrop(zone, input) {
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        if (e.dataTransfer.files[0]) {
            // Create a new event to trigger the input
            const dt = new DataTransfer();
            dt.items.add(e.dataTransfer.files[0]);
            input.files = dt.files;
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
}

function checkSetupReady() {
    const btn = document.getElementById('btnSetup');
    btn.disabled = !(voiceFile && faceFile);
}

// ── Setup Avatar ─────────────────────────────────────────
async function setupAvatar() {
    if (!voiceFile || !faceFile) {
        showToast('Please upload both a voice sample and face image.', 'warning');
        return;
    }

    const btn = document.getElementById('btnSetup');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:20px;height:20px;border-width:2px;"></div> Cloning voice...';

    try {
        const formData = new FormData();
        formData.append('voice_sample', voiceFile);
        formData.append('face_image', faceFile);
        formData.append('session_id', sessionId);

        const res = await fetch(`${API_BASE}/api/setup`, {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Setup failed');
        }

        const data = await res.json();

        isSetupComplete = true;
        document.getElementById('cloneStatus').textContent = '✅ Ready';
        document.getElementById('cloneStatus').className = 'value ready';

        // Enable chat
        document.getElementById('chatInput').disabled = false;
        document.getElementById('btnSend').disabled = false;

        // Hide welcome, show ready state
        const welcome = document.getElementById('chatWelcome');
        if (welcome) {
            welcome.innerHTML = `
                <span class="welcome-icon">🎉</span>
                <h3>Avatar Ready!</h3>
                <p>Your voice has been cloned. Start chatting with your AI avatar below!</p>
            `;
        }

        btn.innerHTML = '✅ Avatar Ready!';
        btn.style.background = 'var(--accent-4)';

        showToast('🎉 Voice cloned successfully! Start chatting!', 'success');

    } catch (e) {
        btn.disabled = false;
        btn.innerHTML = '🚀 Clone Voice & Setup Avatar';
        showToast(`❌ ${e.message}`, 'error');
    }
}

// ── Chat Input ───────────────────────────────────────────
function setupChatInput() {
    const input = document.getElementById('chatInput');

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
}

// ── Send Message ─────────────────────────────────────────
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message || isProcessing) return;

    if (!isSetupComplete) {
        showToast('Please set up your avatar first (upload voice + face).', 'warning');
        return;
    }

    isProcessing = true;
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('btnSend').disabled = true;

    // Hide welcome
    const welcome = document.getElementById('chatWelcome');
    if (welcome) welcome.style.display = 'none';

    // Add user message
    addMessage('user', message);

    // Show loading
    const loadingId = addLoadingMessage();

    try {
        const endpoint = chatMode === 'full' ? '/api/chat' : '/api/chat-text';

        const formData = new FormData();
        formData.append('message', message);
        formData.append('session_id', sessionId);

        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Chat failed');
        }

        const data = await res.json();

        // Remove loading
        removeLoadingMessage(loadingId);

        // Add AI response
        addMessage('ai', data.response, {
            emotion: data.emotion,
            cleanText: data.clean_text,
            audioUrl: data.audio_url,
            videoUrl: data.video_url,
            mode: data.mode,
        });

        // If video response, show in avatar frame
        if (data.video_url) {
            const video = document.getElementById('avatarVideo');
            video.src = `${API_BASE}${data.video_url}`;
            video.style.display = 'block';
            video.muted = false;
            video.loop = false;
            video.play();
            document.getElementById('avatarImage').style.display = 'none';
        }

    } catch (e) {
        removeLoadingMessage(loadingId);
        addMessage('ai', `Oops... something went wrong: ${e.message}`, {
            emotion: 'sad',
            cleanText: e.message,
        });
        showToast(`❌ ${e.message}`, 'error');
    }

    isProcessing = false;
    document.getElementById('btnSend').disabled = false;
    document.getElementById('chatInput').focus();
}

// ── Message Rendering ────────────────────────────────────
function addMessage(type, text, options = {}) {
    const container = document.getElementById('chatMessages');

    const msgEl = document.createElement('div');
    msgEl.className = `message ${type}`;

    const avatarIcon = type === 'user' ? '👤' : '🎭';

    let emotionBadge = '';
    if (options.emotion) {
        emotionBadge = `<span class="message-emotion emotion-${options.emotion}">${options.emotion}</span>`;
    }

    let displayText = options.cleanText || text;

    let mediaHtml = '';
    if (options.audioUrl && !options.videoUrl) {
        mediaHtml = `
            <div class="message-media">
                <audio controls src="${API_BASE}${options.audioUrl}"></audio>
            </div>
        `;
    }
    if (options.videoUrl) {
        mediaHtml = `
            <div class="message-media">
                <video controls src="${API_BASE}${options.videoUrl}" autoplay></video>
            </div>
        `;
    }

    msgEl.innerHTML = `
        <div class="message-avatar">${avatarIcon}</div>
        <div class="message-content">
            ${emotionBadge}
            <div class="message-text">${displayText}</div>
            ${mediaHtml}
            <div class="message-time">${getCurrentTime()}</div>
        </div>
    `;

    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;
}

function addLoadingMessage() {
    const container = document.getElementById('chatMessages');
    const id = 'loading-' + Date.now();

    const msgEl = document.createElement('div');
    msgEl.className = 'message ai';
    msgEl.id = id;

    const pipelineHtml = chatMode === 'full' ? `
        <div class="pipeline-steps">
            <div class="pipeline-step active" id="${id}-step1">
                <span class="step-icon">🧠</span> Thinking with Gemini...
            </div>
            <div class="pipeline-step" id="${id}-step2">
                <span class="step-icon">🎤</span> Generating voice...
            </div>
            <div class="pipeline-step" id="${id}-step3">
                <span class="step-icon">👄</span> Creating lip sync...
            </div>
        </div>
    ` : `
        <div class="pipeline-steps">
            <div class="pipeline-step active" id="${id}-step1">
                <span class="step-icon">🧠</span> Thinking...
            </div>
            <div class="pipeline-step" id="${id}-step2">
                <span class="step-icon">🎤</span> Generating voice...
            </div>
        </div>
    `;

    msgEl.innerHTML = `
        <div class="message-avatar">🎭</div>
        <div class="message-content">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
            ${pipelineHtml}
        </div>
    `;

    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;

    return id;
}

function removeLoadingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ── Mode Toggle ──────────────────────────────────────────
function setMode(mode) {
    chatMode = mode;
    document.getElementById('modeText').classList.toggle('active', mode === 'text');
    document.getElementById('modeFull').classList.toggle('active', mode === 'full');

    if (mode === 'full') {
        showToast('🎬 Full Video mode — responses include lip-synced video', 'info');
    } else {
        showToast('💬 Text + Audio mode — faster, cheaper responses', 'info');
    }
}

// ── Clear Session ────────────────────────────────────────
async function clearSession() {
    try {
        const formData = new FormData();
        formData.append('session_id', sessionId);

        await fetch(`${API_BASE}/api/clear`, {
            method: 'POST',
            body: formData,
        });
    } catch (e) {
        // Continue clearing locally even if API fails
    }

    // Reset state
    sessionId = generateId();
    localStorage.setItem('vc_session_id', sessionId);
    isSetupComplete = false;
    voiceFile = null;
    faceFile = null;

    // Reset UI
    document.getElementById('chatMessages').innerHTML = `
        <div class="chat-welcome" id="chatWelcome">
            <span class="welcome-icon">🎭</span>
            <h3>Welcome to Voice Clone AI</h3>
            <p>Upload a voice sample and face image on the left to get started. Then chat with your AI avatar!</p>
        </div>
    `;

    document.getElementById('chatInput').disabled = true;
    document.getElementById('btnSend').disabled = true;
    document.getElementById('btnSetup').disabled = true;
    document.getElementById('btnSetup').innerHTML = '🚀 Clone Voice & Setup Avatar';
    document.getElementById('btnSetup').style.background = '';

    document.getElementById('avatarImage').style.display = 'none';
    document.getElementById('avatarVideo').style.display = 'none';
    document.getElementById('avatarPlaceholder').style.display = 'flex';

    document.getElementById('voiceStatus').textContent = 'Not uploaded';
    document.getElementById('voiceStatus').className = 'value pending';
    document.getElementById('faceStatus').textContent = 'Not uploaded';
    document.getElementById('faceStatus').className = 'value pending';
    document.getElementById('cloneStatus').textContent = 'Not ready';
    document.getElementById('cloneStatus').className = 'value pending';

    document.getElementById('voiceFileName').style.display = 'none';
    document.getElementById('faceFileName').style.display = 'none';
    document.getElementById('voiceUploadZone').classList.remove('has-file');
    document.getElementById('faceUploadZone').classList.remove('has-file');

    // Reset file inputs
    document.getElementById('voiceFileInput').value = '';
    document.getElementById('faceFileInput').value = '';

    showToast('🗑️ Session cleared.', 'info');
}

// ── Toast Notifications ──────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${message}`;

    container.appendChild(toast);

    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
