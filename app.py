from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from config import Config
from models import db, User, Course, Enrollment, Payment
from forms import RegistrationFormStudent, RegistrationFormTeacher, LoginForm, CourseForm, PaymentForm
import random
import string

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
    if current_user.role == 'admin' or current_user.role == 'teacher':
        courses = Course.query.all()
        return render_template('dashboard.html', courses=courses)
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
    course = Course.query.get_or_404(course_id)
    
    # Verificar si el usuario ya está inscrito en el curso
    existing_enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        flash('You are already enrolled in this course.')
        return redirect(url_for('list_courses'))
    
    # Verificar el límite de inscripción
    current_enrollments = Enrollment.query.filter_by(course_id=course_id, status='approved').count()
    if current_enrollments < 15:
        # Inscribir al estudiante en el curso
        enrollment = Enrollment(student_id=current_user.id, course_id=course_id, status='pending')
        db.session.add(enrollment)
        db.session.commit()
        flash('Enrollment request sent.')
    else:
        # Añadir al estudiante a la lista de espera
        waitlist_entry = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id, status='waitlist').first()
        if waitlist_entry:
            flash('You are already on the waitlist for this course.')
        else:
            waitlist_entry = Enrollment(student_id=current_user.id, course_id=course_id, status='waitlist')
            db.session.add(waitlist_entry)
            db.session.commit()
            flash('You are now on the waitlist for this course.')
    
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

@app.route('/apply_mass_enrollments/<int:course_id>', methods=['POST'])
@login_required
def apply_mass_enrollments(course_id):
    if current_user.role != 'admin':
        flash('You do not have permission to apply mass enrollments.')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    
    # Verifica cuántos estudiantes ya están inscritos en el curso
    current_enrollments = Enrollment.query.filter_by(course_id=course_id).count()
    if current_enrollments >= 15:
        flash('The course already has 15 or more students.')
        return redirect(url_for('dashboard'))
    
    # Calcula cuántos estudiantes se pueden inscribir
    remaining_spots = 15 - current_enrollments

    # Genera y agrega usuarios ficticios
    for _ in range(remaining_spots):
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        email = f'{username}@example.com'
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        if not User.query.filter_by(email=email).first():
            new_user = User(username=username, email=email, role='student')
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            # Inscribe al nuevo usuario en el curso
            enrollment = Enrollment(student_id=new_user.id, course_id=course_id, status='approved')
            db.session.add(enrollment)

    db.session.commit()
    flash(f'{remaining_spots} students have been enrolled in the course.')
    return redirect(url_for('dashboard'))

@app.route('/duplicate_course/<int:course_id>', methods=['POST'])
@login_required
def duplicate_course(course_id):
    if current_user.role != 'admin':
        flash('You do not have permission to duplicate courses.')
        return redirect(url_for('dashboard'))
    
    original_course = Course.query.get_or_404(course_id)
    
    # Crear un nuevo curso duplicado
    new_course = Course(name=f"{original_course.name} - Copy", description=original_course.description)
    db.session.add(new_course)
    db.session.commit()
    
    # Obtener los estudiantes en lista de espera para el curso original
    waitlist_entries = Enrollment.query.filter_by(course_id=course_id, status='waitlist').all()
    
    for entry in waitlist_entries:
        # Mover estudiantes de la lista de espera al nuevo curso
        new_entry = Enrollment(student_id=entry.student_id, course_id=new_course.id, status='pending')
        db.session.add(new_entry)
    
    # Borrar las entradas de la lista de espera para el curso original
    for entry in waitlist_entries:
        db.session.delete(entry)
    
    db.session.commit()
    
    flash('Course duplicated successfully.')
    return redirect(url_for('admin_courses'))


@app.route('/waitlist_report/<int:course_id>')
@login_required
def waitlist_report(course_id):
    if current_user.role != 'admin':
        flash('You do not have permission to view waitlist reports.')
        return redirect(url_for('dashboard'))

    course = Course.query.get_or_404(course_id)
    waitlist_entries = Enrollment.query.filter_by(course_id=course_id, status='waitlist').all()

    return render_template('waitlist_report.html', course=course, waitlist_entries=waitlist_entries)

@app.route('/admin/courses')
@login_required
def admin_courses():
    if current_user.role != 'admin':
        flash('You do not have permission to view courses.')
        return redirect(url_for('dashboard'))
    courses = Course.query.all()
    return render_template('admin_courses.html', courses=courses)

@app.route('/course_students/<int:course_id>')
@login_required
def course_students(course_id):
    course = Course.query.get_or_404(course_id)
    enrollments = Enrollment.query.filter_by(course_id=course_id, status='approved').all()
    
    students = [User.query.get(enrollment.student_id) for enrollment in enrollments]
    
    return render_template('course_students.html', course=course, students=students)



def create_admin():
    with app.app_context():
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('adminpassword')  # Cambia 'adminpassword' por la contraseña que desees
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    create_admin()  # Crea un usuario administrador si no existe
    app.run(debug=True)
