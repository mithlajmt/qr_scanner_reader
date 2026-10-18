/**
 * Robuverse Robot QR Scanner - Client Logic & WebSocket Hub
 */

// State
let ws = null;
let soundEnabled = true;
let scanCount = 0;
let historyItems = [];
let audioCtx = null;

// DOM Elements
const connectionStatus = document.getElementById('connectionStatus');
const statusText = document.getElementById('statusText');
const soundToggle = document.getElementById('soundToggle');
const soundLabel = document.getElementById('soundLabel');

const emptyState = document.getElementById('emptyState');
const activeScanContainer = document.getElementById('activeScanContainer');
const latestValue = document.getElementById('latestValue');
const latestTime = document.getElementById('latestTime');
const latestSource = document.getElementById('latestSource');
const copyBtn = document.getElementById('copyBtn');
const copyBtnText = document.getElementById('copyBtnText');

const totalScansCount = document.getElementById('totalScansCount');
const ipAddressDisplay = document.getElementById('ipAddressDisplay');
const networkUrlText = document.getElementById('networkUrlText');
const hardwareStatus = document.getElementById('hardwareStatus');

const simForm = document.getElementById('simForm');
const simInput = document.getElementById('simInput');
const historyList = document.getElementById('historyList');
const historyBadgeCount = document.getElementById('historyBadgeCount');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

// Initialize Web Audio Synth for Sci-Fi scan chime
function playScanChime() {
    if (!soundEnabled) return;
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        const now = audioCtx.currentTime;
        
        // Tone 1: High note
        const osc1 = audioCtx.createOscillator();
        const gain1 = audioCtx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(880, now); // A5
        osc1.frequency.exponentialRampToValueAtTime(1320, now + 0.12);
        gain1.gain.setValueAtTime(0.25, now);
        gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.18);
        osc1.connect(gain1);
        gain1.connect(audioCtx.destination);
        osc1.start(now);
        osc1.stop(now + 0.18);

        // Tone 2: Confirmation chime
        const osc2 = audioCtx.createOscillator();
        const gain2 = audioCtx.createGain();
        osc2.type = 'triangle';
        osc2.frequency.setValueAtTime(1760, now + 0.08); // A6
        gain2.gain.setValueAtTime(0.2, now + 0.08);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
        osc2.connect(gain2);
        gain2.connect(audioCtx.destination);
        osc2.start(now + 0.08);
        osc2.stop(now + 0.28);
    } catch (e) {
        console.warn("Audio chime error:", e);
    }
}

// Sound toggle handler
soundToggle.addEventListener('click', () => {
    soundEnabled = !soundEnabled;
    soundLabel.textContent = `Sound: ${soundEnabled ? 'ON' : 'OFF'}`;
    soundToggle.classList.toggle('muted', !soundEnabled);
    if (soundEnabled) {
        playScanChime(); // quick test beep
    }
});

// Copy to clipboard
copyBtn.addEventListener('click', async () => {
    const text = latestValue.textContent;
    if (!text || text === '---') return;
    try {
        await navigator.clipboard.writeText(text);
        copyBtn.classList.add('copied');
        copyBtnText.textContent = 'Copied!';
        setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyBtnText.textContent = 'Copy Value';
        }, 2000);
    } catch (err) {
        console.error('Clipboard copy failed:', err);
    }
});

// Render history item
function renderHistoryItem(item, prepend = true) {
    const el = document.createElement('div');
    el.className = 'history-item';
    el.innerHTML = `
        <div class="history-item-left">
            <span class="history-val" title="${escapeHtml(item.value)}">${escapeHtml(item.value)}</span>
            <span class="history-time">${escapeHtml(item.timestamp || item.time_short)}</span>
        </div>
        <span class="history-source-badge">${escapeHtml(item.source || 'Scan')}</span>
    `;

    if (prepend) {
        historyList.prepend(el);
    } else {
        historyList.appendChild(el);
    }
}

function updateHistoryUI() {
    historyBadgeCount.textContent = historyItems.length;
    if (historyItems.length === 0) {
        historyList.innerHTML = '<div class="history-empty">No scans recorded yet.</div>';
    }
}

// Clear history
clearHistoryBtn.addEventListener('click', () => {
    historyItems = [];
    updateHistoryUI();
});

// Handle incoming scan
function handleNewScan(scanItem) {
    playScanChime();

    // Show in Hero section
    emptyState.classList.add('hidden');
    activeScanContainer.classList.remove('hidden');

    latestValue.textContent = scanItem.value;
    latestTime.textContent = `Scanned at ${scanItem.time_short || scanItem.timestamp}`;
    latestSource.textContent = scanItem.source || 'USB SCANNER';

    // Trigger re-animation
    activeScanContainer.style.animation = 'none';
    void activeScanContainer.offsetWidth; // trigger reflow
    activeScanContainer.style.animation = 'scanPop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';

    // Add to history
    if (historyItems.length === 0) {
        historyList.innerHTML = '';
    }
    historyItems.unshift(scanItem);
    renderHistoryItem(scanItem, true);
    historyBadgeCount.textContent = historyItems.length;

    scanCount++;
    totalScansCount.textContent = scanCount;
}

// Manual simulation form
simForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const val = simInput.value.trim();
    if (!val) return;

    try {
        simInput.disabled = true;
        const res = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value: val, source: 'Manual Web Test' })
        });
        if (res.ok) {
            simInput.value = '';
        }
    } catch (err) {
        console.error('Failed to simulate scan:', err);
    } finally {
        simInput.disabled = false;
        simInput.focus();
    }
});

// WebSocket Connection Management
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        connectionStatus.classList.remove('disconnected');
        statusText.textContent = 'ONLINE';
        hardwareStatus.textContent = 'Active';
        hardwareStatus.className = 'stat-value active-link';
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'INIT_STATE') {
                if (msg.local_ip) {
                    const fullUrl = `http://${msg.local_ip}:${msg.port || 8000}`;
                    ipAddressDisplay.textContent = `${msg.local_ip}:${msg.port || 8000}`;
                    networkUrlText.textContent = fullUrl;
                }
                if (msg.total_scans !== undefined) {
                    scanCount = msg.total_scans;
                    totalScansCount.textContent = scanCount;
                }
                if (msg.history && msg.history.length > 0) {
                    historyItems = msg.history;
                    historyList.innerHTML = '';
                    historyItems.forEach(item => renderHistoryItem(item, false));
                    updateHistoryUI();
                    
                    // Show most recent in hero
                    handleNewScan(historyItems[0]);
                }
            } else if (msg.type === 'NEW_SCAN') {
                handleNewScan(msg.data);
            }
        } catch (e) {
            console.error('Error parsing WS message:', e);
        }
    };

    ws.onclose = () => {
        connectionStatus.classList.add('disconnected');
        statusText.textContent = 'OFFLINE (RETRYING)';
        hardwareStatus.textContent = 'Disconnected';
        hardwareStatus.className = 'stat-value';
        setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Start
connectWebSocket();
