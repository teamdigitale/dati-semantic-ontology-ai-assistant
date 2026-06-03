# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

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

class BaseRAGApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseRAGApi.subclasses = BaseRAGApi.subclasses + (cls,)
    async def put_ontology_draft_ai(
        self,
        name: StrictStr,
        put_ontology_draft_ai_request: Optional[PutOntologyDraftAIRequest],
    ) -> RDFGraph:
        ...


    async def put_ontology_query_ai(
        self,
        put_ontology_query_ai_request: Optional[PutOntologyQueryAIRequest],
    ) -> PutOntologyQueryAI200Response:
        ...


    async def post_ontology_rdf_examples(
        self,
        post_ontology_rdf_examples_request: Optional[PostOntologyRDFExamplesRequest],
    ) -> str:
        ...


    async def post_ontology_summary(
        self,
        post_ontology_summary_request: Optional[PostOntologySummaryRequest],
    ) -> str:
        ...


    async def check_vector_db_status(
        self,
        ontologyName: StrictStr,
        ontology_version: StrictStr,
    ) -> VectorDBStatus:
        ...
