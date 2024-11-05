from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, URL
from requests import get
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("flask_key")
bootstrap = Bootstrap5(app)

class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///blogs.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class Movie(db.Model):
    id:Mapped[int] = mapped_column(Integer, primary_key=True)
    title:Mapped[str] = mapped_column(String(250),unique=True, nullable=False)
    year:Mapped[int] = mapped_column(Integer, nullable=False)
    description:Mapped[str] = mapped_column(String(500),nullable=False)
    rating:Mapped[float] = mapped_column(Float, nullable=True)
    ranking:Mapped[int] = mapped_column(Integer, nullable=True)
    review:Mapped[str] = mapped_column(String(250),nullable=True)
    img_url:Mapped[str] = mapped_column(String(250),nullable=False)

class Update(FlaskForm):
    change_rating = FloatField("Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    change_review = StringField("Your Review", validators=[DataRequired()])
    submit = SubmitField("Done")

class Add(FlaskForm):
    movie_title=StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField('Add Movie')

with app.app_context():
    db.create_all()

def search_api(movie):
    search_prep = movie.split()
    if len(search_prep)>1:
        query = '%20'.join(search_prep)
    else:
        query = movie
        
    url = f"https://api.themoviedb.org/3/search/movie?query={query}&include_adult=false&language=en-US&page=1"
    headers = {
        "accept": "application/json",
        "Authorization": f'Bearer {os.getenv("tmdb_token")}'
    }
    response = get(url, headers=headers)
    return response.json()['results']


@app.route("/")
def home():
    # query = db.select(Movie)
    # all_movies = db.session.scalars(query)
    all_movies = db.session.execute(db.select(Movie).order_by(desc(Movie.rating))).scalars()
    list_of_movies = []
    for entry in all_movies:
        list_of_movies.append(entry.title)
    for num in range(len(list_of_movies)):
        ranked_movie = db.session.execute(db.select(Movie).where(Movie.title == list_of_movies[num])).scalar()
        ranked_movie.ranking = num+1
        db.session.commit()
    movies = db.session.execute(db.select(Movie).order_by(Movie.rating)).scalars()
    return render_template("index.html", movies=movies)


@app.route('/edit-<name>', methods=['GET','POST'])
def edit(name):
    form = Update()
    movie = db.session.get(Movie, name)
    if form.validate_on_submit():
        movie_to_update = db.session.execute(db.select(Movie).where(Movie.title == name)).scalar()
        movie_to_update.rating = float(form.change_rating.data)
        movie_to_update.review = form.change_review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", movie=movie, form=form)


@app.route("/<int:num>")
def delete_movie(num):
    movie_to_delete = db.get_or_404(Movie,num)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/select<movie>')
def select(movie):
    titles = search_api(movie)
    return render_template('select.html', titles=titles)


@app.route('/add', methods=['GET','POST'])
def add_movie():
    form = Add()
    if form.validate_on_submit():
        movie=form.movie_title.data
        return redirect(url_for('select', movie=movie))
    return render_template("add.html", form=form)


@app.route('/<int:id><movie>')
def add_title(id, movie):
    titles = search_api(movie)
    for item in titles:
        if item["id"] == id:
            movie_name = item['original_title']
            new_movie = Movie(
                title= item['original_title'],
                year= int(item['release_date'].split('-')[0]),
                description= item['overview'],
                # rating= round(item['vote_average'], 1),
                img_url= f"https://image.tmdb.org/t/p/original{item['poster_path']}"
                )
    try:
        db.session.add(new_movie)
    except UnboundLocalError:
        print("Error")
        new_movie=None
        movie_name=None
    db.session.commit()
    return redirect(url_for('edit', name=movie_name))
    
if __name__ == '__main__':
    app.run(debug=True)
