const API_URL = 'http://localhost:5001';

// State
let currentUser = null;
let currentTab = 'inquiries';
let currentPage = 1;
let selectedPublishers = new Set();

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // CRITICAL FIX: Only run if we're on the dashboard page
    // Check if dashboard elements exist
    const isDashboard = document.getElementById('currentUser') !== null;

    if (isDashboard) {
        checkAuth();
        setupEventListeners();
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
    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    // Tab Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            switchTab(item.dataset.tab);
        });
    });

    // Sync Emails
    const syncBtn = document.getElementById('syncEmailsBtn');
    if (syncBtn) {
        syncBtn.addEventListener('click', syncEmails);
    }

    // Status Filter
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            currentPage = 1;
            loadInquiries(e.target.value);
        });
    }

    // Client Search
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

    // Add Client
    const addClientBtn = document.getElementById('addClientBtn');
    if (addClientBtn) {
        addClientBtn.addEventListener('click', () => {
            openModal('clientModal');
        });
    }

    // Edit Client Form
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

    // Response Form
    const responseForm = document.getElementById('responseForm');
    if (responseForm) {
        responseForm.addEventListener('submit', sendResponse);
    }

    const aiGenerateBtn = document.getElementById('aiGenerateBtn');
    if (aiGenerateBtn) {
        aiGenerateBtn.addEventListener('click', generateAIResponse);
    }

    // Publisher Search
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

    // Import Publishers
    const importPublishersBtn = document.getElementById('importPublishersBtn');
    if (importPublishersBtn) {
        importPublishersBtn.addEventListener('click', () => {
            alert('To import publishers, create a JSON file and send it to POST /api/publishers/bulk-import');
        });
    }

    // Bulk Email
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

    // Select All Publishers
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

    // Modal Close
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal(btn.closest('.modal').id);
        });
    });

    // Close modal on outside click
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

    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');

    // Update title
    const titles = {
        'inquiries': 'Inquiries',
        'clients': 'Clients',
        'responses': 'Send Response',
        'publishers': 'Publishers'
    };
    document.getElementById('pageTitle').textContent = titles[tabName];

    // Load data
    loadTabData(tabName);
}

function loadDashboard() {
    loadInquiries();
    loadInquiryStats();
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
            loadResponsesHistory(); 
            break;
        case 'publishers':
            loadPublishers();
            loadPublisherCount();
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
        'responded': '<img src="https://cdn-icons-png.flaticon.com/512/5372/5372949.png" width="24" height="24" alt="responded">',
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

// Delete client
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

// Open edit client modal
async function editClient(clientId) {
    try {
        // Fetch client data
        const response = await fetch(`${API_URL}/api/clients/${clientId}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            alert('Error loading client data');
            return;
        }

        const client = await response.json();

        // Fill form with client data
        document.getElementById('editClientId').value = client.id;
        document.getElementById('editClientFullName').value = client.full_name || '';
        document.getElementById('editClientEmail').value = client.email || '';
        document.getElementById('editClientPhone').value = client.phone || '';
        document.getElementById('editClientCompany').value = client.company || '';
        document.getElementById('editClientNotes').value = client.notes || '';

        // Open modal
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
            loadResponsesHistory(); 
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
        // Get inquiry details
        const inquiryResponse = await fetch(`${API_URL}/api/inquiries/${inquiryId}`, {
            credentials: 'include'
        });
        const inquiry = await inquiryResponse.json();

        // Generate AI response
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

// Load responses history
async function loadResponsesHistory() {
    try {
        const response = await fetch(`${API_URL}/api/responses?page=${currentPage}`, {
            credentials: 'include'
        });

        const data = await response.json();
        renderResponsesHistory(data.data);
        renderPagination('responsesPagination', data);
    } catch (error) {
        console.error('Error loading responses history:', error);
    }
}

function renderResponsesHistory(responses) {
    const tbody = document.getElementById('responsesTableBody');

    if (!responses || responses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No responses found</td></tr>';
        return;
    }

    tbody.innerHTML = responses.map(resp => `
        <tr>
            <td>${resp.id}</td>
            <td>${resp.client_name || 'Unknown'}</td>
            <td>${resp.inquiry_subject || 'N/A'}</td>
            <td>${formatDate(resp.sent_at)}</td>
            <td>
                <button class="action-btn" onclick="viewResponseDetail(${resp.id})">View</button>
            </td>
        </tr>
    `).join('');
}

async function viewResponseDetail(id) {
    try {
        const response = await fetch(`${API_URL}/api/responses/${id}`, {
            credentials: 'include'
        });

        const responseData = await response.json();

        document.getElementById('inquiryDetails').innerHTML = `
            <div class="inquiry-detail">
                <p><strong>Response ID:</strong> ${responseData.id}</p>
                <p><strong>Client:</strong> ${responseData.client_name}</p>
                <p><strong>Inquiry:</strong> ${responseData.inquiry_subject}</p>
                <p><strong>Sent:</strong> ${formatDate(responseData.sent_at)}</p>
                <p><strong>Sent by:</strong> ${responseData.sent_by || 'Unknown'}</p>
                <div style="margin-top: 20px;">
                    <strong>Response Text:</strong>
                    <div style="background: #f8fafc; padding: 16px; border-radius: 6px; margin-top: 8px; white-space: pre-wrap;">
                        ${responseData.response_text}
                    </div>
                </div>
            </div>
        `;

        openModal('inquiryModal');
    } catch (error) {
        console.error('Error loading response:', error);
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

    // Previous button
    html += `<button class="page-btn" ${data.page === 1 ? 'disabled' : ''} 
        onclick="changePage(${data.page - 1})">Previous</button>`;

    // Page numbers
    for (let i = 1; i <= data.pages; i++) {
        if (i === 1 || i === data.pages || (i >= data.page - 2 && i <= data.page + 2)) {
            html += `<button class="page-btn ${i === data.page ? 'active' : ''}" 
                onclick="changePage(${i})">${i}</button>`;
        } else if (i === data.page - 3 || i === data.page + 3) {
            html += '<span>...</span>';
        }
    }

    // Next button
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