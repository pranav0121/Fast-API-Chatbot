// Enhanced Support Chat JavaScript
let currentTicketId = null;
let selectedCategory = null;
let currentUser = null;
let chatState = 'welcome'; // welcome, category, issues, form, chat
let messageRefreshInterval = null;

// Offline mode functionality
let isOfflineMode = false;
let offlineTickets = [];

// Device tracking integration
let deviceContext = null;
let deviceTracker = null;

// Debug mode
let debugMode = true; // Set to true for detailed logging
let errorLog = [];

// Initialize device tracking for chat
function initializeDeviceTracking() {
    try {
        // Check if device tracker is available
        if (typeof window.deviceTracker !== 'undefined') {
            deviceTracker = window.deviceTracker;
            deviceContext = deviceTracker.getDeviceContext();
            
            console.log('✅ Device tracking initialized for chat');
            console.log('📱 Device context:', deviceContext);
            
            // Track chat widget initialization
            deviceTracker.trackChatEvent('widget_initialized', {
                url: window.location.pathname,
                referrer: document.referrer
            });
            
            // Check for compatibility warnings and show to user if needed
            const warnings = deviceTracker.getCompatibilityWarnings();
            if (warnings.length > 0) {
                handleDeviceCompatibilityWarnings(warnings);
            }
            
            return true;
        } else {
            console.warn('⚠️ Device tracker not available, falling back to basic info');
            // Fallback device info collection
            deviceContext = collectBasicDeviceInfo();
            return false;
        }
    } catch (error) {
        console.error('❌ Error initializing device tracking:', error);
        deviceContext = collectBasicDeviceInfo();
        return false;
    }
}

// Fallback device info collection without device tracker
function collectBasicDeviceInfo() {
    return {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        screenWidth: screen.width,
        screenHeight: screen.height,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        deviceType: getBasicDeviceType(),
        timestamp: new Date().toISOString()
    };
}

// Basic device type detection
function getBasicDeviceType() {
    const ua = navigator.userAgent.toLowerCase();
    if (/mobile|android|iphone|ipod/.test(ua)) return 'mobile';
    if (/ipad|tablet/.test(ua)) return 'tablet';
    return 'desktop';
}

// Handle device compatibility warnings
function handleDeviceCompatibilityWarnings(warnings) {
    const criticalWarnings = warnings.filter(w => w.type === 'error');
    
    if (criticalWarnings.length > 0) {
        // Show critical compatibility issues to user
        setTimeout(() => {
            showNotification(
                criticalWarnings[0].message, 
                'warning', 
                8000
            );
        }, 2000);
    }
}

// Enhanced error logging
function logError(context, error, data = null) {
    const errorEntry = {
        timestamp: new Date().toISOString(),
        context: context,
        error: error.toString(),
        stack: error.stack,
        data: data
    };

    errorLog.push(errorEntry);

    if (debugMode) {
        console.group(`🚨 Error in ${context}`);
        console.error('Error:', error);
        if (data) console.log('Data:', data);
        console.groupEnd();
    }

    // Store errors in localStorage for debugging
    try {
        localStorage.setItem('chatErrorLog', JSON.stringify(errorLog));
    } catch (e) {
        console.warn('Could not save error log to localStorage');
    }
}

// Debug function to show system status
function showSystemStatus() {
    console.group('🔍 System Status');
    console.log('Chat State:', chatState);
    console.log('Selected Category:', selectedCategory);
    console.log('Current User:', currentUser);
    console.log('Current Ticket ID:', currentTicketId);
    console.log('Is Offline Mode:', isOfflineMode);
    console.log('Error Log:', errorLog);
    console.groupEnd();
}

// Expose debug functions globally for testing
window.debugChat = {
    showStatus: showSystemStatus,
    errors: errorLog,
    testAPI: testApiConnection,
    clearErrors: () => { errorLog = []; localStorage.removeItem('chatErrorLog'); }
};

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing chat system...');
    
    // Initialize device tracking first
    initializeDeviceTracking();
    
    loadCategories();
    loadQuickCategories();
    setupEventListeners();
    
    // Initialize Socket.IO for real-time chat
    window.chatSocket = io();
    let reconnecting = false;

    chatSocket.on('connect', () => {
        console.log('✅ User WebSocket connected');
        if (currentTicketId) {
            joinChatRoom(currentTicketId);
        }
        reconnecting = false;
    });

    chatSocket.on('disconnect', () => {
        console.log('❌ User WebSocket disconnected');
        reconnecting = true;
    });

    chatSocket.on('reconnect', () => {
        console.log('🔄 User WebSocket reconnected');
        if (currentTicketId) {
            joinChatRoom(currentTicketId);
        }
        reconnecting = false;
    });

    chatSocket.on('new_message', (data) => {
        console.log('📨 User received new message:', data);
        if (data.ticket_id === currentTicketId) {
            addChatMessage(data.content, data.is_admin ? 'admin' : 'user', data.created_at);
        }
    });

    chatSocket.on('error', (error) => {
        console.error('🚨 User WebSocket error:', error);
    });

    // Test API connectivity
    testApiConnection();

    // Initialize device tracking
    initializeDeviceTracking();
});

let lastJoinedTicketId = null;

function joinChatRoom(ticketId) {
    if (window.chatSocket && chatSocket.connected && ticketId) {
        if (lastJoinedTicketId && lastJoinedTicketId !== ticketId) {
            chatSocket.emit('leave_room', { ticket_id: lastJoinedTicketId });
        }
        chatSocket.emit('join_room', { ticket_id: ticketId });
        lastJoinedTicketId = ticketId;
        console.log(`🚪 User joined room for ticket #${ticketId}`);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Rating stars
    document.querySelectorAll('.rating-stars i').forEach(star => {
        star.addEventListener('click', function () {
            const rating = this.dataset.rating;
            setRating(rating);
        });

        star.addEventListener('mouseenter', function () {
            const rating = this.dataset.rating;
            highlightStars(rating);
        });
    });

    // Reset stars on mouse leave
    document.querySelector('.rating-stars')?.addEventListener('mouseleave', () => {
        const activeRating = document.querySelector('.rating-stars i.active:last-of-type')?.dataset.rating || 0;
        highlightStars(activeRating);
    });
    // Paste images from clipboard
    const liveInput = document.getElementById('live-chat-message-input');
    if (liveInput) {
        liveInput.addEventListener('paste', handlePaste);
    }
    // File attach button
    const attachBtn = document.getElementById('attach-btn');
    const fileInput = document.getElementById('file-input');
    if (attachBtn && fileInput) {
        attachBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            for (const file of e.target.files) {
                uploadAndSendFile(file);
            }
            fileInput.value = '';
        });
    }
    // Drag & drop upload
    const dropArea = document.getElementById('file-upload-area');
    if (dropArea) {
        dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.classList.add('drag-over'); });
        dropArea.addEventListener('dragleave', (e) => { e.preventDefault(); dropArea.classList.remove('drag-over'); });
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault(); dropArea.classList.remove('drag-over');
            for (const file of e.dataTransfer.files) {
                uploadAndSendFile(file);
            }
        });
    }
}

