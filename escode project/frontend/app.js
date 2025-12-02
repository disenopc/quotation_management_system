const API_URL = 'http://localhost:5001';

// State
let currentUser = null;
let currentTab = 'inquiries';
let currentPage = 1;
let currentResponsesPage = 1;
let selectedPublishers = new Set();

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const isDashboard = document.getElementById('currentUser') !== null;

    if (isDashboard) {
        checkAuth();
        setupEventListeners();
        
        // License form event listener
        const licenseForm = document.getElementById('licenseForm');
        if (licenseForm) {
            licenseForm.addEventListener('submit', createLicense);
        }
        
        // License status filter
        const licenseStatusFilter = document.getElementById('licenseStatusFilter');
        if (licenseStatusFilter) {
            licenseStatusFilter.addEventListener('change', (e) => {
                loadLicenses(1, e.target.value);
            });
        }
    }
});

// Authentication
async function checkAuth() {
    try {
        const response = await fetch(`${API_URL}/api/auth/check`, {
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            currentUser = data.user;
            document.getElementById('currentUser').textContent = currentUser.full_name;
            loadDashboard();
        } else {
            window.location.href = '/login.html';
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
    }
}

async function logout() {
    try {
        await fetch(`${API_URL}/api/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        window.location.href = '/login.html';
    } catch (error) {
        console.error('Logout failed:', error);
    }
}

// Event Listeners
function setupEventListeners() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            switchTab(item.dataset.tab);
        });
    });

    const syncBtn = document.getElementById('syncEmailsBtn');
    if (syncBtn) {
        syncBtn.addEventListener('click', syncEmails);
    }

    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            currentPage = 1;
            loadInquiries(e.target.value);
        });
    }

    let clientSearchTimeout;
    const clientSearch = document.getElementById('clientSearch');
    if (clientSearch) {
        clientSearch.addEventListener('input', (e) => {
            clearTimeout(clientSearchTimeout);
            clientSearchTimeout = setTimeout(() => {
                searchClients(e.target.value);
            }, 500);
        });
    }

    const addClientBtn = document.getElementById('addClientBtn');
    if (addClientBtn) {
        addClientBtn.addEventListener('click', () => {
            openModal('clientModal');
        });
    }

    const editClientForm = document.getElementById('editClientForm');
    if (editClientForm) {
        editClientForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const clientId = document.getElementById('editClientId').value;
            const data = {
                full_name: document.getElementById('editClientFullName').value,
                email: document.getElementById('editClientEmail').value,
                phone: document.getElementById('editClientPhone').value,
                company: document.getElementById('editClientCompany').value,
                notes: document.getElementById('editClientNotes').value
            };

            try {
                const response = await fetch(`${API_URL}/api/clients/${clientId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    alert('Client updated successfully!');
                    closeModal('editClientModal');
                    loadClients();
                } else {
                    alert('Error updating client');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error updating client');
            }
        });
    }

    const addClientForm = document.getElementById('addClientForm');
    if (addClientForm) {
        addClientForm.addEventListener('submit', createClient);
    }

    const responseForm = document.getElementById('responseForm');
    if (responseForm) {
        responseForm.addEventListener('submit', sendResponse);
    }

    const aiGenerateBtn = document.getElementById('aiGenerateBtn');
    if (aiGenerateBtn) {
        aiGenerateBtn.addEventListener('click', generateAIResponse);
    }

    let publisherSearchTimeout;
    const publisherSearch = document.getElementById('publisherSearch');
    if (publisherSearch) {
        publisherSearch.addEventListener('input', (e) => {
            clearTimeout(publisherSearchTimeout);
            publisherSearchTimeout = setTimeout(() => {
                searchPublishers(e.target.value);
            }, 500);
        });
    }

    const importPublishersBtn = document.getElementById('importPublishersBtn');
    if (importPublishersBtn) {
        importPublishersBtn.addEventListener('click', () => {
            alert('To import publishers, create a JSON file and send it to POST /api/publishers/bulk-import');
        });
    }

    const bulkEmailBtn = document.getElementById('bulkEmailBtn');
    if (bulkEmailBtn) {
        bulkEmailBtn.addEventListener('click', () => {
            if (selectedPublishers.size === 0) {
                alert('Please select publishers first');
                return;
            }
            openModal('bulkEmailModal');
            document.getElementById('selectedCount').textContent = selectedPublishers.size;
        });
    }

    const bulkEmailForm = document.getElementById('bulkEmailForm');
    if (bulkEmailForm) {
        bulkEmailForm.addEventListener('submit', sendBulkEmail);
    }

    const selectAllPublishers = document.getElementById('selectAllPublishers');
    if (selectAllPublishers) {
        selectAllPublishers.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.publisher-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
                if (e.target.checked) {
                    selectedPublishers.add(cb.dataset.email);
                } else {
                    selectedPublishers.delete(cb.dataset.email);
                }
            });
        });
    }

    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal(btn.closest('.modal').id);
        });
    });

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

// Tab Switching
function switchTab(tabName) {
    currentTab = tabName;
    currentPage = 1;

    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');

    const titles = {
        'inquiries': 'Inquiries',
        'clients': 'Clients',
        'responses': 'Send Response',
        'publishers': 'Publishers',
        'licenses': 'Licenses'
    };
    document.getElementById('pageTitle').textContent = titles[tabName];

    loadTabData(tabName);
}

