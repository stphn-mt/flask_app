from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField, HiddenField, SelectField, SelectMultipleField
from wtforms.fields import TimeField, DateField, URLField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, \
    Length
import re
from app import db
import sqlalchemy as sa
from app.models import User


def is_strong_password(form, password):
    if len(password.data) < 8:
        raise ValidationError('Password must be atleast 8 characters')
    elif not re.search("[a-z]", password.data):
        raise ValidationError('Password must contain at least one lowercase letter')
    elif not re.search("[A-Z]", password.data):
        raise ValidationError('Password must contain at least one uppercase letter')
    elif not re.search("[0-9]", password.data):
        raise ValidationError('Password must contain at least one number')
    elif not re.search("[!@£$%^&*]", password.data):
        raise ValidationError('Password must contain at least one special character: !@£$%^&* ')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), is_strong_password], render_kw={"id": "Password"})
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(),
                                       EqualTo('password')], render_kw={"id": "Confirm_password"})  # Fix here
    show_password = BooleanField('Show password', render_kw={"id": "Check"})
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where( 
            User.username == username.data)) #get first match in db
        if user is not None:
            raise ValidationError('Please use a different username.') #if there is already a user with this username in the db, raise error
        tempstring = username.data.replace("_", "")
        if tempstring.isalnum() == False:
            raise ValidationError('Username can only contain alphanumeric characters and underscores.')

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data)) #same check as above
        allowed_chars = [".", "@", "_", "-"]
        tempstring = email.data
        for char in allowed_chars:
            tempstring = tempstring.replace(char, "")
        if tempstring.isalnum() == False:
            raise ValidationError('Email uses invalid characters.')
        if user is not None:
            raise ValidationError('Please use a different email address.')

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    about_me = TextAreaField('About me',
                             validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs): #defines original username for form to use in validation
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username): #easily validate username on submition
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            if user is not None:
                raise ValidationError('Please use a different username.')
            tempstring = username.data.replace("_", "")
            if tempstring.isalnum() == False:
                raise ValidationError('Username can only contain alphanumeric characters and underscores.')

class EventForm(FlaskForm):
    event_name = StringField('Event Name', validators=[DataRequired()])
    filter_type = SelectField('Filters', choices=[('Sport', 'Sport'), ('Club', 'Club'), 
    ('Support', 'Support'), ('Children','Children'), ('Other', 'Other'),
    ])
    description = TextAreaField('Description', validators=[DataRequired()])
    website = URLField('Website')
    address = StringField('Address')
    postcode = StringField('Postcode')
    latitude = HiddenField('Latitude', render_kw={"id": "latitude"})
    longitude = HiddenField('Longitude', render_kw={"id": "longitude"})
    submit = SubmitField('Submit')

class ModifyEventForm(FlaskForm):
    marker_id = HiddenField('marker_id', validators=[DataRequired()], render_kw={"id": "marker_id"})
    event_name = StringField('Event Name', validators=[DataRequired()], render_kw= {"id": "mod-event_name"})
    filter_type = SelectField('Filters', choices=[('Sport', 'Sport'), ('Club','Club'),
     ('Support', 'Support'), ('Children','Children'), ('Other', 'Other'),], render_kw= {"id": "mod-filter_type"})
    description = TextAreaField('Description', validators=[DataRequired()], render_kw= {"id": "mod-description"})
    website = URLField('Website', render_kw= {"id": "mod-website"})
    submit = SubmitField('Submit')

class LoginForm(FlaskForm): #to create a form, inherit from Flask’s FlaskForm 
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()],render_kw={"id": "password"})
    show_password = BooleanField('Show password', render_kw={"id": "check"})
    remember_me = BooleanField('Remember Me') #check box “remember me”
    submit = SubmitField('Sign In')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), is_strong_password], render_kw={"id": "Password"})
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(),
                                       EqualTo('password')], render_kw={"id": "Confirm_password"})  # Fix here
    show_password = BooleanField('Show password', render_kw={"id": "Check"})
    submit = SubmitField('Request Password Reset')

class ResetPasswordRequestForm(FlaskForm): #”forgot you password?” option, send email to reset
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Submit')

class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


#types: login, register, sign, reset password, request reset password through email, edit profile, post