// Load categories for chat widget
async function loadCategories() {
    try {
        console.log('Loading categories...');
        const response = await fetch('/api/categories');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const categories = await response.json();
        console.log('Categories loaded:', categories);

        const categoriesDiv = document.getElementById('categories');
        if (!categoriesDiv) {
            console.log('Categories div not found');
            return;
        }

        if (Array.isArray(categories) && categories.length > 0) {
            categoriesDiv.innerHTML = categories.map(category => `
                <button class="category-btn" onclick="selectCategory(${category.id}, '${escapeHtml(category.name)}')">
                    <i class="fas fa-${getCategoryIcon(category.name)}"></i>
                    ${category.name}
                </button>
            `).join('');
            console.log('Categories rendered successfully');
        } else {
            console.log('No categories found or invalid format');
            // Use fallback categories
            loadFallbackCategories(categoriesDiv);
        }
    } catch (error) {
        console.error('Error loading categories:', error);
        const categoriesDiv = document.getElementById('categories');
        if (categoriesDiv) {
            loadFallbackCategories(categoriesDiv);
        }
    }
}

// Load fallback categories when API fails
function loadFallbackCategories(categoriesDiv) {
    const fallbackCategories = [
        { id: 1, name: 'Payments' },
        { id: 2, name: 'Product Issues' },
        { id: 3, name: 'Technical Glitches' },
        { id: 4, name: 'General Inquiries' }
    ];

    categoriesDiv.innerHTML = fallbackCategories.map(category => `
        <button class="category-btn" onclick="selectCategory(${category.id}, '${escapeHtml(category.name)}')">
            <i class="fas fa-${getCategoryIcon(category.name)}"></i>
            ${category.name}
        </button>
    `).join('') + `
        <div class="text-center mt-3">
            <small class="text-muted">
                <i class="fas fa-info-circle me-1"></i>
                Working in offline mode. Some features may be limited.
            </small>
        </div>
    `;

    console.log('Fallback categories loaded');
}

// Load categories for quick help section
async function loadQuickCategories() {
    try {
        console.log('Loading quick categories...');
        const response = await fetch('/api/categories');

        const quickCategoriesDiv = document.getElementById('quick-categories');
        if (!quickCategoriesDiv) return;

        let categories;

        if (response.ok) {
            categories = await response.json();
        }

        // Use fallback if API failed or returned empty
        if (!categories || !Array.isArray(categories) || categories.length === 0) {
            console.log('Using fallback categories for quick help');
            categories = [
                { id: 1, name: 'Payments' },
                { id: 2, name: 'Product Issues' },
                { id: 3, name: 'Technical Glitches' },
                { id: 4, name: 'General Inquiries' }
            ];
        }

        quickCategoriesDiv.innerHTML = categories.map(category => `
            <div class="col-md-6 col-lg-3">
                <div class="category-card" onclick="openChatWithCategory(${category.id}, '${escapeHtml(category.name)}')">
                    <div class="category-icon">
                        <i class="fas fa-${getCategoryIcon(category.name)}"></i>
                    </div>
                    <h4>${category.name}</h4>
                    <p>Get help with ${category.name.toLowerCase()} related issues</p>
                </div>
            </div>
        `).join('');

        console.log('Quick categories loaded successfully');

    } catch (error) {
        console.error('Error loading quick categories:', error);
        // Load fallback categories even on error
        const quickCategoriesDiv = document.getElementById('quick-categories');
        if (quickCategoriesDiv) {
            const fallbackCategories = [
                { id: 1, name: 'Payments' },
                { id: 2, name: 'Product Issues' },
                { id: 3, name: 'Technical Glitches' },
                { id: 4, name: 'General Inquiries' }
            ];

            quickCategoriesDiv.innerHTML = fallbackCategories.map(category => `
                <div class="col-md-6 col-lg-3">
                    <div class="category-card" onclick="openChatWithCategory(${category.id}, '${escapeHtml(category.name)}')">
                        <div class="category-icon">
                            <i class="fas fa-${getCategoryIcon(category.name)}"></i>
                        </div>
                        <h4>${category.name}</h4>
                        <p>Get help with ${category.name.toLowerCase()} related issues</p>
                    </div>
                </div>
            `).join('');
        }
    }
}

// Get appropriate icon for category
function getCategoryIcon(categoryName) {
    const icons = {
        'Payments': 'credit-card',
        'Product Issues': 'box',
        'Technical Glitches': 'cog',
        'General Inquiries': 'question-circle'
    };
    return icons[categoryName] || 'question-circle';
}

// Open support chat
function openSupportChat() {
    const chatWidget = document.getElementById('chat-widget');
    const fabContainer = document.getElementById('fab-container');

    chatWidget.classList.add('active');
    fabContainer.style.display = 'none';

    // Track chat opening with device info
    if (deviceTracker) {
        deviceTracker.trackChatEvent('opened', {
            page: window.location.pathname,
            referrer: document.referrer,
            device_context: deviceContext
        });
    }

    // Show welcome screen
    showWelcomeScreen();
}

// Open chat with specific category
function openChatWithCategory(categoryId, categoryName) {
    openSupportChat();
    setTimeout(() => {
        selectCategory(categoryId, categoryName);
    }, 300);
}

// Show welcome screen
function showWelcomeScreen() {
    chatState = 'welcome';
    hideAllChatSections();
    document.getElementById('welcome-screen').style.display = 'block';
}

// Hide all chat sections
function hideAllChatSections() {
    const sections = ['welcome-screen', 'chat-messages', 'common-issues', 'custom-issue-form', 'live-chat'];
    sections.forEach(section => {
        const element = document.getElementById(section);
        if (element) element.style.display = 'none';
    });

    const inputs = ['category-input', 'live-chat-input'];
    inputs.forEach(input => {
        const element = document.getElementById(input);
        if (element) element.style.display = 'none';
    });
}

// Handle category selection
async function selectCategory(categoryId, categoryName) {
    selectedCategory = { id: categoryId, name: categoryName };
    chatState = 'issues';

    console.log('Category selected:', selectedCategory);

    try {
        // Load common queries for this category
        const response = await fetch(`/api/common-queries/${categoryId}`);

        hideAllChatSections();

        let queries = [];

        if (response.ok) {
            queries = await response.json();
            console.log('Common queries loaded:', queries);
        } else {
            console.warn('Failed to load common queries, using fallback');
            queries = getFallbackQueries(categoryName);
        }

        if (queries.length > 0) {
            showCommonIssues(queries);
        } else {
            showNoCommonIssues();
        }

        // Always show the text input for custom questions after showing common issues
        setTimeout(() => {
            const categoryInputDiv = document.getElementById('category-input');
            if (categoryInputDiv) {
                categoryInputDiv.style.display = 'block';
                console.log('Category input section shown');

                // Update the input placeholder
                const input = document.getElementById('category-message-input');
                if (input) {
                    input.placeholder = `Type your ${categoryName.toLowerCase()} question here...`;
                    input.focus();
                }
            } else {
                console.error('Category input element not found!');
            }
        }, 200);

    } catch (error) {
        console.error('Error loading common queries:', error);
        hideAllChatSections();        // Try to show fallback queries
        const fallbackQueries = getFallbackQueries(categoryName);
        if (fallbackQueries.length > 0) {
            showCommonIssues(fallbackQueries);
        } else {
            showNoCommonIssues();
        }

        // Always show the text input for custom questions
        setTimeout(() => {
            const categoryInputDiv = document.getElementById('category-input');
            if (categoryInputDiv) {
                categoryInputDiv.style.display = 'block';
                console.log('Category input section shown (fallback)');

                // Update the input placeholder
                const input = document.getElementById('category-message-input');
                if (input) {
                    input.placeholder = `Type your ${categoryName.toLowerCase()} question here...`;
                    input.focus();
                }
            } else {
                console.error('Category input element not found! (fallback)');
            }
        }, 200);
    }
}

