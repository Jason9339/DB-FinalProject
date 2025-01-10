from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Movie, Cinema, ScreeningTime, Booking, Friend, Review
from app.forms import RegistrationForm, LoginForm, BookingForm
from .models import User, FriendRequest
from flask import jsonify
from flask import session
from werkzeug.security import generate_password_hash

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
            login_user(user)  # 自动处理 session
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
        flash(f'你已成功删除 {friend.username} 作为好友。', 'success')
    else:
        flash('无法找到该好友。', 'error')

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