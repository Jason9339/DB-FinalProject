# app/routes.py
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    jsonify,
)
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from flask import request, redirect, url_for
from app.models import User, Movie, Cinema, ScreeningTime, Booking, Review, Hall
from app.forms import RegistrationForm, LoginForm, BookingForm
from datetime import datetime
from sqlalchemy import and_, exists
from sqlalchemy.exc import IntegrityError
import os 
from werkzeug.utils import secure_filename
main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__)
import app

def update_movie_status():
    """
    更新電影的 is_current 狀態
    根據是否有未來的放映場次來判斷電影是否為當前上映中
    """
    current_time = datetime.now()
    
    # 找出所有電影
    movies = Movie.query.all()
    
    for movie in movies:
        # 檢查該電影是否有未來的放映場次
        has_future_screenings = db.session.query(exists().where(
            and_(
                ScreeningTime.movie_id == movie.id,
                ScreeningTime.date >= current_time
            )
        )).scalar()
        
        # 更新電影狀態
        if movie.is_current != has_future_screenings:
            movie.is_current = has_future_screenings
    
    # 提交所有更改
    try:
        db.session.commit()
        print(f"已更新所有電影狀態於 {current_time}")
    except Exception as e:
        db.session.rollback()
        print(f"更新電影狀態時發生錯誤: {str(e)}")

@main.before_request
def before_request():
    update_movie_status()

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

    bookings = Booking.query.filter_by(screening_id=screening_id).all()
    screening.cinema_id
    total_seats = (
        Hall.query.with_entities(Hall.size).filter_by(id=screening.hall.id).one()[0]
    )
    # 定義座位表（假設一個固定座位結構）
    seats_per_row = 10
    total_rows = total_seats // seats_per_row

    seating_chart = [  # 初始化座位表
        [
            {"seat_number": row * seats_per_row + seat + 1, "status": "available"}
            for seat in range(seats_per_row)
        ]
        for row in range(total_rows)
    ]
    # app.logging.debug(seating_chart)
    # 標記已預約的座位
    for booking in bookings:
        seat_number = int(booking.seat_number)
        row = (seat_number - 1) // seats_per_row
        seat = (seat_number - 1) % seats_per_row

        # 標記該座位為已預約
        if 0 <= row < total_rows and 0 <= seat < seats_per_row:
            seating_chart[row][seat]["status"] = "booked"
        else:
            print(f"Invalid seat number: {seat_number}")

    # 根據 screening_id 過濾相關資料並生成選項
    form.cinema.choices = [(screening.cinema.id, screening.cinema.name)]

    form.hall.choices = [(screening.hall.id, screening.hall.name)]

    form.movie.choices = [(screening.movie.id, screening.movie.title)]

    form.screening_time.choices = [(screening.id, screening.date)]
    bill_detail = {
        "name": User.query.filter_by(id=current_user.id).first().username,
        "cinema": screening.cinema.name,
        "hall": screening.hall.name,
        "movie": screening.movie.title,
        "id": [],
        "price": [],
    }
    if request.method == "POST":
        app.logging.debug(
            f"Form data: {request.form}"
        )  ## 還要設定 cinima 和 movie screening_time
        if form.validate_on_submit():
            # app.logging.debug(form.seat_number.data.split(','))
            for seat in form.seat_number.data.split(","):
                # Check if seat is already booked
                existing_booking = Booking.query.filter_by(
                    screening_id=screening_id, seat_number=seat
                ).first()

                if existing_booking:
                    flash("This seat is already booked", "danger")
                    return render_template(
                        "booking.html", form=form, screening=screening
                    )

                # Create new booking
                booking = Booking(
                    user_id=current_user.id,
                    screening_id=screening_id,
                    seat_number=seat,
                )
                db.session.add(booking)
                db.session.commit()
                flash("Booking successful!", "success")
                bill_detail["id"].append(booking.id)
                bill_detail["price"].append(
                    ScreeningTime.query.with_entities(ScreeningTime.price)
                    .filter_by(id=screening_id)
                    .one()[0]
                )

            # app.logging.debug(bill_detail)
            session["bill_detail"] = bill_detail
            return redirect(url_for("main.payment"))
        else:
            app.logging.debug(f"Form errors: {form.errors}")

    return render_template(
        "booking.html", form=form, screening=screening, seating_chart=seating_chart
    )