// Get fallback queries for categories
function getFallbackQueries(categoryName) {
    const fallbackQueries = {
        'Payments': [
            { question: 'How do I update my payment method?', solution: 'You can update your payment method in Account Settings > Billing section.' },
            { question: 'Why was my payment declined?', solution: 'Payment declines can happen due to insufficient funds or expired cards. Please check with your bank.' },
            { question: 'How do I get a refund?', solution: 'Refunds can be requested within 30 days. Please contact our billing team.' }
        ],
        'Product Issues': [
            { question: 'The product is not working as expected', solution: 'Please try refreshing the page or clearing your browser cache.' },
            { question: 'I can\'t find a specific feature', solution: 'Check our help documentation or use the search function in the app.' },
            { question: 'How do I report a bug?', solution: 'You can report bugs using the "Report Issue" button or contact support.' }
        ],
        'Technical Glitches': [
            { question: 'The page won\'t load properly', solution: 'Try refreshing the page (Ctrl+F5) or clearing your browser cache.' },
            { question: 'I\'m getting error messages', solution: 'Please note the exact error message and try refreshing the page.' },
            { question: 'The app is running slowly', solution: 'Close other browser tabs and check your internet connection.' }
        ],
        'General Inquiries': [
            { question: 'How do I contact customer support?', solution: 'You can reach us through this chat, email, or phone during business hours.' },
            { question: 'What are your business hours?', solution: 'Our support team is available Monday to Friday, 9 AM to 6 PM EST.' },
            { question: 'How do I create an account?', solution: 'Click "Sign Up" on our homepage and follow the registration steps.' }
        ]
    };

    return fallbackQueries[categoryName] || [];
}

// Show common issues
function showCommonIssues(queries) {
    const commonIssuesDiv = document.getElementById('common-issues');
    const issuesList = document.getElementById('issues-list');

    issuesList.innerHTML = `
        <div class="common-issues-header">
            <h6><i class="fas fa-lightbulb text-warning me-2"></i>Common Issues for ${selectedCategory.name}</h6>
            <p class="text-muted small mb-3">Click on an issue below or type your own question in the box below:</p>
        </div>
        ${queries.map(query => `
            <div class="issue-item" onclick="showSolution('${escapeHtml(query.question)}', '${escapeHtml(query.solution)}')">
                <i class="fas fa-lightbulb text-warning me-2"></i>
                <span>${query.question}</span>
                <i class="fas fa-chevron-right ms-auto text-muted"></i>
            </div>
        `).join('')}
        <div class="custom-input-prompt">
            <div class="divider">
                <span>OR</span>
            </div>
            <p class="text-muted small text-center">
                <i class="fas fa-edit me-1"></i>
                Type your specific question in the text box below
            </p>
        </div>
    `;

    commonIssuesDiv.style.display = 'block';
}

// Show when no common issues are available
function showNoCommonIssues() {
    const commonIssuesDiv = document.getElementById('common-issues');
    const issuesList = document.getElementById('issues-list');

    issuesList.innerHTML = `
        <div class="no-common-issues">
            <div class="text-center p-4">
                <i class="fas fa-edit fa-2x text-primary mb-3"></i>
                <h6>Tell us about your ${selectedCategory.name} issue</h6>
                <p class="text-muted small">
                    Please describe your question or problem in the text box below and we'll help you right away.
                </p>
            </div>
        </div>
    `;

    commonIssuesDiv.style.display = 'block';
}

// Show custom issue form
function showCustomIssueForm() {
    chatState = 'form';
    hideAllChatSections();
    document.getElementById('custom-issue-form').style.display = 'block';
    document.getElementById('category-input').style.display = 'none';
}

// Go back to issues from form
function goBackToIssues() {
    if (selectedCategory) {
        selectCategory(selectedCategory.id, selectedCategory.name);
    } else {
        showWelcomeScreen();
    }
}

// Send category message (from input box)
async function sendCategoryMessage() {
    const input = document.getElementById('category-message-input');
    const message = input.value.trim();

    if (!message) {
        showNotification('Please enter your question or issue.', 'warning');
        return;
    }

    console.log('Sending category message:', message);

    // Show loading state
    const button = input.nextElementSibling;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;

    try {
        // Ensure selectedCategory is set (fallback to default)
        if (!selectedCategory) {
            console.log('No category selected, using fallback');
            selectedCategory = { id: 1, name: 'General Support' };
        }

        // Create ticket directly with the message
        await createTicketWithMessage(message);
        input.value = '';
    } catch (error) {
        console.error('Error sending message:', error);
        showNotification('Failed to send message. Please try again.', 'error');
    } finally {
        // Restore button state
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Add Enter key support for category input
function handleCategoryEnter(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendCategoryMessage();
    }
}

// Submit custom issue
async function submitCustomIssue() {
    const name = document.getElementById('user-name').value.trim();
    const email = document.getElementById('user-email').value.trim();
    const description = document.getElementById('issue-description').value.trim();

    if (!description) {
        showNotification('Please describe your issue.', 'warning');
        return;
    }

    console.log('Submitting custom issue:', { name, email, description });

    // Ensure selectedCategory is set (fallback to default)
    if (!selectedCategory) {
        console.log('No category selected, using fallback');
        selectedCategory = { id: 1, name: 'General Support' };
    }

    currentUser = { name, email };
    await createTicketWithMessage(description);
}

// Create ticket with message
async function createTicketWithMessage(message) {
    try {
        if (debugMode) {
            console.group('🎫 Creating Ticket');
            console.log('Message:', message);
            console.log('Selected Category:', selectedCategory);
            console.log('Current User:', currentUser);
        }

        // Ensure we have a valid category (fallback to default)
        const categoryId = selectedCategory?.id || 1;
        const categoryName = selectedCategory?.name || 'General Support';

        const requestBody = {
            name: currentUser?.name || '',
            email: currentUser?.email || '',
            category_id: categoryId,
            subject: `${categoryName} Support Request`,
            message: message,
            // Add device information to ticket creation
            device_info: deviceContext || collectBasicDeviceInfo()
        };

        if (debugMode) {
            console.log('Request Body:', requestBody);
            console.log('Making API call to /api/tickets...');
        }

        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (debugMode) {
            console.log('Response Status:', response.status);
            console.log('Response OK:', response.ok);
        }

        if (!response.ok) {
            const errorText = await response.text();
            if (debugMode) {
                console.error('Response Error Text:', errorText);
            }

            // If server is unreachable, switch to offline mode
            if (response.status === 0 || response.status >= 500) {
                console.log('Server unreachable, switching to offline mode');
                createOfflineTicket(message);
                return;
            }

            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();

        if (debugMode) {
            console.log('Response Data:', data);
            console.groupEnd();
        } if (data.status === 'success') {
            currentTicketId = data.ticket_id;

            // Store the user_id in currentUser object for future message sending
            if (data.user_id && currentUser) {
                currentUser.id = data.user_id;
                if (debugMode) {
                    console.log('Updated currentUser with ID:', currentUser.id);
                }
            }

            // Track successful ticket creation with device info
            if (deviceTracker) {
                deviceTracker.trackTicketCreation(data.ticket_id, categoryId);
            }

            showNotification('Ticket created successfully!', 'success');
            startLiveChat(message);

            // Try to sync any offline tickets
            syncOfflineTickets();
        } else {
            logError('createTicketWithMessage', new Error(`API Error: ${data.message}`), data);
            showNotification(data.message || 'Error creating ticket. Please try again.', 'error');
        }
    } catch (error) {
        if (debugMode) {
            console.groupEnd();
        }

        logError('createTicketWithMessage', error, { message, selectedCategory, currentUser });

        // If it's a network error, switch to offline mode
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            console.log('Network error, switching to offline mode');
            createOfflineTicket(message);
        } else {
            showNotification(`System error: ${error.message}. Please try again later.`, 'error');
        }
    }
}

// Handle offline ticket creation
function createOfflineTicket(message) {
    const ticketId = Date.now(); // Simple ID generation for offline mode
    const ticket = {
        id: ticketId,
        message: message,
        category: selectedCategory?.name || 'General Support',
        name: currentUser?.name || 'Anonymous',
        email: currentUser?.email || '',
        timestamp: new Date().toISOString(),
        status: 'offline-pending'
    };

    // Store in localStorage for persistence
    offlineTickets.push(ticket);
    localStorage.setItem('offlineTickets', JSON.stringify(offlineTickets));

    currentTicketId = ticketId;

    showNotification('Currently offline. Your ticket has been saved and will be sent when connection is restored.', 'info');
    startLiveChat(message);

    // Add offline indicator message
    setTimeout(() => {
        addChatMessage('Thank you for your message. We are currently experiencing connectivity issues, but your ticket has been saved. We will respond as soon as possible.', 'system', new Date().toISOString());
    }, 1000);
}

// Try to sync offline tickets when connection is restored
async function syncOfflineTickets() {
    const savedTickets = localStorage.getItem('offlineTickets');
    if (!savedTickets) return;

    const tickets = JSON.parse(savedTickets);
    const pendingTickets = tickets.filter(t => t.status === 'offline-pending');

    for (const ticket of pendingTickets) {
        try {
            const response = await fetch('/api/tickets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: ticket.name,
                    email: ticket.email,
                    category_id: selectedCategory?.id || 1,
                    subject: `${ticket.category} Support Request`,
                    message: ticket.message
                })
            });

            if (response.ok) {
                // Mark as synced
                ticket.status = 'synced';
                showNotification('Offline ticket has been successfully sent!', 'success');
            }
        } catch (error) {
            console.log('Still offline, will retry later');
            break;
        }
    }

    // Update localStorage
    localStorage.setItem('offlineTickets', JSON.stringify(tickets));
}

