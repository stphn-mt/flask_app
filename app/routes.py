from flask import render_template, flash, redirect, url_for, request, g, jsonify, abort, session
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, PostForm, ResetPasswordRequestForm, ResetPasswordForm, \
        EventForm, ModifyEventForm
from app import app, db, search
import sqlalchemy as sa
from app.models import User, Post, Marker, Location
from flask_login import login_user, logout_user, current_user, login_required
import requests
from datetime import datetime, timezone
from urllib.parse import urlsplit
from app.email import send_password_reset_email
import flask_msearch

# with app.app_context(): #clears my database of all data!
#     def clear_data(session):
#         meta = db.metadata
#         for table in reversed(meta.sorted_tables):
#             print ('Clear table %s' % table)
#             session.execute(table.delete())
#             session.commit()
#     clear_data(db.session)

# with app.app_context(): # hardcode an admin into my db   
#     user = User(username='Stephen1', email='stevejameson238@gmail.com', access_level=1)
#     user.set_password('Admin1!')
#     db.session.add(user)
#     db.session.commit()


@app.before_request
def before_request(): # if user is logged in, record the time they log in, update database
    # print("Before request triggered")  # Debugging
    if current_user.is_authenticated: 
        # print("current_user is triggered")  # Debugging
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        
def get_coordinates(postcode):# Fetch latitude and longitude from Postcodes.io
    url = f"https://api.postcodes.io/postcodes/{postcode}"
    # assign the response of postcodes.io to a variable by http GET request function
    response = requests.get(url)
    if response.status_code == 200: #if request/response successful
        data = response.json() # convert the response to a python dictionary that is friendly for javascript
        return data["result"]["latitude"], data["result"]["longitude"]
    return None, None  # Return None if invalid postcode


@app.route('/', methods = ["GET", "POST"]) #handle map and creating/modifying markers
def map():
    form = EventForm()
    form2 = ModifyEventForm()
    session.permanent = True
    if current_user.is_anonymous:
        current_user.access_level = 0
        return render_template('map.html')
    if 'marker_count' not in session:
        session['marker_count'] = 0  # Initialize counter if not set
    if session['marker_count'] <= 1:
        if form.validate_on_submit():
            address = form.address.data
            postcode = form.postcode.data
            latitude, longitude = get_coordinates(postcode) # get coordinates from postcode automatically
            # Check if location already exists
            location = Location.query.filter_by(latitude=latitude, longitude=longitude).first()
            print('checking lat and long')
            if latitude and longitude: # if postcode is valid
                print('postcode valid')
                if not location: # if location doesn't exist, create it
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
                    event_name = form.event_name.data,
                    approved = False, #if organiser, allow "approve" button to be clicked when showing modify event api
                    event_description = form.description.data,
                    website = form.website.data,
                    filter_type = form.filter_type.data,
                    User_id=current_user.id, # Assign marker to logged-in user
                    Location_id=location.id, # Assign marker to location
                )
            
                db.session.add(marker)
                db.session.commit()
                print('adding marker')
                session['marker_count'] += 1  # Increment counter
                return render_template('map.html', form=form, user_access_level=current_user.access_level, user_id=current_user.id, form2=form2)
            return ("Invalid postcode", 400)

    else:
        flash('You have reached the maximum number of markers allowed today.', 'danger')
    return render_template('map.html', form=form, user_access_level=current_user.access_level, user_id=current_user.id, form2=form2)

# transfer db marker data to / and display all prev stored markers

@app.route('/api/markers') # handle rendering correct markers based on search-filter or no search-filter
def api_markers():
    try:
        query = request.args.get('query', '')  # Get query, default to empty string

        if query:
            print('searching')
            markers = Marker.query.msearch(query, fields=['event_name', 'event_description', 'User_id', 'filter_type']).all()
        else:
            markers = Marker.query.all()
        marker_data = [
            {
                'id': marker.id,
                'latitude': marker.Location.latitude,
                'longitude': marker.Location.longitude,
                'event_name': marker.event_name,
                'description': marker.event_description,
                'approved': marker.approved,
                'website': marker.website,
                'address': marker.Location.address,
                'postcode': marker.Location.postcode,
                'filter_type': marker.filter_type,
                'creator': marker.User_id, #had to change from marker.creator to marker.User_id (<User_id> given instead of int)
                'email_to': marker.creator.email,
                'creator_name': str(marker.creator),
            }
            for marker in markers
        ]
        print(marker_data)
        return jsonify(marker_data)
    except Exception as e:
        print(f"Error: {str(e)}")  # Log error to terminal
        return jsonify({'error': str(e)}), 500

