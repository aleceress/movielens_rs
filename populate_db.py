import pandas as pd
from py2neo import *
import re
import uuid
import pickle
from tqdm import tqdm
from py2neo import bulk
import gc
import getpass

GENRES = [
    "Action",
    "Adventure",
    "Animation",
    "Children",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Fantasy",
    "Film-Noir",
    "Horror",
    "Musical",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Thriller",
    "War",
    "Western",
    "IMAX"
]

TRANSACTION_DIM = 10_000

# preprocess movie csv table, removing year from title and adding it as a new column
def preprocess_movies(movie_db):
    exp = re.compile(r"\((\d+)\)")
    for i, movie in movie_db.iterrows():
        movie_db.at[i, "title"] = " ".join(movie.title.split()[:-1]).replace('"', '\\"')
        year = exp.findall(movie.title)
        movie_db.at[i, "year"] = (
            int(exp.findall(movie.title)[-1]) if len(year) > 0 else -1
        )

    movie_db["year"] = movie_db["year"].astype("Int64")
    return movie_db


# preprocess ratings, converting the score to integer
def preprocess_ratings(ratings_db):
    ratings_db["rating"] = ratings_db["rating"].astype(int)
    return ratings_db


# creates an hash table from ids to uuids
def create_uuid_associations(ids):
    uuid_associations = dict()
    for id in ids:
        uuid_associations[id] = str(uuid.uuid4())
    return uuid_associations


# creates a node of every type, when we pass the type of the node as labels and the properties
def create_node(label, **properties):
    graph.run(
        # the properties are iterated from the dictionary passed, with a type check to add "" if the property is a string
        f"CREATE (n:{label}{{"
        + ",".join(
            [
                f"{k}:" + (f'"{v}"' if type(v) == str else str(v))
                for k, v in properties.items()
            ]
        )
        + f"}})"
    )


# empties the graph 1000 transactions at a time
def empty_graph():
    while (
        graph.run(
            f"""
            MATCH ()-[r]->()
            // Take the first 10k nodes and their rels (if more than 100 rels / node on average lower this number)
            WITH r LIMIT {TRANSACTION_DIM}
            DELETE r
            RETURN count(*);
            """
        ).data()[0]["count(*)"]
        != 0
    ):
        continue

    while (
        graph.run(
            f"""
            MATCH (n)
            // Take the first 10k nodes and their rels (if more than 100 rels / node on average lower this number)
            WITH n LIMIT {TRANSACTION_DIM}
            DELETE n
            RETURN count(*);
            """
        ).data()[0]["count(*)"]
        != 0
    ):
        pass


def create_node_index(name, label, property):
    graph.run(f"CREATE INDEX {name} IF NOT EXISTS FOR (n:{label}) ON n.{property}")

def create_relationship_index(name, rel_type, property):
    graph.run(f"CREATE INDEX {name} IF NOT EXISTS FOR ()-[r:{rel_type}]->() ON r.{property}")


def create_relationship(
    start_node_label, start_node_id, rel_name, end_node_label, end_node_id
):
    graph.run(
        f"""
            MATCH (n1:{start_node_label}{{id: '{start_node_id}'}}),
                  (n2:{end_node_label}{{id:'{end_node_id}'}})
            CREATE (n1)-[r:{rel_name}]->(n2)
            """
    )


def create_bulk_data(table, properties):
    if len(properties) != 0:
        table["properties"] = table.loc[
            :, [property for property in properties]
        ].values.tolist()
        table = table.drop(columns=[property for property in properties])
        table = table[[table.columns[0], table.columns[2], table.columns[1]]]

    table = table.to_records(index=False).tolist()
    return table


def split_in_batches(func, batch_size=TRANSACTION_DIM):
    def wrapper(data, *args, **kwargs):
        data_len = len(data)
        for i in tqdm(range(0, data_len, batch_size)):
            func(
                data[i : batch_size + i if batch_size + i < data_len else -1],
                *args,
                **kwargs,
            )

    return wrapper


@split_in_batches
def create_bulk_relationships(
    relationship_data, name, start_node_key, end_node_key, keys
):
    bulk.create_relationships(
        graph.auto(),
        relationship_data,
        name,
        start_node_key=start_node_key,
        end_node_key=end_node_key,
        keys=keys,
    )


# creates connection with graph
username = input("Enter username: ")
password = getpass.getpass('Enter password: ')
port = input("Enter Neo4j listening port: ")
graph = Graph(f"bolt://localhost:{port}", auth=(username, password))