// Start live chat
function startLiveChat(initialMessage) {
    chatState = 'chat';
    hideAllChatSections();

    const liveChatDiv = document.getElementById('live-chat');
    liveChatDiv.style.display = 'block';

    document.getElementById('live-chat-input').style.display = 'block';
    document.getElementById('ticket-number').textContent = currentTicketId;

    // Join the WebSocket room for this ticket
    if (window.chatSocket && currentTicketId) {
        chatSocket.emit('join_room', { ticket_id: currentTicketId });
        console.log(`🚪 User joined room for ticket #${currentTicketId}`);
    }

    // Load and display messages
    loadChatMessages();

    // Start auto-refresh for new messages
    startMessageRefresh();

    // Add initial message to chat
    if (initialMessage) {
        addChatMessage(initialMessage, 'user', new Date().toISOString());
    }
}

// Load chat messages
async function loadChatMessages() {
    if (!currentTicketId) return;

    try {
        const response = await fetch(`/api/tickets/${currentTicketId}/messages`);
        const data = await response.json();

        // Check if this is a ticket details response (includes status)
        let messages, ticketStatus;

        if (data.messages && data.status) {
            // This is a full ticket response
            messages = data.messages;
            ticketStatus = data.status;
        } else if (Array.isArray(data)) {
            // This is just messages array
            messages = data;
            // Get ticket status separately
            try {
                const ticketResponse = await fetch(`/api/tickets/${currentTicketId}`);
                if (ticketResponse.ok) {
                    const ticketData = await ticketResponse.json();
                    ticketStatus = ticketData.status;
                }
            } catch (e) {
                console.log('Could not fetch ticket status:', e);
            }
        } else {
            messages = [];
        }

        const messagesContainer = document.getElementById('chat-messages-container');
        messagesContainer.innerHTML = messages.map(msg =>
            createChatMessageHTML(msg.content, msg.is_admin ? 'admin' : 'user', msg.created_at)
        ).join('');

        // Check if ticket has been closed/resolved
        if (ticketStatus && (ticketStatus === 'resolved' || ticketStatus === 'closed')) {
            handleTicketClosure(ticketStatus);
        }

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        console.error('Error loading chat messages:', error);
    }
}

