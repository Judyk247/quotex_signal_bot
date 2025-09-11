import os
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

# Get the absolute path to the dashboard directory
dashboard_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(dashboard_dir, 'templates')
static_dir = os.path.join(dashboard_dir, 'static')

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

class Dashboard:
    def __init__(self):
        self.signals = []
        self.performance = {
            'total_signals': 0,
            'winning_signals': 0,
            'losing_signals': 0,
            'total_profit': 0
        }
    
    def add_signal(self, signal):
        formatted_signal = {
            'id': len(self.signals) + 1,
            'asset': signal.get('asset', 'Unknown'),
            'direction': signal.get('signal', 'hold').upper(),
            'confidence': signal.get('confidence', 0),
            'timestamp': signal.get('timestamp', ''),
            'timeframe': signal.get('timeframe', ''),
            'type': signal.get('type', 'unknown')
        }
        
        self.signals.insert(0, formatted_signal)
        self.signals = self.signals[:20]
        
        self.performance['total_signals'] += 1
        
        socketio.emit('new_signal', formatted_signal)
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
    socketio.emit('clients_update', len(socketio.server.manager.rooms))

@socketio.on('disconnect')
def handle_disconnect():
    socketio.emit('clients_update', len(socketio.server.manager.rooms))

@socketio.on('clients_update')
def handle_clients_update():
    socketio.emit('clients_update', len(socketio.server.manager.rooms))