function loadDashboard() {
    loadInquiries();
    loadInquiryStats();
    checkExpiringLicenses();
}

function loadTabData(tabName) {
    switch (tabName) {
        case 'inquiries':
            loadInquiries();
            break;
        case 'clients':
            loadClients();
            break;
        case 'responses':
            loadInquiriesForResponse();
            setTimeout(() => {
                if (document.getElementById('responsesTableBody')) {
                    loadResponses();
                }
            }, 100);
            break;
        case 'publishers':
            loadPublishers();
            loadPublisherCount();
            break;
        case 'licenses':
            loadLicenses();
            loadLicenseStats();
            break;
    }
}

// Inquiries
async function loadInquiries(status = '') {
    try {
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 50
        });

        if (status) params.append('status', status);

        const response = await fetch(`${API_URL}/api/inquiries?${params}`, {
            credentials: 'include'
        });

        const data = await response.json();
        renderInquiries(data.data);
        renderPagination('inquiriesPagination', data);
    } catch (error) {
        console.error('Error loading inquiries:', error);
    }
}

function renderInquiries(inquiries) {
    const tbody = document.querySelector('#inquiriesTab tbody');
    tbody.innerHTML = '';

    inquiries.forEach(inquiry => {
        const statusIcon = getStatusIcon(inquiry.status);

        const row = `
            <tr>
                <td style="text-align: center; font-size: 24px;">${statusIcon}</td>
                <td>${inquiry.id}</td>
                <td>${inquiry.client_name || 'Unknown'}</td>
                <td>${inquiry.subject || 'No subject'}</td>
                <td><span class="status-badge status-${inquiry.status}">${inquiry.status}</span></td>
                <td>${new Date(inquiry.received_at).toLocaleDateString()}</td>
                <td>
                    <button class="action-btn" onclick="viewInquiry(${inquiry.id})">View</button>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function getStatusIcon(status) {
    const icons = {
        'pending': '<img src="https://cdn-icons-png.flaticon.com/512/7887/7887122.png" width="24" height="24" alt="pending">',
        'in_progress': '<img src="https://cdn-icons-png.flaticon.com/512/5578/5578703.png" width="24" height="24" alt="in progress">',
        'responded': '<img src="https://cdn-icons-png.flaticon.com/512/190/190411.png" width="24" height="24" alt="responded">',
        'closed': '<img src="https://cdn-icons-png.flaticon.com/512/463/463612.png" width="24" height="24" alt="closed">'
    };
    return icons[status] || '';
}

async function viewInquiry(id) {
    try {
        const response = await fetch(`${API_URL}/api/inquiries/${id}`, {
            credentials: 'include'
        });

        const inquiry = await response.json();

        document.getElementById('inquiryDetails').innerHTML = `
            <div class="inquiry-detail">
                <p><strong>From:</strong> ${inquiry.client_name} (${inquiry.client_email})</p>
                <p><strong>Subject:</strong> ${inquiry.subject}</p>
                <p><strong>Received:</strong> ${formatDate(inquiry.received_at)}</p>
                <p><strong>Status:</strong> <span class="status-badge status-${inquiry.status}">${inquiry.status}</span></p>
                <div style="margin-top: 20px;">
                    <strong>Message:</strong>
                    <div style="background: #f8fafc; padding: 16px; border-radius: 6px; margin-top: 8px; white-space: pre-wrap;">
                        ${inquiry.message}
                    </div>
                </div>
            </div>
        `;

        openModal('inquiryModal');
    } catch (error) {
        console.error('Error loading inquiry:', error);
    }
}

function respondToInquiry(id) {
    switchTab('responses');
    document.getElementById('inquirySelect').value = id;
}

async function loadInquiryStats() {
    try {
        const response = await fetch(`${API_URL}/api/inquiries/stats`, {
            credentials: 'include'
        });

        const stats = await response.json();
        document.getElementById('pendingBadge').textContent = stats.pending || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function syncEmails() {
    const btn = document.getElementById('syncEmailsBtn');
    btn.disabled = true;
    btn.textContent = 'Syncing...';

    try {
        const response = await fetch(`${API_URL}/api/email/sync`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (data.success) {
            alert(`Synced ${data.count} new emails`);
            loadInquiries();
            loadInquiryStats();
        } else {
            alert('Sync failed: ' + data.error);
        }
    } catch (error) {
        console.error('Sync error:', error);
        alert('Sync failed. Check console for details.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Sync Emails';
    }
}

// Clients
async function loadClients() {
    try {
        const response = await fetch(`${API_URL}/api/clients?page=${currentPage}`, {
            credentials: 'include'
        });

        const data = await response.json();
        renderClients(data.data);
        renderPagination('clientsPagination', data);
    } catch (error) {
        console.error('Error loading clients:', error);
    }
}

function renderClients(clients) {
    const tbody = document.getElementById('clientsTableBody');

    if (clients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No clients found</td></tr>';
        return;
    }

    tbody.innerHTML = clients.map(client => `
        <tr>
            <td>${client.id}</td>
            <td>${client.full_name}</td>
            <td>${client.email}</td>
            <td>${client.phone || '-'}</td>
            <td>${formatDate(client.created_at)}</td>
            <td>
                <button class="action-btn" onclick="editClient(${client.id})">Edit</button>
                <button class="action-btn" style="background: #fee2e2; color: #991b1b;" onclick="deleteClient(${client.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

async function searchClients(term) {
    if (!term) {
        loadClients();
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/clients?search=${encodeURIComponent(term)}`, {
            credentials: 'include'
        });

        const data = await response.json();
        renderClients(data.data);
    } catch (error) {
        console.error('Error searching clients:', error);
    }
}

async function createClient(e) {
    e.preventDefault();

    const data = {
        full_name: document.getElementById('clientName').value,
        email: document.getElementById('clientEmail').value,
        phone: document.getElementById('clientPhone').value,
        notes: document.getElementById('clientNotes').value
    };

    try {
        const response = await fetch(`${API_URL}/api/clients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert('Client created successfully');
            closeModal('clientModal');
            document.getElementById('addClientForm').reset();
            loadClients();
        } else {
            const error = await response.json();
            alert('Error: ' + error.error);
        }
    } catch (error) {
        console.error('Error creating client:', error);
        alert('Failed to create client');
    }
}

async function deleteClient(clientId) {
    if (!confirm('Are you sure you want to delete this client? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/clients/${clientId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Client deleted successfully!');
            loadClients();
        } else if (response.status === 403) {
            alert('Unauthorized: Only administrators and managers can delete clients.');
        } else if (response.status === 400) {
            alert(`Cannot delete: Client has ${data.inquiries_count} existing inquiries.`);
        } else {
            alert(data.error || 'Error deleting client');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting client');
    }
}

async function editClient(clientId) {
    try {
        const response = await fetch(`${API_URL}/api/clients/${clientId}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            alert('Error loading client data');
            return;
        }

        const client = await response.json();

        document.getElementById('editClientId').value = client.id;
        document.getElementById('editClientFullName').value = client.full_name || '';
        document.getElementById('editClientEmail').value = client.email || '';
        document.getElementById('editClientPhone').value = client.phone || '';
        document.getElementById('editClientCompany').value = client.company || '';
        document.getElementById('editClientNotes').value = client.notes || '';

        openModal('editClientModal');

    } catch (error) {
        console.error('Error editing client:', error);
        alert('Error loading client data');
    }
}

// Responses
async function loadInquiriesForResponse() {
    try {
        const response = await fetch(`${API_URL}/api/inquiries?status=pending&per_page=100`, {
            credentials: 'include'
        });

        const data = await response.json();
        const select = document.getElementById('inquirySelect');

        select.innerHTML = '<option value="">Select an inquiry...</option>' +
            data.data.map(inq => `
                <option value="${inq.id}">
                    #${inq.id} - ${inq.subject.substring(0, 50)}...
                </option>
            `).join('');
    } catch (error) {
        console.error('Error loading inquiries:', error);
    }
}

async function sendResponse(e) {
    e.preventDefault();

    const inquiryId = document.getElementById('inquirySelect').value;
    const responseText = document.getElementById('responseText').value;

    if (!inquiryId) {
        alert('Please select an inquiry');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/responses`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                inquiry_id: parseInt(inquiryId),
                response_text: responseText,
                send_email: confirm('Send this response via email?')
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('Response sent successfully!');
            document.getElementById('responseForm').reset();
            loadInquiryStats();
            loadResponses();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error sending response:', error);
        alert('Failed to send response');
    }
}

async function generateAIResponse() {
    const inquiryId = document.getElementById('inquirySelect').value;

    if (!inquiryId) {
        alert('Please select an inquiry first');
        return;
    }

    const btn = document.getElementById('aiGenerateBtn');
    btn.disabled = true;
    btn.textContent = 'Generating...';

    try {
        const inquiryResponse = await fetch(`${API_URL}/api/inquiries/${inquiryId}`, {
            credentials: 'include'
        });
        const inquiry = await inquiryResponse.json();

        const response = await fetch(`${API_URL}/api/ai/generate-response`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                subject: inquiry.subject,
                message: inquiry.message
            })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('responseText').value = data.response;
        } else {
            alert('AI generation failed: ' + data.error);
        }
    } catch (error) {
        console.error('Error generating AI response:', error);
        alert('Failed to generate AI response');
    } finally {
        btn.disabled = false;
        btn.textContent = 'AI Generate';
    }
}

// Publishers
async function loadPublishers() {
    try {
        const response = await fetch(`${API_URL}/api/publishers?page=${currentPage}`, {
            credentials: 'include'
        });

        const data = await response.json();
        renderPublishers(data.data);
        renderPagination('publishersPagination', data);
    } catch (error) {
        console.error('Error loading publishers:', error);
    }
}

function renderPublishers(publishers) {
    const tbody = document.getElementById('publishersTableBody');

    if (publishers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No publishers found</td></tr>';
        return;
    }

    tbody.innerHTML = publishers.map(pub => `
        <tr>
            <td>
                <input type="checkbox" class="publisher-checkbox" 
                    data-email="${pub.email}" 
                    ${selectedPublishers.has(pub.email) ? 'checked' : ''}
                    onchange="togglePublisher('${pub.email}', this.checked)">
            </td>
            <td>${pub.id}</td>
            <td>${pub.name}</td>
            <td>${pub.email}</td>
            <td>${pub.category || '-'}</td>
            <td><span class="status-badge status-${pub.status}">${pub.status}</span></td>
        </tr>
    `).join('');
}

function togglePublisher(email, checked) {
    if (checked) {
        selectedPublishers.add(email);
    } else {
        selectedPublishers.delete(email);
    }
}

async function searchPublishers(term) {
    if (!term) {
        loadPublishers();
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/publishers?search=${encodeURIComponent(term)}`, {
            credentials: 'include'
        });

        const data = await response.json();
        renderPublishers(data.data);
    } catch (error) {
        console.error('Error searching publishers:', error);
    }
}

async function loadPublisherCount() {
    try {
        const response = await fetch(`${API_URL}/api/publishers/count`, {
            credentials: 'include'
        });

        const data = await response.json();
        document.getElementById('publisherCount').textContent = data.count.toLocaleString();
    } catch (error) {
        console.error('Error loading publisher count:', error);
    }
}

async function sendBulkEmail(e) {
    e.preventDefault();

    const subject = document.getElementById('bulkSubject').value;
    const message = document.getElementById('bulkMessage').value;
    const emailList = Array.from(selectedPublishers);

    if (!confirm(`Send email to ${emailList.length} publishers?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/email/bulk-send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                email_list: emailList,
                subject: subject,
                body: message
            })
        });

        const data = await response.json();

        alert(`Sent: ${data.sent}, Failed: ${data.failed}`);
        closeModal('bulkEmailModal');
        document.getElementById('bulkEmailForm').reset();
        selectedPublishers.clear();
        loadPublishers();
    } catch (error) {
        console.error('Error sending bulk email:', error);
        alert('Failed to send bulk email');
    }
}

