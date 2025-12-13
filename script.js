// ==================== グローバル変数 ====================
let currentBetType = 'split'; // 現在選択中の馬券種類
let horses = []; // 馬のデータ {number, odds}
let selectedRace = {
    id: null,
    name: null,
    mode: 'today' // 'today' or 'past'
};

// Data Caches
let todaysDataCache = null;
let pastDataCache = null;
let pastRaceListCache = []; // Processed list of past races

// State
// State
let activeTab = 'tab-today';
let selectedVenueToday = null;
let selectedVenuePast = null;
let selectedDatePast = null;

// ==================== 初期化 ====================
document.addEventListener('DOMContentLoaded', initializeApp);

function initializeApp() {
    setupEventListeners();
    fetchTodaysRaces();
}

// ==================== イベントリスナー設定 ====================
function setupEventListeners() {
    // Tab Switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Past Races Load
    const loadPastBtn = document.getElementById('load-past-races-btn');
    if (loadPastBtn) {
        loadPastBtn.addEventListener('click', loadPastRaces);
    }

    // Dynamic Content Delegation
    document.querySelector('main').addEventListener('click', (e) => {
        const raceSelectBtn = e.target.closest('.race-select-btn');
        const venueTabBtn = e.target.closest('.venue-tab-btn');
        const dateTabBtn = e.target.closest('.date-tab-btn');
        const betTypeBtn = e.target.closest('.bet-type-btn');
        const calculateBtn = e.target.closest('#calculate-btn');
        const resetBtn = e.target.closest('#reset-btn');
        const horseSelectBtn = e.target.closest('.horse-select-btn');

        if (raceSelectBtn) {
            handleRaceSelection(raceSelectBtn);
            return;
        }
        if (dateTabBtn) {
            handleDateSelection(dateTabBtn);
            return;
        }
        if (venueTabBtn) {
            handleVenueSelection(venueTabBtn);
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


function switchTab(tabId) {
    activeTab = tabId;
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');

    // Hide betting section when switching tabs
    resetForm();
}

// ==================== Today's Races Logic ====================
async function fetchTodaysRaces() {
    const statusMsg = document.getElementById('today-status-msg');
    statusMsg.style.display = 'block';
    statusMsg.textContent = '読み込み中...';

    try {
        const response = await fetch('todays_data.json');
        if (!response.ok) throw new Error('データが見つかりません');

        const data = await response.json();
        todaysDataCache = data;

        const races = data.races.map(r => ({ ...r, mode: 'today' }));

        // Group by Venue
        const venues = [...new Set(races.map(r => r.venue))];
        renderVenueTabs('today', venues);

        // Auto-select first venue
        if (venues.length > 0) {
            selectVenue('today', venues[0]);
        }

        statusMsg.style.display = 'none';

    } catch (error) {
        statusMsg.textContent = 'データの読み込みに失敗しました';
        statusMsg.className = 'status-message error';
    }
}

// ==================== Past Races Logic ====================
async function loadDatabase() {
    if (window.globalRaceData) return window.globalRaceData;

    return new Promise((resolve, reject) => {
        Papa.parse("database.csv", {
            download: true,
            header: true,
            skipEmptyLines: true,
            dynamicTyping: true,
            complete: function (results) {
                console.log("Database loaded:", results.data.length, "rows");
                window.globalRaceData = results.data;
                resolve(results.data);
            },
            error: function (error) {
                reject(error);
            }
        });
    });
}

async function loadPastRaces() {
    const btn = document.getElementById('load-past-races-btn');
    const originalText = btn.textContent;
    btn.textContent = '読み込み中...';
    btn.disabled = true;

    const year = document.getElementById('sim-year').value;
    const month = document.getElementById('sim-month').value;

    try {
        const data = await loadDatabase();

        // Filter by date
        const prefix = `${year}年${month}月`;
        const filtered = data.filter(row => row['日付'] && row['日付'].startsWith(prefix));

        if (filtered.length === 0) {
            alert('該当するデータがありませんでした。');
            return;
        }

        // Process into Race objects
        const racesMap = {};
        filtered.forEach(row => {
            const rid = row['race_id'];
            if (!racesMap[rid]) {
                racesMap[rid] = {
                    id: rid,
                    venue: getVenueFromRow(row), // Extract venue
                    number: row['レース'] || '',
                    name: row['レース名'],
                    date: row['日付'],
                    mode: 'past'
                };
            }
        });

        pastRaceListCache = Object.values(racesMap);
        window.pastRaceListCache = pastRaceListCache; // Force global
        console.log("Past Races Loaded:", pastRaceListCache.length, "races");

        // Group by Date first
        const dates = [...new Set(pastRaceListCache.map(r => r.date))].sort((a, b) => {
            // Sort date descending (newest first)
            // Date format likely YYYY年M月D日
            // Simple string compare often works if format is padded, but ideally parse
            // Let's rely on standard Japanese date format logic or just string desc for now
            return b.localeCompare(a, 'ja');
        });

        renderDateTabs(dates);

        // Auto-select first date
        if (dates.length > 0) {
            selectDate(dates[0]);
        }

        document.getElementById('past-date-tabs-container').style.display = 'block';
        document.getElementById('past-venue-tabs-container').style.display = 'block';
        document.getElementById('past-races-list-section').style.display = 'block';

    } catch (e) {
        console.error(e);
        alert('エラーが発生しました: ' + e.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function getVenueFromRow(row) {
    if (row['開催']) return row['開催'].replace(/\d+回/, '').replace(/\d+日目/, '').trim();
    const id = String(row['race_id']);
    const placeCode = id.substring(4, 6);
    const placeMap = {
        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
        "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"
    };
    return placeMap[placeCode] || "その他";
}

// ==================== Venue & Date Rendering ====================

function renderDateTabs(dates) {
    const container = document.getElementById('past-date-tabs');
    const wrapper = document.getElementById('past-date-tabs-container');
    container.innerHTML = '';

    if (dates.length === 0) {
        wrapper.style.display = 'none';
        return;
    }

    dates.forEach(date => {
        // Shorten date for display? "12月7日"
        const label = date.replace(/^\d+年/, '');
        const btn = document.createElement('button');
        btn.className = 'venue-tab-btn date-tab-btn'; // Reuse style + identifier
        btn.textContent = label;
        btn.dataset.date = date;
        container.appendChild(btn);
    });
}

function handleDateSelection(btn) {
    selectDate(btn.dataset.date);
}

function selectDate(date) {
    selectedDatePast = date;

    // Highlight active date
    document.querySelectorAll('.date-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.date === date);
    });

    // Filter venues for this date
    const racesOnDate = pastRaceListCache.filter(r => r.date === date);
    const venues = [...new Set(racesOnDate.map(r => r.venue))];

    renderVenueTabs('past', venues);

    // Auto Select first venue
    if (venues.length > 0) {
        selectVenue('past', venues[0]);
    } else {
        renderRaceList('past-races-list', []);
    }
}

function renderVenueTabs(type, venues) {
    const containerId = type === 'today' ? 'today-venue-tabs' : 'past-venue-tabs';
    const containerWrapper = document.getElementById(`${type}-venue-tabs-container`);
    const container = document.getElementById(containerId);

    container.innerHTML = '';

    if (venues.length === 0) {
        containerWrapper.style.display = 'none';
        return;
    }

    containerWrapper.style.display = 'block';

    venues.forEach(venue => {
        const btn = document.createElement('button');
        btn.className = 'venue-tab-btn';
        btn.textContent = venue;
        btn.dataset.type = type;
        btn.dataset.venue = venue;
        container.appendChild(btn);
    });
}

function handleVenueSelection(btn) {
    const type = btn.dataset.type;
    const venue = btn.dataset.venue;

    selectVenue(type, venue);
}

function selectVenue(type, venue) {
    const containerId = type === 'today' ? 'today-venue-tabs' : 'past-venue-tabs';
    const container = document.getElementById(containerId);

    container.querySelectorAll('.venue-tab-btn:not(.date-tab-btn)').forEach(b => {
        b.classList.toggle('active', b.dataset.venue === venue);
    });

    if (type === 'today') {
        selectedVenueToday = venue;
        const races = todaysDataCache.races.filter(r => r.venue === venue);
        renderRaceList('todays-races-list', races);
    } else {
        selectedVenuePast = venue;
        // Filter by Date AND Venue
        const races = pastRaceListCache.filter(r => r.date === selectedDatePast && r.venue === venue);

        races.sort((a, b) => parseInt(a.number) - parseInt(b.number));
        renderRaceList('past-races-list', races);
    }
}

function renderRaceList(containerId, races) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (races.length === 0) {
        container.innerHTML = '<p>レースがありません</p>';
        return;
    }

    races.forEach(race => {
        const btn = document.createElement('button');
        btn.className = 'race-select-btn';
        btn.dataset.raceId = race.id;
        btn.dataset.mode = race.mode;

        let label = '';
        if (race.mode === 'today') {
            label = `<span class="race-number">${race.number}</span> <span class="race-name">${race.name}</span>`;
        } else {
            // Past: Show Date too
            label = `<small>${race.date}</small><br><span class="race-number">${race.number}R</span> <span class="race-name">${race.name}</span>`;
        }

        btn.innerHTML = label;
        container.appendChild(btn);
    });
}

// ==================== Race Selection & Betting ====================
async function handleRaceSelection(btn) {
    const raceId = btn.dataset.raceId;
    const mode = btn.dataset.mode;

    selectedRace.id = raceId;
    selectedRace.mode = mode;

    // UI Update
    document.querySelectorAll('.race-select-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.getElementById('common-betting-section').style.display = 'block';
    resetForm(true); // Keep race selection, reset inputs

    // Scroll to bet section
    document.getElementById('common-betting-section').scrollIntoView({ behavior: 'smooth' });

    // Header Info
    let raceInfo = '';
    console.log(`Selecting Race: ID=${raceId}, Mode=${mode}`);

    if (mode === 'today') {
        if (!todaysDataCache || !todaysDataCache.races) {
            console.error("Today's cache is missing!");
            return;
        }
        const race = todaysDataCache.races.find(r => String(r.id) === String(raceId));
        if (!race) {
            console.error("Race not found in Today's cache", raceId, todaysDataCache.races);
            return;
        }
        raceInfo = `${race.venue} ${race.number} ${race.name}`;
        selectedRace.name = race.name;
    } else {
        // Fallback to window cache if available
        if ((!pastRaceListCache || pastRaceListCache.length === 0) && window.pastRaceListCache) {
            console.log("Restoring pastRaceListCache from window");
            pastRaceListCache = window.pastRaceListCache;
        }

        if (!pastRaceListCache || pastRaceListCache.length === 0) {
            console.error("Past cache is missing or empty!", pastRaceListCache);
            return;
        }
        const race = pastRaceListCache.find(r => String(r.id) === String(raceId));
        if (!race) {
            console.error("Race not found in Past cache", raceId, pastRaceListCache);
            return;
        }
        raceInfo = `${race.date} ${race.venue} ${race.number}R ${race.name}`;
        selectedRace.name = race.name;
    }
    document.getElementById('selected-race-info').textContent = raceInfo;

    // Fetch Odds
    if (mode === 'today') {
        const race = todaysDataCache.races.find(r => String(r.id) === String(raceId));
        horses = race.horses;
        displayOdds(horses);
    } else {
        // Scrape Fresh Odds for Past Race
        await fetchPastRaceOdds(raceId);
    }

    document.getElementById('bet-type-section').style.display = 'block';

    // Force Win tab active
    handleBetTypeSelection(document.querySelector('.bet-type-btn[data-type="win"]'));
}

async function fetchPastRaceOdds(raceId) {
    const container = document.getElementById('odds-display-area');
    container.innerHTML = '<div style="padding:20px; text-align:center;">オッズ取得中...</div>';
    document.getElementById('odds-display-section').style.display = 'block';

    try {
        // Use netkeiba proxy logic
        // URL for odds: 
        const url = `https://race.netkeiba.com/odds/index.html?race_id=${raceId}`;
        const data = await fetchNetkeiba(url);

        if (data.horses && data.horses.length > 0) {
            horses = data.horses;
            displayOdds(horses);
            document.getElementById('purchase-section').style.display = 'block';
        } else {
            container.innerHTML = '<p>オッズ情報が取得できませんでした。</p>';
        }
    } catch (e) {
        container.innerHTML = `<p class="error">エラー: ${e.message}</p>`;
    }
}

function displayOdds(horsesData) {
    const container = document.getElementById('odds-display-area');
    container.innerHTML = '';

    if (!horsesData || horsesData.length === 0) {
        container.innerHTML = '<p>データなし</p>';
        return;
    }

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
                    <td>${h.odds > 0 ? h.odds.toFixed(1) : '---'}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    container.appendChild(table);
    document.getElementById('odds-display-section').style.display = 'block';
    document.getElementById('purchase-section').style.display = 'block';
}

// ... (Rest of logic: handleBetTypeSelection, calculatePayout, etc. - largely same but ensuring they work with global `horses` variable)

// Re-implement handleBetTypeSelection to ensure it shows selection area
function handleBetTypeSelection(selectedBtn) {
    if (!selectedBtn) return;
    currentBetType = selectedBtn.dataset.type;

    const parent = selectedBtn.parentElement;
    parent.querySelectorAll('.bet-type-btn').forEach(btn => btn.classList.remove('active'));
    selectedBtn.classList.add('active');

    updateSelectionArea();
}

// ... Reuse existing updateSelectionArea, handleHorseSelection, calculatePayout, displayResult ...
// Copied helper functions for completeness or ensure they are preserved

function resetForm(keepRace = false) {
    if (!keepRace) {
        document.querySelectorAll('.race-select-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('common-betting-section').style.display = 'none';
        selectedRace = { id: null, name: null, mode: null };
        horses = [];

        // Reset Bet Type buttons
        document.querySelectorAll('.bet-type-btn').forEach(btn => btn.classList.remove('active'));
        const winBtn = document.querySelector('.bet-type-btn[data-type="win"]');
        if (winBtn) winBtn.classList.add('active');
        currentBetType = 'win';
    }

    document.getElementById('result-section').style.display = 'none';

    // Hide sub-sections if fully resetting or just switching race? 
    // Usually switching race keeps bet type but resets odds display? 
    // Original logic was aggressive. Let's keep it simple: 
    // If keepRace is true, we anticipate new odds affecting the display soon.

    const betInput = document.getElementById('bet-amount');
    if (betInput) betInput.value = 100;

    document.getElementById('selection-area').innerHTML = '<p class="text-light">馬券種類を選択してください。</p>';
    document.getElementById('odds-display-area').innerHTML = '';
    document.getElementById('odds-display-section').style.display = 'none';
    document.getElementById('purchase-section').style.display = 'none';
}

// Utility for Netlify Proxy (Preserved)
async function fetchViaNetlifyProxy(targetUrl) {
    const apiUrl = `/api/fetch?url=${encodeURIComponent(targetUrl)}`;
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return await response.text();
    } catch (error) {
        console.error('Proxy Error:', error);
        throw error;
    }
}

async function fetchNetkeiba(url) {
    const html = await fetchViaNetlifyProxy(url);
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const horses = [];

    // Parsing logic for Odds Page
    // Selector: .RaceOdds_HorseList_Table (Win/Place)
    // Need to handle different page structures if scraping shutuba vs odds
    // The scrape_todays logic uses race/odds/odds_get_form.html?type=b1

    // Let's try to parse standard odds page table
    const rows = doc.querySelectorAll('#odds_tan_block table tr, .RaceOdds_HorseList_Table tr, .Shutuba_Table tr');

    rows.forEach(row => {
        let num, odds;

        // Try different column patterns
        // Pattern 1: Odds Page (Col 2 = Num, Col 6 = Odds)
        const cells = row.querySelectorAll('td');
        if (cells.length > 5) {
            const numTxt = cells[1].textContent.trim();
            const oddsTxt = cells[5].textContent.trim();
            if (numTxt.match(/^\d+$/)) {
                num = parseInt(numTxt);
                odds = parseFloat(oddsTxt);
            }
        }

        // Pattern 2: Shutuba Page (Class names)
        if (!num) {
            const numEl = row.querySelector('.Umaban');
            const oddsEl = row.querySelector('.Odds_Tan, .Popular');
            if (numEl && oddsEl) {
                num = parseInt(numEl.textContent.trim());
                odds = parseFloat(oddsEl.textContent.trim());
            }
        }

        if (num && !isNaN(num)) {
            // Check for duplicate
            if (!horses.find(h => h.number === num)) {
                horses.push({ number: num, odds: isNaN(odds) ? 0 : odds });
            }
        }
    });

    return { horses: horses.sort((a, b) => a.number - b.number) };
}

// Ensure other helpers are available
// ... (Preserve calculatePayout, displayResult, functions)

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
