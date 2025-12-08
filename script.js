// ==================== グローバル変数 ====================
let currentBetType = 'win'; // 現在選択中の馬券種類
let horseCount = 0; // 追加された馬の数
let horses = []; // 馬のデータ {number, odds}
let isAutoMode = true; // 自動取得モード（デフォルト）

// CORSプロキシ設定（複数用意してフォールバック）
const CORS_PROXIES = [
    'https://api.allorigins.win/raw?url=',
    'https://corsproxy.io/?',
    'https://cors-anywhere.herokuapp.com/'
];

// 競馬場データ
const RACECOURSES = {
    central: {
        '01': '札幌',
        '02': '函館',
        '03': '福島',
        '04': '新潟',
        '05': '東京',
        '06': '中山',
        '07': '中京',
        '08': '京都',
        '09': '阪神',
        '10': '小倉'
    },
    local: {
        '30': '門別',
        '35': '盛岡',
        '36': '水沢',
        '42': '浦和',
        '43': '船橋',
        '44': '大井',
        '45': '川崎',
        '46': '金沢',
        '47': '笠松',
        '48': '名古屋',
        '50': '園田',
        '51': '姫路',
        '54': '高知',
        '55': '佐賀'
    }
};

// ==================== 初期化 ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // イベントリスナーを設定
    setupEventListeners();

    // 今日の日付を設定
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('race-date').value = today;

    // 初期状態で3頭分の入力欄を追加
    addHorseInput();
    addHorseInput();
    addHorseInput();

    // 選択エリアを更新
    updateSelectionArea();
}

// ==================== イベントリスナー設定 ====================
function setupEventListeners() {
    // 馬券種類選択ボタン
    const betTypeBtns = document.querySelectorAll('.bet-type-btn');
    betTypeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            betTypeBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentBetType = this.dataset.type;
            updateSelectionArea();
        });
    });

    // 段階的選択のイベントリスナー
    document.getElementById('race-type').addEventListener('change', onRaceTypeChange);
    document.getElementById('race-venue').addEventListener('change', onVenueChange);
    document.getElementById('race-date').addEventListener('change', onDateChange);
    document.getElementById('race-number').addEventListener('change', onRaceNumberChange);

    // オッズ自動取得ボタン
    document.getElementById('fetch-odds-btn').addEventListener('click', fetchOddsFromSelection);

    // 馬を追加ボタン
    document.getElementById('add-horse-btn').addEventListener('click', addHorseInput);

    // 計算ボタン
    document.getElementById('calculate-btn').addEventListener('click', calculatePayout);

    // リセットボタン
    document.getElementById('reset-btn').addEventListener('click', resetForm);
}

// ==================== 馬の入力欄を追加 ====================
function addHorseInput() {
    horseCount++;
    const container = document.getElementById('odds-input-area');

    const row = document.createElement('div');
    row.className = 'horse-input-row';
    row.id = `horse-row-${horseCount}`;

    row.innerHTML = `
        <input type="number" class="horse-number" placeholder="馬番" min="1" max="99" value="${horseCount}">
        <input type="number" class="horse-odds" placeholder="オッズ (例: 3.5)" step="0.1" min="1.0">
        <button class="remove-horse-btn" onclick="removeHorseInput(${horseCount})">削除</button>
    `;

    container.appendChild(row);

    // 入力欄の変更時に選択エリアを更新
    const inputs = row.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('input', updateSelectionArea);
    });
}

// ==================== 馬の入力欄を削除 ====================
function removeHorseInput(id) {
    const row = document.getElementById(`horse-row-${id}`);
    if (row) {
        row.remove();
        updateSelectionArea();
    }
}

// ==================== 馬のデータを取得 ====================
function getHorsesData() {
    const rows = document.querySelectorAll('.horse-input-row');
    const horsesData = [];

    rows.forEach(row => {
        const number = parseInt(row.querySelector('.horse-number').value);
        const odds = parseFloat(row.querySelector('.horse-odds').value);

        if (number && odds && odds > 0) {
            horsesData.push({ number, odds });
        }
    });

    // 馬番順にソート
    horsesData.sort((a, b) => a.number - b.number);

    return horsesData;
}

