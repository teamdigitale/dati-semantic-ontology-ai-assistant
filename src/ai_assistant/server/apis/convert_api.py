# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from ai_assistant.server.apis.convert_api_base import BaseConvertApi
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
    status, UploadFile,
)

from ai_assistant.server.models.extra_models import TokenModel  # noqa: F401
from pydantic import StrictStr
from typing import Any, Optional
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.server.security_api import get_token_jwt

router = APIRouter()

ns_pkg = ai_assistant.server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/ai/ontologyDraft/download",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Convert"],
    summary="Download the ontology draft converted in OWL2",
    response_model_by_alias=True,
)
async def get_ontology_draft_ai_download(
    format: Optional[StrictStr] = Query(None, description="", alias="format"),
    rdf_graph: Optional[RDFGraph] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BaseConvertApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseConvertApi.subclasses[0]().get_ontology_draft_ai_download(format, rdf_graph)


@router.post(
    "/ai/ontologyDraft/convertOWL",
    responses={
        200: {"model": RDFGraph, "description": "OK"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Convert"],
    summary="Convert an OWL file in RDFGraph model",
    response_model_by_alias=True,
)
async def post_ontology_draft_ai_convert_owl(
    file: UploadFile,
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> RDFGraph:
    if not BaseConvertApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseConvertApi.subclasses[0]().post_ontology_draft_ai_convert_owl(file)