// Add chat message to UI
function addChatMessage(content, type, timestamp) {
    const messagesContainer = document.getElementById('chat-messages-container');
    const messageHTML = createChatMessageHTML(content, type, timestamp);
    messagesContainer.insertAdjacentHTML('beforeend', messageHTML);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Create chat message HTML
function createChatMessageHTML(content, type, timestamp) {
    const avatar = type === 'admin' ? 'A' : 'U';
    const time = formatTime(timestamp);

    return `
        <div class="message ${type}">
            ${content}
            <div class="message-time">${time}</div>
        </div>
    `;
}

// Send message in live chat
async function sendMessage() {
    // Try to get message from either input field
    const messageInput = document.getElementById('message-input');
    const liveChatInput = document.getElementById('live-chat-message-input');
    const input = liveChatInput || messageInput;
    const message = input ? input.value.trim() : '';

    if (!message || !currentTicketId) {
        console.log('❌ Cannot send message: missing message or ticket ID');
        return;
    }
    try {
        if (window.chatSocket && chatSocket.connected) {
            // Only send if connected and in the right room
            chatSocket.emit('send_message', {
                ticket_id: currentTicketId,
                content: message,
                is_admin: false
            });
            // Do NOT add message to UI here; wait for server confirmation
            input.value = '';
            console.log('✅ Message sent via WebSocket');
        } else {
            alert('Live chat is not connected. Please wait for connection.');
        }
    } catch (error) {
        console.error('❌ Error sending message:', error);
    }
}

// Handle enter key in chat
function handleChatEnter(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Show solution modal
function showSolution(question, solution) {
    const modal = new bootstrap.Modal(document.getElementById('solutionModal'));
    document.getElementById('solution-content').innerHTML = `
        <div class="solution-content">
            <h6 class="text-primary mb-3">
                <i class="fas fa-question-circle"></i> ${question}
            </h6>
            <div class="solution-text">
                ${solution}
            </div>
        </div>
    `;
    modal.show();
}

// Mark as solved
function markAsSolved() {
    bootstrap.Modal.getInstance(document.getElementById('solutionModal')).hide();

    setTimeout(() => {
        const feedbackModal = new bootstrap.Modal(document.getElementById('feedbackModal'));
        feedbackModal.show();
    }, 300);
}

// Need more help
function needMoreHelp() {
    bootstrap.Modal.getInstance(document.getElementById('solutionModal')).hide();
    showCustomIssueForm();
}

// Toggle chat widget
function toggleChat() {
    const widget = document.getElementById('chat-widget');
    const minimizeBtn = document.querySelector('.minimize-btn i');
    const fabContainer = document.getElementById('fab-container');

    widget.classList.toggle('minimized');

    if (widget.classList.contains('minimized')) {
        minimizeBtn.className = 'fas fa-plus';
        stopMessageRefresh();
    } else {
        minimizeBtn.className = 'fas fa-minus';
        if (chatState === 'chat') {
            startMessageRefresh();
        }
    }
}

// Close chat completely
function closeChat() {
    const widget = document.getElementById('chat-widget');
    const fabContainer = document.getElementById('fab-container');

    widget.classList.remove('active');
    fabContainer.style.display = 'block';

    stopMessageRefresh();
    resetChatState();
}

// Reset chat state
function resetChatState() {
    currentTicketId = null;
    selectedCategory = null;
    currentUser = null;
    chatState = 'welcome';

    // Clear forms
    document.getElementById('user-name').value = '';
    document.getElementById('user-email').value = '';
    document.getElementById('issue-description').value = '';
    document.getElementById('category-message-input').value = '';
    document.getElementById('message-input').value = '';
}

// Start message refresh interval
function startMessageRefresh() {
    if (messageRefreshInterval) return;

    messageRefreshInterval = setInterval(() => {
        if (chatState === 'chat' && currentTicketId) {
            loadChatMessages();
        }
    }, 5000); // Refresh every 5 seconds
}

// Stop message refresh interval
function stopMessageRefresh() {
    if (messageRefreshInterval) {
        clearInterval(messageRefreshInterval);
        messageRefreshInterval = null;
    }
}

// Rating functions
function setRating(rating) {
    document.querySelectorAll('.rating-stars i').forEach((star, index) => {
        star.classList.toggle('active', index < rating);
    });
}

function highlightStars(rating) {
    document.querySelectorAll('.rating-stars i').forEach((star, index) => {
        star.style.color = index < rating ? '#ffc107' : '#ddd';
    });
}

// Submit feedback
async function submitFeedback() {
    const rating = document.querySelectorAll('.rating-stars i.active').length;
    const feedback = document.getElementById('feedback-text').value.trim();

    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ticket_id: currentTicketId,
                rating: rating,
                feedback: feedback
            })
        });

        if (response.ok) {
            showNotification('Thank you for your feedback!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('feedbackModal')).hide();
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
    }
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)} me-2"></i>
        ${message}
    `;

    document.body.appendChild(notification);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'warning': 'exclamation-triangle',
        'error': 'times-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Add CSS for slideOutRight animation
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// Utility functions
function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopMessageRefresh();
});

// Auto-show FAB after page load
window.addEventListener('load', () => {
    setTimeout(() => {
        const fabContainer = document.getElementById('fab-container');
        if (fabContainer) {
            fabContainer.style.display = 'block';
        }
    }, 2000);
});

// Submit new ticket
async function submitTicket() {
    const name = document.getElementById('user-name').value.trim();
    const email = document.getElementById('user-email').value.trim();
    const message = document.getElementById('ticket-message').value.trim();

    if (!message) {
        addMessage('Please describe your issue.', 'system');
        return;
    }

    try {
        const response = await fetch('/api/tickets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                email,
                category_id: selectedCategory.id,
                subject: `${selectedCategory.name} Support Request`,
                message
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            currentTicketId = data.ticket_id;
            document.getElementById('chat-input').style.display = 'flex';
            addMessage('Thank you! We have created a ticket for your issue. Our support team will respond shortly.', 'system');
            addMessage(message, 'user');
        } else {
            addMessage('Error creating ticket. Please try again.', 'system');
        }
    } catch (error) {
        console.error('Error submitting ticket:', error);
        addMessage('System error. Please try again later.', 'system');
    }
}



// Toggle chat widget
function toggleChat() {
    const widget = document.getElementById('chat-widget');
    widget.classList.toggle('minimized');

    const minimizeBtn = document.querySelector('.minimize-btn');
    minimizeBtn.textContent = widget.classList.contains('minimized') ? '+' : '−';
}

// Helper function to add a message to the chat
function addMessage(content, type = 'system') {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = `
        ${content}
        <div class="message-time">${new Date().toLocaleTimeString()}</div>
    `;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Helper function to add HTML content to messages
function addHTML(html) {
    const messagesDiv = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.innerHTML = html;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Event listener for Enter key in message input
document.getElementById('message-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Test API connectivity
async function testApiConnection() {
    try {
        if (debugMode) {
            console.group('🔌 Testing API Connection');
        }

        console.log('Testing API connection...');
        const response = await fetch('/api/health');

        if (response.ok) {
            const data = await response.json();
            if (debugMode) {
                console.log('✅ API connection successful:', data);
                console.groupEnd();
            }
            return true;
        } else {
            if (debugMode) {
                console.warn('❌ API health check failed:', response.status);
                console.groupEnd();
            }

            // Test categories endpoint as fallback
            try {
                const categoriesResponse = await fetch('/api/categories');
                if (categoriesResponse.ok) {
                    console.log('Categories endpoint working, health endpoint may be down');
                    return true;
                }
            } catch (e) {
                console.warn('Both health and categories endpoints failed');
            }

            showNotification('Support system is experiencing issues. Some features may be limited.', 'warning');
            return false;
        }
    } catch (error) {
        if (debugMode) {
            console.groupEnd();
        }

        logError('testApiConnection', error);
        console.error('API connection test failed:', error);
        showNotification('Unable to connect to support system. You can still submit tickets which will be sent when connection is restored.', 'info');
        return false;
    }
}

// Handle ticket closure/resolution
function handleTicketClosure(status) {
    // Only show closure handling once
    if (chatState === 'closed') return;

    console.log(`Ticket ${currentTicketId} has been ${status}`);

    // Update chat state
    chatState = 'closed';

    // Disable chat input
    const messageInput = document.getElementById('message-input');
    const sendButton = document.querySelector('#live-chat-input button');

    if (messageInput) {
        messageInput.disabled = true;
        messageInput.placeholder = `This conversation has been ${status}`;
    }

    if (sendButton) {
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-check"></i>';
    }

    // Update chat status indicator
    const statusIndicator = document.querySelector('.chat-status .status-indicator');
    if (statusIndicator) {
        statusIndicator.innerHTML = `
            <i class="fas fa-check-circle text-success"></i>
            <span>${status === 'resolved' ? 'Issue Resolved' : 'Chat Closed'}</span>
        `;
    }

    // Stop message refresh since ticket is closed
    stopMessageRefresh();

    // Show notification
    const statusMessage = status === 'resolved'
        ? 'Your issue has been resolved! Thank you for contacting support.'
        : 'This conversation has been closed.';

    showNotification(statusMessage, 'success');

    // Show feedback modal after a brief delay
    setTimeout(() => {
        showFeedbackModal();
    }, 2000);
}

// Show feedback modal
function showFeedbackModal() {
    // Create feedback modal if it doesn't exist
    let feedbackModal = document.getElementById('feedbackModal');

    if (!feedbackModal) {
        feedbackModal = document.createElement('div');
        feedbackModal.className = 'modal fade';
        feedbackModal.id = 'feedbackModal';
        feedbackModal.setAttribute('tabindex', '-1');
        feedbackModal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-star text-warning me-2"></i>
                            How was your experience?
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-4">
                            <p class="text-muted">Please rate your support experience</p>
                            <div class="rating-stars">
                                <i class="fas fa-star" data-rating="1"></i>
                                <i class="fas fa-star" data-rating="2"></i>
                                <i class="fas fa-star" data-rating="3"></i>
                                <i class="fas fa-star" data-rating="4"></i>
                                <i class="fas fa-star" data-rating="5"></i>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label for="feedback-text" class="form-label">Additional feedback (optional)</label>
                            <textarea class="form-control" id="feedback-text" rows="3" 
                                placeholder="Tell us about your experience..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Skip</button>
                        <button type="button" class="btn btn-primary" onclick="submitFeedback()">Submit Feedback</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(feedbackModal);

        // Add event listeners for rating stars
        feedbackModal.querySelectorAll('.rating-stars i').forEach(star => {
            star.addEventListener('click', function () {
                const rating = this.dataset.rating;
                setRating(rating);
            });

            star.addEventListener('mouseenter', function () {
                const rating = this.dataset.rating;
                highlightStars(rating);
            });
        });

        // Reset stars on mouse leave
        feedbackModal.querySelector('.rating-stars').addEventListener('mouseleave', () => {
            const activeRating = feedbackModal.querySelector('.rating-stars i.active:last-of-type')?.dataset.rating || 0;
            highlightStars(activeRating);
        });
    }

    // Show the modal
    const bootstrapModal = new bootstrap.Modal(feedbackModal);
    bootstrapModal.show();
}

// File Upload Functionality
let selectedFiles = [];
let dragCounter = 0;

function initializeFileUpload() {
    // Initialize both form and chat file upload areas
    initializeFormFileUpload();
    initializeChatFileUpload();
}

function initializeFormFileUpload() {
    const fileInput = document.getElementById('form-file-input');
    const fileUploadArea = document.getElementById('form-file-upload-area');
    const filePreview = document.getElementById('form-file-preview');

    if (!fileInput || !fileUploadArea || !filePreview) {
        console.warn('Form file upload elements not found, skipping initialization');
        return;
    }

    // File input change
    fileInput.addEventListener('change', (e) => handleFileSelect(e, 'form'));

    // Drag and drop events
    fileUploadArea.addEventListener('dragenter', handleDragEnter);
    fileUploadArea.addEventListener('dragover', handleDragOver);
    fileUploadArea.addEventListener('dragleave', handleDragLeave);
    fileUploadArea.addEventListener('drop', (e) => handleFileDrop(e, 'form'));

    // Click to browse
    fileUploadArea.addEventListener('click', () => {
        fileInput.click();
    });
}

function initializeChatFileUpload() {
    const fileInput = document.getElementById('file-input');
    const fileUploadArea = document.getElementById('file-upload-area');
    const filePreview = document.getElementById('file-preview');
    const attachButton = document.getElementById('attach-btn');

    if (!fileInput || !fileUploadArea || !filePreview || !attachButton) {
        console.warn('Chat file upload elements not found, skipping initialization');
        return;
    }

    // Attach button click
    attachButton.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => handleFileSelect(e, 'chat'));

    // Drag and drop events
    fileUploadArea.addEventListener('dragenter', handleDragEnter);
    fileUploadArea.addEventListener('dragover', handleDragOver);
    fileUploadArea.addEventListener('dragleave', handleDragLeave);
    fileUploadArea.addEventListener('drop', (e) => handleFileDrop(e, 'chat'));

    // Click to browse
    fileUploadArea.addEventListener('click', () => {
        fileInput.click();
    });
}

function handleDragEnter(e) {
    e.preventDefault();
    dragCounter++;
    const fileUploadArea = document.getElementById('file-upload-area');
    fileUploadArea.classList.add('drag-active');
}

function handleDragOver(e) {
    e.preventDefault();
}

function handleDragLeave(e) {
    e.preventDefault();
    dragCounter--;
    if (dragCounter === 0) {
        const fileUploadArea = document.getElementById('file-upload-area');
        fileUploadArea.classList.remove('drag-active');
    }
}

function handleFileDrop(e, context = 'chat') {
    e.preventDefault();
    dragCounter = 0;
    const fileUploadArea = document.getElementById(context === 'form' ? 'form-file-upload-area' : 'file-upload-area');
    fileUploadArea.classList.remove('drag-active');

    const files = Array.from(e.dataTransfer.files);
    processFiles(files, context);
}

function handleFileSelect(e, context = 'chat') {
    const files = Array.from(e.target.files);
    processFiles(files, context);
}

function processFiles(files, context = 'chat') {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    files.forEach(file => {
        // Validate file type
        if (!allowedTypes.includes(file.type)) {
            showErrorMessage(`File type not supported: ${file.name}. Please upload images only.`);
            return;
        }

        // Validate file size
        if (file.size > maxSize) {
            showErrorMessage(`File too large: ${file.name}. Maximum size is 10MB.`);
            return;
        }

        // Add to selected files
        selectedFiles.push(file);
        displayFilePreview(file, context);
    });

    // Update upload area visibility
    updateFileUploadArea(context);
}

function displayFilePreview(file, context = 'chat') {
    const filePreview = document.getElementById(context === 'form' ? 'form-file-preview' : 'file-preview');

    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.innerHTML = `
        <div class="file-info">
            <img src="${URL.createObjectURL(file)}" alt="Preview" class="file-thumbnail">
            <div class="file-details">
                <span class="file-name">${file.name}</span>
                <span class="file-size">${formatFileSize(file.size)}</span>
            </div>
        </div>
        <button type="button" class="btn-remove" onclick="removeFile('${file.name}', '${context}')">
            <i class="fas fa-times"></i>
        </button>
    `;

    filePreview.appendChild(fileItem);
}

function removeFile(fileName, context = 'chat') {
    selectedFiles = selectedFiles.filter(file => file.name !== fileName);

    const filePreview = document.getElementById(context === 'form' ? 'form-file-preview' : 'file-preview');
    const fileItems = filePreview.querySelectorAll('.file-item');

    fileItems.forEach(item => {
        const fileNameElement = item.querySelector('.file-name');
        if (fileNameElement && fileNameElement.textContent === fileName) {
            // Revoke object URL to prevent memory leaks
            const img = item.querySelector('.file-thumbnail');
            if (img && img.src.startsWith('blob:')) {
                URL.revokeObjectURL(img.src);
            }
            item.remove();
        }
    });

    updateFileUploadArea(context);
}

function updateFileUploadArea(context = 'chat') {
    const fileUploadArea = document.getElementById(context === 'form' ? 'form-file-upload-area' : 'file-upload-area');
    const filePreview = document.getElementById(context === 'form' ? 'form-file-preview' : 'file-preview');

    if (selectedFiles.length > 0) {
        fileUploadArea.style.display = 'none';
        filePreview.style.display = 'block';
    } else {
        fileUploadArea.style.display = 'block';
        filePreview.style.display = 'none';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function clearFileSelection() {
    // Revoke all object URLs to prevent memory leaks
    selectedFiles.forEach(file => {
        // Clear both form and chat file previews
        ['form-file-preview', 'file-preview'].forEach(previewId => {
            const filePreview = document.getElementById(previewId);
            if (filePreview) {
                const fileItems = filePreview.querySelectorAll('.file-item');
                fileItems.forEach(item => {
                    const img = item.querySelector('.file-thumbnail');
                    if (img && img.src.startsWith('blob:')) {
                        URL.revokeObjectURL(img.src);
                    }
                });
            }
        });
    });

    selectedFiles = [];

    // Clear both file previews
    ['form-file-preview', 'file-preview'].forEach(previewId => {
        const filePreview = document.getElementById(previewId);
        if (filePreview) {
            filePreview.innerHTML = '';
        }
    });

    // Update both upload areas
    updateFileUploadArea('form');
    updateFileUploadArea('chat');

    // Reset both file inputs
    ['form-file-input', 'file-input'].forEach(inputId => {
        const fileInput = document.getElementById(inputId);
        if (fileInput) {
            fileInput.value = '';
        }
    });
}

// Modified submitTicket function to handle file uploads
async function submitTicketWithAttachment(ticketData) {
    try {
        const formData = new FormData();

        // Add text data
        formData.append('name', ticketData.name);
        formData.append('email', ticketData.email);
        formData.append('category_id', ticketData.category_id);
        formData.append('subject', ticketData.subject);
        formData.append('message', ticketData.message);

        // Add file if selected
        if (selectedFiles.length > 0) {
            formData.append('file', selectedFiles[0]); // For now, handle one file
        }

        const response = await fetch('/api/tickets/with-attachment', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        if (result.status === 'success') {
            currentTicketId = result.ticket_id;

            // Store the user_id in currentUser object for future message sending
            if (result.user_id && currentUser) {
                currentUser.id = result.user_id;
                console.log('Updated currentUser with ID from attachment upload:', currentUser.id);
            }

            clearFileSelection();
            return result;
        } else {
            throw new Error(result.message || 'Failed to create ticket');
        }

    } catch (error) {
        logError('submitTicketWithAttachment', error, ticketData);
        throw error;
    }
}

// Modified sendMessage function to handle file uploads
async function sendMessageWithAttachment(content, isAdmin = false) {
    try {
        if (!currentTicketId) {
            throw new Error('No active ticket');
        }

        const formData = new FormData();
        formData.append('content', content);
        formData.append('user_id', currentUser?.id || '');
        formData.append('is_admin', isAdmin.toString());

        // Add file if selected
        if (selectedFiles.length > 0) {
            formData.append('file', selectedFiles[0]); // For now, handle one file
        }

        const response = await fetch(`/api/tickets/${currentTicketId}/messages/with-attachment`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            clearFileSelection();
            return result;
        } else {
            throw new Error(result.message || 'Failed to send message');
        }

    } catch (error) {
        logError('sendMessageWithAttachment', error, { content, isAdmin });
        throw error;
    }
}

// Update the existing submitTicket function to use file upload when files are selected
const originalSubmitTicket = window.submitTicket;
window.submitTicket = async function (ticketData) {
    if (selectedFiles.length > 0) {
        return await submitTicketWithAttachment(ticketData);
    } else {
        return await originalSubmitTicket(ticketData);
    }
};

// Update the existing sendMessage function to use file upload when files are selected
const originalSendMessage = window.sendMessage;
window.sendMessage = async function (content, isAdmin = false) {
    if (selectedFiles.length > 0) {
        return await sendMessageWithAttachment(content, isAdmin);
    } else {
        return await originalSendMessage(content, isAdmin);
    }
};

// Initialize file upload when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    // Add a small delay to ensure all elements are rendered
    setTimeout(() => {
        initializeFileUpload();
        initializePasteHandler();
    }, 100);
});

// Paste handling functionality
function initializePasteHandler() {
    // Add paste event listener to message input fields
    const messageInput = document.getElementById('message-input');
    const liveChatInput = document.getElementById('live-chat-message-input');
    const categoryInput = document.getElementById('category-message-input');
    const issueDescInput = document.getElementById('issue-description');

    if (liveChatInput) {
        liveChatInput.addEventListener('paste', handlePaste);
        console.log('Added paste handler to live chat input');
    }
    if (categoryInput) {
        categoryInput.addEventListener('paste', handlePaste);
        console.log('Added paste handler to category input');
    }
    if (issueDescInput) {
        issueDescInput.addEventListener('paste', handlePaste);
        console.log('Added paste handler to issue description');
    }
    if (messageInput) {
        messageInput.addEventListener('paste', handlePaste);
        console.log('Added paste handler to message input');
    }

    // Also add to the chat body for broader paste support
    const chatBody = document.querySelector('.chat-body');
    if (chatBody) {
        chatBody.addEventListener('paste', handlePaste);
        // Make chat body focusable for paste events
        chatBody.setAttribute('tabindex', '0');
        console.log('Added paste handler to chat body');
    }

    console.log('Paste handler initialization complete');
}

function handlePaste(event) {
    console.log('Paste event triggered:', event);

    const clipboardItems = event.clipboardData || event.originalEvent.clipboardData;

    if (!clipboardItems) {
        console.log('No clipboard data found');
        return;
    }

    const items = clipboardItems.items;
    let hasImage = false;

    console.log('Clipboard items:', items.length);

    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        console.log('Item type:', item.type);

        // Check if the item is an image
        if (item.type.indexOf('image') !== -1) {
            hasImage = true;
            event.preventDefault(); // Prevent default paste behavior

            console.log('Image detected in clipboard');
            const file = item.getAsFile();
            if (file) {
                console.log('File obtained from clipboard:', file.name, file.size);
                handlePastedImage(file);
            }
            break;
        }
    }
    // If no image was pasted, allow normal text paste
    if (!hasImage) {
        console.log('No image found in clipboard, allowing normal paste');
        return;
    }
}

function handlePastedImage(file) {
    console.log('Processing pasted image:', file);

    // Validate file size
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showNotification('Image too large. Maximum size is 10MB.', 'error');
        return;
    }

    // Clear existing file selection and add the pasted image
    clearFileSelection();
    selectedFiles = [file];

    console.log('Selected files updated:', selectedFiles);

    // Show inline preview in chat
    displayInlinePastedImage(file);

    // Update file upload areas
    updateFileUploadArea('chat');
    updateFileUploadArea('form');

    // Show file preview in designated preview areas
    displayFilePreview(file, 'chat');

    // Show success message
    showNotification('Image pasted successfully! You can now send your message.', 'success');

    // Focus on the appropriate input field
    setTimeout(() => {
        const activeInput = document.activeElement;
        if (activeInput && (activeInput.tagName === 'INPUT' || activeInput.tagName === 'TEXTAREA')) {
            activeInput.focus();
        } else {
            // Focus on the most appropriate message input based on current state
            const messageInput = document.getElementById('live-chat-message-input') ||
                document.getElementById('category-message-input') ||
                document.getElementById('message-input');
            if (messageInput && messageInput.style.display !== 'none') {
                messageInput.focus();
            }
        }
    }, 100);
}

function displayInlinePastedImage(file) {
    // Find the appropriate container for the preview
    let chatContainer = document.getElementById('chat-messages-container') ||
        document.querySelector('.chat-messages') ||
        document.querySelector('.messages');

    if (!chatContainer) {
        console.warn('No chat container found, creating temporary preview');
        // Create a temporary preview area if no chat container exists
        const chatBody = document.querySelector('.chat-body');
        if (chatBody) {
            let tempPreview = document.getElementById('temp-image-preview');
            if (!tempPreview) {
                tempPreview = document.createElement('div');
                tempPreview.id = 'temp-image-preview';
                tempPreview.style.cssText = 'margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 8px;';
                chatBody.appendChild(tempPreview);
            }
            chatContainer = tempPreview;
        } else {
            return; // Can't display preview
        }
    }

    // Remove any existing pasted image preview
    const existingPreview = chatContainer.querySelector('.pasted-image-preview');
    if (existingPreview) {
        const img = existingPreview.querySelector('.pasted-image-thumbnail');
        if (img && img.src.startsWith('blob:')) {
            URL.revokeObjectURL(img.src);
        }
        existingPreview.remove();
    }

    // Create preview message
    const previewMessage = document.createElement('div');
    previewMessage.className = 'message user-message pasted-image-preview';
    previewMessage.innerHTML = `
        <div class="message-content">
            <div class="pasted-image-container">
                <div class="pasted-image-header">
                    <i class="fas fa-paperclip text-primary"></i>
                    <span>Pasted Image: ${file.name || 'clipboard-image.png'}</span>
                    <button class="btn btn-sm btn-outline-danger ms-2" onclick="removePastedImage(this)">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="pasted-image-preview-content">
                    <img src="${URL.createObjectURL(file)}" alt="Pasted image" class="pasted-image-thumbnail" style="max-width: 200px; max-height: 200px; border-radius: 8px; border: 1px solid #ddd;">
                </div>
                <div class="pasted-image-info">
                    <small class="text-muted">Size: ${formatFileSize(file.size)} | Ready to send</small>
                </div>
            </div>
        </div>
        <div class="message-time">${new Date().toLocaleTimeString()}</div>
    `;

    // Add the preview to the container
    chatContainer.appendChild(previewMessage);

    // Scroll to show the preview
    previewMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    console.log('Pasted image preview displayed');
}

function removePastedImage(button) {
    // Remove the preview message
    const previewMessage = button.closest('.pasted-image-preview');
    if (previewMessage) {
        // Revoke object URL to prevent memory leaks
        const img = previewMessage.querySelector('.pasted-image-thumbnail');
        if (img && img.src.startsWith('blob:')) {
            URL.revokeObjectURL(img.src);
        }
        previewMessage.remove();
    }

    // Clear selected files
    clearFileSelection();

    showInfoMessage('Image removed. You can paste another image if needed.');
}

function showSuccessMessage(message) {
    showNotification(message, 'success');
}

function showInfoMessage(message) {
    showNotification(message, 'info');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        animation: slideInRight 0.3s ease-out;
    `;

    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Enhanced sendMessage function to handle pasted images
