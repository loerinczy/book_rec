import pandas as pd

df = pd.read_csv("./Books.csv", encoding="cp1251", sep=";", on_bad_lines="skip")
df[["ISBN", "Book-Title", "Book-Author"]].to_csv("Books_clean.csv")
