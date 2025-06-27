# 🚀 WordPress Control Panel - Server Setup Guide

This guide will walk you through setting up the WordPress Control Panel on your Ubuntu server step by step.

## 📋 Prerequisites

### Server Requirements
- **OS**: Ubuntu 20.04 LTS or newer
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: At least 20GB free space
- **Network**: Internet connection for package downloads
- **Access**: SSH access with sudo privileges

### Before You Begin
- Have your server IP address ready
- Ensure you can SSH into your server
- Have sudo privileges on the server

## 🛠️ Step-by-Step Setup

### Step 1: Connect to Your Server

```bash
# Replace YOUR_SERVER_IP with your actual server IP
ssh username@YOUR_SERVER_IP
```

### Step 2: Update System Packages

```bash
# Update package list and upgrade system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3 python3-pip git curl wget unzip
```

### Step 3: Transfer Control Panel Files

**Option A: Using SCP (from your local machine)**
```bash
# From your local machine where you have the control panel files
scp -r "Control Panel"/* username@YOUR_SERVER_IP:/home/username/wordpress-control/
```

**Option B: Download/Create Files Directly on Server**
```bash
# Create directory on server
mkdir -p /home/username/wordpress-control
cd /home/username/wordpress-control

# Create all the files (app.py, templates, etc.) as shown in the previous responses
```

### Step 4: Install Python Dependencies

```bash
# Navigate to control panel directory
cd /home/username/wordpress-control

# Install Python dependencies
pip3 install -r requirements.txt

# If you get permission errors, try:
pip3 install --user -r requirements.txt
```

### Step 5: Set File Permissions

```bash
# Make setup script executable
chmod +x setup.sh

# Set proper file permissions
chmod +x app.py
chmod 644 requirements.txt
chmod -R 644 templates/
```

### Step 6: Run the Setup Script

```bash
# Run the automated setup
./setup.sh
```

This will:
- Check Python version
- Install dependencies
- Verify all files are present
- Set up the environment

### Step 7: Configure Firewall (Important!)

```bash
# Allow SSH (if not already configured)
sudo ufw allow ssh

# Allow control panel port (be specific about source IP for security)
sudo ufw allow from YOUR_IP_ADDRESS to any port 5000

# Or allow from any IP (less secure, only for testing)
sudo ufw allow 5000

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Step 8: Start the Control Panel

```bash
# Start the control panel
python3 app.py
```

You should see output like:
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://YOUR_SERVER_IP:5000
```

### Step 9: Access the Control Panel

Open your web browser and go to:
```
http://YOUR_SERVER_IP:5000
```

**Default Login Credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **CHANGE THESE IMMEDIATELY AFTER FIRST LOGIN!**

## 🔧 Post-Installation Configuration

### Change Default Credentials

1. Edit the `app.py` file:
```bash
nano app.py
```

2. Find this section:
```python
# Simple authentication (enhance this in production)
if username == 'admin' and password == 'admin123':  # Change this!
```

3. Change `admin123` to a strong password

4. Restart the control panel:
```bash
# Stop with Ctrl+C, then restart
python3 app.py
```

### Run as a Service (Production Setup)

Create a systemd service to run the control panel automatically:

```bash
# Create service file
sudo nano /etc/systemd/system/wordpress-control.service
```

Add this content:
```ini
[Unit]
Description=WordPress Control Panel
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/wordpress-control
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable wordpress-control

# Start the service
sudo systemctl start wordpress-control

# Check status
sudo systemctl status wordpress-control
```

### Set Up Reverse Proxy (Optional but Recommended)

For production, set up Nginx as a reverse proxy:

