# Webflow CMS Bulk Editor

A simple Python/Flask web application that transforms Webflow CMS management with seamless bulk editing capabilities. Connect your Webflow API key to instantly access all your sites and collections through an intuitive interface.

## 🌟 Key Features

- **Secure Local Setup** - API credentials stored safely in local environment files
- **Smart Site Navigation** - Auto-populated dropdowns for sites and collections
- **Bulk Edit Interface** - Edit all CMS items simultaneously in a clean table layout
- **Universal Content Support** - Modify text, images, and all field types at once
- **One-Click Publishing** - Update and publish changes directly to your live CMS
- **Pagination Support** - Handle large collections with efficient pagination
- **Real-time Feedback** - Visual indicators for modified fields and operation status
- **Rate Limit Compliance** - Built-in API rate limiting for reliable operation

## 🏗️ Architecture

This application is built using:
- **Backend**: Python 3.9+ with Flask framework
- **Frontend**: Vanilla JavaScript with modern ES6+ features
- **Security**: Environment-based API token management
- **API**: Webflow API v2 with Site Token authentication

## 📋 Prerequisites

- Python 3.9 or newer
- A Webflow site with API access
- Webflow Site Token (not OAuth - see setup instructions)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone or download this repository
cd webflow-bulk-editor

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Access

1. Go to your Webflow site dashboard
2. Navigate to Site Settings → Integrations
3. Generate a new **Site Token** (not OAuth token)
4. Copy the generated token

### 3. Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file and add your token
WEBFLOW_API_TOKEN=your_webflow_api_token_here
```

### 4. Launch Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📖 How to Use

### Getting Started
1. **Launch the application** and open your browser to `http://localhost:5000`
2. **Select your Webflow site** from the dropdown (populated automatically)
3. **Choose a collection** to edit from the second dropdown
4. **Click "Load Collection"** to fetch the data

### Bulk Editing
1. **Edit fields directly** in the table - all standard CMS field types are supported:
   - Plain text, rich text, email, phone, links
   - Numbers, dates, switches (checkboxes)
   - Images and files (via URL)
   - References to other collection items
   - Select options from predefined lists

2. **Visual feedback** - Modified fields are highlighted with a yellow background

3. **Pagination** - For large collections, use Previous/Next buttons to navigate pages

### Publishing Changes
1. **Review changes** - The interface shows how many items have been modified
2. **Click "Update & Publish"** - This performs two operations:
   - Updates all modified CMS items
   - Publishes the site to make changes live
3. **Monitor progress** - Real-time status updates during the process

## 🔧 Supported Field Types

| Webflow Field Type | Interface Element | Notes |
|------------------|------------------|-------|
| PlainText | Text input | Standard text field |
| RichText | Textarea | HTML content supported |
| Email | Email input | Browser validation |
| Phone | Tel input | Phone number format |
| Link | URL input | Browser validation |
| Number | Number input | Decimal values supported |
| Switch | Checkbox | True/false values |
| DateTime | DateTime picker | ISO 8601 format |
| Option | Dropdown select | Predefined choices |
| Image/File | Text input + preview | URL-based (see limitations) |
| Reference | Text input | Referenced item ID |
| Multi-Reference | Text input | Comma-separated IDs |

## ⚠️ Important Limitations

### File Upload Limitation
The Webflow API does not support direct file uploads when updating CMS items. For image and file fields:
- **Current approach**: Enter publicly accessible URLs
- **Alternative**: Use Webflow's Assets API separately to upload files first, then use the returned URL

### API Rate Limits
- **General API**: 60-120 requests per minute (varies by plan)
- **Publishing**: 1 publish per minute maximum
- **Built-in protection**: The app automatically manages these limits

### Authentication Method
This app uses **Site Tokens**, not OAuth:
- ✅ Perfect for personal/internal tools
- ✅ Simpler setup and maintenance
- ❌ Cannot be distributed as a public app
- ❌ Requires manual token generation per site

## 🛡️ Security Best Practices

### Token Management
- **Never commit** your `.env` file to version control
- **Rotate tokens** regularly in Webflow settings
- **Revoke immediately** if compromise is suspected
- **Limit access** to the machine running this application

### Local Operation
- This tool is designed to run locally on your machine
- API credentials never leave your local environment
- No external services or third-party integrations

## 🐛 Troubleshooting

### "API connection failed"
- Verify your `WEBFLOW_API_TOKEN` in the `.env` file
- Check that the token hasn't expired
- Ensure you're using a Site Token, not an OAuth token

### "Rate limit exceeded"
- The app will automatically retry after the required delay
- Consider editing fewer items at once for large operations

### "Resource not found"
- Verify the site/collection still exists
- Check that your API token has access to the selected site

### Fields not saving
- Ensure field values match the expected format
- Check browser console for detailed error messages
- Some field types require specific formatting (dates, references)

## 🔄 API Workflow

The application follows this sequence:

1. **Authentication**: Validates API token on startup
2. **Site Discovery**: Fetches all accessible sites
3. **Collection Discovery**: Loads collections for selected site
4. **Schema Retrieval**: Gets field definitions for proper rendering
5. **Data Fetching**: Loads collection items with pagination
6. **Bulk Updates**: Patches modified items in chunks of 100
7. **Site Publishing**: Publishes to all domains including Webflow subdomain

## 📝 Technical Details

### Project Structure
```
webflow-bulk-editor/
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Single-page interface
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
├── .env              # Your API credentials (create this)
├── .gitignore        # Excludes sensitive files
└── README.md         # This documentation
```

### API Endpoints Used
- `GET /v2/sites` - List accessible sites
- `GET /v2/sites/{site_id}/collections` - List collections
- `GET /v2/collections/{collection_id}` - Get collection schema
- `GET /v2/collections/{collection_id}/items` - Get collection items
- `PATCH /v2/collections/{collection_id}/items` - Bulk update items
- `POST /v2/sites/{site_id}/publish` - Publish site

## 🤝 Contributing

This tool was built according to the comprehensive technical specification for local Webflow CMS bulk editing. Contributions are welcome for:

- Additional field type support
- Enhanced error handling
- UI/UX improvements
- Performance optimizations

## 📄 License

This project is provided as-is for educational and internal use purposes.

---

**Perfect for**: Content managers, agencies, and developers who need to efficiently update multiple Webflow CMS entries without the tedium of individual item editing.