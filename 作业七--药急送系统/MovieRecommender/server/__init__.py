from flask import Flask, request, render_template, g, session, redirect, flash, url_for
from secret import *
import sqlalchemy
import traceback
import requests
import json
import predictionio

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key

engine = sqlalchemy.create_engine(conn_str)
pio_client = predictionio.EventClient(
    access_key=access_key,
    url=eventserver_url,
    threads=5,
    qsize=500
)


@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except:
        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(_):
    if g.conn is not None:
        g.conn.close()


@app.route('/')
def home():
    n = 50  # number of recommendations

    no_movies = False  # whether there are no specific recommendations for the current user
    response = None
    if 'username' not in session:
        no_movies = True
    else:
        response = requests.post(engine_url, json.dumps({'user': session['username'], 'num': n}), verify=False)
        response = json.loads(response.text)['itemScores']
        if len(response) == 0:
            no_movies = True

    if no_movies:
        if 'username' in session:
            flash('There are no specific recommendations available for you at this moment. ' +
                  'Rate some movies and you\'ll see your recommendations next time.')
        else:
            flash('You are not logged in. Please log in to see recommendations for you.')
        cur = g.conn.execute('''
SELECT movie_id, year, title, plot, rated, released, runtime, genre, director, writer, actors,
       language, country, awards, poster, metascore, imdbrating, imdbvotes, type
FROM movies
WHERE random() < 0.01
LIMIT %s''', n)  # make random recommendations
        movies = [dict(zip(['movie_id', 'year', 'title', 'plot', 'rated', 'released',
                            'runtime', 'genre', 'director', 'writer', 'actors', 'language',
                            'country', 'awards', 'poster', 'metascore', 'imdbrating',
                            'imdbvotes', 'type'], row)) for row in cur]
        return render_template('home.html', movies=movies, rateable='username' in session)
    else:
        cur = g.conn.execute('''
SELECT movie_id, year, title, plot, rated, released, runtime, genre, director, writer, actors,
       language, country, awards, poster, metascore, imdbrating, imdbvotes, type
FROM movies
WHERE movie_id IN %s''', [(tuple(int(r['item']) for r in response),)])
        movie_info = {str(row[0]): row[1:] for row in cur}
        movies = []
        for movie in response:
            movie_id = movie['item']
            movies.append(dict(zip(['movie_id', 'year', 'title', 'plot', 'rated', 'released',
                                    'runtime', 'genre', 'director', 'writer', 'actors', 'language',
                                    'country', 'awards', 'poster', 'metascore', 'imdbrating',
                                    'imdbvotes', 'type', 'rating'],
                                   [movie_id] + list(movie_info[movie_id]) + ['{:.1f}'.format(movie['score'])])))
        return render_template('home.html', movies=movies, rateable=True)


@app.route('/rate', methods=['POST'])
def rate():
    if 'username' not in session:
        flash('You are not logged in.')
        return redirect(url_for('home'))
    ajax = request.json
    username, movie_id, rating = session['username'], int(ajax['movie_id']), float(ajax['rating'])
    with g.conn.begin() as _:
        g.conn.execute('DELETE FROM ratings WHERE username = %s AND movie_id = %s', (username, movie_id))
        g.conn.execute('INSERT INTO ratings VALUES (%s, %s, %s)', (username, movie_id, rating))
    pio_client.create_event(
        event="rate",
        entity_type="user",
        entity_id=username,
        target_entity_type="item",
        target_entity_id=str(movie_id),
        properties={"rating": rating}
    )
    return '', 204  # no response


@app.route('/myratings')
def myratings():
    if 'username' not in session:
        flash('You are not logged in.')
        return redirect(url_for('home'))
    cur = g.conn.execute('''
SELECT m.movie_id, year, title, plot, rated, released, runtime, genre, director, writer, actors,
       language, country, awards, poster, metascore, imdbrating, imdbvotes, type, rating
FROM movies m, ratings r
WHERE m.movie_id = r.movie_id AND r.username = %s''', session['username'])
    movies = [dict(zip(['movie_id', 'year', 'title', 'plot', 'rated', 'released',
                        'runtime', 'genre', 'director', 'writer', 'actors', 'language',
                        'country', 'awards', 'poster', 'metascore', 'imdbrating',
                        'imdbvotes', 'type', 'rating'], row)) for row in cur]
    return render_template('home.html', movies=movies, rateable=True)


@app.route('/search')
def search():
    keyword = request.args.get('keyword')
    cur = g.conn.execute('''
SELECT movie_id, year, title, plot, rated, released, runtime, genre, director, writer, actors,
       language, country, awards, poster, metascore, imdbrating, imdbvotes, type
FROM movies
WHERE title %% %s
LIMIT 10''', keyword)  # must enable the pg_trgm extension
    movies = [dict(zip(['movie_id', 'year', 'title', 'plot', 'rated', 'released',
                        'runtime', 'genre', 'director', 'writer', 'actors', 'language',
                        'country', 'awards', 'poster', 'metascore', 'imdbrating',
                        'imdbvotes', 'type'], row)) for row in cur]
    return render_template('home.html', movies=movies, rateable='username' in session)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        flash('You have already logged in as <b>{}</b>.'.format(session['username']))
        return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = g.conn.execute('''SELECT * FROM users WHERE username = %s AND password = %s''', (username, password))
        user = cur.fetchone()
        if user is None:
            error = 'Invalid username or password.'
        else:
            session['username'] = username
            flash('You are now logged in as <b>{}</b>.'.format(username))
            return redirect(url_for('home'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    if 'username' in session:
        flash('You are now logged out.')
        session.pop('username')
    return redirect(url_for('home'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            g.conn.execute('''INSERT INTO users (username, password) VALUES (%s, %s)''', (username, password))
            flash('Thank you for signing up!')
            session['username'] = username
            return redirect(url_for('home'))
        except Exception as e:
            error = str(e)
    return render_template('signup.html', error=error)

if __name__ == '__main__':
    app.run(debug=True)
