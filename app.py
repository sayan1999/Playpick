import pandas as pd
import streamlit as st
import os, json, random
import numpy as np
from streamlit_star_rating import st_star_rating
import imdb, glob
import datetime
from db import DB
import streamlit_analytics
import pysplitter as pysp


def load_numpy():
    pysp.unsplit(
        "model/splits/corr*.split",
        "model/reconstructedcorr.npy",
    )
    print(os.listdir("model"))
    return np.load("model/reconstructedcorr.npy")


N_REC = 40
N_RANDOM = 10


@st.cache_resource
def init():
    columns = json.load(open("model/columns.json"))
    corr = pd.DataFrame(load_numpy(), columns=columns, index=columns)
    corr = corr[~corr.index.duplicated(keep="first")]
    moviesinfo = pd.read_csv("model/moviesinfo.csv")
    db = DB()
    IMDB = imdb.IMDb()
    return (
        IMDB,
        db,
        corr,
        moviesinfo.drop_duplicates(["title"], keep="first")
        .sort_values("rating", ascending=False)
        .set_index("title"),
    )


#  **************************************************************** Recommendation logic ****************************************************


@st.cache_data
def get_relevant(movie_name, user_rating):
    sim = corr[movie_name] * (user_rating - 2.5)
    return sim


@st.cache_data
def get_recommendation(movieswatched, n_top=N_REC):
    print("Fetching recommendations...")
    if not len(movieswatched):
        return moviesinfo.loc[get_random()]
    already_watched = list(dict(movieswatched).keys())
    allrec = pd.concat(
        [get_relevant(movie_name, rating) for movie_name, rating in movieswatched],
        axis=1,
    ).sum(1)
    newrec = (
        allrec[~allrec.index.isin(already_watched)]
        .sort_values(ascending=False)
        .index.to_list()[:n_top]
    )
    return moviesinfo.loc[newrec + get_random(exceptfor=newrec + already_watched)]


@st.cache_data
def get_random(exceptfor=[]):
    randomlist = (
        moviesinfo[~moviesinfo.index.isin(exceptfor)]
        .query("Reviews > 10000")
        .sample(n=N_RANDOM)
        .index.to_list()
    )
    return randomlist


@st.cache_data
def get_movies():
    return moviesinfo.sort_values("Reviews", ascending=False).index.to_list()


# ************************** Authentication utils ***************************************************


def get_users():
    return db.get_users()


def create_user(user, passw):
    user, passw = user.strip(), passw.strip()
    if user.strip() == "":
        return "empty user", False
    if "_" in user:
        return "dont use _ in username", False
    if user in get_users():
        return "User already exists", False
    if passw.strip() == "":
        return "empty password", False
    db.create_user(user, passw)
    return "", True


def validate_passw(user, passw):
    return db.validate_passw(user, passw)


def get_user_movies(user):
    return list(
        map(
            tuple,
            db.get_user_movies(user),
        )
    )


def add_user_movies(user, movies):
    print(f"Saving {movies} for {user}")
    return db.add_user_movies(user, movies)


def to_refresh():
    # print(st.session_state)
    # print(f'{st.session_state.get("FormSubmitter:recommendations-Submit")=}')
    return st.session_state.get("FormSubmitter:recommendations-Submit") not in [
        None,
        True,
    ]


@st.cache_data
def get_cover_link(movie):
    try:
        return IMDB.get_movie(IMDB.search_movie(movie)[0].getID())["cover url"]
    except:
        return None


if __name__ == "__main__":
    with streamlit_analytics.track(unsafe_password="credict123"):
        print("*" * 100, "\n")
        st.set_page_config(layout="wide", page_title="PlayPick")
        st.title("PlayPick")
        st.write(
            "**Confused? Which movie to watch next? I am PlayPick, I shall help you pick the best movie to watch next for You.**"
        )

        IMDB, db, corr, moviesinfo = init()

        #  *********************************** User authentication ***********************************************
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
                if passw:
                    if validate_passw(user, passw):
                        #  *********************************** authentication done, recommendation now ***********************************************

                        # ******************************* manual search ***************************
                        selected = st.selectbox(
                            "Tell us movies you have watched",
                            [""] + get_movies(),
                            placeholder="Select movie",
                        )
                        if selected:
                            rate = st.number_input(
                                f"Rate {selected} 1-5",
                                min_value=1,
                                max_value=5,
                                value=None,
                            )
                            if rate:
                                add_user_movies(user, [(selected, rate)])

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

                                else:
                                    print("New results...")
                                    st.session_state["movies"] = get_user_movies(user)

                                rec = get_recommendation(st.session_state["movies"])

                                selections = []
                                stars = []
                                thumbnails = []
                                thumbnail_link = []

                                col1, col2, col3, col4, col5 = st.columns(
                                    [3, 4, 1, 1, 5]
                                )
                                col1.text("Title")
                                col2.text("Genre")
                                col3.write("IMDB Rating")
                                col4.write("IMDB rating")
                                col5.write("Your rating")
                                for i, (movie, genre, rating, reviews) in enumerate(
                                    rec.reset_index().values.tolist()
                                ):
                                    # print("Debug", st.session_state)
                                    if i == len(rec) - N_RANDOM:
                                        st.markdown(
                                            "Some random recommendations as well..."
                                        )
                                    col1, col2, col3, col4, col5 = st.columns(
                                        [3, 4, 1, 1, 5]
                                    )
                                    with col1:
                                        selections.append(
                                            st.checkbox(
                                                movie,
                                                key="Checkbox_" + movie,
                                            )
                                        )
                                    col2.markdown(genre)
                                    col3.text(round(rating, 1))
                                    col4.write(int(reviews))
                                    with col5:
                                        stars.append(
                                            st_star_rating(
                                                "",
                                                5,
                                                5,
                                                size=15,
                                                read_only=False,
                                                key="Star_" + movie,
                                            )
                                        )
                                    # thumbnails.append(st.empty())
                                    # thumbnail_link.append(movie)

                                form_submitted = st.form_submit_button("Submit")

                        if form_submitted:
                            add_user_movies(
                                user,
                                [
                                    (rec.index.tolist()[i], stars[i])
                                    for i, sel in enumerate(selections)
                                    if sel
                                ],
                            )
                            placeholder2.empty()
                            st.text(
                                "Submitted your watched movies, refresh to get fresh recommendations..."
                            )

                        recommend = st.button("Recommend")
                        st.text("Movies watched by you...")
                        st.write(str(get_user_movies(user)))

                        # for plc, movie in zip(thumbnails, thumbnail_link):
                        #     if get_cover_link(movie):
                        #         plc.image(get_cover_link(movie))

                    else:
                        st.text("Authentication failed")
