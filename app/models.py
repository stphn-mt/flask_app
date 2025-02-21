from datetime import datetime, timezone
from hashlib import md5
from time import time
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import app, db, login, search
# from flask_msearch import Search
########################################

class Location(db.Model):
    __tablename__ = "Location"
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    address: so.Mapped[str] = so.mapped_column(sa.String(256))
    postcode: so.Mapped[str] = so.mapped_column(sa.String(8))
    latitude: so.Mapped[float] = so.mapped_column(nullable=False)
    longitude: so.Mapped[float] = so.mapped_column(nullable=False)

    markers: so.Mapped['Marker'] = so.relationship(
        "Marker",
        back_populates="Location",
        # lazy="dynamic",  # Enables efficient querying of Markers
    )


followers = sa.Table(
    'followers',
    db.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('User.id', ondelete='CASCADE'),
              primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('User.id', ondelete='CASCADE'),
              primary_key=True)
) #linking table for following and followed


class User(UserMixin, db.Model):
    __tablename__ = "User"
    __searchable__ = ['username', 'email']
    id: so.Mapped[int] = so.mapped_column(primary_key=True) # so.Mapped gives a python data type to the attr, so.mapped_column creates the actual column

    access_level: so.Mapped[int] = so.mapped_column(
        default=0,  # Default to 0 (logged-in User)
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
        back_populates='author',
        passive_deletes=True) #back_populates links Posts.author to User.posts
    following: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, primaryjoin=(followers.c.follower_id == id), # establish link between User and Follower tables, where the id matches (all the Users this current User follows)
        secondaryjoin=(followers.c.followed_id == id), #links followers back to Users. identifies all Users who are followed by the current User
        back_populates='followers',
        passive_deletes=True) #links User.following to Follower.followers (who the User is following)
    followers: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following',
        passive_deletes=True) #same but for who the User is being followed by

    Markers: so.Mapped["Marker"] = so.relationship(
        "Marker",
        back_populates="creator",  # Links to the `Marker.creator` relationship
        # lazy="dynamic",           # Enables efficient querying of Markers
    )
    def __repr__(self):
        return self.username # provides information in a nice format for each User

    def set_password(self, password):
        self.password_hash = generate_password_hash(password) # applies a hashing algorithm to encrypt passwords

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) 

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}' #provides an automatic avatar

    def follow(self, User):
        if not self.is_following(User):
            self.following.add(User)

    def unfollow(self, User):
        if self.is_following(User):
            self.following.remove(User)

    def is_following(self, User):
        query = self.following.select().where(User.id == User.id)
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
def load_User(id):
    return db.session.get(User, int(id))

class Post(db.Model):
    __searchable__ = ['body']  # Fields to index

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id, ondelete='CASCADE'),index=True)
    author: so.Mapped[User] = so.relationship(back_populates='posts', passive_deletes=True)

    def __repr__(self): #provides a User-friendly description of each record in the table
        return '<Post {}>'.format(self.body)

class Marker(db.Model):
    __tablename__ = "Marker"
    __searchable__ = ['event_name', 'event_description', 'User_id', 'filter_type']  # Fields to index
    ########################################
    approved: so.Mapped[bool] = so.mapped_column(default = False, nullable = False)
    website: so.Mapped[str] = so.mapped_column(nullable=True)
    ########################################
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    event_name: so.Mapped[str] = so.mapped_column(sa.String(140), nullable=False)
    event_description: so.Mapped[str] = so.mapped_column(sa.String(140))
    filter_type: so.Mapped[str] = so.mapped_column(sa.String(60))
    User_id: so.Mapped[str] = so.mapped_column(db.ForeignKey("User.id"))
    Location_id: so.Mapped[str] = so.mapped_column(db.ForeignKey("Location.id"))
    
    def __repr__(self) -> str:
        return f"<Marker (id={self.id})>"
    
    Location: so.Mapped["Location"] = so.relationship(
        "Location",
        back_populates="markers",
        foreign_keys="[Marker.Location_id]"
    )

    # Relationship to User
    creator: so.Mapped["User"] = so.relationship(
        "User",
        back_populates="Markers",  # Links to the `User.Markers` relationship
        foreign_keys="[Marker.User_id]"
    )


# # Set up models
# with app.app_context():
#     db.create_all()
#     search.create_index()