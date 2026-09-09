// Tab switching functionality
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.getAttribute('data-tab');
        switchTab(tabName, btn);
    });
});

function switchTab(tabName, btn) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    btn.classList.add('active');
    
    // Load data based on tab
    if (tabName === 'dashboard') {
        loadAircraftData();
    } else if (tabName === 'active') {
        loadActiveAircraft();
    } else if (tabName === 'scheduled') {
        loadScheduledToday();
    } else if (tabName === 'logs') {
        loadLogs();
    } else if (tabName === 'stats') {
        loadStatistics();
    } else if (tabName === 'update') {
        populateAircraftSelect();
    }
}

// Parse a response as JSON, surfacing a readable error when the server returns an HTML page
async function parseJsonResponse(response) {
    const text = await response.text();
    try {
        return JSON.parse(text);
    } catch (e) {
        if (text.trim().startsWith('<')) {
            throw new Error(`Server returned an HTML page instead of JSON (HTTP ${response.status}). Restart the Flask server so the API routes load.`);
        }
        throw new Error(`Invalid response from server (HTTP ${response.status}).`);
    }
}

// Health check
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        if (response.ok && data.status === 'success') {
            document.getElementById('healthStatus').textContent = '✅ Healthy';
            document.getElementById('healthStatus').className = 'healthy';
        } else {
            throw new Error('Health check failed');
        }
    } catch (error) {
        // Fallback: check if API is working
        try {
            const apiResponse = await fetch('/api/aircraft');
            if (apiResponse.ok) {
                document.getElementById('healthStatus').textContent = '✅ Healthy';
                document.getElementById('healthStatus').className = 'healthy';
            } else {
                throw new Error('API check failed');
            }
        } catch (apiError) {
            console.error('Health check error:', error);
            document.getElementById('healthStatus').textContent = '❌ Unhealthy';
            document.getElementById('healthStatus').className = 'unhealthy';
        }
    }
}

// Fetch aircraft data from the server
async function loadAircraftData() {
    try {
        const response = await fetch('/api/aircraft');
        const data = await response.json();
        displayAircraftTable(data);
        updateLastRefreshTime();
    } catch (error) {
        console.error('Error loading aircraft data:', error);
        document.getElementById('aircraftTable').innerHTML = 
            '<tr class="loading"><td colspan="6">❌ Error loading data. Please try again.</td></tr>';
    }
}

// Display aircraft data in the table
function displayAircraftTable(aircraft) {
    const tableBody = document.getElementById('aircraftTable');
    
    if (aircraft.length === 0) {
        tableBody.innerHTML = '<tr class="loading"><td colspan="6">No aircraft records found.</td></tr>';
        return;
    }

    tableBody.innerHTML = aircraft.map(plane => `
        <tr>
            <td><strong>${plane.aircraft_id}</strong></td>
            <td>${plane.name}</td>
            <td><span class="status ${getStatusClass(plane.status)}">${plane.status}</span></td>
            <td>${plane.maintenance_date}</td>
            <td>${plane.engineer_name}</td>
            <td>
                <button class="btn btn-danger" onclick="deleteAircraftFromTable('${plane.aircraft_id}')"><svg viewBox="0 0 24 24"><path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>Delete</button>
            </td>
        </tr>
    `).join('');
}

// Get CSS class based on status
function getStatusClass(status) {
    const statusMap = {
        'Scheduled': 'scheduled',
        'In Progress': 'in-progress',
        'Completed': 'completed'
    };
    return statusMap[status] || '';
}

// Update last refresh time
function updateLastRefreshTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    document.getElementById('lastUpdate').textContent = `Last updated: ${timeString}`;
}

// Load active aircraft (In Progress)
async function loadActiveAircraft() {
    try {
        const response = await fetch('/api/aircraft/active');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayActiveAircraft(data.aircraft, data.count);
        } else {
            showTabError('activeTable', data.error || 'Error loading active aircraft');
        }
    } catch (error) {
        console.error('Error loading active aircraft:', error);
        showTabError('activeTable', 'Error loading active aircraft');
    }
}

