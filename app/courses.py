from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db
from models import Course, Category, User, Review
from tools import CoursesFilter, ImageSaver
from flask_login import current_user
from sqlalchemy import func


bp = Blueprint('courses', __name__, url_prefix='/courses')

PER_PAGE = 3

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

def params():
    return { p: request.form.get(p) for p in COURSE_PARAMS }

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': request.args.getlist('category_ids'),
    }

@bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    courses = CoursesFilter(**search_params()).perform()
    pagination = courses.paginate(page, PER_PAGE)
    courses = pagination.items
    categories = Category.query.all()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
def new():
    categories = Category.query.all()
    users = User.query.all()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users)

@bp.route('/create', methods=['POST'])
def create():

    f = request.files.get('background_img')
    if f and f.filename:
        img = ImageSaver(f).save()

    course = Course(**params(), background_image_id=img.id)
    db.session.add(course)
    db.session.commit()

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))

def calc_course_rating(course_id):
    # Получаем объект курса из базы данных по указанному идентификатору course_id
    course = Course.query.get(course_id)

    # Получаем сумму рейтингов курса
    rating_sum = course.rating_sum

    # Получаем количество рейтингов курса
    rating_num = course.rating_num

    # Проверяем, если количество рейтингов равно нулю, чтобы избежать деления на ноль
    if rating_num == 0:
        return 0

    # Вычисляем и возвращаем средний рейтинг курса, разделяя сумму рейтингов на количество рейтингов
    return rating_sum / rating_num


@bp.route('/<int:course_id>')
def show(course_id):
    # Получение информации о курсе по его идентификатору
    course = Course.query.get(course_id)
    # Получение всех отзывов для данного курса, отсортированных по дате создания
    reviews_all = Review.query.filter_by(course_id=course_id).order_by(Review.created_at.desc()).all()

    # Вычисление среднего рейтинга для курса
    course_rating = calc_course_rating(course_id)

    # Получение списка всех пользователей
    users = User.query.all()

    # Флаг, указывающий, оставил ли текущий пользователь отзыв для данного курса
    flag = False
    for review in reviews_all:
        try:
            if review.user_id == current_user.id:
                flag = True
        except:
            pass

    # Получение последних 5 отзывов для отображения на странице
    reviews_lim5 = Review.query.filter_by(course_id=course_id).order_by(Review.created_at.desc()).limit(5).all()

    # Отображение страницы с информацией о курсе и отзывами
    return render_template('courses/show.html', course=course, reviews_all=reviews_all, reviews_lim5=reviews_lim5, users=users, flag=flag, course_id=course_id, course_rating=course_rating)


@bp.route('/<int:course_id>/reviews', methods=['GET', 'POST'])
def reviews(course_id):
    course = Course.query.get(course_id)

    # Пагинация - получение номера текущей страницы отзывов
    page = request.args.get('page', 1, type=int)
    five_per_page = 5  # Количество отзывов, отображаемых на одной странице

    # Фильтр - определение порядка сортировки отзывов
    sort_by = request.args.get('sort_by', 'new', type=str)
    if sort_by == 'positive':
        order_by = Review.rating.desc()  # Сортировка по возрастанию рейтинга
    elif sort_by == 'negative':
        order_by = Review.rating.asc()  # Сортировка по убыванию рейтинга
    else:
        order_by = Review.created_at.desc()  # Сортировка по дате создания (новые сверху)

    # Получение отфильтрованных и отсортированных отзывов с пагинацией
    reviews_all = Review.query.filter_by(course_id=course_id)\
        .join(User)\
        .add_columns(User.login)\
        .add_columns(User.last_name)\
        .add_columns(User.first_name)\
        .order_by(order_by)\
        .paginate(page, five_per_page, error_out=False)

    # Проверка, вошел ли пользователь в аккаунт или нет
    if current_user.is_authenticated:
        flag = False
        existing_review = Review.query.filter_by(course_id=course_id, user_id=current_user.id).first()
        if existing_review:
            flag = True  # У пользователя уже есть отзыв для данного курса
    else:
        flag = None  # Пользователь не вошел в аккаунт

    # Отображение страницы с отзывами
    return render_template('courses/reviews.html', course=course, reviews_all=reviews_all, flag=flag,  sort_by=sort_by, per_page=five_per_page, page=page)


@bp.route('/<int:course_id>/add_review', methods=['POST'])
def add_review(course_id):
    # Проверяем, вошел ли пользователь в аккаунт или нет
    if not current_user.is_authenticated:
        flash('Для оставления отзыва необходимо войти в свой аккаунт.', 'warning')
        return redirect(url_for('auth.login'))

    # Получаем оценку и текст отзыва из формы
    rating = int(request.form['rating'])
    text = request.form['text']

    # Проверяем допустимость оценки (должна быть в диапазоне от 0 до 5)
    if rating < 0 or rating > 5:
        flash('Недопустимая оценка', 'danger')
        return redirect(url_for('courses.show', course_id=course_id))

    # Проверяем, оставлял ли пользователь уже отзыв для данного курса
    existing_review = Review.query.filter_by(course_id=course_id, user_id=current_user.id).first()
    if existing_review:
        flash('Вы уже оставили отзыв для этого курса.', 'danger')
        return redirect(url_for('courses.show', course_id=course_id))

    # Создаем новый отзыв
    review = Review(rating=rating, text=text, created_at=func.now(), course_id=course_id, user_id=current_user.id)
    db.session.add(review)
    db.session.commit()

    # Обновляем информацию о курсе: увеличиваем количество рейтингов и общую сумму рейтинга
    course = Course.query.get(course_id)
    course.rating_num += 1
    course.rating_sum += rating
    db.session.add(course)
    db.session.commit()

    # Отображаем сообщение об успешном добавлении отзыва
    flash('Отзыв успешно добавлен.', 'success')

    # Перенаправляем пользователя на страницу курса
    return redirect(url_for('courses.show', course_id=course_id))

@bp.route('/<int:course_id>/reviews', methods=['GET'])
def view_reviews(course_id):
    course = Course.query.get(course_id)

    # Получение всех отзывов для данного курса, отсортированных по дате создания (новые сверху)
    reviews = Review.query.filter_by(course_id=course_id).order_by(Review.created_at.desc())

    # Получение списка всех пользователей
    users = User.query.all()

    # Отображение страницы с отзывами
    return render_template('courses/reviews.html', course=course, reviews=reviews, users=users)
