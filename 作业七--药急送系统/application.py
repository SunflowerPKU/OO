#coding: utf-8
#from gevent import monkey
import time
from flask import Flask, render_template, request, g, session, redirect, flash, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
import json 
import requests
from elasticsearch import Elasticsearch
import sqlalchemy
import predictionio

import sys  
reload(sys)  
sys.setdefaultencoding('utf8')
#monkey.patch_all()
application = Flask(__name__)
application.config['SECRET_KEY'] = 'secret!'
eventserver_url = 'http://52.87.217.221:7070'
#eventserver_url = 'http://127.0.0.1:7070'
access_key = 'fWPlsqEj5AOv4EQSzkCvz-yoOpjeuPnMyWimv_nZS1pT5ndWzEme8S0hspWVzfo-'

pio_client = predictionio.EventClient(
    access_key=access_key,
    url=eventserver_url,
    threads=5,
    qsize=500
)

disp_process_pref = "===[Process]===: "
    

#####################################
#
# For hanlding PostGreSQL
#
#####################################

conn_str = 'postgresql://tanxin:413372@localhost:5432/medicine'
engine_url = 'https://52.87.217.221:8000/queries.json'
#engine_url = 'https://127.0.0.1:5432/queries.json'
#engine_url = 'https://localhost:8000/queries.json'

engine = sqlalchemy.create_engine(conn_str)

@application.before_request
def before_request():
    try:
        g.conn = engine.connect()
        print("connect finished")
    except:
        g.conn = None


@application.teardown_request
def teardown_request(_):
    if g.conn is not None:
        g.conn.close()


# Render home page
@application.route('/')
def index():

    print("session")
    return redirect(url_for('signin'))
    if 'username' not in session:
        print("not in session")
        return redirect(url_for('signin'))
    print("in session")
    print(session['username'])
    response = requests.post(engine_url, json.dumps({'user': session['username'], 'num': 20}), verify=False)
    response = json.loads(response.text)['itemScores']
    #response=""
    cur1 = g.conn.execute('''SELECT account FROM users WHERE username = %s''', username)
    cur1_account = cur1.fetchone()
    print len(response)
    if len(response) == 0:

        cur = g.conn.execute('''
        SELECT *
        FROM medicine
        WHERE random() < 0.01
        LIMIT %s''', 20)  

        medicine_dict = get_medicine(cur)
        return render_template('index.html', this_username = session['username'], this_account = cur1_account[0], show_what = "热销药品", medicine_info_list = medicine_dict)


    return render_template('index.html', this_username = session['username'], this_account = cur1_account[0], show_what = "热销药品", medicine_info_list = '')

# Render home page
@application.route('/index')
def index_():


    cur = g.conn.execute('''
    SELECT *
    FROM medicine
    LIMIT %s''', 10)
    medicine_dict = get_medicine(cur)
    print(len(medicine_dict))
    username=session['username']
    cur1 = g.conn.execute('''SELECT account FROM users WHERE username = %s''', username)
    cur1_account = cur1.fetchone()
    return render_template('index.html', this_username = session['username'], this_account = cur1_account[0], show_what = "热销药品", medicine_info_list = medicine_dict)

@application.route('/signin', methods = ['GET', 'POST'])
def signin():
    error = None

    if request.method == 'POST':
        username = request.form.get('user-username')
        password = request.form.get('user-password')

        cur = g.conn.execute('''SELECT * FROM users WHERE username = %s AND password = %s''', (username, password))
        user = cur.fetchone()
        if user is None:
            return render_template('signin.html')
        else:            
            session['username'] = username

        cur = g.conn.execute('''
        SELECT *
        FROM medicine
        LIMIT %s''', 10)  

        medicine_dict = get_medicine(cur)
        print(len(medicine_dict))

        cur1 = g.conn.execute('''SELECT account FROM users WHERE username = %s AND password = %s''', (username, password))
        cur1_account = cur1.fetchone()
        return render_template('index.html', this_username = session['username'], this_account = cur1_account[0], show_what = "热销药品", medicine_info_list = medicine_dict)#redirect(url_for('index'))

    return render_template('signin.html')



