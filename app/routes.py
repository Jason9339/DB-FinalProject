from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Movie, Cinema, ScreeningTime, Booking
from app.forms import RegistrationForm, LoginForm, BookingForm

main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__)


@main.route("/")
def home():
    movies = Movie.query.filter_by(is_current=True).limit(10).all()
    top_rated_movies = Movie.query.order_by(Movie.rating.desc()).limit(5).all()
    most_commented_movies = (
        Movie.query.order_by(Movie.comments_count.desc()).limit(5).all()
    )

    return render_template(
        "home.html",
        movies=movies,
        top_rated_movies=top_rated_movies,
        most_commented_movies=most_commented_movies,
    )


@main.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    screenings = ScreeningTime.query.filter_by(movie_id=movie_id).all()
    return render_template("movie_detail.html", movie=movie, screenings=screenings)


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
        existing_booking = Booking.query.filter_by(
            screening_id=screening_id, seat_number=form.seat_number.data
        ).first()

        if existing_booking:
            flash("This seat is already booked", "danger")
            return render_template("booking.html", form=form, screening=screening)

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
    # if form.validate_on_submit():
    #     # admin=User.query.filter_by(email=form.email.data).first()
    #     # Special case: Check for admin credentials
    #     # login_user(admin)
    #     if form.email.data == "admin@example.com" and form.password.data == "admin123":
    #         # Redirect to admin dashboard if credentials match
    #         return redirect(url_for("main.admin_dashboard"))

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

@main.route("/admin", endpoint="admin_dashboard")
@login_required
def admin_dashboard():
    # Ensure only admin users can access this route
    if current_user.username != "admin":
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for("main.home"))

    # Fetch all cinemas and group movies by cinema
    cinemas = Cinema.query.all()
    cinema_movies = {}
    for cinema in cinemas:
        screening_times = ScreeningTime.query.filter_by(cinema_id=cinema.id).all()
        movies = {
            screening.movie
            for screening in screening_times
            if screening.movie.is_current
        }
        cinema_movies[cinema.name] = list(movies)
    return render_template("admin.html", cinema_movies=cinema_movies)


@main.route("/movies/showing")
def movies_showing():
    page = request.args.get("page", 1, type=int)
    per_page = 12
    movies_query = Movie.query.filter(Movie.is_current == True).order_by(
        Movie.release_date.desc()
    )
    movies = movies_query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template("movies_showing.html", movies=movies)


@main.route("/movies/top-rated")
def top_rated_movies():
    page = request.args.get("page", 1, type=int)
    per_page = 12
    movies_query = Movie.query.order_by(Movie.rating.desc())
    movies = movies_query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template("top_rated_movies.html", movies=movies)


@main.route("/movies/most-commented")
def most_commented_movies():
    page = request.args.get("page", 1, type=int)
    per_page = 12
    movies_query = Movie.query.order_by(Movie.comments_count.desc())
    movies = movies_query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template("most_commented_movies.html", movies=movies)


@main.route("/cinemas")
def cinemas():
    cinemas = Cinema.query.all()
    return render_template("cinemas.html", cinemas=cinemas)


@main.route("/cinema/<int:cinema_id>/screenings")
def cinema_screenings(cinema_id):
    cinema = Cinema.query.get_or_404(cinema_id)
    screenings = ScreeningTime.query.filter_by(cinema_id=cinema_id).all()
    return render_template(
        "cinema_screenings.html", cinema=cinema, screenings=screenings
    )


@main.route("/my-list")
@login_required
def my_list():
    favorite_movies = current_user.favorite_movies
    return render_template("my_list.html", favorite_movies=favorite_movies)
from datetime import datetime, timedelta

def insert_create_fixed_screening_times(movies, cinemas):
    """Create fixed screening times for insert movie in choosen cinemas."""
    screenings = []
    fixed_times = [
        datetime.now().replace(hour=10, minute=0),
        datetime.now().replace(hour=14, minute=0),
        datetime.now().replace(hour=18, minute=0),
    ]
    for i, movie in enumerate(movies):
        for cinema in cinemas:
            for hall in cinema.halls:  # Assuming each cinema has `halls` as an attribute
                for time in fixed_times:
                    screenings.append(
                        ScreeningTime(
                            movie_id=movie.id,
                            cinema_id=cinema.id,
                            hall_id=hall.id,
                            date=time + timedelta(days=i % 7),
                            price=300 + (i % 5) * 10,  # Adjust pricing logic as needed
                        )
                    )
    return screenings

