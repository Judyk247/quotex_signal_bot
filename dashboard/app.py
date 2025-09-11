import os
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

# Get absolute paths to fix template issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, 
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)
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

# Add debug route to check template path
@app.route('/debug/paths')
def debug_paths():
    return {
        'base_dir': BASE_DIR,
        'template_dir': TEMPLATE_DIR,
        'static_dir': STATIC_DIR,
        'template_exists': os.path.exists(TEMPLATE_DIR),
        'index_exists': os.path.exists(os.path.join(TEMPLATE_DIR, 'index.html')) if os.path.exists(TEMPLATE_DIR) else False,
        'static_exists': os.path.exists(STATIC_DIR)
    }

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

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
