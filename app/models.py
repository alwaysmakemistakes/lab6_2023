import os
import sqlalchemy as sa
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from flask import url_for
from app import db

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

    def __repr__(self):
        return '<Category %r>' % self.name


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    login = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=sa.sql.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return ' '.join([self.last_name, self.first_name, self.middle_name or ''])

    def __repr__(self):
        return '<User %r>' % self.login

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    short_desc = db.Column(db.Text, nullable=False)
    full_desc = db.Column(db.Text, nullable=False)
    rating_sum = db.Column(db.Integer, nullable=False, default=0)
    rating_num = db.Column(db.Integer, nullable=False, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    background_image_id = db.Column(db.String(100), db.ForeignKey('images.id'))
    created_at = db.Column(db.DateTime,
                           nullable=False,
                           server_default=sa.sql.func.now())

    author = db.relationship('User')
    category = db.relationship('Category', lazy=False)
    bg_image = db.relationship('Image')

    def __repr__(self):
        return '<Course %r>' % self.name

    @property
    def rating(self):
        if self.rating_num > 0:
            return self.rating_sum / self.rating_num
        return 0

class Image(db.Model):
    __tablename__ = 'images'

    id = db.Column(db.String(100), primary_key=True)
    file_name = db.Column(db.String(100), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    md5_hash = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime,
                           nullable=False,
                           server_default=sa.sql.func.now())
    object_id = db.Column(db.Integer)
    object_type = db.Column(db.String(100))

    def __repr__(self):
        return '<Image %r>' % self.file_name

    @property
    def storage_filename(self):
        _, ext = os.path.splitext(self.file_name)
        return self.id + ext

    @property
    def url(self):
        return url_for('image', image_id=self.id)

class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=True, server_default=sa.sql.func.now())
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    course = db.relationship('Course')
    user = db.relationship('User')

    def __repr__(self):
        return '<Review %r>' % self.id
    #возвращает строку, содержащую строковое представление объекта Review,
    #в котором подставляется значение атрибута