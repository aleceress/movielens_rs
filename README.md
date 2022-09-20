# __A Neo4j Recommender System__
This repository contains the implementation of a __Recommender System__ in __Neo4j__.

### __Dataset__

The data used for recommendation come from some of the tables of the [MovieLens 25M Dataset](https://grouplens.org/datasets/movielens/25m/), specifically `ratings.csv`, `movies.csv`, `tags.csv`, `genome-scores.csv` and `genome-tags.csv`. You need to insert them in a `data` folder.

### __Population script__
The script [populate_db.py](https://github.com/aleceress/movielens_rs/blob/main/populate_db.py) populates a pre-existing Neo4j graph with data from these tables. An example of instantiation of the graph can be seen in figure.

![](https://i.ibb.co/645mdHs/graph.png)

The script is gonna generate some pickle files in the data folder (serialized dictionaries that map original dataset ids to the UUIDs used in the Neo4j database).

__NB:__ you need to have a Neo4j database running on your machine (connection is to localhost). The script is gonna ask you if you want to delete your data from the current database: this is done because if you execute the script twice, all data will be duplicated.

### __Recommendation__

The file [datasetanalysis.ipynb](https://github.com/aleceress/movielens_rs/blob/main/datasetanalysis.ipynb) contains some statistics on the dataset that help understand performance.

The file [queries.ipynb](https://github.com/aleceress/movielens_rs/blob/main/queries.ipynb) contains execution and performance measures of the queries implied by the following __workflow__.

---
1. Given a __User__, find his __top k Genres__
2. Given a __User__, find his __top k Categories__
3. Given a __Genre__, find its __top k Users__
4. Given a __Category__, find its __top k Users__
5. Given a __User__, find __similar users__
6. Given a __Users__, recommend __Movies__ based on __similar Users__
7. Given a __Movie__, find __similar Movies__
8. Given a __User__, recommend __Movies__ based on __similarity__ with the ones he has rated.
---

The file [gds_recommendation.py](https://github.com/aleceress/movielens_rs/blob/main/gds_recommendation.py) contains some functions used for the recommendation, basically wrappers of some [GDS library](https://neo4j.com/docs/graph-data-science/current/algorithms/) functions.

[Relazione.pdf](https://github.com/aleceress/movielens_rs/blob/main/Relazione.pdf) and [Neo4j Recommender System.pdf](https://github.com/aleceress/movielens_rs/blob/main/Neo4j%20Recommender%20System.pdf) contain a  deeper discussion on the project (in italian) and a summary presentation of it (in english).

### __Running__
 
To run all the code in the respository, you can create a virtual environment and run the following commands.

```
virtualenv venv 
source ./venv/bin/activate
pip install -r requirements.txt
```

Non enterprise versions of Neo4j do not consent to have more than one active database at the time: if you don't want to use the default database `neo4j`, you can create a new one and activate it following [this procedure](https://stackoverflow.com/questions/45784232/how-to-create-new-database-in-neo4j/45802452#45802452).

__NB__: it is advisable to execute the script [populate_db.py](https://stackoverflow.com/questions/45784232/how-to-create-new-database-in-neo4j/45802452#45802452) on a machine with at least 8 GB of RAM.