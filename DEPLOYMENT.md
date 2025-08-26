# Deploying to DigitalOcean

This guide provides step-by-step instructions for deploying the Object Counter application to a DigitalOcean Droplet running Ubuntu.

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

# Install Python, pip, virtual environment tools, and Nginx
sudo apt install python3-pip python3-venv nginx -y

# Install OpenCV's system dependencies
sudo apt install libgl1-mesa-glx -y
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

This will ensure your application runs as a service, automatically starting on boot and restarting if it crashes.

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

### Step 4: Configure Nginx as a Reverse Proxy

Nginx will act as the public-facing web server and pass requests to your Gunicorn application.

Create a new Nginx configuration file:
```bash
sudo nano /etc/nginx/sites-available/object-counter
```

Paste in the following configuration. **Replace `your_domain_or_ip` with your server's IP address or your domain name.**

```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        include proxy_params;
        proxy_pass http://unix:/root/Counting/object-counter.sock;
    }
}
```

Enable this configuration by creating a symbolic link, then test and restart Nginx:
```bash
# Link the config file
sudo ln -s /etc/nginx/sites-available/object-counter /etc/nginx/sites-enabled

# Test the Nginx configuration for syntax errors
sudo nginx -t

# Restart Nginx to apply the changes
sudo systemctl restart nginx
```

### Step 5: Firewall and Final Steps

Allow Nginx traffic through the firewall:
```bash
sudo ufw allow 'Nginx Full'
```

At this point, you should be able to access your application at `http://your_domain_or_ip`.

### Crucial Final Step: HTTPS/SSL

Because the application uses the device camera, it **must** be served over a secure HTTPS connection. The easiest way to set this up is with Let's Encrypt and Certbot.

DigitalOcean has an excellent tutorial on this process: [How To Secure Nginx with Let's Encrypt on Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-22-04).

Following that guide will install a free SSL certificate and automatically configure Nginx to use it, completing your secure deployment.
