// ==================== グローバル変数 ====================
let currentBetType = 'win'; // 現在選択中の馬券種類
let horses = []; // 馬のデータ {number, odds}
let selectedRace = {
    id: null,
    name: null,
};

// ==================== 初期化 ====================
document.addEventListener('DOMContentLoaded', initializeApp);

function initializeApp() {
    fetchTodaysRaces();
    setupEventListeners();
}

// ==================== イベントリスナー設定 ====================
function setupEventListeners() {
    const mainElement = document.querySelector('main');
    if (!mainElement) return;

    mainElement.addEventListener('click', (e) => {
        const raceSelectBtn = e.target.closest('.race-select-btn');
        const betTypeBtn = e.target.closest('.bet-type-btn');
        const calculateBtn = e.target.closest('#calculate-btn');
        const resetBtn = e.target.closest('#reset-btn');
        const horseSelectBtn = e.target.closest('.horse-select-btn');

        if (raceSelectBtn) {
            handleRaceSelection(raceSelectBtn);
            return;
        }
        if (betTypeBtn) {
            handleBetTypeSelection(betTypeBtn);
            return;
        }
        if (calculateBtn) {
            calculatePayout();
            return;
        }
        if (resetBtn) {
            resetForm();
            return;
        }
        if (horseSelectBtn) {
            handleHorseSelection(horseSelectBtn);
            return;
        }
    });
}

// ==================== データ取得・表示 ====================
async function fetchTodaysRaces() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const kaisaiDate = `${year}${month}${day}`;

    const url = `https://race.netkeiba.com/top/race_list.html?kaisai_date=${kaisaiDate}`;
    showStatus('今日のレース情報を取得中...', 'info');
    try {
        const html = await fetchViaNetlifyProxy(url);
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        const raceList = [];
        const raceElements = doc.querySelectorAll('.RaceList_Box .RaceList_Item');

        raceElements.forEach(race => {
            const link = race.querySelector('a');
            if (link) {
                const href = link.href;
                const raceIdMatch = href.match(/race_id=([0-9a-zA-Z_]+)/);
                
                const venueName = race.querySelector('.JyoName')?.textContent.trim();
                const raceNumber = race.querySelector('.Race_Num')?.textContent.trim();
                const raceName = race.querySelector('.RaceName')?.textContent.trim();

                if (raceIdMatch && venueName && raceNumber && raceName) {
                    raceList.push({
                        id: raceIdMatch[1],
                        venue: venueName,
                        number: raceNumber,
                        name: raceName,
                    });
                }
            }
        });
        
        displayTodaysRaces(raceList);
        if (raceList.length > 0) {
            showStatus('レースを選択してください。', 'info');
        } else {
            showStatus('今日の開催レース情報が見つかりませんでした。', 'error');
        }

    } catch (error) {
        showStatus(`レース情報の取得に失敗しました: ${error.message}`, 'error');
        displayTodaysRaces([]); // Show disabled button on error
    }
}

function displayTodaysRaces(races) {
    const container = document.getElementById('todays-races-list');
    container.innerHTML = '';

    if (races.length === 0) {
        const button = document.createElement('button');
        button.className = 'race-select-btn';
        button.disabled = true;
        button.innerHTML = `<span class="race-name">本日のレースはありません</span>`;
        container.appendChild(button);
        return;
    }

    races.forEach(race => {
        const button = document.createElement('button');
        button.className = 'race-select-btn';
        button.dataset.raceId = race.id;
        button.dataset.raceName = `${race.venue} ${race.number} ${race.name}`; // Store full name
        button.innerHTML = `
            <span class="race-number">${race.venue} ${race.number}</span>
            <span class="race-name">${race.name}</span>
        `;
        container.appendChild(button);
    });
}


function handleRaceSelection(selectedBtn) {
    if (!selectedBtn || selectedBtn.disabled) return;

    selectedRace.id = selectedBtn.dataset.raceId;
    selectedRace.name = selectedBtn.dataset.raceName;
    
    document.querySelectorAll('.race-select-btn').forEach(btn => btn.classList.remove('active'));
    selectedBtn.classList.add('active');

    fetchOdds(selectedRace.id);
}

