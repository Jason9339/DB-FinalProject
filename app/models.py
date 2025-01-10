# models.py
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event


user_friends = db.Table(
    "user_friends",
    db.Column("user1_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("user2_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    favorite_movies = db.relationship(
        "Movie", secondary="user_favorites", backref="favorited_by"
    )
    bookings = db.relationship("Booking", backref="user", lazy=True)
    reviews = db.relationship("Review", backref="user", lazy=True)
    friends = db.relationship(
        "User",
        secondary=user_friends,  # 使用已定義的 user_friends
        primaryjoin=(id == user_friends.c.user1_id),
        secondaryjoin=(id == user_friends.c.user2_id),
        backref=db.backref("friendship", lazy="dynamic"),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    genre = db.Column(db.String(100))
    screening_times = db.relationship("ScreeningTime", backref="movie", lazy=True)
    release_date = db.Column(db.String(50), nullable=True)
    poster_url = db.Column(db.String(300), nullable=True)
    reviews = db.relationship("Review", backref="movie", lazy=True)
    is_current = db.Column(db.Boolean, default=True, nullable=False)
    rating = db.Column(db.Float, default=0.0, nullable=False)
    comments_count = db.Column(db.Integer, default=0, nullable=False)   


class Cinema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(300))
    halls = db.relationship("Hall", backref="cinema", lazy=True)
    screening_times = db.relationship("ScreeningTime", backref="cinema", lazy=True)


class Hall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cinema_id = db.Column(db.Integer, db.ForeignKey("cinema.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # e.g., A1, A2
    size = db.Column(db.Integer, nullable=False)  # Number of seats
    screening_times = db.relationship("ScreeningTime", backref="hall", lazy=True)


class ScreeningTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"), nullable=False)
    cinema_id = db.Column(db.Integer, db.ForeignKey("cinema.id"), nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey("hall.id"), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Float, nullable=False)
    bookings = db.relationship("Booking", backref="screening", lazy=True)
    seats = db.relationship("Seat", backref="screening", lazy=True)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    screening_id = db.Column(
        db.Integer, db.ForeignKey("screening_time.id"), nullable=False
    )
    seat_number = db.Column(db.String(10), nullable=False)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rate = db.Column(db.Float, nullable=False)

    @staticmethod
    def after_insert(mapper, connection, target):
        # 更新評論數和平均評分
        Movie.query.filter_by(id=target.movie_id).update(
            {
                "comments_count": Movie.comments_count + 1,
                "rating": db.session.query(db.func.avg(Review.rate))
                .filter(Review.movie_id == target.movie_id)
                .scalar() or 0.0
            }
        )

    @staticmethod
    def after_delete(mapper, connection, target):
        # 更新評論數和平均評分
        Movie.query.filter_by(id=target.movie_id).update(
            {
                "comments_count": Movie.comments_count - 1,
                "rating": db.session.query(db.func.avg(Review.rate))
                .filter(Review.movie_id == target.movie_id)
                .scalar() or 0.0
            }
        )

# 在Review類定義後添加事件監聽器
event.listen(Review, 'after_insert', Review.after_insert)
event.listen(Review, 'after_delete', Review.after_delete)


class Seat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    screening_id = db.Column(
        db.Integer, db.ForeignKey("screening_time.id"), nullable=False
    )
    seat_number = db.Column(db.String(10), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)


user_favorites = db.Table(
    "user_favorites",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("movie_id", db.Integer, db.ForeignKey("movie.id"), primary_key=True),
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
