from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_mqtt import Mqtt
from flask_bcrypt import Bcrypt
import web_config
import web_db_operations as db
import time
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = web_config.SECRET_KEY
app.config['MQTT_BROKER_URL'] = web_config.MQTT_BROKER_HOST
app.config['MQTT_BROKER_PORT'] = web_config.MQTT_BROKER_PORT
app.config['MQTT_CLIENT_ID'] = web_config.MQTT_CLIENT_ID_WEB
app.config['MQTT_USERNAME'] = ''
app.config['MQTT_PASSWORD'] = ''
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

mqtt = Mqtt(app)
bcrypt_web = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

class User(UserMixin):
    def __init__(self, id, name, status, email):
        self.id = id
        self.name = name
        self.status = status
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = db.get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, status, email FROM person WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['id'], name=user_data['name'], status=user_data['status'], email=user_data['email'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = db.get_user_by_name(username)

        if user_data and user_data['password'] and \
           db.check_password(user_data['password'], password):
            user_obj = User(id=user_data['id'], name=user_data['name'], status=user_data['status'], email=user_data['email'])
            login_user(user_obj)
            flash(f'Logged in successfully as {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html', title='Login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/index')
@login_required
def index():
    image_url = f"{web_config.LATEST_IMAGE_URL}?t={int(time.time())}"
    return render_template('index.html', title='Smart Door Control', image_url=image_url)

@app.route('/open-door', methods=['POST'])
@login_required
def open_door():
    try:
        mqtt.publish(web_config.MQTT_TOPIC_DOOR_OPEN_COMMAND, "1")
        flash('Door open command sent!', 'success')
        return jsonify(success=True, message="Door open command sent")
    except Exception as e:
        flash(f'Error sending open door command: {e}', 'danger')
        return jsonify(success=False, message=str(e)), 500

@app.route('/request-photo', methods=['POST'])
@login_required
def request_photo():
    try:
        mqtt.publish(web_config.MQTT_TOPIC_REQUEST_PHOTO, "1")
        flash('Photo request sent! Image will update shortly.', 'info')
        return jsonify(success=True, message="Photo request sent.")
    except Exception as e:
        flash(f'Error sending photo request: {e}', 'danger')
        return jsonify(success=False, message=str(e)), 500

@app.route('/get_new_image_url')
@login_required
def get_new_image_url():
    new_image_url = f"{web_config.LATEST_IMAGE_URL}?t={int(time.time())}"
    return jsonify(imageUrl=new_image_url)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        user_data = db.get_user_by_name(current_user.name)

        if not (user_data and user_data['password'] and db.check_password(user_data['password'], current_password)):
            flash('Incorrect current password.', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
        elif len(new_password) < 6:
             flash('New password must be at least 6 characters long.', 'danger')
        else:
            if db.update_user_password(current_user.id, new_password):
                flash('Your password has been updated!', 'success')
                return redirect(url_for('index'))
            else:
                flash('An error occurred while updating your password.', 'danger')
    return render_template('settings.html', title='Settings')

@app.route('/logs')
@login_required
def logs():
    visit_logs = db.get_all_visit_logs()
    return render_template('logs.html', title='Visit Logs', logs=visit_logs)

@mqtt.on_connect()
def handle_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print("WebApp: Connected to MQTT Broker!")
    else:
        print(f"WebApp: Failed to connect to MQTT, return code {rc}")

@mqtt.on_log()
def handle_mqtt_logging(client, userdata, level, buf):
    pass

if __name__ == '__main__':
    static_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if not os.path.exists(static_dir_path):
        os.makedirs(static_dir_path, exist_ok=True)
        print(f"Created static directory: {static_dir_path}")

    app.run(debug=True, host='0.0.0.0', port=5000)
