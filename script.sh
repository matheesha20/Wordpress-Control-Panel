#sudo apt update && sudo apt upgrade -y

#sudo apt install -y nginx mariadb-server php-fpm php-mysql php-xml php-gd php-curl php-mbstring unzip

#sudo systemctl enable --now nginx mariadb php8.1-fpm

#sudo mysql_secure_installation

---------------------------------------------------------------------------------------------------------------------

sudo mysql -u root -p

CREATE DATABASE wp_ammida CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'user_ammida'@'localhost' IDENTIFIED BY '!&#prog83e&ljaxeD+EM';
GRANT ALL ON wp_ammida.* TO 'user_ammida'@'localhost';

FLUSH PRIVILEGES;
EXIT;

---------------------------------------------------------------------------------------------------------------------

sudo mkdir -p /var/www/ammidatours.com/public_html

sudo chown -R www-data:www-data /var/www/ammidatours.com
sudo chmod -R 755 /var/www

cd /var/www/ammidatours.com/public_html
sudo wget https://wordpress.org/latest.zip
sudo unzip latest.zip && sudo mv wordpress/* . && sudo rm -rf wordpress latest.zip

sudo cp wp-config-sample.php wp-config.php

sudo nano wp-config.php

define('DB_NAME', 'wp_ammida');
define('DB_USER', 'user_ammida');
define('DB_PASSWORD', '!&#prog83e&ljaxeD+EM');
$table_prefix = 'ammida_';

define( 'FS_METHOD', 'direct' );

---------------------------------------------------------------------------------------------------------------------


sudo nano /etc/nginx/sites-available/bpo_backend

server {
    listen 127.0.0.1:8081;
    root /var/www/bpo.lk/public_html;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
    }

    location ~ /\.ht {
        deny all;
    }
    client_max_body_size 512M;
}

sudo ln -s /etc/nginx/sites-available/bpo_backend /etc/nginx/sites-enabled/

---------------------------------------------------------------------------------------------------------------------

sudo nano /etc/nginx/sites-available/bpo.lk


server {
    listen 80;
    server_name bpo.lk www.bpo.lk;

    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    client_max_body_size 512M;
}


sudo ln -s /etc/nginx/sites-available/ammidatours.com /etc/nginx/sites-enabled/

sudo nginx -t && sudo systemctl reload nginx

---------------------------------------------------------------------------------------------------------------------

sudo nano /var/www/bpo.lk/public_html/wp-config.php

if (
    isset($_SERVER['HTTP_X_FORWARDED_PROTO']) &&
    $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https'
) {
    $_SERVER['HTTPS'] = 'on';
}


sudo nginx -t
sudo systemctl reload nginx
sudo systemctl restart php8.1-fpm

---------------------------------------------------------------------------------------------------------------------

#sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ammidatours.com -d www.ammidatours.com  --No Need this command

---------------------------------------------------------------------------------------------------------------------

sudo adduser --home /var/www/ammidatours.com/public_html ftp_ammida

sudo chown -R ftp_ammida:www-data /var/www/ammidatours.com/public_html
sudo chmod -R 755 /var/www/ammidatours.com/public_html

sudo chown -R www-data:www-data /var/www/ammidatours.com/public_html
sudo find /var/www/ammidatours.com/public_html -type d -exec chmod 755 {} \;
sudo find /var/www/ammidatours.com/public_html -type f -exec chmod 644 {} \;

sudo systemctl restart vsftpd

---------------------------------------------------------------------------------------------------------------------

#sudo nano /etc/php/8.1/fpm/php.ini

#upload_max_filesize = 512M
#post_max_size      = 512M
#memory_limit       = 1G
#max_execution_time = 300
#max_input_time     = 300

#sudo systemctl restart php8.1-fpm

---------------------------------------------------------------------------------------------------------------------

sudo chown -R www-data:www-data /var/www/ammidatours.com/public_html/wp-content/wpvividbackups
sudo chmod -R 755      /var/www/ammidatours.com/public_html/wp-content/wpvividbackups