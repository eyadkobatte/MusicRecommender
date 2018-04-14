from flask import Flask, render_template, url_for, request, jsonify, session, redirect, escape
from flaskext.mysql import MySQL

from celery_tasks import create_matrix

import pandas as pd
import pickle
import os.path
import Recommenders

app = Flask(__name__)

app.secret_key = '\xf9\xd5Qu\xee\xe6\x13\xda#)\xf9\x16t\xe6\x1b`\x87\xf2\n\xe4\x0f\x7f\xc1\xa3'

mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '123456'
app.config['MYSQL_DATABASE_DB'] = 'msd'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()

@app.route('/', methods=['POST','GET'])
def index():
    return render_template('index.html')

# @app.route('/home', methods=['POST','GET'])
# def home():
#     user_id = request.form.get('user_id')
#     if user_id is not '':
#         cursor.execute('Select count(*) from users where user_id = "' + str(user_id) + '";')
#         user_details = cursor.fetchall()
#         if user_details is not None:
#             # User Exists
#             file_handler = open('trained_model','rb')
#             model = pickle.load(file_handler)
#
#             user_songs = model.get_user_items(user_id)
#             all_songs = model.get_all_items_train_data()
#             if user_details[0][0] > 10:
#                 # User has more than 10 song history
#                 matrix_file_name = 'user_data/' + user_id + '-matrix'
#                 if os.path.isfile(matrix_file_name):
#                     # User matrix is already created
#                     matrix_file = open(matrix_file_name, 'rb')
#                     matrix = pickle.load(matrix_file)
#                     recommendations = model.generate_top_recommendations(user_id, matrix, all_songs, user_songs)
#                     return render_template('home.html', user_id=user_id, mode=0, history=user_songs, recommendations=recommendations, status='New Music Ready')
#                 else:
#                     # Creating new user matrix
#                     create_matrix.delay(user_id, user_songs, all_songs)
#
#                     pop_recommender = Recommenders.popularity_recommender_py()
#                     pop_recommender.create(pd.read_pickle('train_data'), 'user_id','song')
#                     recommendations = pop_recommender.recommend(user_id)
#
#                     return render_template('home.html', user_id=user_id, mode=1, history=user_songs, recommendations=recommendations, status='Recommendations getting ready. Please try again later.')
#                 file_handler.close()
#             elif user_details[0][0]==0:
#                 # User Doesn't Exist
#                 return render_template('index.html', status='UserId Not Found. Try Again', class_label='alert alert-danger')
#             else:
#                 # User has less than 10 songs history
#                 pop_recommender = Recommenders.popularity_recommender_py()
#                 pop_recommender.create(pd.read_pickle('train_data'), 'user_id','song')
#                 recommendations = pop_recommender.recommend(user_id)
#
#                 return render_template('home.html', user_id=user_id, mode=2, history=user_songs, recommendations=recommendations, status='Not Enough Music History. Listen to more songs first.')
#     else:
#         return render_template('index.html', status='Enter Valid User ID', class_label='alert alert-danger')
# Mode 0: Matrix is already created
# Mode 1: Creating New matrix
# Mode 2: Not Enough History for matrix

@app.route('/signUp', methods=['POST','GET'])
def signUp():
    user_id = request.form.get('user_id')
    if user_id is '':
        return render_template('index.html', status='Enter Valid User ID to register', class_label='alert alert-danger')
    cursor.execute('Select user_id from triplets where user_id = "' + str(user_id) + '";')
    user_details = cursor.fetchall()
    if user_details is not ():
        return render_template('index.html', status='Not Unique User Id To Register', class_label='alert alert-danger')
    else:
        cursor.execute('Insert into users (user_id, old_user) values (%s, %s)', (user_id, 1))
        conn.commit()
        conn.close()
        return render_template('index.html', status='User Created', class_label='alert alert-success', temp=cursor.fetchall())

@app.route('/addNewSong', methods=['POST','GET'])
def addNewSong():
    user_id = request.form.get('user_id')
    return render_template('add_new_song.html', user_id=user_id)


