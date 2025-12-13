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
let currentBetMethod = 'normal'; // 'normal', 'box', 'nagashi', 'formation'

// Methods Definition
const bettingMethods = {
    'win': ['normal'],
    'place': ['normal'],
    'quinella': ['normal', 'box', 'nagashi'], // nagashi = 1-axis
    'exacta': ['normal', 'box', 'nagashi', 'formation'], // nagashi = 1-axis, multi?
    'wide': ['normal', 'box', 'nagashi'],
    'trio': ['normal', 'box', 'nagashi', 'formation'], // nagashi = 1-axis, formation
    'trifecta': ['normal', 'box', 'nagashi', 'formation']
};

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

    // Date Dropdown Change
    const dateSelect = document.getElementById('past-date-select');
    if (dateSelect) {
        dateSelect.addEventListener('change', (e) => handleDateChange(e.target));
    }

    // Dynamic Content Delegation
    document.querySelector('main').addEventListener('click', (e) => {
        const target = e.target;
        // console.log('Click detected on:', target, target.className); // Cleanup logs if desired

        const raceSelectBtn = target.closest('.race-select-btn');
        const venueTabBtn = target.closest('.venue-tab-btn');
        const betTypeBtn = target.closest('.bet-type-btn');
        const methodTabBtn = target.closest('.method-tab-btn');
        const calculateBtn = target.closest('#calculate-btn');
        const resetBtn = target.closest('#reset-btn');
        const horseSelectBtn = target.closest('.horse-select-btn');

        if (raceSelectBtn) {
            handleRaceSelection(raceSelectBtn);
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
        if (methodTabBtn) {
            handleMethodSelection(methodTabBtn);
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
    // Force reload if needed or check cache policy. 
    // Usually fetching from file:// or simple server might cache.
    // Adding timestamp query param.
    // Note: If using file:// protocol, query params might not work or be ignored, but worth a try.
    // If globalRaceData exists, maybe we should clear it if the user clicks "Load" again?
    // Current logic returns cached globalRaceData. 
    // If admin updates CSV, user has to refresh page.
    // Let's NOT return cached data if we assume the user wants fresh data on click?
    // But loadDatabase is called by loadPastRaces.
    // If we want fresh data, we should clear `window.globalRaceData` before calling or force reload.
    // For now, let's just bust cache on fetch.
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

    // Clear Global Cache to ensure fresh reload if button is clicked again?
    // window.globalRaceData = null; // Optional: Uncomment if we want "Load" to always fetch fresh.

    const year = document.getElementById('sim-year').value;
    const month = document.getElementById('sim-month').value;

    try {
        window.globalRaceData = null; // Force reload logic
        const data = await loadDatabase();

        // Filter by date
        const prefix = `${year}年${month}月`;
        const filtered = data.filter(row => row['日付'] && row['日付'].startsWith(prefix));

        console.log(`Filtering for ${prefix}: Found ${filtered.length} rows`);

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
                    number: parseInt(row['レース番号']) || 0,
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
            // Parse Japanese Date "YYYY年M月D日"
            const parseDate = (dStr) => {
                const match = dStr.match(/(\d+)年(\d+)月(\d+)日/);
                if (!match) return 0;
                return new Date(match[1], match[2] - 1, match[3]).getTime();
            };
            return parseDate(b) - parseDate(a); // Descending
        });

        console.log("Dates found:", dates);

        renderDateSelect(dates);

        // Auto-select first date
        if (dates.length > 0) {
            // Need to set select value manually if we auto-select
            // selectDate(dates[0]); // This updates logic
            // But UI dropdown needs to update too.
            // renderDateSelect creates options.
            // We should pick the first option.
            const select = document.getElementById('past-date-select');
            select.value = dates[0];
            selectDate(dates[0]);
        }

        document.getElementById('past-date-select-container').style.display = 'block';
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

// ==================== Venue & Date Rendering ====================

function renderDateSelect(dates) {
    const select = document.getElementById('past-date-select');
    select.innerHTML = '<option value="">日付を選択してください</option>';

    if (dates.length === 0) return;

    dates.forEach(date => {
        const option = document.createElement('option');
        option.value = date;
        option.textContent = date;
        select.appendChild(option);
    });
}

function handleDateChange(selectElement) {
    const selectedDate = selectElement.value;
    if (!selectedDate) {
        // Clear venues/races if needed
        document.getElementById('past-venue-tabs-container').style.display = 'none';
        return;
    }
    selectDate(selectedDate);
}

function selectDate(date) {
    selectedDatePast = date;
    console.log("Selected Date:", date);

    // Filter venues for this date
    const racesOnDate = pastRaceListCache.filter(r => r.date === date);
    const venues = [...new Set(racesOnDate.map(r => r.venue))]; // Assuming unique venues

    // Render Venue Tabs (Using existing logic, need to ensure container visibility)
    // Note: renderVenueTabs handles sorting/rendering
    renderVenueTabs('past', venues);

    // Auto-select first venue
    if (venues.length > 0) {
        selectVenue('past', venues[0]);
    }

    document.getElementById('past-venue-tabs-container').style.display = 'block';
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
// ==================== Betting Logic & Odds Approximation ====================

function getLocalBetTypeName(type) {
    const map = {
        'win': '単勝', 'place': '複勝',
        'quinella': '馬連', 'exacta': '馬単', 'wide': 'ワイド',
        'trio': '3連複', 'trifecta': '3連単'
    };
    return map[type] || type;
}

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
        // Use Netkeiba Scraping via Proxy for Past Race (Restored)
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
        // Attempt 1: odds_get_form.html (Live/Dynamic Odds)
        let url = `https://race.netkeiba.com/odds/odds_get_form.html?type=b1&race_id=${raceId}&rf=shutuba_submenu&_t=${new Date().getTime()}`;
        let data = await fetchNetkeiba(url);

        // Check if data is valid (has horses and at least one horse has non-zero odds)
        const hasValidOdds = data.horses && data.horses.length > 0 && data.horses.some(h => h.odds > 0);

        if (!hasValidOdds) {
            console.log("odds_get_form returned no odds (---). Falling back to shutuba.html");
            // Attempt 2: shutuba.html (Race Card / Static Odds)
            url = `https://race.netkeiba.com/race/shutuba.html?race_id=${raceId}&rf=race_submenu&_t=${new Date().getTime()}`;
            const fallbackData = await fetchNetkeiba(url);

            // Check if fallback1 worked
            const fallbackHasOdds = fallbackData.horses && fallbackData.horses.length > 0 && fallbackData.horses.some(h => h.odds > 0);

            if (!fallbackHasOdds) {
                console.log("shutuba.html returned no odds. Falling back to result.html");
                // Attempt 3: result.html (Race Result / Final Odds)
                url = `https://race.netkeiba.com/race/result.html?race_id=${raceId}&rf=race_submenu&_t=${new Date().getTime()}`;
                const resultData = await fetchNetkeiba(url);

                if (resultData.horses && resultData.horses.some(h => h.odds > 0)) {
                    console.log("Using result data from result.html");
                    data = resultData;
                } else {
                    // If result also fails, fallback to shutuba logic (at least has names)
                    data = fallbackData.horses.length > 0 ? fallbackData : data;
                }
            } else {
                console.log("Using fallback data from shutuba.html");
                data = fallbackData;
            }
        }

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
                <th>馬名</th>
                <th>単勝オッズ</th>
            </tr>
        </thead>
        <tbody>
            ${horsesData.map(h => `
                <tr>
                    <td>${h.number}</td>
                    <td>${h.name || '-'}</td>
                    <td>${h.odds > 0 ? h.odds.toFixed(1) : '---'}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    container.appendChild(table);
    document.getElementById('odds-display-section').style.display = 'block';
    document.getElementById('purchase-section').style.display = 'block';
}

function resetForm(keepRace = false) {
    if (!keepRace) {
        // Only clear race selection highlight if we are unselecting the race
        // But handleRaceSelection usually updates selectedRace BEFORE calling this with true?
        // Wait, logic check: usually resetForm is called to clear INPUTS when switching races.
        // If switching tabs, we might clear everything.
        // For now, minimal reset.
        document.querySelectorAll('.race-select-btn').forEach(b => b.classList.remove('active'));
        if (!selectedRace.id) { // Only hide if no race selected
            document.getElementById('common-betting-section').style.display = 'none';
        }
    }
    // Deep reset if not keeping race
    if (!keepRace) {
        selectedRace = { id: null, name: null, mode: null };
        horses = [];
        document.querySelectorAll('.bet-type-btn').forEach(btn => btn.classList.remove('active'));
        currentBetType = 'win';
        document.getElementById('common-betting-section').style.display = 'none';
    }

    document.getElementById('result-section').style.display = 'none';
    const betInput = document.getElementById('bet-amount');
    if (betInput) betInput.value = 100;

    document.getElementById('selection-area').innerHTML = '<p class="text-light">馬券種類を選択してください。</p>';
    document.getElementById('odds-display-area').innerHTML = '';
    document.getElementById('odds-display-section').style.display = 'none';
    document.getElementById('purchase-section').style.display = 'none';
}

// Utility for Public Proxy (CorsProxy.io) to bypass CORS
async function fetchViaPublicProxy(targetUrl) {
    // CorsProxy.io is a direct proxy
    const apiUrl = `https://corsproxy.io/?${encodeURIComponent(targetUrl)}`;
    console.log("Fetching via proxy:", apiUrl);
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);

        // Netkeiba uses EUC-JP encoding. 
        // response.text() defaults to UTF-8 resulting in mojibake.
        // We must decode manually from ArrayBuffer.
        const buffer = await response.arrayBuffer();
        const decoder = new TextDecoder('euc-jp');
        return decoder.decode(buffer);
    } catch (error) {
        console.error('Proxy Error:', error);
        throw error;
    }
}

// Re-implement handleBetTypeSelection
function handleBetTypeSelection(selectedBtn) {
    if (!selectedBtn) return;
    currentBetType = selectedBtn.dataset.type;
    console.log("Bet type selected:", currentBetType);

    // UI Update
    const parent = selectedBtn.parentElement;
    parent.querySelectorAll('.bet-type-btn').forEach(btn => btn.classList.remove('active'));
    selectedBtn.classList.add('active');

    // Reset Betting Method to 'normal' default
    currentBetMethod = 'normal';
    renderBettingMethodSelector();

    updateSelectionArea();
}

function renderBettingMethodSelector() {
    const container = document.getElementById('bet-method-container');
    const available = bettingMethods[currentBetType] || ['normal'];

    // Japanese labels
    const labels = {
        'normal': '通常',
        'box': 'ボックス',
        'nagashi': '流し',
        'formation': 'フォーメーション'
    };

    container.innerHTML = available.map(m => `
        <button class="method-tab-btn ${m === currentBetMethod ? 'active' : ''}" data-method="${m}">
            ${labels[m]}
        </button>
    `).join('');
}

function handleMethodSelection(btn) {
    if (!btn) return;
    const method = btn.dataset.method;

    // Update state
    currentBetMethod = method;

    // Update UI
    document.querySelectorAll('.method-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Clear selections when method changes (structure changes)
    selectedHorses = []; // Or specific reset depending on implementation
    document.querySelectorAll('.horse-select-btn').forEach(b => b.classList.remove('selected'));

    updateSelectionArea();
}


async function fetchNetkeiba(url) {
    const html = await fetchViaPublicProxy(url);
    console.log("Fetched HTML length:", html.length);
    if (html.length < 500) console.log("Short HTML content:", html);

    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const horses = [];


    // Selectors for various page types

    const sel1 = doc.querySelectorAll('#odds_tan_block table tr');
    const sel2 = doc.querySelectorAll('.RaceOdds_HorseList_Table tr');
    const sel3 = doc.querySelectorAll('.Shutuba_Table tr');
    const sel4 = doc.querySelectorAll('#All_Result_Table tr'); // New selector

    // Prioritize #odds_tan_block (Win Odds specific)
    let rows = sel1;
    if (rows.length === 0) rows = sel2;
    if (rows.length === 0) rows = sel3;
    if (rows.length === 0) rows = sel4; // New condition

    // Determine table type
    const isShutuba = doc.querySelector('.Shutuba_Table') !== null;
    const isResult = doc.querySelector('#All_Result_Table') !== null;
    console.log(`Table type: ${isResult ? 'Result Page' : (isShutuba ? 'Shutuba (Race Card)' : 'Odds Page')}`);

    rows.forEach((row, idx) => {
        let num, odds, name;
        // Try to find cells
        const cells = row.querySelectorAll('td');

        // Debug
        // let logMsg = `Row ${idx}: `;
        // const allExample = Array.from(cells).map((c, i) => `[${i}]="${c.textContent.trim()}"`).join(', ');
        // logMsg += ` AllCells: ${allExample}`;

        if (isResult) {
            // Result Page Logic
            // Rank: Col 1 (usually order of finish)
            let r = 0;
            if (cells.length > 0) {
                const txt = cells[0].textContent.trim();
                if (!isNaN(parseInt(txt))) r = parseInt(txt);
            }

            // Name: .Horse_Name or col 3
            const nameEl = row.querySelector('.Horse_Name');
            if (nameEl) name = nameEl.textContent.trim();
            else if (cells.length > 3) name = cells[3].textContent.trim();

            // Num: .Umaban or col 2
            const numEl = row.querySelector('.Umaban, div.Umaban');
            if (numEl) num = parseInt(numEl.textContent.trim());
            else if (cells.length > 2) {
                const n = parseInt(cells[2].textContent.trim());
                if (!isNaN(n)) num = n;
            }

            // Odds: .Odds or col 11 (approx)
            const oddsEl = row.querySelector('.Odds');
            if (oddsEl) {
                odds = parseFloat(oddsEl.textContent.trim());
            } else {
                Array.from(cells).forEach((c, cIdx) => {
                    if (cIdx > 8 && cIdx < 14) { // Check a range of columns where odds might appear
                        const txt = c.textContent.trim();
                        if (txt.match(/^\d+\.\d+$/)) { // Simple regex for decimal number
                            odds = parseFloat(txt);
                        }
                    }
                });
            }

            // Populate rank if valid
            if (num && !isNaN(num)) {
                // Check for duplicate
                if (!horses.find(h => h.number === num)) {
                    horses.push({ number: num, odds: (isNaN(odds) ? 0 : odds), name: name || `馬番${num}`, rank: r });
                }
            }
            return; // Skip other logic for Result page row
        } else if (isShutuba) {
            // Shutuba Page Logic
            // Name: .HorseName or .HorseInfo
            const nameEl = row.querySelector('.HorseName, .HorseInfo');
            if (nameEl) name = nameEl.textContent.trim();

            // Odds: .Odds_Tan or .Popular
            const numEl = row.querySelector('.Umaban, .Horse_Num');
            const oddsEl = row.querySelector('.Odds_Tan, .Popular');

            if (numEl) num = parseInt(numEl.textContent.trim());

            if (oddsEl) {
                const txt = oddsEl.textContent.trim();
                // console.log(`Shutuba Row ${idx}: Num=${num}, OddsTxt="${txt}"`); // Debug log
                odds = parseFloat(txt);
            }
        } else {
            // Odds Page Logic (Standard)
            // Strategy 1: Standard Odds Table (Col 2: HorseNum, Col 3: Name, Col 6: WinOdds)
            if (cells.length >= 6) {
                const n = parseInt(cells[1].textContent.trim());
                const o = parseFloat(cells[5].textContent.trim());

                // Name usually in col 3
                if (cells[2]) name = cells[2].textContent.trim();

                if (!isNaN(n)) {
                    num = n;
                    odds = o;
                }
            }
        }

        // Universal class fallback (Strategy 2) if specific logic failed
        if (!num) {
            const numEl = row.querySelector('.Umaban, .Horse_Num');
            if (numEl) num = parseInt(numEl.textContent.trim());
        }
        if (!name) {
            const nameEl = row.querySelector('.Horse_Name, .HorseName');
            if (nameEl) name = nameEl.textContent.trim();
        }
        if (num && (odds === undefined || isNaN(odds))) {
            const oddsEl = row.querySelector('.Odds_Tan, .Popular, .Odds');
            if (oddsEl) odds = parseFloat(oddsEl.textContent.trim());
        }

        if (num && !isNaN(num)) {
            // Check for duplicate
            if (!horses.find(h => h.number === num)) {
                // Handle "---" or invalid parsing
                horses.push({ number: num, odds: (isNaN(odds) ? 0 : odds), name: name || `馬番${num}` });
            }
        }
    });

    // console.log("Parsed horses:", horses.length);
    if (horses.length === 0) console.warn("No horses parsed! HTML snippet:", html.substring(0, 1000));

    return { horses: horses.sort((a, b) => a.number - b.number) };
}

// ==================== CSV Data Handling for Past Races ====================
function getHorsesFromCSV(raceId) {
    if (!window.globalRaceData || window.globalRaceData.length === 0) {
        console.warn("getHorsesFromCSV: globalRaceData is empty");
        return [];
    }

    // Debug: Check first row keys and raceId format
    const firstRow = window.globalRaceData[0];
    console.log("Debug Data Check:", {
        searchId: raceId,
        searchIdType: typeof raceId,
        firstRowId: firstRow['race_id'],
        firstRowIdType: typeof firstRow['race_id'],
        allKeys: Object.keys(firstRow)
    });

    // globalRaceData is an array of rows. Filter by race_id.
    // Ensure strict string comparison works by trimming and handling types
    const raceRows = window.globalRaceData.filter(row => {
        const rowId = String(row['race_id']).trim();
        const targetId = String(raceId).trim();
        return rowId === targetId;
    });
    console.log(`getHorsesFromCSV: Found ${raceRows.length} rows for race ${raceId}`);

    return raceRows.map(row => ({
        number: parseInt(row['馬 番']) || parseInt(row['馬番']) || 0, // Try generic variations
        name: row['馬名'],
        odds: parseFloat(row['単勝 オッズ']) || parseFloat(row['単勝']) || 0,
        rank: parseInt(row['着 順']) || parseInt(row['着順']) || 0
    })).sort((a, b) => a.number - b.number);
}

// ==================== UI Update Functions (Restored) ====================
function updateSelectionArea() {
    console.log("updateSelectionArea called. Method:", currentBetMethod);
    const selectionArea = document.getElementById('selection-area');

    if (horses.length === 0) {
        selectionArea.innerHTML = '<p class="text-light">オッズデータがありません。</p>';
        return;
    }

    const generateHtml = (labels) => {
        let html = '';
        const horseOptions = horses.map(h => {
            const oddsDisplay = h.odds > 0 ? `(${h.odds})` : '';
            return `<button class="horse-select-btn" data-horse="${h.number}">
                <span class="horse-num">${h.number}</span>
                <span class="horse-odds-sm">${oddsDisplay}</span>
            </button>`;
        }).join('');

        return labels.map((label, i) => `
            <div class="selection-group">
                <label>${label}</label>
                <div class="horse-select-grid" data-position="${i + 1}">
                    ${horseOptions}
                </div>
            </div>
        `).join('');
    };

    let html = '';

    // Layout Logic based on Method
    if (currentBetMethod === 'box') {
        html = generateHtml(['ボックス選択（複数選択可）']);
    }
    else if (currentBetMethod === 'nagashi') {
        html = generateHtml(['軸馬選択', '相手馬選択']);
    }
    else if (currentBetMethod === 'formation') {
        // Formation
        if (['trifecta', 'trio'].includes(currentBetType)) {
            html = generateHtml(['1頭目（1着）', '2頭目（2着）', '3頭目（3着）']);
        } else {
            html = generateHtml(['1頭目（1着）', '2頭目（2着）']);
        }
    }
    else {
        // Normal (Default)
        switch (currentBetType) {
            case 'win':
            case 'place':
                html = generateHtml(['馬選択']);
                break;
            case 'quinella':
            case 'wide':
                // Normal Quinella/Wide = Select 2 horses (unordered)
                // Usability: Single grid, select 2? Or 1st/2nd (redundant for unordered)?
                // JRA "Normal" = Select combinations.
                // Let's use Single Grid ("Mark 2") for unordered "Normal".
                html = generateHtml(['馬選択（2頭）']);
                break;
            case 'trio':
                html = generateHtml(['馬選択（3頭）']);
                break;
            case 'exacta':
                html = generateHtml(['1着', '2着']);
                break;
            case 'trifecta':
                html = generateHtml(['1着', '2着', '3着']);
                break;
        }
    }

    selectionArea.innerHTML = html;
}

function handleHorseSelection(selectedBtn) {
    if (!selectedBtn) return;

    // The UI generates separate grids for each position (1st, 2nd, etc.)
    // We enforce Single Selection per grid to match this "Formation/Position" style UI.
    const parentGrid = selectedBtn.parentElement;

    // Toggle selection if already selected
    if (selectedBtn.classList.contains('selected')) {
        selectedBtn.classList.remove('selected');
    } else {
        // Clear other selections in the same grid
        parentGrid.querySelectorAll('.horse-select-btn').forEach(btn => btn.classList.remove('selected'));
        // Select the clicked one
        selectedBtn.classList.add('selected');
    }

    // Optional: Check uniqueness across grids?
    // For now, allow selecting same horse in different grids (user might want to change selection order, validateInput handles logic)
}

// Calculate approximate odds based on Win odds
// Calculate approximate odds based on Win odds
function calculateEstimatedOdds(type, selectedHorses) {
    if (selectedHorses.length === 0) return 0;

    // Sort logic handled in caller? Assuming inputs are relevant horses
    const h1 = selectedHorses[0];
    const win1 = h1.odds;

    // Basic rules
    if (type === 'win') return win1;

    // Place: Win * 0.25 + 1.1 (Approx)
    if (type === 'place') {
        const est = win1 * 0.25 + 1.1;
        return parseFloat(est.toFixed(1));
    }

    // For Multi-horse bets
    if (selectedHorses.length < 2) return 0;
    const h2 = selectedHorses[1];
    const win2 = h2.odds;
    const sumWin = win1 + win2;

    if (type === 'quinella') return parseFloat((sumWin * 2.5).toFixed(1));
    if (type === 'exacta') return parseFloat((sumWin * 4.0).toFixed(1));
    if (type === 'wide') return parseFloat((sumWin * 0.8).toFixed(1));

    if (selectedHorses.length < 3) return 0;
    const h3 = selectedHorses[2];
    const sumWin3 = sumWin + h3.odds;

    if (type === 'trio') return parseFloat((sumWin3 * 6.0).toFixed(1));
    if (type === 'trifecta') return parseFloat((sumWin3 * 15.0).toFixed(1));

    return 0;
}

// ==================== Interaction Logic ====================
function handleHorseSelection(selectedBtn) {
    if (!selectedBtn) return;

    const parentGrid = selectedBtn.parentElement;
    const position = parseInt(parentGrid.dataset.position); // 1-based index

    // Selection Logic based on Method
    if (currentBetMethod === 'box' || currentBetMethod === 'formation') {
        // Multi-select allowed
        selectedBtn.classList.toggle('selected');
    }
    else if (currentBetMethod === 'nagashi') {
        // Nagashi: Grid 1 is Axis, Grid 2 is Opponent
        if (position === 1) {
            // Axis: Limit depending on bet type?
            // Usually Nagashi implies 1 Axis (or 2 for 3-Ren).
            // Simple implementation: Limit Grid 1 to 1 horse (Single Axis) for simplicity, or 2 for Trio/Trifecta?
            // Standard Nagashi is 1-Axis. "2-Axis Nagashi" is separate.
            // Let's enforce Single Axis for now.

            // Toggle off others
            parentGrid.querySelectorAll('.horse-select-btn').forEach(b => b.classList.remove('selected'));
            selectedBtn.classList.add('selected');
        } else {
            // Opponent: Multi-select
            selectedBtn.classList.toggle('selected');
        }
    }
    else {
        // Normal (Default): Single Select per Grid
        // (For Quinella Normal, allows just 1 pair? Yes, usually 1 combination per input)
        parentGrid.querySelectorAll('.horse-select-btn').forEach(b => b.classList.remove('selected'));
        selectedBtn.classList.add('selected');
    }
}

// ==================== Calculation & Simulation ====================
function calculatePayout() {
    const betAmount = parseInt(document.getElementById('bet-amount').value) || 100;

    // Gather selections by grid position
    const grids = document.querySelectorAll('.horse-select-grid');
    const selections = {}; // { 1: [ids], 2: [ids], 3: [ids] }

    grids.forEach(grid => {
        const pos = grid.dataset.position;
        const selected = Array.from(grid.querySelectorAll('.horse-select-btn.selected')).map(b => parseInt(b.dataset.horse));
        if (selected.length > 0) selections[pos] = selected;
    });

    // Validate
    if (Object.keys(selections).length === 0) {
        alert("馬を選択してください");
        return;
    }

    // Generate Combinations (Points)
    let combinations = [];

    try {
        combinations = generateCombinations(currentBetType, currentBetMethod, selections);
    } catch (e) {
        console.error(e);
        alert("組み合わせ計算エラー: " + e.message);
        return;
    }

    const points = combinations.length;
    const totalCost = points * betAmount;

    if (points === 0) {
        alert("有効な組み合わせがありません\n（選択数が不足しているか、重複があります）");
        return;
    }

    // Confirm Purchase
    const proceed = confirm(`【購入確認】\n賭け式: ${getLocalBetTypeName(currentBetType)} (${getLocalMethodName(currentBetMethod)})\n点数: ${points}点\n合計金額: ${totalCost.toLocaleString()}円\n\n購入（シミュレーション）しますか？`);

    if (!proceed) return;

    // Simulate Results
    simulateResults(combinations, betAmount, totalCost);
}

function getLocalMethodName(m) {
    const map = { 'normal': '通常', 'box': 'ボックス', 'nagashi': '流し', 'formation': 'フォーメーション' };
    return map[m] || m;
}

function generateCombinations(type, method, selections) {
    // Helper: Cartesian Product
    const cartesian = (...a) => a.reduce((a, b) => a.flatMap(d => b.map(e => [d, e].flat())));

    let combs = [];

    // --- Box ---
    if (method === 'box') {
        const sel = selections[1] || [];
        if (sel.length < 2) return [];
        // Combinations of r from n
        const k = (type === 'trio' || type === 'trifecta') ? 3 : 2;
        // Logic depends on type
        // Permutation (Exacta/Trifecta) vs Combination (Quinella/Wide/Trio)
        // Actually Box usually means "All Permutations" for Ordered types, "All Combinations" for Unordered.

        const isOrdered = ['exacta', 'trifecta'].includes(type);

        // Use helper to generate
        combs = getCombinations(sel, k); // Combinations
        if (isOrdered) {
            // Expand to Permutations
            combs = combs.flatMap(c => getPermutations(c));
        }
    }
    // --- Nagashi ---
    else if (method === 'nagashi') {
        const axis = selections[1] || [];
        const opps = selections[2] || [];

        if (axis.length === 0 || opps.length === 0) return [];
        const a = axis[0]; // Assume 1 axis

        // Nagashi Logic
        // Quinella/Wide: Axis - Opp match.
        // Exacta: Axis -> Opp (usually Fixed Axis 1st). 
        // Trio: Axis - Opp - Opp (Axis 1 head, select 2 from opps). Wait, Trio Nagashi 1-Axis means Axis is IN top 3.
        // Trifecta: Axis -> Opp -> Opp? Or Axis 1st fixed?
        // Standard "Nagashi" usually implies:
        // - Ordered Types (Exacta/Trifecta): Axis 1st Fixed. (Use "Multi" to vary).
        // - Unordered Types (Quinella/Wide/Trio): Axis included.

        // Simplified Nagashi Implementation:
        if (type === 'quinella' || type === 'wide' || type === 'exacta') {
            // Pair: Axis + 1 Opp
            opps.forEach(o => combs.push([a, o]));

            // For Exacta, strict order Axis -> Opp. (Unless Multi checked? Assuming standard).
        }
        else if (type === 'trio' || type === 'trifecta') {
            // 3-Horse: Axis + 2 Opps
            // Opps must have size >= 2
            const oppPairs = getCombinations(opps, 2);
            oppPairs.forEach(pair => combs.push([a, ...pair]));
        }
    }
    // --- Normal / Formation ---
    else {
        // Formation Logic (Cartesian product of positions)
        // Normal is just restricted Formation (Single sel per pos)
        const p1 = selections[1] || [];
        const p2 = selections[2] || [];
        let p3 = selections[3] || [];

        if (type === 'win' || type === 'place') {
            p1.forEach(h => combs.push([h]));
            return combs;
        }

        // Multi-leg
        if ((p1.length === 0 || p2.length === 0)) return [];
        if (['trio', 'trifecta'].includes(type) && p3.length === 0) return [];

        let candidates = [];
        if (['trio', 'trifecta'].includes(type)) {
            candidates = cartesian(p1, p2, p3); // [[1,2,3], [1,2,4]...]
        } else {
            candidates = cartesian(p1, p2); // [[1,2], [3,4]...]
        }

        // Filter Invalid (Duplicate horses in same comb)
        // e.g. 1-1 is invalid.
        combs = candidates.filter(c => new Set(c).size === c.length);

        // For Unordered types (Quinella/Wide/Trio), filter duplicates ignoring order?
        // e.g. 1-2 and 2-1 are same.
        // Formation generates permutations.
        // For Unordered, usually Formation implies "Position 1" "Position 2".
        // If I put 1 in P1 and 2 in P2 -> 1-2.
        // If I put 2 in P1 and 1 in P2 -> 2-1.
        // For Quinella, 1-2 and 2-1 are same bet. JRA Formation collapses duplicates.
        if (!['exacta', 'trifecta'].includes(type)) {
            const uniqueSet = new Set();
            const uniqueCombs = [];
            combs.forEach(c => {
                const key = [...c].sort((a, b) => a - b).join('-');
                if (!uniqueSet.has(key)) {
                    uniqueSet.add(key);
                    uniqueCombs.push(c);
                }
            });
            combs = uniqueCombs;
        }
    }

    return combs;
}

// Math Helpers
function getCombinations(options, k) {
    if (k === 1) return options.map(o => [o]);
    let result = [];
    for (let i = 0; i < options.length; i++) {
        const head = options[i];
        const tail = options.slice(i + 1);
        const tailCombs = getCombinations(tail, k - 1);
        tailCombs.forEach(tc => result.push([head, ...tc]));
    }
    return result;
}

function getPermutations(arr) {
    if (arr.length <= 1) return [arr];
    let result = [];
    for (let i = 0; i < arr.length; i++) {
        const curr = arr[i];
        const rem = [...arr.slice(0, i), ...arr.slice(i + 1)];
        const perms = getPermutations(rem);
        perms.forEach(p => result.push([curr, ...p]));
    }
    return result;
}

// Simulation
function simulateResults(combinations, betAmount, totalCost) {
    // Check Ranks
    const hasRank = horses.some(h => h.rank && h.rank > 0);
    if (!hasRank) {
        alert("レース結果データがありません（本日のレース等はシミュレーション不可）");
        return;
    }

    const ranks = horses.filter(h => h.rank > 0).sort((a, b) => a.rank - b.rank);
    const r1 = ranks[0] ? ranks[0].number : -1;
    const r2 = ranks[1] ? ranks[1].number : -1;
    const r3 = ranks[2] ? ranks[2].number : -1;

    let totalPayout = 0;
    let hitCount = 0;
    let hitDetails = [];

    combinations.forEach(comb => {
        let isWin = false;
        // Betting Type Logic
        if (currentBetType === 'win') isWin = (comb[0] === r1);
        else if (currentBetType === 'quinella') isWin = (comb.includes(r1) && comb.includes(r2));
        else if (currentBetType === 'exacta') isWin = (comb[0] === r1 && comb[1] === r2);
        else if (currentBetType === 'wide') {
            // Top 3 any pair
            const match1 = comb.includes(r1);
            const match2 = comb.includes(r2);
            const match3 = comb.includes(r3);
            if ((match1 && match2) || (match1 && match3) || (match2 && match3)) isWin = true;
        }
        else if (currentBetType === 'trio') isWin = (comb.includes(r1) && comb.includes(r2) && comb.includes(r3));
        else if (currentBetType === 'trifecta') isWin = (comb[0] === r1 && comb[1] === r2 && comb[2] === r3);

        if (isWin) {
            hitCount++;
            // Calculate Odds (Approx)
            // Need horse objects
            const hObjs = comb.map(n => horses.find(h => h.number === n));
            const odds = calculateEstimatedOdds(currentBetType, hObjs);
            totalPayout += Math.floor(betAmount * odds);
            hitDetails.push(`${comb.join('-')} (${odds}倍)`);
        }
    });

    // Result Alert
    const net = totalPayout - totalCost;
    let msg = hitCount > 0 ? `⭐️ 的中！ (${hitCount}点)` : "💔 外れ...";
    msg += `\n\n購入: ${totalCost.toLocaleString()}円\n払戻: ${totalPayout.toLocaleString()}円\n収支: ${net > 0 ? '+' : ''}${net.toLocaleString()}円`;

    if (hitCount > 0) {
        msg += `\n\n的中内訳:\n${hitDetails.join('\n')}`;
    }

    alert(msg);
}

function getSelectedHorses() {
    // Modified to preserve order based on grid position
    const selected = []; // Use array to preserve order
    const grids = document.querySelectorAll('.horse-select-grid');

    // Sort grids by position just in case
    const sortedGrids = Array.from(grids).sort((a, b) => parseInt(a.dataset.position) - parseInt(b.dataset.position));

    sortedGrids.forEach(grid => {
        const selectedButtons = grid.querySelectorAll('.horse-select-btn.selected');
        selectedButtons.forEach(btn => {
            selected.push(parseInt(btn.dataset.horse));
        });
    });

    // Only sort for non-ordered types? 
    // Win/Place/Quinella/Wide/Trio -> Order doesn't matter (usually box or ascending).
    // Exacta/Trifecta -> Order matters.
    const orderedTypes = ['exacta', 'trifecta'];
    if (!orderedTypes.includes(currentBetType)) {
        selected.sort((a, b) => a - b);
    }

    return selected;
}

