# DBMS Project

## Reasons

### Why using this instead of other RS models

> Firstly, the need to determine either similar users or similar items in order to make predictions can be impractical in large scale settings. Secondly, the sparsity of the user rating matrix creates challenges for robust similarity computation.
~ Matteo Cimini [[source](https://medium.com/quantyca/graph-based-real-time-recommendation-systems-8a6b3909b603)]

> __Problem with batch learning (pre-calculated)__ : a better approach would be to react to the customer’s actions while they are still browsing your site, and recalculate their recommendations in real time, for example, to suggest accessories, pants or shirt to match the new pair of sunglasses. 


### __Computational cost (vs Reational databases)__

Relational databases can model relationships; but to traverse those relationships, you need to write SQL queries that JOIN tables together. The joining process is computationally expensive, and becomes slower as the number of joins increases, which makes real-time analysis impractical in production,

> The key point to notice here is that both steps of the process depend on relationships: first, the relationship between customers, and second, the relationships between the customers and their purchases. The faster you can query and traverse these relationships, the stronger your ability is to deliver recommendations in real time.

> In addition, using a graph data structure for storing the data, we can easily traverse through the graph, finding patterns our users have in common.

> As a result, you can perform relationship-based queries in real time, and quickly query customers’ past purchases, as well as instantly capture any new interests shown in their current online visit, both of which are essential for making real-time recommendations.

> Graph Databases can make recommendations more personalized by including contextual informations by leveraging connections between your data.


## __Data__


### Movie database [[method](https://47billion.com/blog/recommendation-system-using-graph-database/),  [db](https://grouplens.org/datasets/movielens/25m/)]

### __Tools__
- [py2neo](https://py2neo.org/2021.1/)
- sudo systemctl start neo4j
- sudo systemctl status neo4j


### __UML diagram__

![img](UMLdiagram.drawio.png)

__Constraints__:

- There could be users that haven't rated any item (even if otherwise he is not in the dump, since it is a N to N table of ratings, it is really common to have new users, and we could manage the __cold start problem__  by recommending the most popular movies)
  - Same goes for movies (also frequently added)
- The __score__ in _rating_ is a value between 1 and 5
- The __genre id__ can assume the following values: {Action, Adventure, Animation, Children's, Comedy, Crime, Documentary, Drama, Fantasy, Film-Noir, Horror, Musical, Mystery, Romance, Sci-Fi, Thriller, War, Western}. A movie could have no genre but a genre exists only if it has been associated with a movie, because is a description of it. A movie can, so, be in relation with only 18 genres, i.e. the cardinality of the above set.
- The __category id__ can assume only one of the 1128 genome tag names saved in the dataset. M = #genome tags and N= #movies. (categories __REDUCED__ under a threshold of 0.4)
- The minimal cardinality of the relation __similar__ between movies is 0 because a movie is not considered similar to itself (this would just add noise to the queries _6_ and _7_, since we don't want to recommend movies the user has already watched).
  
__Motivations__:

- We want the relationship between user and movie to be navigable both ways:
  - from __user__ to __movie__ because of queries  _4_, _5_,  _6_ and _8_ (and to compute the top categories/genres for user in orther to mantain the relationships  "top categories" and "top genres" correct for queries _1_ and _2_ )
  - from __movie__ to __user__ because of queries _3_,  _4_, _5_, and _6_ 
\
Since we more frequently need to navigate the relationship in the first direction (also, in query _4_ _5_ we need both directions: the first to indentify the movies rated by the user, and the second to associate those movies to other users in orther to identify them as similar), I chose to represent it in the UML diagram. 

- Given the workflow, we both need to access genre from movie (to compute the user top genres) and related movies from genre (_query 3_). Since for a given a genre we have many related movie - while there's a way more strict limit on the number of possible genres associated with a movie, liited by the cardinality of the genre set - it makes more sense to represent the first direction. 
  - workflow goes the same for __category__ (queries ), but in this case the efficiency difference is eliminated by the fact that each movie is associated exactly with the same number of categories and vice-versa. The association is in this case represented from category to movie because we expect to need to answer the second query more often, given that the first computation occurs only when the user rates a new movie, and is retrieved from the relation "top category" otherwise.
  
I also added a relationship between user and category "top categories" or an attribute and an other one between user and genre like "top genres", to be recalulated each timethe user adds a movie, so we don't need to get all the movies 

#### __Queries?__

  1. Get __top k genres__, given a __user__ (get movies by user, group by genre and then avg or max multiplied by count)
  2. Get __top k categories__, given a __user__ (get movies by user, group by category and then avg or max multiplied by count)
  3. Get __top k movies__, given a __genre__ (movies related to a genre, group by movie, get avg rating and take the maximum count)
  4. Get __top k movies__, given a __category__ (category, highest score)
  5. Get __similar users__ (users who rated highly the same movies), given a user (user --> his movies --> other users who rated highly those movies)
  6. Recommending movies from __similar users__ (user --> his movies --> other users who rated highly those movies --> the movies they rated highly --> order by rating --> take the first K)
  7. Get __similar movies__, given a movie (concept of __similarity__ developed through categories and genres, a movie is similar to itself)
  8. Recommending __similar movies__ (user --> movies ---> similar movies --> order by rating )


__Logical model__

#### __VS other models__

- Relations are the most imporant thing to work on to recommend 
- Attributes are very important and are good to be seen as the weight of an arc between the two nodes in a graph representation (the score in the relationship between user and movie represent how much the user enjoyed it, and the confidence in the relationship between movie and category indicate how much that label is good to decribe that movie).


__Nodes__
- User
- Movie
- Genre
- Category

__Edges__
- Rated (User and Movie)  
- Has_top_genre (User and Genre)
- Has_top_category (User and Category)
- Similar (Movie and Movie)
- Has_genre (Movie and Genre)
- Describes (Category and Movie)

__Graphical representation__

Here is a graphical representation (not a correct instantiation, for example a user should always have K top genres and and K top categories)

![img](GraphRep.drawio.png)

__Translation script__

__Movie__

> You are right that it is generally not recommended to use the internal Neo4j node IDs. This is mainly because if a node gets deleted

Created uuid as attribute and used them instead of _1_, _2_, _3_ in orther for them to be unique.

Pre-Processed the title to get a separate field _year_

__User__

uuid same as movie

__Movie -> User__

Needed bulk operations each 100.000 'cause 25.000.095 relationships (around 11 minutes instead of 25 hours)

__Movie -> Genre__

Around 10 minutes mainly because of the pre-processing needed. Thought about using bulk operation but that would have required the most expensive operation to be anyway run separately and also stored.


#### Examples 
##### Most rated movies 

```
MATCH (u:Users)-[:WATCHED]->(m2:Movies)
WITH m2 ORDER BY m2.rating_mean
RETURN m2.title AS title, m2.rating_mean AS avg_rating
ORDER BY m2.rating_mean DESC LIMIT 100;
```

##### User-based recommendation 

[GDS LIBRARY](https://neo4j.com/docs/graph-data-science/current/algorithms/similarity-functions/)

[ARTICLE1](https://towardsdatascience.com/exploring-practical-recommendation-engines-in-neo4j-ff09fe767782)

[ARTICLE2](https://medium.com/larus-team/how-to-create-recommendation-engine-in-neo4j-7963e635c730)


```
MATCH (u1:Users)-[:WATCHED]->(m3:Movies)
WHERE u1.userId =~'1'
WITH [i IN m3.movieId | i] AS movies
MATCH path = (u:Users)-[:WATCHED]->(m1:Movies)-[s:SIMILAR]->(m2:Movies),
(m2)-[:GENRES]->(g:Genres),
(u)-[:FAVORITE]->(g)
WHERE u.userId =~'10' AND NOT m2.movieId IN movies
RETURN distinct u.userId AS userId, g.genres as genres, 
m2.title as title, m2.rating_mean AS rating
ORDER BY m2.rating_mean descending
LIMIT 10
```

##### Item-based recommendation 

```sql
MATCH (m2:Movies {movieId: "10"})-[:GENRES]->(g:Genres)<-[:GENRES]-(other:Movies)
WITH m2, other, COUNT(g) AS intersection, COLLECT(g.genres) AS i
MATCH (m2)-[:GENRES]->(m2g:Genres)
WITH m2,other, intersection,i, COLLECT(m2g.genres) AS s1
MATCH (other)-[:GENRES]->(og:Genres)
WITH m2,other,intersection,i, s1, COLLECT(og.genres) AS s2
WITH m2,other,intersection,s1,s2
WITH m2,other,intersection,s1+[x IN s2 WHERE NOT x IN s1] AS union, s1, s2
```

##### User-based recommendation 

```sql
MATCH (u1:User {userId: $userId})
        -[r1:CLICKED]->(n1:RecentNews)
        <-[r2:CLICKED]-(u2:User)
        -[r3:CLICKED]->(n2:RecentNews)
RETURN u1.userId AS userId,
        count(DISTINCT n1) AS clickedNews,
        count(DISTINCT u2) AS likeUsers,
        count(DISTINCT n2) AS potentialRecommendations

```

> While the above can work well in some cases, and while it can certainly be a massive improvement from joining SQL tables or cross-walking over document stores, notice that we get a lot of potential recommendations back (almost 11K) and must traverse many user nodes (over 63K).

[FastRP](https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/fastrp/)

```sql
MATCH (p1:User {name: 'Leonardo', surname:"Marrancone"})-[x:WATCH]->(movie)<-[y:WATCH]-(p2:User)
WHERE p2 <> p1
WITH p1, p2, collect(x.rating) AS p1Ratings, collect(y.rating) AS p2Ratings
RETURN p1.name AS SelectedUser,
 p2.name AS SimilarUser,
 gds.alpha.similarity.cosine(p1Ratings, p2Ratings) AS sim
ORDER BY sim DESC
``` 

```sql 
MATCH (p1:User {name:"Leonardo", surname:"Marrancone"})-[x:WATCH]->(m:Show)
WITH p1, gds.alpha.similarity.asVector(m, x.rating) AS p1avg
MATCH (p2:User)-[y:WATCH]->(m:Show) WHERE p2 <> p1
WITH p1, p2, p1avg, gds.alpha.similarity.asVector(m, y.rating) AS p2avg
WITH p1, p2, gds.alpha.similarity.pearson(p1avg, p2avg, {vectorType: "maps"}) AS pearson
ORDER BY pearson DESC
MATCH (p2)-[r:WATCH]->(m:Show) WHERE NOT EXISTS( (p1)-[:WATCH]->(m) )
RETURN m.name as showname, SUM(pearson * r.rating) AS score
ORDER BY score DESC
```