// Utilities
function renderPagination(elementId, data) {
    const container = document.getElementById(elementId);

    if (data.pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';

    html += `<button class="page-btn" ${data.page === 1 ? 'disabled' : ''} 
        onclick="changePage(${data.page - 1})">Previous</button>`;

    for (let i = 1; i <= data.pages; i++) {
        if (i === 1 || i === data.pages || (i >= data.page - 2 && i <= data.page + 2)) {
            html += `<button class="page-btn ${i === data.page ? 'active' : ''}" 
                onclick="changePage(${i})">${i}</button>`;
        } else if (i === data.page - 3 || i === data.page + 3) {
            html += '<span>...</span>';
        }
    }

    html += `<button class="page-btn" ${data.page === data.pages ? 'disabled' : ''} 
        onclick="changePage(${data.page + 1})">Next</button>`;

    container.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    loadTabData(currentTab);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

setInterval(() => {
    console.log('Auto-syncing emails...');
    syncEmails();
}, 5 * 60 * 1000);

// ============================================================================
// RESPONSES - TRAZABILIDAD CON CONVERSATION THREADS
// ============================================================================

const responsesPerPage = 50;

async function loadResponses(page = 1) {
    try {
        const response = await fetch(`${API_URL}/api/responses?page=${page}&per_page=${responsesPerPage}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error loading responses');
        }
        
        const data = await response.json();
        renderResponsesTable(data);
        renderResponsesPagination(data);
        updateResponsesStats(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading responses');
    }
}

function renderResponsesTable(data) {
    const tbody = document.getElementById('responsesTableBody');
    
    if (!tbody) {
        console.error('responsesTableBody not found');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (data.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No responses found</td></tr>';
        return;
    }
    
    data.data.forEach(resp => {
        const row = document.createElement('tr');
        
        let statusBadge = '';
        
        if (resp.deal_status === 'closed_won') {
            statusBadge = '<span class="badge badge-won">Deal Won</span>';
        } else if (resp.deal_status === 'closed_lost') {
            statusBadge = '<span class="badge badge-lost">Deal Lost</span>';
        } else if (resp.client_replied && resp.follow_up_method === 'email') {
            statusBadge = '<span class="badge badge-success">Replied by Email</span>';
        } else if (resp.follow_up_method === 'other_channel') {
            statusBadge = '<span class="badge badge-info">Other Channel</span>';
        } else {
            statusBadge = '<span class="badge badge-warning">Pending</span>';
        }
        
        const sentDate = formatDateTime(resp.sent_at);
        
        let actions = `
            <button class="btn-small btn-info" onclick="viewResponseDetails(${resp.id})">
                View
            </button>
        `;
        
        if (resp.deal_status === 'open') {
            if (!resp.client_replied) {
                actions += `
                    <button class="btn-small btn-success" onclick="markAsReplied(${resp.id})">
                        Client Replied
                    </button>
                `;
            }
            
            actions += `
                <div class="action-dropdown" style="display: inline-block; position: relative;">
                    <button class="btn-small btn-secondary" onclick="toggleActionMenu(${resp.id})">
                        More ▼
                    </button>
                    <div id="action-menu-${resp.id}" class="action-menu" style="display: none;">
                        <button onclick="markAsOtherChannel(${resp.id})">Continued by Other Means</button>
                        <button onclick="markAsDealWon(${resp.id})">Deal Closed (Won)</button>
                        <button onclick="markAsDealLost(${resp.id})">Deal Closed (Lost)</button>
                    </div>
                </div>
            `;
        }
        
        row.innerHTML = `
            <td>${resp.id}</td>
            <td>${escapeHtml(resp.client_name || 'N/A')}</td>
            <td>${escapeHtml(resp.client_company || 'N/A')}</td>
            <td>${escapeHtml(resp.client_phone || 'N/A')}</td>
            <td>${sentDate}</td>
            <td>${statusBadge}</td>
            <td class="actions-cell">${actions}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function renderResponsesPagination(data) {
    const pagination = document.getElementById('responsesPagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    if (data.pages <= 1) return;
    
    if (data.page > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.textContent = 'Previous';
        prevBtn.className = 'btn-pagination';
        prevBtn.onclick = () => loadResponses(data.page - 1);
        pagination.appendChild(prevBtn);
    }
    
    for (let i = 1; i <= data.pages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = `btn-pagination ${i === data.page ? 'active' : ''}`;
        pageBtn.onclick = () => loadResponses(i);
        pagination.appendChild(pageBtn);
    }
    
    if (data.page < data.pages) {
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next';
        nextBtn.className = 'btn-pagination';
        nextBtn.onclick = () => loadResponses(data.page + 1);
        pagination.appendChild(nextBtn);
    }
}

function updateResponsesStats(data) {
    const totalEl = document.getElementById('totalResponses');
    const repliedEl = document.getElementById('clientsReplied');
    const pendingEl = document.getElementById('pendingReplies');
    
    if (totalEl) totalEl.textContent = data.total;
    
    if (data.data.length > 0) {
        const replied = data.data.filter(r => r.client_replied).length;
        const pending = data.data.filter(r => !r.client_replied).length;
        
        if (repliedEl) repliedEl.textContent = replied;
        if (pendingEl) pendingEl.textContent = pending;
    }
}

function toggleActionMenu(responseId) {
    const menu = document.getElementById(`action-menu-${responseId}`);
    if (menu) {
        document.querySelectorAll('.action-menu').forEach(m => {
            if (m.id !== `action-menu-${responseId}`) {
                m.style.display = 'none';
            }
        });
        
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
}

async function markAsOtherChannel(responseId) {
    if (!confirm('Mark that conversation continued by other means (phone, WhatsApp, etc.)?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/responses/${responseId}/update-follow-up`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({
                follow_up_method: 'other_channel',
                client_replied: 1
            })
        });
        
        if (!response.ok) {
            throw new Error('Error updating');
        }
        
        alert('Marked as continued by other channel');
        loadResponses(currentResponsesPage);
    } catch (error) {
        console.error('Error:', error);
        alert('Error updating response');
    }
}

// UPDATED: Mark deal as won with mandatory license creation and auto-extraction
async function markAsDealWon(responseId) {
    if (!confirm('Mark this deal as WON?\n\nYou will need to create a license for this client.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/responses/${responseId}/update-follow-up`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({
                deal_status: 'closed_won'
            })
        });
        
        if (!response.ok) {
            throw new Error('Error updating');
        }
        
        const respData = await fetch(`${API_URL}/api/responses/${responseId}`, {
            credentials: 'include'
        });
        const responseDetails = await respData.json();
        
        const inquiryData = await fetch(`${API_URL}/api/inquiries/${responseDetails.inquiry_id}`, {
            credentials: 'include'
        });
        const inquiry = await inquiryData.json();
        
        openLicenseModal(responseDetails, inquiry);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error updating response');
    }
}

async function markAsDealLost(responseId) {
    if (!confirm('Mark this deal as LOST (did not close)?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/responses/${responseId}/update-follow-up`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({
                deal_status: 'closed_lost'
            })
        });
        
        if (!response.ok) {
            throw new Error('Error updating');
        }
        
        alert('Deal marked as lost');
        loadResponses(currentResponsesPage);
    } catch (error) {
        console.error('Error:', error);
        alert('Error updating response');
    }
}