```bash
# Install Nginx if not already installed
sudo apt install -y nginx

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/wordpress-control
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/wordpress-control /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## 🔒 Security Recommendations

### 1. Firewall Configuration
```bash
# Only allow specific IPs to access the control panel
sudo ufw delete allow 5000
sudo ufw allow from YOUR_OFFICE_IP to any port 5000
sudo ufw allow from YOUR_HOME_IP to any port 5000
```

### 2. SSL Certificate (Highly Recommended)
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 3. Database Security
```bash
# Set proper permissions on SQLite database
chmod 600 /home/username/wordpress-control/wordpress_control.db
```

### 4. Regular Backups
```bash
# Create backup script
nano /home/username/backup-control-panel.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR="/home/username/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /home/username/wordpress-control/wordpress_control.db $BACKUP_DIR/wordpress_control_$DATE.db

# Keep only last 7 backups
find $BACKUP_DIR -name "wordpress_control_*.db" -mtime +7 -delete
```

Make executable and add to cron:
```bash
chmod +x /home/username/backup-control-panel.sh

# Add to crontab (daily backup at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/username/backup-control-panel.sh") | crontab -
```

## 🎯 Using the Control Panel

### First Time Setup

1. **Login** with default credentials
2. **Change password** in app.py
3. **System Setup**: Click "System Setup" to install Nginx, MariaDB, PHP
4. **Create First Site**: Use "Add New Site" to create your first WordPress installation

### Creating WordPress Sites

1. Click "Add New Site"
2. Enter domain name (e.g., `example.com`)
3. Click "Create WordPress Site"
4. Wait for installation to complete
5. Visit your new WordPress site!

### Managing Plugin Permissions

For WPVivid backup plugin:
1. Install WPVivid through WordPress admin
2. Go to site details in control panel
3. Click "Plugin Permissions"
4. Enter `wpvividbackups`
5. Click "Apply Permissions"

## 🐛 Troubleshooting

### Control Panel Won't Start
```bash
# Check Python version
python3 --version

# Check if port is in use
sudo netstat -tlnp | grep :5000

# Check dependencies
pip3 show Flask
```

### Command Execution Errors (cd command not found)
If you see errors like "sudo: cd: command not found":
```bash
# This is already fixed in the latest version
# The issue was with shell built-in commands and sudo
# Make sure you're using the updated app.py file
```

### File Permission Issues
```bash
# If WordPress installation fails due to permissions:
sudo chown -R www-data:www-data /var/www/
sudo chmod -R 755 /var/www/

# If Nginx config creation fails:
sudo chmod 755 /etc/nginx/sites-available/
```

### Database Errors
```bash
# Check MariaDB status
sudo systemctl status mariadb

# Restart MariaDB
sudo systemctl restart mariadb
```

### Permission Errors
```bash
# Fix ownership
sudo chown -R username:username /home/username/wordpress-control

# Check sudo privileges
sudo -l
```

### Nginx Issues
```bash
# Check Nginx status
sudo systemctl status nginx

# Check configuration
sudo nginx -t

# View error logs
sudo tail -f /var/log/nginx/error.log
```

## 📞 Getting Help

If you encounter issues:

1. **Check the logs** in the control panel (Site Details page)
2. **Verify system requirements** are met
3. **Check firewall settings** if you can't access the control panel
4. **Review error messages** in the terminal where you started the control panel

## 🔄 Updating the Control Panel

To update the control panel:

```bash
# Stop the service
sudo systemctl stop wordpress-control

# Backup current version
cp -r /home/username/wordpress-control /home/username/wordpress-control-backup

# Replace files with new version
# ... upload new files ...

# Start the service
sudo systemctl start wordpress-control
```

## ✅ Success Checklist

- [ ] Server is accessible via SSH
- [ ] Python 3.8+ is installed
- [ ] Control panel files are uploaded
- [ ] Dependencies are installed
- [ ] Firewall is configured
- [ ] Control panel starts without errors
- [ ] Web interface is accessible
- [ ] Default credentials are changed
- [ ] System setup completed successfully
- [ ] First WordPress site created successfully

**🎉 Your WordPress Control Panel is now ready for production use!**

---

**Need Help?** 
- Check the main README.md for detailed feature documentation
- Review DEPLOYMENT_PLAN.md for architecture details
- Ensure all steps in this guide are completed in order 