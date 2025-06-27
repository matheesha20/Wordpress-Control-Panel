#!/usr/bin/env python3
"""
WordPress Multi-Site Control Panel
A web-based control panel for managing multiple WordPress installations on Ubuntu Server
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import subprocess
import os
import secrets
import string
import hashlib
from datetime import datetime
import json
import re

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Database initialization
def init_db():
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    
    # Sites table
    c.execute('''CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain_name TEXT UNIQUE NOT NULL,
        db_name TEXT NOT NULL,
        db_user TEXT NOT NULL,
        db_password TEXT NOT NULL,
        ftp_user TEXT NOT NULL,
        nginx_port INTEGER,
        ssl_enabled BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # System status table
    c.execute('''CREATE TABLE IF NOT EXISTS system_status (
        id INTEGER PRIMARY KEY,
        nginx_installed BOOLEAN DEFAULT 0,
        mariadb_installed BOOLEAN DEFAULT 0,
        php_installed BOOLEAN DEFAULT 0,
        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Logs table
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        site_id INTEGER,
        action TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (site_id) REFERENCES sites (id)
    )''')
    
    conn.commit()
    conn.close()

# Helper functions
def run_command(command, capture_output=True):
    """Execute shell command safely"""
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(command, shell=True, timeout=300)
            return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def generate_password(length=16):
    """Generate secure password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_db_prefix(domain):
    """Generate database table prefix from domain"""
    clean_domain = re.sub(r'[^a-zA-Z0-9]', '', domain.split('.')[0])
    return f"{clean_domain[:8]}_"

def log_action(site_id, action, status, message=""):
    """Log action to database"""
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (site_id, action, status, message) VALUES (?, ?, ?, ?)",
              (site_id, action, status, message))
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get system status
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    c.execute("SELECT * FROM system_status WHERE id = 1")
    system_status = c.fetchone()
    
    # Get sites
    c.execute("SELECT * FROM sites ORDER BY created_at DESC")
    sites = c.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', system_status=system_status, sites=sites)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple authentication (enhance this in production)
        if username == 'admin' and password == 'admin123':  # Change this!
            session['logged_in'] = True
            user = User('admin')
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    logout_user()
    return redirect(url_for('login'))

