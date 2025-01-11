# DB-FinalProject

## Project Structure

```
DB-FinalProject/
│
├── app/
│   ├── __init__.py     # 初始化 Flask 應用
│   ├── models.py       # 資料庫模型
│   ├── routes.py       # 路由邏輯
│   └── forms.py        # 表單處理
│   └── seed.py         # 初始化資料
│
├── static/
│   ├── css/
│   │   └── main.css    # 自定義樣式
│   ├── js/
│   │   └── main.js     # 自定義腳本
│   └── images/         # 圖片資源
│
├── templates/
│   ├── base.html       # 母版頁面
│   ├── home.html       # 首頁
│   ├── login.html      # 登入頁面
│   └── register.html   # 註冊頁面
│
├── instance/
│   └── movie_database.db  # SQLite 資料庫
│
├── config.py           # 設定檔案
├── run.py              # 啟動 Flask 應用
├── requirements.txt    # Python 依賴項
└── README.md           # 專案說明文件
```

## 資料庫查看

若要查看資料庫內容，請下載 [DB Browser for SQLite](https://sqlitebrowser.org/)，並開啟 `instance` 目錄中的 `movie_database.db` 檔案。

## 專案設置步驟

1. clone repository

   ```bash
   git clone https://github.com/your-username/DB-FinalProject.git
   cd DB-FinalProject
   ```

2. 創建虛擬環境

   ```bash
   python -m venv venv
   source venv/bin/activate  # 在 Windows 上使用 `venv\Scripts\activate`
   ```

3. 安裝依賴

   ```bash
   pip install -r requirements.txt
   ```

4. 運行應用
   ```bash
   python run.py
   ```

## 功能特點

- Flask Web 應用
- SQLite 資料庫
- 使用者認證系統
- 響應式設計

## 技術

- Python
- Flask
- SQLite
- HTML/CSS
- JavaScript