// ==================== 選択エリアを更新 ====================
function updateSelectionArea() {
    horses = getHorsesData();
    const selectionArea = document.getElementById('selection-area');

    if (horses.length === 0) {
        selectionArea.innerHTML = '<p style="color: #999;">オッズを入力してください</p>';
        return;
    }

    let html = '';

    switch (currentBetType) {
        case 'win': // 単勝
        case 'place': // 複勝
            html = generateSingleSelection('的中馬番を選択');
            break;

        case 'quinella': // 馬連
        case 'exacta': // 馬単
        case 'wide': // ワイド
            html = generateDoubleSelection();
            break;

        case 'trio': // 三連複
        case 'trifecta': // 三連単
            html = generateTripleSelection();
            break;
    }

    selectionArea.innerHTML = html;
}

// ==================== 単一選択UI生成 ====================
function generateSingleSelection(label) {
    let html = `<div class="selection-group">
        <label>${label}</label>
        <div class="horse-select-grid">`;

    horses.forEach(horse => {
        html += `<button class="horse-select-btn" data-position="1" data-horse="${horse.number}">${horse.number}番</button>`;
    });

    html += `</div></div>`;

    // イベントリスナーを設定するためにタイムアウトを使用
    setTimeout(() => {
        document.querySelectorAll('.horse-select-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                // 同じポジションの他のボタンの選択を解除
                const position = this.dataset.position;
                document.querySelectorAll(`[data-position="${position}"]`).forEach(b => {
                    b.classList.remove('selected');
                });
                this.classList.add('selected');
            });
        });
    }, 0);

    return html;
}

// ==================== 2頭選択UI生成 ====================
function generateDoubleSelection() {
    const isExacta = currentBetType === 'exacta';
    const labels = isExacta ? ['1着', '2着'] : ['1頭目', '2頭目'];

    let html = '';

    for (let i = 0; i < 2; i++) {
        html += `<div class="selection-group">
            <label>${labels[i]}を選択</label>
            <div class="horse-select-grid">`;

        horses.forEach(horse => {
            html += `<button class="horse-select-btn" data-position="${i + 1}" data-horse="${horse.number}">${horse.number}番</button>`;
        });

        html += `</div></div>`;
    }

    // イベントリスナーを設定
    setTimeout(() => {
        document.querySelectorAll('.horse-select-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const position = this.dataset.position;
                document.querySelectorAll(`[data-position="${position}"]`).forEach(b => {
                    b.classList.remove('selected');
                });
                this.classList.add('selected');
            });
        });
    }, 0);

    return html;
}

// ==================== 3頭選択UI生成 ====================
function generateTripleSelection() {
    const isTrifecta = currentBetType === 'trifecta';
    const labels = isTrifecta ? ['1着', '2着', '3着'] : ['1頭目', '2頭目', '3頭目'];

    let html = '';

    for (let i = 0; i < 3; i++) {
        html += `<div class="selection-group">
            <label>${labels[i]}を選択</label>
            <div class="horse-select-grid">`;

        horses.forEach(horse => {
            html += `<button class="horse-select-btn" data-position="${i + 1}" data-horse="${horse.number}">${horse.number}番</button>`;
        });

        html += `</div></div>`;
    }

    // イベントリスナーを設定
    setTimeout(() => {
        document.querySelectorAll('.horse-select-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const position = this.dataset.position;
                document.querySelectorAll(`[data-position="${position}"]`).forEach(b => {
                    b.classList.remove('selected');
                });
                this.classList.add('selected');
            });
        });
    }, 0);

    return html;
}

// ==================== 選択された馬番を取得 ====================
function getSelectedHorses() {
    const selected = [];
    const buttons = document.querySelectorAll('.horse-select-btn.selected');

    buttons.forEach(btn => {
        const position = parseInt(btn.dataset.position);
        const horseNumber = parseInt(btn.dataset.horse);
        selected.push({ position, horseNumber });
    });

    // ポジション順にソート
    selected.sort((a, b) => a.position - b.position);

    return selected.map(s => s.horseNumber);
}

// ==================== 払戻金を計算 ====================
function calculatePayout() {
    const betAmount = parseInt(document.getElementById('bet-amount').value) || 100;
    const selectedHorses = getSelectedHorses();

    // バリデーション
    if (!validateInput(selectedHorses)) {
        return;
    }

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

    displayResult(payout, betAmount, explanation);
}

