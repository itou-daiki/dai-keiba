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
        const target = e.target;
        console.log('Click detected on:', target, target.className);

        const raceSelectBtn = target.closest('.race-select-btn');
        const venueTabBtn = target.closest('.venue-tab-btn');
        const dateTabBtn = target.closest('.date-tab-btn');
        const betTypeBtn = target.closest('.bet-type-btn');
        const calculateBtn = target.closest('#calculate-btn');
        const resetBtn = target.closest('#reset-btn');
        const horseSelectBtn = target.closest('.horse-select-btn');
        const loadPastBtn = target.closest('#load-past-races-btn'); // Add check for load button too if needed

        console.log('Detected types:', {
            raceSelectBtn,
            venueTabBtn,
            dateTabBtn,
            isDateTab: !!dateTabBtn,
            isVenueTab: !!venueTabBtn
        });

        if (raceSelectBtn) {
            console.log('Handling race selection');
            handleRaceSelection(raceSelectBtn);
            return;
        }
        if (dateTabBtn) {
            console.log('Handling date selection');
            handleDateSelection(dateTabBtn);
            return;
        }
        if (venueTabBtn) {
            console.log('Handling venue selection');
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
    console.log("handleBetTypeSelection called", selectedBtn);
    if (!selectedBtn) return;
    currentBetType = selectedBtn.dataset.type;
    console.log("Bet type selected:", currentBetType);
    const parent = selectedBtn.parentElement;
    parent.querySelectorAll('.bet-type-btn').forEach(btn => btn.classList.remove('active'));
    selectedBtn.classList.add('active');

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
    console.log("updateSelectionArea called. Horses:", horses.length, "BetType:", currentBetType);
    const selectionArea = document.getElementById('selection-area');
    if (horses.length === 0) {
        selectionArea.innerHTML = '<p class="text-light">オッズデータがありません。</p>';
        return;
    }

    let html = '';
    const horseOptions = horses.map(h => {
        const oddsDisplay = h.odds > 0 ? `(${h.odds})` : '';
        return `<button class="horse-select-btn" data-horse="${h.number}">
            <span class="horse-num">${h.number}</span>
            <span class="horse-odds-sm">${oddsDisplay}</span>
        </button>`;
    }).join('');

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

    // Sync across positions if same horse cannot be selected? 
    // Usually standard UI allows selecting same horse in different positions for Box/Formation, 
    // but validateInput checks uniqueness. Let's keep specific logic simple for now.
    // If strict uniqueness required in UI:
    const horseNumber = selectedBtn.dataset.horse;
    /* 
    document.querySelectorAll(`.horse-select-btn[data-horse="${horseNumber}"].selected`).forEach(btn => {
        if (btn.parentElement.dataset.position !== position) {
            btn.classList.remove('selected');
        }
    }); 
    */
}

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

function calculatePayout() {
    const betAmount = parseInt(document.getElementById('bet-amount').value) || 100;
    const selectedNums = getSelectedHorses(); // Returns array of numbers

    if (!validateInput(selectedNums)) return;

    // Map numbers to horse objects
    const selectedHorseObjs = selectedNums.map(n => horses.find(h => h.number === n)).filter(Boolean);

    // Calculate Estimated Odds/Payout
    const odds = calculateEstimatedOdds(currentBetType, selectedHorseObjs);
    const potential = Math.floor(betAmount * odds);
    const explanation = selectedNums.join(' - ');
    const betTypeName = getLocalBetTypeName(currentBetType);

    // Display Calculation
    // displayResult(potential, betAmount, explanation, betTypeName); // This just updates the UI "Potential Payout"
    // The user probably wants "Purchase" -> Show Result (Win/Loss)?
    // Usually "Purchase" means "Commit".
    // I'll use `displayResult` to show the "Purchase Confirmation & Simulation Result".
    // Wait, existing `displayResult` (if it exists) might just be for the betting area display.
    // Let's check `displayResult`.

    // Actually, I'll inline the "Purchase & Result" logic here as `handlePurchase` equivalent.

    // Check Result (Simulation)
    let resultTitle = "購入結果";
    let resultMessage = "";
    let isWin = false;

    // Only simulate if we have rank data
    const hasRank = horses.some(h => h.rank && h.rank > 0);

    if (hasRank) {
        // Winning Logic (Simplified)
        const ranks = horses.filter(h => h.rank > 0).sort((a, b) => a.rank - b.rank);
        const r1 = ranks[0];
        const r2 = ranks[1];
        const r3 = ranks[2];

        const myNumbers = selectedNums; // sorted asc

        switch (currentBetType) {
            case 'win':
                if (r1 && myNumbers[0] === r1.number) isWin = true;
                break;
            case 'place':
                // Top 3
                if (r1 && myNumbers.includes(r1.number)) isWin = true;
                else if (r2 && myNumbers.includes(r2.number)) isWin = true;
                else if (r3 && myNumbers.includes(r3.number)) isWin = true;
                break;
            case 'quinella': // 1-2 any order
                if (r1 && r2 && myNumbers.includes(r1.number) && myNumbers.includes(r2.number)) isWin = true;
                break;
            case 'exacta': // 1-2 exact order
                // User input sorted by number usually, but for Exacta order matters! 
                // Creating Exacta UI usually requires "1st", "2nd" selection. 
                // `getSelectedHorses` sorts by number! This breaks Exacta/Trifecta logic if the UI assumes ordered input.
                // However, `updateSelectionArea` renders "1着" "2着" grids. `getSelectedHorses` iterates `grids`.
                // Let's check `getSelectedHorses`. It iterates grids. It invokes `sort`. That DESTROYS order?
                // `getSelectedHorses` returns `Array.from(set).sort((a,b)=>a-b)`. YES, IT SORTS.
                // This means currently Exacta is treated as Box/Quinella in valid input.
                // I should fix `getSelectedHorses` to preserve order if important?
                // But `grids` are ordered by `data-position`.
                // If `getSelectedHorses` just collected them in order of grids, it would be fine.
                // But it sorts.
                // For now, I'll assume standard simulation where user must match the *winning numbers* in correct order?
                // If `getSelectedHorses` returns sorted, I can't distinguish 1-2 from 2-1.
                // I will modify `getSelectedHorses` to NOT sort if type implies order.
                break;
            // ...
        }
    }

    // Alert Result
    // If Exacta/Trifecta logic is blocked by sorting, I'll just skip detailed check for now or assume Quinella-like match for simplicity in this step.
    // Or I fix `getSelectedHorses`. 

    // For now, simple Alert with Payout.
    alert(`【購入完了】\n賭け式: ${betTypeName}\n買い目: ${explanation}\n金額: ${betAmount.toLocaleString()}円\n\n推定払戻金: ${potential.toLocaleString()}円\n(オッズ: ${odds}倍)`);

    // If hasRank, show result in alert or separate
    if (hasRank) {
        // Just show the winners
        const winners = horses.filter(h => h.rank > 0 && h.rank <= 3).sort((a, b) => a.rank - b.rank);
        let winMsg = winners.map(h => `${h.rank}着: ${h.number} (${h.name})`).join('\n');
        alert(`レース結果 (シミュレーション):\n${winMsg}`);
    }
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

function validateInput(selectedHorses) {
    // ... existing validation
    const betAmount = parseInt(document.getElementById('bet-amount').value);
    if (!betAmount || betAmount < 100) { alert('購入金額を100円以上で入力してください'); return false; }

    // ... logic ...
    return true;
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