@app.route('/system-setup', methods=['GET', 'POST'])
def system_setup():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Run system setup commands
        commands = [
            "apt update && apt upgrade -y",
            "apt install -y nginx mariadb-server php-fpm php-mysql php-xml php-gd php-curl php-mbstring unzip",
            "systemctl enable --now nginx mariadb php8.1-fpm"
        ]
        
        results = []
        for cmd in commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            results.append({
                'command': cmd,
                'success': success,
                'output': stdout if success else stderr
            })
        
        # Update system status
        conn = sqlite3.connect('wordpress_control.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO system_status (id, nginx_installed, mariadb_installed, php_installed) VALUES (1, 1, 1, 1)")
        conn.commit()
        conn.close()
        
        return jsonify({'results': results})
    
    return render_template('system_setup.html')

@app.route('/add-site', methods=['GET', 'POST'])
def add_site():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        domain_name = request.form['domain_name'].strip().lower()
        
        # Generate credentials
        db_name = f"wp_{re.sub(r'[^a-zA-Z0-9]', '', domain_name.split('.')[0])}"
        db_user = f"user_{re.sub(r'[^a-zA-Z0-9]', '', domain_name.split('.')[0])}"
        db_password = generate_password()
        ftp_user = f"ftp_{re.sub(r'[^a-zA-Z0-9]', '', domain_name.split('.')[0])}"
        
        # Find available port (starting from 8081)
        conn = sqlite3.connect('wordpress_control.db')
        c = conn.cursor()
        c.execute("SELECT MAX(nginx_port) FROM sites")
        max_port = c.fetchone()[0]
        nginx_port = (max_port + 1) if max_port else 8081
        
        try:
            # Insert site into database
            c.execute("""INSERT INTO sites 
                        (domain_name, db_name, db_user, db_password, ftp_user, nginx_port, status) 
                        VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                     (domain_name, db_name, db_user, db_password, ftp_user, nginx_port))
            site_id = c.lastrowid
            conn.commit()
            
            # Create database
            db_commands = [
                f"mysql -u root -e \"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\"",
                f"mysql -u root -e \"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';\"",
                f"mysql -u root -e \"GRANT ALL ON {db_name}.* TO '{db_user}'@'localhost';\"",
                f"mysql -u root -e \"FLUSH PRIVILEGES;\""
            ]
            
            # Install WordPress
            wp_commands = [
                f"mkdir -p /var/www/{domain_name}/public_html",
                f"chown -R www-data:www-data /var/www/{domain_name}",
                f"chmod -R 755 /var/www",
                f"bash -c 'cd /var/www/{domain_name}/public_html && wget https://wordpress.org/latest.zip'",
                f"bash -c 'cd /var/www/{domain_name}/public_html && unzip latest.zip && mv wordpress/* . && rm -rf wordpress latest.zip'",
                f"bash -c 'cd /var/www/{domain_name}/public_html && cp wp-config-sample.php wp-config.php'"
            ]
            
            all_commands = db_commands + wp_commands
            
            for cmd in all_commands:
                success, stdout, stderr = run_command(f"sudo {cmd}")
                if not success:
                    log_action(site_id, f"Command: {cmd}", "failed", stderr)
                    raise Exception(f"Command failed: {cmd}\nError: {stderr}")
                else:
                    log_action(site_id, f"Command: {cmd}", "success", stdout)
            
            # Update wp-config.php
            wp_config_content = f"""<?php
define('DB_NAME', '{db_name}');
define('DB_USER', '{db_user}');
define('DB_PASSWORD', '{db_password}');
define('DB_HOST', 'localhost');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', 'utf8mb4_unicode_ci');

$table_prefix = '{generate_db_prefix(domain_name)}';

define('FS_METHOD', 'direct');

if ( ! defined( 'ABSPATH' ) ) {{
    define( 'ABSPATH', __DIR__ . '/' );
}}

require_once ABSPATH . 'wp-settings.php';
"""
            
            wp_config_path = f"/var/www/{domain_name}/public_html/wp-config.php"
            
            # Write wp-config.php with proper permissions
            try:
                with open(wp_config_path, 'w') as f:
                    f.write(wp_config_content)
                # Set proper ownership after creating the file
                run_command(f"sudo chown www-data:www-data {wp_config_path}")
                run_command(f"sudo chmod 644 {wp_config_path}")
            except PermissionError:
                # If we can't write directly, use sudo to create the file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.php') as temp_file:
                    temp_file.write(wp_config_content)
                    temp_path = temp_file.name
                
                run_command(f"sudo cp {temp_path} {wp_config_path}")
                run_command(f"sudo chown www-data:www-data {wp_config_path}")
                run_command(f"sudo chmod 644 {wp_config_path}")
                
                # Clean up temp file
                import os
                os.unlink(temp_path)
            
            # Create Nginx configuration
            nginx_config = create_nginx_config(domain_name, nginx_port)
            nginx_config_path = f"/etc/nginx/sites-available/{domain_name}"
            
            # Write nginx config with proper permissions
            try:
                with open(nginx_config_path, 'w') as f:
                    f.write(nginx_config)
            except PermissionError:
                # If we can't write directly, use sudo to create the file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as temp_file:
                    temp_file.write(nginx_config)
                    temp_path = temp_file.name
                
                run_command(f"sudo cp {temp_path} {nginx_config_path}")
                
                # Clean up temp file
                import os
                os.unlink(temp_path)
            
            # Enable site
            run_command(f"sudo ln -s /etc/nginx/sites-available/{domain_name} /etc/nginx/sites-enabled/")
            run_command("sudo nginx -t && sudo systemctl reload nginx")
            
            # Create FTP user
            ftp_password = generate_password(12)
            run_command(f"sudo adduser --home /var/www/{domain_name}/public_html {ftp_user} --disabled-password --gecos ''")
            # Set FTP user password
            run_command(f"echo '{ftp_user}:{ftp_password}' | sudo chpasswd")
            
            # Update database with FTP password for reference
            c.execute("UPDATE sites SET db_password = ? WHERE id = ?", (f"{db_password}|FTP:{ftp_password}", site_id))
            
            # Set permissions
            permission_commands = [
                f"chown -R www-data:www-data /var/www/{domain_name}/public_html",
                f"find /var/www/{domain_name}/public_html -type d -exec chmod 755 {{}} \\;",
                f"find /var/www/{domain_name}/public_html -type f -exec chmod 644 {{}} \\;"
            ]
            
            for cmd in permission_commands:
                run_command(f"sudo {cmd}")
            
            # Update site status
            c.execute("UPDATE sites SET status = 'active' WHERE id = ?", (site_id,))
            conn.commit()
            
            log_action(site_id, "Site Creation", "success", f"Site {domain_name} created successfully")
            flash(f"Site {domain_name} created successfully!")
            
        except Exception as e:
            log_action(site_id if 'site_id' in locals() else None, "Site Creation", "failed", str(e))
            flash(f"Error creating site: {str(e)}")
        finally:
            conn.close()
        
        return redirect(url_for('index'))
    
    return render_template('add_site.html')

def create_nginx_config(domain_name, port):
    """Create Nginx configuration for a WordPress site"""
    return f"""# Backend configuration
server {{
    listen 127.0.0.1:{port};
    root /var/www/{domain_name}/public_html;
    index index.php;

    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
    }}

    location ~ /\\.ht {{
        deny all;
    }}
    
    client_max_body_size 512M;
}}

# Frontend proxy configuration
server {{
    listen 80;
    server_name {domain_name} www.{domain_name};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    client_max_body_size 512M;
}}"""

@app.route('/site/<int:site_id>')
def site_details(site_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    c.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    site = c.fetchone()
    
    c.execute("SELECT * FROM logs WHERE site_id = ? ORDER BY timestamp DESC LIMIT 50", (site_id,))
    logs = c.fetchall()
    
    conn.close()
    
    return render_template('site_details.html', site=site, logs=logs)

@app.route('/plugin-permissions/<int:site_id>', methods=['POST'])
def plugin_permissions(site_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    plugin_name = request.form.get('plugin_name', 'wpvividbackups')
    
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    c.execute("SELECT domain_name FROM sites WHERE id = ?", (site_id,))
    site = c.fetchone()
    
    if site:
        domain_name = site[0]
        plugin_path = f"/var/www/{domain_name}/public_html/wp-content/{plugin_name}"
        
        commands = [
            f"chown -R www-data:www-data {plugin_path}",
            f"chmod -R 755 {plugin_path}"
        ]
        
        results = []
        for cmd in commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            results.append({
                'command': cmd,
                'success': success,
                'output': stdout if success else stderr
            })
            log_action(site_id, f"Plugin Permission: {cmd}", "success" if success else "failed", stdout if success else stderr)
        
        flash(f"Plugin permissions updated for {plugin_name}")
    
    conn.close()
    return redirect(url_for('site_details', site_id=site_id))

@app.route('/api/sites')
def api_sites():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    c.execute("SELECT * FROM sites")
    sites = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    conn.close()
    
    return jsonify(sites)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000) 