// ==================== 入力バリデーション ====================
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

    // 同じ馬が選択されていないかチェック
    const uniqueHorses = new Set(selectedHorses);
    if (uniqueHorses.size !== selectedHorses.length) {
        alert('同じ馬を複数選択することはできません');
        return false;
    }

    return true;
}

// ==================== 単勝・複勝の払戻金計算 ====================
function calculateSinglePayout(horseNumber, betAmount) {
    const horse = horses.find(h => h.number === horseNumber);
    if (!horse) return 0;

    const payout = betAmount * horse.odds;
    return Math.floor(payout / 10) * 10; // 10円未満切り捨て
}

// ==================== 馬連・馬単・ワイドの払戻金計算 ====================
function calculateDoublePayout(selectedHorses, betAmount) {
    // 実際のオッズは組み合わせによって異なるため、
    // ここでは選択された馬の単勝オッズを掛け合わせた簡易計算
    // 本来は組み合わせオッズが必要

    const horse1 = horses.find(h => h.number === selectedHorses[0]);
    const horse2 = horses.find(h => h.number === selectedHorses[1]);

    if (!horse1 || !horse2) return 0;

    // 簡易計算：2頭のオッズの平均 × 係数
    let coefficient = 1.5;
    if (currentBetType === 'exacta') coefficient = 2.0;
    if (currentBetType === 'wide') coefficient = 1.2;

    const combinedOdds = ((horse1.odds + horse2.odds) / 2) * coefficient;
    const payout = betAmount * combinedOdds;

    return Math.floor(payout / 10) * 10;
}

// ==================== 三連複・三連単の払戻金計算 ====================
function calculateTriplePayout(selectedHorses, betAmount) {
    const horse1 = horses.find(h => h.number === selectedHorses[0]);
    const horse2 = horses.find(h => h.number === selectedHorses[1]);
    const horse3 = horses.find(h => h.number === selectedHorses[2]);

    if (!horse1 || !horse2 || !horse3) return 0;

    // 簡易計算：3頭のオッズの平均 × 係数
    let coefficient = 5.0;
    if (currentBetType === 'trifecta') coefficient = 10.0;

    const combinedOdds = ((horse1.odds + horse2.odds + horse3.odds) / 3) * coefficient;
    const payout = betAmount * combinedOdds;

    return Math.floor(payout / 10) * 10;
}

