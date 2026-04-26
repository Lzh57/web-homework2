import os
import json
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'any_secret_string'

# --- 1. 檔案路徑定義 ---
USER_DATA_FILE = 'users.json'

# --- 2. 輔助函式 ---

def init_json_file(file_path: str) -> None:
    """初始化 JSON 檔案，若不存在則建立並寫入預設 admin 資料"""
    if not os.path.exists(file_path):
        initial_data = {
            "users": [
                {
                    "username": "admin",
                    "email": "admin@example.com",
                    "password": "admin123",
                    "phone": "0912345678",
                    "birthdate": "1990-01-01"
                }
            ]
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=4, ensure_ascii=False)


def read_users(file_path: str) -> dict:
    """讀取 users.json，回傳 dict；若檔案不存在或格式錯誤則回傳空清單"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": []}
    except json.JSONDecodeError:
        return {"users": []}


def save_users(file_path: str, data: dict) -> bool:
    """將資料寫回 JSON，成功回傳 True，失敗回傳 False"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except (PermissionError, OSError):
        return False


def validate_register(form_data: dict, users: list) -> dict:
    """
    驗證註冊表單資料。
    回傳 {"success": True, "data": {...}} 或 {"success": False, "error": "訊息"}
    """
    username = form_data.get("username", "").strip()
    email = form_data.get("email", "").strip()
    password = form_data.get("password", "").strip()
    phone = form_data.get("phone", "").strip()
    birthdate = form_data.get("birthdate", "").strip()

    # 必填欄位
    if not username or not email or not password or not birthdate:
        return {"success": False, "error": "帳號、Email、密碼、出生日期為必填欄位"}

    # Email 格式
    if "@" not in email or "." not in email:
        return {"success": False, "error": "Email 格式不正確，需包含 @ 與 ."}

    # 密碼長度
    if not (6 <= len(password) <= 16):
        return {"success": False, "error": "密碼長度需介於 6 至 16 字元"}

    # 電話選填驗證
    if phone:
        if not (phone.isdigit() and len(phone) == 10 and phone.startswith("09")):
            return {"success": False, "error": "電話需為 10 碼數字且開頭為 09"}

    # 帳號與 Email 重複檢查
    for user in users:
        if user["username"] == username:
            return {"success": False, "error": "帳號已被使用"}
        if user["email"] == email:
            return {"success": False, "error": "Email 已被使用"}

    return {
        "success": True,
        "data": {
            "username": username,
            "email": email,
            "password": password,
            "phone": phone,
            "birthdate": birthdate
        }
    }


def verify_login(email: str, password: str, users: list) -> dict:
    """
    驗證登入的 Email 與密碼。
    回傳 {"success": True, "data": {...}} 或 {"success": False, "error": "訊息"}
    """
    for user in users:
        if user["email"] == email and user["password"] == password:
            return {"success": True, "data": user}
    return {"success": False, "error": "Email 或密碼錯誤"}


# --- 3. 自訂過濾器 ---

@app.template_filter('mask_phone')
def mask_phone(phone: str) -> str:
    """將電話中間四碼遮罩，例如 0912345678 → 0912****78"""
    if phone and len(phone) == 10:
        return phone[:4] + "****" + phone[8:]
    return phone


@app.template_filter('format_tw_date')
def format_tw_date(date_str: str) -> str:
    """將西元年日期字串轉為民國年，例如 1990-01-01 → 民國 79 年 01 月 01 日"""
    try:
        year, month, day = date_str.split("-")
        tw_year = int(year) - 1911
        return f"民國 {tw_year} 年 {month} 月 {day} 日"
    except Exception:
        return date_str


# --- 4. 初始化（模組層級）---
init_json_file(USER_DATA_FILE)


# --- 5. 路由 ---

