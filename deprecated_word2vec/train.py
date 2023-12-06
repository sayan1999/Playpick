import logging
import pandas as pd
from collections import Counter
from gensim.models import Word2Vec

logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
)

MIN_NO_RATINGS = 100
MIN_RATING = 3

# read imdb data
movies = pd.read_csv("data/ml-latest/movies.csv")
ratings = pd.read_csv("data/ml-latest/ratings.csv")

# fetch userdata
movieidx = movies.merge(
    ratings[["movieId", "rating"]].groupby("movieId").aggregate("mean"), on="movieId"
).set_index("movieId")
goodmovies = movieidx[movieidx["rating"] >= MIN_RATING].index.to_list()
movieidx = movieidx[movieidx["rating"] >= MIN_RATING]
titletomovie = movies[["movieId", "title"]].set_index("title").to_dict()["movieId"]
genres = movies[["movieId", "genres"]].set_index("movieId").to_dict()["genres"]

ratings = ratings[ratings["movieId"].isin(goodmovies)]
moviesByUser = ratings.groupby("userId")["movieId"].apply(list)
moviesByUser = moviesByUser[moviesByUser.apply(len) > MIN_NO_RATINGS]


# word2vec model to get similarity embeddings
model = Word2Vec(
    window=10,
    sg=1,
    hs=0,
    negative=10,
    alpha=0.03,
    min_alpha=0.0007,
    min_count=50,
    seed=14,
    workers=20,
)
model.build_vocab(moviesByUser, progress_per=200)
model.train(moviesByUser, total_examples=model.corpus_count, epochs=10, report_delay=1)
model.save("movielens.model")
