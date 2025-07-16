// Admin Dashboard JavaScript
let currentTicketId = null;
let activeConversations = new Map();
let refreshInterval = null;
let adminSocket = null; // WebSocket connection for admin
let lastAdminJoinedTicketId = null;
let selectedAdminFile = null; // For file handling

// Initialize admin dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded - Starting admin dashboard initialization...');

    // Initialize WebSocket connection for real-time chat
    initializeWebSocket();

    // Test if we can reach the server
    fetch('/api/admin/dashboard-stats')
        .then(response => {
            console.log('Initial server test response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Initial server test data:', data);
        })
        .catch(error => {
            console.error('Initial server test failed:', error);
        });

    loadDashboardData();
    loadCategories();
    loadTickets();
    loadActiveConversations();

    // Start auto-refresh for live chat
    startAutoRefresh();

    console.log('Admin dashboard initialization complete');
});

// Notification system for admin interface
function showNotification(message, type = 'info', duration = 5000) {
    // Create notification container if it doesn't exist
    let notificationContainer = document.getElementById('admin-notifications');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'admin-notifications';
        notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 350px;
        `;
        document.body.appendChild(notificationContainer);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.style.cssText = `
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border: none;
    `;

    const icon = {
        'info': 'fas fa-info-circle',
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-triangle',
        'error': 'fas fa-times-circle'
    }[type] || 'fas fa-info-circle';

    notification.innerHTML = `
        <i class="${icon} me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    notificationContainer.appendChild(notification);

    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, duration);
}

// Admin connection status indicator
function updateConnectionStatus(connected) {
    let statusIndicator = document.getElementById('admin-connection-status');
    if (!statusIndicator) {
        statusIndicator = document.createElement('div');
        statusIndicator.id = 'admin-connection-status';
        statusIndicator.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            z-index: 1000;
            transition: all 0.3s ease;
        `;
        document.body.appendChild(statusIndicator);
    }

    if (connected) {
        statusIndicator.className = 'bg-success text-white';
        statusIndicator.innerHTML = '<i class="fas fa-wifi me-1"></i>Connected';
    } else {
        statusIndicator.className = 'bg-danger text-white';
        statusIndicator.innerHTML = '<i class="fas fa-wifi me-1"></i>Disconnected';
    }
}

// Join admin room for a ticket
function joinAdminRoom(ticketId) {
    if (adminSocket && adminSocket.connected && ticketId) {
        if (lastAdminJoinedTicketId && lastAdminJoinedTicketId !== ticketId) {
            adminSocket.emit('leave_room', { ticket_id: lastAdminJoinedTicketId });
        }
        adminSocket.emit('join_room', { ticket_id: ticketId });
        lastAdminJoinedTicketId = ticketId;
        console.log(`🚪 Admin joined room for ticket #${ticketId}`);
    }
}

// Initialize WebSocket for real-time admin communication
function initializeWebSocket() {
    try {
        adminSocket = io();
        let reconnecting = false;
        console.log('🔌 Admin WebSocket connection initialized');

        adminSocket.on('connect', () => {
            console.log('✅ Admin WebSocket connected');
            if (currentTicketId) {
                joinAdminRoom(currentTicketId);
            }
            reconnecting = false;
        });
        adminSocket.on('disconnect', () => {
            console.log('❌ Admin WebSocket disconnected');
            reconnecting = true;
        });
        adminSocket.on('reconnect', () => {
            console.log('🔄 Admin WebSocket reconnected');
            if (currentTicketId) {
                joinAdminRoom(currentTicketId);
            }
            reconnecting = false;
        });
        adminSocket.on('new_message', (data) => {
            console.log('📨 New message received:', data);
            if (data.ticket_id === currentTicketId) {
                addNewMessageToChat(data);
            }
            loadActiveConversations();
            if (!data.is_admin) {
                showNotification(`New message from user in ticket #${data.ticket_id}`, 'info');
            }
        });
        adminSocket.on('error', (error) => {
            console.error('🚨 Admin WebSocket error:', error);
        });
    } catch (e) {
        console.error('Failed to initialize WebSocket:', e);
    }
}

