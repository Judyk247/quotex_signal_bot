from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import threading
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

class Dashboard:
    def __init__(self):
        self.signals = []
        self.performance = {
            'total_signals': 0,
            'winning_signals': 0,
            'losing_signals': 0,
            'total_profit': 0
        }
        self.connected_clients = 0
    
    def add_signal(self, signal):
        """Add a new signal to dashboard"""
        formatted_signal = {
            'id': len(self.signals) + 1,
            'asset': signal.get('asset', 'Unknown'),
            'direction': signal.get('signal', 'hold').upper(),
            'confidence': signal.get('confidence', 0),
            'timestamp': signal.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'timeframe': signal.get('timeframe', ''),
            'type': signal.get('type', 'unknown')
        }
        
        self.signals.insert(0, formatted_signal)
        self.signals = self.signals[:50]  # Keep only last 50 signals
        
        self.performance['total_signals'] += 1
        
        # Broadcast to all connected clients
        socketio.emit('new_signal', formatted_signal)
        socketio.emit('performance_update', self.performance)
    
    def update_performance(self, is_win, profit):
        """Update performance metrics"""
        if is_win:
            self.performance['winning_signals'] += 1
        else:
            self.performance['losing_signals'] += 1
        
        self.performance['total_profit'] += profit
        socketio.emit('performance_update', self.performance)

# Global dashboard instance
dashboard = Dashboard()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/signals')
def get_signals():
    return jsonify(dashboard.signals)

@app.route('/api/performance')
def get_performance():
    return jsonify(dashboard.performance)

@socketio.on('connect')
def handle_connect():
    dashboard.connected_clients += 1
    print(f"Client connected. Total clients: {dashboard.connected_clients}")

@socketio.on('disconnect')
def handle_disconnect():
    dashboard.connected_clients -= 1
    print(f"Client disconnected. Total clients: {dashboard.connected_clients}")

def run_dashboard():
    """Run the Flask dashboard"""
    print("Starting dashboard on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_dashboard()
