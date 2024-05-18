"""
# My first app
Here's our first attempt at using data to create a table:
"""

import streamlit as st
import pandas as pd
import numpy as np
import crate.client as client
import os
import json
import boto3


def get_cratedb_password():

    secret_name = "dome_cratedb_password"
    region_name = "eu-west-3"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response["SecretString"]
        secret = json.loads(secret)["cratedb_password"]
    except:
        secret = os.getenv("CRATEDB_PASSWORD")

    return secret


def get_matching_entry(author: str, book: str):
    select_stmt = f"""
        select * 
        from dome.books_search 
        where 
            match(title, '{book}') 
            and match(author, '{author}') 
        limit 1"""

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(select_stmt)
        entry = cursor.fetchall()
    return entry


def get_connection() -> client.connection.Connection:
    connection = client.connect(
        "https://beige-nute-gunray.aks1.eastus2.azure.cratedb.net:4200",
        username="admin",
        password=get_cratedb_password(),
    )
    return connection


def recommend(selected_author: str, selected_book: str, top_k: int):
    # standardize
    selected_author = selected_author.lower()
    selected_book = selected_book.lower()

    # load ratings
    ratings = pd.read_csv("/data/Ratings.csv", encoding="cp1251", sep=";")
    ratings = ratings[ratings["Book-Rating"] != 0]

    # load books
    books = pd.read_csv(
        "/data/Books.csv", encoding="cp1251", sep=";", on_bad_lines="skip"
    )

    # users_ratigs = pd.merge(ratings, users, on=['User-ID'])
    dataset = pd.merge(ratings, books, on=["ISBN"])
    dataset_lowercase = dataset.apply(
        lambda x: x.str.lower() if (x.dtype == "object") else x
    )

    selected_author_readers = dataset_lowercase["User-ID"][
        (dataset_lowercase["Book-Title"] == selected_book)
        & (dataset_lowercase["Book-Author"].str.contains(selected_author))
    ]
    selected_author_readers = selected_author_readers.tolist()
    selected_author_readers = np.unique(selected_author_readers)

    # final dataset
    books_of_selected_author_readers = dataset_lowercase[
        (dataset_lowercase["User-ID"].isin(selected_author_readers))
    ]

    # Number of ratings per other books in dataset
    number_of_rating_per_book = (
        books_of_selected_author_readers.groupby(["Book-Title"])
        .agg("count")
        .reset_index()
    )

    # select only books which have actually higher number of ratings than threshold
    books_to_compare = number_of_rating_per_book["Book-Title"][
        number_of_rating_per_book["User-ID"] >= 8
    ]
    books_to_compare = books_to_compare.tolist()

    if selected_book not in books_to_compare:
        return None

    ratings_data_raw = books_of_selected_author_readers[
        ["User-ID", "Book-Rating", "Book-Title"]
    ][books_of_selected_author_readers["Book-Title"].isin(books_to_compare)]

    # group by User and Book and compute mean
    ratings_data_raw_nodup = ratings_data_raw.groupby(["User-ID", "Book-Title"])[
        "Book-Rating"
    ].mean()

    # reset index to see User-ID in every row
    ratings_data_raw_nodup = ratings_data_raw_nodup.to_frame().reset_index()

    dataset_for_corr = ratings_data_raw_nodup.pivot(
        index="User-ID", columns="Book-Title", values="Book-Rating"
    )

    result_list = []

    # Take out the Lord of the Rings selected book from correlation dataframe
    dataset_of_other_books = dataset_for_corr.copy(deep=False)
    dataset_of_other_books.drop([selected_book], axis=1, inplace=True)

    # empty lists
    book_titles = []
    correlations = []
    avgrating = []

    # corr computation
    for book_title in list(dataset_of_other_books.columns.values):
        book_titles.append(book_title)
        correlations.append(
            dataset_for_corr[selected_book].corr(dataset_of_other_books[book_title])
        )
        tab = (
            ratings_data_raw[ratings_data_raw["Book-Title"] == book_title]
            .groupby(ratings_data_raw["Book-Title"])["Book-Rating"]
            .mean()
        )
        avgrating.append(tab.values[0])
    # final dataframe of all correlation of each book
    corr_fellowship = pd.DataFrame(
        list(zip(book_titles, correlations, avgrating)),
        columns=["book", "corr", "avg_rating"],
    )
    corr_fellowship.head()

    # top 10 books with highest corr
    result_list.append(corr_fellowship.sort_values("corr", ascending=False).head(top_k))
    result_list = result_list[0]["book"].values

    return result_list


# rec_list = recommend(
#     "tolkien", "the fellowship of the ring (the lord of the rings, part 1)", 5
# )
# print(rec_list)

if "author" not in st.session_state:
    st.session_state.author = ""
if "book" not in st.session_state:
    st.session_state.book = ""
if "top_k" not in st.session_state:
    st.session_state.top_k = 5

st.session_state.author = st.text_input(
    label="Who is the author of the book?", value=st.session_state.author
)
st.session_state.book = st.text_input(
    label="What is your favorite book?", value=st.session_state.book
)

st.session_state.top_k = st.slider(
    label="How many books should I recommend?",
    min_value=0,
    max_value=10,
    value=0,
)

run = st.button("Submit")
if run:
    entry = get_matching_entry(st.session_state.author, st.session_state.book)
    if entry:
        author = entry[0][2]
        book = entry[0][1]
        st.write(f"Found book: {author}: {book}")
        rec_list = recommend(author, book, st.session_state.top_k)

        if rec_list is None:
            st.write(
                "Sorry, as there are less than 8 ratings for the selected book,"
                " we cannot recommend based on it."
            )
        else:
            s = ""

            for i in rec_list:
                s += "- " + i + "\n"

            st.write(f"Here are the first {st.session_state.top_k} recommended books:")
            st.markdown(s)
    else:
        st.write(
            "It looks like there is not matching book,"
            " please try with different input!"
        )
