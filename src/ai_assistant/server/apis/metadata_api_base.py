# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictBytes, StrictStr
from typing import Any, Optional, Tuple, Union
from ai_assistant.server.models.mwsx_ontology_catalog_ontology_metadata_set import MWSXOntologyCatalogOntologyMetadataSet
from fastapi import File, UploadFile
from ai_assistant.server.security_api import get_token_jwt

class BaseMetadataApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseMetadataApi.subclasses = BaseMetadataApi.subclasses + (cls,)
    async def post_ai_ontology_draft_metadata(
        self,
        format: Optional[StrictStr],
        new_version: Optional[StrictStr],
        file: Optional[UploadFile],
        # modified by hand as the generation is wrong: the json must be parsed as a file
        metadata: Optional[UploadFile],
    ) -> str:
        ...
