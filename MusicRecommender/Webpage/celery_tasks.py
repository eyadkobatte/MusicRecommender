from celery import Celery
import pickle
import Recommenders


app = Celery('celery_tasks', broker='pyamqp://guest@localhost//')

@app.task
def create_matrix(user_id):
    file_handler = open('trained_model','rb')
    model = pickle.load(file_handler)
    file_handler.close()

    user_songs = model.get_user_items(user_id)
    all_songs = model.get_all_items_train_data()

    matrix = model.construct_cooccurence_matrix(user_songs, all_songs)
    matrix_file_name = 'user_data/' + user_id + '-matrix'
    matrix_file = open(matrix_file_name, 'wb')
    pickle.dump(matrix,matrix_file)
    matrix_file.close()
