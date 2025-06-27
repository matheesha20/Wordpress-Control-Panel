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

@app.route('/delete-site/<int:site_id>', methods=['POST'])
def delete_site(site_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    
    # Get site details before deletion
    c.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    site = c.fetchone()
    
    if not site:
        flash('Site not found')
        return redirect(url_for('index'))
    
    domain_name = site[1]
    db_name = site[2]
    db_user = site[3]
    ftp_user = site[5]
    
    try:
        log_action(site_id, "Site Deletion Started", "info", f"Starting deletion of {domain_name}")
        
        # 1. Create backup before deletion (optional safety measure)
        backup_commands = [
            f"mkdir -p /tmp/wp-backups/{domain_name}",
            f"mysqldump {db_name} > /tmp/wp-backups/{domain_name}/{db_name}.sql 2>/dev/null || true",
            f"tar -czf /tmp/wp-backups/{domain_name}/files.tar.gz -C /var/www/{domain_name}/public_html . 2>/dev/null || true"
        ]
        
        for cmd in backup_commands:
            run_command(f"sudo {cmd}")
        
        # 2. Remove database and user
        db_cleanup_commands = [
            f"mysql -u root -e \"DROP DATABASE IF EXISTS {db_name};\"",
            f"mysql -u root -e \"DROP USER IF EXISTS '{db_user}'@'localhost';\"",
            f"mysql -u root -e \"FLUSH PRIVILEGES;\""
        ]
        
        for cmd in db_cleanup_commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            if success:
                log_action(site_id, f"Database cleanup: {cmd}", "success", stdout)
            else:
                log_action(site_id, f"Database cleanup: {cmd}", "warning", stderr)
        
        # 3. Remove Nginx configuration
        nginx_cleanup_commands = [
            f"rm -f /etc/nginx/sites-enabled/{domain_name}",
            f"rm -f /etc/nginx/sites-available/{domain_name}",
            "nginx -t && systemctl reload nginx || true"
        ]
        
        for cmd in nginx_cleanup_commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            log_action(site_id, f"Nginx cleanup: {cmd}", "success" if success else "warning", stdout if success else stderr)
        
        # 4. Remove FTP user
        ftp_cleanup_commands = [
            f"userdel {ftp_user} 2>/dev/null || true",
            f"groupdel {ftp_user} 2>/dev/null || true"
        ]
        
        for cmd in ftp_cleanup_commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            log_action(site_id, f"FTP cleanup: {cmd}", "success" if success else "info", stdout if success else stderr)
        
        # 5. Remove files and directories
        file_cleanup_commands = [
            f"rm -rf /var/www/{domain_name}"
        ]
        
        for cmd in file_cleanup_commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            if success:
                log_action(site_id, f"File cleanup: {cmd}", "success", stdout)
            else:
                log_action(site_id, f"File cleanup: {cmd}", "warning", stderr)
        
        # 6. Remove from database
        c.execute("DELETE FROM sites WHERE id = ?", (site_id,))
        conn.commit()
        
        log_action(site_id, "Site Deletion Completed", "success", f"Site {domain_name} deleted successfully")
        flash(f"Site {domain_name} has been deleted successfully. Backup saved to /tmp/wp-backups/{domain_name}/")
        
    except Exception as e:
        log_action(site_id, "Site Deletion Failed", "failed", str(e))
        flash(f"Error deleting site: {str(e)}")
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/retry-site/<int:site_id>', methods=['POST'])
def retry_site_setup(site_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('wordpress_control.db')
    c = conn.cursor()
    
    # Get site details
    c.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    site = c.fetchone()
    
    if not site:
        flash('Site not found')
        return redirect(url_for('index'))
    
    domain_name = site[1]
    db_name = site[2]
    db_user = site[3]
    db_password = site[4]
    ftp_user = site[5]
    nginx_port = site[6]
    
    try:
        log_action(site_id, "Site Retry Started", "info", f"Retrying setup for {domain_name}")
        
        # Update status to pending
        c.execute("UPDATE sites SET status = 'pending' WHERE id = ?", (site_id,))
        conn.commit()
        
        # Check what's already completed and what needs to be done
        setup_status = check_site_setup_status(domain_name, db_name, db_user, ftp_user, nginx_port)
        
        # Resume from where we left off
        resume_site_setup(site_id, domain_name, db_name, db_user, db_password, ftp_user, nginx_port, setup_status)
        
        # Update status to active if successful
        c.execute("UPDATE sites SET status = 'active' WHERE id = ?", (site_id,))
        conn.commit()
        
        log_action(site_id, "Site Retry Completed", "success", f"Site {domain_name} setup completed successfully")
        flash(f"Site {domain_name} setup completed successfully!")
        
    except Exception as e:
        c.execute("UPDATE sites SET status = 'failed' WHERE id = ?", (site_id,))
        conn.commit()
        log_action(site_id, "Site Retry Failed", "failed", str(e))
        flash(f"Error retrying site setup: {str(e)}")
    finally:
        conn.close()
    
    return redirect(url_for('site_details', site_id=site_id))

def check_site_setup_status(domain_name, db_name, db_user, ftp_user, nginx_port):
    """Check which parts of the site setup are already completed"""
    status = {
        'database_exists': False,
        'database_user_exists': False,
        'wordpress_downloaded': False,
        'wp_config_exists': False,
        'nginx_config_exists': False,
        'nginx_enabled': False,
        'ftp_user_exists': False,
        'directory_exists': False
    }
    
    try:
        # Check database
        success, stdout, stderr = run_command(f"mysql -u root -e \"USE {db_name};\"")
        status['database_exists'] = success
        
        # Check database user
        success, stdout, stderr = run_command(f"mysql -u root -e \"SELECT User FROM mysql.user WHERE User='{db_user}';\"")
        status['database_user_exists'] = success and db_user in stdout
        
        # Check WordPress installation
        wp_path = f"/var/www/{domain_name}/public_html"
        status['directory_exists'] = os.path.exists(wp_path)
        status['wordpress_downloaded'] = os.path.exists(f"{wp_path}/wp-config-sample.php")
        status['wp_config_exists'] = os.path.exists(f"{wp_path}/wp-config.php")
        
        # Check Nginx configuration
        nginx_config_path = f"/etc/nginx/sites-available/{domain_name}"
        nginx_enabled_path = f"/etc/nginx/sites-enabled/{domain_name}"
        status['nginx_config_exists'] = os.path.exists(nginx_config_path)
        status['nginx_enabled'] = os.path.exists(nginx_enabled_path)
        
        # Check FTP user
        success, stdout, stderr = run_command(f"id {ftp_user}")
        status['ftp_user_exists'] = success
        
    except Exception as e:
        log_action(None, "Setup Status Check Failed", "warning", str(e))
    
    return status

def resume_site_setup(site_id, domain_name, db_name, db_user, db_password, ftp_user, nginx_port, status):
    """Resume site setup from where it left off"""
    
    # 1. Create database if not exists
    if not status['database_exists']:
        success, stdout, stderr = run_command(f"sudo mysql -u root -e \"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\"")
        if success:
            log_action(site_id, "Database Created", "success", f"Database {db_name} created")
        else:
            raise Exception(f"Failed to create database: {stderr}")
    
    # 2. Create database user if not exists
    if not status['database_user_exists']:
        commands = [
            f"mysql -u root -e \"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';\"",
            f"mysql -u root -e \"GRANT ALL ON {db_name}.* TO '{db_user}'@'localhost';\"",
            f"mysql -u root -e \"FLUSH PRIVILEGES;\""
        ]
        
        for cmd in commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            if success:
                log_action(site_id, f"Database User: {cmd}", "success", stdout)
            else:
                log_action(site_id, f"Database User: {cmd}", "warning", stderr)
    
    # 3. Create directory if not exists
    if not status['directory_exists']:
        commands = [
            f"mkdir -p /var/www/{domain_name}/public_html",
            f"chown -R www-data:www-data /var/www/{domain_name}",
            f"chmod -R 755 /var/www"
        ]
        
        for cmd in commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            if success:
                log_action(site_id, f"Directory Setup: {cmd}", "success", stdout)
            else:
                raise Exception(f"Failed directory setup: {stderr}")
    
    # 4. Download WordPress if not downloaded
    if not status['wordpress_downloaded']:
        wp_commands = [
            f"bash -c 'cd /var/www/{domain_name}/public_html && wget https://wordpress.org/latest.zip'",
            f"bash -c 'cd /var/www/{domain_name}/public_html && unzip latest.zip && mv wordpress/* . && rm -rf wordpress latest.zip'"
        ]
        
        for cmd in wp_commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            if success:
                log_action(site_id, f"WordPress Download: {cmd}", "success", stdout)
            else:
                raise Exception(f"Failed WordPress download: {stderr}")
    
    # 5. Create wp-config.php if not exists
    if not status['wp_config_exists']:
        wp_config_content = f"""<?php
define('DB_NAME', '{db_name}');
define('DB_USER', '{db_user}');
define('DB_PASSWORD', '{db_password}');
define('DB_HOST', 'localhost');
define('DB_CHARSET', 'utf8mb4');
define('DB_COLLATE', 'utf8mb4_unicode_ci');

$table_prefix = '{generate_db_prefix(domain_name)}';

define('FS_METHOD', 'direct');

// WordPress HTTPS detection for proxy setups
if (
    isset($_SERVER['HTTP_X_FORWARDED_PROTO']) &&
    $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https'
) {{
    $_SERVER['HTTPS'] = 'on';
}}

if ( ! defined( 'ABSPATH' ) ) {{
    define( 'ABSPATH', __DIR__ . '/' );
}}

require_once ABSPATH . 'wp-settings.php';
"""
        
        wp_config_path = f"/var/www/{domain_name}/public_html/wp-config.php"
        
        try:
            with open(wp_config_path, 'w') as f:
                f.write(wp_config_content)
            run_command(f"sudo chown www-data:www-data {wp_config_path}")
            run_command(f"sudo chmod 644 {wp_config_path}")
        except PermissionError:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.php') as temp_file:
                temp_file.write(wp_config_content)
                temp_path = temp_file.name
            
            run_command(f"sudo cp {temp_path} {wp_config_path}")
            run_command(f"sudo chown www-data:www-data {wp_config_path}")
            run_command(f"sudo chmod 644 {wp_config_path}")
            
            import os
            os.unlink(temp_path)
        
        log_action(site_id, "WordPress Config Created", "success", "wp-config.php created")
    
    # 6. Create Nginx configuration if not exists
    if not status['nginx_config_exists']:
        nginx_config = create_nginx_config(domain_name, nginx_port)
        nginx_config_path = f"/etc/nginx/sites-available/{domain_name}"
        
        try:
            with open(nginx_config_path, 'w') as f:
                f.write(nginx_config)
        except PermissionError:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.conf') as temp_file:
                temp_file.write(nginx_config)
                temp_path = temp_file.name
            
            run_command(f"sudo cp {temp_path} {nginx_config_path}")
            
            import os
            os.unlink(temp_path)
        
        log_action(site_id, "Nginx Config Created", "success", f"Nginx config for {domain_name} created")
    
    # 7. Enable Nginx site if not enabled
    if not status['nginx_enabled']:
        commands = [
            f"ln -s /etc/nginx/sites-available/{domain_name} /etc/nginx/sites-enabled/",
            "nginx -t && systemctl reload nginx"
        ]
        
        for cmd in commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            if success:
                log_action(site_id, f"Nginx Enable: {cmd}", "success", stdout)
            else:
                log_action(site_id, f"Nginx Enable: {cmd}", "warning", stderr)
    
    # 8. Create FTP user if not exists
    if not status['ftp_user_exists']:
        ftp_password = generate_password(12)
        commands = [
            f"adduser --home /var/www/{domain_name}/public_html {ftp_user} --disabled-password --gecos ''",
            f"echo '{ftp_user}:{ftp_password}' | chpasswd"
        ]
        
        for cmd in commands:
            success, stdout, stderr = run_command(f"sudo {cmd}")
            if success:
                log_action(site_id, f"FTP User: {cmd}", "success", stdout)
            else:
                log_action(site_id, f"FTP User: {cmd}", "warning", stderr)
    
    # 9. Set final permissions
    permission_commands = [
        f"chown -R www-data:www-data /var/www/{domain_name}/public_html",
        f"find /var/www/{domain_name}/public_html -type d -exec chmod 755 {{}} \\;",
        f"find /var/www/{domain_name}/public_html -type f -exec chmod 644 {{}} \\;"
    ]
    
    for cmd in permission_commands:
        success, stdout, stderr = run_command(f"sudo {cmd}")
        if success:
            log_action(site_id, f"Permissions: {cmd}", "success", stdout)
        else:
            log_action(site_id, f"Permissions: {cmd}", "warning", stderr)

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