const originalSendMessageFunction = window.sendMessage;
window.sendMessage = async function (content, isAdmin = false) {
    // Get the actual message content from input if not provided
    if (!content) {
        const messageInput = document.getElementById('message-input') || document.getElementById('live-chat-message-input');
        content = messageInput ? messageInput.value.trim() : '';
    }

    // If there are selected files (including pasted images), use file upload
    if (selectedFiles.length > 0) {
        try {
            const result = await sendMessageWithAttachment(content, isAdmin);

            // Clear the pasted image preview
            const pastedPreviews = document.querySelectorAll('.pasted-image-preview');
            pastedPreviews.forEach(preview => {
                const img = preview.querySelector('.pasted-image-thumbnail');
                if (img && img.src.startsWith('blob:')) {
                    URL.revokeObjectURL(img.src);
                }
                preview.remove();
            });

            // Clear message input
            const messageInput = document.getElementById('message-input') || document.getElementById('live-chat-message-input');
            if (messageInput) {
                messageInput.value = '';
            }

            return result;
        } catch (error) {
            showErrorMessage('Failed to send message with image. Please try again.');
            throw error;
        }
    } else {
        // Use original send message function
        return await originalSendMessageFunction(content, isAdmin);
    }
};

// File upload functionality
let isFileUploadVisible = false;

