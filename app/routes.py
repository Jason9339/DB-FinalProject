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
from app.models import User, Movie, Cinema, ScreeningTime, Booking, Friend, Review, Booking, Hall, Seat
from .models import User, FriendRequest, Review
from app.forms import RegistrationForm, LoginForm, BookingForm
from datetime import datetime
from sqlalchemy import and_, exists
from sqlalchemy.exc import IntegrityError
import os 
from werkzeug.utils import secure_filename
from flask import jsonify
from flask import session
from werkzeug.security import generate_password_hash

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
            login_user(user)  # 自动处理 session
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

@main.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    new_username = request.form.get('username')
    new_email = request.form.get('email')

    # 更新用戶資料
    current_user.username = new_username
    current_user.email = new_email
    try:
        db.session.commit()
        flash('資料已成功更新！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('更新失敗，請稍後再試。', 'danger')
        print(f"更新錯誤: {e}")

    return redirect(url_for('main.profile'))


@main.route('/profile', defaults={'username': None})
@main.route('/profile/<username>')
@login_required
def profile(username):
    if username:  # 如果 URL 中有 username，顯示該用戶的資料
        user = User.query.filter_by(username=username).first()  # 查找該用戶信息
        if not user:
            # 如果找不到該用戶，返回 404 錯誤
            return render_template('404.html'), 404
        # 傳遞該用戶收到的好友邀請
        received_requests = FriendRequest.query.filter_by(receiver_id=current_user.id, status='pending').all()
        return render_template('profile.html', user=user, friend_requests=received_requests)

    # 如果沒有提供 username，則顯示當前登入用戶的資料
    user = current_user  # 當前登入用戶
    # 傳遞當前用戶收到的好友邀請
    received_requests = FriendRequest.query.filter_by(receiver_id=current_user.id, status='pending').all()
    return render_template('profile.html', user=user, friend_requests=received_requests)
@main.route('/user_friends')
@login_required
def user_friends():
    # 获取当前用户的所有好友关系
    user_friends = Friend.query.filter(
        (Friend.user_id == current_user.id) | (Friend.friend_id == current_user.id)
    ).all()

    # 将好友关系分为 user 和 friend，并去重
    friends_set = set()
    for friend in user_friends:
        if friend.user_id == current_user.id:
            friends_set.add(friend.friend)
        else:
            friends_set.add(friend.user)

    # 转换为列表
    friends_list = list(friends_set)
    
    # 获取好友们收藏的电影
    friends_favorites = {}
    for friend in friends_list:
        # 获取该好友的收藏电影
        favorite_movies = friend.favorite_movies.all()
        friends_favorites[friend.id] = favorite_movies

    return render_template('user_friends.html', friends=friends_list, favorites=friends_favorites)

# 删除好友的路由
@main.route('/remove-friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    # 查找好友对象
    friend = User.query.get(friend_id)
    
    if friend:
        # 从当前用户的好友列表中移除
        Friend.query.filter(
            ((Friend.user_id == current_user.id) & (Friend.friend_id == friend.id)) |
            ((Friend.user_id == friend.id) & (Friend.friend_id == current_user.id))
        ).delete()
        
        db.session.commit()
        flash(f'你已成功删除 {friend.username} 作為好友。', 'success')
    else:
        flash('無法找到好友。', 'error')

    return redirect(url_for('main.user_friends'))

@main.route('/my_reviews')
@login_required
def my_reviews():
    reviews = current_user.reviews  # 假設 User 模型有 comments 屬性
    return render_template('my_reviews.html', reviews=reviews)

@main.route('/delete-review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    # 查找該條評論
    review = Review.query.get(review_id)
    
    if review:
        # 檢查是否是當前用戶的評論
        if review.user_id == current_user.id:
            db.session.delete(review)  # 刪除評論
            db.session.commit()  # 提交變更
            flash('Review deleted successfully!', 'success')
        else:
            flash('You do not have permission to delete this review.', 'error')
    else:
        flash('Review not found!', 'error')

    # 重定向回 "我的評論" 頁面
    return redirect(url_for('main.my_reviews'))

@main.route('/send-friend-request', methods=['POST'])
@login_required
def send_friend_request():
    # 使用 current_user 获取发送者 ID
    sender_id = current_user.id
    
    # 从请求中获取接收者的 UID
    data = request.json
    receiver_uid = data.get('uid')
    
    # 防止用户向自己发送好友请求
    if sender_id == receiver_uid:
        return jsonify({'error': '不能向自己发送好友邀请'}), 300
    
    # 查找接收者用户
    receiver = User.query.filter_by(id=receiver_uid).first()
    if not receiver:
        return jsonify({'error': '用户不存在'}), 400
    
    existing_friendship = Friend.query.filter(
        (Friend.user_id == sender_id) & (Friend.friend_id == receiver.id) |
        (Friend.user_id == receiver.id) & (Friend.friend_id == sender_id)
    ).first()

    if existing_friendship:
        return jsonify({'error': '你們已经是好友'}), 300

    # 检查是否已经存在未处理的好友邀请
    existing_request = FriendRequest.query.filter_by(
        sender_id=sender_id,
        receiver_id=receiver.id,
        status='pending'
    ).first()
    
    if existing_request:
        return jsonify({'error': '好友邀请已发送'}), 300
    
    # 创建新的好友邀请
    new_request = FriendRequest(
        sender_id=sender_id,
        receiver_id=receiver.id,
        status='pending'
    )
    db.session.add(new_request)
    db.session.commit()
    
    return jsonify({'message': '好友邀请已发送'}), 200

@main.route('/get-friend-requests', methods=['GET'])
@login_required
def get_friend_requests():
    # 使用 current_user 获取当前登录用户的 ID
    current_user_id = current_user.id
    
    # 查询当前用户收到的好友邀请，状态为 pending
    friend_requests = FriendRequest.query.filter_by(
        receiver_id=current_user_id,
        status='pending'
    ).all()
    
    # 构建返回数据
    data = [
        {
            'id': request.id,
            'sender_id': request.sender_id,
            'sender_username': User.query.get(request.sender_id).username  # 获取发送者的用户名
        }
        for request in friend_requests
    ]
    
    return jsonify({'requests': data}), 200

@main.route('/respond-friend-request', methods=['POST'])
def respond_friend_request():
    data = request.json
    request_id = data.get('request_id')
    action = data.get('action')  # 'accept' 或 'reject'

    # 验证好友邀请是否存在
    friend_request = FriendRequest.query.get(request_id)
    if not friend_request:
        return jsonify({'error': '好友邀請不存在'}), 404

    # 确认当前用户是接收者
    current_user_id = current_user.id
    if friend_request.receiver_id != current_user_id:
        return jsonify({'error': '無權操作此好友邀請'}), 403

    # 根据 action 执行相应操作
    if action == 'accept':
        # 更新好友邀请状态
        friend_request.status = 'accepted'

        # 添加到好友列表
        from app.models import Friend  # 确保导入 Friend 模型
        # 添加互为好友
        db.session.add(Friend(user_id=friend_request.sender_id, friend_id=friend_request.receiver_id))
        db.session.add(Friend(user_id=friend_request.receiver_id, friend_id=friend_request.sender_id))

        db.session.commit()

        # 使用 flash 显示提示信息
        flash(f"你已與 {friend_request.sender.username} 成為好友！", "success")
    elif action == 'reject':
        # 更新好友邀请状态
        friend_request.status = 'rejected'
    else:
        return jsonify({'error': '無效的操作'}), 400

    db.session.commit()
    return jsonify({'message': f'好友邀請已{action}'}), 200

@main.route('/profile_edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        if new_password:
            current_user.set_password(new_password)
            db.session.commit()
            flash('密碼已更新！', 'success')
            return redirect(url_for('main.profile'))  # 更新後跳轉到個人資料頁面
        else:
            flash('請輸入新密碼！', 'error')

    # 如果是 GET 請求，顯示編輯頁面
    return render_template('profile_edit.html')

@main.route('/edit_review/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    review = Review.query.get_or_404(review_id)
    
    # 確保只有評論的作者能夠編輯評論
    if review.user_id != current_user.id:
        flash('You do not have permission to edit this review.', 'error')
        return redirect(url_for('main.my_reviews'))

    if request.method == 'POST':
        # 獲取更新的內容
        new_content = request.form['content']
        new_rating = request.form['rating']
        
        # 更新評論
        review.content = new_content
        review.rate = new_rating
        db.session.commit()

        flash('Review updated successfully!', 'success')
        return redirect(url_for('main.my_reviews'))

    return render_template('edit_review.html', review=review)

@main.route('/get-booked-seats', methods=['GET'])
@login_required
def get_booked_seats():
    current_user_id = current_user.id
    bookings = Booking.query.filter_by(user_id=current_user_id).all()

    data = [
        {
            'id': booking.id,  # 添加 booking id
            'movie_title': Movie.query.get(booking.screening.movie_id).title,
            'seat_number': booking.seat_number,
            'screening_time': booking.screening.date.strftime('%Y-%m-%d %H:%M')
        }
        for booking in bookings
    ]
    
    return jsonify({'bookings': data}), 200

# 取消訂位的視圖
@main.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        # 查找訂位
        booking = Booking.query.get(booking_id)
        
        if not booking:
            if is_ajax:
                return jsonify({'success': False, 'error': '找不到此訂位'}), 404
            flash('找不到此訂位!', 'danger')
            return redirect(url_for('main.profile'))

        # 檢查訂位是否屬於當前用戶
        if booking.user_id != current_user.id:
            if is_ajax:
                return jsonify({'success': False, 'error': '無權取消此訂位'}), 403
            flash('無權取消此訂位!', 'danger')
            return redirect(url_for('main.profile'))

        # 刪除訂位
        try:
            db.session.delete(booking)
            db.session.commit()
            
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': '訂位已成功取消'
                })
            
            flash('訂位已取消!', 'success')
            return redirect(url_for('main.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"取消訂位時發生錯誤: {str(e)}")
            
            if is_ajax:
                return jsonify({
                    'success': False,
                    'error': '取消訂位時發生系統錯誤'
                }), 500
                
            flash('取消訂位失敗!', 'danger')
            return redirect(url_for('main.profile'))
            
    except Exception as e:
        current_app.logger.error(f"處理取消訂位請求時發生錯誤: {str(e)}")
        
        if is_ajax:
            return jsonify({
                'success': False,
                'error': '處理請求時發生錯誤'
            }), 500
            
        flash('處理請求時發生錯誤!', 'danger')
        return redirect(url_for('main.profile'))
    

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
        halls_data = request.form.getlist('hall') 

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
