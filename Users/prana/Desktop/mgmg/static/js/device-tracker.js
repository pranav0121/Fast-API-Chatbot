/**
 * Device Tracking JavaScript Integration
 * Captures device information on the client-side for better support analytics
 */

class DeviceTracker {
    constructor() {
        this.deviceInfo = this.collectDeviceInfo();
        this.sessionId = this.getOrCreateSessionId();
        this.startTime = new Date();
    }

    /**
     * Collect comprehensive device information
     */
    collectDeviceInfo() {
        const nav = navigator;
        const screen = window.screen;
        
        return {
            // Basic browser info
            userAgent: nav.userAgent,
            language: nav.language,
            languages: nav.languages ? Array.from(nav.languages) : [nav.language],
            cookieEnabled: nav.cookieEnabled,
            
            // Screen information
            screenWidth: screen.width,
            screenHeight: screen.height,
            colorDepth: screen.colorDepth,
            pixelDepth: screen.pixelDepth,
            
            // Viewport information
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
            
            // Device capabilities
            touchSupport: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
            
            // Platform detection
            platform: nav.platform,
            
            // Connection info (if available)
            connection: this.getConnectionInfo(),
            
            // Timezone
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            timezoneOffset: new Date().getTimezoneOffset(),
            
            // Hardware info (if available)
            hardwareConcurrency: nav.hardwareConcurrency,
            deviceMemory: nav.deviceMemory,
            
            // Timestamp
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Get network connection information
     */
    getConnectionInfo() {
        const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        if (conn) {
            return {
                effectiveType: conn.effectiveType,
                downlink: conn.downlink,
                rtt: conn.rtt,
                saveData: conn.saveData
            };
        }
        return null;
    }

    /**
     * Detect device type based on user agent and screen size
     */
    getDeviceType() {
        const ua = navigator.userAgent.toLowerCase();
        const width = window.innerWidth;
        
        // Check for mobile patterns
        if (/mobile|android|iphone|ipod|blackberry|windows phone/.test(ua)) {
            return 'mobile';
        }
        
        // Check for tablet patterns
        if (/ipad|tablet|kindle/.test(ua)) {
            return 'tablet';
        }
        
        // Screen size-based detection as fallback
        if (width <= 768) {
            return 'mobile';
        } else if (width <= 1024) {
            return 'tablet';
        }
        
        return 'desktop';
    }

    /**
     * Detect browser name and version
     */
    getBrowserInfo() {
        const ua = navigator.userAgent;
        let browser = 'Unknown';
        let version = '0.0';
        
        const browsers = [
            { name: 'Chrome', pattern: /Chrome\/([0-9.]+)/ },
            { name: 'Firefox', pattern: /Firefox\/([0-9.]+)/ },
            { name: 'Safari', pattern: /Version\/([0-9.]+).*Safari/ },
            { name: 'Edge', pattern: /Edge\/([0-9.]+)/ },
            { name: 'Opera', pattern: /Opera\/([0-9.]+)/ },
            { name: 'Internet Explorer', pattern: /MSIE ([0-9.]+)/ }
        ];
        
        for (const b of browsers) {
            const match = ua.match(b.pattern);
            if (match) {
                browser = b.name;
                version = match[1];
                break;
            }
        }
        
        return { name: browser, version: version };
    }

    /**
     * Detect operating system
     */
    getOSInfo() {
        const ua = navigator.userAgent;
        const platform = navigator.platform;
        
        const os_patterns = [
            { name: 'Windows', pattern: /Windows NT ([0-9.]+)/ },
            { name: 'macOS', pattern: /Mac OS X ([0-9_]+)/ },
            { name: 'iOS', pattern: /OS ([0-9_]+)/ },
            { name: 'Android', pattern: /Android ([0-9.]+)/ },
            { name: 'Linux', pattern: /Linux/ }
        ];
        
        for (const os of os_patterns) {
            const match = ua.match(os.pattern);
            if (match) {
                const version = match[1] ? match[1].replace(/_/g, '.') : 'Unknown';
                return { name: os.name, version: version };
            }
        }
        
        return { name: platform || 'Unknown', version: 'Unknown' };
    }

    /**
     * Get or create session ID
     */
    getOrCreateSessionId() {
        let sessionId = sessionStorage.getItem('device_session_id');
        if (!sessionId) {
            sessionId = this.generateSessionId();
            sessionStorage.setItem('device_session_id', sessionId);
        }
        return sessionId;
    }

    /**
     * Generate unique session ID
     */
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Get complete device context for support
     */
    getDeviceContext() {
        const browser = this.getBrowserInfo();
        const os = this.getOSInfo();
        
        return {
            sessionId: this.sessionId,
            deviceType: this.getDeviceType(),
            browser: browser,
            os: os,
            capabilities: {
                touchSupport: this.deviceInfo.touchSupport,
                cookiesEnabled: this.deviceInfo.cookieEnabled,
                webSocket: typeof WebSocket !== 'undefined',
                localStorage: typeof Storage !== 'undefined',
                sessionStorage: typeof sessionStorage !== 'undefined',
                fileAPI: typeof FileReader !== 'undefined',
                webRTC: typeof RTCPeerConnection !== 'undefined'
            },
            screen: {
                width: this.deviceInfo.screenWidth,
                height: this.deviceInfo.screenHeight,
                viewport: `${this.deviceInfo.viewportWidth}x${this.deviceInfo.viewportHeight}`
            },
            connection: this.deviceInfo.connection,
            language: this.deviceInfo.language,
            timezone: this.deviceInfo.timezone,
            userAgent: this.deviceInfo.userAgent
        };
    }

    /**
     * Track page view event
     */
    trackPageView(page = window.location.pathname) {
        this.trackEvent('page_view', {
            page: page,
            referrer: document.referrer,
            title: document.title
        });
    }

    /**
     * Track chat interaction
     */
    trackChatEvent(eventType, data = {}) {
        this.trackEvent('chat_' + eventType, data);
    }

    /**
     * Track ticket creation
     */
    trackTicketCreation(ticketId, categoryId = null) {
        this.trackEvent('ticket_create', {
            ticketId: ticketId,
            categoryId: categoryId
        });
    }

    /**
     * Generic event tracking
     */
    trackEvent(eventType, data = {}) {
        const eventData = {
            eventType: eventType,
            sessionId: this.sessionId,
            deviceContext: this.getDeviceContext(),
            timestamp: new Date().toISOString(),
            data: data
        };

        // Store locally for potential batch sending
        this.storeEvent(eventData);

        // Send to server if possible
        this.sendEventToServer(eventData);
    }

    /**
     * Store event locally
     */
    storeEvent(eventData) {
        try {
            const events = JSON.parse(localStorage.getItem('device_tracking_events') || '[]');
            events.push(eventData);
            
            // Keep only last 50 events to avoid storage bloat
            if (events.length > 50) {
                events.splice(0, events.length - 50);
            }
            
            localStorage.setItem('device_tracking_events', JSON.stringify(events));
        } catch (e) {
            console.warn('Could not store device tracking event:', e);
        }
    }

    /**
     * Send event to server
     */
    sendEventToServer(eventData) {
        try {
            // Use fetch if available, fallback to XMLHttpRequest
            if (typeof fetch !== 'undefined') {
                fetch('/api/device-tracking', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(eventData)
                }).catch(error => {
                    console.warn('Device tracking request failed:', error);
                });
            } else {
                // Fallback for older browsers
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/device-tracking', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.send(JSON.stringify(eventData));
            }
        } catch (e) {
            console.warn('Could not send device tracking data:', e);
        }
    }

    /**
     * Get compatibility warnings for current device
     */
    getCompatibilityWarnings() {
        const warnings = [];
        const browser = this.getBrowserInfo();
        const deviceType = this.getDeviceType();
        
        // Check for known compatibility issues
        if (browser.name === 'Internet Explorer') {
            warnings.push({
                type: 'error',
                message: 'Internet Explorer is not fully supported. Please use Chrome, Firefox, or Edge for the best experience.'
            });
        }
        
        if (deviceType === 'mobile' && browser.name === 'Safari') {
            warnings.push({
                type: 'warning',
                message: 'Some features may be limited on mobile Safari. Consider using Chrome mobile for full functionality.'
            });
        }
        
        // Check for missing capabilities
        if (!this.deviceInfo.cookieEnabled) {
            warnings.push({
                type: 'warning',
                message: 'Cookies are disabled. Some features may not work correctly.'
            });
        }
        
        if (typeof WebSocket === 'undefined') {
            warnings.push({
                type: 'error',
                message: 'WebSocket is not supported. Real-time chat may not work.'
            });
        }
        
        return warnings;
    }

    /**
     * Send compatibility info to support team
     */
    reportCompatibilityIssue(description) {
        this.trackEvent('compatibility_issue', {
            description: description,
            warnings: this.getCompatibilityWarnings(),
            deviceContext: this.getDeviceContext()
        });
    }
}

// Initialize device tracker when DOM is ready
let deviceTracker;

document.addEventListener('DOMContentLoaded', function() {
    try {
        deviceTracker = new DeviceTracker();
        
        // Track initial page view
        deviceTracker.trackPageView();
        
        // Show compatibility warnings if any
        const warnings = deviceTracker.getCompatibilityWarnings();
        if (warnings.length > 0) {
            console.group('Device Compatibility Warnings:');
            warnings.forEach(warning => {
                if (warning.type === 'error') {
                    console.error(warning.message);
                } else {
                    console.warn(warning.message);
                }
            });
            console.groupEnd();
        }
        
        // Export to global scope for other scripts
        window.deviceTracker = deviceTracker;
        
    } catch (error) {
        console.error('Failed to initialize device tracker:', error);
    }
});

// Integration with existing chat system
if (typeof window !== 'undefined') {
    // Hook into chat events if they exist
    document.addEventListener('chatInitialized', function() {
        if (deviceTracker) {
            deviceTracker.trackChatEvent('initialized');
        }
    });
    
    document.addEventListener('ticketCreated', function(event) {
        if (deviceTracker && event.detail) {
            deviceTracker.trackTicketCreation(event.detail.ticketId, event.detail.categoryId);
        }
    });
    
    // Add device info to chat forms
    document.addEventListener('submit', function(event) {
        if (deviceTracker && event.target.classList.contains('chat-form')) {
            // Add hidden fields with device info
            const deviceContext = deviceTracker.getDeviceContext();
            
            const hiddenFields = [
                { name: 'device_type', value: deviceContext.deviceType },
                { name: 'browser_name', value: deviceContext.browser.name },
                { name: 'browser_version', value: deviceContext.browser.version },
                { name: 'os_name', value: deviceContext.os.name },
                { name: 'os_version', value: deviceContext.os.version },
                { name: 'session_id', value: deviceContext.sessionId }
            ];
            
            hiddenFields.forEach(field => {
                if (!event.target.querySelector(`input[name="${field.name}"]`)) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = field.name;
                    input.value = field.value;
                    event.target.appendChild(input);
                }
            });
        }
    });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeviceTracker;
}

// Debug helper
window.getDeviceInfo = function() {
    if (deviceTracker) {
        console.log('Device Information:', deviceTracker.getDeviceContext());
        return deviceTracker.getDeviceContext();
    } else {
        console.error('Device tracker not initialized');
        return null;
    }
};
