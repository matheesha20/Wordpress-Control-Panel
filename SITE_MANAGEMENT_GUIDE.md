# Site Management Guide - Delete & Retry Features

## 🗑️ Site Deletion

### Safe Site Deletion Process

The control panel provides a comprehensive site deletion feature that safely removes all components while creating backups.

#### What Gets Deleted:
1. **WordPress Files**: Complete `/var/www/domain/` directory
2. **Database**: Site database and dedicated user
3. **Nginx Configuration**: Virtual host files and symlinks
4. **FTP User**: Site-specific FTP account
5. **Control Panel Records**: Database entries and logs

#### Safety Features:
- ✅ **Automatic Backup**: Created before deletion in `/tmp/wp-backups/domain/`
- ✅ **Confirmation Required**: Multiple confirmation steps
- ✅ **Graceful Cleanup**: Uses `IF EXISTS` and error handling
- ✅ **System Protection**: Cannot damage other sites or system

#### How to Delete a Site:

**From Dashboard:**
1. Locate the site in the sites table
2. Click the red trash icon (🗑️) in the Actions column
3. Read the confirmation modal carefully
4. Check "I understand this will permanently delete the site"
5. Click "Delete Site Permanently"

**From Site Details:**
1. Go to site details page
2. Scroll to Quick Actions panel
3. Click "Delete Site" button
4. Confirm in the popup dialog

### Backup Location
Before deletion, backups are created in:
```
/tmp/wp-backups/domain.com/
├── database.sql          # Database dump
└── files.tar.gz         # WordPress files archive
```

## 🔄 Site Setup Retry

### Smart Resume Feature

When a site installation fails, the retry feature intelligently resumes from where it left off without damaging existing components.

#### What Gets Checked:
- ✅ **Database Existence**: Checks if database and user exist
- ✅ **WordPress Download**: Verifies WordPress files are present
- ✅ **Configuration Files**: Checks wp-config.php existence
- ✅ **Nginx Setup**: Validates virtual host configuration
- ✅ **FTP User**: Confirms user account creation
- ✅ **File Permissions**: Ensures proper ownership and permissions

#### Safe Resume Process:
1. **Status Check**: Analyzes what's already completed
2. **Smart Skip**: Skips successful steps to avoid conflicts
3. **Resume Point**: Continues from the failed step
4. **Completion**: Marks site as active when finished

#### When to Use Retry:
- 🔴 Site status shows "failed"
- 🔴 Installation was interrupted
- 🔴 Network issues during setup
- 🔴 Permission errors occurred
- 🔴 Service was temporarily unavailable

#### How to Retry Setup:

**From Dashboard:**
1. Look for sites with "Failed" status (red badge)
2. Click the yellow retry icon (🔄) in the Actions column
3. Review the retry confirmation modal
4. Click "Retry Setup"

**From Site Details:**
1. Go to failed site details page
2. Click "Retry Setup" button in Quick Actions
3. Confirm the retry operation

### Resume Safety Features:

#### ✅ **Non-Destructive**
- Never overwrites existing working components
- Skips completed steps automatically
- Preserves existing data and configurations

#### ✅ **System Protection**
- Cannot affect other sites
- Maintains system integrity
- Uses safe file operations

#### ✅ **Error Recovery**
- Handles partial installations gracefully
- Recovers from network interruptions
- Manages permission conflicts safely

## 📊 Status Indicators

### Site Status Types:
- 🟢 **Active**: Site is fully functional
- 🟡 **Pending**: Installation in progress
- 🔴 **Failed**: Installation failed, retry available

### Action Buttons by Status:

#### Active Sites:
- 👁️ View Details
- 🌐 Visit Website  
- 🛡️ Plugin Permissions
- 🗑️ Delete Site

#### Failed Sites:
- 👁️ View Details
- 🔄 **Retry Setup** (yellow button)
- 🛡️ Plugin Permissions
- 🗑️ Delete Site

#### Pending Sites:
- 👁️ View Details
- 🛡️ Plugin Permissions
- 🗑️ Delete Site

## 🔧 Technical Details

### Deletion Process:
```bash
# 1. Create backup
mkdir -p /tmp/wp-backups/domain/
mysqldump database > backup.sql
tar -czf files.tar.gz /var/www/domain/

# 2. Remove database
DROP DATABASE IF EXISTS database;
DROP USER IF EXISTS 'user'@'localhost';

# 3. Remove Nginx config
rm -f /etc/nginx/sites-enabled/domain
rm -f /etc/nginx/sites-available/domain
nginx -t && systemctl reload nginx

# 4. Remove FTP user
userdel ftp_user

# 5. Remove files
rm -rf /var/www/domain
```

### Retry Process:
```python
# 1. Check current status
check_database_exists()
check_wordpress_downloaded()
check_nginx_configured()
check_ftp_user_exists()

# 2. Resume from failures
if not database_exists:
    create_database()
if not wordpress_downloaded:
    download_wordpress()
# Continue for each component...
```

## 🚨 Important Notes

### Before Deleting:
1. **Download Important Data**: Export any critical content
2. **Verify Backup**: Ensure automatic backup is sufficient
3. **Check Dependencies**: Confirm no other systems depend on this site
4. **Document URLs**: Note any external links to the site

### Before Retrying:
1. **Check Resources**: Ensure server has adequate resources
2. **Verify Network**: Confirm internet connectivity for downloads
3. **Service Status**: Check nginx, mariadb, php-fpm are running
4. **Disk Space**: Ensure sufficient space for WordPress installation

## 🛡️ Best Practices

### Site Management:
- ✅ Regular monitoring of site status
- ✅ Prompt retry of failed installations
- ✅ Clean deletion of unused sites
- ✅ Backup verification before deletion
- ✅ Resource monitoring during operations

### Troubleshooting:
- 📋 Check activity logs in site details
- 📋 Verify system component status
- 📋 Review error messages carefully
- 📋 Use retry feature for transient failures
- 📋 Contact support for persistent issues

---

**These features ensure safe, efficient management of WordPress sites while protecting system integrity and preventing data loss.** 