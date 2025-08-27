# Automatic Deployments with GitHub Webhooks

This guide explains how to set up automatic deployments for your application. When you push a new commit to your `final-version` branch on GitHub, this system will automatically pull the changes onto your server and restart the application.

This process involves four main parts:
1. A deployment script on your server.
2. A small listener application on your server.
3. A systemd service to run the listener.
4. A webhook configured in your GitHub repository.

---

### Step 1: Create the Deployment Script

This script contains the commands needed to update and restart your application.

First, create the script file:
```bash
# Navigate to your project directory
cd /var/www/html/Counting

# Create a new script file
sudo nano deploy.sh
```

Paste the following content into `deploy.sh`:

```bash
#!/bin/bash

# Navigate to the project directory
cd /var/www/html/Counting || exit

# Pull the latest changes from the final-version branch
git pull origin final-version

# Activate the virtual environment
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt

# Restart the Gunicorn service
sudo systemctl restart object-counter

echo "Deployment finished at $(date)"
```

Save the file, and then make it executable:
```bash
sudo chmod +x deploy.sh
```

### Step 2: Create the Webhook Listener App

This is a simple Flask application that listens for a notification from GitHub.

Create the Python file for the listener:
```bash
# Make sure you are in the project directory
# /var/www/html/Counting
sudo nano webhook_listener.py
```

Paste the following Python code into the file.

```python
import hmac
import hashlib
import subprocess
from flask import Flask, request, abort

app = Flask(__name__)

# IMPORTANT: Set a secret token here and in the GitHub webhook settings.
# This can be any random string of your choice.
APP_SECRET = 'your_very_secret_token_here'

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify the request is from GitHub
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        abort(403)

    sha_name, signature_hash = signature.split('=', 1)
    if sha_name != 'sha256':
        abort(501)

    mac = hmac.new(APP_SECRET.encode(), msg=request.data, digestmod=hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), signature_hash):
        abort(403)

    # If the signature is valid, run the deployment script
    if request.json.get('ref') == 'refs/heads/final-version':
        subprocess.Popen(['./deploy.sh', '>>', 'deploy.log', '2>&1'])
        return 'Deployment started', 200

    return 'Push was not to the final-version branch', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

### Step 3: Create a systemd Service for the Listener

This service will run the `webhook_listener.py` app continuously.

Create a new service file:
```bash
sudo nano /etc/systemd/system/webhook_listener.service
```

Paste the following configuration:

```ini
[Unit]
Description=Webhook listener for auto-deployment
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/html/Counting
# The listener runs using the same virtual environment
ExecStart=/var/www/html/Counting/venv/bin/python webhook_listener.py

[Install]
WantedBy=multi-user.target
```

Now, start and enable the listener service:
```bash
sudo systemctl start webhook_listener
sudo systemctl enable webhook_listener
```

### Step 4: Configure the GitHub Webhook

The final step is to tell GitHub to send notifications to your listener.

1.  Go to your repository on GitHub.
2.  Click on **Settings**, then **Webhooks** in the side menu.
3.  Click **Add webhook**.
4.  **Payload URL:** Enter `http://counting.sytes.net:5001/webhook`.
5.  **Content type:** Change this to `application/json`.
6.  **Secret:** Enter the same secret token you put in the `webhook_listener.py` file (e.g., `your_very_secret_token_here`). This is very important for security.
7.  **Which events would you like to trigger this webhook?** Select **Just the `push` event.**
8.  Make sure **Active** is checked.
9.  Click **Add webhook**.

### Step 5: Update Your Firewall

You need to allow traffic on the port your listener is using (5001 in this example).

```bash
sudo ufw allow 5001/tcp
```

---

That's it! Now, whenever you `git push` a new commit to the `final-version` branch, your server will automatically pull the changes and restart the application. You can check the `deploy.log` file in your project directory to see the output of the deployment script.
