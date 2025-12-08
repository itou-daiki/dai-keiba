// ==================== グローバル変数 ====================
let currentBetType = 'win'; // 現在選択中の馬券種類
let horses = []; // 馬のデータ {number, odds}
let raceInfo = {
    type: null,
    venue: null,
    date: null,
    number: null,
};

// CORSプロキシ設定
const CORS_PROXIES = [
    'https://api.allorigins.win/raw?url=',
    'https://corsproxy.io/?',
];

// 競馬場データ
const RACECOURSES = {
    central: { '01': '札幌', '02': '函館', '03': '福島', '04': '新潟', '05': '東京', '06': '中山', '07': '中京', '08': '京都', '09': '阪神', '10': '小倉' },
    local: { '30': '門別', '35': '盛岡', '36': '水沢', '42': '浦和', '43': '船橋', '44': '大井', '45': '川崎', '46': '金沢', '47': '笠松', '48': '名古屋', '50': '園田', '51': '姫路', '54': '高知', '55': '佐賀' }
};

// ==================== 初期化 ====================
document.addEventListener('DOMContentLoaded', initializeApp);

function initializeApp() {
    setupEventListeners();
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('race-date').value = today;
    raceInfo.date = today;
    generateRaceNumberButtons();
}

// ==================== イベントリスナー設定 ====================
function setupEventListeners() {
    // 競馬場タイプ選択
    document.getElementById('race-type-btns').addEventListener('click', handleRaceTypeSelection);
    
    // 日付選択
    document.getElementById('race-date').addEventListener('change', (e) => {
        raceInfo.date = e.target.value;
        showRaceNumberGroup();
    });

    // オッズ取得ボタン
    document.getElementById('fetch-odds-btn').addEventListener('click', fetchOddsFromSelection);

    // 馬券種類選択
    document.getElementById('bet-type-section').addEventListener('click', handleBetTypeSelection);

    // 計算ボタン
    document.getElementById('calculate-btn').addEventListener('click', calculatePayout);

    // リセットボタン
    document.getElementById('reset-btn').addEventListener('click', resetForm);
}

// ==================== UI生成 ====================
function generateRaceVenueButtons(raceType) {
    const container = document.getElementById('venue-btns');
    container.innerHTML = '';
    const courses = RACECOURSES[raceType];
    for (const [code, name] of Object.entries(courses)) {
        const button = document.createElement('button');
        button.className = 'btn-group-item';
        button.dataset.value = code;
        button.textContent = name;
        container.appendChild(button);
    }
    container.addEventListener('click', handleVenueSelection);
    document.getElementById('venue-group').style.display = 'block';
}

function generateRaceNumberButtons() {
    const container = document.getElementById('race-number-btns');
    container.innerHTML = '';
    for (let i = 1; i <= 12; i++) {
        const button = document.createElement('button');
        button.className = 'btn-group-item';
        button.dataset.value = i.toString().padStart(2, '0');
        button.textContent = `${i}R`;
        container.appendChild(button);
    }
    container.addEventListener('click', handleRaceNumberSelection);
}


// ==================== UI操作ハンドラ ====================
function handleRaceTypeSelection(e) {
    if (!e.target.matches('.btn-group-item')) return;
    const selectedBtn = e.target;
    raceInfo.type = selectedBtn.dataset.value;
    
    // UI更新
    updateButtonGroup(selectedBtn);
    generateRaceVenueButtons(raceInfo.type);
    
    // 非表示リセット
    ['date-group', 'race-number-group', 'fetch-btn-group'].forEach(id => {
        document.getElementById(id).style.display = 'none';
    });
    raceInfo.venue = null;
    raceInfo.number = null;
}

function handleVenueSelection(e) {
    if (!e.target.matches('.btn-group-item')) return;
    const selectedBtn = e.target;
    raceInfo.venue = selectedBtn.dataset.value;
    updateButtonGroup(selectedBtn);
    document.getElementById('date-group').style.display = 'block';
    if(raceInfo.date) showRaceNumberGroup();
}

function handleRaceNumberSelection(e) {
    if (!e.target.matches('.btn-group-item')) return;
    const selectedBtn = e.target;
    raceInfo.number = selectedBtn.dataset.value;
    updateButtonGroup(selectedBtn);
    document.getElementById('fetch-btn-group').style.display = 'block';
}

function showRaceNumberGroup() {
     document.getElementById('race-number-group').style.display = 'block';
}

