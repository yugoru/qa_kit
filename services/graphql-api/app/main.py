from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from prometheus_fastapi_instrumentator import Instrumentator

from .schema import schema


app = FastAPI(
    title="QA Kit GraphQL API",
    version="0.1.0",
)

Instrumentator().instrument(app).expose(app)

graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
async def health():
    return {"status": "ok"}
