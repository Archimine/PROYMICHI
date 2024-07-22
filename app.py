from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from config import Config
from models import db, User, Course, Enrollment, Payment
from forms import RegistrationFormStudent, RegistrationFormTeacher, LoginForm, CourseForm, PaymentForm

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    form = RegistrationFormStudent()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role='student')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered student!')
        return redirect(url_for('login'))
    return render_template('register_student.html', form=form)

@app.route('/register_teacher', methods=['GET', 'POST'])
def register_teacher():
    form = RegistrationFormTeacher()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role='teacher')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered teacher!')
        return redirect(url_for('login'))
    return render_template('register_teacher.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'admin':
        flash('You do not have permission to create a course')
        return redirect(url_for('dashboard'))
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(name=form.name.data, description=form.description.data)
        db.session.add(course)
        db.session.commit()
        flash('Course created successfully')
        return redirect(url_for('dashboard'))
    return render_template('create_course.html', form=form)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'admin':
        flash('You do not have permission to edit this course')
        return redirect(url_for('dashboard'))
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        course.name = form.name.data
        course.description = form.description.data
        db.session.commit()
        flash('Course updated successfully')
        return redirect(url_for('dashboard'))
    return render_template('edit_course.html', form=form, course=course)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'admin':
        flash('You do not have permission to delete this course')
        return redirect(url_for('dashboard'))
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully')
    return redirect(url_for('dashboard'))

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash('You do not have permission to access this page.')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    # Verificar que el estudiante no esté matriculado en más de 3 cursos
    if len(current_user.enrollments) >= 3:
        flash('You cannot enroll in more than 3 courses.')
        return redirect(url_for('list_courses'))
    
    # Verificar si el estudiante ya está matriculado en el curso
    if Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first():
        flash('You are already enrolled in this course.')
        return redirect(url_for('list_courses'))
    
    # Crear una nueva inscripción
    enrollment = Enrollment(student_id=current_user.id, course_id=course_id, status='pending')
    db.session.add(enrollment)
    db.session.commit()
    flash('Enrollment request sent.')
    return redirect(url_for('list_courses'))

@app.route('/waitlist/<int:course_id>', methods=['POST'])
@login_required
def waitlist(course_id):
    course = Course.query.get_or_404(course_id)
    if Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first():
        flash('You are already enrolled or on the waitlist for this course')
        return redirect(url_for('dashboard'))
    waitlist_entry = Enrollment(student_id=current_user.id, course_id=course_id, status='waitlist')
    db.session.add(waitlist_entry)
    db.session.commit()
    flash('You are now on the waitlist for this course')
    return redirect(url_for('dashboard'))

@app.route('/validate_enrollment/<int:enrollment_id>', methods=['POST'])
@login_required
def validate_enrollment(enrollment_id):
    if current_user.role != 'admin':
        flash('You do not have permission to validate enrollments')
        return redirect(url_for('dashboard'))
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    if request.form['action'] == 'approve':
        enrollment.status = 'approved'
    else:
        enrollment.status = 'rejected'
    db.session.commit()
    flash(f'Enrollment {enrollment.status.capitalize()} successfully')
    return redirect(url_for('dashboard'))

@app.route('/course_report/<int:course_id>')
@login_required
def course_report(course_id):
    if current_user.role != 'teacher':
        flash('You do not have permission to view this report')
        return redirect(url_for('dashboard'))
    course = Course.query.get_or_404(course_id)
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    return render_template('course_report.html', course=course, enrollments=enrollments)

@app.route('/make_payment', methods=['GET', 'POST'])
@login_required
def make_payment():
    form = PaymentForm()
    if form.validate_on_submit():
        payment = Payment(student_id=current_user.id, amount=form.amount.data)
        db.session.add(payment)
        db.session.commit()
        flash('Payment recorded successfully')
        return redirect(url_for('dashboard'))
    return render_template('make_payment.html', form=form)

@app.route('/confirm_payment/<int:payment_id>', methods=['POST'])
@login_required
def confirm_payment(payment_id):
    if current_user.role != 'admin':
        flash('You do not have permission to confirm payments')
        return redirect(url_for('dashboard'))
    payment = Payment.query.get_or_404(payment_id)
    if request.form['action'] == 'approve':
        payment.status = 'approved'
    else:
        payment.status = 'rejected'
    db.session.commit()
    flash(f'Payment {payment.status.capitalize()} successfully')
    return redirect(url_for('dashboard'))

@app.route('/courses')
@login_required
def list_courses():
    if current_user.role != 'student':
        flash('You do not have permission to access this page.')
        return redirect(url_for('dashboard'))
    courses = Course.query.all()
    return render_template('list_courses.html', courses=courses)

@app.route('/admin/enrollments')
@login_required
def manage_enrollments():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('dashboard'))
    enrollments = Enrollment.query.all()
    return render_template('manage_enrollments.html', enrollments=enrollments)

@app.route('/admin/approve_enrollment/<int:enrollment_id>', methods=['POST'])
@login_required
def approve_enrollment(enrollment_id):
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('dashboard'))
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    enrollment.status = 'approved'
    db.session.commit()
    flash('Enrollment approved.')
    return redirect(url_for('manage_enrollments'))

@app.route('/admin/reject_enrollment/<int:enrollment_id>', methods=['POST'])
@login_required
def reject_enrollment(enrollment_id):
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('dashboard'))
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    enrollment.status = 'rejected'
    db.session.commit()
    flash('Enrollment rejected.')
    return redirect(url_for('manage_enrollments'))

def create_admin():
    with app.app_context():
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('adminpassword')  # Cambia 'adminpassword' por la contraseña que desees
            db.session.add(admin)
            db.session.commit()
            print("Administrador creado exitosamente.")
        else:
            print("El administrador ya existe.")

if __name__ == '__main__':
    create_admin()  # Llama a la función para crear el admin
    app.run(debug=True)
