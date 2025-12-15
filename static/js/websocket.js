/**
 * WebSocket client for real-time dashboard updates
 */

class DashboardWebSocket {
    constructor(url) {
        // Auto-detect protocol based on page protocol
        if (!url.startsWith('ws://') && !url.startsWith('wss://')) {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            this.url = `${protocol}//${host}${url}`;
        } else {
            this.url = url;
        }
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.handlers = {};
    }
    
    connect() {
        try {
            console.log('Connecting to WebSocket:', this.url);
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = (e) => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.onOpen(e);
            };
            
            this.ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                this.handleMessage(data);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.onError(error);
            };
            
            this.ws.onclose = (e) => {
                console.log('WebSocket closed');
                this.onClose(e);
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
        }
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket is not open');
        }
    }
    
    on(eventType, handler) {
        if (!this.handlers[eventType]) {
            this.handlers[eventType] = [];
        }
        this.handlers[eventType].push(handler);
    }
    
    handleMessage(data) {
        const eventType = data.type;
        if (this.handlers[eventType]) {
            this.handlers[eventType].forEach(handler => handler(data));
        }
        
        // Call generic message handler
        this.onMessage(data);
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }
    
    // Override these in implementation
    onOpen(e) {}
    onMessage(data) {}
    onError(error) {}
    onClose(e) {}
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardWebSocket;
}
