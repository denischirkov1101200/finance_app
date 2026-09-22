from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Category

auth_bp = Blueprint('auth', __name__)

DEFAULT_CATEGORIES = [
    ('Зарплата', 'income'),
    ('Фриланс', 'income'),
    ('Инвестиции', 'income'),
    ('Продукты', 'expense'),
    ('Транспорт', 'expense'),
    ('Жильё', 'expense'),
    ('Развлечения', 'expense'),
    ('Здоровье', 'expense'),
    ('Одежда', 'expense'),
    ('Прочее', 'expense'),
]

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not email or not password:
            flash('Заполните все поля', 'danger')
            return render_template('register.html')

        if password != password2:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Пароль должен быть не короче 6 символов', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('register.html')

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id

        for name, cat_type in DEFAULT_CATEGORIES:
            db.session.add(Category(user_id=user.id, name=name, type=cat_type))

        db.session.commit()
        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash('Неверный email или пароль', 'danger')
            return render_template('login.html')

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.dashboard'))

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))