async function fetchOdds(raceId) {
    const url = `https://race.netkeiba.com/race/shutuba.html?race_id=${raceId}`;
    setLoading(true);
    showStatus(`「${selectedRace.name}」のオッズを取得中...`, 'info');

    try {
        const oddsData = await fetchNetkeiba(url);
        if (oddsData && oddsData.horses && oddsData.horses.length > 0) {
            horses = oddsData.horses;
            displayOdds(horses);
            showStatus(`✓ オッズを取得しました！`, 'success');
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

// ==================== UIハンドラ ====================
function handleBetTypeSelection(selectedBtn) {
    if (!selectedBtn) return;
    currentBetType = selectedBtn.dataset.type;
    const parent = selectedBtn.parentElement;
    parent.querySelectorAll('.bet-type-btn').forEach(btn => btn.classList.remove('active'));
    selectedBtn.classList.add('active');
    updateSelectionArea();
}

// ==================== 払戻金計算 ====================
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
            explanation = `${selectedHorses.join(' - ')}番`;
            break;

        case 'trio':
        case 'trifecta':
            payout = calculateTriplePayout(selectedHorses, betAmount);
            explanation = `${selectedHorses.join(' - ')}番`;
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
            <span class="result-label">レース</span>
            <span class="result-value">${selectedRace.name}</span>
        </div>
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
    
    horses = [];
    selectedRace = { id: null, name: null };
    currentBetType = 'win';
    
    const betTypeContainer = document.getElementById('bet-type-section');
    betTypeContainer.querySelectorAll('.bet-type-btn').forEach(btn => btn.classList.remove('active'));
    betTypeContainer.querySelector('.bet-type-btn[data-type="win"]').classList.add('active');

    fetchTodaysRaces();
}


// ==================== ユーティリティ ====================
function setLoading(isLoading) {
    if (isLoading) {
        showStatus('データを取得中...', 'info');
    }
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

/**
 * Netlifyのサーバーレスプロキシ経由でURLからHTMLを取得します。
 * @param {string} targetUrl 取得対象のURL
 * @returns {Promise<string>} 取得したHTML文字列
 */
async function fetchViaNetlifyProxy(targetUrl) {
    // /api/fetch エンドポイントに、URLをエンコードしてクエリパラメータとして渡す
    const apiUrl = `/api/fetch?url=${encodeURIComponent(targetUrl)}`;
    console.log(`Netlifyプロキシ経由で取得: ${apiUrl}`);

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`サーバーからの応答が不正です: ${response.status} ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Netlifyプロキシ経由でのフェッチに失敗しました:', error);
        throw new Error(`データ取得に失敗しました。(${error.message})`);
    }
}

async function fetchNetkeiba(url) {
    const html = await fetchViaNetlifyProxy(url); // 新しい関数を使用
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const horses = [];
    const rows = doc.querySelectorAll('.Shutuba_Table tbody tr');
    rows.forEach(row => {
        const numCell = row.querySelector('.Umaban');
        const oddsCell = row.querySelector('.Odds_Tan'); 
        if (numCell && oddsCell) {
            const number = parseInt(numCell.textContent.trim(), 10);
            const odds = parseFloat(oddsCell.textContent.trim());
            if (number && !isNaN(odds) && odds > 0) {
                horses.push({ number, odds });
            }
        }
    });
     if (horses.length === 0) { 
        const altRows = doc.querySelectorAll('.RaceTable01 tr[class^="HorseList"]');
        altRows.forEach(row => {
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
}

function handleHorseSelection(selectedBtn) {
    if (!selectedBtn) return;
    
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
        parentGrid.querySelectorAll('.horse-select-btn').forEach(btn => btn.classList.remove('active'));
        selectedBtn.classList.add('active');
    }
    
    const horseNumber = selectedBtn.dataset.horse;
    document.querySelectorAll(`.horse-select-btn[data-horse="${horseNumber}"].selected`).forEach(btn => {
        if(btn.parentElement.dataset.position !== position) {
            btn.classList.remove('selected');
        }
    });
}