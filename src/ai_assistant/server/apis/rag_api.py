# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from ai_assistant.server.apis.rag_api_base import BaseRAGApi
import ai_assistant.server.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from ai_assistant.server.models.extra_models import TokenModel  # noqa: F401
from pydantic import StrictStr
from typing import Any, Optional
from ai_assistant.server.models.post_ontology_rdf_examples_request import PostOntologyRDFExamplesRequest
from ai_assistant.server.models.post_ontology_summary_request import PostOntologySummaryRequest
from ai_assistant.server.models.put_ontology_draft_ai_request import PutOntologyDraftAIRequest
from ai_assistant.server.models.put_ontology_query_ai200_response import PutOntologyQueryAI200Response
from ai_assistant.server.models.put_ontology_query_ai_request import PutOntologyQueryAIRequest
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.server.models.vector_db_status import VectorDBStatus
from ai_assistant.server.security_api import get_token_jwt

router = APIRouter()

ns_pkg = ai_assistant.server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.put(
    "/ai/rag/ontologyDraft/{name}",
    responses={
        200: {"model": RDFGraph, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["RAG"],
    summary="Ask for AI support in ontology design.",
    response_model_by_alias=True,
)
async def put_ontology_draft_ai(
    name: StrictStr = Path(..., description=""),
    put_ontology_draft_ai_request: Optional[PutOntologyDraftAIRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> RDFGraph:
    if not BaseRAGApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRAGApi.subclasses[0]().put_ontology_draft_ai(name, put_ontology_draft_ai_request)


@router.put(
    "/ai/rag/ontologyQuery",
    responses={
        200: {"model": PutOntologyQueryAI200Response, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["RAG"],
    summary="Ask anything about this ontology, and get an answer with the relevant entities.",
    response_model_by_alias=True,
)
async def put_ontology_query_ai(
    put_ontology_query_ai_request: Optional[PutOntologyQueryAIRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> PutOntologyQueryAI200Response:
    if not BaseRAGApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRAGApi.subclasses[0]().put_ontology_query_ai(put_ontology_query_ai_request)


@router.post(
    "/ai/rag/ontologyRDFExamples",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["RAG"],
    summary="Returns an example of RDF instaces in Turtle format, based on the classes provided in the request body and the current RDF graph.",
    response_model_by_alias=True,
)
async def post_ontology_rdf_examples(
    post_ontology_rdf_examples_request: Optional[PostOntologyRDFExamplesRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BaseRAGApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRAGApi.subclasses[0]().post_ontology_rdf_examples(post_ontology_rdf_examples_request)


@router.post(
    "/ai/rag/ontologySummary",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["RAG"],
    summary="Returns a summary of the ontology.",
    response_model_by_alias=True,
)
async def post_ontology_summary(
    post_ontology_summary_request: Optional[PostOntologySummaryRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BaseRAGApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRAGApi.subclasses[0]().post_ontology_summary(post_ontology_summary_request)


@router.get(
    "/ai/rag/{ontologyName}/vectorDB/status",
    responses={
        200: {"model": VectorDBStatus, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["RAG"],
    summary="Check the vector database status for a specific ontology version.",
    response_model_by_alias=True,
)
async def check_vector_db_status(
    ontologyName: StrictStr = Path(..., description=""),
    ontology_version: StrictStr = Query(None, description="", alias="ontologyVersion"),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> VectorDBStatus:
    if not BaseRAGApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRAGApi.subclasses[0]().check_vector_db_status(ontologyName, ontology_version)