async function loadRecentActivity() {
    try {
        const response = await fetch('/api/admin/recent-activity');
        const activities = await response.json();

        const activityList = document.getElementById('recent-activity');
        if (activities.length === 0) {
            activityList.innerHTML = '<p class="text-muted">No recent activity</p>';
            return;
        }

        activityList.innerHTML = activities.map(activity => `
            <div class="activity-item fade-in">
                <div class="activity-icon">
                    <i class="${activity.icon}"></i>
                </div>
                <div class="activity-content">
                    <h6>${activity.title}</h6>
                    <p>${activity.description} • ${formatTime(activity.created_at)}</p>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// Dashboard data loading
async function loadDashboardData() {
    try {
        console.log('🔄 Loading dashboard data...');

        const response = await fetch('/api/admin/dashboard-stats');
        console.log('Dashboard response status:', response.status);

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                // Redirect to admin login if not authenticated
                window.location.href = '/auth/admin_login';
                return;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Dashboard data received:', data);

        // Update dashboard cards with received data
        document.getElementById('total-tickets').textContent = data.totalTickets || 0;
        document.getElementById('pending-tickets').textContent = data.pendingTickets || 0;
        document.getElementById('resolved-tickets').textContent = data.resolvedTickets || 0;
        document.getElementById('active-chats').textContent = data.activeChats || 0;

        console.log('✅ Dashboard data loaded successfully');

        // Also load recent activity
        await loadRecentActivity();

    } catch (error) {
        console.error('❌ Error loading dashboard data:', error);
        showNotification(`Failed to load dashboard data: ${error.message}`, 'error');

        // Set default values if loading fails
        document.getElementById('total-tickets').textContent = '?';
        document.getElementById('pending-tickets').textContent = '?';
        document.getElementById('resolved-tickets').textContent = '?';
        document.getElementById('active-chats').textContent = '?';
    }
}

// Tickets functions
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const categories = await response.json();

        const categoryFilter = document.getElementById('category-filter');
        if (categoryFilter) {
            categoryFilter.innerHTML = '<option value="">All Categories</option>' +
                categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

async function loadTickets() {
    try {
        console.log('Loading tickets...');
        const response = await fetch('/api/admin/tickets');

        console.log('Tickets response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Tickets API error:', response.status, errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const response_data = await response.json();
        console.log('Tickets response received:', response_data);

        // Check if response has error
        if (response_data.error || !response_data.success) {
            console.error('Tickets error:', response_data.error);
            showNotification(`Tickets error: ${response_data.error || 'Unknown error'}`, 'error');

            const tbody = document.getElementById('tickets-tbody');
            tbody.innerHTML = `<tr><td colspan="12" class="text-center text-danger">
                Error loading tickets: ${response_data.error || 'Unknown error'}
            </td></tr>`;
            return;
        }

        // Extract tickets array from response
        const tickets = response_data.tickets || [];
        console.log(`Extracted ${tickets.length} tickets from response`);

        const tbody = document.getElementById('tickets-tbody');
        if (!Array.isArray(tickets) || tickets.length === 0) {
            console.log('No tickets found');
            tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">No tickets found</td></tr>';
            return;
        }

        console.log(`Rendering ${tickets.length} tickets`);
        tbody.innerHTML = tickets.map(ticket => `
            <tr class="fade-in">
                <td>#${ticket.id}</td>
                <td>${ticket.subject || 'No subject'}</td>
                <td><span class="priority-badge priority-${ticket.priority || 'medium'}">${(ticket.priority || 'medium').toUpperCase()}</span></td>
                <td><span class="escalation-badge escalation-${ticket.escalation_level || 'normal'}">${(ticket.escalation_level || 'normal').toUpperCase()}</span></td>
                <td class="organization-cell">
                    <div class="organization-name">${ticket.organization || 'Unknown Org'}</div>
                    <small class="text-muted">${ticket.user_name || 'Anonymous'}</small>
                </td>
                <td>${ticket.category || 'Unknown'}</td>
                <td>${ticket.user_name || 'Anonymous'}</td>
                <td class="device-info-cell">
                    ${ticket.device_type || ticket.browser || ticket.operating_system ? 
                        `<div class="device-summary">
                            ${ticket.device_type ? `<i class="fas fa-${ticket.device_type === 'mobile' ? 'mobile-alt' : ticket.device_type === 'tablet' ? 'tablet-alt' : 'desktop'}" title="${ticket.device_type}"></i>` : ''}
                            ${ticket.browser ? `<span class="browser-info" title="${ticket.browser} ${ticket.browser_version || ''}">${ticket.browser}</span>` : ''}
                            ${ticket.operating_system ? `<small class="os-info" title="${ticket.operating_system} ${ticket.os_version || ''}">${ticket.operating_system}</small>` : ''}
                        </div>` : 
                        '<span class="text-muted">No device info</span>'
                    }
                </td>
                <td><span class="status-badge status-${ticket.status}">${ticket.status.replace('_', ' ')}</span></td>
                <td>${formatTime(ticket.created_at)}</td>
                <td>${ticket.end_date ? `<span class="text-success"><i class="fas fa-check-circle"></i> ${formatTime(ticket.end_date)}</span>` : '<span class="text-muted">-</span>'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="viewTicket(${ticket.id})" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-success me-1" onclick="startChat(${ticket.id})" title="Start Chat">
                        <i class="fas fa-comments"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTicket(${ticket.id})" title="Delete Ticket">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');

        console.log('Tickets rendered successfully');

    } catch (error) {
        console.error('Error loading tickets:', error);
        showNotification('Failed to load tickets. Please check the server connection.', 'error');

        const tbody = document.getElementById('tickets-tbody');
        tbody.innerHTML = `<tr><td colspan="11" class="text-center text-danger">
            Failed to load tickets: ${error.message}
        </td></tr>`;
    }
}

function filterTickets() {
    const statusFilter = document.getElementById('status-filter').value;
    const priorityFilter = document.getElementById('priority-filter').value;
    const escalationFilter = document.getElementById('escalation-filter').value;
    const categoryFilter = document.getElementById('category-filter').value;
    const organizationFilter = document.getElementById('organization-filter').value.toLowerCase();

    const rows = document.querySelectorAll('#tickets-tbody tr');

    rows.forEach(row => {
        const cells = row.cells;
        if (cells.length < 9) return; // Skip header or malformed rows

        const status = cells[7].textContent.toLowerCase().trim();
        const priority = cells[2].textContent.toLowerCase().trim();
        const escalation = cells[3].textContent.toLowerCase().trim();
        const category = cells[5].textContent.toLowerCase().trim();
        const organization = cells[4].textContent.toLowerCase().trim();

        const statusMatch = !statusFilter || status.includes(statusFilter.replace('_', ' '));
        const priorityMatch = !priorityFilter || priority.includes(priorityFilter);
        const escalationMatch = !escalationFilter || escalation.includes(escalationFilter);
        const categoryMatch = !categoryFilter || category.includes(categoryFilter.toLowerCase());
        const organizationMatch = !organizationFilter || organization.includes(organizationFilter);

        if (statusMatch && priorityMatch && escalationMatch && categoryMatch && organizationMatch) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

async function viewTicket(ticketId) {
    try {
        console.log(`Loading ticket details for ticket ID: ${ticketId}`);
        const response = await fetch(`/api/admin/tickets/${ticketId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const ticket = await response.json();
        console.log('Ticket data loaded:', ticket);

        // Check if we have messages with attachments
        if (ticket.messages) {
            ticket.messages.forEach((msg, index) => {
                console.log(`Message ${index + 1}:`, {
                    content: msg.content.substring(0, 50) + '...',
                    has_attachments: msg.attachments && msg.attachments.length > 0,
                    attachment_count: msg.attachments ? msg.attachments.length : 0,
                    attachment_url: msg.attachment_url,
                    attachments: msg.attachments
                });
            });
        }

        document.getElementById('ticket-details').innerHTML = `
            <div class="ticket-info">
                <h6>Ticket #${ticket.id}</h6>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Subject:</strong> ${ticket.subject}</p>
                        <p><strong>Category:</strong> ${ticket.category}</p>
                        <p><strong>Priority:</strong> <span class="priority-badge priority-${ticket.priority || 'medium'}">${(ticket.priority || 'medium').toUpperCase()}</span></p>
                        <p><strong>Escalation Level:</strong> <span class="escalation-badge escalation-${ticket.escalation_level || 'normal'}">${(ticket.escalation_level || 'normal').toUpperCase()}</span></p>
                        <p><strong>Status:</strong> <span class="status-badge status-${ticket.status}">${ticket.status.replace('_', ' ')}</span></p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Organization:</strong> <span class="fw-bold text-primary">${ticket.organization || 'Unknown Organization'}</span></p>
                        <p><strong>User:</strong> ${ticket.user_name || 'Anonymous'}</p>
                        <p><strong>Email:</strong> ${ticket.user_email || 'Not provided'}</p>
                        <p><strong>Created:</strong> ${formatTime(ticket.created_at)}</p>
                        ${ticket.updated_at ? `<p><strong>Last Updated:</strong> ${formatTime(ticket.updated_at)}</p>` : ''}
                        ${ticket.end_date ? `<p><strong>End Date:</strong> <span class="text-success">${formatTime(ticket.end_date)}</span></p>` : ''}
                    </div>
                </div>
                ${ticket.device_type || ticket.browser || ticket.operating_system ? `
                <div class="device-info-section">
                    <h6><i class="fas fa-laptop"></i> Device Information</h6>
                    <div class="row">
                        <div class="col-md-6">
                            ${ticket.device_type ? `<p><strong>Device Type:</strong> <i class="fas fa-${ticket.device_type === 'mobile' ? 'mobile-alt' : ticket.device_type === 'tablet' ? 'tablet-alt' : 'desktop'}"></i> ${ticket.device_type}</p>` : ''}
                            ${ticket.browser ? `<p><strong>Browser:</strong> ${ticket.browser} ${ticket.browser_version ? `v${ticket.browser_version}` : ''}</p>` : ''}
                            ${ticket.operating_system ? `<p><strong>Operating System:</strong> ${ticket.operating_system} ${ticket.os_version ? `v${ticket.os_version}` : ''}</p>` : ''}
                        </div>
                        <div class="col-md-6">
                            ${ticket.device_brand ? `<p><strong>Device Brand:</strong> ${ticket.device_brand}</p>` : ''}
                            ${ticket.device_model ? `<p><strong>Device Model:</strong> ${ticket.device_model}</p>` : ''}
                            ${ticket.ip_address ? `<p><strong>IP Address:</strong> <code>${ticket.ip_address}</code></p>` : ''}
                            ${ticket.device_fingerprint ? `<p><strong>Device ID:</strong> <small><code>${ticket.device_fingerprint.substring(0, 16)}...</code></small></p>` : ''}
                        </div>
                    </div>
                </div>
                ` : ''}
                <div class="ticket-messages">
                    <h6>Messages:</h6>
                    ${ticket.messages.map(msg => {
            console.log('Processing message for rendering:', {
                hasAttachments: msg.attachments && msg.attachments.length > 0,
                attachmentUrl: msg.attachment_url,
                attachmentCount: msg.attachments ? msg.attachments.length : 0
            });

            return `
                        <div class="message-item ${msg.is_admin ? 'admin' : 'user'}">
                            <div class="message-header">
                                <strong>${msg.is_admin ? 'Admin' : (ticket.user_name || 'User')}</strong>
                                <span class="text-muted">${formatTime(msg.created_at)}</span>
                            </div>
                            <div class="message-body">${msg.content}</div>
                            ${(msg.attachments && msg.attachments.length > 0) || (msg.attachment_url) ? `
                                <div class="message-attachments">
                                    <h6 class="mt-2 mb-1"><i class="fas fa-paperclip"></i> Attachments:</h6>
                                    <div class="attachments-grid">
                                        ${msg.attachments && msg.attachments.length > 0 ? msg.attachments.map(att => {
                console.log('Processing attachment:', att);
                const attachmentUrl = att.url || att.file_path || `/static/uploads/${att.filename || att.stored_name}`;
                console.log('Final attachment URL:', attachmentUrl);

                return `
                                            <div class="attachment-item" style="margin: 5px; padding: 10px; border: 1px solid #ddd; border-radius: 8px; display: inline-block;">
                                                <div class="attachment-preview" style="text-align: center;">
                                                    <img src="${attachmentUrl}" alt="${att.original_name || att.filename}" 
                                                         class="attachment-thumbnail" 
                                                         onclick="openImageModal('${attachmentUrl}', '${att.original_name || att.filename}')" 
                                                         style="cursor: pointer; max-width: 150px; max-height: 150px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
                                                         onerror="console.error('Failed to load image:', this.src); this.style.display='none'; this.nextElementSibling.style.display='block';">
                                                    <div class="file-icon" style="display: none; font-size: 48px; color: #666;">
                                                        <i class="fas fa-file-image"></i>
                                                        <div style="font-size: 12px; margin-top: 5px;">Image not found</div>
                                                    </div>
                                                </div>
                                                <div class="attachment-info" style="text-align: center; margin-top: 5px;">
                                                    <div><small><strong>${att.original_name || att.filename}</strong></small></div>
                                                    <div><small class="text-muted">(${formatFileSize(att.file_size || 0)})</small></div>
                                                    <div>
                                                        <a href="${attachmentUrl}" target="_blank" class="btn btn-sm btn-outline-primary mt-1">
                                                            <i class="fas fa-external-link-alt"></i> View
                                                        </a>
                                                        <button onclick="testImageUrl('${attachmentUrl}')" class="btn btn-sm btn-outline-info mt-1">
                                                            <i class="fas fa-search"></i> Test
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                            `;
            }).join('') : ''}
                                        ${msg.attachment_url ? `
                                            <div class="attachment-item" style="margin: 5px; padding: 10px; border: 1px solid #ddd; border-radius: 8px; display: inline-block;">
                                                <div class="attachment-preview" style="text-align: center;">
                                                    <img src="${msg.attachment_url}" alt="Attachment" 
                                                         class="attachment-thumbnail" 
                                                         onclick="openImageModal('${msg.attachment_url}', 'attachment')" 
                                                         style="cursor: pointer; max-width: 150px; max-height: 150px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
                                                         onerror="console.error('Failed to load image:', this.src); this.style.display='none'; this.nextElementSibling.style.display='block';">
                                                    <div class="file-icon" style="display: none; font-size: 48px; color: #666;">
                                                        <i class="fas fa-file-image"></i>
                                                        <div style="font-size: 12px; margin-top: 5px;">Image not found</div>
                                                    </div>
                                                </div>
                                                <div class="attachment-info" style="text-align: center; margin-top: 5px;">
                                                    <div><small><strong>Attachment</strong></small></div>
                                                    <div>
                                                        <a href="${msg.attachment_url}" target="_blank" class="btn btn-sm btn-outline-primary mt-1">
                                                            <i class="fas fa-external-link-alt"></i> View
                                                        </a>
                                                        <button onclick="testImageUrl('${msg.attachment_url}')" class="btn btn-sm btn-outline-info mt-1">
                                                            <i class="fas fa-search"></i> Test
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;

        const modal = new bootstrap.Modal(document.getElementById('ticketModal'));
        modal.show();

        currentTicketId = ticketId;
    } catch (error) {
        console.error('Error viewing ticket:', error);
        showNotification('Error loading ticket details: ' + error.message, 'error');
    }
}

// Live Chat functions
async function loadActiveConversations() {
    try {
        const response = await fetch('/api/admin/active-conversations');
        const conversations = await response.json();

        const conversationsList = document.getElementById('conversations-list');
        if (conversations.length === 0) {
            conversationsList.innerHTML = '<p class="text-muted text-center">No active conversations</p>';
            return;
        }

        conversationsList.innerHTML = conversations.map(conv => `
            <div class="conversation-item ${conv.id === currentTicketId ? 'active' : ''}" 
                 onclick="selectConversation(${conv.id})">
                <h6>${conv.user_name || 'Anonymous User'}</h6>
                <p>${conv.subject}</p>
                <small class="text-muted">${formatTime(conv.last_message_at)}</small>
                ${conv.unread_count > 0 ? `<span class="badge bg-primary">${conv.unread_count}</span>` : ''}
            </div>
        `).join('');

        // Update active conversations map
        conversations.forEach(conv => {
            activeConversations.set(conv.id, conv);
        });
    } catch (error) {
        console.error('Error loading active conversations:', error);
    }
}

async function selectConversation(ticketId) {
    if (currentTicketId && adminSocket && adminSocket.connected) {
        adminSocket.emit('leave_room', { ticket_id: currentTicketId });
    }
    currentTicketId = ticketId;
    joinAdminRoom(ticketId);

    // Update UI
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.conversation-item').classList.add('active');

    // Load conversation details
    const conversation = activeConversations.get(ticketId);
    if (conversation) {
        document.getElementById('chat-user-name').textContent =
            `${conversation.user_name || 'Anonymous'} - ${conversation.subject}`;
        document.getElementById('admin-chat-input').style.display = 'block';
    }

    // Load messages
    await loadChatMessages(ticketId);
}

async function loadChatMessages(ticketId) {
    try {
        const response = await fetch(`/api/tickets/${ticketId}/messages`);
        const messages = await response.json(); const messagesContainer = document.getElementById('admin-chat-messages');
        messagesContainer.innerHTML = messages.map(msg => `
            <div class="chat-message ${msg.is_admin ? 'admin' : 'user'} fade-in">
                <div class="message-avatar ${msg.is_admin ? 'admin' : 'user'}">
                    ${msg.is_admin ? 'A' : 'U'}
                </div>
                <div class="message-content">
                    ${msg.content}
                    ${msg.attachments && msg.attachments.length > 0 ? `
                        <div class="message-attachments">
                            ${msg.attachments.map(att => `
                                <div class="attachment-item">
                                    <img src="${att.url}" alt="${att.original_name}" class="attachment-thumbnail" onclick="openImageModal('${att.url}', '${att.original_name}')">
                                    <div class="attachment-info">
                                        <small>${att.original_name}</small>
                                        <small class="text-muted">(${formatFileSize(att.file_size)})</small>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    <div class="message-time">${formatTime(msg.created_at)}</div>
                </div>
            </div>
        `).join('');

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        console.error('Error loading chat messages:', error);
    }
}

async function sendAdminMessage() {
    const input = document.getElementById('admin-message-input');
    const message = input.value.trim();
    if (!message || !currentTicketId) return;
    try {
        if (adminSocket && adminSocket.connected) {
            adminSocket.emit('send_message', {
                ticket_id: currentTicketId,
                content: message,
                is_admin: true
            });
            input.value = '';
            // Do NOT add message to UI here; wait for server confirmation
            console.log('✅ Admin message sent via WebSocket');
        } else {
            alert('Live chat is not connected. Please wait for connection.');
        }
    } catch (error) {
        console.error('❌ Error sending admin message:', error);
        showNotification('Failed to send message. Please try again.', 'error');
    }
}

function handleEnter(event) {
    if (event.key === 'Enter') {
        sendAdminMessage();
    }
}

async function updateTicketStatus(status) {
    if (!currentTicketId) return;

    let adminMessage = '';

    // If resolving or closing, ask for optional message
    if (status === 'resolved' || status === 'closed') {
        adminMessage = prompt(
            `${status === 'resolved' ? 'Resolving' : 'Closing'} ticket #${currentTicketId}.\n\n` +
            'Enter an optional message to send to the user (or leave blank for default message):'
        );

        // User cancelled the prompt
        if (adminMessage === null) return;
    }

    try {
        const requestBody = { status };
        if (adminMessage && adminMessage.trim()) {
            requestBody.message = adminMessage.trim();
        }

        const response = await fetch(`/api/admin/tickets/${currentTicketId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (response.ok) {
            const result = await response.json();

            // Refresh data
            await loadTickets();
            await loadActiveConversations();
            await loadDashboardData();

            // Show success message
            const notificationMessage = result.notification_sent
                ? `Ticket status updated to ${status} and user has been notified`
                : `Ticket status updated to ${status}`;

            showNotification(notificationMessage, 'success');

            // If ticket was closed, show additional info
            if (status === 'resolved' || status === 'closed') {
                console.log(`Ticket ${currentTicketId} ${status}. User notification: ${result.notification_sent}`);
            }
        } else {
            const error = await response.json();
            showNotification(`Error: ${error.error || 'Failed to update ticket'}`, 'error');
        }
    } catch (error) {
        console.error('Error updating ticket status:', error);
        showNotification('Error updating ticket status', 'error');
    }
}

// Analytics functions
async function loadAnalytics() {
    try {
        const response = await fetch('/api/admin/analytics');
        const analytics = await response.json();

        // Create charts
        createCategoryChart(analytics.categoryData);
        createResolutionChart(analytics.resolutionData);
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function createCategoryChart(data) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    '#667eea',
                    '#f093fb',
                    '#4facfe',
                    '#43e97b',
                    '#f6d365'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function createResolutionChart(data) {
    const ctx = document.getElementById('resolutionChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Average Resolution Time (hours)',
                data: data.values,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Utility functions
function formatTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();

    // Check if the date is valid
    if (isNaN(date.getTime())) {
        return 'Invalid date';
    }

    // If the date string doesn't include timezone info, assume it's UTC
    const adjustedDate = dateString.includes('Z') || dateString.includes('+') || dateString.includes('-')
        ? date
        : new Date(dateString + 'Z'); // Add 'Z' to indicate UTC if no timezone info

    const diff = now - adjustedDate;

    // Handle future dates (shouldn't happen, but just in case)
    if (diff < 0) {
        return 'Just now';
    }

    // Less than 1 minute
    if (diff < 60000) return 'Just now';

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes} min${minutes === 1 ? '' : 's'} ago`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    }

    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days} day${days === 1 ? '' : 's'} ago`;
    }

    // More than 7 days, show actual date
    return adjustedDate.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function refreshData() {
    console.log('🔄 Refreshing all admin data...');
    showNotification('Refreshing data...', 'info', 2000);

    // Refresh data based on current active section
    const activeSection = document.querySelector('.content-section.active');
    if (activeSection) {
        const sectionId = activeSection.id.replace('-section', '');

        switch (sectionId) {
            case 'dashboard':
                loadDashboardData();
                break;
            case 'tickets':
                loadTickets();
                loadCategories();
                break;
            case 'live-chat':
                loadActiveConversations();
                if (currentTicketId) {
                    loadChatMessages(currentTicketId);
                }
                break;
            case 'analytics':
                loadAnalytics();
                break;
        }
    } else {
        // Default refresh all
        loadDashboardData();
        loadTickets();
        loadCategories();
        loadActiveConversations();
    }

    console.log('✅ Data refresh completed');
}

function startAutoRefresh() {
    // Refresh live chat data every 10 seconds
    refreshInterval = setInterval(() => {
        if (document.getElementById('live-chat-section').classList.contains('active')) {
            loadActiveConversations();
            if (currentTicketId) {
                loadChatMessages(currentTicketId);
            }
        }
    }, 10000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});

// Admin authentication functions
function adminLogout() {
    if (confirm('Are you sure you want to logout from the admin panel?')) {
        window.location.href = '/auth/admin/logout';
    }
}

// Check admin authentication on page load
document.addEventListener('DOMContentLoaded', () => {
    // Add authentication check for admin APIs
    const originalFetch = window.fetch;
    window.fetch = function (...args) {
        return originalFetch.apply(this, args)
            .then(response => {
                if (response.status === 401) {
                    // Admin session expired
                    alert('Admin session expired. Please login again.');
                    window.location.href = '/auth/admin/login';
                    return Promise.reject(new Error('Authentication required'));
                }
                return response;
            })
            .catch(error => {
                console.error('Fetch error:', error);
                throw error;
            });
    };
});

// Chat from ticket modal
function openLiveChat() {
    if (currentTicketId) {
        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('ticketModal')).hide();

        // Switch to live chat section
        showSection('live-chat');

        // Select the conversation
        setTimeout(() => {
            selectConversation(currentTicketId);
        }, 100);
    }
}

function startChat(ticketId) {
    currentTicketId = ticketId;
    showSection('live-chat');
    setTimeout(() => {
        selectConversation(ticketId);
    }, 100);
}

// Section management
function showSection(sectionName) {
    console.log(`🔄 Switching to section: ${sectionName}`);

    // Remove active class from all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });

    // Remove active class from all menu items
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
    });

    // Show selected section
    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.classList.add('active');
    }

    // Activate corresponding menu item
    const menuItem = document.querySelector(`[onclick="showSection('${sectionName}')"]`);
    if (menuItem) {
        menuItem.classList.add('active');
    }

    // Update page title
    const titles = {
        'dashboard': 'Dashboard',
        'tickets': 'Tickets',
        'live-chat': 'Live Chat',
        'analytics': 'Analytics'
    };

    const pageTitle = document.getElementById('page-title');
    if (pageTitle && titles[sectionName]) {
        pageTitle.textContent = titles[sectionName];
    }

    // Load section-specific data
    switch (sectionName) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'tickets':
            loadTickets();
            break;
        case 'live-chat':
            loadActiveConversations();
            break;
        case 'analytics':
            loadAnalytics();
            break;
    }

    console.log(`✅ Section switched to: ${sectionName}`);
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Function to open image in modal
function openImageModal(imageUrl, imageName) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('imageModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'imageModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="imageModalTitle">Image Attachment</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center">
                        <img id="modalImage" class="img-fluid" style="max-height: 70vh;">
                    </div>
                    <div class="modal-footer">
                        <a id="downloadImageBtn" class="btn btn-primary" download>
                            <i class="fas fa-download"></i> Download
                        </a>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // Update modal content
    document.getElementById('imageModalTitle').textContent = imageName;
    document.getElementById('modalImage').src = imageUrl;
    document.getElementById('downloadImageBtn').href = imageUrl;
    document.getElementById('downloadImageBtn').download = imageName;

    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

// Helper function to test image URLs for debugging
function testImageUrl(url) {
    console.log('Testing image URL:', url);

    // Test if the URL is reachable
    fetch(url, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                console.log('✅ Image URL is accessible:', url);
                showNotification(`Image URL is accessible: ${url}`, 'success');
            } else {
                console.error('❌ Image URL not accessible:', url, 'Status:', response.status);
                showNotification(`Image URL not accessible (${response.status}): ${url}`, 'error');
            }
        })
        .catch(error => {
            console.error('❌ Error testing image URL:', url, error);
            showNotification(`Error accessing image URL: ${url}`, 'error');
        });

    // Also try to open in new tab for manual verification
    window.open(url, '_blank');
}

async function deleteTicket(ticketId) {
    // Show confirmation dialog
    const ticketElement = document.querySelector(`button[onclick="deleteTicket(${ticketId})"]`).closest('tr');
    const ticketSubject = ticketElement?.cells[1]?.textContent || `#${ticketId}`;

    const confirmed = confirm(
        `Are you sure you want to delete ticket ${ticketSubject}?\n\n` +
        'This action will permanently delete:\n' +
        '• The ticket and all its messages\n' +
        '• All file attachments\n' +
        '• All associated data\n\n' +
        'This action cannot be undone!'
    );

    if (!confirmed) return;

    try {
        console.log(`Deleting ticket ${ticketId}...`);
        showNotification(`Deleting ticket #${ticketId}...`, 'info');

        const response = await fetch(`/api/admin/tickets/${ticketId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const result = await response.json();

            // Refresh data
            await loadTickets();
            await loadActiveConversations();
            await loadDashboardData();

            // Show success message
            showNotification(`Ticket #${ticketId} deleted successfully`, 'success');

            // If we were viewing this ticket, close the modal
            if (currentTicketId === ticketId) {
                const ticketModal = document.getElementById('ticketModal');
                if (ticketModal && bootstrap.Modal.getInstance(ticketModal)) {
                    bootstrap.Modal.getInstance(ticketModal).hide();
                }
                currentTicketId = null;
            }

            console.log(`Ticket ${ticketId} deleted successfully`);
        } else {
            const error = await response.json();
            showNotification(`Error: ${error.error || 'Failed to delete ticket'}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting ticket:', error);
        showNotification('Error deleting ticket', 'error');
    }
}

async function deleteCurrentTicket() {
    if (!currentTicketId) {
        showNotification('No ticket selected', 'error');
        return;
    }

    // Close the modal first
    const modal = bootstrap.Modal.getInstance(document.getElementById('ticketModal'));
    if (modal) {
        modal.hide();
    }

    // Wait a moment for modal to close, then trigger delete
    setTimeout(() => {
        deleteTicket(currentTicketId);
    }, 300);
}

// File handling for admin chat
function handleAdminFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        selectedAdminFile = file;
        document.getElementById('admin-selected-file-name').textContent = file.name;
        document.getElementById('admin-file-preview').style.display = 'block';
        console.log('📎 Admin file selected:', file.name);
    }
}

function clearAdminFileSelection() {
    selectedAdminFile = null;
    document.getElementById('admin-file-input').value = '';
    document.getElementById('admin-file-preview').style.display = 'none';
    console.log('❌ Admin file selection cleared');
}