@application.route('/signup', methods = ['GET', 'POST'])
def signup():

    if request.method == 'POST':
        username = request.form.get('user-username')
        password = request.form.get('user-password')
        account = request.form.get('user-account')
        session['username'] = username
        session['account'] = account
        try:
            g.conn.execute('''INSERT INTO users (username, password, account) VALUES (%s, %s, %s)''', (username, password, account))
            session['username'] = username
        except Exception as e:
            return render_template('signup.html')



        return redirect(url_for('signin'))#render_template('index.html', this_username = session['username'], show_what = "Top Picks", medicine_info_list = '')



    return render_template('signup.html')



@application.route('/search_medicine', methods = ["POST"])
def search_movie():

    medicine_name = request.form.get('search-box')
    medicine_name0= medicine_name
    medicine_name = '%'+medicine_name+'%'
    cur = g.conn.execute('SELECT * FROM medicine WHERE name like %s LIMIT 20',medicine_name)

    medicine_dict = get_medicine(cur)
  
    cur1 = g.conn.execute('SELECT account FROM users WHERE username like %s ',session['username'])
    cur1_account = cur1.fetchone()
    return render_template('index.html', this_username = session['username'], this_account = cur1_account[0],show_what = "搜索结果: "+medicine_name0, medicine_info_list = medicine_dict)




@application.route('/show_medicine')
def show_movie():
    med_genre = request.args.get('genre')
    genre=[];
    medicine_info_list = []
    if med_genre == '感冒发烧':

        genre='%'+'感冒发烧'+'%'

        cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id in (SELECT medicine_id FROM medicine_genres WHERE genres like %s)',genre)
        
        medicine_dict = get_medicine(cur)

        show = "感冒发烧"

    elif med_genre == '腹泻':
        genre='%'+'腹泻'+'%'
        cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id in (SELECT medicine_id FROM medicine_genres WHERE genres like %s)',genre)
        
        medicine_dict = get_medicine(cur)

        show = "腹泻"

    elif med_genre == '减肥':
        genre='%'+'减肥'+'%'
        cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id in (SELECT medicine_id FROM medicine_genres WHERE genres like %s)',genre)
        
        medicine_dict = get_medicine(cur)
        show = "减肥"

    elif med_genre == '跌打损伤':
        genre='%'+'跌打损伤'+'%'
        cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id in (SELECT medicine_id FROM medicine_genres WHERE genres like %s)',genre)
        
        medicine_dict = get_medicine(cur)
        show = "跌打损伤"

    else:
        cur = g.conn.execute('SELECT * FROM medicine WHERE random() < 10 LIMIT 20')
        
        medicine_dict = get_medicine(cur)
        show = "其它"
    cur1 = g.conn.execute('SELECT account FROM users WHERE username like %s ',session['username'])
    cur1_account = cur1.fetchone()
    return render_template('index.html', this_username = session['username'], this_account = cur1_account[0], show_what = show, medicine_info_list = medicine_dict)



@application.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('signin'))



@application.route('/profile')
def profile():
    cur = g.conn.execute('SELECT fullname,gender,mobile,email, description FROM userinfo WHERE username=%s',session['username'])
    userinfo=[row for row in cur]
    print userinfo
    return render_template('profile.html', this_username = session['username'],user_info_list=userinfo)

@application.route('/medicine', methods = ["GET", "POST"])
def inbox():

    medicine_id = request.args.get('medicine_id')
    """
    user_comment = []
    if request.method == 'POST':
        
        new_comment = request.form.get('user-comment')

        if new_comment != '':
            try:
                g.conn.execute('INSERT INTO comments (username, movie_id, comments) VALUES (%s, %s, %s)', (session['username'], movie_id, new_comment))

            except:
                pass

        else:

            if request.form["btn_cl"] == "1":
                user_rate = 1
                send_rating(session['username'], movie_id, user_rate)
            elif request.form["btn_cl"] == "2":
                user_rate = 2
                send_rating(session['username'], movie_id, user_rate)
            elif request.form["btn_cl"] == "3":
                user_rate = 3
                send_rating(session['username'], movie_id, user_rate)
            elif request.form["btn_cl"] == "4":
                user_rate = 4
                send_rating(session['username'], movie_id, user_rate)
            elif request.form["btn_cl"] == "5":
                user_rate = 5
                send_rating(session['username'], movie_id, user_rate)
            else:
                user_rate = 3
                send_rating(session['username'], movie_id, user_rate)

         
            


        
    try:
        cur = g.conn.execute('SELECT comments, username FROM comments WHERE movie_id=%s', (movie_id))
        
        for each in cur:
            user_comment.append([each[1], each[0]])
    except:
        pass

    if user_comment == "None":
        user_comment = []
    """

    cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id=%s',medicine_id)
    cur1 = g.conn.execute('SELECT account FROM users WHERE username like %s ',session['username'])
    cur1_account = cur1.fetchone()
    medicine_dict = get_medicine(cur)[0]
    
    seller = g.conn.execute('SELECT seller_name FROM medicine_sellers WHERE medicine_id = %s ',medicine_id)
    seller_name = seller.fetchone()
    medicine_dict['seller'] = seller_name[0]

    description = g.conn.execute('SELECT description FROM medicine WHERE medicine_id = %s ',medicine_id)
    des = description.fetchone()
    medicine_dict['description'] = des[0]
    return render_template('movie_page.html', this_username = session['username'], this_account = cur1_account[0], this_medicine = medicine_dict, this_movie_comment = [])


