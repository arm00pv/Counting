# Future Feature: n8n Integration

This document outlines a plan for a future feature: integrating the Object Counter application with [n8n](https://n8n.io/), a workflow automation tool.

The goal of this integration is to send the results of a successful analysis (the final count and the processed image) to an n8n webhook. This allows the data to be used in other applications and services, creating powerful automated workflows.

---

## Part 1: Frontend Changes

The user interface in `templates/index.html` needs to be updated to allow the user to specify their n8n webhook URL.

### 1. Add UI Elements

In `index.html`, add a new section for the n8n configuration, for example, below the "target-info" div:

```html
<!-- Add this after the 'target-info' div -->
<div class="n8n-container">
    <label for="n8n-webhook-url">n8n Webhook URL (optional):</label>
    <input type="text" id="n8n-webhook-url" size="50">
</div>
```

You will also need to add some basic styling for `.n8n-container` in the `<style>` block.

### 2. Update JavaScript Logic

The frontend JavaScript needs to be updated to send the webhook URL to the backend.

1.  **Get a reference to the new input field:**
    ```javascript
    const n8nWebhookUrl = document.getElementById('n8n-webhook-url');
    ```

2.  **Modify the `analyzeBtn` event listener:**
    Update the `payload` object to include the value from the new input field.

    ```javascript
    // Inside the analyzeBtn.addEventListener('click', ...)
    const webhookUrl = n8nWebhookUrl.value;
    let payload = {
        image: capturedImageData,
        threshold: threshold
    };
    if (selectedTargetImgData) {
        payload.target_image = selectedTargetImgData.split(',')[1];
    }
    if (webhookUrl) {
        payload.n8n_webhook_url = webhookUrl;
    }
    processFrame(payload);
    ```

---

## Part 2: Backend Changes

The backend `app.py` needs to be updated to handle sending the data to the webhook.

### 1. Add New Dependency

The `requests` library is needed to make HTTP requests to the n8n webhook. Add it to `requirements.txt`:
```
# requirements.txt
...
torchvision==0.18.0
requests==2.31.0
```
Remember to re-install dependencies after changing this file.

### 2. Update Backend Logic

Modify the `/process_frame` endpoint in `app.py`.

1.  **Import the `requests` library:**
    ```python
    import requests
    ```

2.  **Get the webhook URL from the payload:**
    ```python
    # Inside the process_frame() function
    n8n_webhook_url = data.get('n8n_webhook_url')
    ```

3.  **Send the webhook after a successful analysis:**
    After `process_image` returns the result, and just before returning the `jsonify` response, add the following logic:

    ```python
    # ... after processed_image, count = process_image(...)

    if n8n_webhook_url:
        try:
            # We need the processed image as base64 to send it
            _, buffer = cv2.imencode('.jpg', processed_image)
            processed_image_b64 = base64.b64encode(buffer).decode('utf-8')

            webhook_payload = {
                'count': count,
                'image_b64': processed_image_b64
            }
            requests.post(n8n_webhook_url, json=webhook_payload, timeout=5)
        except requests.exceptions.RequestException as e:
            # Log the error, but don't crash the main app
            print(f"Error sending webhook to n8n: {e}")

    # The rest of the function returns the response to the user as normal
    # ... return jsonify(...)
    ```

---

## Part 3: Example n8n Workflow

The user is responsible for creating their own workflow in n8n. Here is a basic example of how to capture the data.

1.  In your n8n canvas, create a new workflow.
2.  Add a **Webhook** node as the trigger.
3.  The node will display a **Test URL**. Copy this URL and paste it into the "n8n Webhook URL" input field in the Object Counter app.
4.  In the n8n Webhook node, click **"Listen for test event"**.
5.  Go back to the Object Counter app and click "Analyze".
6.  The webhook node in n8n should now receive the data (`count` and `image_b64`). You can now connect this data to other nodes, such as a **Google Sheets** node to log the count, or a **Slack** node to send a notification.
