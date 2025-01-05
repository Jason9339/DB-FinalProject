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

@main.route('/cinemas')
def cinemas():
    cinemas = Cinema.query.all()
    return render_template('cinemas.html', cinemas=cinemas)

@main.route('/cinema/<int:cinema_id>/screenings')
def cinema_screenings(cinema_id):
    cinema = Cinema.query.get_or_404(cinema_id)
    screenings = ScreeningTime.query.filter_by(cinema_id=cinema_id).all()
    return render_template('cinema_screenings.html', cinema=cinema, screenings=screenings)

@main.route("/my-list")
@login_required
def my_list():
    favorite_movies = current_user.favorite_movies
    return render_template("my_list.html", favorite_movies=favorite_movies)

@main.route('/update_status', methods=['POST'])
@login_required
def update_status():
    status = request.form.get('status')
    current_user.status = status
    db.session.commit()
    flash('狀態更新成功！', 'success')
    return redirect(url_for('main.profile')) 

@main.route('/profile')
@login_required
def profile():
    upcoming_movies = Movie.query.filter(Movie.is_current == False).order_by(Movie.release_date).all()
    return render_template('profile.html', user=current_user, upcoming_movies=upcoming_movies)

@main.route('/favorite_movies')
@login_required
def favorite_movies():
    favorite_movie_ids = db.session.query(user_favorites.c.movie_id).filter_by(user_id=current_user.id).all()
    favorite_movie_ids = [movie_id[0] for movie_id in favorite_movie_ids]  
    movies = Movie.query.filter(Movie.id.in_(favorite_movie_ids)).all()
    return render_template('favorite_movies.html', movies=movies)

@main.route('/user_friends')
@login_required
def user_friends():
    user_friends = current_user.friends  # 需要確保 User 模型有這個屬性
    return render_template('user_friends.html', friends=user_friends)

@main.route('/my_reviews')
@login_required
def my_reviews():
    reviews = current_user.reviews  # 假設 User 模型有 comments 屬性
    return render_template('my_reviews.html', reviews=reviews)

@main.route("/add_friend", methods=["GET", "POST"])
@login_required
def add_friend():
    form = AddFriendForm()
    if form.validate_on_submit():
        friend = User.query.filter_by(email=form.friend_email.data).first()
        if not friend:
            flash("User not found", "error")
            return redirect(url_for("add_friend"))
        if current_user.is_friend(friend):
            flash("You are already friends with this user", "info")
        else:
            current_user.add_friend(friend)
            db.session.commit()
            flash(f"You are now friends with {friend.username}!", "success")
        return redirect(url_for("add_friend"))
    return render_template("add_friend.html", form=form)

@main.route('/send-friend-request', methods=['POST'])
def send_friend_request():
    data = request.json
    user_id = data.get('user_id')
    if user_id not in users:
        return jsonify({'error': 'User not found'}), 404
    # 假設 current_user 是已登入用戶的 ID
    current_user = '123'
    if user_id == current_user:
        return jsonify({'error': '不能添加自己為好友'}), 400
    # 新增好友邀請
    friend_requests.setdefault(user_id, []).append(current_user)
    return jsonify({'message': f'好友邀請已發送給 {users[user_id]}'}), 200

@main.route('/accept-friend-request', methods=['POST'])
def accept_friend_request():
    data = request.json
    user_id = data.get('user_id')
    # 假設 current_user 是已登入用戶的 ID
    current_user = '123'
    if user_id not in friend_requests or current_user not in friend_requests[user_id]:
        return jsonify({'error': '無效的好友邀請'}), 404
    # 接受好友邀請（假設有一個 friends 資料結構）
    friends = {current_user: []}  # 模擬的好友列表
    friends.setdefault(current_user, []).append(user_id)
    friends.setdefault(user_id, []).append(current_user)
    # 移除好友邀請
    friend_requests[user_id].remove(current_user)
    if not friend_requests[user_id]:
        del friend_requests[user_id]
    return jsonify({'message': f'你已接受來自 {users[user_id]} 的好友邀請'}), 200
