from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from config import Config
from models import db, User, Course
from forms import RegistrationFormStudent, RegistrationFormTeacher, LoginForm, CourseForm

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

@app.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if current_user.role == 'student':
        form = RegistrationFormStudent(obj=current_user)
    else:
        form = RegistrationFormTeacher(obj=current_user)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash('Your profile has been updated!')
        return redirect(url_for('index'))

    return render_template('update_profile.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