@main.route("/book/bill/", methods=["GET", "POST"])
@login_required
def payment():
    bill_detail = session.get("bill_detail", [])
    app.logging.debug(bill_detail)
    name = bill_detail["name"]
    ids = bill_detail["id"]
    price = bill_detail["price"]
    price_sum = sum(price)
    return render_template(
        "bill.html",
        name=name,
        book_id=ids,
        price=price,
        price_sum=price_sum,
        cinema=bill_detail["cinema"],
        hall=bill_detail["hall"],
        movie=bill_detail["movie"],
    )


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
    session.pop('_flashes', None)
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("main.home"))
        else:
            flash("Login unsuccessful. Please check email and password", "login_danger")
    return render_template("login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    session.pop('_flashes', None)
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


# Add these at the top of your routes.py file
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/insert', methods=['GET', 'POST'])
def insert_movie():  
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

        print("Form submitted")  # Debug print
        print(request.form)      # Debug print
        print(request.files)     # Debug print

        title = request.form.get('title')
        description = request.form.get('description')
        genre = request.form.get('genre')
        release_date = request.form.get('release_date')
        selected_cinema = request.form.get('cinema')

        # Handle file upload
        if 'poster_file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
            
        file = request.files['poster_file']
        
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Ensure filename is secure
            filename = secure_filename(file.filename)
            
            # Generate unique filename to prevent overwrites
            unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            
            # Ensure upload folder exists
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            try:
                # Save the file
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Generate the URL for the image to access it via static
                poster_url = url_for('static', filename=f'images/{unique_filename}')
                
            except Exception as e:
                flash(f'Error saving file: {str(e)}', 'error')
                return redirect(request.url)

        # Create new movie
        try:
            new_movie = Movie(
                title=title,
                description=description,
                genre=genre,
                release_date=release_date,
                poster_url=poster_url,
                rating=0,
                is_current=False
            )

            db.session.add(new_movie)
            db.session.commit()

            # Handle cinema and screening times
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
                                movie_id=new_movie.id,
                                cinema_id=cinema.id,
                                hall_id=hall.id,
                                date=time,
                                price=300
                            )
                        )

            db.session.add_all(screenings)
            db.session.commit()
            
            flash('Movie added successfully!', 'success')
            return redirect(url_for('main.admin_dashboard'))
            
        except Exception as e:
            print(f"Error details: {str(e)}")  # Debug print
            db.session.rollback()
            flash(f'Error adding movie: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('insert.html', cinemas=cinemas, cinema_movies=cinema_movies)

@main.route('/update', methods=['GET', 'POST'])
def update_movie():
    movies = Movie.query.all()
    selected_movie_id = request.args.get('movie')
    selected_movie = Movie.query.get(selected_movie_id) if selected_movie_id else None

    if request.method == 'POST' and selected_movie:
        selected_movie.title = request.form.get('title', selected_movie.title)
        selected_movie.description = request.form.get('description', selected_movie.description)
        selected_movie.genre = request.form.get('genre', selected_movie.genre)
        # Remove is_current update - it's handled automatically
        
        db.session.commit()

        flash(f"Movie '{selected_movie.title}' has been updated successfully.", "success")
        return redirect(url_for('main.admin_dashboard'))

    return render_template('update.html', movies=movies, selected_movie=selected_movie)

@main.route('/delete', methods=['GET', 'POST'])
def delete_movie():
    # Fetch all cinemas
    cinemas = Cinema.query.all()
    selected_cinema = request.args.get('cinema') or request.form.get('cinema')
    movies = []

    if selected_cinema:
        if selected_cinema == 'all':
            movies = Movie.query.all()
        else:
            cinema = Cinema.query.filter_by(name=selected_cinema).first()
            if cinema:
                screenings = ScreeningTime.query.filter_by(cinema_id=cinema.id).all()
                movies = {screening.movie for screening in screenings}
                movies = list(movies)

    if request.method == 'POST':
        movie_id = request.form.get('movie')
        if not selected_cinema:
            flash("Please select a cinema.", "error")
            return redirect(url_for('main.delete_movie'))

        if not movie_id:
            flash("Please select a movie to delete.", "error")
            return redirect(url_for('main.delete_movie', cinema=selected_cinema))

        movie_to_delete = Movie.query.get(movie_id)
        if not movie_to_delete:
            flash("Movie not found.", "error")
            return redirect(url_for('main.delete_movie', cinema=selected_cinema))

        cinema = Cinema.query.filter_by(name=selected_cinema).first()
        if not cinema:
            flash("Cinema not found.", "error")
            return redirect(url_for('main.delete_movie', cinema=selected_cinema))

        ScreeningTime.query.filter_by(movie_id=movie_to_delete.id, cinema_id=cinema.id).delete()
        remaining_screenings = ScreeningTime.query.filter_by(movie_id=movie_to_delete.id).count()

        if remaining_screenings == 0:
            db.session.delete(movie_to_delete)

        db.session.commit()
        flash(f"Movie '{movie_to_delete.title}' has been deleted from '{selected_cinema}'.", "success")
        return redirect(url_for('main.admin_dashboard'))

    return render_template('delete.html', cinemas=cinemas, movies=movies, selected_cinema=selected_cinema)


@main.route('/add_cinema', methods=['GET', 'POST'])
def add_cinema():
    if request.method == 'POST':
        # Get data from the form
        cinema_name = request.form.get('name')
        location = request.form.get('location')
        halls_data = request.form.getlist('halls') 

        # Validate input
        if not cinema_name or not location:
            flash("Cinema name and location are required.", "danger")
            return redirect(url_for('main.add_cinema'))

        # Check if the cinema already exists
        existing_cinema = Cinema.query.filter_by(name=cinema_name).first()
        if existing_cinema:
            flash("A cinema with this name already exists.", "danger")
            return redirect(url_for('main.add_cinema'))

        # Create a new cinema
        new_cinema = Cinema(name=cinema_name, location=location)

        # Add halls to the cinema
        for hall_data in halls_data:
            hall_name, hall_size = hall_data.split(',')  
            new_cinema.halls.append(Hall(name=hall_name.strip(), size=int(hall_size.strip())))

        # Add the new cinema to the database
        db.session.add(new_cinema)
        db.session.commit()

        flash(f"Cinema '{cinema_name}' has been added successfully.", "success")
        return redirect(url_for('main.admin_dashboard'))

    return render_template('add_cinema.html')

@main.route('/delete_cinema', methods=['GET', 'POST'])
def delete_cinema():
    # Fetch all cinemas for the dropdown
    cinemas = Cinema.query.all()

    if request.method == 'POST':
        # Get selected cinema ID from the form
        cinema_id = request.form.get('cinema')
        cinema_to_delete = Cinema.query.get_or_404(cinema_id)

        # Check if the cinema is playing any movies
        screenings = ScreeningTime.query.filter_by(cinema_id=cinema_to_delete.id).count()
        if screenings > 0:
            flash(f"Cannot delete cinema '{cinema_to_delete.name}' because it is playing movies.", "danger")
            return redirect(url_for('main.delete_cinema'))

        # Delete the cinema
        db.session.delete(cinema_to_delete)
        db.session.commit()

        flash(f"Cinema '{cinema_to_delete.name}' has been deleted successfully.", "success")
        return redirect(url_for('main.admin_dashboard'))

    return render_template('delete_cinema.html', cinemas=cinemas)

@main.route('/add_screeningtime', methods=['GET', 'POST'])
def add_screeningtime():
    # Fetch all cinemas for the dropdown
    cinemas = Cinema.query.all()

    # Get selected cinema from the query parameters
    selected_cinema_name = request.args.get('cinema')
    selected_cinema = None
    movies = []

    # If a cinema is selected, fetch its movies
    if selected_cinema_name:
        selected_cinema = Cinema.query.filter_by(name=selected_cinema_name).first()
        if selected_cinema:
            # Fetch movies currently being screened in the selected cinema
            screenings = ScreeningTime.query.filter_by(cinema_id=selected_cinema.id).all()
            movies = {screening.movie for screening in screenings}  # Unique movies
            movies = list(movies)  # Convert to a list for rendering

    if request.method == 'POST':
        # Handle form submission
        movie_id = request.form.get('movie')
        cinema_id = request.form.get('cinema_id')
        hall_id = request.form.get('hall')
        date = request.form.get('date')
        price = request.form.get('price')

        # Validate and process the date
        try:
            screening_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            flash("Invalid date format. Use 'YYYY-MM-DD HH:MM:SS'.", "danger")
            return redirect(url_for('main.add_screeningtime', cinema=cinema_id))

        # Check if the screening already exists
        existing_screening = ScreeningTime.query.filter_by(
            movie_id=movie_id,
            cinema_id=cinema_id,
            hall_id=hall_id,
            date=screening_date
        ).first()

        if existing_screening:
            flash("This screening time already exists.", "danger")
        else:
            # Create and add the new screening
            new_screening = ScreeningTime(
                movie_id=movie_id,
                cinema_id=cinema_id,
                hall_id=hall_id,
                date=screening_date,
                price=price
            )
            db.session.add(new_screening)
            db.session.commit()
            flash("Screening time added successfully.", "success")

        return redirect(url_for('main.admin_dashboard'))

    return render_template(
        'add_screeningtime.html',
        cinemas=cinemas,
        movies=movies,
        selected_cinema=selected_cinema
    )
