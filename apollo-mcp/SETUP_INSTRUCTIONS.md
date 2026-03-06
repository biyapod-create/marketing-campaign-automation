# Apollo.io MCP Server - Setup Instructions

## 📋 Overview
This folder contains the Apollo.io MCP server by lkm1developer. This server allows Claude to search for prospects, enrich contact data, and access Apollo.io's 210M+ contact database.

## 🔧 Prerequisites
Before installing, you need:
1. **Node.js** (version 14 or higher)
2. **npm** (comes with Node.js)
3. **Apollo.io API Key**

## 🔑 Getting Your Apollo.io API Key

### Step 1: Log into Apollo.io
1. Go to https://app.apollo.io
2. Sign in to your account
3. You must be an admin or have API permissions

### Step 2: Navigate to API Settings
1. Click on your profile icon (top right)
2. Go to **Settings**
3. Click on **API** in the left sidebar
4. URL: https://developer.apollo.io/keys/

### Step 3: Create API Key
1. Click **"Create API Key"**
2. Enter a name (e.g., "MCP Server - Allennetic")
3. Enter description (e.g., "For Claude AI prospect search")
4. Choose either:
   - **Master Key** - Toggle "Set as master key" for full access
   - **Custom** - Select specific endpoints you want
5. Click **"Create API key"**
6. **IMPORTANT**: Copy the API key immediately and save it securely
   - You won't be able to see it again!

## 📦 Installation Steps

### 1. Open PowerShell or Command Prompt
Press `Windows + R`, type `powershell`, and press Enter

### 2. Navigate to This Folder
```powershell
cd "C:\Apollo + SMTP\apollo-mcp"
```

### 3. Clone the Repository
```powershell
git clone https://github.com/lkm1developer/apollo-io-mcp-server.git .
```

### 4. Install Dependencies
```powershell
npm install
```

### 5. Build the Project
```powershell
npm run build
```

### 6. Create Environment File
Create a file named `.env` in this folder with your API key:
```
APOLLO_IO_API_KEY=your_apollo_api_key_here
```

Replace `your_apollo_api_key_here` with your actual Apollo.io API key.

## 🚀 Testing the Server

Test if the server works:
```powershell
npm start
```

If you see the server running without errors, it's working!

## 🔗 Connecting to Claude Desktop

Add this configuration to your Claude Desktop config file:

**Location**: `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`

**Add this**:
```json
{
  "mcpServers": {
    "apollo-io": {
      "command": "node",
      "args": ["C:\\Apollo + SMTP\\apollo-mcp\\dist\\index.js"],
      "env": {
        "APOLLO_IO_API_KEY": "your_apollo_api_key_here"
      }
    }
  }
}
```

Replace `your_apollo_api_key_here` with your actual API key.

## ✅ What You Can Do With This MCP

Once connected, you can ask Claude to:

1. **Find Prospects**
   - "Find 20 tech startups in Lagos"
   - "Search for CTOs at fintech companies in Nigeria"

2. **Enrich Contact Data**
   - "Get the email for John Doe at Example Corp"
   - "Find contact information for the CEO of [Company]"

3. **Search Organizations**
   - "Find companies in the e-commerce sector with 50-200 employees"
   - "Show me businesses that raised funding recently"

4. **Check Job Postings**
   - "What companies are hiring developers in Nigeria?"
   - "Find businesses posting cloud engineering jobs"

## 🛠️ Troubleshooting

### Error: "Node is not recognized"
- You need to install Node.js from https://nodejs.org
- Download the LTS version and install it

### Error: "Git is not recognized"
- You need to install Git from https://git-scm.com
- Download and install, then restart PowerShell

### Error: "Invalid API key"
- Double-check your API key is copied correctly
- Make sure there are no extra spaces
- Verify the key is active in your Apollo.io dashboard

### Server won't start
- Make sure you ran `npm install` and `npm run build`
- Check that the `.env` file exists and has the correct API key

## 📚 Available Tools

The server provides these tools to Claude:

1. **people_enrichment** - Get detailed info about a person
2. **organization_enrichment** - Get company details
3. **people_search** - Find people by criteria
4. **organization_search** - Find companies by criteria
5. **organization_job_postings** - See company hiring activity

## 🔒 Security Notes

- Never share your API key publicly
- The `.env` file should be kept private
- Don't commit the `.env` file to version control

---

**Need Help?** Contact Allennetic support or check the official repository:
https://github.com/lkm1developer/apollo-io-mcp-server
