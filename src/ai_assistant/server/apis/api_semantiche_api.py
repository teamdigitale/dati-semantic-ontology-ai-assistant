# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from ai_assistant.server.apis.api_semantiche_api_base import BaseAPISemanticheApi
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
from pydantic import StrictBool, StrictStr
from typing import Any, Optional
from ai_assistant.server.models.file_info import FileInfo
from ai_assistant.server.models.mwsx_ontology_catalog_entries import MWSXOntologyCatalogEntries
from ai_assistant.server.models.ontology_catalog_entry_status import OntologyCatalogEntryStatus
from ai_assistant.server.models.ontology_catalog_history import OntologyCatalogHistory
from ai_assistant.server.models.post_apisem_catalog_request import PostApisemCatalogRequest
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.server.security_api import get_token_jwt

router = APIRouter()

ns_pkg = ai_assistant.server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/ai/apisem/catalog",
    responses={
        200: {"model": MWSXOntologyCatalogEntries, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Returns the current content of the ontology catalog used to generate semantic annotations for provided YAML service specifications",
    response_model_by_alias=True,
)
async def get_apisem_catalog(
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> MWSXOntologyCatalogEntries:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().get_apisem_catalog()


@router.post(
    "/ai/apisem/catalog",
    responses={
        200: {"model": MWSXOntologyCatalogEntries, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Adds a new ontology to the current ontology catalog, creates the corresponding vector DB instance",
    response_model_by_alias=True,
)
async def post_apisem_catalog(
    post_apisem_catalog_request: Optional[PostApisemCatalogRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> MWSXOntologyCatalogEntries:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().post_apisem_catalog(post_apisem_catalog_request)


@router.delete(
    "/ai/apisem/catalog",
    responses={
        200: {"model": bool, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Reset the content of the current catalog",
    response_model_by_alias=True,
)
async def delete_apisem_catalog(
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> bool:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().delete_apisem_catalog()


@router.get(
    "/ai/apisem/catalog/history",
    responses={
        200: {"model": OntologyCatalogHistory, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Returns the list of operations executed on the ontology catalog",
    response_model_by_alias=True,
)
async def get_apisem_catalog_history(
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> OntologyCatalogHistory:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().get_apisem_catalog_history()


@router.put(
    "/ai/apisem/catalog/{name}",
    responses={
        200: {"model": MWSXOntologyCatalogEntries, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Replace the given ontology in the catalog with the one provided in the request body",
    response_model_by_alias=True,
)
async def put_apisem_catalog_name(
    name: StrictStr = Path(..., description=""),
    version: StrictStr = Query(None, description="", alias="version"),
    rdf_graph: RDFGraph = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> MWSXOntologyCatalogEntries:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().put_apisem_catalog_name(name, version, rdf_graph)


@router.delete(
    "/ai/apisem/catalog/{name}",
    responses={
        200: {"model": bool, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Reset the content of the current catalog",
    response_model_by_alias=True,
)
async def delete_apisem_catalog_name(
    name: StrictStr = Path(..., description=""),
    version: StrictStr = Query(None, description="", alias="version"),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> bool:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().delete_apisem_catalog_name(name, version)


@router.get(
    "/ai/apisem/catalog/{name}/status",
    responses={
        200: {"model": OntologyCatalogEntryStatus, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Returns the current status of a given ontology catalog entry",
    response_model_by_alias=True,
)
async def get_apisem_catalog_name_status(
    name: StrictStr = Path(..., description=""),
    version: StrictStr = Query(None, description="", alias="version"),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> OntologyCatalogEntryStatus:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().get_apisem_catalog_name_status(name, version)


@router.post(
    "/ai/apisem/schema",
    responses={
        200: {"model": FileInfo, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["APISemantiche"],
    summary="Takes a YAML file containing the specification of a service and returns the YAML specification annotated",
    response_model_by_alias=True,
)
async def post_apisem_schema(
    file_info: FileInfo = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> FileInfo:
    if not BaseAPISemanticheApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAPISemanticheApi.subclasses[0]().post_apisem_schema(file_info)
