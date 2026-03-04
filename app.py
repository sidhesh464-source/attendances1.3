from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, SchoolClass, Enrollment, Attendance, Message
from config import SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'role_selection'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Public Routes ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_home'))
        elif current_user.role == 'faculty':
            return redirect(url_for('faculty_home'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'principal':
            return redirect(url_for('principal_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def role_selection():
    return render_template('index.html')

# --- Authentication Routes ---
@app.route('/login/student', methods=['GET', 'POST'])
def login_student():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, role='student').first()
        if user and check_password_hash(user.password, password):
            if user.is_blocked:
                flash('Your account is blocked. Please contact admin.', 'error')
                return redirect(url_for('login_student'))
            login_user(user)
            return redirect(url_for('student_home'))

        flash('Invalid Credentials', 'error')
    return render_template('login_student.html')

@app.route('/login/faculty', methods=['GET', 'POST'])
def login_faculty():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, role='faculty').first()
        if user and check_password_hash(user.password, password):
            if user.is_blocked:
                flash('Your account is blocked. Please contact admin.', 'error')
                return redirect(url_for('login_faculty'))
            login_user(user)
            return redirect(url_for('faculty_home'))

        flash('Invalid Credentials', 'error')
    return render_template('login_faculty.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        username = request.form.get('username') # Register No
        password = request.form.get('password')
        name = request.form.get('name')
        
        if User.query.filter_by(username=username).first():
            flash('User already exists', 'error')
            return redirect(url_for('register_student'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, role='student', name=name)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login_student'))
    return render_template('register_student.html')

@app.route('/register/faculty', methods=['GET', 'POST'])
def register_faculty():
    if request.method == 'POST':
        username = request.form.get('username') # Faculty ID
        password = request.form.get('password')
        name = request.form.get('name')
        department = request.form.get('department')
        
        if User.query.filter_by(username=username).first():
            flash('User already exists', 'error')
            return redirect(url_for('register_faculty'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, role='faculty', name=name, department=department)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login_faculty'))
    return render_template('register_faculty.html')

# --- Student Routes ---
@app.route('/student/home')
@login_required
def student_home():
    if current_user.role != 'student': return redirect(url_for('home'))
    return render_template('student_home.html')

@app.route('/student/enroll', methods=['GET', 'POST'])
@login_required
def enroll_class():
    if current_user.role != 'student': return redirect(url_for('home'))
    school_classes = SchoolClass.query.all()
    if request.method == 'POST':
        class_id = request.form.get('class')
        if not Enrollment.query.filter_by(student_id=current_user.id, class_id=class_id).first():
            enrollment = Enrollment(student_id=current_user.id, class_id=class_id)
            db.session.add(enrollment)
            db.session.commit()
            flash('Enrolled successfully!', 'success')
        else:
            flash('Already enrolled in this class.', 'warning')
        return redirect(url_for('enroll_class'))
    return render_template('student_enrollment.html', school_classes=school_classes)

# Placeholders for future routes to avoid errors in templates
@app.route('/student/attendance')
@login_required
def student_attendance():
    if current_user.role != 'student': return redirect(url_for('home'))
    
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    attendance_summary = []
    
    for enrollment in enrollments:
        school_class = enrollment.school_class
        # Get all attendance records for this student in this class
        records = Attendance.query.filter_by(student_id=current_user.id, class_id=school_class.id).all()
        
        total_classes = len(records)
        attended_classes = len([r for r in records if r.status == 'Present'])
        percentage = (attended_classes / total_classes * 100) if total_classes > 0 else 0
        
        status_color = 'green'
        if percentage < 90: status_color = 'yellow'
        if percentage < 80: status_color = 'red'
        
        attendance_summary.append({
            'class_id': school_class.id,
            'class_name': school_class.name,
            'total_classes': total_classes,
            'attended': attended_classes,
            'percentage': round(percentage, 2),
            'status_color': status_color
        })
        
    return render_template('student_attendance.html', summary=attendance_summary)

@app.route('/student/attendance/details/<int:class_id>')
@login_required
def student_attendance_details(class_id):
    if current_user.role != 'student': return redirect(url_for('home'))
    
    school_class = SchoolClass.query.get(class_id)
    records = Attendance.query.filter_by(student_id=current_user.id, class_id=class_id).order_by(Attendance.date.desc()).all()
    
    return render_template('student_attendance_details.html', school_class=school_class, records=records)

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import send_file

@app.route('/faculty/home')
@login_required
def faculty_home():
    if current_user.role != 'faculty': return redirect(url_for('home'))
    school_classes = SchoolClass.query.all()
    return render_template('faculty_home.html', school_classes=school_classes)

@app.route('/faculty/analytics/<int:class_id>')
@login_required
def faculty_analytics(class_id):
    if current_user.role != 'faculty': return redirect(url_for('home'))
    school_class = SchoolClass.query.get(class_id)
    # Get attendance data for graph (e.g., date-wise presence)
    records = Attendance.query.filter_by(class_id=class_id).all()
    
    dates = []
    present_counts = []
    absent_counts = []
    
    # Process data for chart
    date_map = {}
    for r in records:
        d_str = r.date.strftime('%Y-%m-%d')
        if d_str not in date_map: date_map[d_str] = {'Present': 0, 'Absent': 0}
        date_map[d_str][r.status] += 1
        
    sorted_dates = sorted(date_map.keys())
    for d in sorted_dates:
        dates.append(d)
        present_counts.append(date_map[d]['Present'])
        absent_counts.append(date_map[d]['Absent'])
    
    return render_template('faculty_analytics.html', school_class=school_class, dates=dates, present_counts=present_counts, absent_counts=absent_counts)

@app.route('/faculty/export_pdf/<int:class_id>')
@login_required
def export_pdf(class_id):
    if current_user.role != 'faculty': return redirect(url_for('home'))
    school_class = SchoolClass.query.get(class_id)
    records = Attendance.query.filter_by(class_id=class_id).order_by(Attendance.date).all()
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Attendance Report for {school_class.name}")
    
    y = 730
    p.drawString(100, y, "Date | Student | Status")
    y -= 20
    
    for r in records:
        student_name = r.student.name if r.student else "Unknown"
        p.drawString(100, y, f"{r.date} | {student_name} | {r.status}")
        y -= 15
        if y < 50:
            p.showPage()
            y = 750
            
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'attendance_{school_class.name}.pdf', mimetype='application/pdf')

@app.route('/faculty/take_attendance', methods=['GET', 'POST'])
@login_required
def take_attendance():
    if current_user.role != 'faculty': return redirect(url_for('home'))
    school_classes = SchoolClass.query.all()
    students = []
    selected_class_id = request.args.get('class_id')
    
    if selected_class_id:
        # Get students enrolled in this class
        enrollments = Enrollment.query.filter_by(class_id=selected_class_id).all()
        for enrollment in enrollments:
            students.append(enrollment.student)
            
    return render_template('faculty_take_attendance.html', school_classes=school_classes, students=students, selected_class_id=selected_class_id)

@app.route('/faculty/attendance/confirm', methods=['POST'])
@login_required
def confirm_attendance():
    if current_user.role != 'faculty': return redirect(url_for('home'))
    
    class_id = request.form.get('class_id')
    school_class = SchoolClass.query.get(class_id)
    
    # Process form data to get student statuses
    students_data = []
    # We need to re-fetch enrolled students to iterate through form keys essentially, 
    # or better, iterate through the form keys that start with "status_"
    
    for key, value in request.form.items():
        if key.startswith('status_'):
            student_id = int(key.split('_')[1])
            student = User.query.get(student_id)
            students_data.append({
                'student': student,
                'status': value
            })
            
    return render_template('faculty_attendance_confirm.html', students=students_data, school_class=school_class)

@app.route('/faculty/attendance/submit', methods=['POST'])
@login_required
def submit_attendance():
    if current_user.role != 'faculty': return redirect(url_for('home'))
    
    class_id = request.form.get('class_id')
    
    for key, value in request.form.items():
        if key.startswith('status_'):
            student_id = int(key.split('_')[1])
            
            # Record attendance
            attendance = Attendance(
                student_id=student_id,
                class_id=class_id,
                faculty_id=current_user.id,
                status=value,
                date=datetime.now().date()
            )
            db.session.add(attendance)
            
    db.session.commit()
    flash('Attendance submitted successfully!', 'success')
    return redirect(url_for('faculty_home'))

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        user = current_user
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.age = request.form.get('age')
        user.dob = request.form.get('dob')
        user.gender = request.form.get('gender')
        
        # Handle photo upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename != '':
                # Secure the filename and save
                filename = secure_filename(photo.filename)
                # Add user id to filename to make it unique
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                unique_filename = f'user_{user.id}.{ext}'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                photo.save(filepath)
                user.photo = f'uploads/{unique_filename}'  # Use forward slash for web URLs
        
        if user.role == 'student':
            user.father_name = request.form.get('father_name')
            user.mother_name = request.form.get('mother_name')
        elif user.role == 'faculty':
            user.department = request.form.get('department')
            user.date_of_join = request.form.get('date_of_join')
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        
        if user.role == 'student': return redirect(url_for('student_profile'))
        elif user.role == 'faculty': return redirect(url_for('faculty_profile'))
        elif user.role == 'principal': return redirect(url_for('principal_profile'))
        else: return redirect(url_for('home'))
        
    return render_template('edit_profile.html')

@app.route('/profile/remove_photo')
@login_required
def remove_photo():
    user = current_user
    if user.photo:
        # Optional: delete file from disk
        # full_path = os.path.join(app.root_path, user.photo)
        # if os.path.exists(full_path): os.remove(full_path)
        user.photo = None
        db.session.commit()
    flash('Photo removed!', 'success')
    return redirect(url_for('edit_profile'))


@app.route('/student/profile')
@login_required
def student_profile():
    if current_user.role != 'student': return redirect(url_for('home'))
    return render_template('student_profile.html')

@app.route('/faculty/profile')
@login_required
def faculty_profile():
    if current_user.role != 'faculty': return redirect(url_for('home'))
    return render_template('faculty_profile.html')

# --- Admin Routes ---
@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, role='admin').first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid Credentials', 'error')
    return render_template('login_admin.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    school_classes = SchoolClass.query.all()
    class_stats = []
    for school_class in school_classes:
        student_count = len(school_class.enrollments)
        class_stats.append({'id': school_class.id, 'name': school_class.name, 'student_count': student_count})
        
    users = User.query.all()
    return render_template('admin_dashboard.html', class_stats=class_stats, users=users)

@app.route('/admin/add_user/<role_type>', methods=['GET', 'POST'])
@login_required
def add_user(role_type):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username') # Reg No
        name = request.form.get('name')
        
        # Default password is 'welcome'
        hashed_pw = generate_password_hash('welcome')
        
        if User.query.filter_by(username=username).first():
            flash(f'User with Reg No {username} already exists.', 'error')
            return redirect(url_for('add_user', role_type=role_type))
            
        new_user = User(username=username, password=hashed_pw, role=role_type, name=name)
        
        # Add role specific fields if any (currently just generic User fields are enough for creation)
        if role_type == 'faculty':
            new_user.department = request.form.get('department')
            
        db.session.add(new_user)
        db.session.commit()
        flash(f'{role_type.capitalize()} added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin_add_user.html', role_type=role_type)

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot delete admin user.', 'error')
    else:
        # Delete associated records first to avoid constraint errors
        Enrollment.query.filter_by(student_id=user.id).delete()
        Attendance.query.filter_by(student_id=user.id).delete()
        Attendance.query.filter_by(faculty_id=user.id).delete()
        Message.query.filter_by(sender_id=user.id).delete()
        
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_block/<int:user_id>')
@login_required
def toggle_block(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot block admin user.', 'error')
    else:
        user.is_blocked = not user.is_blocked
        db.session.commit()
        status = 'blocked' if user.is_blocked else 'unblocked'
        flash(f'User {user.name} has been {status}.', 'success')
        
    return redirect(url_for('admin_dashboard'))

# --- Principal Routes ---

@app.route('/login/principal', methods=['GET', 'POST'])
def login_principal():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, role='principal').first()
        if user and check_password_hash(user.password, password):
            if user.is_blocked:
                flash('Your account is blocked. Please contact admin.', 'error')
                return redirect(url_for('login_principal'))
            login_user(user)
            return redirect(url_for('principal_dashboard'))

        flash('Invalid Credentials', 'error')
    return render_template('login_principal.html')

@app.route('/principal/dashboard')
@login_required
def principal_dashboard():
    if current_user.role != 'principal':
        return redirect(url_for('home'))
    
    # Notifications/Messages sent by principal
    sent_messages = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
        
    return render_template('principal_dashboard.html', sent_messages=sent_messages)

@app.route('/principal/search_students')
@login_required
def principal_search_students():
    if current_user.role != 'principal':
        return redirect(url_for('home'))
        
    query = request.args.get('query')
    students = []
    if query:
        students = User.query.filter(User.role == 'student', User.name.ilike(f'%{query}%')).all()
        
    return render_template('principal_students.html', students=students, query=query)

@app.route('/principal/student_details/<int:student_id>')
@login_required
def principal_student_details(student_id):
    if current_user.role != 'principal' and current_user.role != 'faculty': # Also allow faculty
        return redirect(url_for('home'))
        
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        return redirect(url_for('home'))
        
    # Get attendance summary
    enrollments = Enrollment.query.filter_by(student_id=student.id).all()
    attendance_summary = []
    for enrollment in enrollments:
        school_class = enrollment.school_class
        records = Attendance.query.filter_by(student_id=student.id, class_id=school_class.id).all()
        total = len(records)
        attended = len([r for r in records if r.status == 'Present'])
        percentage = (attended / total * 100) if total > 0 else 0
        attendance_summary.append({
            'class_name': school_class.name,
            'percentage': round(percentage, 2)
        })

    return render_template('student_details.html', student=student, attendance_summary=attendance_summary)

@app.route('/principal/send_message', methods=['POST'])
@login_required
def send_message():
    if current_user.role != 'principal':
        return redirect(url_for('home'))
        
    content = request.form.get('content')
    recipient_type = request.form.get('recipient_type') # 'student', 'faculty', 'both'
    
    if content:
        msg = Message(sender_id=current_user.id, recipient_type=recipient_type, content=content)
        db.session.add(msg)
        db.session.commit()
        flash('Message sent successfully!', 'success')
        
    return redirect(url_for('principal_dashboard'))

@app.route('/principal/delete_message/<int:message_id>')
@login_required
def delete_message(message_id):
    if current_user.role != 'principal':
        return redirect(url_for('home'))
        
    msg = Message.query.get_or_404(message_id)
    if msg.sender_id == current_user.id:
        db.session.delete(msg)
        db.session.commit()
        flash('Message deleted.', 'success')
        
    return redirect(url_for('principal_dashboard'))

@app.route('/principal/profile')
@login_required
def principal_profile():
    if current_user.role != 'principal': return redirect(url_for('home'))
    return render_template('principal_profile.html')

# --- Faculty Updates ---
@app.route('/faculty/search_students')
@login_required
def faculty_search_students():
    if current_user.role != 'faculty':
        return redirect(url_for('home'))
        
    query = request.args.get('query')
    students = []
    if query:
        students = User.query.filter(User.role == 'student', User.name.ilike(f'%{query}%')).all()
        
    return render_template('faculty_students.html', students=students, query=query)


# --- Common Routes ---
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        
        # Verify current password
        if check_password_hash(current_user.password, current_pw):
            current_user.password = generate_password_hash(new_pw)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Incorrect current password.', 'error')
            
    return render_template('change_password.html')

# Context Processor for Notifications
@app.context_processor
def inject_notifications():
    notifications = []
    if current_user.is_authenticated:
        if current_user.role == 'student':
            notifications = Message.query.filter(
                (Message.recipient_type == 'student') | (Message.recipient_type == 'both')
            ).order_by(Message.timestamp.desc()).limit(5).all()
        elif current_user.role == 'faculty':
            notifications = Message.query.filter(
                (Message.recipient_type == 'faculty') | (Message.recipient_type == 'both')
            ).order_by(Message.timestamp.desc()).limit(5).all()
            
    return dict(notifications=notifications)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed classes
        class_names = ['C Language', 'Python Language', 'Java', 'JavaScript', 'Web Development']
        for name in class_names:
            if not SchoolClass.query.filter_by(name=name).first():
                db.session.add(SchoolClass(name=name))
        
        # Seed Admin
        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('welcome')
            admin = User(username='admin', password=hashed_pw, role='admin', name='Administrator')
            db.session.add(admin)
            
        db.session.commit()
    app.run(debug=True, port=8080, host='0.0.0.0')
