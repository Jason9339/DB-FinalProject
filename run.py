# run.py
from app import create_app, db
from app.seed import init_db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        init_db()  # 初始化示例數據
    app.run(debug=True, host='0.0.0.0', port=5000)
