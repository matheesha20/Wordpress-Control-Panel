# WordPress Multi-Site Control Panel

A web-based control panel for managing multiple WordPress installations on Ubuntu Server. This control panel automates all the steps from your script including system setup, database creation, WordPress installation, Nginx configuration, and file permissions.

## 🚀 Features

- **System Setup**: Automated installation of Nginx, MariaDB, and PHP-FPM
- **WordPress Installation**: One-click WordPress site creation
- **Database Management**: Automatic database and user creation
- **Nginx Configuration**: Automated virtual host setup with proxy configuration
- **File Permissions**: Proper WordPress file and directory permissions
- **Plugin Support**: Easy permission management for plugins like WPVivid
- **FTP Integration**: Automatic FTP user creation for each site
- **Activity Logging**: Complete audit trail of all operations
- **Responsive UI**: Modern Bootstrap-based interface

## 📋 Requirements

- Ubuntu Server 20.04+ 
- Python 3.8+
- Sudo privileges
- Root access for system configuration

## 🛠️ Installation

### 1. Clone or Download the Control Panel

```bash
# If you have the files, skip this step
# Otherwise, create the directory structure as shown in the files above
```

### 2. Install Python Dependencies

```bash
cd /path/to/control-panel
pip3 install -r requirements.txt
```

### 3. Set Up the Application

```bash
# Make sure you're in the control panel directory
python3 app.py
```

The control panel will be available at: `http://your-server-ip:5000`

## 🔐 Default Login

- **Username**: admin
- **Password**: admin123

⚠️ **IMPORTANT**: Change the default credentials in `app.py` before production use!

## 📖 Usage Guide

### Step 1: System Setup
1. Login to the control panel
2. Go to **System Setup**
3. Click **Start System Setup** to install:
   - Nginx web server
   - MariaDB database server
   - PHP-FPM processor
   - Required PHP extensions

### Step 2: Create WordPress Sites
1. Go to **Add New Site**
2. Enter domain name (e.g., `example.com`)
3. Click **Create WordPress Site**

The system will automatically:
- Create a MySQL database and user
- Download and install WordPress
- Configure Nginx virtual host
- Set up FTP user
- Configure proper file permissions

### Step 3: Manage Sites
- View all sites on the **Dashboard**
- Click on any site to view details, logs, and manage settings
- Use **Plugin Permissions** to set permissions for WPVivid and other plugins

## 🔧 What Gets Created for Each Site

For a domain like `example.com`, the system creates:

### Database
- **Database**: `wp_example`
- **User**: `user_example`
- **Password**: Auto-generated secure password
- **Table Prefix**: `example_`

### File Structure
```
/var/www/example.com/
└── public_html/
    ├── wp-config.php (configured)
    ├── wp-content/
    ├── wp-admin/
    ├── wp-includes/
    └── ... (WordPress files)
```

### Nginx Configuration
- Backend server on port 8081, 8082, etc.
- Frontend proxy on port 80
- PHP-FPM integration
- 512MB upload limit

### FTP User
- **Username**: `ftp_example`
- **Home Directory**: `/var/www/example.com/public_html`

## 🔌 Plugin Permissions

For plugins like WPVivid Backup:
1. Install the plugin through WordPress admin
2. Go to site details in the control panel
3. Click **Plugin Permissions**
4. Enter plugin folder name (e.g., `wpvividbackups`)
5. Click **Apply Permissions**

This runs the commands from your script:
```bash
sudo chown -R www-data:www-data /var/www/domain/public_html/wp-content/plugin-name
sudo chmod -R 755 /var/www/domain/public_html/wp-content/plugin-name
```

## 🛡️ Security Considerations

### Before Production Use:
1. **Change default login credentials** in `app.py`
2. **Set up HTTPS** for the control panel
3. **Configure firewall** to restrict access to port 5000
4. **Set proper file permissions** on the control panel files
5. **Regular backups** of the SQLite database

### Recommended Security Setup:
```bash
# Restrict control panel access
sudo ufw allow from YOUR_IP_ADDRESS to any port 5000

# Set up proper file permissions
chmod 600 wordpress_control.db
chmod 700 app.py
```

## 🐛 Troubleshooting

### Common Issues:

1. **Permission Denied Errors**
   - Ensure the user running the control panel has sudo privileges
   - Check file permissions on directories

2. **Database Connection Errors**
   - Run `sudo mysql_secure_installation` first
   - Ensure MariaDB is running: `sudo systemctl status mariadb`

3. **Nginx Configuration Errors**
   - Check nginx syntax: `sudo nginx -t`
   - View nginx logs: `sudo tail -f /var/log/nginx/error.log`

4. **WordPress Installation Fails**
   - Check internet connectivity for WordPress download
   - Ensure `/var/www` directory exists and is writable

## 📁 File Structure

```
Control Panel/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── wordpress_control.db   # SQLite database (created automatically)
├── templates/
│   ├── base.html         # Base template
│   ├── login.html        # Login page
│   ├── dashboard.html    # Main dashboard
│   ├── add_site.html     # Add new site form
│   ├── system_setup.html # System setup page
│   └── site_details.html # Individual site details
└── README.md             # This file
```

## 🔄 Nginx Configuration Details

Each site gets two server blocks:

1. **Backend** (Internal, port 8081+)
   - Serves WordPress files
   - PHP-FPM integration
   - Large file upload support

2. **Frontend** (Public, port 80)
   - Proxy to backend
   - SSL termination (when configured)
   - Load balancing ready

## 📊 Activity Logging

The control panel logs all operations:
- System setup commands
- WordPress installations
- Permission changes
- Error messages

View logs in the site details page or check the database directly.

## 🚀 Production Deployment

For production use:

1. **Use a reverse proxy** (Nginx) for the control panel
2. **Set up SSL** for the control panel interface
3. **Configure automatic backups** of the SQLite database
4. **Monitor system resources** and set up alerts
5. **Regular updates** of system packages

## 📞 Support

This control panel automates all the steps from your original script. If you encounter issues:

1. Check the activity logs in the control panel
2. Verify system requirements are met
3. Ensure proper sudo privileges
4. Check nginx and PHP-FPM service status

## 🔮 Future Enhancements

Planned features:
- SSL certificate automation (Let's Encrypt)
- Backup management integration
- Resource monitoring
- Multi-user support
- API endpoints
- Plugin marketplace integration

---

**Note**: This control panel is designed to replicate your exact WordPress deployment workflow. All commands and configurations match your original script requirements. 