# Deploying to DigitalOcean with Apache

This guide provides step-by-step instructions for deploying the Object Counter application to a DigitalOcean Droplet running Ubuntu, using **Apache** as the reverse proxy.

This guide has been personalized with the configuration details you provided.

## Prerequisites
- A DigitalOcean account and a Droplet with at least 2 GB of RAM.
- Your domain `counting.sytes.net` pointed at your Droplet's IP address `159.203.138.32`.
- Your project code cloned into `/var/www/html/Counting/`.

---

### Step 1: Initial Server Setup

First, SSH into your Droplet. Then, update your server and install the necessary system packages.

```bash
# Update package lists and upgrade existing packages
sudo apt update && sudo apt upgrade -y

# Install Python, pip, virtual environment tools, and Apache
sudo apt install python3-pip python3-venv apache2 -y

# Install OpenCV's system dependencies
sudo apt install libgl1-mesa-glx -y

# Enable necessary Apache modules
sudo a2enmod proxy proxy_http rewrite
sudo systemctl restart apache2
```

### Step 2: Application Code Setup

Your code is already cloned. The next steps are to set up the Python environment and its ownership. The `www-data` user needs to own the project files to run the application securely.

```bash
# Navigate to your project directory
cd /var/www/html/Counting

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the Python dependencies
pip install -r requirements.txt

# Set ownership for the web server user
# Deactivate virtualenv first before running chown
deactivate
sudo chown -R www-data:www-data /var/www/html/Counting
```

### Step 3: Create a systemd Service File

This will ensure your application runs as a service, automatically starting on boot and restarting if it crashes.

Create a new service file:
```bash
sudo nano /etc/systemd/system/object-counter.service
```

Paste the following content into the file. It has been updated with your specific paths and the recommended `www-data` user.

```ini
[Unit]
Description=Gunicorn instance to serve the Object Counter app
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/html/Counting
Environment="PATH=/var/www/html/Counting/venv/bin"
ExecStart=/var/www/html/Counting/venv/bin/gunicorn --workers 3 --bind unix:object-counter.sock -m 007 --timeout 120 app:app

[Install]
WantedBy=multi-user.target
```

After saving the file, start and enable the new service:
```bash
sudo systemctl start object-counter
sudo systemctl enable object-counter
```

### Step 4: Configure Apache as a Reverse Proxy

Create a new Apache configuration file for your site:
```bash
sudo nano /etc/apache2/sites-available/object-counter.conf
```

Paste in the following configuration, which has been updated with your domain and socket path.

```apache
<VirtualHost *:80>
    ServerName counting.sytes.net

    ProxyPreserveHost On
    ProxyPass / unix:/var/www/html/Counting/object-counter.sock|http://localhost/
    ProxyPassReverse / unix:/var/www/html/Counting/object-counter.sock|http://localhost/
</VirtualHost>
```

Enable this site configuration, test the syntax, and restart Apache:
```bash
# Enable the new site
sudo a2ensite object-counter.conf

# Test the Apache configuration for syntax errors
sudo apache2ctl configtest

# Restart Apache to apply the changes
sudo systemctl restart apache2
```

### Step 5: Firewall and Final Steps

Allow Apache traffic through the firewall:
```bash
sudo ufw allow 'Apache Full'
```

At this point, you should be able to access your application at `http://counting.sytes.net`.

### Crucial Final Step: HTTPS/SSL

Because the application uses the device camera, it **must** be served over a secure HTTPS connection. Use Let's Encrypt and Certbot to secure your site for free.

DigitalOcean has an excellent tutorial for this: [How To Secure Apache with Let's Encrypt on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-secure-apache-with-let-s-encrypt-on-ubuntu-22-04). When you run `sudo certbot --apache`, it will automatically detect your `counting.sytes.net` configuration and set up SSL.