@main.route('/insert', methods=['GET', 'POST'])
def insert_movie():
    # Fetch all cinemas
    cinemas = Cinema.query.all()
    cinema_movies = {}
    for cinema in cinemas:
        screening_times = ScreeningTime.query.filter_by(cinema_id=cinema.id).all()
        movies = {
            screening.movie
            for screening in screening_times
            if screening.movie.is_current
        }
        cinema_movies[cinema.name] = list(movies)

    if request.method == 'POST':
        # Handle form submission
        title = request.form.get('title')
        description = request.form.get('description')
        genre = request.form.get('genre')
        release_date = request.form.get('release_date')
        poster_url = f"/static/images/{request.form.get('poster_url', '').strip()}"
        is_current = request.form.get('is_current') == 'true'
        selected_cinema = request.form.get('cinema')  # Get the selected cinema

        # Create a new Movie instance
        new_movie = Movie(
            title=title,
            description=description,
            genre=genre,
            release_date=release_date,
            poster_url=poster_url,
            rating=0,
            is_current=is_current
        )

        # Save the new movie to the database to generate its ID
        db.session.add(new_movie)
        db.session.commit()  # Commit to assign an ID to new_movie

        # Generate fixed screening times for the new movie
        selected_cinemas = (
            cinemas if selected_cinema == 'all'
            else [cinema for cinema in cinemas if cinema.name == selected_cinema]
        )

        screenings = []
        fixed_times = [
            datetime.now().replace(hour=10, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=14, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=18, minute=0, second=0, microsecond=0),
        ]
        for cinema in selected_cinemas:
            for hall in cinema.halls:
                for time in fixed_times:
                    screenings.append(
                        ScreeningTime(
                            movie_id=new_movie.id,  # Use the ID of the committed movie
                            cinema_id=cinema.id,
                            hall_id=hall.id,
                            date=time,
                            price=300  # Set a fixed price
                        )
                    )

        # Save the screenings to the database
        db.session.add_all(screenings)
        db.session.commit()

        return redirect(url_for('main.admin_dashboard'))  # Redirect to admin page after successful insertion

    # Render the insert.html template for GET requests
    return render_template('insert.html', cinemas=cinemas, cinema_movies=cinema_movies)


@main.route('/delete', methods=['GET', 'POST'])
def delete_movie():
    # Fetch all cinemas
    cinemas = Cinema.query.all()

    # Get selected cinema from query parameters or form data
    selected_cinema = request.args.get('cinema') or request.form.get('cinema')

    # Initialize movies list
    movies = []
    if selected_cinema:
        if selected_cinema == 'all':
            # Fetch all movies when "All" is selected
            movies = Movie.query.all()
        else:
            # Fetch movies specific to the selected cinema
            cinema = Cinema.query.filter_by(name=selected_cinema).first()
            if cinema:
                screenings = ScreeningTime.query.filter_by(cinema_id=cinema.id).all()
                movies = {screening.movie for screening in screenings}
                movies = list(movies)  # Convert to a list for rendering in the template

    if request.method == 'POST':
        # Handle deletion logic
        movie_id = request.form.get('movie')
        movie_to_delete = Movie.query.get(movie_id)

        if not movie_to_delete:
            flash("Movie not found", "error")
            return redirect(url_for('main.delete_movie', cinema=selected_cinema))

        # Delete screenings only for the selected cinema
        cinema = Cinema.query.filter_by(name=selected_cinema).first()
        if not cinema:
            flash("Cinema not found", "error")
            return redirect(url_for('main.delete_movie', cinema=selected_cinema))

        ScreeningTime.query.filter_by(movie_id=movie_to_delete.id, cinema_id=cinema.id).delete()

        # Check if the movie has screenings in other cinemas
        remaining_screenings = ScreeningTime.query.filter_by(movie_id=movie_to_delete.id).count()
        if remaining_screenings == 0:
            db.session.delete(movie_to_delete)
        db.session.commit()
        flash(f"Movie '{movie_to_delete.title}' has been deleted from '{selected_cinema}'.", "success")

        return redirect(url_for('main.admin_dashboard'))

    return render_template('delete.html', cinemas=cinemas, movies=movies, selected_cinema=selected_cinema)


@main.route('/update', methods=['GET', 'POST'])
def update_movie():
    # Logic to handle updating movies (if needed)
    return render_template('update.html')
