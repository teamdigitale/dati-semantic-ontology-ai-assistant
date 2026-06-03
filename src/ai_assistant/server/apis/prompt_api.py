# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from ai_assistant.server.apis.prompt_api_base import BasePromptApi
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
from typing import Any, List, Optional
from ai_assistant.server.models.auto_chart_request import AutoChartRequest
from ai_assistant.server.models.chart_configuration import ChartConfiguration
from ai_assistant.server.models.describe_chart_request import DescribeChartRequest
from ai_assistant.server.models.describe_individual_request import DescribeIndividualRequest
from ai_assistant.server.models.describe_ontology_entity_request import DescribeOntologyEntityRequest
from ai_assistant.server.models.describe_sparql_query_request import DescribeSparqlQueryRequest
from ai_assistant.server.models.suggest_class_data_properties_request import SuggestClassDataPropertiesRequest
from ai_assistant.server.models.text2sparql_request import Text2sparqlRequest
from ai_assistant.server.security_api import get_token_jwt

router = APIRouter()

ns_pkg = ai_assistant.server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/ai/entity_description",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Returns the description for an entity",
    response_model_by_alias=True,
)
async def describe_ontology_entity(
    describe_ontology_entity_request: Optional[DescribeOntologyEntityRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().describe_ontology_entity(describe_ontology_entity_request)


@router.post(
    "/ai/individual_description",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Returns the description for an individual (class instance)",
    response_model_by_alias=True,
)
async def describe_individual(
    describe_individual_request: Optional[DescribeIndividualRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().describe_individual(describe_individual_request)


@router.post(
    "/ai/class_data_properties",
    responses={
        200: {"model": List[str], "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Returns a list of possible data properties for a given class",
    response_model_by_alias=True,
)
async def suggest_class_data_properties(
    suggest_class_data_properties_request: Optional[SuggestClassDataPropertiesRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> List[str]:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().suggest_class_data_properties(suggest_class_data_properties_request)


@router.post(
    "/ai/class_subclasses",
    responses={
        200: {"model": List[str], "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Returns a list of possible subclasses for a given class",
    response_model_by_alias=True,
)
async def suggest_class_subclasses(
    suggest_class_data_properties_request: Optional[SuggestClassDataPropertiesRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> List[str]:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().suggest_class_subclasses(suggest_class_data_properties_request)


@router.post(
    "/ai/sparql_description",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Returns a description of a sparql query",
    response_model_by_alias=True,
)
async def describe_sparql_query(
    describe_sparql_query_request: Optional[DescribeSparqlQueryRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().describe_sparql_query(describe_sparql_query_request)


@router.post(
    "/ai/autochart",
    responses={
        200: {"model": ChartConfiguration, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Returns a chart configuration for a SPARQL query suggested by AI",
    response_model_by_alias=True,
)
async def auto_chart(
    auto_chart_request: Optional[AutoChartRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> ChartConfiguration:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().auto_chart(auto_chart_request)


@router.post(
    "/ai/autochart_description",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Returns a description of a chart",
    response_model_by_alias=True,
)
async def describe_chart(
    describe_chart_request: Optional[DescribeChartRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().describe_chart(describe_chart_request)


@router.post(
    "/ai/text2sparql",
    responses={
        200: {"model": str, "description": "Successful operation"},
        401: {"description": "Unhauthorized"},
    },
    tags=["Prompt"],
    summary="Converts a natural language text into a SPARQL query",
    response_model_by_alias=True,
)
async def text2sparql(
    text2sparql_request: Optional[Text2sparqlRequest] = Body(None, description=""),
    token_jwt: TokenModel = Security(
        get_token_jwt
    ),
) -> str:
    if not BasePromptApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePromptApi.subclasses[0]().text2sparql(text2sparql_request)
