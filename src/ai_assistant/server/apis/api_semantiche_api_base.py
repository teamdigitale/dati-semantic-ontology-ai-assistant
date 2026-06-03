# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictBool, StrictStr
from typing import Any, Optional
from ai_assistant.server.models.file_info import FileInfo
from ai_assistant.server.models.mwsx_ontology_catalog_entries import MWSXOntologyCatalogEntries
from ai_assistant.server.models.ontology_catalog_entry_status import OntologyCatalogEntryStatus
from ai_assistant.server.models.ontology_catalog_history import OntologyCatalogHistory
from ai_assistant.server.models.post_apisem_catalog_request import PostApisemCatalogRequest
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.server.security_api import get_token_jwt

class BaseAPISemanticheApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAPISemanticheApi.subclasses = BaseAPISemanticheApi.subclasses + (cls,)
    async def get_apisem_catalog(
        self,
    ) -> MWSXOntologyCatalogEntries:
        ...


    async def post_apisem_catalog(
        self,
        post_apisem_catalog_request: Optional[PostApisemCatalogRequest],
    ) -> MWSXOntologyCatalogEntries:
        ...


    async def delete_apisem_catalog(
        self,
    ) -> bool:
        ...


    async def get_apisem_catalog_history(
        self,
    ) -> OntologyCatalogHistory:
        ...


    async def put_apisem_catalog_name(
        self,
        name: StrictStr,
        version: StrictStr,
        rdf_graph: RDFGraph,
    ) -> MWSXOntologyCatalogEntries:
        ...


    async def delete_apisem_catalog_name(
        self,
        name: StrictStr,
        version: StrictStr,
    ) -> bool:
        ...


    async def get_apisem_catalog_name_status(
        self,
        name: StrictStr,
        version: StrictStr,
    ) -> OntologyCatalogEntryStatus:
        ...


    async def post_apisem_schema(
        self,
        file_info: FileInfo,
    ) -> FileInfo:
        ...
