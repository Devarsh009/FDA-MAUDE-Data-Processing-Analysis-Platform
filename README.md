# MAUDE Data Processor

A comprehensive web application for processing and analyzing FDA MAUDE (Manufacturer and User Facility Device Experience) medical device adverse event data. Features AI-powered IMDRF code mapping, manufacturer normalization, secure authentication, and data visualization capabilities.

## 🚀 Features

- **🔐 Secure Authentication** - User registration, login, and password recovery via email
- **📊 Data Processing** - Clean and standardize MAUDE CSV/Excel files with intelligent column detection
- **🏷️ IMDRF Code Mapping** - Hierarchical mapping of device problems to IMDRF codes using Annex A-G structure
- **🏭 Manufacturer Normalization** - AI-assisted manufacturer name cleanup and M&A resolution with web verification
- **📅 Date Standardization** - Automatic conversion to DD-MM-YYYY format
- **✅ Data Validation** - Comprehensive validation with regulatory compliance checks
- **🎨 Modern UI** - Beautiful, responsive web interface with drag-and-drop file upload
- **📈 Data Visualization** - Interactive dashboards and analytics (coming soon)

## 🛠️ Tech Stack

- **Backend:** Python 3.8+, Flask
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **AI/ML:** Groq API (Llama 3.1 70B)
- **Data Processing:** Pandas, OpenPyXL, xlrd
- **Authentication:** Flask-Login, bcrypt
- **Email:** Flask-Mail (Gmail/Mailgun)

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/maude-data-processor.git
   cd maude-data-processor
   ```

2. **Install dependencies**
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Set the following environment variables (or update `run.py`):
   ```bash
   # Required
   GROQ_API_KEY=your-groq-api-key
   
   # Optional (for password reset)
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   MAIL_DEFAULT_SENDER=your-email@gmail.com
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

5. **Access the application**
   - Open http://localhost:5000 in your browser
   - Register a new account to get started

## 📖 Usage

1. **Register/Login** - Create an account or sign in
2. **Upload MAUDE File** - Drag and drop or select CSV/Excel file
3. **Upload IMDRF Annexure** (Optional) - Upload Annexes A-G file for IMDRF code mapping
4. **Process** - Click "Process File" to start the pipeline
5. **Download** - Download the cleaned and enriched output file

## 🔄 Data Processing Pipeline

The application processes MAUDE data through the following stages:

1. **Column Identification** - AI-assisted detection of required columns
2. **Data Cleaning** - Removal of specified columns and data sanitization
3. **Date Standardization** - Conversion to DD-MM-YYYY format
4. **Row Filtering** - Removal of rows with missing critical dates
5. **Manufacturer Normalization** - AI-powered name cleanup and M&A resolution
6. **IMDRF Mapping** - Hierarchical mapping to IMDRF codes (Level-1 → Level-2 → Level-3)
7. **Validation** - Comprehensive output validation with regulatory compliance checks

## 🔒 Security

- Passwords hashed with bcrypt
- Password reset tokens expire after 1 hour
- User data stored securely in JSON files
- API keys managed via environment variables
- No sensitive data committed to repository

## 📁 Project Structure

```
maude-data-processor/
├── backend/
│   ├── auth.py                    # Authentication & user management
│   ├── column_identifier.py       # AI-assisted column detection
│   ├── groq_client.py             # Groq API integration
│   ├── imdrf_mapper.py            # IMDRF code mapping logic
│   ├── manufacturer_normalizer.py # Manufacturer normalization
│   └── processor.py               # Main processing pipeline
├── templates/
│   ├── index.html                 # Main dashboard
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── forgot_password.html       # Password recovery
│   └── reset_password.html        # Password reset
├── app.py                         # Flask application
├── config.py                      # Configuration settings
├── run.py                         # Application launcher
└── requirements.txt               # Python dependencies
```

## 🔧 Configuration

### Email Setup (Password Reset)

**Gmail:**
1. Enable 2-Step Verification in Google Account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Set `MAIL_USERNAME` and `MAIL_PASSWORD` environment variables

**Mailgun (Recommended for Production):**
1. Sign up at https://www.mailgun.com (free tier: 1,000 emails/month)
2. Verify domain and get SMTP credentials
3. Set environment variables:
   ```bash
   MAIL_SERVER=smtp.mailgun.org
   MAIL_PORT=587
   MAIL_USERNAME=postmaster@your-domain.mailgun.org
   MAIL_PASSWORD=your-mailgun-password
   MAIL_USE_TLS=True
   ```

## 🚧 Future Enhancements

- Interactive data visualization dashboards
- Advanced analytics and reporting
- Export to multiple formats (PDF, JSON)
- Batch processing capabilities
- API endpoints for programmatic access
- Real-time processing status updates

## 📝 License

[Add your license here]

## 👤 Author

Devarsh Radadia

## 🙏 Acknowledgments

- FDA MAUDE database
- IMDRF (International Medical Device Regulators Forum)
- Groq for AI/ML capabilities

---

**Note:** This is a production-ready application designed for processing FDA medical device adverse event data with regulatory compliance in mind.
