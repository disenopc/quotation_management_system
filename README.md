# Quotation Management Platform

Professional platform for managing client inquiries, quotations, and email responses with AI assistance.

## Table of Contents
1. [What This Platform Does](#what-this-platform-does)
2. [Installation Guide](#installation-guide)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Using the Platform](#using-the-platform)
6. [Importing Publishers](#importing-publishers)
7. [Migrating to AWS Bedrock](#migrating-to-aws-bedrock)
8. [Troubleshooting](#troubleshooting)

---

## What This Platform Does

This platform helps you:

1. **Manage Email Inquiries**: Automatically fetch and organize emails from your business inbox
2. **Client Database**: Store and search client information (name, email, phone)
3. **Response System**: Reply to inquiries directly from the platform with AI assistance
4. **Status Tracking**: Track inquiry status (pending, in progress, responded, closed) with dates
5. **Publisher Management**: Handle your 12,500+ publisher database with bulk email capabilities
6. **Secure Access**: Login-protected with user authentication stored in SQL database

---

## Installation Guide

### Step 1: Install Python

You need Python 3.8 or higher.

**Check if you have Python:**
```bash
python --version
```

**If you don't have Python, download it from:** https://www.python.org/downloads/

### Step 2: Set Up Project

1. **Navigate to your project folder:**
```bash
cd /path/to/project
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv
```

3. **Activate the virtual environment:**

On Windows:
```bash
venv\Scripts\activate
```

On Mac/Linux:
```bash
source venv/bin/activate
```

4. **Install required packages:**
```bash
cd backend
pip install -r requirements.txt
```

This installs:
- Flask (web server)
- Flask-CORS (cross-origin requests)
- Werkzeug (security)
- python-dotenv (environment variables)
- requests (HTTP requests for AI)

### Step 3: Initialize Database

The database will be created automatically on first run, but you can manually initialize it:

```bash
python -c "from database import db; print('Database initialized')"
```

This creates:
- `database/quotations.db` (SQLite database)
- All required tables (users, clients, inquiries, responses, publishers)

---

## Configuration

### Step 1: Create Environment File

Create a file called `.env` in the `backend` folder with these settings:

```env
# Database
DATABASE_PATH=database/quotations.db

# Security (CHANGE THIS IN PRODUCTION)
SECRET_KEY=your-super-secret-key-change-this-now

# Email Configuration (Gmail example)
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# AI Configuration - FREE (Groq)
AI_PROVIDER=free
FREE_AI_API_KEY=your-groq-api-key-here
FREE_AI_BASE_URL=https://api.groq.com/openai/v1
FREE_AI_MODEL=llama-3.1-70b-versatile

# Application
DEBUG=True
HOST=0.0.0.0
PORT=5000
```

### Step 2: Get Free AI API Key (Groq)

1. Go to https://console.groq.com
2. Sign up for free account
3. Create API key
4. Paste it in `.env` as `FREE_AI_API_KEY`

**Groq is FREE and FAST** for AI responses!

### Step 3: Configure Email

For Gmail:
1. Enable 2-factor authentication on your Google account
2. Generate "App Password": https://myaccount.google.com/apppasswords
3. Use the app password (not your regular password) in `.env`

For Outlook/Hotmail:
```env
IMAP_SERVER=outlook.office365.com
SMTP_SERVER=smtp-mail.outlook.com
```

---

## Running the Application

### Start the Server

1. **Navigate to backend folder:**
```bash
cd backend
```

2. **Run the server:**
```bash
python app.py
```

You should see:
```
Starting server on 0.0.0.0:5000
AI Provider: free
 * Running on http://0.0.0.0:5000
```

3. **Open your browser:**
Go to: `http://localhost:5000`

### Default Login

- **Username:** admin
- **Password:** admin123

**IMPORTANT:** Change the password immediately after first login!

---

## Using the Platform

### 1. Dashboard Overview

After login, you'll see:
- **Inquiries Tab**: All received emails with status and dates
- **Clients Tab**: Client database with search
- **Responses Tab**: Send replies with AI assistance
- **Publishers Tab**: Your 12,500+ publisher database

### 2. Syncing Emails

Click "Sync Emails" button to:
- Fetch new unread emails from your inbox
- Automatically create client records
- Create inquiry records with pending status

### 3. Managing Inquiries

**View Inquiry:**
- Click "View" to see full email content
- See client info, subject, message, date

**Respond to Inquiry:**
- Click "Respond" button
- Gets AI-generated response suggestion
- Edit as needed
- Send via email directly from platform
- Auto-marks as "responded" with timestamp

### 4. Status Flags

Inquiries have 4 statuses:
- **pending**: Just received, not yet addressed
- **in_progress**: Someone is working on it
- **responded**: Reply has been sent
- **closed**: Completed/archived

### 5. Client Management

- View all clients with pagination
- Search by name, email, or phone
- Add new clients manually
- Auto-created when emails arrive

### 6. AI Response Generation

1. Select an inquiry
2. Click "AI Generate"
3. AI creates professional response based on:
   - Original inquiry subject
   - Client message
   - Your business context
4. Edit the response as needed
5. Send directly via email

---

## Importing Publishers

You have 12,500 publishers to import. Here's how:

### Method 1: JSON File

Create a file `publishers.json`:

```json
[
  {
    "name": "Publisher Name 1",
    "email": "publisher1@example.com",
    "category": "Technology",
    "status": "active"
  },
  {
    "name": "Publisher Name 2",
    "email": "publisher2@example.com",
    "category": "News",
    "status": "active"
  }
]
```

### Method 2: Python Script

Create `import_publishers.py`:

```python
import requests
import json

# Your publishers data
publishers = [
    {"name": "Pub 1", "email": "pub1@example.com", "category": "Tech"},
    {"name": "Pub 2", "email": "pub2@example.com", "category": "News"},
    # ... 12,500 more
]

# Import in batches (optimized for performance)
batch_size = 1000
for i in range(0, len(publishers), batch_size):
    batch = publishers[i:i+batch_size]
    
    response = requests.post(
        'http://localhost:5000/api/publishers/bulk-import',
        json=batch,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Batch {i//batch_size + 1}: {response.json()}")
```

Run it:
```bash
python import_publishers.py
```

**Performance:** Optimized to handle 12,500+ records efficiently with batch processing and database indexing.

---

## Migrating to AWS Bedrock

Currently using FREE AI (Groq). When ready to scale to AWS Bedrock:

### Step 1: Set Up AWS

1. Get AWS account
2. Enable Bedrock in your region
3. Create IAM user with Bedrock permissions
4. Get Access Key ID and Secret Access Key

### Step 2: Update Configuration

In `.env`:
```env
AI_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

### Step 3: Install Boto3

In `requirements.txt`, uncomment:
```
boto3==1.34.0
botocore==1.34.0
```

Then run:
```bash
pip install boto3 botocore
```

### Step 4: Update Code

In `backend/ai_assistant.py`:

1. **Uncomment the imports at the top:**
```python
import boto3
from botocore.config import Config as BotoConfig
```

2. **Uncomment `_init_bedrock()` function**

3. **Uncomment `_generate_bedrock()` function**

4. **Restart server**

**That's it!** The code is already prepared for this migration.

---

## Troubleshooting

### Database Issues

**Error: "Database locked"**
- Close all connections to the database
- Restart the server

**Error: "Table doesn't exist"**
- Delete `database/quotations.db`
- Restart server (auto-creates tables)

### Email Issues

**Error: "IMAP connection failed"**
- Check email/password in `.env`
- For Gmail: Use App Password, not regular password
- Check IMAP is enabled in email settings

**Error: "SMTP connection failed"**
- Check SMTP server and port
- Gmail: smtp.gmail.com:587
- Outlook: smtp-mail.outlook.com:587

### AI Issues

**Error: "FREE_AI_API_KEY is required"**
- Get API key from https://console.groq.com
- Add to `.env` file

**AI response is slow**
- Normal for first request (model loading)
- Subsequent requests are faster
- Consider upgrading to Bedrock for production

### Login Issues

**Can't login with admin/admin123**
- Check database exists: `ls database/`
- Recreate database if needed
- Check console for errors

---

## API Endpoints Reference

For integration or custom scripts:

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/check` - Check auth status

### Inquiries
- `GET /api/inquiries` - List inquiries (pagination, filtering)
- `GET /api/inquiries/:id` - Get single inquiry
- `POST /api/inquiries` - Create inquiry
- `PUT /api/inquiries/:id/status` - Update status
- `GET /api/inquiries/stats` - Get statistics

### Clients
- `GET /api/clients` - List clients
- `POST /api/clients` - Create client
- `PUT /api/clients/:id` - Update client

### Responses
- `POST /api/responses` - Send response
- `GET /api/responses/inquiry/:id` - Get responses for inquiry

### Publishers
- `GET /api/publishers` - List publishers
- `POST /api/publishers/bulk-import` - Bulk import
- `GET /api/publishers/count` - Get total count

### Email
- `POST /api/email/sync` - Sync emails
- `POST /api/email/bulk-send` - Send bulk emails
- `GET /api/email/test` - Test email connection

### AI
- `POST /api/ai/generate-response` - Generate AI response

---

## Security Notes

1. **Change default password** after first login
2. **Use strong SECRET_KEY** in production
3. **Don't commit `.env`** to version control
4. **Use HTTPS** in production (not HTTP)
5. **Backup database** regularly

---

## Performance Notes

- **Database:** SQLite with WAL mode and optimized indexes
- **Pagination:** 50-100 records per page for fast loading
- **Batch Processing:** Handles 12,500+ publishers efficiently
- **Email Sync:** Fetches max 50 emails per sync to avoid timeouts

---

## Support

For issues:
1. Check this README
2. Check console for error messages
3. Verify `.env` configuration
4. Test email/AI connections separately

---

## Summary

You now have:
- A working quotation management platform
- Email sync and response system
- AI-assisted response generation
- Client and publisher databases
- Secure authentication
- Ready to scale to Bedrock

**Next Steps:**
1. Change default password
2. Configure email settings
3. Get Groq API key
4. Import your publishers
5. Start managing inquiries