import pandas as pd
import streamlit as st
from gensim.models import Word2Vec
import os, json, random
import numpy as np
from streamlit_star_rating import st_star_rating
import imdb, glob

RANDOM = 50
CORRELATED = 300
N_REC = 40


# def get_cover_link(ID):
# try:
#     movie = IMDB.get_movie(ID)
#     return movie["cover url"]
# except:
#     print("Failed to get IMDB image")
#     return ""


@st.cache_resource
def init():
    movies = pd.read_csv("data/ml-latest/movies.csv")
    ratings = pd.read_csv("data/ml-latest/ratings.csv")
    urls = pd.read_csv("data/ml-latest/links.csv")

    MIN_NO_RATINGS = 100
    MIN_RATING = 3

    movieidx = (
        movies.merge(
            ratings[["movieId", "rating"]].groupby("movieId").aggregate("mean"),
            on="movieId",
        )
        .merge(urls, on="movieId")
        .set_index("movieId")
    )
    goodmovies = movieidx[movieidx["rating"] >= MIN_RATING].index.to_list()
    movieidx = movieidx[movieidx["rating"] >= MIN_RATING]
    movieidx["year"] = (
        movieidx["title"]
        .str.extractall(r"\((\d{4})\)$")
        .reset_index()
        .drop_duplicates("movieId", keep="last")
        .set_index("movieId")[0]
    )
    titletomovie = movies[["movieId", "title"]].set_index("title").to_dict()["movieId"]
    genres = movies[["movieId", "genres"]].set_index("movieId").to_dict()["genres"]
    # ratings = ratings[ratings["movieId"].isin(goodmovies)]
    # moviesByUser = ratings.groupby("userId")["movieId"].apply(list)
    # moviesByUser = moviesByUser[moviesByUser.apply(len) > MIN_NO_RATINGS]
    model = Word2Vec.load("movielens.model")
    return movies, ratings, movieidx, titletomovie, genres, model


@st.cache_data
def n_similar_movies(v, n=6):
    if v in model.wv.key_to_index:
        ms = model.wv.most_similar(v, topn=n + 1)[1:]
        new_ms = []
        for j in ms:
            new_ms.append(movieidx.loc[j[0]].title)
        return new_ms
    return []


@st.cache_data
def get_relevant(movie="Transformers (2007)"):
    if type(movie) is not int:
        movie = titletomovie[movie]
    n = 7
    return n_similar_movies(movie, n)


@st.cache_data
def get_recommendation(movieswatched, n_top=20):
    print("Fetching recommendations...")
    recommendations = [
        relevant
        for movie in movieswatched
        for relevant in get_relevant(movie)
        if relevant not in movieswatched
    ]
    randomized_recommendations = random.sample(
        recommendations, min(len(recommendations), CORRELATED)
    )
    others = movieidx[
        (
            (~movieidx.title.isin(recommendations + movieswatched))
            & (movieidx.rating > 3)
        )
    ]

    randoms = list(
        np.random.choice(
            others.title.to_list(),
            RANDOM,
            (others.rating / others.rating.sum()).to_list(),
        )
    )
    return (
        movieidx[
            movieidx.title.isin(
                random.sample(
                    randomized_recommendations + randoms,
                    n_top,
                )
            )
        ]
        .sort_values("year", ascending=False)
        .reset_index()
    )


@st.cache_data
def get_movies():
    return movies.sort_values("title", ascending=False).title.to_list()


def get_users():
    return [f.split("_", 1)[0] for f in os.listdir("users")]


def create_user(user, passw):
    user, passw = user.strip(), passw.strip()
    if user.strip() == "":
        return "empty user", False
    if "_" in user:
        return "dont use _ in username", False
    if user in map(lambda x: x.split("_", 1)[0], os.listdir("users")):
        return "User already exists", False
    if passw.strip() == "":
        return "empty password", False
    json.dump(
        [],
        open(os.path.join("users", user + "_" + passw + ".json"), "w+"),
    )
    return "", True


def validate_passw(user, passw):
    if os.path.isfile(os.path.join("users", user + "_" + passw + ".json")):
        return True
    return False


def get_user_movies(user):
    return json.load(
        open(glob.glob(os.path.join("users", user + "_" + "*" + ".json"))[0])
    )