function displayActiveAircraft(aircraft, count) {
    const tableBody = document.getElementById('activeTable');
    document.getElementById('activeCount').innerHTML = `
        <strong>Aircraft in Maintenance:</strong> ${count} aircraft currently being serviced
    `;
    
    if (aircraft.length === 0) {
        tableBody.innerHTML = '<tr class="loading"><td colspan="5">No aircraft currently in maintenance. ✅</td></tr>';
        return;
    }

    tableBody.innerHTML = aircraft.map(plane => `
        <tr>
            <td><strong>${plane.aircraft_id}</strong></td>
            <td>${plane.name}</td>
            <td><span class="status ${getStatusClass(plane.status)}">${plane.status}</span></td>
            <td>${plane.maintenance_date}</td>
            <td>${plane.engineer_name}</td>
        </tr>
    `).join('');
}

// Load scheduled for today
async function loadScheduledToday() {
    try {
        const response = await fetch('/api/aircraft/scheduled-today');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayScheduledToday(data.aircraft, data.count, data.date);
        } else {
            showTabError('scheduledTable', data.error || 'Error loading scheduled aircraft');
        }
    } catch (error) {
        console.error('Error loading scheduled aircraft:', error);
        showTabError('scheduledTable', 'Error loading scheduled aircraft');
    }
}

function displayScheduledToday(aircraft, count, date) {
    const tableBody = document.getElementById('scheduledTable');
    const today = new Date().toISOString().split('T')[0];
    
    document.getElementById('scheduledCount').innerHTML = `
        <strong>Scheduled for ${date}:</strong> ${count} aircraft scheduled today
    `;
    
    if (aircraft.length === 0) {
        tableBody.innerHTML = '<tr class="loading"><td colspan="5">No aircraft scheduled for today.</td></tr>';
        return;
    }

    tableBody.innerHTML = aircraft.map(plane => `
        <tr>
            <td><strong>${plane.aircraft_id}</strong></td>
            <td>${plane.name}</td>
            <td><span class="status ${getStatusClass(plane.status)}">${plane.status}</span></td>
            <td>${plane.maintenance_date}</td>
            <td>${plane.engineer_name}</td>
        </tr>
    `).join('');
}

// Load and display logs
async function loadLogs() {
    try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayLogs(data.logs);
            populateLogFilter(data.logs);
        } else {
            showTabError('logsTable', data.error || 'Error loading logs');
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        showTabError('logsTable', 'Error loading logs');
    }
}

function displayLogs(logs) {
    const logsDiv = document.getElementById('logsTable');
    
    if (logs.length === 0) {
        logsDiv.innerHTML = '<div class="loading">No activity logs yet.</div>';
        return;
    }

    // Sort logs by timestamp (newest first)
    const sortedLogs = logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    logsDiv.innerHTML = sortedLogs.map(log => {
        const date = new Date(log.timestamp);
        const formattedTime = date.toLocaleString();
        const actionClass = log.action.toLowerCase().replace('_', '-');
        
        let actionDisplay = log.action.replace(/_/g, ' ');
        let detailsHtml = '';
        
        if (log.action === 'STATUS_UPDATED') {
            detailsHtml = `
                <div class="log-details">
                    <strong>${log.details.previous_status}</strong> → <strong>${log.details.new_status}</strong> 
                    <br>Aircraft: ${log.details.aircraft_name} (${log.details.engineer})
                </div>
            `;
        } else if (log.action === 'AIRCRAFT_REGISTERED') {
            detailsHtml = `
                <div class="log-details">
                    Aircraft: ${log.details.name} <br>
                    Initial Status: ${log.details.initial_status} <br>
                    Engineer: ${log.details.engineer}
                </div>
            `;
        } else if (log.action === 'AIRCRAFT_DELETED') {
            detailsHtml = `
                <div class="log-details">
                    Aircraft: ${log.details.name} (${log.details.status}) <br>
                    Engineer: ${log.details.engineer}
                </div>
            `;
        }
        
        return `
            <div class="log-entry ${actionClass}">
                <div class="log-timestamp">📅 ${formattedTime}</div>
                <div class="log-action">✈️ ${actionDisplay} - ${log.aircraft_id}</div>
                ${detailsHtml}
            </div>
        `;
    }).join('');
}

