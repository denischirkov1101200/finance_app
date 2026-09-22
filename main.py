from datetime import date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from models import db, Transaction, Category

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    today = date.today()
    first_day = today.replace(day=1)

    # Summary for current month
    income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= first_day,
        Transaction.date <= today
    ).scalar() or Decimal('0')

    expense = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= first_day,
        Transaction.date <= today
    ).scalar() or Decimal('0')

    balance = income - expense

    # Recent transactions
    recent = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc(), Transaction.id.desc()).limit(8).all()

    return render_template(
        'dashboard.html',
        income=float(income),
        expense=float(expense),
        balance=float(balance),
        recent=recent,
        month_name=today.strftime('%B %Y')
    )


@main_bp.route('/transactions')
@login_required
def transactions_list():
    page = request.args.get('page', 1, type=int)
    type_filter = request.args.get('type', '')
    category_id = request.args.get('category', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    q = Transaction.query.filter_by(user_id=current_user.id)

    if type_filter in ('income', 'expense'):
        q = q.filter_by(type=type_filter)
    if category_id:
        q = q.filter_by(category_id=category_id)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)

    pagination = q.order_by(Transaction.date.desc(), Transaction.id.desc()).paginate(page=page, per_page=15)
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.type, Category.name).all()

    return render_template(
        'transactions.html',
        pagination=pagination,
        categories=categories,
        type_filter=type_filter,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to
    )


@main_bp.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def transaction_add():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.type, Category.name).all()

    if request.method == 'POST':
        try:
            amount = Decimal(request.form.get('amount', '0').replace(',', '.'))
            if amount <= 0:
                raise ValueError('Сумма должна быть положительной')
            t_type = request.form.get('type')
            if t_type not in ('income', 'expense'):
                raise ValueError('Неверный тип')
            cat_id = request.form.get('category_id') or None
            if cat_id:
                cat = Category.query.filter_by(id=int(cat_id), user_id=current_user.id).first()
                if not cat:
                    raise ValueError('Категория не найдена')
            else:
                cat = None
            desc = request.form.get('description', '').strip()
            d = date.fromisoformat(request.form.get('date') or date.today().isoformat())

            tr = Transaction(
                user_id=current_user.id,
                category_id=cat.id if cat else None,
                amount=amount,
                type=t_type,
                description=desc,
                date=d
            )
            db.session.add(tr)
            db.session.commit()
            flash('Транзакция добавлена', 'success')
            return redirect(url_for('main.transactions_list'))
        except Exception as e:
            flash(f'Ошибка: {e}', 'danger')

    return render_template('transaction_form.html', categories=categories, transaction=None)


@main_bp.route('/transactions/<int:tid>/edit', methods=['GET', 'POST'])
@login_required
def transaction_edit(tid):
    tr = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.type, Category.name).all()

    if request.method == 'POST':
        try:
            amount = Decimal(request.form.get('amount', '0').replace(',', '.'))
            if amount <= 0:
                raise ValueError('Сумма должна быть положительной')
            t_type = request.form.get('type')
            if t_type not in ('income', 'expense'):
                raise ValueError('Неверный тип')
            cat_id = request.form.get('category_id') or None
            if cat_id:
                cat = Category.query.filter_by(id=int(cat_id), user_id=current_user.id).first()
                if not cat:
                    raise ValueError('Категория не найдена')
            else:
                cat = None
            desc = request.form.get('description', '').strip()
            d = date.fromisoformat(request.form.get('date') or date.today().isoformat())

            tr.amount = amount
            tr.type = t_type
            tr.category_id = cat.id if cat else None
            tr.description = desc
            tr.date = d
            db.session.commit()
            flash('Транзакция обновлена', 'success')
            return redirect(url_for('main.transactions_list'))
        except Exception as e:
            flash(f'Ошибка: {e}', 'danger')

    return render_template('transaction_form.html', categories=categories, transaction=tr)


@main_bp.route('/transactions/<int:tid>/delete', methods=['POST'])
@login_required
def transaction_delete(tid):
    tr = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    db.session.delete(tr)
    db.session.commit()
    flash('Транзакция удалена', 'info')
    return redirect(url_for('main.transactions_list'))


@main_bp.route('/categories')
@login_required
def categories_list():
    cats = Category.query.filter_by(user_id=current_user.id).order_by(Category.type, Category.name).all()
    return render_template('categories.html', categories=cats)


@main_bp.route('/categories/add', methods=['POST'])
@login_required
def category_add():
    name = request.form.get('name', '').strip()
    cat_type = request.form.get('type', 'expense')
    if name and cat_type in ('income', 'expense'):
        db.session.add(Category(user_id=current_user.id, name=name, type=cat_type))
        db.session.commit()
        flash('Категория добавлена', 'success')
    else:
        flash('Некорректные данные', 'danger')
    return redirect(url_for('main.categories_list'))


@main_bp.route('/categories/<int:cid>/delete', methods=['POST'])
@login_required
def category_delete(cid):
    cat = Category.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    # Unlink transactions first
    Transaction.query.filter_by(category_id=cat.id).update({'category_id': None})
    db.session.delete(cat)
    db.session.commit()
    flash('Категория удалена', 'info')
    return redirect(url_for('main.categories_list'))


# ---------- Analytics API ----------

@main_bp.route('/api/summary')
@login_required
def api_summary():
    date_from = request.args.get('from') or (date.today().replace(day=1)).isoformat()
    date_to = request.args.get('to') or date.today().isoformat()

    income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= date_from,
        Transaction.date <= date_to
    ).scalar() or 0

    expense = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= date_from,
        Transaction.date <= date_to
    ).scalar() or 0

    return jsonify({
        'income': float(income),
        'expense': float(expense),
        'balance': float(income) - float(expense),
        'from': date_from,
        'to': date_to
    })


@main_bp.route('/api/by-category')
@login_required
def api_by_category():
    t_type = request.args.get('type', 'expense')
    date_from = request.args.get('from') or (date.today().replace(day=1)).isoformat()
    date_to = request.args.get('to') or date.today().isoformat()

    rows = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == t_type,
        Transaction.date >= date_from,
        Transaction.date <= date_to
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all()

    labels = [r[0] for r in rows]
    values = [float(r[1]) for r in rows]

    # Also include uncategorized
    uncat = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == t_type,
        Transaction.category_id.is_(None),
        Transaction.date >= date_from,
        Transaction.date <= date_to
    ).scalar() or 0
    if float(uncat) > 0:
        labels.append('Без категории')
        values.append(float(uncat))

    return jsonify({'labels': labels, 'values': values})


@main_bp.route('/api/timeline')
@login_required
def api_timeline():
    # Last 6 months
    today = date.today()
    months = []
    for i in range(5, -1, -1):
        d = (today.replace(day=1) - timedelta(days=30 * i))
        months.append((d.year, d.month))

    labels = []
    income_data = []
    expense_data = []

    for year, month in months:
        labels.append(f'{month:02d}.{year}')
        inc = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'income',
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).scalar() or 0
        exp = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).scalar() or 0
        income_data.append(float(inc))
        expense_data.append(float(exp))

    return jsonify({
        'labels': labels,
        'income': income_data,
        'expense': expense_data
    })