import os
from flask import Flask, jsonify, request, send_file
from flask_socketio import SocketIO
import json

# Get absolute path to templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
INDEX_PATH = os.path.join(TEMPLATE_DIR, 'index.html')

app = Flask(__name__)
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
    """Serve dashboard HTML - guaranteed to work"""
    try:
        # Try to find the template file
        possible_paths = [
            '/opt/render/project/src/templates/index.html',  # Render path
            os.path.join(os.path.dirname(__file__), 'templates', 'index.html'),  # Relative path
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'index.html'),  # Main directory
            'templates/index.html'  # Current directory
        ]
        
        for template_path in possible_paths:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read(), 200, {'Content-Type': 'text/html'}
        
        # If no template found, CREATE IT PROGRAMMATICALLY
        return create_fallback_dashboard()
        
    except Exception as e:
        return create_fallback_dashboard()

def create_fallback_dashboard():
    """Create dashboard HTML programmatically as fallback"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Quotex Trading Bot Dashboard</title>
        <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f4; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: white; padding: 20px; border-radius: 5px; text-align: center; }
            .signal { padding: 10px; border-bottom: 1px solid #eee; display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; }
            .profit { color: green; font-weight: bold; }
            .loss { color: red; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Quotex Trading Bot Dashboard</h1>
            <p>Real-time trading signals</p>
        </div>
        
        <div class="stats">
            <div class="stat-card"><h3>Total Signals</h3><div id="total-signals">0</div></div>
            <div class="stat-card"><h3>Winning Signals</h3><div id="winning-signals" class="profit">0</div></div>
            <div class="stat-card"><h3>Losing Signals</h3><div id="losing-signals" class="loss">0</div></div>
            <div class="stat-card"><h3>Total Profit</h3><div id="total-profit" class="profit">$0.00</div></div>
            <div class="stat-card"><h3>Win Rate</h3><div id="win-rate">0%</div></div>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 5px;">
            <h2>Recent Trading Signals</h2>
            <div class="signal" style="font-weight: bold; background: #f8f9fa;">
                <div>Time</div><div>Asset</div><div>Signal</div><div>Timeframe</div><div>Confidence</div>
            </div>
            <div id="signals-container"></div>
        </div>
        
        <script>
            const socket = io();
            socket.on('new_signal', function(signal) {
                const container = document.getElementById('signals-container');
                const signalElement = document.createElement('div');
                signalElement.className = 'signal';
                signalElement.innerHTML = `
                    <div>${signal.timestamp}</div>
                    <div>${signal.asset}</div>
                    <div class="${signal.direction.toLowerCase()}">${signal.direction}</div>
                    <div>${signal.timeframe}</div>
                    <div>${signal.confidence}%</div>
                `;
                container.insertBefore(signalElement, container.firstChild);
            });
            
            socket.on('performance_update', function(data) {
                document.getElementById('total-signals').textContent = data.total_signals;
                document.getElementById('winning-signals').textContent = data.winning_signals;
                document.getElementById('losing-signals').textContent = data.losing_signals;
                document.getElementById('total-profit').textContent = '$' + data.total_profit.toFixed(2);
                
                const winRate = data.total_signals > 0 ? 
                    ((data.winning_signals / data.total_signals) * 100).toFixed(1) : 0;
                document.getElementById('win-rate').textContent = winRate + '%';
            });
        </script>
    </body>
    </html>
    """
    return html_content, 200, {'Content-Type': 'text/html'}

@app.route('/debug/filesystem')
def debug_filesystem():
    """Debug the entire filesystem structure"""
    import os
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    def list_files(startpath):
        file_tree = {}
        for root, dirs, files in os.walk(startpath):
            level = root.replace(startpath, '').count(os.sep)
            indent = ' ' * 2 * level
            file_tree[os.path.basename(root)] = {
                'files': files,
                'path': root
            }
        return file_tree
    
    return jsonify({
        'current_working_dir': os.getcwd(),
        'base_dir': base_dir,
        'filesystem': list_files('/opt/render/project/src'),
        'templates_exists': os.path.exists('/opt/render/project/src/templates'),
        'dashboard_files': os.listdir(os.path.dirname(__file__)) if os.path.exists(os.path.dirname(__file__)) else 'NOT_FOUND'
    })

# Debug endpoint to check file existence
@app.route('/debug/files')
def debug_files():
    files = {
        'base_dir': BASE_DIR,
        'template_dir': TEMPLATE_DIR,
        'index_path': INDEX_PATH,
        'index_exists': os.path.exists(INDEX_PATH),
        'current_dir_files': os.listdir('.'),
        'template_dir_files': os.listdir(TEMPLATE_DIR) if os.path.exists(TEMPLATE_DIR) else 'NOT FOUND'
    }
    return jsonify(files)

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

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