// Initialize file upload when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    setupFileUploadHandlers();
});

function setupFileUploadHandlers() {
    // Attach button handler
    const attachBtn = document.getElementById('attach-btn');
    if (attachBtn) {
        attachBtn.addEventListener('click', toggleFileUpload);
    }

    // File upload areas
    setupFileUploadArea('file-upload-area', 'file-input');
    setupFileUploadArea('form-file-upload-area', 'form-file-input');
}

function toggleFileUpload() {
    const fileUploadArea = document.getElementById('file-upload-area');
    const filePreview = document.getElementById('file-preview');

    if (!fileUploadArea) return;

    isFileUploadVisible = !isFileUploadVisible;

    if (isFileUploadVisible) {
        fileUploadArea.classList.add('active');
        if (filePreview && filePreview.style.display !== 'none') {
            filePreview.style.display = 'block';
        }
    } else {
        fileUploadArea.classList.remove('active');
        if (filePreview && filePreview.children.length === 0) {
            filePreview.style.display = 'none';
        }
    }
}

function setupFileUploadArea(uploadAreaId, fileInputId) {
    const uploadArea = document.getElementById(uploadAreaId);
    const fileInput = document.getElementById(fileInputId);

    if (!uploadArea || !fileInput) return;

    // Click to browse
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // File selection handler
    fileInput.addEventListener('change', (e) => {
        handleFileSelection(e.target.files, uploadAreaId);
    });

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-active');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-active');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-active');
        handleFileSelection(e.dataTransfer.files, uploadAreaId);
    });
}