@app.route('/api/markers/', methods=['POST']) # handle modifying markers from modify form in map view
def update_marker():
    try:
        
        marker_id = request.form.get('marker_id')
        print(marker_id)
        marker = Marker.query.get(marker_id)

        if not marker:
            flash("Marker not found!", "danger")
            return redirect(url_for('map'))

        marker.event_name = request.form.get('event_name', marker.event_name)
        marker.event_description = request.form.get('description', marker.event_description)
        marker.website = request.form.get('website', marker.website)

        db.session.commit()
        search.update_noticeboard()
        search.update_noticeboard(Marker)

        return redirect(url_for('map'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/markers/<int:marker_id>', methods=['DELETE']) # handle deleting markers in map view
def delete_marker(marker_id):
    try:
        marker = Marker.query.get(marker_id)
        if not marker:
            return jsonify({'error': 'Marker not found'}), 404
        db.session.delete(marker)
        if marker.User_id == current_user.id and session['marker_count'] > 0:
            session['marker_count'] -= 1
        db.session.commit()
        search.update_noticeboard()
        search.update_noticeboard(Marker)
        return jsonify({'message': 'Marker deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/approve/<int:marker_id>', methods=['PUT']) # handle approving markers in map view
def approve(marker_id): 
    try:
        marker = Marker.query.get(marker_id)
        if not marker:
            return jsonify({'error': 'Marker not found'}), 404
        marker.approved = True
        db.session.commit()
        return jsonify({'message': 'Marker approved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_user/<int:user_id>', methods=['DELETE']) # handle deleting users in admin view
def delete_user(user_id):
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    search.update_index(User)
    return jsonify({'status': 'deleted'})


# Flask route updates:
@app.route('/admin-view') # show table of all users and handle search queries
@login_required
def admin_view():
    if current_user.is_authenticated and current_user.access_level == 1:
        try:
            query = request.args.get('query', '')
            if query:
                user_data = User.query.msearch(query, fields=['username', 'email']).all()
            else:
                user_data = User.query.all()
            marker_data = Marker.query.all()
            return render_template('admin_view.html', users=user_data, markers=marker_data)
        except Exception as e:
            print(f"Error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    else:
        return redirect(url_for('noticeboard.html'))

@app.route('/promote_user/<int:user_id>', methods=['POST']) # handle promoting users in admin view
@login_required
def promote_user(user_id):
    if current_user.access_level != 1:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if user:
        user.access_level = 1
        db.session.commit()
        return jsonify({'status': 'promoted'})
    return jsonify({'error': 'User not found'}), 404

@app.route('/update_user/<int:user_id>', methods=['POST']) # handle updating user info in admin view
@login_required
def update_user(user_id):
    if current_user.access_level != 1:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data or 'field' not in data or 'value' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    user = User.query.get(user_id)
    if user:
        setattr(user, data['field'], data['value'])
        db.session.commit()
        return jsonify({'status': 'updated'})
    return jsonify({'error': 'User not found'}), 404


@app.route('/', methods=['GET', 'POST']) #accept data input from webpage
@app.route('/noticeboard', methods=['GET', 'POST']) # accept “/” or “/noticeboard” as route
@login_required
def noticeboard():
    form = PostForm() #display option to post something
    if form.validate_on_submit(): # if user presses “submit” on post form
        post = Post(body=form.post.data, author=current_user) #add a new record in the post db with the data in the form
        db.session.add(post) #stage changes
        db.session.commit() #commit to db
        flash('Your post is now live!') # show user message
        return redirect(url_for('noticeboard')) # reset the page (return back to noticeboard, which is the current page)

    page = request.args.get('page', 1, type=int) # I THINK “page” is the key of the dict, “1” is the default value (default num of pages) unless there are more.
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False) #paginate the posts by page? [following_posts] [pre-configged no. of mosts per page]
    next_url = url_for('noticeboard', page=posts.next_num) \
        if posts.has_next else None # create next_url variable if there is one available
    prev_url = url_for('noticeboard', page=posts.prev_num) \
        if posts.has_prev else None # same logic
    return render_template('noticeboard.html', title='Noticeboard', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, user_id = current_user.id) # render noticeboard.html, with title home, form = postform, list of paginated posts, and next/prev otions

@app.route('/explore', methods=["GET", "POST"]) # webpage for finding new organisers to follow
@login_required
def explore():
    user_asks = request.args.get('query', '').strip() #look for submitted search query to filter database by
    page = request.args.get('page', 1, type=int) # just moved inside edit zone, get the page we are at
    if user_asks: # if there is a query
        search_results = search_posts_and_users(user_asks) # filter the search for the query
        total = len(search_results)
        posts = search_results[(page - 1) * app.config['POSTS_PER_PAGE']: page * app.config['POSTS_PER_PAGE']] 
        next_url = url_for('explore', page=page + 1) if page * app.config['POSTS_PER_PAGE'] < total else None
        prev_url = url_for('explore', page=page - 1) if page > 1 else None
        return render_template('noticeboard.html', title='Explore', posts=posts, next_url=next_url, prev_url=prev_url, user_id = current_user.id)
    else:
        all_posts = sa.select(Post).order_by(Post.timestamp.desc()) # get all posts in descending order of time
        posts = db.paginate(all_posts, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False) # paginate posts, with descending order of time
        next_url = url_for('explore', page=posts.next_num) \
            if posts.has_next else None
        prev_url = url_for('explore', page=posts.prev_num) \
            if posts.has_prev else None

        return render_template('noticeboard.html', title='Explore',
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, user_id = current_user.id)

def search_posts_and_users(query): # function that allows search by username with flask-msearch
    post_results = Post.query.msearch(query, fields=['body']).all()
    user_results = User.query.msearch(query, fields=['username']).all()

    # Extract user IDs from matched users
    user_ids = []
    for result in user_results:
        user_ids.append(result.id)

    # Get posts by those users
    if user_ids:
        user_posts = Post.query.filter(Post.user_id.in_(user_ids)).all()
    else:
        user_posts = []

    # Remove duplicates using a dictionary
    unique_posts = {}
    for post in (post_results + user_posts):
        unique_posts[post.id] = post  # Keep only the latest occurrence

    return list(unique_posts.values())  # Convert back to list for pagination

@app.route('/delete_post/<int:post_id>', methods=['POST']) # deletes post on explore/home/profile
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id) #query for the first matching result in db, otherwise return a 404 error
    if current_user.id != post.author.id and not current_user.access_level == 1:
        flash("You are not authorized to delete this post.", "danger")
        return redirect(url_for('noticeboard'))
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully.", "success")
    
    return redirect(url_for('noticeboard'))

@app.route('/login', methods=['GET', 'POST']) #provides form and redirect to page user tried to access
def login():
    if current_user.is_authenticated:
        return redirect(url_for('noticeboard')) # if user already logged in, redirect to noticeboard (home) page
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
            next_page = url_for('noticeboard') # if no next, then redirect to home page
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form) # if form is invalid (required inputs missing) then refresh.


@app.route('/logout') #pops user session and logs out.
def logout():
    logout_user()
    session.pop("marker_count", None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST']) #adds user to db
def register():
    if current_user.is_authenticated:
        return redirect(url_for('noticeboard')) #don’t let logged in users try to re-register
    form = RegistrationForm() #render form
    if form.validate_on_submit(): # if all required inputs given
        user = User(username=form.username.data, email=form.email.data) # create new user record
        user.set_password(form.password.data)  #apply hash algorithm to user’s password to keep safe when committed to db
        db.session.add(user) #make a cookie of the user to temporarily store data (when user traverses diff pages)
        db.session.commit() # also permanently save user details and redirect to login page
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form) # if required inputs not given, refresh page


@app.route('/reset_password_request', methods=['GET', 'POST']) #Let's user request a password reset by entering email from login page
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('noticeboard'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data)) # get first result from query for the user’s email
        if user:
            send_password_reset_email(user) # if there is such an email given by the user, send an automated email
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form) # refresh the page if incorrectly filled in form



