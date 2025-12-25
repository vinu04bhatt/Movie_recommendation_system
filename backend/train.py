import os
import pandas as pd
import numpy as np
import xgboost as xgb
from rules import GENRES

os.makedirs("model", exist_ok=True)

ratings = pd.read_csv("ratings.csv")
movies = pd.read_csv("movies.csv")

movies["genre_list"] = movies["genres"].str.split("|")

def build_target_vector(df):
    vec = np.zeros(len(GENRES))
    for genres in df["genre_list"]:
        for g in genres:
            if g in GENRES:
                vec[GENRES.index(g)] += 1
    return vec / vec.sum() if vec.sum() > 0 else vec

X, Y = [], []

for uid, grp in ratings.groupby("userId"):
    liked = grp[grp["rating"] >= 4]
    if len(liked) < 3:
        continue

    liked = liked.merge(movies, on="movieId")
    y = build_target_vector(liked)

    fav_movie_genres = liked.iloc[0]["genre_list"]
    x = np.zeros(len(GENRES))
    for g in fav_movie_genres:
        if g in GENRES:
            x[GENRES.index(g)] = 1

    X.append(x)
    Y.append(y)

X = np.array(X)
Y = np.array(Y)

model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    objective="reg:squarederror"
)

model.fit(X, Y)
model.save_model("model/xgb_model.json")

print("✅ XGBoost model trained and saved")
