# coding: utf-8
import re
from contextlib import asynccontextmanager
import os
import json

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import EmbeddingFunc
from lightrag.namespace import NameSpace
from lightrag.rerank import custom_rerank, RerankModel

from .models.rdf_graph import RDFGraph
from .models.vector_db_status import VectorDBStatus
from ..gscape import load_gscape

from ..rag import OntoRAG
from ..jvm import startJVM
from ..llm.openai import (
    vllm_embed,
    vllm_model_complete,
)
from ai_assistant.server.apis.convert_api import router as ConvertApiRouter
from ai_assistant.server.apis.prompt_api import router as PromptApiRouter
from ai_assistant.server.apis.rag_api import router as RAGApiRouter


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Lifespan of the server."""
    ########################################
    # Startup event
    ########################################
    load_dotenv(override=False)
    prefix = os.getenv("ROOT_PATH")
    if prefix:
        app_instance.mount(prefix, app_instance)
    app_instance.designer_rag = await create_rag()
    await initialize_pipeline_status()
    startJVM()
    logger.info("Ontology AI-Assistant public version")
    yield
    ########################################
    # Shutdown event
    ########################################
    await app_instance.designer_rag.finalize_storages()

async def create_rag(ontology_name: str = None, ontology_version: str = None):
    working_dir = os.getenv("WORKING_DIR", os.curdir)
    if ontology_name is not None and ontology_version is not None:
        working_dir = os.path.join(
            working_dir,
            ontology_name,
            re.sub(r"[^A-Za-z0-9_]+", "_", ontology_version)
        )

    rerank_model = RerankModel(
        rerank_func=custom_rerank,
        kwargs={
            "model": str(os.getenv("RERANK_MODEL")),
            "base_url": str(os.getenv("RERANK_BINDING_HOST")),
            "api_key": str(os.getenv("RERANK_BINDING_API_KEY")),
        },
    )

    rag = OntoRAG(
        working_dir=working_dir,
        llm_model_name=os.getenv("LLM_MODEL"),
        llm_model_func=vllm_model_complete,
        llm_model_kwargs=(
            {"temperature": float(os.getenv("TEMPERATURE", 0.5))} |
            {"seed": int(os.getenv("SEED"))} if os.getenv("SEED") is not None else {} |
            {"timeout": float(os.getenv("TIMEOUT"))} if os.getenv("TIMEOUT") is not None else {}
        ),
        enable_llm_cache=os.getenv("ENABLE_LLM_CACHE", "False").strip().lower() == "true",
        enable_llm_cache_for_entity_extract=os.getenv(
            "ENABLE_LLM_CACHE_FOR_EXTRACT", "False"
        ).strip().lower() == "true",
        addon_params={
            "example_number": 0,
            "enable_vdb_load_for_extract": os.getenv("ENABLE_VDB_LOAD_FOR_EXTRACT", "False").strip().lower() == "true",
            "enable_vdb_load": os.getenv("ENABLE_VDB_LOAD", "True").strip().lower() == "true",
            "enable_disk_persist": os.getenv("ENABLE_DISK_PERSIST", "False").strip().lower() == "true",
        },
        entity_extract_max_gleaning=0,
        embedding_func=EmbeddingFunc(
            embedding_dim=int(os.getenv("EMBEDDING_DIM", 1024)),
            max_token_size=int(os.getenv("EMBEDDING_MAX_TOKEN_SIZE", 8192)),
            func=vllm_embed,
            # func=stub_embed,  # for embeddings stub func
        ),

        # Rerank Configuration - provide the rerank function
        rerank_model_func=rerank_model.rerank, # Method 2
    )
    
    await rag.initialize_storages()

    graph_file_path = os.path.join(
        working_dir, f"graph_{NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION}.gscape"
    )
    if os.path.exists(graph_file_path):
        with open(graph_file_path) as f:
            graph_text = f.read()
        rdfGraph = RDFGraph.from_dict(json.loads(graph_text))
        graph = load_gscape(rdfGraph)
        await rag.chunk_entity_relation_graph.set_graph(graph)

    return rag

app = FastAPI(
    title="AI assistant API model",
    description="This is the API for the AI assistant module",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ConvertApiRouter)
app.include_router(PromptApiRouter)
app.include_router(RAGApiRouter)

from ..utils import logger
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logger.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
