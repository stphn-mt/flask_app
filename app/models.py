from datetime import datetime, timezone
from hashlib import md5
from time import time
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import app, db, login
from flask_whooshalchemy import whoosh_index

########################################
class Request_organiser(db.Model):
    user_id: so.Mapped[int] = so.mapped_column(
        primary_key=True, 
        sa.ForeignKey("User.id"), 
        unique=True
    )
    reason: so.Mapped[str] = so.mapped_column(sa.String(256))
    # Relationship to User
    user: so.WriteOnlyMapped["User"] = so.relationship(
        "User",
        back_populates="request_organiser",
    ) #maps foreign key to User table's id

class Location(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    address: so.Mapped[str] = so.mapped_column(sa.String(256))
    postcode: so.Mapped[str] = so.mapped_column(sa.String(8))
    latitude: so.Mapped[float] = so.mapped_column(nullable=False)
    longitude: so.Mapped[float] = so.mapped_column(nullable=False)

    markers: so.WriteOnlyMapped["Marker"] = so.relationship(
        "Marker",
        back_populates="location",
        lazy="dynamic",  # Enables efficient querying of markers
    )

# Organisation = sa.Table(
#     'organisation',
#     db.metadata,
#     sa.Column('id', sa.Integer, primary_key=True),
#     sa.Column('name', sa.String)
# ) doesn't work, might have to add extra table just for this
#  and its not that necessary of a feature anyway
########################################

followers = sa.Table(
    'followers',
    db.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'),
              primary_key=True)
) #linking table for following and followed


class User(UserMixin, db.Model):

    id: so.Mapped[int] = so.mapped_column(primary_key=True) # so.Mapped gives a python data type to the attr, so.mapped_column creates the actual column

    access_level: so.Mapped[int] = so.mapped_column(
        default=0,  # Default to 0 (logged-in user)
        nullable=False
    )
    
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256)) #attr can be defined as Optional
    
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))

    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))

    posts: so.WriteOnlyMapped['Post'] = so.relationship( 
        back_populates='author') #back_populates links Posts.author to User.posts
    following: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, primaryjoin=(followers.c.follower_id == id), # establish link between User and Follower tables, where the id matches (all the users this current user follows)
        secondaryjoin=(followers.c.followed_id == id), #links followers back to users. identifies all users who are followed by the current user
        back_populates='followers') #links User.following to Follower.followers (who the user is following)
    followers: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following') #same but for who the user is being followed by

    request_organiser: so.WriteOnlyMapped["RequestOrganiser"] = so.relationship(
        "RequestOrganiser",
        back_populates="user",
        uselist=False,  # This ensures a one-to-one relationship
    )
    markers: so.WriteOnlyMapped["Marker"] = so.relationship(
        "Marker",
        back_populates="creator",  # Links to the `Marker.creator` relationship
        lazy="dynamic",           # Enables efficient querying of markers
    )
    def __repr__(self):
        return '<User {}>'.format(self.username) # provides information in a nice format for each User

    def set_password(self, password):
        self.password_hash = generate_password_hash(password) # applies a hashing algorithm to encrypt passwords

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) 

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}' #provides an automatic avatar

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery())
        return db.session.scalar(query)

    def following_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery())
        return db.session.scalar(query)

    def following_posts(self):
        Author = so.aliased(User)
        Follower = so.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(sa.or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return db.session.get(User, id)


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class Post(db.Model):
    __searchable__ = ['body']  # Fields to index

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)

    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self): #provides a user-friendly description of each record in the table
        return '<Post {}>'.format(self.body)

class Marker(db.Model):
    __searchable__ = ['event_name', 'event_description', 'user_id', 'filter_type']  # Fields to index
    
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    event_name: so.Mapped[str] = so.mapped_column(sa.String(140), nullable=True)
    event_time: so.Mapped[datetime] = so.mapped_column(nullable=True)
    event_description: so.Mapped[str] = so.mapped_column(sa.String(140))
    filter_type: so.Mapped[str] = so.mapped_column(sa.String(60))
    user_id: so.Mapped[str] = so.mapped_column(db.ForeignKey("User.id"))
    location_id: so.Mapped[str] = so.mapped_column(db.ForeignKey("Location.id"))

    def __repr__(self) -> str:
        return f"<Marker (id={self.id})>"
    
    location: so.WriteOnlyMapped["Location"] = so.relationship(
        "Location",
        back_populates="markers",
        foreign_keys="[Marker.location_id]"
    )

    # Relationship to User
    creator: so.WriteOnlyMapped["User"] = so.relationship(
        "User",
        back_populates="markers",  # Links to the `User.markers` relationship
        foreign_keys="[Marker.user_id]"
    )
    

woosh_index(app, Marker)