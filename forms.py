from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, NumberRange

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CourseForm(FlaskForm):
    name = StringField('Course Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Save')

class RegistrationFormStudent(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class RegistrationFormTeacher(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class PaymentForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Pay')