function handleBetTypeSelection(e) {
    if (!e.target.matches('.bet-type-btn')) return;
    currentBetType = e.target.dataset.type;
    updateButtonGroup(e.target, '.bet-type-btn');
    updateSelectionArea();
}

function updateButtonGroup(selectedBtn, itemSelector = '.btn-group-item') {
    const parent = selectedBtn.parentElement;
    parent.querySelectorAll(itemSelector).forEach(btn => btn.classList.remove('active'));
    selectedBtn.classList.add('active');
}


// ==================== データ取得・表示 ====================
async function fetchOddsFromSelection() {
    const raceId = generateRaceId();
    if (!raceId) {
        showStatus('すべての項目を選択してください', 'error');
        return;
    }

    const url = `https://race.netkeiba.com/race/shutuba.html?race_id=${raceId}`;
    setLoading(true);
    showStatus(`レースID: ${raceId} のオッズを取得中...`, 'info');

    try {
        const oddsData = await fetchNetkeiba(url);
        if (oddsData && oddsData.horses && oddsData.horses.length > 0) {
            horses = oddsData.horses;
            displayOdds(horses);
            showStatus(`✓ ${horses.length}頭のオッズデータを取得しました！`, 'success');
            document.getElementById('bet-type-section').style.display = 'block';
            document.getElementById('odds-display-section').style.display = 'block';
            document.getElementById('purchase-section').style.display = 'block';
            updateSelectionArea();
        } else {
            throw new Error('オッズデータが見つかりませんでした。');
        }
    } catch (error) {
        showStatus(`✗ エラー: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

function displayOdds(horsesData) {
    const container = document.getElementById('odds-display-area');
    container.innerHTML = '';
    const table = document.createElement('table');
    table.className = 'odds-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>馬番</th>
                <th>単勝オッズ</th>
            </tr>
        </thead>
        <tbody>
            ${horsesData.map(h => `
                <tr>
                    <td>${h.number}</td>
                    <td>${h.odds.toFixed(1)}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    container.appendChild(table);
}

// ==================== 払戻金計算ロジック ====================
function calculatePayout() {
    const betAmount = parseInt(document.getElementById('bet-amount').value) || 100;
    const selectedHorses = getSelectedHorses();

    if (!validateInput(selectedHorses)) return;

    let payout = 0;
    let explanation = '';
    
    switch (currentBetType) {
        case 'win':
        case 'place':
            payout = calculateSinglePayout(selectedHorses[0], betAmount);
            explanation = `${selectedHorses[0]}番`;
            break;

        case 'quinella':
        case 'exacta':
        case 'wide':
            payout = calculateDoublePayout(selectedHorses, betAmount);
            explanation = `${selectedHorses[0]}番 - ${selectedHorses[1]}番`;
            break;

        case 'trio':
        case 'trifecta':
            payout = calculateTriplePayout(selectedHorses, betAmount);
            explanation = `${selectedHorses[0]}番 - ${selectedHorses[1]}番 - ${selectedHorses[2]}番`;
            break;
    }
    const betTypeName = getBetTypeName(currentBetType);

    displayResult(payout, betAmount, explanation, betTypeName);
}

function getSelectedHorses() {
    const selected = new Set();
    const grids = document.querySelectorAll('.horse-select-grid');
    
    grids.forEach(grid => {
        const selectedButtons = grid.querySelectorAll('.horse-select-btn.selected');
        selectedButtons.forEach(btn => {
            selected.add(parseInt(btn.dataset.horse));
        });
    });

    return Array.from(selected).sort((a,b) => a - b);
}

function validateInput(selectedHorses) {
    const betAmount = parseInt(document.getElementById('bet-amount').value);

    if (!betAmount || betAmount < 100) {
        alert('購入金額を100円以上で入力してください');
        return false;
    }

    if (betAmount % 100 !== 0) {
        alert('購入金額は100円単位で入力してください');
        return false;
    }

    let requiredCount = 1;
    switch (currentBetType) {
        case 'quinella':
        case 'exacta':
        case 'wide':
            requiredCount = 2;
            break;
        case 'trio':
        case 'trifecta':
            requiredCount = 3;
            break;
    }

    if (selectedHorses.length < requiredCount) {
        alert(`${requiredCount}頭の馬を選択してください`);
        return false;
    }
    
    const uniqueHorses = new Set(selectedHorses);
    if (uniqueHorses.size !== selectedHorses.length) {
        alert('同じ馬を複数選択することはできません');
        return false;
    }

    return true;
}


// ==================== 払戻金計算 ====================
function calculateSinglePayout(horseNumber, betAmount) {
    const horse = horses.find(h => h.number === horseNumber);
    if (!horse) return 0;

    const payout = betAmount * horse.odds;
    return Math.floor(payout / 10) * 10;
}

function calculateDoublePayout(selectedHorses, betAmount) {
    const horse1 = horses.find(h => h.number === selectedHorses[0]);
    const horse2 = horses.find(h => h.number === selectedHorses[1]);

    if (!horse1 || !horse2) return 0;

    let coefficient = 1.5;
    if (currentBetType === 'exacta') coefficient = 2.0;
    if (currentBetType === 'wide') coefficient = 1.2;

    const combinedOdds = ((horse1.odds + horse2.odds) / 2) * coefficient;
    const payout = betAmount * combinedOdds;

    return Math.floor(payout / 10) * 10;
}

function calculateTriplePayout(selectedHorses, betAmount) {
    const horse1 = horses.find(h => h.number === selectedHorses[0]);
    const horse2 = horses.find(h => h.number === selectedHorses[1]);
    const horse3 = horses.find(h => h.number === selectedHorses[2]);

    if (!horse1 || !horse2 || !horse3) return 0;

    let coefficient = 5.0;
    if (currentBetType === 'trifecta') coefficient = 10.0;

    const combinedOdds = ((horse1.odds + horse2.odds + horse3.odds) / 3) * coefficient;
    const payout = betAmount * combinedOdds;

    return Math.floor(payout / 10) * 10;
}

// ==================== 結果表示・リセット ====================
function displayResult(payout, betAmount, explanation, betTypeName) {
    const resultContent = document.getElementById('result-content');
    const profit = payout - betAmount;
    const returnRate = betAmount > 0 ? ((payout / betAmount) * 100).toFixed(1) : 0;
    
    resultContent.innerHTML = `
        <div class="result-item">
            <span class="result-label">馬券種類</span>
            <span class="result-value">${betTypeName}</span>
        </div>
        <div class="result-item">
            <span class="result-label">的中馬番</span>
            <span class="result-value">${explanation}</span>
        </div>
        <div class="result-item">
            <span class="result-label">払戻金</span>
            <span class="result-value big">${payout.toLocaleString()}円</span>
        </div>
        <div class="result-item">
            <span class="result-label">損益</span>
            <span class="result-value" style="color: ${profit >= 0 ? 'var(--success-color)' : 'var(--error-color)'};">
                ${profit >= 0 ? '+' : ''}${profit.toLocaleString()}円 (回収率: ${returnRate}%)
            </span>
        </div>
    `;
    const resultSection = document.getElementById('result-section');
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function resetForm() {
    ['bet-type-section', 'odds-display-section', 'purchase-section', 'result-section'].forEach(id => {
        document.getElementById(id).style.display = 'none';
    });
    
    raceInfo = { type: null, venue: null, date: new Date().toISOString().split('T')[0], number: null };
    document.getElementById('race-date').value = raceInfo.date;

    document.querySelectorAll('.btn-group-item.active').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById('venue-group').style.display = 'none';
    document.getElementById('race-number-group').style.display = 'none';
    document.getElementById('fetch-btn-group').style.display = 'none';
    
    horses = [];
    currentBetType = 'win';
    updateButtonGroup(document.querySelector('.bet-type-btn[data-type="win"]'), '.bet-type-btn');
}

// ==================== ユーティリティ ====================
function generateRaceId() {
    if (!raceInfo.type || !raceInfo.venue || !raceInfo.date || !raceInfo.number) {
        return null;
    }
    const [year, month, day] = raceInfo.date.split('-');
    return `${year}${raceInfo.venue}${month}${day}${raceInfo.number}`;
}

function setLoading(isLoading) {
    const btn = document.getElementById('fetch-odds-btn');
    btn.disabled = isLoading;
    btn.querySelector('.btn-text').style.display = isLoading ? 'none' : 'inline';
    btn.querySelector('.btn-loading').style.display = isLoading ? 'inline-flex' : 'none';
}

function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('scraping-status');
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'block';
}

function getBetTypeName(type) {
    const names = { 'win': '単勝', 'place': '複勝', 'quinella': '馬連', 'exacta': '馬単', 'wide': 'ワイド', 'trio': '三連複', 'trifecta': '三連単' };
    return names[type] || type;
}

// (fetchWithProxy, fetchNetkeiba は既存のものをほぼ流用)
async function fetchWithProxy(url, proxyIndex = 0) {
    if (proxyIndex >= CORS_PROXIES.length) {
        throw new Error('すべてのCORSプロキシで失敗しました');
    }
    const proxy = CORS_PROXIES[proxyIndex];
    const proxyUrl = proxy + encodeURIComponent(url);
    try {
        const response = await fetch(proxyUrl);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.text();
    } catch (error) {
        console.warn(`プロキシ ${proxy} 失敗.`, error);
        return fetchWithProxy(url, proxyIndex + 1);
    }
}

async function fetchNetkeiba(url) {
    const html = await fetchWithProxy(url);
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const horses = [];
    const rows = doc.querySelectorAll('.RaceTable01 tr[class^="HorseList"]');
    rows.forEach(row => {
        const numCell = row.querySelector('td:nth-child(2)');
        const oddsCell = row.querySelector('td:nth-child(14)'); 
        if (numCell && oddsCell) {
            const number = parseInt(numCell.textContent.trim(), 10);
            const odds = parseFloat(oddsCell.textContent.trim());
            if (number && !isNaN(odds) && odds > 0) {
                horses.push({ number, odds });
            }
        }
    });
    if (horses.length === 0) {
      const altRows = doc.querySelectorAll('.Shutuba_Table tbody tr');
        altRows.forEach(row => {
            const numCell = row.querySelector('.Num');
            const oddsCell = row.querySelector('.Popular');
             if (numCell && oddsCell) {
                const number = parseInt(numCell.textContent.trim());
                const odds = parseFloat(oddsCell.textContent.trim());
                 if (number && !isNaN(odds) && odds > 0) {
                    horses.push({ number, odds });
                }
            }
        });
    }
    return { horses };
}

function updateSelectionArea() {
    const selectionArea = document.getElementById('selection-area');
    if (horses.length === 0) {
        selectionArea.innerHTML = '<p class="text-light">オッズを先に取得してください。</p>';
        return;
    }

    let html = '';
    const horseOptions = horses.map(h => `<button class="horse-select-btn" data-horse="${h.number}">${h.number}</button>`).join('');

    const generateHtml = (labels) => {
        return labels.map((label, i) => `
            <div class="selection-group">
                <label>${label}</label>
                <div class="horse-select-grid" data-position="${i + 1}">
                    ${horseOptions}
                </div>
            </div>
        `).join('');
    }

    switch (currentBetType) {
        case 'win':
        case 'place':
            html = generateHtml(['的中馬']);
            break;
        case 'quinella':
        case 'wide':
            html = generateHtml(['1頭目', '2頭目']);
            break;
        case 'exacta':
            html = generateHtml(['1着', '2着']);
            break;
        case 'trio':
            html = generateHtml(['1頭目', '2頭目', '3頭目']);
            break;
        case 'trifecta':
            html = generateHtml(['1着', '2着', '3着']);
            break;
    }
    selectionArea.innerHTML = html;
    selectionArea.querySelectorAll('.horse-select-grid').forEach(grid => {
        grid.addEventListener('click', handleHorseSelection);
    });
}

function handleHorseSelection(e) {
    if (!e.target.matches('.horse-select-btn')) return;
    const selectedBtn = e.target;
    
    const isMultiSelect = ['quinella', 'wide', 'trio'].includes(currentBetType);
    const parentGrid = selectedBtn.parentElement;
    const position = parentGrid.dataset.position;

    if (isMultiSelect) {
        const maxSelections = currentBetType === 'trio' ? 3 : 2;
        if (selectedBtn.classList.contains('selected')) {
            selectedBtn.classList.remove('selected');
        } else {
            const selectedCount = parentGrid.querySelectorAll('.selected').length;
            if (selectedCount < maxSelections) {
                selectedBtn.classList.add('selected');
            }
        }
    } else {
        parentGrid.querySelectorAll('.horse-select-btn').forEach(btn => btn.classList.remove('selected'));
        selectedBtn.classList.add('selected');
    }
    
    const horseNumber = selectedBtn.dataset.horse;
    document.querySelectorAll(`.horse-select-btn[data-horse="${horseNumber}"].selected`).forEach(btn => {
        if(btn.parentElement.dataset.position !== position) {
            btn.classList.remove('selected');
        }
    });
}