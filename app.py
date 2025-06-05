# app.py
from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news.db'
db = SQLAlchemy(app)


# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    news = db.relationship('News', backref='author', lazy=True)


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Веб-интерфейс
# Обновим функцию главной страницы
@app.route('/')
def index():
    # Загружаем новости вместе с авторами в одном запросе
    news_list = News.query.options(joinedload(News.author)).all()
    return render_template('index.html', news_list=news_list)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])
        new_user = User(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            email=request.form['email'],
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/news/add', methods=['GET', 'POST'])
def add_news():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_news = News(
            title=request.form['title'],
            content=request.form['content'],
            user_id=session['user_id']
        )
        db.session.add(new_news)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_news.html')


@app.route('/news/edit/<int:id>', methods=['GET', 'POST'])
def edit_news(id):
    news_item = News.query.get_or_404(id)
    if news_item.user_id != session['user_id']:
        return redirect(url_for('index'))

    if request.method == 'POST':
        news_item.title = request.form['title']
        news_item.content = request.form['content']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_news.html', news=news_item)


@app.route('/news/delete/<int:id>')
def delete_news(id):
    news_item = News.query.get_or_404(id)
    if news_item.user_id != session['user_id']:
        return redirect(url_for('index'))

    db.session.delete(news_item)
    db.session.commit()
    return redirect(url_for('index'))


# REST API
@app.route('/api/users', methods=['GET', 'POST'])
def api_users():
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([{
            'id': u.id,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email
        } for u in users])

    if request.method == 'POST':
        data = request.json
        hashed_password = generate_password_hash(data['password'])
        new_user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User created'}), 201


@app.route('/api/users/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_user(id):
    user = User.query.get_or_404(id)

    if request.method == 'GET':
        return jsonify({
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        })

    if request.method == 'PUT':
        data = request.json
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        if 'password' in data:
            user.password = generate_password_hash(data['password'])
        db.session.commit()
        return jsonify({'message': 'User updated'})

    if request.method == 'DELETE':
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted'})


@app.route('/api/news', methods=['GET', 'POST'])
def api_news():
    if request.method == 'GET':
        news_list = News.query.all()
        return jsonify([{
            'id': n.id,
            'title': n.title,
            'content': n.content,
            'user_id': n.user_id
        } for n in news_list])

    if request.method == 'POST':
        data = request.json
        new_news = News(
            title=data['title'],
            content=data['content'],
            user_id=data['user_id']
        )
        db.session.add(new_news)
        db.session.commit()
        return jsonify({'message': 'News created'}), 201


@app.route('/api/news/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_news_item(id):
    news = News.query.get_or_404(id)

    if request.method == 'GET':
        return jsonify({
            'id': news.id,
            'title': news.title,
            'content': news.content,
            'user_id': news.user_id
        })

    if request.method == 'PUT':
        data = request.json
        news.title = data.get('title', news.title)
        news.content = data.get('content', news.content)
        db.session.commit()
        return jsonify({'message': 'News updated'})

    if request.method == 'DELETE':
        db.session.delete(news)
        db.session.commit()
        return jsonify({'message': 'News deleted'})


# Клиент для тестирования API
@app.route('/api-test')
def api_test():
    return render_template('api_test.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)