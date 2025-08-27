# Deploying to DigitalOcean with Apache

This guide provides step-by-step instructions for deploying the Object Counter application to a DigitalOcean Droplet running Ubuntu, using **Apache** as the reverse proxy.

## Prerequisites
- A DigitalOcean account.
- A Droplet with at least 2 GB of RAM is recommended.
- A domain name pointed at your Droplet's IP address (for setting up HTTPS with Let's Encrypt).

---

### Step 1: Initial Server Setup

First, SSH into your new Droplet as the `root` user. Then, update your server and install the necessary system packages.

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

Next, get the application code onto your server and set up its Python environment.

```bash
# Clone the repository
# Make sure to use the correct branch, e.g., final-version
git clone https://github.com/arm00pv/Counting
cd Counting

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the Python dependencies
pip install -r requirements.txt
```

### Step 3: Create a systemd Service File

This will ensure your application runs as a service, automatically starting on boot and restarting if it crashes. This step is the same as the Nginx setup.

Create a new service file using a text editor like `nano`:
```bash
sudo nano /etc/systemd/system/object-counter.service
```

Paste the following content into the file.
**Important:** Make sure to replace `/root/Counting` with the actual path to your project directory. You can find this by running `pwd` inside the `Counting` directory.

```ini
[Unit]
Description=Gunicorn instance to serve the Object Counter app
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/root/Counting
Environment="PATH=/root/Counting/venv/bin"
ExecStart=/root/Counting/venv/bin/gunicorn --workers 3 --bind unix:object-counter.sock -m 007 --timeout 120 app:app

[Install]
WantedBy=multi-user.target
```

After saving the file, start and enable the new service:
```bash
sudo systemctl start object-counter
sudo systemctl enable object-counter
```

### Step 4: Configure Apache as a Reverse Proxy

Apache will act as the public-facing web server and pass requests to your Gunicorn application via the Unix socket.

Create a new Apache configuration file:
```bash
sudo nano /etc/apache2/sites-available/object-counter.conf
```

Paste in the following configuration. **Replace `your_domain_or_ip` with your server's IP address or your domain name.**

```apache
<VirtualHost *:80>
    ServerName your_domain_or_ip

    ProxyPreserveHost On
    ProxyPass / unix:/root/Counting/object-counter.sock|http://localhost/
    ProxyPassReverse / unix:/root/Counting/object-counter.sock|http://localhost/
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

At this point, you should be able to access your application at `http://your_domain_or_ip`.

### Crucial Final Step: HTTPS/SSL

Because the application uses the device camera, it **must** be served over a secure HTTPS connection. The easiest way to set this up is with Let's Encrypt and Certbot.

DigitalOcean has an excellent tutorial on this process for Apache: [How To Secure Apache with Let's Encrypt on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-secure-apache-with-let-s-encrypt-on-ubuntu-22-04).

Following that guide will install a free SSL certificate and automatically configure Apache to use it, completing your secure deployment.
