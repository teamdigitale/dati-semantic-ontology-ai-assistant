# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401
from typing import Optional, Tuple

from fastapi import UploadFile, HTTPException
from pydantic import StrictStr

from ai_assistant.gscape import serialize_owl
from ai_assistant.owl import parse_ontology, OWL2Gscape
from ai_assistant.server.apis.metadata_api_base import BaseMetadataApi
from ai_assistant.server.models.mwsx_ontology_catalog_ontology_metadata_set import \
    MWSXOntologyCatalogOntologyMetadataSet


class MetadataApiImpl(BaseMetadataApi):
    subclasses: ClassVar[Tuple] = ()

    async def post_ai_ontology_draft_metadata(
            self,
            format: Optional[StrictStr],
            new_version: Optional[StrictStr],
            file: Optional[UploadFile],
            metadata: Optional[UploadFile],
    ) -> str:
        ontology_file = await file.read()
        metadata_parsed = MWSXOntologyCatalogOntologyMetadataSet.from_json((await metadata.read()).decode("utf-8"))
        try:
            ontology = parse_ontology(ontology_file)
            o2gscape = OWL2Gscape(ontology)
            enriched_ontology = o2gscape.update_metadata(metadata_parsed, new_version)
            return serialize_owl(enriched_ontology, format)
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})
