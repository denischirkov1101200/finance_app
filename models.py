from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    categories = db.relationship('Category', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'

    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name} ({self.type})>'

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    description = db.Column(db.Text, default='')
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'amount': float(self.amount),
            'type': self.type,
            'description': self.description,
            'date': self.date.isoformat(),
            'category': self.category.name if self.category else None,
            'category_id': self.category_id,
        }

    def __repr__(self):
        return f'<Transaction {self.type} {self.amount} on {self.date}>'