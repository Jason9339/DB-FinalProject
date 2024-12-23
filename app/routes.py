# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Movie, Cinema, ScreeningTime, Booking, Review
from app.forms import RegistrationForm, LoginForm, BookingForm
from datetime import datetime

main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__)


@main.route("/")
def home():
    movies = Movie.query.filter_by(is_current=True).limit(6).all()
    # top_rated_movies = Movie.query.order_by(Movie.rating.desc()).limit(6).all()
    # most_commented_movies = (
    #     Movie.query.order_by(Movie.comments_count.desc()).limit(6).all()
    # )

    return render_template(
        "home.html",
        movies=movies,
        top_rated_movies=[],
        most_commented_movies=[],
    )


@main.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    current_time = datetime.now()
    reviews = (
        Review.query.filter_by(movie_id=movie_id)
        .join(User, Review.user_id == User.id)
        .add_columns(User.username, Review.content, Review.rate)
        .all()
    )
    average_rating = (
        db.session.query(db.func.avg(Review.rate))
        .filter(Review.movie_id == movie_id)
        .scalar()
    )
    average_rating = round(average_rating, 1) if average_rating else 0
    screenings = ScreeningTime.query.filter(
        ScreeningTime.movie_id == movie_id,
        ScreeningTime.date >= current_time  
    ).all()
    return render_template("movie_detail.html", movie=movie, reviews=reviews, screenings=screenings, average_rating=average_rating)


@main.route("/favorite/<int:movie_id>", methods=["POST"])
@login_required
def toggle_favorite(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if movie in current_user.favorite_movies:
        current_user.favorite_movies.remove(movie)
    else:
        current_user.favorite_movies.append(movie)
    db.session.commit()
    return redirect(url_for("main.movie_detail", movie_id=movie_id))


@main.route("/book/<int:screening_id>", methods=["GET", "POST"])
@login_required
def book_seat(screening_id):
    screening = ScreeningTime.query.get_or_404(screening_id)
    form = BookingForm()

    if form.validate_on_submit():
        # Check if seat is already booked
        existing_booking = Booking.query.filter_by(
            screening_id=screening_id, seat_number=form.seat_number.data
        ).first()

        if existing_booking:
            flash("This seat is already booked", "danger")
            return render_template("booking.html", form=form, screening=screening)

        # Create new booking
        booking = Booking(
            user_id=current_user.id,
            screening_id=screening_id,
            seat_number=form.seat_number.data,
        )
        db.session.add(booking)
        db.session.commit()
        flash("Booking successful!", "success")
        return redirect(url_for("main.home"))

    return render_template("booking.html", form=form, screening=screening)


@auth.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful!", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("main.home"))
        else:
            flash("Login unsuccessful. Please check email and password", "danger")
    return render_template("login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.home"))


@main.route("/search")
def search():
    query = request.args.get("query", "")
    if query:
        movies = Movie.query.filter(Movie.title.ilike(f"%{query}%")).all()
    else:
        movies = []
    return render_template("search_results.html", movies=movies, query=query)


@main.route('/submit_review/<int:movie_id>', methods=['POST'])
@login_required
def submit_review(movie_id):
    try:
        rate = float(request.form.get('rate'))
        review_content = request.form.get('review')

        if not (0.5 <= rate <= 5.0):
            flash("Rate must be between 0.5 and 5.0.", "error")
            return redirect(url_for('main.movie_detail', movie_id=movie_id))

        if not review_content.strip():
            flash("Review content cannot be empty.", "error")
            return redirect(url_for('main.movie_detail', movie_id=movie_id))
    except ValueError:
        flash("Invalid rating value.", "error")
        return redirect(url_for('main.movie_detail', movie_id=movie_id))

    new_review = Review(
        user_id=current_user.id,
        movie_id=movie_id,
        content=review_content.strip(),
        rate=rate,
    )
    db.session.add(new_review)
    db.session.commit()

    flash("Your review has been submitted successfully!", "success")
    return redirect(url_for('main.movie_detail', movie_id=movie_id))