@app.route('/')
def index():
    """首頁，提供登入與註冊連結"""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register_route():
    """註冊頁面：GET 顯示表單，POST 驗證並寫入資料"""
    if request.method == 'POST':
        form_data = {
            "username": request.form.get("username", "").strip(),
            "email": request.form.get("email", "").strip(),
            "password": request.form.get("password", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "birthdate": request.form.get("birthdate", "").strip(),
        }
        data = read_users(USER_DATA_FILE)
        result = validate_register(form_data, data["users"])

        if result["success"]:
            data["users"].append(result["data"])
            save_users(USER_DATA_FILE, data)
            return redirect(url_for('login_route'))
        else:
            return redirect(url_for('error_route', message=result["error"]))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        data = read_users(USER_DATA_FILE)
        result = verify_login(email, password, data["users"])

        if result["success"]:
            # --- 修改部分：存入 Session ---
            user_data = result["data"]
            session['username'] = user_data['username']
            session['is_admin'] = (user_data['username'] == 'admin')
            # 導向公告頁
            return redirect(url_for('announcement')) 
        else:
            return redirect(url_for('error_route', message=result["error"]))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # 清除所有 session 資料
    return redirect(url_for('index'))

@app.route('/announcement')
@app.route('/announcement')
def announcement():
    if 'username' not in session:
        return redirect(url_for('error_route', message="請先登入"))
    
    # --- 新增這兩行：讀取目前登入者的資料 ---
    data = read_users(USER_DATA_FILE)
    user = next((u for u in data["users"] if u["username"] == session['username']), None)
    
    # --- 修改這行：把 user 變數傳給 HTML ---
    return render_template('announcement.html', user=user)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('error_route', message="請先登入"))

    data = read_users(USER_DATA_FILE)
    # 找目前登入的這個人
    user = next((u for u in data["users"] if u["username"] == session['username']), None)
    
    if request.method == 'POST':
        new_email = request.form.get("email", "").strip()
        new_phone = request.form.get("phone", "").strip()
        new_birthdate = request.form.get("birthdate", "").strip()
        new_password = request.form.get("password", "").strip()

        # Email 重複檢查 (排除自己)
        for u in data["users"]:
            if u["email"] == new_email and u["username"] != session['username']:
                return redirect(url_for('error_route', message="Email 已被其他會員使用"))

        # 更新資料
        user['email'] = new_email
        user['phone'] = new_phone
        user['birthdate'] = new_birthdate
        if new_password: # 有填才改密碼
            user['password'] = new_password
        
        save_users(USER_DATA_FILE, data)
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


@app.route('/users/<username>/edit', methods=['GET', 'POST'])
def edit_user_route(username):
    if not session.get('is_admin'):
        return redirect(url_for('error_route', message="無權限訪問"))

    data = read_users(USER_DATA_FILE)
    user = next((u for u in data["users"] if u["username"] == username), None)

    if request.method == 'POST':
        user['phone'] = request.form.get("phone", "").strip()
        user['birthdate'] = request.form.get("birthdate", "").strip()
        new_pw = request.form.get("password", "").strip()
        if new_pw:
            user['password'] = new_pw
        
        save_users(USER_DATA_FILE, data)
        return redirect(url_for('users_list_route'))

    return render_template('edit_user.html', user=user)

@app.route('/users/<username>/delete', methods=['POST']) # 必須是 POST
def delete_user_route(username):
    if not session.get('is_admin'):
        return redirect(url_for('error_route', message="無權限訪問"))

    # 不能刪除 admin 或 自己
    if username == 'admin' or username == session.get('username'):
        return redirect(url_for('error_route', message="不可刪除此管理員帳號"))

    data = read_users(USER_DATA_FILE)
    data["users"] = [u for u in data["users"] if u["username"] != username]
    save_users(USER_DATA_FILE, data)
    return redirect(url_for('users_list_route'))


@app.route('/users')
def users_list_route():
    # 檢查是否為 admin
    if not session.get('is_admin'):
        return redirect(url_for('error_route', message="無權限訪問"))
    
    data = read_users(USER_DATA_FILE)
    return render_template('users.html', users=data["users"])


@app.route('/error')
def error_route():
    """統一錯誤頁，接收 message 參數並顯示"""
    msg = request.args.get('message', '未知錯誤')
    return render_template('error.html', message=msg)