@app.route('/reset_password/<token>', methods=['GET', 'POST']) # Webpage to reset password using token from email
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('noticeboard'))
    user = User.verify_reset_password_token(token) # give the user a time-limited token (preconfigured time such as 30min)
    if not user: # if token expired/invalid, redirect to home page
        return redirect(url_for('noticeboard'))
    form = ResetPasswordForm() # if the token is still valid, provide a form to reset password
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/user/<username>') # view other user profiles for follow/unfollow
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


@app.route('/edit_profile', methods=['GET', 'POST']) #allows user to modify info about themselves for others to see.
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit(): #If the user changes and submits data on their profile, save their changes
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET': # if user goes onto the edit_profile page, fill in the form with their current data
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
        form.email.data = current_user.email
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@app.route('/follow/<username>', methods=['POST']) # allows follow of users
@login_required
def follow(username):
    form = EmptyForm() #provides a button to submit
    if form.validate_on_submit(): 
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.') #if no user to follow, flash message and redirect
            return redirect(url_for('noticeboard'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'You are following {username}!')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('noticeboard'))


@app.route('/unfollow/<username>', methods=['POST']) # allows unfollow of users
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit(): #if clicked unfollow, get the user from the database to unfollow
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None: #Check if the user trying to be unfollowed exists
            flash(f'User {username} not found.')
            return redirect(url_for('noticeboard'))
        if user == current_user: #Check if user is trying to unfollow themselves
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user) #If pass all checks, unfollow user, flash confirmation message.
        db.session.commit()
        flash(f'You are not following {username}.')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('noticeboard'))



'''
ADD DELETE BUTTON ON USER PROFILES
'''