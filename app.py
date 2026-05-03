import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Appointment, Invoice, Completion, Rating, LocationLog, Payroll
from utils.auth import role_required
from utils.notifications import notify_engineer_of_assignment, notify_admin_of_booking, send_notification
from utils.maps import get_google_maps_api_key, ai_triage_suggestion
from utils.payments import process_payout
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key-change-me-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- PUBLIC GUEST ROUTES ---

@app.route('/')
def index():
    # Show Customer View by default
    return redirect(url_for('customer_view'))

@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin_dashboard'))

@app.route('/engineer')
def engineer_redirect():
    return redirect(url_for('engineer_dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# Signup disabled as per requirements. Admin creates all accounts.
# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     ...

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Account is disabled. Please contact admin.')
                return redirect(url_for('login'))
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'engineer':
                return redirect(url_for('engineer_dashboard'))
            else:
                return redirect(url_for('customer_view'))
        
        flash('Invalid login credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('customer_view'))

@app.route('/customer')
def customer_view():
    recent_booking_id = session.get('last_booking_id')
    appointment = None
    if recent_booking_id:
        appointment = db.session.get(Appointment, recent_booking_id)
    return render_template('customer_dashboard.html', appointment=appointment)

@app.route('/book', methods=['GET', 'POST'])
def book_appointment():
    selected_service = request.args.get('service', '')
    if request.method == 'POST':
        # Guest Details
        guest_name = request.form['name']
        guest_email = request.form['email']
        guest_phone = request.form['phone']
        
        issue = request.form['issue']
        service_category = request.form.get('service_category')
        preferred_date_str = request.form.get('date', '')
        
        try:
            preferred_date = datetime.strptime(preferred_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Please select a valid preferred visit date.', 'error')
            return redirect(url_for('book_appointment', service=service_category))

        # Location is now text-based only; lat/lng default to 0
        lat = 0.0
        lng = 0.0
        physical_address = request.form.get('physical_address', '')
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(f"guest_{datetime.now().timestamp()}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = os.path.join('uploads', filename)

        appointment = Appointment(
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            service_category=service_category,
            issue=issue,
            preferred_date=preferred_date,
            location_lat=lat,
            location_lng=lng,
            physical_address=physical_address,
            image_path=image_path,
            status='Pending',
            qr_code_data=f"SR-{datetime.now().timestamp()}"
        )
        db.session.add(appointment)
        db.session.commit()
        
        # Store in session so they can see it on the dashboard
        session['last_booking_id'] = appointment.id
        
        # Notify Admins
        notify_admin_of_booking(guest_name, appointment.id)
        
        flash('Booking submitted successfully! You can track it here.')
        return redirect(url_for('customer_view'))
    
    return render_template('book_appointment.html',
                           google_maps_api_key=None,
                           current_date=datetime.now().strftime('%Y-%m-%d'),
                           selected_service=selected_service)



@app.route('/invoice/<int:id>')
def view_invoice(id):
    invoice = db.session.get(Invoice, id)
    if not invoice:
        flash('Invoice not found.')
        return redirect(url_for('customer_view'))
    return render_template('payment_page.html', invoice=invoice)

@app.route('/invoice/<int:id>/pay', methods=['POST'])
def process_payment(id):
    invoice = db.session.get(Invoice, id)
    if not invoice:
        flash('Invoice not found.')
        return redirect(url_for('customer_view'))
    
    # Simulate payment processing
    invoice.status = 'Paid'
    db.session.commit()
    
    flash('Payment of E{:,.2f} received. Thank you!'.format(invoice.amount))
    return redirect(url_for('customer_view'))





# --- ADMIN FEATURES ---

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    appointments = Appointment.query.all()
    engineers = User.query.filter_by(role='engineer').all()
    stats = {
        'pending': Appointment.query.filter_by(status='Pending').count(),
        'assigned': Appointment.query.filter_by(status='Assigned').count(),
        'progress': Appointment.query.filter_by(status='In Progress').count(),
        'completed': Appointment.query.filter_by(status='Completed').count()
    }
    return render_template('admin_dashboard.html', appointments=appointments, engineers=engineers, stats=stats, google_maps_api_key=get_google_maps_api_key())

@app.route('/admin/create-engineer', methods=['POST'])
@login_required
@role_required('admin')
def create_engineer():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    employment_type = request.form.get('employment_type', 'inhouse')
    phone = request.form.get('phone')
    
    momo_number = request.form.get('momo_number')
    bank_name = request.form.get('bank_name')
    account_number = request.form.get('account_number')
    
    if User.query.filter_by(email=email).first():
        flash('Staff email already exists')
    else:
        new_eng = User(
            name=name, email=email, role='engineer', 
            employment_type=employment_type, phone=phone,
            momo_number=momo_number, bank_name=bank_name,
            account_number=account_number
        )
        new_eng.set_password(password)
        db.session.add(new_eng)
        db.session.commit()
        flash(f'Engineer account created for {name}')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/technicians')
@login_required
@role_required('admin')
def manage_technicians():
    technicians = User.query.filter(User.role != 'admin').all()
    return render_template('manage_technicians.html', technicians=technicians)

@app.route('/admin/technicians/toggle/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_technician_status(id):
    user = db.session.get(User, id)
    if user:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f'Status updated for {user.name}')
    return redirect(url_for('manage_technicians'))

@app.route('/admin/technicians/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_technician(id):
    user = db.session.get(User, id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'Technician {user.name} removed')
    return redirect(url_for('manage_technicians'))

@app.route('/admin/payroll', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def payroll():
    if request.method == 'POST':
        user_id = request.form['user_id']
        amount = float(request.form['amount'])
        method = request.form.get('payment_method', 'MoMo')
        notes = request.form.get('notes')
        
        user = db.session.get(User, user_id)
        
        # Trigger Payout via Utility
        payout_result = process_payout(user, amount, method)
        
        record = Payroll(
            user_id=user_id, 
            amount=amount, 
            payment_method=method,
            notes=notes,
            status='Success' if payout_result['success'] else 'Failed',
            transaction_id=payout_result.get('transaction_id')
        )
        db.session.add(record)
        db.session.commit()
        
        if payout_result['success']:
            flash(f'Payout successful: {payout_result["message"]}')
        else:
            flash(f'Payout error: {payout_result["message"]}', 'error')
            
        return redirect(url_for('payroll'))
        
    technicians = User.query.filter_by(role='engineer').all()
    records = Payroll.query.order_by(Payroll.payment_date.desc()).all()
    return render_template('payroll.html', technicians=technicians, records=records)
    
@app.route('/admin/system-qr')
@login_required
@role_required('admin')
def system_qr():
    return render_template('system_qr.html')

@app.route('/api/location/update', methods=['POST'])
@login_required
def update_location():
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    apt_id = data.get('appointment_id')
    
    if lat and lng:
        log = LocationLog(user_id=current_user.id, appointment_id=apt_id, lat=lat, lng=lng)
        db.session.add(log)
        db.session.commit()
        return {'status': 'success'}
    return {'status': 'error', 'message': 'Missing data'}, 400

@app.route('/admin/journey/<int:apt_id>')
@login_required
@role_required('admin')
def view_journey(apt_id):
    apt = db.session.get(Appointment, apt_id)
    logs = LocationLog.query.filter_by(appointment_id=apt_id).order_by(LocationLog.timestamp.asc()).all()
    return render_template('journey_map.html', appointment=apt, logs=logs)

@app.route('/admin/assign/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def assign_engineer(id):
    engineer_id = request.form['engineer_id']
    apt = db.session.get(Appointment, id)
    apt.engineer_id = engineer_id
    apt.status = 'Assigned'
    db.session.commit()
    notify_engineer_of_assignment(engineer_id, id)
    flash('Engineer assigned successfully!')
    return redirect(url_for('admin_dashboard'))

# ... rest of admin routes (invoice, approve) remain same but need to handle guest names ...

@app.route('/admin/invoice/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def generate_invoice(id):
    if request.method == 'POST':
        service_fee = float(request.form['service_fee'])
        transport_fee = float(request.form['transport_fee'])
        description = request.form['description']
        total = service_fee + transport_fee
        
        invoice = Invoice(
            appointment_id=id,
            service_fee=service_fee,
            transport_fee=transport_fee,
            amount=total,
            description=description
        )
        db.session.add(invoice)
        db.session.commit()
        flash('Invoice generated!')
        return redirect(url_for('admin_dashboard'))
    
    apt = db.session.get(Appointment, id)
    ai_note = ai_triage_suggestion(apt.issue)
    return render_template('invoice.html', appointment=apt, ai_note=ai_note)

@app.route('/admin/approve/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_approve_job(id):
    apt = db.session.get(Appointment, id)
    apt.status = 'Completed'
    db.session.commit()
    flash('Job final approval granted!')
    return redirect(url_for('admin_dashboard'))

# --- ENGINEER FEATURES ---

@app.route('/engineer/dashboard')
@login_required
@role_required('engineer')
def engineer_dashboard():
    jobs = Appointment.query.filter_by(engineer_id=current_user.id).all()
    return render_template('engineer_dashboard.html', jobs=jobs, google_maps_api_key=get_google_maps_api_key())

@app.route('/engineer/status/<int:id>', methods=['POST'])
@login_required
@role_required('engineer')
def update_engineer_status(id):
    status = request.form.get('status')
    notes = request.form.get('notes')
    signature = request.form.get('signature')
    
    apt = db.session.get(Appointment, id)
    apt.status = status
    if notes:
        apt.notes = notes
        
    if status == 'Done':
        comp = Completion.query.filter_by(appointment_id=id).first()
        if not comp:
            comp = Completion(appointment_id=id)
            db.session.add(comp)
        comp.engineer_confirm = True
        comp.engineer_signature = signature
        
    db.session.commit()
    flash(f'Status updated to {status}')
    return redirect(url_for('engineer_dashboard'))

@app.route('/appointment/<int:id>/confirm', methods=['POST'])
def customer_confirm_completion(id):
    signature = request.form.get('signature')
    apt = db.session.get(Appointment, id)
    
    comp = Completion.query.filter_by(appointment_id=id).first()
    if not comp:
        comp = Completion(appointment_id=id)
        db.session.add(comp)
    
    comp.customer_confirm = True
    comp.customer_signature = signature
    
    # If both confirmed, auto-complete
    if comp.engineer_confirm and comp.customer_confirm:
        apt.status = 'Completed'
        flash('Service successfully completed and verified!')
    else:
        flash('Completion confirmed. Waiting for final processing.')
        
    db.session.commit()
    return redirect(url_for('customer_view'))

# --- API ROUTES ---

@app.route('/api/notifications')
@login_required
def get_notifications():
    from models import Notification
    # Get direct user notifications OR notifications targeted at their role
    notifs = Notification.query.filter(
        (Notification.user_id == current_user.id) | 
        (Notification.role_target == current_user.role)
    ).filter_by(is_read=False).order_by(Notification.timestamp.desc()).all()
    
    return {
        'count': len(notifs),
        'notifications': [{
            'id': n.id,
            'message': n.message,
            'time': n.timestamp.strftime('%H:%M')
        } for n in notifs]
    }

@app.route('/api/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    from models import Notification
    from models import db
    notifs = Notification.query.filter(
        (Notification.user_id == current_user.id) | 
        (Notification.role_target == current_user.role)
    ).filter_by(is_read=False).all()
    
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return {'status': 'success'}

# --- DATABASE SETUP SCRIPT ---

@app.cli.command("init-db")
def init_db():
    db.create_all()
    if not User.query.filter_by(email='admin@digitalinfra.pro').first():
        admin = User(name='Admin User', email='admin@digitalinfra.pro', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    print("Database initialized.")

@app.route('/appointment/<int:id>/rate', methods=['POST'])
@login_required
def submit_rating(id):
    rating_val = request.form.get('rating')
    feedback = request.form.get('feedback')
    
    existing_rating = Rating.query.filter_by(appointment_id=id).first()
    if existing_rating:
        flash('Rating already submitted.')
    else:
        rating = Rating(appointment_id=id, rating=int(rating_val), feedback=feedback)
        db.session.add(rating)
        db.session.commit()
        flash('Thank you for your feedback!')
        
    return redirect(url_for('customer_view'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
