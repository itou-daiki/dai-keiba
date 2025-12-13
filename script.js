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
        const loadSimBtn = e.target.closest('#load-simulation-btn');

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
        if (loadSimBtn) {
            loadSimulationData();
            return;
        }
    });
}

// ==================== データ取得・表示 ====================
let todaysDataCacche = null;

async function fetchTodaysRaces() {
    showStatus('今日のレース情報を読み込んでいます...', 'info');
    try {
        // GitHub Pages用に事前にスクレイピングされたJSONを読み込む
        const response = await fetch('todays_data.json');
        if (!response.ok) {
            throw new Error('レース情報ファイル(todays_data.json)が見つかりません。管理画面で更新してください。');
        }

        const data = await response.json();
        todaysDataCacche = data;

        const raceList = data.races.map(r => ({
            id: r.id,
            venue: r.venue,
            number: r.number,
            name: r.name
        }));

        displayTodaysRaces(raceList);

        if (raceList.length > 0) {
            showStatus(`データ日時: ${data.date} (管理画面で更新可能)`, 'success');
        } else {
            showStatus('本日のレースデータはありません。', 'info');
        }

    } catch (error) {
        console.error(error);
        showStatus('レース情報の読み込みに失敗しました。管理画面で「今日のレース情報を更新」を実行してください。', 'error');
        displayTodaysRaces([]);
    }
}