async function markAsReplied(responseId) {
    if (!confirm('Confirm that client replied to this quotation?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/responses/${responseId}/update-follow-up`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify({
                client_replied: 1,
                follow_up_method: 'email'
            })
        });
        
        if (!response.ok) {
            throw new Error('Error updating');
        }
        
        alert('Marked as replied successfully');
        loadResponses(currentResponsesPage);
    } catch (error) {
        console.error('Error:', error);
        alert('Error marking as replied');
    }
}

async function viewResponseDetails(responseId) {
    try {
        const response = await fetch(`${API_URL}/api/responses/${responseId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error loading details');
        }
        
        const data = await response.json();
        showResponseModal(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading response details');
    }
}

function showResponseModal(data) {
    const modal = document.getElementById('responseModal');
    if (!modal) {
        console.error('responseModal not found');
        return;
    }
    
    const repliedBadge = data.client_replied 
        ? '<span class="badge badge-success">Client Replied</span>'
        : '<span class="badge badge-warning">Pending Response</span>';
    
    let conversationHTML = '';
    
    if (data.conversation_thread && data.conversation_thread.length > 0) {
        conversationHTML = '<div class="conversation-thread">';
        
        data.conversation_thread.forEach(msg => {
            const isAgent = msg.sender === 'agent';
            const senderClass = isAgent ? 'agent-message' : 'client-message';
            const senderLabel = isAgent ? 'You (Agent)' : data.client_name;
            const timestamp = formatDateTime(msg.sent_at);
            
            conversationHTML += `
                <div class="message ${senderClass}">
                    <div class="message-header">
                        <strong>${escapeHtml(senderLabel)}</strong>
                        <span class="message-time">${timestamp}</span>
                    </div>
                    <div class="message-body">
                        ${escapeHtml(msg.message).replace(/\n/g, '<br>')}
                    </div>
                </div>
            `;
        });
        
        conversationHTML += '</div>';
    } else {
        conversationHTML = `
            <div class="detail-section">
                <h4>Response Sent</h4>
                <div class="message-box">
                    ${escapeHtml(data.response_text).replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
    }
    
    const modalContent = document.getElementById('responseModalContent');
    modalContent.innerHTML = `
        <h3>Response #${data.id}</h3>
        
        <div class="detail-section">
            <h4>Client Information</h4>
            <p><strong>Name:</strong> ${escapeHtml(data.client_name)}</p>
            <p><strong>Email:</strong> ${escapeHtml(data.client_email)}</p>
            <p><strong>Inquiry:</strong> ${escapeHtml(data.inquiry_subject)}</p>
        </div>
        
        <div class="detail-section">
            <h4>Original Inquiry</h4>
            <div class="message-box">
                ${escapeHtml(data.inquiry_message || 'N/A').replace(/\n/g, '<br>')}
            </div>
        </div>
        
        <div class="detail-section">
            <h4>Conversation History</h4>
            ${conversationHTML}
        </div>
        
        <div class="detail-section">
            <h4>Status</h4>
            <p><strong>Sent by:</strong> ${escapeHtml(data.sent_by)}</p>
            <p><strong>Date:</strong> ${formatDateTime(data.sent_at)}</p>
            <p><strong>Status:</strong> ${repliedBadge}</p>
        </div>
        
        ${!data.client_replied ? `
            <div class="modal-actions">
                <button class="btn btn-primary" onclick="markAsRepliedFromModal(${data.id})">
                    Mark as Replied
                </button>
            </div>
        ` : ''}
    `;
    
    modal.classList.add('active');
}

async function markAsRepliedFromModal(responseId) {
    await markAsReplied(responseId);
    closeResponseModal();
}

function closeResponseModal() {
    const modal = document.getElementById('responseModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    const dateStr = date.toLocaleDateString('en-US', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
    const timeStr = date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
    
    return `${dateStr} ${timeStr}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('click', function(event) {
    if (!event.target.matches('.btn-secondary')) {
        document.querySelectorAll('.action-menu').forEach(menu => {
            menu.style.display = 'none';
        });
    }
});

// ============================================================================
// LICENSE MANAGEMENT WITH DEAL QUEUE AND AUTO-EXTRACTION
// ============================================================================

// UPDATED: Open license modal with auto-extraction from inquiry message
function openLicenseModal(responseData, inquiryData = null) {
    document.getElementById('licenseResponseId').value = responseData.id;
    document.getElementById('licenseClientId').value = responseData.client_id || responseData.inquiry_id;
    document.getElementById('licenseClientName').value = responseData.client_name;
    document.getElementById('licenseClientDisplay').value = `${responseData.client_name} - ${responseData.client_email}`;
    
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('licenseStartDate').value = today;
    
    const nextYear = new Date();
    nextYear.setFullYear(nextYear.getFullYear() + 1);
    document.getElementById('licenseEndDate').value = nextYear.toISOString().split('T')[0];
    
    document.getElementById('licenseSalesPerson').value = currentUser.full_name;
    
    if (responseData.follow_up_method === 'email') {
        document.getElementById('licenseSource').value = 'email';
    } else if (responseData.follow_up_method === 'other_channel') {
        document.getElementById('licenseSource').value = 'other';
    }
    
    // AUTO-EXTRACT license info from inquiry message
    if (inquiryData && inquiryData.message) {
        const message = inquiryData.message.toLowerCase();
        
        // Detect license type
        if (message.includes('enterprise') || message.includes('unlimited')) {
            document.getElementById('licenseType').value = 'Enterprise';
        } else if (message.includes('professional') || message.includes('pro')) {
            document.getElementById('licenseType').value = 'Professional';
        } else if (message.includes('basic') || message.includes('starter')) {
            document.getElementById('licenseType').value = 'Basic';
        }
        
        // Extract price
        const priceMatch = message.match(/\$\s*(\d+[,\d]*\.?\d*)/);
        if (priceMatch) {
            const price = priceMatch[1].replace(/,/g, '');
            document.getElementById('licensePrice').value = price;
        }
        
        // Extract duration
        const monthsMatch = message.match(/(\d+)\s*(months?|meses)/i);
        const yearsMatch = message.match(/(\d+)\s*(years?|años)/i);
        
        if (yearsMatch) {
            const years = parseInt(yearsMatch[1]);
            const endDate = new Date();
            endDate.setFullYear(endDate.getFullYear() + years);
            document.getElementById('licenseEndDate').value = endDate.toISOString().split('T')[0];
        } else if (monthsMatch) {
            const months = parseInt(monthsMatch[1]);
            const endDate = new Date();
            endDate.setMonth(endDate.getMonth() + months);
            document.getElementById('licenseEndDate').value = endDate.toISOString().split('T')[0];
        }
    }
    
    openModal('licenseModal');
}

// UPDATED: Create license with FULL VALIDATION
async function createLicense(e) {
    e.preventDefault();
    
    const licenseType = document.getElementById('licenseType').value;
    const startDate = document.getElementById('licenseStartDate').value;
    const endDate = document.getElementById('licenseEndDate').value;
    const salesPerson = document.getElementById('licenseSalesPerson').value;
    const source = document.getElementById('licenseSource').value;
    
    // VALIDATION
    if (!licenseType) {
        alert(' Please select a license type');
        document.getElementById('licenseType').focus();
        return;
    }
    
    if (!startDate || !endDate) {
        alert(' Please select start and end dates');
        return;
    }
    
    if (new Date(endDate) <= new Date(startDate)) {
        alert(' End date must be after start date');
        document.getElementById('licenseEndDate').focus();
        return;
    }
    
    if (!salesPerson.trim()) {
        alert(' Please enter the sales person name');
        document.getElementById('licenseSalesPerson').focus();
        return;
    }
    
    if (!source) {
        alert(' Please select a source');
        document.getElementById('licenseSource').focus();
        return;
    }
    
    const data = {
        response_id: parseInt(document.getElementById('licenseResponseId').value),
        client_id: parseInt(document.getElementById('licenseClientId').value),
        license_type: licenseType,
        start_date: startDate,
        end_date: endDate,
        sales_person: salesPerson.trim(),
        source: source,
        price: document.getElementById('licensePrice').value || null,
        notes: document.getElementById('licenseNotes').value || null
    };
    
    try {
        const response = await fetch(`${API_URL}/api/licenses`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error creating license');
        }
        
        alert(' License created successfully! ');
        closeModal('licenseModal');
        document.getElementById('licenseForm').reset();
        
        loadResponses(currentResponsesPage);
        switchTab('licenses');
        
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error creating license: ' + error.message);
    }
}

// UPDATED: Load licenses WITH queue
async function loadLicenses(page = 1, status = '') {
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 50
        });
        
        if (status) params.append('status', status);
        
        const response = await fetch(`${API_URL}/api/licenses?${params}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error loading licenses');
        }
        
        const data = await response.json();
        renderLicensesTable(data);
        renderLicensesPagination(data);
        
        // Load deals in queue
        await loadDealsInQueue();
        
    } catch (error) {
        console.error('Error:', error);
        const tbody = document.getElementById('licensesTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center">Error loading licenses</td></tr>';
        }
    }
}

function renderLicensesTable(data) {
    const tbody = document.getElementById('licensesTableBody');
    
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (data.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center">No licenses found</td></tr>';
        return;
    }
    
    data.data.forEach(license => {
        const row = document.createElement('tr');
        
        const endDate = new Date(license.end_date);
        const today = new Date();
        const daysRemaining = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
        
        let statusBadge = '';
        let daysText = '';
        
        if (daysRemaining < 0) {
            statusBadge = '<span class="badge badge-lost">Expired</span>';
            daysText = `<span style="color: #ef4444;">${Math.abs(daysRemaining)} days ago</span>`;
        } else if (daysRemaining <= 30) {
            statusBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #d97706;">Expiring Soon</span>';
            daysText = `<span style="color: #d97706;">${daysRemaining} days</span>`;
        } else {
            statusBadge = '<span class="badge badge-success">Active</span>';
            daysText = `<span style="color: #059669;">${daysRemaining} days</span>`;
        }
        
        row.innerHTML = `
            <td>${license.id}</td>
            <td>${escapeHtml(license.client_name)}</td>
            <td>${escapeHtml(license.client_company || 'N/A')}</td>
            <td><strong>${escapeHtml(license.license_type)}</strong></td>
            <td>${formatDate(license.start_date).split(' ')[0]}</td>
            <td>${formatDate(license.end_date).split(' ')[0]}</td>
            <td>${daysText}</td>
            <td>${escapeHtml(license.sales_person)}</td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn-small btn-info" onclick="viewLicenseDetails(${license.id})">
                    View
                </button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function renderLicensesPagination(data) {
    const pagination = document.getElementById('licensesPagination');
    if (!pagination) return;
    
    pagination.innerHTML = '';
    
    if (data.pages <= 1) return;
    
    if (data.page > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.textContent = 'Previous';
        prevBtn.className = 'btn-pagination';
        prevBtn.onclick = () => {
            const status = document.getElementById('licenseStatusFilter').value;
            loadLicenses(data.page - 1, status);
        };
        pagination.appendChild(prevBtn);
    }
    
    for (let i = 1; i <= data.pages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = `btn-pagination ${i === data.page ? 'active' : ''}`;
        pageBtn.onclick = () => {
            const status = document.getElementById('licenseStatusFilter').value;
            loadLicenses(i, status);
        };
        pagination.appendChild(pageBtn);
    }
    
    if (data.page < data.pages) {
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next';
        nextBtn.className = 'btn-pagination';
        nextBtn.onclick = () => {
            const status = document.getElementById('licenseStatusFilter').value;
            loadLicenses(data.page + 1, status);
        };
        pagination.appendChild(nextBtn);
    }
}

async function viewLicenseDetails(licenseId) {
    try {
        const response = await fetch(`${API_URL}/api/licenses/${licenseId}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error loading license');
        }
        
        const license = await response.json();
        showLicenseDetailsModal(license);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading license details');
    }
}

function showLicenseDetailsModal(license) {
    const endDate = new Date(license.end_date);
    const today = new Date();
    const daysRemaining = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
    
    let statusBadge = '';
    if (daysRemaining < 0) {
        statusBadge = '<span class="badge badge-lost">Expired</span>';
    } else if (daysRemaining <= 30) {
        statusBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #d97706;">Expiring Soon</span>';
    } else {
        statusBadge = '<span class="badge badge-success">Active</span>';
    }
    
    const content = document.getElementById('licenseDetailsContent');
    content.innerHTML = `
        <div class="detail-section">
            <h4>Client Information</h4>
            <p><strong>Name:</strong> ${escapeHtml(license.client_name)}</p>
            <p><strong>Email:</strong> ${escapeHtml(license.client_email)}</p>
            <p><strong>Company:</strong> ${escapeHtml(license.client_company || 'N/A')}</p>
        </div>
        
        <div class="detail-section">
            <h4>License Details</h4>
            <p><strong>License Type:</strong> ${escapeHtml(license.license_type)}</p>
            <p><strong>Start Date:</strong> ${formatDate(license.start_date).split(' ')[0]}</p>
            <p><strong>End Date:</strong> ${formatDate(license.end_date).split(' ')[0]}</p>
            <p><strong>Days Remaining:</strong> ${daysRemaining} days</p>
            <p><strong>Status:</strong> ${statusBadge}</p>
        </div>
        
        <div class="detail-section">
            <h4>Sales Information</h4>
            <p><strong>Sales Person:</strong> ${escapeHtml(license.sales_person)}</p>
            <p><strong>Source:</strong> ${escapeHtml(license.source)}</p>
            ${license.price ? `<p><strong>Price:</strong> $${parseFloat(license.price).toLocaleString()}</p>` : ''}
        </div>
        
        ${license.notes ? `
        <div class="detail-section">
            <h4>Notes</h4>
            <p>${escapeHtml(license.notes)}</p>
        </div>
        ` : ''}
        
        <div class="modal-actions">
            <button class="btn btn-secondary" onclick="closeModal('licenseDetailsModal')">
                Close
            </button>
            ${daysRemaining > 0 && daysRemaining <= 60 ? `
                <button class="btn btn-primary" onclick="sendRenewalReminder(${license.id})">
                    Send Renewal Reminder
                </button>
            ` : ''}
        </div>
    `;
    
    openModal('licenseDetailsModal');
}

// UPDATED: Load license stats with queue count
async function loadLicenseStats() {
    try {
        const response = await fetch(`${API_URL}/api/licenses/stats`, {
            credentials: 'include'
        });
        
        if (!response.ok) return;
        
        const stats = await response.json();
        
        const activeCount = document.getElementById('activeLicensesCount');
        const expiringCount = document.getElementById('expiringSoonCount');
        const expiredCount = document.getElementById('expiredCount');
        const queueCount = document.getElementById('dealsInQueueCount');
        const queueBadge = document.getElementById('dealsInQueueBadge');
        const revenue = document.getElementById('totalRevenue');
        
        if (activeCount) activeCount.textContent = stats.total_active;
        if (expiringCount) expiringCount.textContent = stats.expiring_soon;
        if (expiredCount) expiredCount.textContent = stats.expired;
        if (queueCount) queueCount.textContent = stats.deals_in_queue || 0;
        if (queueBadge) queueBadge.textContent = stats.deals_in_queue || 0;
        if (revenue) revenue.textContent = `$${parseFloat(stats.total_revenue).toLocaleString()}`;
        
    } catch (error) {
        console.error('Error loading license stats:', error);
    }
}

async function sendRenewalReminder(licenseId) {
    alert('Renewal reminder functionality coming soon!\nThis will send an email to the client about their upcoming license expiration.');
}

async function checkExpiringLicenses() {
    try {
        const response = await fetch(`${API_URL}/api/licenses/expiring?days=30`, {
            credentials: 'include'
        });
        
        if (!response.ok) return;
        
        const expiring = await response.json();
        
        if (expiring.length > 0) {
            console.log(` ${expiring.length} license(s) expiring in the next 30 days`);
            
            if (expiring.length <= 5) {
                const names = expiring.map(l => l.client_name).join(', ');
                console.log(`Expiring licenses: ${names}`);
            }
        }
        
    } catch (error) {
        console.error('Error checking expiring licenses:', error);
    }
}

// NEW: Load deals in queue (won but no license)
async function loadDealsInQueue() {
    try {
        const response = await fetch(`${API_URL}/api/licenses/deals-in-queue`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error loading deals in queue');
        }
        
        const deals = await response.json();
        renderDealsInQueue(deals);
        
        const queueCount = document.getElementById('dealsInQueueCount');
        const queueBadge = document.getElementById('dealsInQueueBadge');
        if (queueCount) queueCount.textContent = deals.length;
        if (queueBadge) queueBadge.textContent = deals.length;
        
    } catch (error) {
        console.error('Error:', error);
    }
}

// NEW: Render deals in queue table
function renderDealsInQueue(deals) {
    const tbody = document.getElementById('dealsQueueTableBody');
    
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (deals.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center" style="color: #059669;">All deals have licenses created!</td></tr>';
        return;
    }
    
    deals.forEach(deal => {
        const row = document.createElement('tr');
        
        const wonDate = formatDateTime(deal.updated_at || deal.sent_at);
        
        row.innerHTML = `
            <td>${deal.response_id}</td>
            <td>${escapeHtml(deal.client_name)}</td>
            <td>${escapeHtml(deal.client_company || 'N/A')}</td>
            <td>${escapeHtml(deal.client_email)}</td>
            <td>${wonDate}</td>
            <td>
                <button class="btn-small btn-primary" onclick="createLicenseFromQueue(${deal.response_id}, ${deal.inquiry_id})">
                    Create License
                </button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// NEW: Create license from queue
async function createLicenseFromQueue(responseId, inquiryId) {
    try {
        const respData = await fetch(`${API_URL}/api/responses/${responseId}`, {
            credentials: 'include'
        });
        const responseDetails = await respData.json();
        
        const inquiryData = await fetch(`${API_URL}/api/inquiries/${inquiryId}`, {
            credentials: 'include'
        });
        const inquiry = await inquiryData.json();
        
        openLicenseModal(responseDetails, inquiry);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error loading deal information');
    }
}