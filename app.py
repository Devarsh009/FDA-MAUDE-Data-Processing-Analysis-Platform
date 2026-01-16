"""
Flask application for MAUDE data processing web interface with authentication.
"""
import os
import json
from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import tempfile

from backend.processor import MAUDEProcessor
from backend.auth import AuthManager, User
from backend.imdrf_insights import (
    prepare_data_for_insights,
    analyze_imdrf_insights,
    get_top_manufacturers_for_prefix
)
from backend.txt_to_csv_converter import TxtToCsvConverter, get_txt_preview
from config import (
    GROQ_API_KEY, SECRET_KEY, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS,
    MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max file size for large TXT files
# Use /tmp for Vercel (serverless) or temp directory for local
if os.path.exists('/tmp'):
    app.config['UPLOAD_FOLDER'] = os.path.join('/tmp', 'maude_uploads')
elif os.getenv('TMPDIR'):
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getenv('TMPDIR'), 'maude_uploads')
elif os.getenv('TMP'):
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getenv('TMP'), 'maude_uploads')
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'maude_uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize Flask-Mail
mail = Mail(app)

# Initialize Auth Manager
auth_manager = AuthManager(SECRET_KEY)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    return auth_manager.get_user(user_id)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_password_reset_email(email: str, token: str):
    """Send password reset email."""
    try:
        reset_url = f"{request.host_url}reset-password?token={token}"
        
        msg = Message(
            subject='MAUDE Data Processor - Password Reset',
            recipients=[email],
            html=f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">Password Reset Request</h2>
                    <p>You requested to reset your password for the MAUDE Data Processor.</p>
                    <p>Click the button below to reset your password:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" 
                           style="background: #2563eb; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p style="font-size: 12px; color: #666;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{reset_url}" style="color: #2563eb;">{reset_url}</a>
                    </p>
                    <p style="font-size: 12px; color: #666;">
                        This link will expire in 1 hour. If you didn't request this, please ignore this email.
                    </p>
                </div>
            </body>
            </html>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


# Authentication Routes
@app.route('/login')
def login():
    """Render login page."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # Expose test accounts to the login template when enabled
    try:
        from config import TEST_ACCOUNTS_ENABLED, TEST_USER_EMAIL, TEST_USER_PASSWORD
        test_accounts = []
        if TEST_ACCOUNTS_ENABLED:
            test_accounts = [{
                'email': TEST_USER_EMAIL,
                'password': TEST_USER_PASSWORD,
                'label': 'Test Account'
            }]
    except Exception:
        test_accounts = []
    return render_template('login.html', test_accounts=test_accounts)


@app.route('/register')
def register():
    """Render registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/forgot-password')
def forgot_password():
    """Render forgot password page."""
    return render_template('forgot_password.html')


@app.route('/reset-password')
def reset_password():
    """Render reset password page."""
    token = request.args.get('token')
    if not token:
        return redirect(url_for('forgot_password'))
    return render_template('reset_password.html', token=token)


@app.route('/logout')
@login_required
def logout():
    """Logout user."""
    logout_user()
    return redirect(url_for('login'))


# API Routes
@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle login API request."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = auth_manager.authenticate_user(email, password)
    if user:
        login_user(user, remember=True)
        return jsonify({'success': True, 'message': 'Login successful'}), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401


@app.route('/api/register', methods=['POST'])
def api_register():
    """Handle registration API request."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    success, message = auth_manager.register_user(email, password, name)
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'error': message}), 400


@app.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    """Handle forgot password API request."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # Always return success to prevent email enumeration
    if auth_manager.user_exists(email):
        token = auth_manager.generate_reset_token(email)
        if token:
            send_password_reset_email(email, token)
    
    return jsonify({
        'success': True,
        'message': 'If an account exists with that email, a password reset link has been sent.'
    }), 200


@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    """Handle reset password API request."""
    data = request.get_json()
    token = data.get('token', '')
    password = data.get('password', '')
    
    if not token or not password:
        return jsonify({'error': 'Token and password are required'}), 400
    
    success, message = auth_manager.reset_password(token, password)
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'error': message}), 400


# Protected Routes
@app.route('/')
@login_required
def index():
    """Render main upload page."""
    return render_template('index.html', user=current_user)


