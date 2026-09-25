from typing import Optional

from fastapi import UploadFile, HTTPException
from pydantic.v1 import StrictStr

from ai_assistant.server.apis.convert_api_base import BaseConvertApi
from ai_assistant.server.models.owl2_rdf_graph_conversion_result import OWL2RDFGraphConversionResult
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
    ) -> OWL2RDFGraphConversionResult:
        ontology_file = await file.read()
        try:
            ontology = parse_ontology(ontology_file)
            o2gscape = OWL2Gscape(ontology)
            rdf_graph = o2gscape.owl_to_rdf_graph()
            originalAxioms = len(ontology.getAxioms())
            acceptedAxioms = len(o2gscape.acceptedAxioms)
            return OWL2RDFGraphConversionResult(
                rdfGraph=rdf_graph,
                acceptedAxioms=acceptedAxioms,
                originalAxioms=originalAxioms,
                rejectedAxioms=originalAxioms - acceptedAxioms,
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})

    async def get_ontology_draft_ai_download_rejected_axioms(
            self,
            format: Optional[StrictStr],
            file: UploadFile,
    ) :
        ontology_file = await file.read()
        try:
            ontology = parse_ontology(ontology_file)
            o2gscape = OWL2Gscape(ontology)
            o2gscape.owl_to_rdf_graph()
            return serialize_owl(o2gscape.get_rejected_axioms_as_ontology(), format)
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})