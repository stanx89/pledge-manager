# Pledge Manager Django Application

A Django web application for managing pledge records with file upload functionality and authentication.

## Features

- **Authentication**: Login protection for all functionality (username: `mubote`, password: `kayombo`)
- **File Upload**: Upload CSV or Excel files with pledge data
- **Data Management**: View, edit, and delete pledge records
- **Primary Key**: Mobile number as primary key (duplicates are updated)
- **Status Tracking**: Track normal message sent and WhatsApp sent status (default: false)
- **Card Capacity**: Auto-calculated capacity based on paid amount (0, 1, or 2)
- **SMS Integration**: Send SMS messages using Notify Africa API
- **WhatsApp Integration**: Send WhatsApp invitations with personalized images
- **Upload Logs**: Keep track of upload statistics and errors
- **Admin Interface**: Full Django admin interface for advanced management
- **Responsive UI**: Tailwind CSS responsive user interface

## Quick Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations** (this automatically creates the login user):
   ```bash
   python manage.py migrate
   ```

3. **Start the server**:
   ```bash
   python manage.py runserver
   ```

4. **Access the application**:
   - Navigate to http://127.0.0.1:8000
   - Login with: `mubote` / `kayombo`

## Authentication

The application is protected by login authentication:
- **Username**: `mubote`
- **Password**: `kayombo`  
- User is automatically created when running migrations
- All routes except static files require authentication

## Data Structure

### PledgeRecord Model
- `mobile_number` (Primary Key): Person's mobile number
- `name`: Person's name (editable)
- `pledge`: Pledged amount
- `paid`: Amount paid
- `remaining`: Remaining amount (auto-calculated: pledge - paid)
- `card_capacity`: Card capacity (auto-calculated based on paid amount)
  - 2 if paid >= $100,000
  - 1 if paid >= $50,000
  - 0 otherwise
- `normal_message_sent`: Boolean flag for normal message status (default: false)
- `whatsapp_sent`: Boolean flag for WhatsApp message status (default: false)
- `created_at`: Record creation timestamp
- `updated_at`: Record last update timestamp

### File Upload Requirements
- **Accepted Formats**: CSV, Excel (.xlsx, .xls)
- **Required Columns**: Name, Mobile Number, Pledge, Paid
- **Optional Column**: Remaining (will be calculated if not provided)
- **Duplicate Handling**: If mobile number exists, update pledge and paid amounts

## Installation & Setup

1. **Clone or create the project**:
   ```bash
   cd /Users/stan/harusi
   ```

2. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**:
   ```bash
   python manage.py runserver
   ```

7. **Configure SMS (Optional)**:
   Edit `pledge_manager/settings.py` and update:
   ```python
   NOTIFY_AFRICA_API_TOKEN = "your_actual_api_token"
   NOTIFY_AFRICA_SENDER_ID = "your_sender_id"
   ```

8. **Access the application**:
   - Main interface: http://127.0.0.1:8000/
   - Admin interface: http://127.0.0.1:8000/admin/

## Usage

### Upload File
1. Go to the upload page
2. Select a CSV or Excel file with the required columns
3. The system will process the file and show upload statistics
4. View upload logs to see what happened during processing

### Manage Records
- View all records with search functionality
- Edit individual records (name, amounts, message status)
- Delete records with confirmation
- Use pagination for large datasets

### Admin Interface
- Access full CRUD operations
- Bulk editing capabilities
- Advanced filtering and search
- Export functionality

### SMS Messaging
- Send individual SMS messages to specific records
- Send bulk SMS to multiple records at once
- Customizable message templates with variable substitution
- Automatic status tracking (normal_message_sent field updated)
- Integration with Notify Africa SMS API
- Default message template with pledge details

## Sample File Format

Create a CSV file with these columns:
```csv
Name,Mobile Number,Pledge,Paid,Remaining
John Doe,1234567890,1000,500,500
Jane Smith,0987654321,2000,2000,0
```

A sample file `sample_pledges.csv` is included in the project root.

## File Processing Logic

1. **Column Mapping**: The system automatically maps various column name formats:
   - Name: name, full_name, person_name
   - Mobile Number: mobile_number, mobile, phone, phone_number, contact
   - Pledge: pledge, pledged, pledge_amount
   - Paid: paid, amount_paid, paid_amount
   - Remaining: remaining, balance, remaining_amount

2. **Update Logic**:
   - If mobile number exists: Update name, pledge, and paid amounts
   - If mobile number doesn't exist: Create new record
   - Remaining amount is always recalculated

3. **Error Handling**:
   - Invalid data formats are logged
   - Processing continues even if some rows fail
   - Detailed error reporting in upload logs

## Project Structure

```
pledge_manager/
├── manage.py
├── requirements.txt
├── sample_pledges.csv
├── pledge_manager/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── pledges/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── forms.py
    ├── models.py
    ├── urls.py
    ├── views.py
    ├── migrations/
    └── templates/
        └── pledges/
            ├── base.html
            ├── list.html
            ├── upload.html
            ├── edit_record.html
            ├── delete.html
            └── upload_logs.html
```

## Technologies Used

- Django 5.1.5
- Python 3.14
- Bootstrap 5.1.3
- Font Awesome 6.0.0
- Pandas (for file processing)
- OpenPyXL (for Excel file support)

## Key Features Details

### Mobile Number as Primary Key
- Ensures uniqueness and prevents true duplicates
- Updates existing records when same mobile number is uploaded
- Enables efficient lookups and updates

### Message Status Tracking
- `normal_message_sent`: Track if normal SMS/message was sent
- `whatsapp_sent`: Track if WhatsApp message was sent
- Both default to `false` and can be updated via admin or edit forms

### Upload Count Tracking
- Logs every upload with statistics
- Tracks total records processed, new records created, updated records
- Error logging for troubleshooting failed uploads

## Contributing

This is a Django application following standard Django project structure and best practices. Feel free to extend functionality as needed.