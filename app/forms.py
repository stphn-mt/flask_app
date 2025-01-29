from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    TextAreaField, HiddenField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, \
    Length
import sqlalchemy as sa
from app import db
from app.models import User

class RequestOrganiserForm(FlaskForm):
    reason = StringField('What events would you organise?', validators=[DataRequired()])
    submit = SubmitField('Submit')

class EventForm(FlaskForm):
    event_name = StringField('Event Name', validators=[DataRequired()])
    event_time = DateTimeLocalField(
        'Event Time',
        validators=[DataRequired()],
        format='%Y-%m-%dT%H:%M'  # Format for HTML5 datetime-local input
    filter_type = StringField('Filters')
    )
    description = TextAreaField('Description', validators=[DataRequired()])
    address = StringField('Address')
    postcode = StringField('Postcode')
    latitude = HiddenField('Latitude', render_kw={"id": "latitude"})
    longitude = HiddenField('Longitude', render_kw={"id": "longitude"})
    submit = SubmitField('Submit')

class LoginForm(FlaskForm): #to create a form, inherit from Flask’s FlaskForm 
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me') #check box “remember me”
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where( 
            User.username == username.data)) #get first match in db
        if user is not None:
            raise ValidationError('Please use a different username.') #if there is already a user with this username in the db, raise error

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data)) #same check as above
        if user is not None:
            raise ValidationError('Please use a different email address.')


class ResetPasswordRequestForm(FlaskForm): #”forgot you password?” option, send email to reset
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField('Request Password Reset')


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me',
                             validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            if user is not None:
                raise ValidationError('Please use a different username.')


class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Submit')

#types: login, register, sign, reset password, request reset password through email, edit profile, post