def send_rating(page_user, movie_id, user_rate):

    with g.conn.begin() as _:
        g.conn.execute('DELETE FROM ratings WHERE username = %s AND movie_id = %s', (page_user, movie_id))
        g.conn.execute('INSERT INTO ratings (username, movie_id, rating) VALUES (%s, %s, %s)', (page_user, movie_id, user_rate))
    pio_client.create_event(
            event="rate",
            entity_type="user",
            entity_id=page_user,
            target_entity_type="item",
            target_entity_id=str(movie_id),
            properties={"rating": user_rate}
        )

@application.route('/profile-edit',methods = ["GET", "POST"])
def profile_edit():
    fullname = request.form.get('user-fullname')
    gender = request.form.get('user-gender')
    mobile = request.form.get('user-mobile')
    email = request.form.get('user-email')
    description = request.form.get('user-description')
    # username=session['username']
    print (session['username'],fullname,gender,mobile,email, description)
    g.conn.execute('Delete from userinfo where username=%s', session['username'])
    g.conn.execute('INSERT INTO userinfo (username,fullname,gender,mobile,email, description) VALUES (%s,%s, %s, %s,%s,%s)', (session['username'],fullname,gender,mobile,email, description))
    # if fullname!=[]
    #     flag=1;
    # flash('You profile has been updated.')


    return render_template('profile-edit.html', this_username = session['username'])

def get_medicine(cur):
    medicine_info={}
    print("cur")
    for row in cur:
        medicine_info[row[0]]=(row[1], row[2],row[3],row[4])
        print(row)

    #medicine_info = {row[0]: (row[1], row[2],row[3]) for row in cur}
    medicines = []
    print(len(medicine_info))
    for key in medicine_info:
        medicines.append({'medicine_id': key,
                       'price': str(medicine_info[key][0]),
                       'num': medicine_info[key][1],
                       'name': medicine_info[key][2],
                       'url': medicine_info[key][3]})
    return medicines

@application.route('/add_shoppingcart',methods = ["GET", "POST"])
def add_shoppingcart():
    medicine_id = request.args.get('id')
    medicine_num = request.form.get('number')

    g.conn.execute('INSERT INTO shopping_cart (username, medicine_id, num) VALUES (%s,%s,%s)',(session['username'],medicine_id,medicine_num))

    cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id=%s',medicine_id)
    cur1 = g.conn.execute('SELECT account FROM users WHERE username like %s ',session['username'])
    cur1_account = cur1.fetchone()
    medicine_dict = get_medicine(cur)[0]
    
    seller = g.conn.execute('SELECT seller_name FROM medicine_sellers WHERE medicine_id = %s ',medicine_id)
    seller_name = seller.fetchone()
    medicine_dict['seller'] = seller_name[0]

    description = g.conn.execute('SELECT description FROM medicine WHERE medicine_id = %s ',medicine_id)
    des = description.fetchone()
    medicine_dict['description'] = des[0]
    return render_template('movie_page.html', this_username = session['username'], this_account = cur1_account[0], this_medicine = medicine_dict, this_movie_comment = [])