@app.route('/process', methods=['POST'])
@login_required
def process_file():
    """Process uploaded MAUDE file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload CSV or Excel file.'}), 400
    
    # Note: GROQ_API_KEY is optional - app works without it using deterministic methods only
    # if not GROQ_API_KEY:
    #     return jsonify({'error': 'GROQ_API_KEY not configured. Please set environment variable.'}), 500
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        # Create output file path
        output_filename = f"cleaned_{filename.rsplit('.', 1)[0]}.xlsx"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Initialize processor
        processor = MAUDEProcessor()
        
        # Load IMDRF structure if provided
        imdrf_loaded = False
        if 'imdrf_file' in request.files:
            imdrf_file = request.files['imdrf_file']
            if imdrf_file.filename and imdrf_file.filename.strip():
                imdrf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"imdrf_{secure_filename(imdrf_file.filename)}")
                imdrf_file.save(imdrf_path)
                processor.load_imdrf_structure(imdrf_path)
                imdrf_loaded = True
                print(f"IMDRF annex file loaded from: {imdrf_file.filename}")
        
        if not imdrf_loaded:
            print("WARNING: No IMDRF annex file provided. IMDRF codes will be blank.")
        
        # Process file
        stats = processor.process_file(input_path, output_path)
        
        # Check validation - HARD STOPS for critical failures
        critical_failures = []
        if not stats['validation'].get('column_count_correct', False):
            critical_failures.append('Column count check failed')
        if not stats['validation'].get('file_will_open', False):
            critical_failures.append('File integrity check failed')
        if not stats['validation'].get('date_format_correct', False):
            critical_failures.append('Date format check failed (HARD STOP: no literal "nan", all dates must be DD-MM-YYYY)')
        if not stats['validation'].get('imdrf_adjacent', False):
            critical_failures.append('IMDRF Code column position check failed (HARD STOP: must be adjacent to Device Problem)')
        if not stats['validation'].get('imdrf_codes_valid', False):
            critical_failures.append('IMDRF codes validation failed (HARD STOP: all codes must exist in Annex)')
        
        # Non-critical validations (warn but don't fail)
        warnings = []
        if not stats['validation'].get('no_timestamps', False):
            warnings.append('Timestamp check failed (non-critical)')
        
        # HARD STOP on critical failures
        if critical_failures:
            error_msg = f"Validation failed (HARD STOP): {', '.join(critical_failures)}"
            if warnings:
                error_msg += f" | Warnings: {', '.join(warnings)}"
            
            return jsonify({
                'error': error_msg,
                'validation_results': stats['validation'],
                'stats': stats,
                'failed_checks': critical_failures,
                'warnings': warnings
            }), 400
        elif warnings:
            # Log warnings but don't fail
            print(f"Validation warnings: {', '.join(warnings)}")
        
        # Return file for download
        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


# IMDRF Insights Routes
@app.route('/imdrf-insights')
@login_required
def imdrf_insights_page():
    """Render IMDRF Insights page."""
    return render_template('imdrf_insights.html', user=current_user)


@app.route('/api/imdrf-insights/prepare', methods=['POST'])
@login_required
def api_prepare_insights():
    """Prepare uploaded CSV or Excel file for IMDRF insights analysis."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check file extension
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in allowed_extensions:
        return jsonify({'error': 'Invalid file type. Please upload CSV, XLS, or XLSX file.'}), 400

    try:
        # Save uploaded file with unique name
        filename = secure_filename(file.filename)
        file_id = f"{current_user.id}_{os.urandom(8).hex()}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(input_path)

        # Prepare data for insights
        result = prepare_data_for_insights(input_path)

        # Store file info in session for later use
        session[f'insights_file_{file_id}'] = input_path

        return jsonify({
            'success': True,
            'file_id': file_id,
            'all_prefixes': result['all_prefixes'],
            'all_manufacturers': result['all_manufacturers'],
            'total_rows': result['total_rows'],
            'rows_with_imdrf': result['rows_with_imdrf'],
            'rows_with_dates': result['rows_with_dates']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/imdrf-insights/top-manufacturers', methods=['GET'])
@login_required
def api_top_manufacturers():
    """Get top manufacturers for a specific IMDRF prefix."""
    prefix = request.args.get('prefix')
    file_id = request.args.get('file_id')

    if not prefix or not file_id:
        return jsonify({'error': 'Missing prefix or file_id parameter'}), 400

    try:
        # Retrieve file path from session
        file_path = session.get(f'insights_file_{file_id}')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found. Please upload again.'}), 404

        # Prepare data again (in memory)
        result = prepare_data_for_insights(file_path)
        df_exploded = result['df_exploded']
        mfr_col = result['mfr_col']

        # Get top manufacturers
        top_mfrs = get_top_manufacturers_for_prefix(df_exploded, prefix, mfr_col, top_n=5)

        return jsonify({
            'success': True,
            'top_manufacturers': top_mfrs
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/imdrf-insights/analyze', methods=['POST'])
@login_required
def api_analyze_insights():
    """Perform IMDRF insights analysis."""
    data = request.get_json()

    file_id = data.get('file_id')
    prefix = data.get('prefix')
    manufacturers = data.get('manufacturers', [])
    grain = data.get('grain', 'W')
    threshold_k = data.get('threshold_k', 2.0)

    if not file_id or not prefix or not manufacturers:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        # Retrieve file path from session
        file_path = session.get(f'insights_file_{file_id}')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found. Please upload again.'}), 404

        # Prepare data
        result = prepare_data_for_insights(file_path)
        df_exploded = result['df_exploded']

        # Perform analysis
        analysis_result = analyze_imdrf_insights(
            df_exploded,
            prefix,
            manufacturers,
            grain,
            threshold_k
        )

        # Convert pandas data to JSON-serializable format
        manufacturer_series = {}
        for mfr, series in analysis_result['manufacturer_series'].items():
            manufacturer_series[mfr] = {
                'dates': series.index.strftime('%Y-%m-%d').tolist(),
                'values': series.tolist()
            }

        response_data = {
            'success': True,
            'universal_mean': analysis_result['universal_mean'],
            'prefix_mean': analysis_result['prefix_mean'],
            'prefix_std': analysis_result['prefix_std'],
            'upper_threshold': analysis_result['upper_threshold'],
            'lower_threshold': analysis_result['lower_threshold'],
            'manufacturer_series': manufacturer_series,
            'date_range': analysis_result['date_range'].strftime('%Y-%m-%d').tolist() if len(analysis_result['date_range']) > 0 else [],
            'statistics': analysis_result['statistics'],
            'grain': grain,
            'selected_prefix': prefix
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400


# TXT to CSV Converter Routes
@app.route('/txt-to-csv')
@login_required
def txt_to_csv_page():
    """Render TXT to CSV converter page."""
    return render_template('txt_to_csv.html', user=current_user)


@app.route('/api/txt-to-csv/preview', methods=['POST'])
@login_required
def api_txt_preview():
    """Upload TXT file and get preview."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.txt'):
        return jsonify({'error': 'Invalid file type. Please upload a .txt file.'}), 400

    try:
        # Save uploaded file with unique name
        filename = secure_filename(file.filename)
        file_id = f"{current_user.id}_{os.urandom(8).hex()}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(input_path)

        # Get preview
        preview = get_txt_preview(input_path, num_rows=10)

        # Store file path in session
        session[f'txt_file_{file_id}'] = input_path

        return jsonify({
            'success': True,
            'file_id': file_id,
            'preview': preview
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/txt-to-csv/convert', methods=['POST'])
@login_required
def api_txt_convert():
    """Convert TXT file to CSV."""
    data = request.get_json()
    file_id = data.get('file_id')

    if not file_id:
        return jsonify({'error': 'Missing file_id parameter'}), 400

    try:
        # Retrieve file path from session
        file_path = session.get(f'txt_file_{file_id}')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found. Please upload again.'}), 404

        # Generate output path
        output_file_id = f"{current_user.id}_{os.urandom(8).hex()}"
        output_filename = os.path.splitext(os.path.basename(file_path))[0] + '.csv'
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{output_file_id}_{output_filename}")

        # Convert file
        converter = TxtToCsvConverter()
        stats = converter.process_file_chunked(file_path, output_path)

        # Store output path in session
        session[f'csv_file_{output_file_id}'] = {
            'path': output_path,
            'filename': output_filename
        }

        return jsonify({
            'success': True,
            'output_file_id': output_file_id,
            'stats': stats
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/txt-to-csv/download/<file_id>')
@login_required
def api_txt_download(file_id):
    """Download converted CSV file."""
    try:
        # Retrieve file info from session
        file_info = session.get(f'csv_file_{file_id}')
        if not file_info or not os.path.exists(file_info['path']):
            return jsonify({'error': 'File not found. Please convert again.'}), 404

        return send_file(
            file_info['path'],
            as_attachment=True,
            download_name=file_info['filename'],
            mimetype='text/csv'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    # Check for Groq API key
    if not GROQ_API_KEY:
        print("WARNING: GROQ_API_KEY not set. Set it as an environment variable.")
    
    # Check for mail configuration
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("WARNING: Mail credentials not configured. Password recovery emails will not work.")
        print("Set MAIL_USERNAME and MAIL_PASSWORD environment variables.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