@app.route('/home', methods=['POST','GET'])
def home():
    if 'user_id' in session:
        user_id = escape(session['user_id'])
    if request.form.get('user_id'):
        user_id = request.form.get('user_id')
    file_to_render = 'index.html'
    values = {}

    if user_id:
        # Some User Id Entered
        session['user_id'] = user_id
        cursor.execute('Select count(*) from users where user_id = "' + str(user_id) + '";')
        sql_results = cursor.fetchall()
        if sql_results[0][0] > 0:
            # Valid User Id Entered
            cursor.execute('Select count(*) from triplets where user_id = "' + str(user_id) + '";')
            number_of_songs_listened_to = cursor.fetchall()[0][0]

            cursor.execute('Select * from triplets where user_id = "' + str(user_id) + '";')
            user_song_history = cursor.fetchall()

            if number_of_songs_listened_to >= 10:
                # User has more than 10 song History
                matrix_file_name = 'user_data/' + user_id + '-matrix'
                if os.path.isfile(matrix_file_name):
                    # Matrix has already been created
                    model_file_handler = open('trained_model','rb')
                    item_model = pickle.load(model_file_handler)
                    matrix_file = open(matrix_file_name, 'rb')

                    matrix = pickle.load(matrix_file)
                    user_songs = item_model.get_user_items(user_id)
                    all_songs = item_model.get_all_items_train_data()
                    new_recommendations = item_model.generate_top_recommendations(user_id, matrix, all_songs, user_songs)

                    file_to_render = 'home.html'
                    values['status'] = 'New Recommendations Ready'
                    values['history'] = user_song_history
                    values['recommendations'] = new_recommendations
                    values['user_id'] = user_id
                else:
                    # Matrix not created and should be created now
                    create_matrix.delay(user_id)

                    popularity_recommender = Recommenders.popularity_recommender_py()
                    popularity_recommender.create(pd.read_pickle('train_data'), 'user_id', 'song')
                    new_recommendations = popularity_recommender.recommend(user_id)

                    file_to_render = 'home.html'
                    values['status'] = 'Creating New Recommendations. Please Check Later.'
                    values['history'] = user_song_history
                    values['recommendations'] = new_recommendations
                    values['user_id'] = user_id
            else:
                # User doesnt have enough song history
                cursor.execute('Select * from triplets where user_id = "' + str(user_id) + '";')
                user_song_history = cursor.fetchall()

                popularity_recommender = Recommenders.popularity_recommender_py()
                popularity_recommender.create(pd.read_pickle('train_data'), 'user_id', 'song')
                new_recommendations = popularity_recommender.recommend(user_id)

                file_to_render = 'home.html'
                values['status'] = 'Not Enough History'
                values['history'] = user_song_history
                values['recommendations'] = new_recommendations
                values['user_id'] = user_id
        else:
            # Invalid User Id Entered
            file_to_render = 'index.html'
            values['status'] = 'No User Found'
            values['class_label'] = 'alert alert-danger'
    else:
        # No User ID Entered
        file_to_render = 'index.html'
        values['status'] = 'No User Id Entered'
        values['class_label'] = 'alert alert-danger'

    return render_template(file_to_render, values = values)


    #
    #
    # if user_id is not '':
    #     cursor.execute('Select count(*) from users where user_id = "' + str(user_id) + '";')
    #     user_details = cursor.fetchall()
    #     if user_details is not None:
    #         # User Exists
    #         file_handler = open('trained_model','rb')
    #         model = pickle.load(file_handler)
    #
    #         user_songs = model.get_user_items(user_id)
    #         all_songs = model.get_all_items_train_data()
    #         if user_details[0][0] > 10:
    #             # User has more than 10 song history
    #             matrix_file_name = 'user_data/' + user_id + '-matrix'
    #             if os.path.isfile(matrix_file_name):
    #                 # User matrix is already created
    #                 matrix_file = open(matrix_file_name, 'rb')
    #                 matrix = pickle.load(matrix_file)
    #                 recommendations = model.generate_top_recommendations(user_id, matrix, all_songs, user_songs)
    #                 return render_template('home.html', user_id=user_id, mode=0, history=user_songs, recommendations=recommendations, status='New Music Ready')
    #             else:
    #                 # Creating new user matrix
    #                 create_matrix.delay(user_id, user_songs, all_songs)
    #
    #                 pop_recommender = Recommenders.popularity_recommender_py()
    #                 pop_recommender.create(pd.read_pickle('train_data'), 'user_id','song')
    #                 recommendations = pop_recommender.recommend(user_id)
    #
    #                 return render_template('home.html', user_id=user_id, mode=1, history=user_songs, recommendations=recommendations, status='Recommendations getting ready. Please try again later.')
    #             file_handler.close()
    #         elif user_details[0][0]==0:
    #             # User Doesn't Exist
    #             return render_template('index.html', status='UserId Not Found. Try Again', class_label='alert alert-danger')
    #         else:
    #             # User has less than 10 songs history
    #             pop_recommender = Recommenders.popularity_recommender_py()
    #             pop_recommender.create(pd.read_pickle('train_data'), 'user_id','song')
    #             recommendations = pop_recommender.recommend(user_id)
    #
    #             return render_template('home.html', user_id=user_id, mode=2, history=user_songs, recommendations=recommendations, status='Not Enough Music History. Listen to more songs first.')
    # else:
    #     return render_template('index.html', status='Enter Valid User ID', class_label='alert alert-danger')

@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


if __name__=='__main__':
    app.run(debug=True)
