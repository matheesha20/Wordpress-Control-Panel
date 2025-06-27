#!/bin/bash

# WordPress Multi-Site Control Panel Setup Script
echo "🚀 WordPress Multi-Site Control Panel Setup"
echo "==========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root. Please run as a user with sudo privileges."
   exit 1
fi

# Check if sudo is available
if ! command -v sudo &> /dev/null; then
    echo "❌ sudo is required but not installed. Please install sudo first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "❌ Python 3.8+ required. Current version: $python_version"
    echo "Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "📦 Installing pip..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python dependencies installed successfully"

# Create templates directory if it doesn't exist
if [ ! -d "templates" ]; then
    echo "📁 Creating templates directory..."
    mkdir -p templates
fi

# Set proper permissions
echo "🔒 Setting file permissions..."
chmod +x app.py
chmod 644 requirements.txt
chmod 644 README.md

# Check if all required files exist
required_files=("app.py" "requirements.txt" "templates/base.html" "templates/login.html" "templates/dashboard.html" "templates/add_site.html" "templates/system_setup.html" "templates/site_details.html")

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo "❌ Missing required files:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    echo "Please ensure all files are present before running setup."
    exit 1
fi

echo "✅ All required files present"

# Display final instructions
echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Run the control panel:"
echo "   python3 app.py"
echo ""
echo "2. Access the control panel at:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo "   or"
echo "   http://localhost:5000"
echo ""
echo "3. Login with default credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "- Change the default password in app.py before production use"
echo "- Configure firewall to restrict access to port 5000"
echo "- Set up HTTPS for production environments"
echo ""
echo "📖 For detailed instructions, see README.md"
echo ""
echo "🚀 Ready to manage multiple WordPress installations!" 