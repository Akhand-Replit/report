import streamlit as st
import pandas as pd
import datetime
from sqlalchemy import create_engine, text
import io
import base64
from PIL import Image
import requests
from streamlit_option_menu import option_menu
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Page config
st.set_page_config(
    page_title="Akhand Office Report",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 1rem;
    }
    
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    
    .stat-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E88E5;
    }
    
    .stat-label {
        font-size: 1rem;
        color: #777;
    }
    
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    .stButton > button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        font-weight: 600;
        height: 2.5rem;
        border-radius: 5px;
    }
    
    .stTextInput > div > div > input {
        height: 2.5rem;
    }
    
    .report-item {
        background-color: #f1f7fe;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #1E88E5;
    }
    
    .task-item {
        background-color: #f1fff1;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #4CAF50;
    }
    
    .task-item.completed {
        background-color: #f0f0f0;
        border-left: 4px solid #9e9e9e;
    }
    
    .profile-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .profile-image {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def init_connection():
    try:
        return create_engine(st.secrets["postgres"]["url"])
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# Initialize DB tables if they don't exist
def init_db():
    with engine.connect() as conn:
        conn.execute(text('''
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            profile_pic_url TEXT,
            is_active BOOLEAN DEFAULT TRUE
        );
        
        CREATE TABLE IF NOT EXISTS daily_reports (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER REFERENCES employees(id),
            report_date DATE NOT NULL,
            report_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER REFERENCES employees(id),
            task_description TEXT NOT NULL,
            due_date DATE,
            is_completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''))
        conn.commit()

# Check if admin exists
def check_admin_exists():
    with engine.connect() as conn:
        result = conn.execute(text('''
        SELECT COUNT(*) FROM employees
        WHERE username = :username AND id = 1
        '''), {'username': st.secrets.get("admin_username", "admin")})
        count = result.fetchone()[0]
    return count > 0

# Create admin user if not exists
def create_admin_user():
    with engine.connect() as conn:
        conn.execute(text('''
        INSERT INTO employees (id, username, password, full_name, profile_pic_url, is_active)
        VALUES (1, :username, :password, 'Administrator', 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y', TRUE)
        ON CONFLICT (id) DO NOTHING
        '''), {
            'username': st.secrets.get("admin_username"),
            'password': st.secrets.get("admin_password")
        })
        conn.commit()

# Authentication function
def authenticate(username, password):
    if username == st.secrets.get("admin_username") and password == st.secrets.get("admin_password"):
        return {"id": 1, "username": username, "full_name": "Administrator", "is_admin": True, "profile_pic_url": "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"}
    
    with engine.connect() as conn:
        result = conn.execute(text('''
        SELECT id, username, full_name, profile_pic_url
        FROM employees
        WHERE username = :username AND password = :password AND is_active = TRUE
        '''), {'username': username, 'password': password})
        user = result.fetchone()
    
    if user:
        return {"id": user[0], "username": user[1], "full_name": user[2], "is_admin": False, "profile_pic_url": user[3]}
    return None

# Login form
def display_login():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-header">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">Employee Management System</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login"):
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Logout function
def logout():
    st.session_state.pop("user", None)
    st.experimental_rerun()

# Admin Dashboard
def admin_dashboard():
    st.markdown('<h1 class="main-header">Admin Dashboard</h1>', unsafe_allow_html=True)
    
    # Admin profile display
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)
        try:
            st.image(st.session_state.user["profile_pic_url"], width=80, clamp=True, output_format="auto", channels="RGB", use_container_width=False)
        except:
            st.image("https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y", width=80)
        
        st.markdown(f'''
        <div>
            <h3>{st.session_state.user["full_name"]}</h3>
            <p>Administrator</p>
        </div>
        ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Employees", "Reports", "Tasks", "Logout"],
        icons=["house", "people", "clipboard-data", "list-task", "box-arrow-right"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6", "border-radius": "10px", "margin-bottom": "20px"},
            "icon": {"color": "#1E88E5", "font-size": "16px"},
            "nav-link": {"font-size": "16px", "text-align": "center", "padding": "10px", "border-radius": "5px"},
            "nav-link-selected": {"background-color": "#1E88E5", "color": "white", "font-weight": "600"},
        }
    )
    
    if selected == "Dashboard":
        display_admin_dashboard()
    elif selected == "Employees":
        manage_employees()
    elif selected == "Reports":
        view_all_reports()
    elif selected == "Tasks":
        manage_tasks()
    elif selected == "Logout":
        logout()

# Admin Dashboard Overview
def display_admin_dashboard():
    st.markdown('<h2 class="sub-header">Overview</h2>', unsafe_allow_html=True)
    
    # Statistics
    with engine.connect() as conn:
        # Total employees
        result = conn.execute(text('SELECT COUNT(*) FROM employees WHERE is_active = TRUE AND id != 1'))
        total_employees = result.fetchone()[0]
        
        # Total reports
        result = conn.execute(text('SELECT COUNT(*) FROM daily_reports'))
        total_reports = result.fetchone()[0]
        
        # Total tasks
        result = conn.execute(text('SELECT COUNT(*) FROM tasks'))
        total_tasks = result.fetchone()[0]
        
        # Completed tasks
        result = conn.execute(text('SELECT COUNT(*) FROM tasks WHERE is_completed = TRUE'))
        completed_tasks = result.fetchone()[0]
        
        # Recent reports
        result = conn.execute(text('''
        SELECT e.full_name, dr.report_date, dr.report_text 
        FROM daily_reports dr 
        JOIN employees e ON dr.employee_id = e.id 
        ORDER BY dr.created_at DESC 
        LIMIT 5
        '''))
        recent_reports = result.fetchall()
        
        # Pending tasks
        result = conn.execute(text('''
        SELECT e.full_name, t.task_description, t.due_date 
        FROM tasks t 
        JOIN employees e ON t.employee_id = e.id 
        WHERE t.is_completed = FALSE
        ORDER BY t.due_date ASC 
        LIMIT 5
        '''))
        pending_tasks = result.fetchall()
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{total_employees}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Active Employees</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{total_reports}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Total Reports</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{total_tasks}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Total Tasks</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        completion_rate = 0 if total_tasks == 0 else round((completed_tasks / total_tasks) * 100)
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{completion_rate}%</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Task Completion Rate</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent activities
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="sub-header">Recent Reports</h3>', unsafe_allow_html=True)
        if recent_reports:
            for report in recent_reports:
                st.markdown(f'''
                <div class="report-item">
                    <strong>{report[0]}</strong> - {report[1].strftime('%d %b, %Y')}
                    <p>{report[2][:100]}{'...' if len(report[2]) > 100 else ''}</p>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("No reports available")
    
    with col2:
        st.markdown('<h3 class="sub-header">Pending Tasks</h3>', unsafe_allow_html=True)
        if pending_tasks:
            for task in pending_tasks:
                due_date = task[2].strftime('%d %b, %Y') if task[2] else "No due date"
                st.markdown(f'''
                <div class="task-item">
                    <strong>{task[0]}</strong> - Due: {due_date}
                    <p>{task[1][:100]}{'...' if len(task[1]) > 100 else ''}</p>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("No pending tasks")

# Manage Employees
def manage_employees():
    st.markdown('<h2 class="sub-header">Manage Employees</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Employee List", "Add New Employee"])
    
    with tab1:
        # Fetch and display all employees
        with engine.connect() as conn:
            result = conn.execute(text('''
            SELECT id, username, full_name, profile_pic_url, is_active 
            FROM employees
            WHERE id != 1
            ORDER BY full_name
            '''))
            employees = result.fetchall()
        
        if not employees:
            st.info("No employees found. Add employees using the 'Add New Employee' tab.")
        else:
            st.write(f"Total employees: {len(employees)}")
            
            for i, employee in enumerate(employees):
                with st.expander(f"{employee[2]} ({employee[1]})", expanded=False):
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        try:
                            st.image(employee[3], width=100, use_container_width=False)
                        except:
                            st.image("https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y", width=100)
                    
                    with col2:
                        st.write(f"**Username:** {employee[1]}")
                        st.write(f"**Full Name:** {employee[2]}")
                        st.write(f"**Status:** {'Active' if employee[4] else 'Inactive'}")
                        
                        # Action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if employee[4]:  # If active
                                if st.button(f"Deactivate", key=f"deactivate_{employee[0]}"):
                                    with engine.connect() as conn:
                                        conn.execute(text('UPDATE employees SET is_active = FALSE WHERE id = :id'), {'id': employee[0]})
                                        conn.commit()
                                    st.success(f"Deactivated employee: {employee[2]}")
                                    st.experimental_rerun()
                            else:  # If inactive
                                if st.button(f"Activate", key=f"activate_{employee[0]}"):
                                    with engine.connect() as conn:
                                        conn.execute(text('UPDATE employees SET is_active = TRUE WHERE id = :id'), {'id': employee[0]})
                                        conn.commit()
                                    st.success(f"Activated employee: {employee[2]}")
                                    st.experimental_rerun()
                        
                        with col2:
                            if st.button(f"Reset Password", key=f"reset_{employee[0]}"):
                                new_password = "password123"  # Default reset password
                                with engine.connect() as conn:
                                    conn.execute(text('UPDATE employees SET password = :password WHERE id = :id'), 
                                                {'id': employee[0], 'password': new_password})
                                    conn.commit()
                                st.success(f"Password reset to '{new_password}' for {employee[2]}")
    
    with tab2:
        # Form to add new employee
        with st.form("add_employee_form"):
            username = st.text_input("Username", help="Username for employee login")
            password = st.text_input("Password", type="password", help="Initial password")
            full_name = st.text_input("Full Name")
            profile_pic_url = st.text_input("Profile Picture URL", help="Link to employee profile picture")
            
            submitted = st.form_submit_button("Add Employee")
            if submitted:
                if not username or not password or not full_name:
                    st.error("Please fill all required fields")
                else:
                    # Check if username already exists
                    with engine.connect() as conn:
                        result = conn.execute(text('SELECT COUNT(*) FROM employees WHERE username = :username'), 
                                             {'username': username})
                        count = result.fetchone()[0]
                        
                        if count > 0:
                            st.error(f"Username '{username}' already exists")
                        else:
                            # Insert new employee
                            try:
                                conn.execute(text('''
                                INSERT INTO employees (username, password, full_name, profile_pic_url, is_active)
                                VALUES (:username, :password, :full_name, :profile_pic_url, TRUE)
                                '''), {
                                    'username': username,
                                    'password': password,
                                    'full_name': full_name,
                                    'profile_pic_url': profile_pic_url if profile_pic_url else "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"
                                })
                                conn.commit()
                                st.success(f"Successfully added employee: {full_name}")
                            except Exception as e:
                                st.error(f"Error adding employee: {e}")

# View All Reports
def view_all_reports():
    st.markdown('<h2 class="sub-header">Employee Reports</h2>', unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Employee filter
        with engine.connect() as conn:
            result = conn.execute(text('''
            SELECT id, full_name FROM employees 
            WHERE is_active = TRUE AND id != 1
            ORDER BY full_name
            '''))
            employees = result.fetchall()
        
        employee_options = ["All Employees"] + [emp[1] for emp in employees]
        employee_filter = st.selectbox("Select Employee", employee_options)
    
    with col2:
        # Date range filter
        today = datetime.date.today()
        date_options = [
            "All Time",
            "Today",
            "This Week",
            "This Month",
            "This Year",
            "Custom Range"
        ]
        date_filter = st.selectbox("Date Range", date_options)
    
    with col3:
        # Custom date range if selected
        if date_filter == "Custom Range":
            start_date = st.date_input("Start Date", today - datetime.timedelta(days=30))
            end_date = st.date_input("End Date", today)
        else:
            # Set default dates based on filter
            if date_filter == "Today":
                start_date = today
                end_date = today
            elif date_filter == "This Week":
                start_date = today - datetime.timedelta(days=today.weekday())
                end_date = today
            elif date_filter == "This Month":
                start_date = today.replace(day=1)
                end_date = today
            elif date_filter == "This Year":
                start_date = today.replace(month=1, day=1)
                end_date = today
            else:  # All Time
                start_date = datetime.date(2000, 1, 1)
                end_date = today
    
    # Build query based on filters
    query = '''
    SELECT e.full_name, dr.report_date, dr.report_text, dr.id, e.id as employee_id
    FROM daily_reports dr
    JOIN employees e ON dr.employee_id = e.id
    WHERE dr.report_date BETWEEN :start_date AND :end_date
    '''
    
    params = {'start_date': start_date, 'end_date': end_date}
    
    if employee_filter != "All Employees":
        query += ' AND e.full_name = :employee_name'
        params['employee_name'] = employee_filter
    
    query += ' ORDER BY dr.report_date DESC, e.full_name'
    
    # Execute query
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        reports = result.fetchall()
    
    # Display reports
    if not reports:
        st.info("No reports found for the selected criteria")
    else:
        st.write(f"Found {len(reports)} reports")
        
        # Group by employee for export
        employee_reports = {}
        for report in reports:
            if report[0] not in employee_reports:
                employee_reports[report[0]] = []
            employee_reports[report[0]].append(report)
        
        # Export options
        col1, col2 = st.columns([3, 1])
        with col2:
            if employee_filter != "All Employees" and len(employee_reports) == 1:
                if st.button("Export as PDF"):
                    pdf = create_report_pdf(reports)
                    st.download_button(
                        label="Download PDF",
                        data=pdf,
                        file_name=f"{employee_filter}_reports_{start_date}_to_{end_date}.pdf",
                        mime="application/pdf"
                    )
        
        # Display reports
        for employee_name, emp_reports in employee_reports.items():
            with st.expander(f"Reports by {employee_name} ({len(emp_reports)})", expanded=True):
                # Group by month/year for better organization
                reports_by_period = {}
                for report in emp_reports:
                    period = report[1].strftime('%B %Y')
                    if period not in reports_by_period:
                        reports_by_period[period] = []
                    reports_by_period[period].append(report)
                
                for period, period_reports in reports_by_period.items():
                    st.markdown(f"##### {period}")
                    for report in period_reports:
                        st.markdown(f'''
                        <div class="report-item">
                            <span style="color: #777;">{report[1].strftime('%A, %d %b %Y')}</span>
                            <p>{report[2]}</p>
                        </div>
                        ''', unsafe_allow_html=True)

# Create PDF for reports
def create_report_pdf(reports):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=12
    )
    elements.append(Paragraph(f"Work Reports: {reports[0][0]}", title_style))
    elements.append(Spacer(1, 12))
    
    # Date range
    date_style = ParagraphStyle(
        'DateRange',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        textColor=colors.gray
    )
    min_date = min(report[1] for report in reports).strftime('%d %b %Y')
    max_date = max(report[1] for report in reports).strftime('%d %b %Y')
    elements.append(Paragraph(f"Period: {min_date} to {max_date}", date_style))
    elements.append(Spacer(1, 20))
    
    # Group reports by month
    reports_by_month = {}
    for report in reports:
        month_year = report[1].strftime('%B %Y')
        if month_year not in reports_by_month:
            reports_by_month[month_year] = []
        reports_by_month[month_year].append(report)
    
    # Add each month's reports
    for month, month_reports in reports_by_month.items():
        # Month header
        month_style = ParagraphStyle(
            'Month',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10
        )
        elements.append(Paragraph(month, month_style))
        
        # Reports for the month
        for report in month_reports:
            # Date
            date_style = ParagraphStyle(
                'Date',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.blue
            )
            elements.append(Paragraph(report[1].strftime('%A, %d %b %Y'), date_style))
            
            # Report text
            text_style = ParagraphStyle(
                'ReportText',
                parent=styles['Normal'],
                fontSize=10,
                leftIndent=10
            )
            elements.append(Paragraph(report[2], text_style))
            elements.append(Spacer(1, 12))
        
        elements.append(Spacer(1, 10))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# Manage Tasks
def manage_tasks():
    st.markdown('<h2 class="sub-header">Manage Tasks</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["View Tasks", "Assign New Task"])
    
    with tab1:
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            # Employee filter
            with engine.connect() as conn:
                result = conn.execute(text('''
                SELECT id, full_name FROM employees 
                WHERE is_active = TRUE AND id != 1
                ORDER BY full_name
                '''))
                employees = result.fetchall()
            
            employee_options = ["All Employees"] + [emp[1] for emp in employees]
            employee_filter = st.selectbox("Select Employee", employee_options, key="task_employee_filter")
        
        with col2:
            # Status filter
            status_options = ["All Tasks", "Pending", "Completed"]
            status_filter = st.selectbox("Task Status", status_options)
        
        # Build query based on filters
        query = '''
        SELECT t.id, e.full_name, t.task_description, t.due_date, t.is_completed, t.created_at, e.id as employee_id
        FROM tasks t
        JOIN employees e ON t.employee_id = e.id
        WHERE 1=1
        '''
        
        params = {}
        
        if employee_filter != "All Employees":
            query += ' AND e.full_name = :employee_name'
            params['employee_name'] = employee_filter
        
        if status_filter == "Pending":
            query += ' AND t.is_completed = FALSE'
        elif status_filter == "Completed":
            query += ' AND t.is_completed = TRUE'
        
        query += ' ORDER BY t.due_date ASC NULLS LAST, t.created_at DESC'
        
        # Execute query
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            tasks = result.fetchall()
        
        # Display tasks
        if not tasks:
            st.info("No tasks found for the selected criteria")
        else:
            st.write(f"Found {len(tasks)} tasks")
            
            for task in tasks:
                task_id = task[0]
                employee_name = task[1]
                task_description = task[2]
                due_date = task[3].strftime('%d %b, %Y') if task[3] else "No due date"
                is_completed = task[4]
                created_at = task[5].strftime('%d %b, %Y')
                
                # Display the task with status-based styling
                status_class = "completed" if is_completed else ""
                st.markdown(f'''
                <div class="task-item {status_class}">
                    <strong>{employee_name}</strong> - Due: {due_date}
                    <p>{task_description}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #777; font-size: 0.8rem;">Created: {created_at}</span>
                        <span style="font-weight: 600; color: {'#9e9e9e' if is_completed else '#4CAF50'};">
                            {"Completed" if is_completed else "Pending"}
                        </span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if not is_completed:
                        if st.button(f"Mark as Completed", key=f"complete_{task_id}"):
                            with engine.connect() as conn:
                                conn.execute(text('UPDATE tasks SET is_completed = TRUE WHERE id = :id'), {'id': task_id})
                                conn.commit()
                            st.success("Task marked as completed")
                            st.experimental_rerun()
                    else:
                        if st.button(f"Reopen Task", key=f"reopen_{task_id}"):
                            with engine.connect() as conn:
                                conn.execute(text('UPDATE tasks SET is_completed = FALSE WHERE id = :id'), {'id': task_id})
                                conn.commit()
                            st.success("Task reopened")
                            st.experimental_rerun()
                
                with col2:
                    if st.button(f"Delete Task", key=f"delete_{task_id}"):
                        with engine.connect() as conn:
                            conn.execute(text('DELETE FROM tasks WHERE id = :id'), {'id': task_id})
                            conn.commit()
                        st.success("Task deleted")
                        st.experimental_rerun()
    
    with tab2:
        # Form to assign new task
        with st.form("assign_task_form"):
            # Employee selection
            employee_map = {emp[1]: emp[0] for emp in employees}
            employee = st.selectbox("Assign to Employee", [emp[1] for emp in employees])
            
            # Task details
            task_description = st.text_area("Task Description")
            due_date = st.date_input("Due Date", datetime.date.today() + datetime.timedelta(days=7))
            
            submitted = st.form_submit_button("Assign Task")
            if submitted:
                if not task_description:
                    st.error("Please enter a task description")
                else:
                    # Insert new task
                    try:
                        with engine.connect() as conn:
                            conn.execute(text('''
                            INSERT INTO tasks (employee_id, task_description, due_date, is_completed)
                            VALUES (:employee_id, :task_description, :due_date, FALSE)
                            '''), {
                                'employee_id': employee_map[employee],
                                'task_description': task_description,
                                'due_date': due_date
                            })
                            conn.commit()
                        st.success(f"Successfully assigned task to {employee}")
                    except Exception as e:
                        st.error(f"Error assigning task: {e}")

# Employee Dashboard
def employee_dashboard():
    st.markdown('<h1 class="main-header">Employee Dashboard</h1>', unsafe_allow_html=True)
    
    # Employee profile display
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div class="profile-container">', unsafe_allow_html=True)
        try:
            st.image(st.session_state.user["profile_pic_url"], width=80, clamp=True, output_format="auto", channels="RGB")
        except:
            st.image("https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y", width=80)
        
        st.markdown(f'''
        <div>
            <h3>{st.session_state.user["full_name"]}</h3>
            <p>Employee</p>
        </div>
        ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Submit Report", "My Reports", "My Tasks", "Logout"],
        icons=["house", "pencil", "journal-text", "list-check", "box-arrow-right"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6", "border-radius": "10px", "margin-bottom": "20px"},
            "icon": {"color": "#1E88E5", "font-size": "16px"},
            "nav-link": {"font-size": "16px", "text-align": "center", "padding": "10px", "border-radius": "5px"},
            "nav-link-selected": {"background-color": "#1E88E5", "color": "white", "font-weight": "600"},
        }
    )
    
    if selected == "Dashboard":
        display_employee_dashboard()
    elif selected == "Submit Report":
        submit_report()
    elif selected == "My Reports":
        view_my_reports()
    elif selected == "My Tasks":
        view_my_tasks()
    elif selected == "Logout":
        logout()

# Employee Dashboard Overview
def display_employee_dashboard():
    st.markdown('<h2 class="sub-header">My Overview</h2>', unsafe_allow_html=True)
    
    employee_id = st.session_state.user["id"]
    
    # Statistics
    with engine.connect() as conn:
        # Total reports
        result = conn.execute(text('SELECT COUNT(*) FROM daily_reports WHERE employee_id = :employee_id'), 
                             {'employee_id': employee_id})
        total_reports = result.fetchone()[0]
        
        # Reports this month
        today = datetime.date.today()
        first_day_of_month = today.replace(day=1)
        result = conn.execute(text('''
        SELECT COUNT(*) FROM daily_reports 
        WHERE employee_id = :employee_id AND report_date >= :first_day
        '''), {'employee_id': employee_id, 'first_day': first_day_of_month})
        reports_this_month = result.fetchone()[0]
        
        # Total tasks
        result = conn.execute(text('SELECT COUNT(*) FROM tasks WHERE employee_id = :employee_id'), 
                             {'employee_id': employee_id})
        total_tasks = result.fetchone()[0]
        
        # Pending tasks
        result = conn.execute(text('''
        SELECT COUNT(*) FROM tasks 
        WHERE employee_id = :employee_id AND is_completed = FALSE
        '''), {'employee_id': employee_id})
        pending_tasks = result.fetchone()[0]
        
        # Recent reports
        result = conn.execute(text('''
        SELECT report_date, report_text FROM daily_reports 
        WHERE employee_id = :employee_id 
        ORDER BY report_date DESC LIMIT 3
        '''), {'employee_id': employee_id})
        recent_reports = result.fetchall()
        
        # Pending tasks details
        result = conn.execute(text('''
        SELECT id, task_description, due_date FROM tasks 
        WHERE employee_id = :employee_id AND is_completed = FALSE 
        ORDER BY due_date ASC NULLS LAST LIMIT 5
        '''), {'employee_id': employee_id})
        pending_task_details = result.fetchall()
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{total_reports}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Total Reports</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{reports_this_month}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Reports This Month</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{total_tasks}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Total Tasks</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="stat-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="stat-value">{pending_tasks}</div>', unsafe_allow_html=True)
        st.markdown('<div class="stat-label">Pending Tasks</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent activity and pending tasks
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="sub-header">My Recent Reports</h3>', unsafe_allow_html=True)
        if recent_reports:
            for report in recent_reports:
                st.markdown(f'''
                <div class="report-item">
                    <strong>{report[0].strftime('%d %b, %Y')}</strong>
                    <p>{report[1][:100]}{'...' if len(report[1]) > 100 else ''}</p>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("No reports submitted yet")
        
        if st.button("Submit New Report", key="quick_submit"):
            st.session_state["selected_tab"] = "Submit Report"
            st.experimental_rerun()
    
    with col2:
        st.markdown('<h3 class="sub-header">My Pending Tasks</h3>', unsafe_allow_html=True)
        if pending_task_details:
            for task in pending_task_details:
                due_date = task[2].strftime('%d %b, %Y') if task[2] else "No due date"
                st.markdown(f'''
                <div class="task-item">
                    <strong>Due: {due_date}</strong>
                    <p>{task[1][:100]}{'...' if len(task[1]) > 100 else ''}</p>
                </div>
                ''', unsafe_allow_html=True)
                
                if st.button(f"Mark as Completed", key=f"quick_complete_{task[0]}"):
                    with engine.connect() as conn:
                        conn.execute(text('UPDATE tasks SET is_completed = TRUE WHERE id = :id'), {'id': task[0]})
                        conn.commit()
                    st.success("Task marked as completed")
                    st.experimental_rerun()
        else:
            st.info("No pending tasks")

# Submit Report
def submit_report():
    st.markdown('<h2 class="sub-header">Submit Daily Report</h2>', unsafe_allow_html=True)
    
    employee_id = st.session_state.user["id"]
    
    with st.form("submit_report_form"):
        report_date = st.date_input("Report Date", datetime.date.today())
        
        # Check if a report already exists for this date
        with engine.connect() as conn:
            result = conn.execute(text('''
            SELECT id FROM daily_reports 
            WHERE employee_id = :employee_id AND report_date = :report_date
            '''), {'employee_id': employee_id, 'report_date': report_date})
            existing_report = result.fetchone()
        
        if existing_report:
            st.warning(f"You already have a report for {report_date.strftime('%d %b, %Y')}. Submitting will update your existing report.")
        
        report_text = st.text_area("What did you work on today?", height=200)
        
        submitted = st.form_submit_button("Submit Report")
        if submitted:
            if not report_text:
                st.error("Please enter your report")
            else:
                try:
                    with engine.connect() as conn:
                        if existing_report:
                            # Update existing report
                            conn.execute(text('''
                            UPDATE daily_reports 
                            SET report_text = :report_text, created_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                            '''), {'report_text': report_text, 'id': existing_report[0]})
                            success_message = "Report updated successfully"
                        else:
                            # Insert new report
                            conn.execute(text('''
                            INSERT INTO daily_reports (employee_id, report_date, report_text)
                            VALUES (:employee_id, :report_date, :report_text)
                            '''), {
                                'employee_id': employee_id,
                                'report_date': report_date,
                                'report_text': report_text
                            })
                            success_message = "Report submitted successfully"
                        
                        conn.commit()
                    st.success(success_message)
                except Exception as e:
                    st.error(f"Error submitting report: {e}")

# View My Reports
def view_my_reports():
    st.markdown('<h2 class="sub-header">My Reports</h2>', unsafe_allow_html=True)
    
    employee_id = st.session_state.user["id"]
    
    # Date range filter
    col1, col2 = st.columns(2)
    
    with col1:
        today = datetime.date.today()
        date_options = [
            "All Reports",
            "This Week",
            "This Month",
            "This Year",
            "Custom Range"
        ]
        date_filter = st.selectbox("Date Range", date_options)
    
    with col2:
        # Custom date range if selected
        if date_filter == "Custom Range":
            start_date = st.date_input("Start Date", today - datetime.timedelta(days=30))
            end_date = st.date_input("End Date", today)
        else:
            # Set default dates based on filter
            if date_filter == "This Week":
                start_date = today - datetime.timedelta(days=today.weekday())
                end_date = today
            elif date_filter == "This Month":
                start_date = today.replace(day=1)
                end_date = today
            elif date_filter == "This Year":
                start_date = today.replace(month=1, day=1)
                end_date = today
            else:  # All Reports
                start_date = datetime.date(2000, 1, 1)
                end_date = today
    
    # Fetch reports
    with engine.connect() as conn:
        result = conn.execute(text('''
        SELECT id, report_date, report_text
        FROM daily_reports
        WHERE employee_id = :employee_id
        AND report_date BETWEEN :start_date AND :end_date
        ORDER BY report_date DESC
        '''), {'employee_id': employee_id, 'start_date': start_date, 'end_date': end_date})
        reports = result.fetchall()
    
    # Display reports
    if not reports:
        st.info("No reports found for the selected period")
    else:
        st.write(f"Found {len(reports)} reports")
        
        # Group by month/year for better organization
        reports_by_period = {}
        for report in reports:
            period = report[1].strftime('%B %Y')
            if period not in reports_by_period:
                reports_by_period[period] = []
            reports_by_period[period].append(report)
        
        for period, period_reports in reports_by_period.items():
            with st.expander(f"{period} ({len(period_reports)} reports)", expanded=True):
                for report in period_reports:
                    report_id = report[0]
                    report_date = report[1]
                    report_text = report[2]
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f'''
                        <div class="report-item">
                            <strong>{report_date.strftime('%A, %d %b %Y')}</strong>
                            <p>{report_text}</p>
                        </div>
                        ''', unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("Edit", key=f"edit_{report_id}"):
                            st.session_state.edit_report = {
                                'id': report_id,
                                'date': report_date,
                                'text': report_text
                            }
                            st.experimental_rerun()
        
    # Edit report if selected
    if hasattr(st.session_state, 'edit_report'):
        st.markdown('<h3 class="sub-header">Edit Report</h3>', unsafe_allow_html=True)
        
        with st.form("edit_report_form"):
            report_date = st.date_input("Report Date", st.session_state.edit_report['date'])
            report_text = st.text_area("Report Text", st.session_state.edit_report['text'], height=200)
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Update Report")
            with col2:
                cancel = st.form_submit_button("Cancel")
            
            if submitted:
                if not report_text:
                    st.error("Please enter your report")
                else:
                    try:
                        with engine.connect() as conn:
                            conn.execute(text('''
                            UPDATE daily_reports 
                            SET report_text = :report_text, report_date = :report_date, created_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                            '''), {
                                'report_text': report_text, 
                                'report_date': report_date, 
                                'id': st.session_state.edit_report['id']
                            })
                            conn.commit()
                        st.success("Report updated successfully")
                        del st.session_state.edit_report
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error updating report: {e}")
            
            if cancel:
                del st.session_state.edit_report
                st.experimental_rerun()

# View My Tasks
def view_my_tasks():
    st.markdown('<h2 class="sub-header">My Tasks</h2>', unsafe_allow_html=True)
    
    employee_id = st.session_state.user["id"]
    
    # Task status filter
    status_options = ["All Tasks", "Pending", "Completed"]
    status_filter = st.selectbox("Show", status_options)
    
    # Build query based on filter
    query = '''
    SELECT id, task_description, due_date, is_completed, created_at
    FROM tasks
    WHERE employee_id = :employee_id
    '''
    
    params = {'employee_id': employee_id}
    
    if status_filter == "Pending":
        query += ' AND is_completed = FALSE'
    elif status_filter == "Completed":
        query += ' AND is_completed = TRUE'
    
    query += ' ORDER BY due_date ASC NULLS LAST, created_at DESC'
    
    # Fetch tasks
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        tasks = result.fetchall()
    
    # Display tasks
    if not tasks:
        st.info("No tasks found")
    else:
        st.write(f"Found {len(tasks)} tasks")
        
        # Separate into pending and completed for better organization
        pending_tasks = [task for task in tasks if not task[3]]
        completed_tasks = [task for task in tasks if task[3]]
        
        # Display pending tasks first
        if pending_tasks and status_filter != "Completed":
            st.markdown('<h3 class="sub-header">Pending Tasks</h3>', unsafe_allow_html=True)
            
            for task in pending_tasks:
                task_id = task[0]
                task_description = task[1]
                due_date = task[2].strftime('%d %b, %Y') if task[2] else "No due date"
                created_at = task[4].strftime('%d %b, %Y')
                
                st.markdown(f'''
                <div class="task-item">
                    <strong>Due: {due_date}</strong>
                    <p>{task_description}</p>
                    <div style="text-align: right; color: #777; font-size: 0.8rem;">
                        Created: {created_at}
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                if st.button(f"Mark as Completed", key=f"complete_{task_id}"):
                    with engine.connect() as conn:
                        conn.execute(text('UPDATE tasks SET is_completed = TRUE WHERE id = :id'), {'id': task_id})
                        conn.commit()
                    st.success("Task marked as completed")
                    st.experimental_rerun()
        
        # Display completed tasks
        if completed_tasks and status_filter != "Pending":
            st.markdown('<h3 class="sub-header">Completed Tasks</h3>', unsafe_allow_html=True)
            
            for task in completed_tasks:
                task_id = task[0]
                task_description = task[1]
                due_date = task[2].strftime('%d %b, %Y') if task[2] else "No due date"
                created_at = task[4].strftime('%d %b, %Y')
                
                st.markdown(f'''
                <div class="task-item completed">
                    <strong>Due: {due_date}</strong>
                    <p>{task_description}</p>
                    <div style="text-align: right; color: #777; font-size: 0.8rem;">
                        Created: {created_at}
                    </div>
                </div>
                ''', unsafe_allow_html=True)

# Main function
def main():
    global engine
    engine = init_connection()
    
    if engine:
        # Initialize database tables
        init_db()
        
        # Ensure admin user exists
        if not check_admin_exists():
            create_admin_user()
        
        # Check if user is logged in
        if "user" not in st.session_state:
            display_login()
        else:
            # Show appropriate dashboard based on user type
            if st.session_state.user.get("is_admin", False):
                admin_dashboard()
            else:
                employee_dashboard()
    else:
        st.error("Failed to connect to the database. Please check your database configuration.")

if __name__ == "__main__":
    main()