function populateLogFilter(logs) {
    const filterSelect = document.getElementById('logFilterAircraft');
    const aircraftIds = [...new Set(logs.map(log => log.aircraft_id))];
    
    aircraftIds.forEach(id => {
        if (!Array.from(filterSelect.options).some(opt => opt.value === id)) {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = id;
            filterSelect.appendChild(option);
        }
    });
    
    filterSelect.addEventListener('change', async (e) => {
        if (e.target.value) {
            try {
                const response = await fetch(`/api/logs/${e.target.value}`);
                const data = await response.json();
                if (data.status === 'success') {
                    displayLogs(data.logs);
                }
            } catch (error) {
                console.error('Error filtering logs:', error);
            }
        } else {
            loadLogs();
        }
    });
}

// Load and display statistics
async function loadStatistics() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayStatistics(data.statistics);
        } else {
            showTabError('stats', data.error || 'Error loading statistics');
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
        showTabError('stats', 'Error loading statistics');
    }
}

function displayStatistics(stats) {
    document.getElementById('statTotal').textContent = stats.total_aircraft;
    document.getElementById('statScheduled').textContent = stats.scheduled;
    document.getElementById('statInProgress').textContent = stats.in_progress;
    document.getElementById('statCompleted').textContent = stats.completed;
    document.getElementById('statStatusChanges').textContent = stats.total_status_changes;
    document.getElementById('statLogEntries').textContent = stats.total_log_entries;
    
    // Update progress chart
    const total = stats.total_aircraft;
    if (total > 0) {
        const scheduledPct = (stats.scheduled / total) * 100;
        const inProgressPct = (stats.in_progress / total) * 100;
        const completedPct = (stats.completed / total) * 100;
        
        document.getElementById('barScheduled').style.width = scheduledPct + '%';
        document.getElementById('barInProgress').style.width = inProgressPct + '%';
        document.getElementById('barCompleted').style.width = completedPct + '%';
    }
}

