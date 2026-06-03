from typing import Optional

from fastapi import UploadFile, HTTPException
from pydantic.v1 import StrictStr

from ai_assistant.server.apis.convert_api_base import BaseConvertApi
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.gscape import rdf_graph_to_owl, serialize_owl
from ai_assistant.owl import OWL2Gscape, parse_ontology
class ConvertApiImpl(BaseConvertApi):
    async def get_ontology_draft_ai_download(
            self,
            format: Optional[StrictStr],
            rdf_graph: Optional[RDFGraph],
    ) :
        if rdf_graph is None:
            return ""
        try:
            owl_ontology = rdf_graph_to_owl(rdf_graph)
            return serialize_owl(owl_ontology, format)
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})

    async def post_ontology_draft_ai_convert_owl(
            self,
            file: UploadFile,
    ) -> RDFGraph:
        ontology = await file.read()
        try:
            return OWL2Gscape(parse_ontology(ontology)).owl_to_rdf_graph()
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})
