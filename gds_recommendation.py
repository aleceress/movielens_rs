def exists_gds_graph(neo4j_graph, graph_name):
    return neo4j_graph.run(
        (f"CALL gds.graph.exists('{graph_name}')" f"YIELD graphName, exists")
    ).data()[0]["exists"]


def delete_gds_graph(neo4j_graph, gds_name):
    neo4j_graph.run(f"CALL gds.graph.drop('{gds_name}')")


def create_gds_projection(
    neo4j_graph,
    gds_name,
    node_names,
    node_property=None,
    rel_property=None,
    rel_names=None,
    orientation="UNDIRECTED"
):

    if exists_gds_graph(neo4j_graph, gds_name):
        delete_gds_graph(neo4j_graph, gds_name)

    neo4j_graph.run(
        "CALL gds.graph.project( "
        + f"'{gds_name}', "
        + (
            f"{node_names}, "
            if node_property is None
            else f"{{ {node_names[0]} : {{properties: '{node_property}'}} }}, "
        )
        + (
            f"[{{ {rel_names[0]} : {{ properties: '{rel_property}', orientation: '{orientation}'}} }}]"
            if rel_names is not None
            else "['*'] "
        )
        + ")"
        + "YIELD graphName, nodeProjection, nodeCount AS nodes, relationshipCount AS rels "
        + "RETURN graphName, nodes, rels"
    )

def create_gds_cypher_projection(neo4j_graph, gds_name, node_names, rel_names, property_name):
    if exists_gds_graph(neo4j_graph, gds_name):
        delete_gds_graph(neo4j_graph, gds_name)

    neo4j_graph.run(
        (
            f"CALL gds.graph.project.cypher('{gds_name}', "
            f" 'MATCH (n) WHERE n:{node_names[0]} OR n:{node_names[1]} OR n:{node_names[2]} RETURN id(n) AS id, labels(n) AS labels', "
            f"'MATCH (n)-[r:{rel_names[0]}|{rel_names[1]}]-(m) RETURN id(n) AS source, id(m) AS target, type(r) AS type, coalesce(r.{property_name}, 1.0) AS {property_name}'"  
            ") "   
            "YIELD graphName AS graph, nodeCount AS nodes, relationshipCount AS rels" 
        )
    )

def mutate_fastRP_embedding(
    neo4j_graph, gds_name, node_names, rel_names, rel_property, embedding_name
):
    neo4j_graph.run(
        (
            f"CALL gds.fastRP.mutate('{gds_name}', "
            "{ "
            f"nodeLabels: {node_names}, "
            f"relationshipTypes: {rel_names}, "
            "embeddingDimension: 256, "
            f"relationshipWeightProperty: '{rel_property}', "
            f"randomSeed: 42, "
            f"mutateProperty: '{embedding_name}'"
            "} "
            ") "
            "YIELD nodePropertiesWritten"
        )
    )


def write_fastRP_embedding(neo4j_graph, gds_name, nodes, embedding_name):
    neo4j_graph.run(
        (
            f"CALL gds.graph.writeNodeProperties('{gds_name}', ['{embedding_name}'], {nodes})"
            "YIELD propertiesWritten"
        )
    )


def write_knn_sim_relationships(
    neo4j_graph, knn_gds_name, node_name, embedding_name, rel_name, property, K=5
):

    neo4j_graph.run(
        f"""
        MATCH (n1:{node_name})-[r:{rel_name}]->(n2:{node_name})
        DELETE r
        """
    )

    neo4j_graph.run(
        f"""
            CALL gds.knn.write('{knn_gds_name}', {{
                nodeProperties: ["{embedding_name}"],
                writeRelationshipType: '{rel_name}',
                writeProperty: '{property}',
                topK: {K}
            }})
            YIELD nodesCompared, relationshipsWritten
        """
    )

