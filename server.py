#!/usr/bin/env python
import os
from flask import Flask, abort, request, jsonify, g, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from passlib.apps import custom_app_context as pwd_context
from datetime import datetime
from flask_mail import Mail, Message

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

'''
|-----------------------------------------------------------------
| Email Configurations
|-----------------------------------------------------------------
'''

app.config.update(
    DEBUG=True,
    #EMAIL SETTINGS
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME = '<email to be used to send emails>',
    MAIL_PASSWORD = '<app password>'
    )

db = SQLAlchemy(app)
auth = HTTPBasicAuth()
mail = Mail(app)
'''
|-----------------------------------------------------------------
| Number of tables in the restaurent
|-----------------------------------------------------------------
| Here we make an assumption that every table in the restaurant 
| has equal number of chairs. By the term "one reservation"
| a single table will be reserved. One can reserve the table per 
| single day and only one reservation can be made for a single 
| table per single day  
'''
number_of_tables=10

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
    telephone = db.Column(db.String(32), index=True)
    password_hash = db.Column(db.String(64))
    email= db.Column(db.String(32))
    name= db.Column(db.String(32))
    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

'''
|-----------------------------------------------------------------
| Reservation model
|-----------------------------------------------------------------
| Code responsible for the reservation model. This acts as the    
| reservation object model used for the ORM. 
|-----------------------------------------------------------------
'''
class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    telephone = db.Column(db.String(32))
    date = db.Column(db.DateTime, index=True)

'''
|-----------------------------------------------------------------
| Password Authentication
|-----------------------------------------------------------------
'''

@auth.verify_password
def verify_password(telephone, password):
    # try to authenticate with username/password
    user = User.query.filter_by(telephone=telephone).first()
    if not user or not user.verify_password(password):
            return False   
    g.user = user
    return True

'''
|-----------------------------------------------------------------
| Custom error handlers to support json
|-----------------------------------------------------------------
'''

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

'''
|-----------------------------------------------------------------
| App Routes
|-----------------------------------------------------------------
'''

'''
|-----------------------------------------------------------------
| Here there is no check implemented for restricting a single  
| email for single user. Thus two users can user the same email 
|-----------------------------------------------------------------
'''
@app.route('/api/user/add', methods=['POST'])
def new_user():
    telephone = request.json.get('telephone')
    password = request.json.get('password')
    email = request.json.get('email')
    name = request.json.get('name')
    if telephone is None or password is None or email is None or name is None:
        abort(make_response(jsonify(message="Missing arguments"), 400))    # missing arguments
    if User.query.filter_by(telephone=telephone).first() is not None:
        abort(make_response(jsonify(message="A user with the same telephone number exists!"), 400))    # existing user
    user = User(telephone=telephone,email=email,name=name)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return (jsonify({'status': 'User added successfully!'}), 201)


@app.route('/api/user/<int:id>')
def get_user(id):
    user = User.query.get(id)
    if not user:
        abort(400)
    return jsonify({'telephone': user.telephone})

@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.telephone})

@app.route('/api/reservation',methods=['POST'])
@auth.login_required
def make_reservation():
    date=request.json.get('date')
    user_id=request.authorization.username
    
    #getting user email
    user=User.query.filter_by(telephone=user_id).first()

    #Processing date and creating python datetime object
    date_obj=datetime.strptime(date, '%Y-%m-%d')
    reservations= Reservation.query.filter_by(date=date_obj).count()
    
    if reservations<number_of_tables :
        #More resevations can be made
        reservation=Reservation(telephone=user_id,date=date_obj)
        db.session.add(reservation)
        db.session.commit()

        #Sending the email
        try:
            msg = Message("Reservation made successfully!",
              sender="restaurant@gmail.com",
              recipients=[user.email])
            message_string = """Hi {0},\nYou have made a reservation successfully in our restaurant on {1}.\nFeel free to contact us for any inquiries. Thank you.\nRestaurant Staff"""           
            msg.body=message_string.format(user.name,date)
            mail.send(msg)
            return(jsonify({'status':'Reservation added successfully'}))

        except Exception as e:
            return(jsonify({'status':'Reservation added successfully but email not sent'})) 

        
    else :
        #Cannot make anymore reservations
        return(jsonify({'status':'Reservation adding failed !. We cannot accomodate any more reservations for the mentioned date'}))


'''
|-----------------------------------------------------------------
| Main method
|-----------------------------------------------------------------
'''

if __name__ == '__main__':
    if not os.path.exists('db.sqlite'):
        db.create_all()
    app.run(debug=True)