function displayTodaysRaces(races) {
    const container = document.getElementById('todays-races-list');
    container.innerHTML = '';

    if (races.length === 0) {
        const button = document.createElement('button');
        button.className = 'race-select-btn';
        button.disabled = true;
        button.innerHTML = `<span class="race-name">データなし</span>`;
        container.appendChild(button);
        return;
    }

    races.forEach(race => {
        const button = document.createElement('button');
        button.className = 'race-select-btn';
        button.dataset.raceId = race.id;
        button.dataset.raceName = `${race.venue} ${race.number} ${race.name}`;
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
    setLoading(true);
    showStatus(`「${selectedRace.name}」のオッズを表示中...`, 'info');

    try {
        // キャッシュから検索
        const race = todaysDataCacche.races.find(r => r.id === raceId);

        if (race && race.horses && race.horses.length > 0) {
            horses = race.horses;
            displayOdds(horses);
            showStatus(`✓ オッズを表示しました`, 'success');
            document.getElementById('bet-type-section').style.display = 'block';
            document.getElementById('odds-display-section').style.display = 'block';
            document.getElementById('purchase-section').style.display = 'block';
            updateSelectionArea();
        } else {
            throw new Error('このレースのオッズデータがありません。');
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

    return Array.from(selected).sort((a, b) => a - b);
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
    const html = await fetchViaNetlifyProxy(url);
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
        if (btn.parentElement.dataset.position !== position) {
            btn.classList.remove('selected');
        }
    });
}

// ==================== シミュレーション機能 ====================
// ==================== シミュレーション機能 ====================
let globalRaceData = null; // CSVデータをキャッシュ

async function loadDatabase() {
    if (globalRaceData) return globalRaceData;

    return new Promise((resolve, reject) => {
        Papa.parse("database.csv", {
            download: true,
            header: true,
            skipEmptyLines: true,
            dynamicTyping: true,
            complete: function (results) {
                console.log("Database loaded:", results.data.length, "rows");
                globalRaceData = results.data;
                resolve(globalRaceData);
            },
            error: function (error) {
                console.error("CSV Parse Error:", error);
                reject(error);
            }
        });
    });
}

async function loadSimulationData() {
    const yearStr = document.getElementById('sim-year').value;
    const monthStr = document.getElementById('sim-month').value;

    // YYYY年M月 or YYYY年MM月 format matching
    // CSV has "2025年12月6日" format date column: "日付"

    const loadBtn = document.getElementById('load-simulation-btn');
    loadBtn.disabled = true;
    loadBtn.textContent = '読み込み中...';

    try {
        const data = await loadDatabase();
        if (!data || data.length === 0) {
            throw new Error("データベースが空か、読み込めませんでした。");
        }

        // Filter data key: "日付" like "2024年1月%"
        // yearStr=2024, monthStr=01 -> "2024年1月" or "2024年01月" (Usually single digit month has no pad in Japanese date format often, but let's check scraper)
        // Scraper uses: date_text = match.group(1) from netkeiba title (e.g. 2024年1月5日)
        // So month is likely not zero-padded if < 10.

        const targetMonth = parseInt(monthStr, 10); // Remove zero padding
        const filterPrefix = `${yearStr}年${targetMonth}月`;

        console.log("Filtering for:", filterPrefix);

        // Filter relevant rows
        const filteredRows = data.filter(row => {
            return row['日付'] && row['日付'].startsWith(filterPrefix);
        });

        if (filteredRows.length === 0) {
            throw new Error(`${yearStr}年${targetMonth}月のデータが見つかりませんでした。`);
        }

        runSimulationCSV(filteredRows);

    } catch (error) {
        console.error('シミュレーションエラー:', error);
        alert(`エラー: ${error.message}`);
    } finally {
        loadBtn.disabled = false;
        loadBtn.textContent = 'データを読み込む';
    }
}

function runSimulationCSV(rows) {
    // Rows contains mixed race info and horse info (it is 1 row per horse)
    // We need to group by race_id

    const races = {};

    rows.forEach(row => {
        const rid = row['race_id'];
        if (!races[rid]) {
            races[rid] = {
                race_id: rid,
                race_title: row['レース名'],
                horses: []
            };
        }
        races[rid].horses.push({
            horse_number: row['馬 番'],
            popularity: row['人 気'],
            odds: row['単勝 オッズ'],
            rank: row['着 順'],
            horse_name: row['馬名']
        });
    });

    // Convert to array
    const raceList = Object.values(races);

    // Init stats
    let totalBets = 0;
    let totalWins = 0;
    let totalPayout = 0;
    const betAmount = 100;
    const raceResults = [];

    raceList.forEach(race => {
        // Sort horses by popularity
        const sortedHorses = race.horses.sort((a, b) => {
            const popA = parseFloat(a.popularity) || 999;
            const popB = parseFloat(b.popularity) || 999;
            return popA - popB;
        });

        const favorite = sortedHorses[0];
        if (!favorite) return;

        totalBets += betAmount;

        // Check win
        // rank might be "1" or 1
        const rank = parseInt(favorite.rank);

        if (rank === 1) {
            totalWins++;
            const odds = parseFloat(favorite.odds) || 0;
            const payout = Math.floor((betAmount * odds) / 10) * 10;
            totalPayout += payout;

            raceResults.push({
                race: race.race_title || race.race_id,
                horse: favorite.horse_number,
                odds: odds,
                payout: payout,
                win: true
            });
        } else {
            raceResults.push({
                race: race.race_title || race.race_id,
                horse: favorite.horse_number,
                odds: parseFloat(favorite.odds) || 0,
                payout: 0,
                win: false
            });
        }
    });

    const profit = totalPayout - totalBets;
    const recoveryRate = totalBets > 0 ? ((totalPayout / totalBets) * 100).toFixed(1) : 0;
    const winRate = raceList.length > 0 ? ((totalWins / raceList.length) * 100).toFixed(1) : 0;

    displaySimulationResults({
        totalRaces: raceList.length,
        totalBets,
        totalWins,
        totalPayout,
        profit,
        recoveryRate,
        winRate,
        results: raceResults
    });
}

// Function runSimulation(races, horses) is no longer used, replaced by runSimulationCSV

function displaySimulationResults(stats) {
    const resultDiv = document.getElementById('simulation-result');
    const statsDiv = document.getElementById('simulation-stats');

    statsDiv.innerHTML = `
        <div class="simulation-summary">
            <div class="result-item">
                <span class="result-label">総レース数</span>
                <span class="result-value">${stats.totalRaces}レース</span>
            </div>
            <div class="result-item">
                <span class="result-label">総投資額</span>
                <span class="result-value">${stats.totalBets.toLocaleString()}円</span>
            </div>
            <div class="result-item">
                <span class="result-label">的中数</span>
                <span class="result-value">${stats.totalWins}回</span>
            </div>
            <div class="result-item">
                <span class="result-label">的中率</span>
                <span class="result-value">${stats.winRate}%</span>
            </div>
            <div class="result-item">
                <span class="result-label">総払戻金</span>
                <span class="result-value">${stats.totalPayout.toLocaleString()}円</span>
            </div>
            <div class="result-item">
                <span class="result-label">損益</span>
                <span class="result-value" style="color: ${stats.profit >= 0 ? 'var(--success-color)' : 'var(--error-color)'};">
                    ${stats.profit >= 0 ? '+' : ''}${stats.profit.toLocaleString()}円
                </span>
            </div>
            <div class="result-item">
                <span class="result-label">回収率</span>
                <span class="result-value big" style="color: ${stats.recoveryRate >= 100 ? 'var(--success-color)' : 'var(--error-color)'};">
                    ${stats.recoveryRate}%
                </span>
            </div>
        </div>
        <p class="help-text" style="margin-top: 16px;">
            ※ このシミュレーションは「単勝1番人気を全て購入」した場合の結果です
        </p>
    `;

    resultDiv.style.display = 'block';
    resultDiv.scrollIntoView({ behavior: 'smooth' });
}