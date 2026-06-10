<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Kinotop | Shorts — Professional videolar</title>
    <link rel="manifest" href="/static/manifest.json">
    <link rel="apple-touch-icon" href="/static/icons/icon-192.png">
    <meta name="theme-color" content="#667eea">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background: #000;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
            height: 100vh;
            position: fixed;
            width: 100%;
        }

        .shorts-container {
            position: relative;
            width: 100%;
            height: 100vh;
            overflow-y: scroll;
            scroll-snap-type: y mandatory;
            scroll-behavior: smooth;
            background: #000;
            -webkit-overflow-scrolling: touch;
        }
        .shorts-container::-webkit-scrollbar { display: none; }

        .short-video {
            position: relative;
            width: 100%;
            height: 100vh;
            scroll-snap-align: start;
            background: #0a0a0a;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .short-video iframe {
            width: 100%;
            height: 100%;
            border: none;
            position: absolute;
            top: 0;
            left: 0;
            opacity: 0;
            transition: opacity 0.25s ease;
            object-fit: cover;
        }
        .short-video iframe.active {
            opacity: 1;
            z-index: 5;
        }
        .short-video iframe.inactive {
            opacity: 0;
            z-index: 1;
        }

        .short-info {
            position: absolute;
            bottom: 90px;
            left: 20px;
            right: 80px;
            z-index: 15;
            background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 100%);
            padding: 20px 14px 12px 14px;
            border-radius: 20px;
            pointer-events: none;
        }
        .short-title {
            color: white;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 4px;
            text-shadow: 0 1px 4px rgba(0,0,0,0.6);
        }
        .short-desc {
            color: rgba(255,255,255,0.75);
            font-size: 0.8rem;
            line-height: 1.3;
            text-shadow: 0 1px 2px rgba(0,0,0,0.4);
        }

        .overlay-buttons {
            position: absolute;
            right: 14px;
            bottom: 100px;
            z-index: 20;
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .overlay-btn {
            background: rgba(20,20,35,0.7);
            backdrop-filter: blur(12px);
            width: 46px;
            height: 46px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.3rem;
            cursor: pointer;
            transition: transform 0.2s cubic-bezier(0.2, 0.9, 0.4, 1.1), background 0.2s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .overlay-btn:active { transform: scale(0.92); }

        .logo {
            position: fixed;
            top: 18px;
            left: 18px;
            z-index: 50;
            background: rgba(0,0,0,0.55);
            backdrop-filter: blur(12px);
            padding: 8px 20px;
            border-radius: 40px;
            color: white;
            font-weight: 700;
            font-size: 1rem;
            border: 0.5px solid rgba(255,255,255,0.2);
        }
        .logo span {
            background: linear-gradient(135deg, #fff, #b794f4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .admin-btn {
            position: fixed;
            top: 18px;
            right: 80px;
            z-index: 50;
            background: rgba(0,0,0,0.55);
            backdrop-filter: blur(12px);
            width: 42px;
            height: 42px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            text-decoration: none;
            font-size: 1.1rem;
            border: 0.5px solid rgba(255,255,255,0.2);
        }

        /* Telegram seriallar tugmasi */
        .telegram-series-btn {
            position: fixed;
            top: 18px;
            right: 18px;
            z-index: 51;
            background: linear-gradient(135deg, #1f8a4c, #29b364);
            backdrop-filter: blur(8px);
            padding: 8px 18px;
            border-radius: 40px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: white;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            border: none;
            box-shadow: 0 4px 14px rgba(0,0,0,0.3);
            transition: transform 0.2s ease;
        }
        .telegram-series-btn:active { transform: scale(0.95); }
        .telegram-series-btn i { font-size: 1.2rem; }

        /* DINAMIK TUGMA - admin panel orqali boshqariladi */
        .dynamic-action-btn {
            position: fixed;
            top: 76px;
            right: 18px;
            z-index: 51;
            background: linear-gradient(135deg, #ff8c42, #ff6a1a);
            backdrop-filter: blur(8px);
            padding: 8px 18px;
            border-radius: 40px;
            display: none;
            align-items: center;
            gap: 8px;
            color: white;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            border: none;
            box-shadow: 0 4px 14px rgba(0,0,0,0.3);
            transition: transform 0.2s ease;
        }
        .dynamic-action-btn:active { transform: scale(0.95); }
        .dynamic-action-btn i { font-size: 1.1rem; }

        .code-btn {
            position: fixed;
            bottom: 24px;
            left: 20px;
            right: 20px;
            background: linear-gradient(135deg, rgba(102,126,234,0.96), rgba(118,75,162,0.96));
            backdrop-filter: blur(24px);
            border-radius: 70px;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            z-index: 100;
            border: 1px solid rgba(255,255,255,0.25);
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        }
        .code-btn:active { transform: scale(0.97); }
        .code-btn-left { display: flex; align-items: center; gap: 14px; }
        .code-btn-icon {
            width: 48px;
            height: 48px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
        }
        .code-btn-text h4 { color: white; font-size: 0.95rem; font-weight: 700; }
        .code-btn-text p { color: rgba(255,255,255,0.75); font-size: 0.7rem; }

        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.94);
            backdrop-filter: blur(20px);
            z-index: 200;
            display: none;
            align-items: center;
            justify-content: center;
        }
        .modal-overlay.show { display: flex; }
        .modal-container {
            width: 90%;
            max-width: 400px;
            background: rgba(20,20,35,0.9);
            backdrop-filter: blur(20px);
            border-radius: 48px;
            overflow: hidden;
            border: 1px solid rgba(102,126,234,0.5);
        }
        .modal-header {
            padding: 28px 20px;
            text-align: center;
            background: linear-gradient(135deg, #667eea, #764ba2);
        }
        .modal-header h3 { color: white; font-size: 1.5rem; margin-bottom: 6px; }
        .modal-header p { color: rgba(255,255,255,0.85); font-size: 0.85rem; }

        .code-screen {
            background: rgba(0,0,0,0.6);
            margin: 28px 24px;
            padding: 22px 16px;
            border-radius: 60px;
            text-align: center;
            border: 1.5px solid rgba(102,126,234,0.7);
        }
        .code-digits {
            font-size: 2.8rem;
            font-weight: 800;
            letter-spacing: 18px;
            color: white;
            font-family: monospace;
        }
        .numpad {
            padding: 0 24px 20px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
        }
        .numpad-btn {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 70px;
            padding: 18px;
            font-size: 1.7rem;
            font-weight: 700;
            color: white;
            text-align: center;
            cursor: pointer;
        }
        .numpad-btn:active { background: #667eea; transform: scale(0.96); }
        .action-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            padding: 0 24px 20px;
        }
        .action-clear, .action-delete {
            border: none;
            border-radius: 60px;
            padding: 14px;
            font-weight: 600;
            cursor: pointer;
        }
        .action-clear { background: #dc3545cc; color: white; }
        .action-delete { background: #ffc107cc; color: #1e1e2a; }
        .watch-submit {
            width: calc(100% - 48px);
            margin: 0 24px 28px;
            padding: 16px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 80px;
            color: white;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
        }
        .modal-close {
            position: absolute;
            top: 24px;
            right: 24px;
            background: rgba(255,255,255,0.2);
            width: 44px;
            height: 44px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.3rem;
            cursor: pointer;
        }

        .film-loading {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.96);
            z-index: 300;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 20px;
            visibility: hidden;
            opacity: 0;
            transition: 0.25s;
        }
        .film-loading.show { visibility: visible; opacity: 1; }
        .film-loading-spinner {
            width: 56px;
            height: 56px;
            border: 3px solid rgba(102,126,234,0.3);
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .scroll-instruction {
            position: absolute;
            bottom: 150px;
            left: 0;
            right: 0;
            text-align: center;
            z-index: 55;
            pointer-events: none;
            transition: opacity 0.5s ease;
            opacity: 1;
        }
        .scroll-instruction.fade-out { opacity: 0; visibility: hidden; }
        .scroll-arrow {
            width: 32px;
            height: 32px;
            border-left: 2.5px solid rgba(255,255,255,0.8);
            border-bottom: 2.5px solid rgba(255,255,255,0.8);
            transform: rotate(-45deg);
            margin: 0 auto 12px;
            animation: arrowAnim 1.6s infinite;
        }
        .scroll-text {
            color: rgba(255,255,255,0.9);
            font-size: 0.85rem;
            background: rgba(0,0,0,0.3);
            padding: 6px 16px;
            border-radius: 40px;
            display: inline-block;
        }
        @keyframes arrowAnim {
            0%, 100% { transform: rotate(-45deg) translate(0,0); opacity: 0.4; }
            50% { transform: rotate(-45deg) translate(8px,8px); opacity: 1; }
        }

        @media (max-width: 480px) {
            .code-digits { font-size: 2rem; letter-spacing: 12px; }
            .numpad-btn { padding: 14px; font-size: 1.4rem; }
            .telegram-series-btn, .dynamic-action-btn { padding: 5px 12px; font-size: 0.7rem; }
            .dynamic-action-btn { top: 68px; }
        }
    </style>
</head>
<body>

<div class="scroll-instruction" id="scrollInstruction">
    <div class="scroll-arrow"></div>
    <div class="scroll-text">👆 Yuqoriga suring | Shortslar avtomatik ijro etiladi</div>
</div>

<div class="logo"><span>🎬 KINOTOP</span></div>
<a href="/admin" class="admin-btn">🔐</a>

<!-- Seriallar tugmasi (Telegram) -->
<div class="telegram-series-btn" id="telegramSeriesBtn">
    <i class="fab fa-telegram-plane"></i>
    <span>Seriallar</span>
</div>

<!-- Dinamik tugma - admin panel orqali boshqariladi -->
<div class="dynamic-action-btn" id="dynamicActionBtn">
    <i class="fas fa-ticket-alt"></i>
    <span id="dynamicBtnText">Top Kino</span>
</div>

<div class="shorts-container" id="shortsContainer"></div>

<div class="code-btn" id="openModalBtn">
    <div class="code-btn-left">
        <div class="code-btn-icon"><i class="fas fa-qrcode"></i></div>
        <div class="code-btn-text">
            <h4>Maxfiy kod orqali kino</h4>
            <p>4 xonali kod bilan premium filmlar</p>
        </div>
    </div>
    <div class="code-btn-arrow"><i class="fas fa-chevron-up"></i></div>
</div>

<div class="modal-overlay" id="modalOverlay">
    <div class="modal-close" id="closeModalBtn"><i class="fas fa-times"></i></div>
    <div class="modal-container">
        <div class="modal-header">
            <h3>🎟️ Film kod paneli</h3>
            <p>4 xonali kodni kiriting va darhol tomosha qiling</p>
        </div>
        <div class="code-screen">
            <div class="code-digits" id="codeDisplay">____</div>
            <div class="code-hint" style="color:#aaa; font-size:0.7rem; margin-top:10px;">Raqamlarni kiriting</div>
        </div>
        <div class="numpad">
            <div class="numpad-btn" data-value="1">1</div><div class="numpad-btn" data-value="2">2</div><div class="numpad-btn" data-value="3">3</div>
            <div class="numpad-btn" data-value="4">4</div><div class="numpad-btn" data-value="5">5</div><div class="numpad-btn" data-value="6">6</div>
            <div class="numpad-btn" data-value="7">7</div><div class="numpad-btn" data-value="8">8</div><div class="numpad-btn" data-value="9">9</div>
            <div class="numpad-btn" data-value=""></div><div class="numpad-btn" data-value="0">0</div><div class="numpad-btn" data-value=""></div>
        </div>
        <div class="action-buttons">
            <div class="action-clear" id="clearBtn">Tozalash</div>
            <div class="action-delete" id="backspaceBtn"><i class="fas fa-backspace"></i> O'chir</div>
        </div>
        <button class="watch-submit" id="watchSubmitBtn"><i class="fas fa-play-circle"></i> Tomosha qilish</button>
    </div>
</div>

<div class="film-loading" id="filmLoading">
    <div class="film-loading-spinner"></div>
    <div class="film-loading-text">🎞️ Kino tayyorlanmoqda...</div>
</div>

<script>
    const originalShorts = {{ shorts | tojson | safe }};
    
    function shuffleArray(arr) {
        for (let i = arr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
        return arr;
    }
    
    let shorts = shuffleArray([...originalShorts]);
    const shortsContainer = document.getElementById('shortsContainer');
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function renderShorts() {
        shortsContainer.innerHTML = '';
        shorts.forEach((short, idx) => {
            const div = document.createElement('div');
            div.className = 'short-video';
            div.setAttribute('data-id', short.id);
            div.setAttribute('data-index', idx);
            div.innerHTML = `
                <iframe data-src="${short.embed_url}" src="about:blank" allow="autoplay; encrypted-media; fullscreen" allowfullscreen></iframe>
                <div class="short-info">
                    <div class="short-title">${escapeHtml(short.sarlavha)}</div>
                    <div class="short-desc">${escapeHtml(short.tafsilot || '⚡ Trending short')}</div>
                </div>
                <div class="overlay-buttons">
                    <div class="overlay-btn sound-btn" data-id="${short.id}">🔇</div>
                    <div class="overlay-btn share-btn"><i class="fa-regular fa-share-from-square"></i></div>
                </div>
            `;
            shortsContainer.appendChild(div);
        });
    }
    
    let allVideos = [];
    let currentIndex = -1;
    let currentIframe = null;
    let isVideoLoading = false;
    
    function getAllVideos() {
        allVideos = Array.from(document.querySelectorAll('.short-video'));
    }
    
    function playVideoAt(index) {
        if (index === currentIndex || isVideoLoading) return;
        if (index < 0 || index >= allVideos.length) return;
        isVideoLoading = true;
        
        allVideos.forEach(item => {
            const iframe = item.querySelector("iframe");
            if (iframe) {
                iframe.src = "about:blank";
                iframe.classList.remove("active");
                iframe.classList.add("inactive");
            }
        });
    
        const video = allVideos[index];
        const iframe = video.querySelector("iframe");
        if (!iframe) { isVideoLoading = false; return; }
    
        let src = iframe.dataset.src;
        if (!src.includes("autoplay=1")) src += (src.includes("?") ? "&" : "?") + "autoplay=1";
        if (!src.includes("mute=0")) src += "&mute=0";
        
        document.querySelectorAll('.sound-btn').forEach(btn => { btn.innerHTML = '🔇'; });
        const soundBtn = video.querySelector('.sound-btn');
        if (soundBtn) soundBtn.innerHTML = '🔊';
        
        setTimeout(() => {
            iframe.src = src;
            iframe.classList.remove("inactive");
            iframe.classList.add("active");
            currentIframe = iframe;
            currentIndex = index;
            isVideoLoading = false;
        }, 50);
    }
    
    function toggleSound(btn) {
        const parent = btn.closest('.short-video');
        if (!parent) return;
        const idx = parseInt(parent.getAttribute('data-index'));
        if (idx === currentIndex && currentIframe && currentIframe.contentWindow) {
            if (btn.innerHTML === '🔊') {
                btn.innerHTML = '🔇';
                currentIframe.contentWindow.postMessage('{"event":"command","func":"mute","args":""}', '*');
            } else {
                btn.innerHTML = '🔊';
                currentIframe.contentWindow.postMessage('{"event":"command","func":"unMute","args":""}', '*');
            }
        } else {
            playVideoAt(idx);
        }
    }
    
    function shareToTelegram(videoTitle) {
        const botUsername = "Kodlikino_topbot";
        const message = `🎬 KinoTop🤩 t.me/${botUsername} da eng sara filmlarni tomosha qiling! 🔥 ${videoTitle}`;
        window.open(`https://t.me/share/url?url=https://t.me/${botUsername}&text=${encodeURIComponent(message)}`, '_blank');
    }
    
    function openTelegramChannel() {
        window.open('https://t.me/Kodlikino_topbot', '_blank');
    }
    
    // Dinamik tugmani sozlash (admin panel orqali)
    function initDynamicButton() {
        const dynamicBtn = document.getElementById('dynamicActionBtn');
        const btnTextSpan = document.getElementById('dynamicBtnText');
        
        // Serverdan tugma sozlamalarini olish
        fetch('/api/action-button')
            .then(res => res.json())
            .then(data => {
                if (data && data.enabled === true) {
                    btnTextSpan.innerText = data.text || "Top Kino";
                    dynamicBtn.style.display = 'flex';
                    const url = data.url || "https://t.me/Kodlikino_topbot";
                    dynamicBtn.onclick = () => { window.open(url, '_blank'); };
                } else {
                    // default: tugma ko'rinsin va vaqtinchalik "Top Kino" bilan ishlasin
                    btnTextSpan.innerText = "Top Kino";
                    dynamicBtn.style.display = 'flex';
                    dynamicBtn.onclick = () => { window.open('https://t.me/Kodlikino_topbot', '_blank'); };
                }
            })
            .catch(() => {
                // fallback: tugmani default holatda ko'rsatish
                btnTextSpan.innerText = "Top Kino";
                dynamicBtn.style.display = 'flex';
                dynamicBtn.onclick = () => { window.open('https://t.me/Kodlikino_topbot', '_blank'); };
            });
    }
    
    function attachEventListeners() {
        document.querySelectorAll('.sound-btn').forEach(btn => {
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            newBtn.addEventListener('click', (e) => { e.stopPropagation(); toggleSound(newBtn); });
        });
        
        document.querySelectorAll('.share-btn').forEach(btn => {
            const newShare = btn.cloneNode(true);
            btn.parentNode.replaceChild(newShare, btn);
            newShare.addEventListener('click', (e) => {
                e.stopPropagation();
                const parentVideo = newShare.closest('.short-video');
                const titleElem = parentVideo?.querySelector('.short-title');
                const videoTitle = titleElem ? titleElem.innerText : "KinoTop short";
                shareToTelegram(videoTitle);
            });
        });
    }
    
    function initFirstVideo() {
        if (allVideos.length > 0) setTimeout(() => playVideoAt(0), 50);
    }
    
    function getCurrentVisibleIndex() {
        const scrollTop = shortsContainer.scrollTop;
        const itemHeight = window.innerHeight;
        return Math.min(Math.max(0, Math.round(scrollTop / itemHeight)), allVideos.length - 1);
    }
    
    let scrollTimer = null;
    function onScrollHandler() {
        if (scrollTimer) clearTimeout(scrollTimer);
        scrollTimer = setTimeout(() => {
            const newIndex = getCurrentVisibleIndex();
            if (newIndex !== currentIndex && newIndex >= 0 && newIndex < allVideos.length) {
                playVideoAt(newIndex);
            }
        }, 70);
    }
    
    // KOD MODAL
    let currentCode = '';
    const maxCodeLength = 4;
    const codeDisplay = document.getElementById('codeDisplay');
    const modalOverlay = document.getElementById('modalOverlay');
    const filmLoading = document.getElementById('filmLoading');
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const clearBtn = document.getElementById('clearBtn');
    const backspaceBtn = document.getElementById('backspaceBtn');
    const watchSubmitBtn = document.getElementById('watchSubmitBtn');
    
    function updateDisplay() { 
        codeDisplay.textContent = currentCode.padEnd(maxCodeLength, '_'); 
        if (currentCode.length === maxCodeLength) submitCode(); 
    }
    function addDigit(d) { if (currentCode.length < maxCodeLength) { currentCode += d; updateDisplay(); } }
    function clearCode() { currentCode = ''; updateDisplay(); }
    function backspaceFunc() { currentCode = currentCode.slice(0, -1); updateDisplay(); }
    
    function submitCode() {
        if (currentCode.length !== maxCodeLength) { alert('4 xonali kodni kiriting!'); return; }
        filmLoading.classList.add('show');
        fetch(`/api/check/${currentCode}`)
            .then(res => res.json())
            .then(data => {
                if (data.exists) window.location.href = `/film/${currentCode}`;
                else throw new Error('NOT_FOUND');
            })
            .catch(() => {
                filmLoading.classList.remove('show');
                alert(`❌ "${currentCode}" kodli film topilmadi!`);
                clearCode();
            });
    }
    
    document.querySelectorAll('.numpad-btn').forEach(btn => {
        const val = btn.getAttribute('data-value');
        if (val && val.trim() !== '') btn.addEventListener('click', () => addDigit(val));
    });
    clearBtn.addEventListener('click', clearCode);
    backspaceBtn.addEventListener('click', backspaceFunc);
    watchSubmitBtn.addEventListener('click', submitCode);
    openModalBtn.addEventListener('click', () => { modalOverlay.classList.add('show'); clearCode(); });
    closeModalBtn.addEventListener('click', () => { modalOverlay.classList.remove('show'); clearCode(); });
    modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) modalOverlay.classList.remove('show'); });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modalOverlay.classList.contains('show')) modalOverlay.classList.remove('show');
        if (modalOverlay.classList.contains('show') && /^[0-9]$/.test(e.key)) addDigit(e.key);
        if (modalOverlay.classList.contains('show') && e.key === 'Enter') submitCode();
    });
    
    document.getElementById('telegramSeriesBtn').addEventListener('click', openTelegramChannel);
    
    window.addEventListener("beforeunload", () => { document.querySelectorAll("iframe").forEach(i => i.src = "about:blank"); });
    document.addEventListener("visibilitychange", () => { if (document.hidden) document.querySelectorAll("iframe").forEach(i => i.src = "about:blank"); });
    
    function initApp() {
        renderShorts();
        getAllVideos();
        attachEventListeners();
        shortsContainer.addEventListener('scroll', onScrollHandler);
        
        let touchStartY = 0, touchEndY = 0, touchTimer = null;
        shortsContainer.addEventListener('touchstart', (e) => { touchStartY = e.touches[0].clientY; });
        shortsContainer.addEventListener('touchend', () => {
            const diff = touchStartY - touchEndY;
            if (Math.abs(diff) > 40) {
                if (touchTimer) clearTimeout(touchTimer);
                touchTimer = setTimeout(() => {
                    const newIndex = getCurrentVisibleIndex();
                    if (newIndex !== currentIndex) playVideoAt(newIndex);
                }, 70);
            }
        });
        shortsContainer.addEventListener('touchmove', (e) => { touchEndY = e.touches[0].clientY; });
        
        setTimeout(() => {
            const instr = document.getElementById('scrollInstruction');
            if (instr) instr.classList.add('fade-out');
        }, 2500);
        
        initFirstVideo();
        initDynamicButton(); // Dinamik tugmani yuklash
    }
    
    initApp();
</script>
</body>
</html>