// Delete aircraft
async function deleteAircraftFromTable(aircraftId) {
    if (!confirm(`Are you sure you want to delete ${aircraftId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/aircraft/${aircraftId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (response.ok && data.status === 'success') {
            showMessage('✅ ' + data.message, 'success', 'dashboard');
            loadAircraftData();
        } else {
            showMessage('❌ ' + (data.error || 'Error deleting aircraft'), 'error', 'dashboard');
        }
    } catch (error) {
        console.error('Error deleting aircraft:', error);
        showMessage('❌ Error deleting aircraft: ' + error.message, 'error', 'dashboard');
    }
}

// Aircraft Registration Form
document.getElementById('aircraftForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        aircraft_id: document.getElementById('aircraftId').value.trim(),
        name: document.getElementById('aircraftName').value.trim(),
        maintenance_date: document.getElementById('maintenanceDate').value,
        engineer_name: document.getElementById('engineerName').value.trim()
    };
    
    try {
        const response = await fetch('/api/aircraft', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await parseJsonResponse(response);
        
        if (response.ok && data.status === 'success') {
            showMessage(`✅ ${data.message}`, 'success', 'register');
            document.getElementById('aircraftForm').reset();
            // Refresh the dashboard
            setTimeout(() => loadAircraftData(), 500);
        } else {
            showMessage(`❌ ${data.error || 'Error registering aircraft'}`, 'error', 'register');
        }
    } catch (error) {
        console.error('Error adding aircraft:', error);
        showMessage('❌ Error: ' + error.message, 'error', 'register');
    }
});

// Populate aircraft select dropdown
async function populateAircraftSelect() {
    try {
        const response = await fetch('/api/aircraft');
        const aircraft = await response.json();
        const select = document.getElementById('aircraftSelect');
        
        select.innerHTML = '<option value="">-- Choose an aircraft --</option>';
        
        aircraft.forEach(plane => {
            const option = document.createElement('option');
            option.value = plane.aircraft_id;
            option.textContent = `${plane.aircraft_id} - ${plane.name} (${plane.status})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error populating aircraft select:', error);
    }
}

// Aircraft Select change event
document.getElementById('aircraftSelect').addEventListener('change', async (e) => {
    const aircraftId = e.target.value;
    
    if (!aircraftId) {
        document.getElementById('currentStatus').value = '';
        document.getElementById('nextStatus').value = '';
        return;
    }
    
    try {
        const response = await fetch('/api/aircraft');
        const aircraft = await response.json();
        const selected = aircraft.find(a => a.aircraft_id === aircraftId);
        
        if (selected) {
            document.getElementById('currentStatus').value = selected.status;
            
            // Determine next status based on current status
            const statusOrder = {
                'Scheduled': 'In Progress',
                'In Progress': 'Completed',
                'Completed': 'No further updates'
            };
            
            document.getElementById('nextStatus').value = statusOrder[selected.status] || 'Unknown';
        }
    } catch (error) {
        console.error('Error fetching aircraft details:', error);
    }
});

// Update Status Form
document.getElementById('statusForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const aircraftId = document.getElementById('aircraftSelect').value;
    const currentStatus = document.getElementById('currentStatus').value;
    
    if (!aircraftId) {
        showMessage('❌ Please select an aircraft', 'error', 'update');
        return;
    }
    
    if (currentStatus === 'Completed') {
        showMessage('❌ Aircraft is already at final status (Completed). No further updates possible.', 'error', 'update');
        return;
    }
    
    try {
        const response = await fetch(`/api/aircraft/${aircraftId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await parseJsonResponse(response);
        
        if (response.ok && data.status === 'success') {
            showMessage(`✅ Status updated: ${data.old_status} → ${data.new_status}`, 'success', 'update');
            // Reset form and refresh
            document.getElementById('statusForm').reset();
            document.getElementById('currentStatus').value = '';
            document.getElementById('nextStatus').value = '';
            setTimeout(() => {
                populateAircraftSelect();
                loadAircraftData();
            }, 500);
        } else {
            showMessage(`❌ ${data.error || 'Error updating status'}`, 'error', 'update');
        }
    } catch (error) {
        console.error('Error updating status:', error);
        showMessage('❌ Error: ' + error.message, 'error', 'update');
    }
});

// Show message in the appropriate tab
function showMessage(message, type, tabId) {
    let messageElement;
    if (tabId === 'register') {
        messageElement = document.getElementById('registerMessage');
    } else if (tabId === 'update') {
        messageElement = document.getElementById('statusMessage');
    } else {
        return; // No message element for other tabs
    }
    
    messageElement.textContent = message;
    messageElement.className = `message ${type}`;
    
    // Auto-hide message after 5 seconds
    setTimeout(() => {
        messageElement.className = 'message';
        messageElement.textContent = '';
    }, 5000);
}

// Show error in tab
function showTabError(elementId, errorMessage) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<tr class="loading"><td colspan="6">❌ ${errorMessage}</td></tr>`;
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    // Check health
    checkHealth();
    setInterval(checkHealth, 10000); // Check every 10 seconds
    
    // Load data immediately
    loadAircraftData();

    // Refresh every 5 seconds (dashboard only)
    setInterval(() => {
        if (document.getElementById('dashboard').classList.contains('active')) {
            loadAircraftData();
        }
    }, 5000);

    // Manual refresh button
    document.getElementById('refreshBtn').addEventListener('click', loadAircraftData);
    
    // Active Aircraft refresh
    if (document.getElementById('refreshActiveBtn')) {
        document.getElementById('refreshActiveBtn').addEventListener('click', loadActiveAircraft);
    }
    
    // Scheduled Today refresh
    if (document.getElementById('refreshScheduledBtn')) {
        document.getElementById('refreshScheduledBtn').addEventListener('click', loadScheduledToday);
    }
    
    // Logs refresh
    if (document.getElementById('refreshLogsBtn')) {
        document.getElementById('refreshLogsBtn').addEventListener('click', loadLogs);
    }
    
    // Stats refresh
    if (document.getElementById('refreshStatsBtn')) {
        document.getElementById('refreshStatsBtn').addEventListener('click', loadStatistics);
    }
});

