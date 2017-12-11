#!/usr/bin/env python
import os
from flask import Flask, abort, request, jsonify, g, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from passlib.apps import custom_app_context as pwd_context


'''
|-----------------------------------------------------------------
| Initialization
|-----------------------------------------------------------------
| Below code initialize the configurations that are needed to 
| run the server such as the sqlite database.
|-----------------------------------------------------------------
'''
app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True


db = SQLAlchemy(app)
auth = HTTPBasicAuth()

'''
|-----------------------------------------------------------------
| User model
|-----------------------------------------------------------------
| Code responsible for the user model. This acts as the user   
| object model used for the ORM. Functions related to the user 
| model such as encrypting password implemented here
|-----------------------------------------------------------------
'''

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True)
    password_hash = db.Column(db.String(64))

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

'''
|-----------------------------------------------------------------
| Password Authentication
|-----------------------------------------------------------------
'''

@auth.verify_password
def verify_password(username, password):
    # try to authenticate with username/password
    user = User.query.filter_by(username=username).first()
    if not user or not user.verify_password(password):
            return False   
    g.user = user
    return True

'''
|-----------------------------------------------------------------
| App Routes
|-----------------------------------------------------------------
'''

@app.route('/api/users', methods=['POST'])
def new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(400)    # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        abort(400)    # existing user
    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return (jsonify({'username': user.username}), 201,
            {'Location': url_for('get_user', id=user.id, _external=True)})


@app.route('/api/users/<int:id>')
def get_user(id):
    user = User.query.get(id)
    if not user:
        abort(400)
    return jsonify({'username': user.username})

@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.username})


'''
|-----------------------------------------------------------------
| Main method
|-----------------------------------------------------------------
'''

if __name__ == '__main__':
    if not os.path.exists('db.sqlite'):
        db.create_all()
    app.run(debug=True)