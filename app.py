import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# Flask uygulaması
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # Güvenlik anahtarı

# Veritabanı bağlantısı
DATABASE = 'users.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)  # Timeout set to 10 seconds
    conn.row_factory = sqlite3.Row
    return conn


# Veritabanı başlatma fonksiyonu
def init_db():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email TEXT NOT NULL,
                            username TEXT NOT NULL,
                            password TEXT NOT NULL
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS finances (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            transaction_name TEXT NOT NULL,
                            transaction_type TEXT NOT NULL,  -- 'income' or 'expense'
                            transaction_date TEXT NOT NULL,
                            amount REAL NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES users (id)
                        )''')
        conn.commit()
    except sqlite3.Error as e:
        flash(f"Error initializing database: {e}", 'error')
    finally:
        conn.close()


# Ana Sayfa
@app.route('/')
def index():
    return render_template('index.html')


# Kayıt Sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Şifre doğrulama
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))

        # Şifreyi hash'leyerek kaydet
        hashed_password = generate_password_hash(password)

        # Veritabanı bağlantısı
        conn = get_db_connection()
        cursor = conn.cursor()

        # E-posta ve kullanıcı adı kontrolü
        cursor.execute("SELECT * FROM users WHERE email = ? OR username = ?", (email, username))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email or username already exists.', 'error')
            conn.close()
            return redirect(url_for('register'))

        # Kullanıcıyı veritabanına ekle
        cursor.execute("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", (email, username, hashed_password))
        conn.commit()
        conn.close()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Login Sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form['email_or_username']
        password = request.form['password']

        # Veritabanı bağlantısı
        conn = get_db_connection()
        cursor = conn.cursor()

        # Kullanıcı adı veya e-posta ile sorgulama
        cursor.execute("SELECT * FROM users WHERE email = ? OR username = ?", (email_or_username, email_or_username))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            flash('Login successful!', 'success')
            session['user_id'] = user['id']  # Kullanıcı ID'sini oturuma kaydet
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email/username or password.', 'error')
            conn.close()
            return redirect(url_for('login'))

    return render_template('login.html')


# Dashboard Sayfası
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()

    cursor.execute("""
    SELECT transaction_name, transaction_type, transaction_date, amount, id
    FROM finances
    WHERE user_id = ?
    """, (session['user_id'],))

    finance_entries = cursor.fetchall()

    formatted_entries = []
    transaction_colors = []  # Renkleri burada hazırlayın
    for entry in finance_entries:
        formatted_entry = dict(entry)
        formatted_entry['formatted_amount'] = f"{formatted_entry['amount']:,.2f}"
        formatted_entries.append(formatted_entry)

        # Renk ataması
        if formatted_entry['transaction_type'] == 'income':
            transaction_colors.append('rgb(75, 192, 192)')  # Gelir için yeşil
        else:
            transaction_colors.append('rgb(255, 99, 132)')  # Gider için kırmızı

    total_income = sum(entry['amount'] for entry in finance_entries if entry['transaction_type'] == 'income')
    total_expenses = sum(entry['amount'] for entry in finance_entries if entry['transaction_type'] == 'expense')
    net_total = total_income - total_expenses

    conn.close()

    return render_template('dashboard.html',
                           user=user,
                           finance_entries=formatted_entries,
                           total_income=f"{total_income:,.2f}",
                           total_expenses=f"{total_expenses:,.2f}",
                           net_total=f"{net_total:,.2f}",
                           transaction_colors=transaction_colors)  # Renkleri şablona gönderin

# Veritabanında işlem silme
@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Veritabanından silme işlemi
    cursor.execute("DELETE FROM finances WHERE id = ? AND user_id = ?", (transaction_id, session['user_id']))
    conn.commit()
    conn.close()

    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('dashboard'))
from datetime import datetime
from datetime import datetime

@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Ensure user is logged in

    # Get today's date in YYYY-MM-DD format
    today_date = datetime.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        transaction_name = request.form['transaction_name']
        amount = request.form['amount']
        transaction_type = 'income'  # Since it's income
        transaction_date = request.form['transaction_date']

        # Validate amount is a valid positive number
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Income must be a positive number.', 'error')
                return redirect(url_for('add_income'))
        except ValueError:
            flash('Invalid amount. Please enter a valid number.', 'error')
            return redirect(url_for('add_income'))

        # Validate the date format (YYYY-MM-DD)
        try:
            datetime.strptime(transaction_date, '%Y-%m-%d')  # Check if date is in the correct format
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('add_income'))

        # Insert the income entry into the finances table
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO finances (user_id, transaction_name, transaction_type, transaction_date, amount)
            VALUES (?, ?, ?, ?, ?)
        """, (session['user_id'], transaction_name, transaction_type, transaction_date, amount))

        conn.commit()
        conn.close()

        flash('Income added successfully!', 'success')
        return redirect(url_for('dashboard'))  # Redirect to the dashboard

    return render_template('add_income.html', today_date=today_date)


@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Ensure the user is logged in

    # Get today's date in YYYY-MM-DD format
    today_date = datetime.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        transaction_name = request.form['transaction_name']
        amount = request.form['amount']
        transaction_type = 'expense'  # Since it's an expense
        transaction_date = request.form['transaction_date']

        # Validate amount is a valid positive number
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Expense must be a positive number.', 'error')
                return redirect(url_for('add_expense'))
        except ValueError:
            flash('Invalid amount. Please enter a valid number.', 'error')
            return redirect(url_for('add_expense'))

        # Validate the date format (YYYY-MM-DD)
        try:
            datetime.strptime(transaction_date, '%Y-%m-%d')  # Check if date is in the correct format
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('add_expense'))

        # Insert the expense entry into the finances table
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO finances (user_id, transaction_name, transaction_type, transaction_date, amount)
            VALUES (?, ?, ?, ?, ?)
        """, (session['user_id'], transaction_name, transaction_type, transaction_date, amount))

        conn.commit()
        conn.close()

        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))  # Redirect to the dashboard

    return render_template('add_expense.html', today_date=today_date)

# Kullanıcı profili (Profile Page)# Kullanıcı profili ve güncelleme (Profile Update)
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Kullanıcı giriş yapmamışsa login sayfasına yönlendir

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()  # Kullanıcı bilgilerini alıyoruz

    conn.close()

    if request.method == 'POST':
        # Kullanıcıdan gelen verileri alıyoruz
        username = request.form['username']
        email = request.form['email']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']

        # Mevcut şifreyi doğrula
        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('profile'))  # Eğer mevcut şifre yanlışsa geri dön

        # Yeni şifreyi doğrula
        if new_password and new_password != confirm_new_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('profile'))  # Yeni şifreler eşleşmiyorsa geri dön

        # Yeni şifre varsa, hashleyip güncelle
        if new_password:
            hashed_new_password = generate_password_hash(new_password)
        else:
            hashed_new_password = user['password']  # Şifreyi değiştirmemek için mevcut şifreyi kullan

        # Kullanıcı bilgilerini güncelle
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET username = ?, email = ?, password = ?
            WHERE id = ?
        """, (username, email, hashed_new_password, user_id))

        conn.commit()
        conn.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))  # Profil başarıyla güncellendiyse profile sayfasına dön

    return render_template('profile.html', user=user)
# Kullanıcı çıkışı (Log Out)
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Oturumu temizle
    session.pop('username', None)  # Kullanıcı adı bilgisini de temizle
    flash('You have logged out successfully.', 'success')
    return redirect(url_for('login'))  # Çıkış yaptıktan sonra login sayfasına yönlendir


# Uygulama Çalıştırma
if __name__ == '__main__':
    init_db()  # Veritabanı tablosunu oluştur
    app.run(debug=True)