if (
    input(
        "Do you want to delete all the data in the default neo4j database? "
        "(n will create duplicates if you execute the script more than once) [y/n] "
    ).lower()
    == "y"
):
    print("deleting nodes and relationships...")
    empty_graph()


print("Generating USER uuids...")
ratings = preprocess_ratings(pd.read_csv("data/ratings.csv"))
users_uuid_associations = create_uuid_associations(ratings.userId.unique())
with open("data/users_uuids.pkl", "wb+") as f:
    pickle.dump(users_uuid_associations, f)


print("Creating USER nodes...")
for user_id in tqdm(ratings.userId.unique()):
    create_node("User", id=users_uuid_associations[user_id])

print("Generating GENRE uuids...")

genre_uuid_associations = create_uuid_associations(GENRES)
with open("data/genre_uuids.pkl", "wb+") as f:
    pickle.dump(genre_uuid_associations, f)



print("Creating GENRE nodes...")
for genre_name in GENRES:
    create_node("Genre", id=genre_uuid_associations[genre_name], name=genre_name)



print("Generating CATEGORY uuids...")

categories = pd.read_csv("data/genome-tags.csv")

categories_uuid_associations = create_uuid_associations(categories.tagId.values)
with open("data/categories_uuids.pkl", "wb+") as f:
    pickle.dump(categories_uuid_associations, f)

print("Creating CATEGORY nodes...")
for i, category in categories.iterrows():
    create_node(
        "Category", id=categories_uuid_associations[category.tagId], name=category.tag
    )

del categories
gc.collect()

print("Generating MOVIE uuids...")
movies = preprocess_movies(pd.read_csv("data/movies.csv"))
movies_uuid_associations = create_uuid_associations(movies.movieId.values)
with open("data/movies_uuids.pkl", "wb+") as f:
    pickle.dump(movies_uuid_associations, f)


print("Creating MOVIE nodes...")
for i, movie in tqdm(movies.iterrows(), total=len(movies)):
    create_node(
        "Movie",
        id=movies_uuid_associations[movie.movieId],
        title=movie.title,
        year=movie.year,
    )



# creating indexes to enhance performances in relationship creation
create_node_index("movie_index", "Movie", "id")
create_node_index("user_index", "User", "id")
create_node_index("category_index", "Category", "id")
create_node_index("genre_index", "Genre", "id")


create_relationship_index("rates_index", "RATES", "score")
create_relationship_index("has_category_index", "HAS_CATEGORY", "relevance")

print("Generating (Movie)-HAS_GENRE->(Genre) relationships...")

for i, movie in tqdm(movies.iterrows(), total=len(movies)):
    for genre in movie.genres.split("|"):
        if genre == "(no genres listed)":
            continue
        create_relationship(
            "Movie", 
            movies_uuid_associations[movie.movieId],
            "HAS_GENRE",
            "Genre", 
            genre_uuid_associations[genre]
)

del movies
gc.collect()


print("Generating bulk data (User)-[:RATES]->(Movie)...")
ratings["userId"] = ratings["userId"].apply(lambda id: users_uuid_associations[id])
ratings["movieId"] = ratings["movieId"].apply(lambda id: movies_uuid_associations[id])
rating_relationships_data = create_bulk_data(ratings, ["rating", "timestamp"])

del ratings
gc.collect()

print("Generating relationships from data...")
create_bulk_relationships(
    rating_relationships_data, "RATES", ("User", "id"), ("Movie", "id"), ["score"]
)

del rating_relationships_data
gc.collect()

categories_scores = pd.read_csv("data/genome-scores.csv")

print("Generating bulk data (Movie)-[:HAS_CATEGORY]->(Category)...")
categories_scores = categories_scores[categories_scores.relevance >= 0.4]

categories_scores["tagId"] = categories_scores["tagId"].apply(
    lambda id: categories_uuid_associations[id]
)
categories_scores["movieId"] = categories_scores["movieId"].apply(
    lambda id: movies_uuid_associations[id]
)
categories_scores_relationships_data = create_bulk_data(
    categories_scores, ["relevance"]
)

del categories_scores
gc.collect()

print("Generating relationships from data...")
create_bulk_relationships(
    categories_scores_relationships_data,
    "HAS_CATEGORY",
    ("Movie", "id"),
    ("Category", "id"),
    ["relevance"],
)

del categories_scores_relationships_data
gc.collect()
