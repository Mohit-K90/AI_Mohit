from neo4j import AsyncGraphDatabase
from typing import Dict, List, Any, Optional
import json


class GraphService:
    def __init__(self):
        self.driver = None
        self.uri = "bolt://localhost:7687"
        self.auth = ("neo4j", "password")

    async def initialize(self):
        """Initialize Neo4j connection"""
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth)
        await self._verify_connection()

    async def _verify_connection(self):
        """Verify Neo4j connection"""
        async with self.driver.session() as session:
            result = await session.run("RETURN 1 as test")
            record = await result.single()
            if record["test"] != 1:
                raise Exception("Failed to connect to Neo4j")

    async def get_concept_with_context(self, concept_name: str, domain: str, depth: int = 2) -> Dict[str, Any]:
        """
        Retrieve concept with related information from knowledge graph
        """
        query = """
        MATCH (c:Concept {name: $concept_name})-[:BELONGS_TO]->(d:Domain {name: $domain})

        // Get prerequisites
        OPTIONAL MATCH (c)-[:REQUIRES]->(prereq:Prerequisite)

        // Get examples
        OPTIONAL MATCH (c)-[:EXEMPLIFIED_BY]->(example:Example)

        // Get related concepts
        OPTIONAL MATCH (c)-[:RELATED_TO]-(related:Concept)
        WHERE related <> c

        // Get chapter content
        OPTIONAL MATCH (c)-[:PART_OF]->(chapter:Chapter)-[:BELONGS_TO]->(book:Book)

        RETURN c as concept,
               collect(DISTINCT prereq) as prerequisites,
               collect(DISTINCT example) as examples,
               collect(DISTINCT related) as related_concepts,
               collect(DISTINCT {chapter: chapter, book: book}) as source_content
        """

        async with self.driver.session() as session:
            result = await session.run(query, concept_name=concept_name, domain=domain)
            record = await result.single()

            if not record:
                raise ValueError(f"Concept '{concept_name}' not found in domain '{domain}'")

            return self._format_concept_data(record)

    def _format_concept_data(self, record) -> Dict[str, Any]:
        """Format Neo4j record into structured data"""
        concept = dict(record["concept"])
        prerequisites = [dict(p) for p in record["prerequisites"]]
        examples = [dict(e) for e in record["examples"]]
        related_concepts = [dict(r) for r in record["related_concepts"]]
        source_content = [
            {"chapter": dict(sc["chapter"]), "book": dict(sc["book"])}
            for sc in record["source_content"] if sc["chapter"]
        ]

        return {
            "concept": concept,
            "prerequisites": prerequisites,
            "examples": examples,
            "related_concepts": related_concepts,
            "source_content": source_content
        }

    async def search_concepts(self, query: str, domain: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for concepts by name or description"""
        cypher_query = """
        MATCH (c:Concept)
        WHERE toLower(c.name) CONTAINS toLower($query) 
           OR toLower(c.description) CONTAINS toLower($query)
        """

        if domain:
            cypher_query += """
            MATCH (c)-[:BELONGS_TO]->(d:Domain {name: $domain})
            """

        cypher_query += """
        RETURN c
        ORDER BY 
            CASE WHEN toLower(c.name) = toLower($query) THEN 0 ELSE 1 END,
            c.name
        LIMIT $limit
        """

        async with self.driver.session() as session:
            result = await session.run(cypher_query, query=query, domain=domain, limit=limit)
            concepts = []
            async for record in result:
                concepts.append(dict(record["c"]))
            return concepts

    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()