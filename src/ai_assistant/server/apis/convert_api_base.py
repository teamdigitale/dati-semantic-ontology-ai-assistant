# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictBytes, StrictStr
from typing import Any, Optional, Tuple, Union
from ai_assistant.server.models.owl2_rdf_graph_conversion_result import OWL2RDFGraphConversionResult
from ai_assistant.server.models.rdf_graph import RDFGraph
from fastapi import File, UploadFile
from ai_assistant.server.security_api import get_token_jwt

class BaseConvertApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseConvertApi.subclasses = BaseConvertApi.subclasses + (cls,)
    async def get_ontology_draft_ai_download(
        self,
        format: Optional[StrictStr],
        rdf_graph: Optional[RDFGraph],
    ) -> str:
        ...


    async def get_ontology_draft_ai_download_rejected_axioms(
        self,
        format: Optional[StrictStr],
        file: Optional[UploadFile],
    ) -> str:
        ...


    async def post_ontology_draft_ai_convert_owl(
        self,
        file: Optional[UploadFile],
    ) -> OWL2RDFGraphConversionResult:
        ...