def add_user_movies(user, movies):
    print(f"Saving {movies} for {user}")
    return json.dump(
        list(set(get_user_movies(user) + movies)),
        open(glob.glob(os.path.join("users", user + "_" + "*" + ".json"))[0], "w+"),
    )


def to_refresh():
    # print(f'{st.session_state.get("FormSubmitter:recommendations-Submit")=}')
    return st.session_state.get("FormSubmitter:recommendations-Submit") not in [
        None,
        True,
    ]


if __name__ == "__main__":
    print("\n" * 3)
    st.set_page_config(layout="wide", page_title="PlayPick")
    st.title("PlayPick")
    st.write(
        "**Confused? Which movie to watch next? I am PlayPick, I shall help you pick the best movie to watch next for You.**"
    )

    movies, ratings, movieidx, titletomovie, genres, model = init()

    user = st.selectbox(
        "Select an account",
        ["Choose", "Create account"] + get_users(),
        placeholder="Select User",
    )
    if user not in ["", "Choose"]:
        if user == "Create account":
            placeholder = st.empty()
            with placeholder.container():
                newuser = st.text_input("Enter your name", max_chars=20).strip()
                newpass = st.text_input(
                    "Enter password", type="password", max_chars=20
                ).strip()
                submituser = st.button("Submit")
                if submituser and newuser:
                    err, sts = create_user(newuser, newpass)
                    if sts:
                        user = newuser
                        st.text("User account created, refresh to start now")
                        if st.button("Refresh"):
                            placeholder.empty()
                    else:
                        st.text(err)
            pass
        else:
            passw = st.text_input("Enter password", type="password").strip()
            if validate_passw(user, passw):
                selected = st.selectbox(
                    "Tell us movies you have watched",
                    [""] + get_movies(),
                    placeholder="Select movie",
                )
                if selected:
                    add_user_movies(user, [selected])
                placeholder2 = st.empty()
                with placeholder2.container():
                    st.text(
                        "Mark the Movies you have watched and we'll improve our recommendation"
                    )
                    with st.form(
                        "recommendations",
                    ):
                        if not to_refresh():
                            print("Serving cached results...")
                            st.session_state["movies"] = st.session_state.get(
                                "movies", get_user_movies(user)
                            )
                            df = pd.DataFrame(
                                get_recommendation(
                                    st.session_state["movies"], n_top=N_REC
                                )
                            )
                        else:
                            print("New results...")
                            st.session_state["movies"] = get_user_movies(user)
                            random.shuffle(st.session_state["movies"])
                            df = pd.DataFrame(
                                get_recommendation(
                                    st.session_state["movies"], n_top=N_REC
                                )
                            )
                        selections = []
                        thumbnails = []
                        thumblink_link = []
                        for i in range(len(df)):
                            movie, genre, rating, movieId = df.iloc[i][
                                ["title", "genres", "rating", "movieId"]
                            ].tolist()
                            genre = genre.replace("|", ", ")
                            col1, col2, col3, col4, col5 = st.columns([3, 2, 0.5, 2, 3])
                            with col1:
                                selections.append(
                                    st.checkbox(movie, key=str(i) + movie)
                                )
                            col2.write(genre)
                            col3.write(round(rating, 1))
                            with col4:
                                stars = st_star_rating(
                                    "",
                                    5,
                                    round(rating),
                                    size=20,
                                    emoticons=True,
                                    read_only=True,
                                    key=str(i) + movie + str(rating),
                                )
                            with col5:
                                st.write(
                                    "**Matched from:** "
                                    + "; ".join(
                                        list(
                                            set(get_relevant(movie)).intersection(
                                                st.session_state["movies"]
                                            )
                                        )[:4]
                                        or ["Random"]
                                    ),
                                )
                        form_submitted = st.form_submit_button("Submit")

                if form_submitted:
                    add_user_movies(user, df.title[selections].to_list())
                    placeholder2.empty()
                    st.text(
                        "Submitted your watched movies, refresh to get fresh recommendations..."
                    )

                recommend = st.button("Recommend")
                st.text("Movies watched by you...")
                st.write(", ".join(get_user_movies(user)))

                # IMDB = imdb.IMDb()
                # for plc, ID in zip(thumbnails, thumblink_link):
                #     if get_cover_link(ID):
                #         plc.image(get_cover_link(ID))

            else:
                st.text("Authentication failed")