// ==================== 結果を表示 ====================
function displayResult(payout, betAmount, explanation) {
    const resultSection = document.getElementById('result-section');
    const resultContent = document.getElementById('result-content');

    const profit = payout - betAmount;
    const returnRate = ((payout / betAmount) * 100).toFixed(1);

    const betTypeName = getBetTypeName(currentBetType);

    resultContent.innerHTML = `
        <div class="result-item">
            <div class="result-label">馬券種類</div>
            <div class="result-value">${betTypeName}</div>
        </div>

        <div class="result-item">
            <div class="result-label">的中馬番</div>
            <div class="result-value">${explanation}</div>
        </div>

        <div class="result-item">
            <div class="result-label">購入金額</div>
            <div class="result-value">${betAmount.toLocaleString()}円</div>
        </div>

        <div class="result-item">
            <div class="result-label">払戻金</div>
            <div class="result-value big">${payout.toLocaleString()}円</div>
        </div>

        <div class="result-item" style="border-left-color: ${profit >= 0 ? 'var(--success-color)' : 'var(--error-color)'}">
            <div class="result-label">損益</div>
            <div class="result-value" style="color: ${profit >= 0 ? 'var(--success-color)' : 'var(--error-color)'}">
                ${profit >= 0 ? '+' : ''}${profit.toLocaleString()}円 (回収率: ${returnRate}%)
            </div>
        </div>
    `;

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ==================== 馬券種類名を取得 ====================
function getBetTypeName(type) {
    const names = {
        'win': '単勝',
        'place': '複勝',
        'quinella': '馬連',
        'exacta': '馬単',
        'wide': 'ワイド',
        'trio': '三連複',
        'trifecta': '三連単'
    };
    return names[type] || type;
}

// ==================== フォームをリセット ====================
function resetForm() {
    // 馬の入力欄をクリア
    const container = document.getElementById('odds-input-area');
    container.innerHTML = '';
    horseCount = 0;

    // 初期状態の3頭を追加
    addHorseInput();
    addHorseInput();
    addHorseInput();

    // 購入金額をリセット
    document.getElementById('bet-amount').value = 100;

    // レース情報をクリア
    document.getElementById('race-type').value = '';
    document.getElementById('race-name').value = '';

    // 結果を非表示
    document.getElementById('result-section').style.display = 'none';

    // 選択エリアを更新
    updateSelectionArea();
}

// ==================== スクレイピング機能 ====================

// 競馬種別変更時の処理
function onRaceTypeChange(e) {
    const raceType = e.target.value;
    const venueGroup = document.getElementById('venue-group');
    const venueSelect = document.getElementById('race-venue');

    if (!raceType) {
        venueGroup.style.display = 'none';
        return;
    }

    // 競馬場リストを更新
    venueSelect.innerHTML = '<option value="">競馬場を選択してください</option>';
    const courses = RACECOURSES[raceType];

    for (const [code, name] of Object.entries(courses)) {
        const option = document.createElement('option');
        option.value = code;
        option.textContent = name;
        venueSelect.appendChild(option);
    }

    venueGroup.style.display = 'block';

    // 後続のフィールドを非表示
    document.getElementById('date-group').style.display = 'none';
    document.getElementById('race-number-group').style.display = 'none';
    document.getElementById('fetch-btn-group').style.display = 'none';
}

// 競馬場変更時の処理
function onVenueChange(e) {
    const venue = e.target.value;
    const dateGroup = document.getElementById('date-group');

    if (!venue) {
        dateGroup.style.display = 'none';
        return;
    }

    dateGroup.style.display = 'block';

    // 後続のフィールドを非表示
    document.getElementById('race-number-group').style.display = 'none';
    document.getElementById('fetch-btn-group').style.display = 'none';
}

// 日付変更時の処理
function onDateChange(e) {
    const date = e.target.value;
    const raceNumberGroup = document.getElementById('race-number-group');

    if (!date) {
        raceNumberGroup.style.display = 'none';
        return;
    }

    raceNumberGroup.style.display = 'block';

    // 取得ボタンを非表示（レース番号選択後に表示）
    document.getElementById('fetch-btn-group').style.display = 'none';
}

// レース番号変更時の処理
function onRaceNumberChange(e) {
    const raceNumber = e.target.value;
    const fetchBtnGroup = document.getElementById('fetch-btn-group');

    if (!raceNumber) {
        fetchBtnGroup.style.display = 'none';
        return;
    }

    fetchBtnGroup.style.display = 'block';
}

// レースID生成関数
function generateRaceId() {
    const date = document.getElementById('race-date').value; // YYYY-MM-DD
    const venue = document.getElementById('race-venue').value;
    const raceNumber = document.getElementById('race-number').value;

    if (!date || !venue || !raceNumber) {
        return null;
    }

    // 日付をYYYYMMDD形式に変換
    const [year, month, day] = date.split('-');

    // レースIDの構造: YYYY + 競馬場コード(2桁) + MMDD + レース番号(2桁)
    const raceId = year + venue + month + day + raceNumber;

    return raceId;
}

// 選択からオッズを取得
async function fetchOddsFromSelection() {
    const raceId = generateRaceId();

    if (!raceId) {
        showStatus('すべての項目を選択してください', 'error');
        return;
    }

    // netkeibaのURLを生成
    const url = `https://race.netkeiba.com/race/shutuba.html?race_id=${raceId}`;

    console.log('生成されたレースID:', raceId);
    console.log('生成されたURL:', url);

    try {
        setLoading(true);
        showStatus(`レースID: ${raceId} のオッズを取得中...`, 'info');

        const oddsData = await fetchNetkeiba(url);

        if (oddsData && oddsData.horses && oddsData.horses.length > 0) {
            populateHorsesFromScraping(oddsData);
            showStatus(`✓ ${oddsData.horses.length}頭のオッズデータを取得しました！`, 'success');
        } else {
            throw new Error('オッズデータが見つかりませんでした。レース情報を確認してください。');
        }

    } catch (error) {
        console.error('スクレイピングエラー:', error);
        showStatus(`✗ エラー: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

// ステータスメッセージ表示
function showStatus(message, type = 'info', statusId = 'scraping-status') {
    const statusDiv = document.getElementById(statusId);
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'block';
}

// ローディング状態切替
function setLoading(isLoading) {
    const btn = document.getElementById('fetch-odds-btn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoading = btn.querySelector('.btn-loading');

    if (isLoading) {
        btn.disabled = true;
        btnText.style.display = 'none';
        btnLoading.style.display = 'inline-flex';
    } else {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}

// netkeiba からオッズ取得
async function fetchNetkeiba(url) {
    try {
        const html = await fetchWithProxy(url);
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        const horses = [];

        // netkeiba の出馬表ページから単勝オッズを取得
        // テーブル構造: .RaceTableDataSet または .Shutuba_Table
        const rows = doc.querySelectorAll('.RaceTableDataSet tr, .Shutuba_Table tbody tr');

        rows.forEach(row => {
            // 馬番を取得
            const numCell = row.querySelector('.Waku, .Num, td:first-child');
            const oddsCell = row.querySelector('.Odds, .Popular, td.txt_r');

            if (numCell && oddsCell) {
                const numberText = numCell.textContent.trim();
                const oddsText = oddsCell.textContent.trim();

                const number = parseInt(numberText);
                const odds = parseFloat(oddsText);

                if (number && odds && !isNaN(number) && !isNaN(odds) && odds > 0) {
                    horses.push({ number, odds });
                }
            }
        });

        // 代替パターン: 別のHTML構造に対応
        if (horses.length === 0) {
            const altRows = doc.querySelectorAll('table tr');
            altRows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    const number = parseInt(cells[0].textContent.trim());
                    const oddsMatch = cells[cells.length - 1].textContent.match(/[\d.]+/);
                    const odds = oddsMatch ? parseFloat(oddsMatch[0]) : null;

                    if (number && odds && !isNaN(number) && !isNaN(odds) && odds > 0) {
                        horses.push({ number, odds });
                    }
                }
            });
        }

        // レース名を取得
        const raceName = doc.querySelector('.RaceName, h1, .race_name')?.textContent.trim() || '';

        return { horses, raceName, source: 'netkeiba' };

    } catch (error) {
        throw new Error(`netkeibaからの取得に失敗: ${error.message}`);
    }
}

// CORSプロキシ経由でHTMLを取得
async function fetchWithProxy(url, proxyIndex = 0) {
    if (proxyIndex >= CORS_PROXIES.length) {
        throw new Error('すべてのCORSプロキシで失敗しました');
    }

    const proxy = CORS_PROXIES[proxyIndex];
    const proxyUrl = proxy + encodeURIComponent(url);

    try {
        const response = await fetch(proxyUrl, {
            method: 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const html = await response.text();
        return html;

    } catch (error) {
        console.warn(`プロキシ${proxyIndex + 1}失敗、次を試行中...`, error);
        // 次のプロキシで再試行
        return fetchWithProxy(url, proxyIndex + 1);
    }
}

// スクレイピングしたデータで馬の入力欄を自動生成
function populateHorsesFromScraping(oddsData) {
    // 既存の入力欄をクリア
    const container = document.getElementById('odds-input-area');
    container.innerHTML = '';
    horseCount = 0;

    // 取得したデータで入力欄を生成
    oddsData.horses.forEach(horse => {
        horseCount++;
        const row = document.createElement('div');
        row.className = 'horse-input-row';
        row.id = `horse-row-${horseCount}`;

        row.innerHTML = `
            <input type="number" class="horse-number" placeholder="馬番" min="1" max="99" value="${horse.number}">
            <input type="number" class="horse-odds" placeholder="オッズ" step="0.1" min="1.0" value="${horse.odds}">
            <button class="remove-horse-btn" onclick="removeHorseInput(${horseCount})">削除</button>
        `;

        container.appendChild(row);

        // 入力欄の変更時に選択エリアを更新
        const inputs = row.querySelectorAll('input');
        inputs.forEach(input => {
            input.addEventListener('input', updateSelectionArea);
        });
    });

    // 選択エリアを更新
    updateSelectionArea();
}

// ==================== ユーティリティ関数 ====================

// 数値を3桁カンマ区切りにする
function formatNumber(num) {
    return num.toLocaleString('ja-JP');
}

// オッズを検証
function isValidOdds(odds) {
    return !isNaN(odds) && odds > 0;
}

// 馬番を検証
function isValidHorseNumber(num) {
    return Number.isInteger(num) && num > 0 && num < 100;
}
