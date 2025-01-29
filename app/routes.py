from datetime import datetime, timezone
from urllib.parse import urlsplit
from flask import render_template, flash, redirect, url_for, request, g, jsonify
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, PostForm, ResetPasswordRequestForm, ResetPasswordForm, \
        EventForm, RequestOrganiserForm
from app.models import User, Post, Marker
from app.email import send_password_reset_email
import flask_whooshalchemy

@app.before_request
def before_request(): # if user is logged in, record the time they log in
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

##################################################


@app.route('/request_organiser', methods=["GET", "POST"])
@login_required
def request_organiser():
    form = RequestOrganiserForm() #get form

    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == current_user.username))

        # Check if user already made a request
        existing_request = db.session.scalar(sa.select(Request_organiser).where(Request_organiser.user_id == user.id))
        if existing_request:
            flash("You have already submitted a request.")
            return redirect(url_for('index'))

        user_requested = Request_organiser(user_id=user.id, reason=form.reason.data)
        db.session.add(user_requested)
        db.session.commit()

        flash("Your request has been received! Please wait for an admin to respond.")
        return redirect(url_for('index'))

    return render_template('request_organiser.html', form=form)

@app.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Marker.query.get_or_404(event_id)
    if event.created_by != current_user.id and not current_user.access_level==2:
        abort(403)  # Unauthorized access
    if request.method == 'POST':
        event.event_name = request.form['title']
        event.event_description = request.form['description']
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_event.html', event=event)

@app.route('/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Marker.query.get_or_404(event_id)
    if event.created_by != current_user.user_id and not current_user.access_level==2:
        abort(403)  # Unauthorized access
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.access_level==2:
        abort(403)  # Unauthorized access
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_view'))
    return render_template('edit_user.html', user=user)

@app.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.access_level==2:
        abort(403)  # Unauthorized access
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_view'))
##################################################
@app.route('/', methods=['GET', 'POST']) #accept data input from webpage
@app.route('/index', methods=['GET', 'POST']) # accept “/” or “/index” as route
@login_required
def index():
    form = PostForm() #display option to post something
    if form.validate_on_submit(): # if user presses “submit” on post form
        post = Post(body=form.post.data, author=current_user) #add a new record in the post db with the data in the form
        db.session.add(post) #stage changes
        db.session.commit() #commit to db
        flash('Your post is now live!') # show user message
        return redirect(url_for('index')) # reset the page (return back to index, which is the current page)
    page = request.args.get('page', 1, type=int) # I THINK “page” is the key of the dict, “1” is the default value (default num of pages) unless there are more.
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False) #paginate the posts by page? [following_posts] [pre-configged no. of mosts per page, error out????]
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None # create next_url variable if there is one available
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None # same logic
    return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url) # render index.html, with title home, form = postform, list of paginated posts, and next/prev otions

@app.route('/map', methods = ["GET", "POST"])
def map():
    form = EventForm()
    if form.validate_on_submit():
        # Retrieve form data
        event_name = form.event_name.data
        event_time = form.event_time.data
        event_description = form.description.data
        latitude = form.latitude.data
        longitude = form.longitude.data
        filter_type = form.filter_type.data  
        address = form.address.data
        postcode = form.address.data
        # Check if location already exists
        location = Location.query.filter_by(latitude=latitude, longitude=longitude).first()
        
        if not location:
            location = Location(
                address=address,  # ADDRESS AND POSTCODE NEED TO BE FOUND
                postcode=postcode,
                latitude=latitude,
                longitude=longitude
            )
            db.session.add(location)
            db.session.flush()  # ensure location id is assigned before using it

        # Create and store new marker
        marker = Marker(
            event_name=event_name,
            event_time=event_time,
            event_description=event_description,
            filter_type=filter_type,
            user_id=current_user.id,  # Assign marker to logged-in user
            location_id=location.id   # Assign marker to location
        )
        
        db.session.add(marker)
        db.session.commit()
        return render_template('map.html', form=form)
    return render_template('map.html', form=form)

# transfer db marker data to /map and display all prev stored markers

@app.route('/api/markers')
def api_markers():
    query = request.args.get('query')  # Get the search query from the request
    if query:
        markers = Marker.query.whoosh_search(query).all()  # Perform full-text search
    else:
        markers = Marker.query.all()  # Fetch all markers if no search query
    marker_data = [
        {
            'latitude': marker.location.latitude,
            'longitude': marker.location.longitude,
            'event_name': marker.event_name,
            'event_time': marker.event_time,
            'description': marker.event_description
        }
        for marker in markers
    ]
    return jsonify(marker_data)  # Return JSON response


@app.route('/admin-view')
def admin_view():
    user_data = User.query.all()  # Fetch all users
    marker_data = Marker.query.all()  # Fetch all markers

    # Pass data to the template
    return render_template('admin_view.html', users=user_data, markers=marker_data)

@app.route('/explore', methods=["GET", "POST"])
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False) # paginate posts, with descending order of time
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Explore',
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index')) # if user already logged in, redirect to index (home) page
    form = LoginForm() # if not logged in, provide a login form
    if form.validate_on_submit(): # if submitted with valid entries in the field
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data)) # let user = the first match where username entered matches a username in the db
        if user is None or not user.check_password(form.password.data): # if there isn’t a matching user, or the password doesn’t match
            flash('Invalid username or password')
            return redirect(url_for('login')) # reset login page and display error
        login_user(user, remember=form.remember_me.data) # from Flask Login library, sets user session as “authenticated” so bypasses decorator “@alogin_required”
        next_page = request.args.get('next') #part of Flask Login,  next= page that was tryig to be accessed when not logged in
        if not next_page or urlsplit(next_page).netloc != '': #netloc secures the url to ensure hackers can’t redirect users to a malicious website
            next_page = url_for('index') # if no next, then redirect to home page
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form) # if form is invalid (required inputs missing) then refresh.


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index')) #don’t let logged in users try to re-register
    form = RegistrationForm() #render form
    if form.validate_on_submit(): # if all required inputs given
        user = User(username=form.username.data, email=form.email.data) # create new user record
        user.set_password(form.password.data)  #apply hash algorithm to user’s password to keep safe when committed to db
        db.session.add(user) #make a cookie of the user to temporarily store data (when user traverses diff pages)
        db.session.commit() # also permanently save user details and redirect to login page
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form) # if required inputs not given, refresh page


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data)) # get first result from query for the user’s email
        if user:
            send_password_reset_email(user) # if there is such an email given by the user, send an automated email
        flash(
            'Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form) # refresh the page if incorrectly filled in form


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token) # give the user a time-limited token (preconfigured time such as 30min)
    if not user: # if token expired/invalid, redirect to home page
        return redirect(url_for('index'))
    form = ResetPasswordForm() # if the token is still valid, provide a form to reset password
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username)) #get the matching user otherwise return a 404 invalid page error
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'],
                        error_out=False) # collect + paginate all the current user’s posts in descending time order
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm() # provide a submit button to follow/unfollow users
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit(): #If the user changes and submits data on their profile, save their changes
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET': # if user goes onto the edit_profile page, fill in the form with their current data
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm() #provides a button to submit
    if form.validate_on_submit(): 
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash('User %(username)s not found.', username=username) #if no user to follow, flash message and redirect
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following %(username)s!', username=username)
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash('User %(username)s not found.', username=username)
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following %(username)s.', username=username)
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))