@application.route('/show_shoppingcart')
def show_shoppingcart():
    
    medicine_info_list = []
    
    cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id in (SELECT medicine_id FROM (SELECT * FROM shopping_cart WHERE username like %s) AS a)',session['username'])
         
    medicine_dict = get_medicine(cur)

    show = "我的购物车"

    cur1 = g.conn.execute('SELECT account FROM users WHERE username like %s ',session['username'])
    cur1_account = cur1.fetchone()

    cur2 = g.conn.execute('SELECT medicine_id, num FROM shopping_cart where username like %s', session['username'])
    cart_info={}
    for row in cur2:
        cart_info[row[0]]=(row[1])

    for key in cart_info:
        for i in range(len(medicine_dict)):
            if medicine_dict[i]['medicine_id'] == key:
                medicine_dict[i]['number'] = cart_info[key]


    return render_template('shoppingcart.html', this_username = session['username'], this_account = cur1_account[0], show_what = show, medicine_info_list = medicine_dict)


@application.route('/clean_shoppingcart',methods = ["GET", "POST"])
def clean_shoppingcart():

    g.conn.execute('''DELETE FROM shopping_cart WHERE username = %s''', session['username'])
    
    medicine_info_list = []
    cur = g.conn.execute('SELECT * FROM medicine WHERE medicine_id in (SELECT medicine_id FROM (SELECT * FROM shopping_cart WHERE username like %s) AS a)',session['username'])
         
    medicine_dict = get_medicine(cur)

    show = "我的购物车"

    cur1 = g.conn.execute('SELECT account FROM users WHERE username = %s ',session['username'])
    cur1_account = cur1.fetchone()

    cur2 = g.conn.execute('SELECT medicine_id, num FROM shopping_cart where username = %s', session['username'])
    cart_info={}
    for row in cur2:
        cart_info[row[0]]=(row[1])

    for key in cart_info:
        for i in range(len(medicine_dict)):
            if medicine_dict[i]['medicine_id'] == key:
                medicine_dict[i]['number'] = cart_info[key]
    
    return render_template('shoppingcart.html', this_username = session['username'], this_account = cur1_account[0], show_what = show, medicine_info_list = medicine_dict)

@application.route('/pay',methods = ["GET", "POST"])
def pay():
    
    med_price = {}
    total = 0
    cur = g.conn.execute('SELECT medicine_id, num FROM shopping_cart WHERE username = %s', session['username'])
    cur_shoppingcart = cur.fetchall()
    for i in range(len(cur_shoppingcart)):
        cur_price = g.conn.execute('SELECT price FROM medicine WHERE medicine_id = %s', cur_shoppingcart[i][0])
        cur_price = cur_price.fetchone()
        price = cur_price[0]
        id = cur_shoppingcart[i][0]
        med_price[id] = price

    for i in range(len(cur_shoppingcart)):
        total += float(med_price[id])*float(cur_shoppingcart[i][1])

    cur_account = g.conn.execute('SELECT account FROM users WHERE username = %s', session['username'])
    cur_account = cur_account.fetchone()
    user_account = float(cur_account[0])

    if user_account >= total:

        a = float(user_account-total)
        g.conn.execute('UPDATE users SET account = %s WHERE username = %s', a, session['username'])
        
        for i in range(len(cur_shoppingcart)):

            number_buy = float(cur_shoppingcart[i][1])
            cur_number = g.conn.execute('SELECT num FROM medicine WHERE medicine_id = %s', cur_shoppingcart[i][0])
            cur_number = cur_number.fetchone()
            number = float(cur_number[0])
            new_number = int(number-number_buy)
            cur_number = g.conn.execute('UPDATE medicine SET num =  %s WHERE medicine_id = %s', new_number, cur_shoppingcart[i][0])

        g.conn.execute('''DELETE FROM shopping_cart WHERE username = %s''', session['username'])

    else:
        pass


    cur = g.conn.execute('''
    SELECT *
    FROM medicine
    LIMIT %s''', 10)
    medicine_dict = get_medicine(cur)
    print(len(medicine_dict))
    username=session['username']
    cur1 = g.conn.execute('''SELECT account FROM users WHERE username = %s''', username)
    cur1_account = cur1.fetchone()
    return render_template('index.html', this_username = session['username'], this_account = cur1_account[0], show_what = "热销药品", medicine_info_list = medicine_dict)

# Main function
if __name__ == '__main__':
    application.run(debug=True, host="0.0.0.0", port=5000)
    #application.run()