function handleFileSelection(files, uploadAreaId) {
    const previewId = uploadAreaId.includes('form') ? 'form-file-preview' : 'file-preview';
    const preview = document.getElementById(previewId);

    if (!preview) return;

    Array.from(files).forEach(file => {
        if (isValidFile(file)) {
            addFileToPreview(file, preview);
            selectedFiles.push(file);
        } else {
            showErrorMessage(`Invalid file: ${file.name}. Only images (JPG, PNG, GIF) up to 10MB are allowed.`);
        }
    });

    if (preview.children.length > 0) {
        preview.style.display = 'block';
    }
}

function isValidFile(file) {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    return allowedTypes.includes(file.type) && file.size <= maxSize;
}

function addFileToPreview(file, preview) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';

    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info';

    // Create thumbnail
    const thumbnail = document.createElement('img');
    thumbnail.className = 'file-thumbnail';

    const reader = new FileReader();
    reader.onload = (e) => {
        thumbnail.src = e.target.result;
    };
    reader.readAsDataURL(file);

    // File details
    const details = document.createElement('div');
    details.className = 'file-details';
    details.innerHTML = `
        <div class="file-name">${file.name}</div>
        <div class="file-size">${formatFileSize(file.size)}</div>
    `;

    // Remove button
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn-remove';
    removeBtn.innerHTML = '<i class="fas fa-times"></i>';
    removeBtn.onclick = () => {
        removeFileFromPreview(fileItem, file);
    };

    fileInfo.appendChild(thumbnail);
    fileInfo.appendChild(details);
    fileItem.appendChild(fileInfo);
    fileItem.appendChild(removeBtn);

    preview.appendChild(fileItem);
}

function removeFileFromPreview(fileItem, file) {
    // Remove from selectedFiles array
    const index = selectedFiles.findIndex(f => f.name === file.name && f.size === file.size);
    if (index > -1) {
        selectedFiles.splice(index, 1);
    }

    // Remove from DOM
    fileItem.remove();

    // Hide preview if empty
    const preview = fileItem.closest('.file-preview');
    if (preview && preview.children.length === 0) {
        preview.style.display = 'none';

        // Hide file upload area if no files
        const uploadArea = document.getElementById('file-upload-area');
        if (uploadArea && selectedFiles.length === 0) {
            uploadArea.classList.remove('active');
            isFileUploadVisible = false;
        }
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
