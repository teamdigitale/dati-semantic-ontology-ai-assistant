# coding: utf-8

import json
import os
from typing import Optional

from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import StrictStr, StrictBool

from ai_assistant.gscape import load_gscape, write_gscape
from ai_assistant.rag import OntoRAG
from ai_assistant.server.apis.rag_api import BaseRAGApi
from ai_assistant.server.models.post_ontology_rdf_examples_request import PostOntologyRDFExamplesRequest
from ai_assistant.server.models.post_ontology_summary_request import PostOntologySummaryRequest
from ai_assistant.server.models.put_ontology_draft_ai_request import PutOntologyDraftAIRequest
from ai_assistant.server.models.put_ontology_query_ai_request import PutOntologyQueryAIRequest
from ai_assistant.server.models.put_ontology_query_ai200_response import PutOntologyQueryAI200Response
from ai_assistant.server.models.rdf_graph import RDFGraph

from lightrag.utils import get_env_value

from ai_assistant.utils import (
    languages,
    DEFAULT_LANGUAGE,
    DEFAULT_IRI_LANGUAGE,
)

class RAGApiImpl(BaseRAGApi):
    async def put_ontology_draft_ai(
            self,
            name: StrictStr,
            put_ontology_draft_ai_request: Optional[PutOntologyDraftAIRequest],
    ) -> RDFGraph:
        from ..main import app
        if put_ontology_draft_ai_request.current_rdf_graph:
            gscape = load_gscape(put_ontology_draft_ai_request.current_rdf_graph)
            await app.designer_rag.chunk_entity_relation_graph.set_graph(gscape)
        if put_ontology_draft_ai_request.iri_style is not None:
            if put_ontology_draft_ai_request.iri_style:
                app.designer_rag.addon_params["iri_format"] = "camelCase"
            else:
                app.designer_rag.addon_params["iri_format"] = "snake_case"
        if put_ontology_draft_ai_request.simple_name_language is not None:
            simple_name_lang_tag = put_ontology_draft_ai_request.simple_name_language
            iri_language = languages[simple_name_lang_tag]
            app.designer_rag.addon_params["iri_language"] = iri_language
        if put_ontology_draft_ai_request.annotation_language is not None:
            annotation_lang_tag = put_ontology_draft_ai_request.annotation_language
            language = languages[annotation_lang_tag]
            app.designer_rag.addon_params["language"] = language
        await app.designer_rag.ainsert(put_ontology_draft_ai_request.text)
        graph = write_gscape(await app.designer_rag.chunk_entity_relation_graph.get_graph())
        app.designer_rag.addon_params["iri_format"] = get_env_value("IRI_FORMAT", "camelCase", str),
        app.designer_rag.addon_params["iri_language"] = get_env_value("IRI_LANGUAGE", DEFAULT_IRI_LANGUAGE, str),
        app.designer_rag.addon_params["language"] = get_env_value("SUMMARY_LANGUAGE", DEFAULT_LANGUAGE, str),
        await app.designer_rag._drop_all()
        app.designer_rag.reinitialize_doc_status()
        return graph

    async def put_ontology_query_ai(
            self,
            put_ontology_query_ai_request: Optional[PutOntologyQueryAIRequest],
    ) -> PutOntologyQueryAI200Response:
        from ..main import app

        query = put_ontology_query_ai_request.text
        graph = put_ontology_query_ai_request.current_rdf_graph

        try:
            drop_outcome = await app.designer_rag.chunk_entity_relation_graph.drop()
            if drop_outcome["status"] == "success":
                vdb_load_result = await app.designer_rag.ainsert_kg_from_gscape(graph, False)
            else:
                raise HTTPException(status_code=404, detail={"message": "Dropping graph error: {drop_outcome['message']}"})

            if vdb_load_result["status"] != "error":
                query_response = await app.designer_rag.aqueryOnOntology(query)
            else:
                error_message = f"VectorDB loading failed: {vdb_load_result['message']}"
                raise HTTPException(status_code=404, detail={"message": error_message})

            if query_response:
                return PutOntologyQueryAI200Response(
                    query_answer=query_response[0],
                    ontology_entities=query_response[1],
                )
            else:
                raise HTTPException(status_code=404, detail={"message": "Executing the query resulted in an error"})
        finally:
            drop_outcome = await app.designer_rag.chunk_entity_relation_graph.drop()
            if drop_outcome["status"] == "error":
                raise HTTPException(status_code=404, detail={"message": "Dropping graph error: {drop_outcome['message']}"})

    async def post_ontology_rdf_examples(
            self,
            post_ontology_rdf_examples_request: Optional[PostOntologyRDFExamplesRequest],
    ) -> str:
        from ..main import app

        graph = post_ontology_rdf_examples_request.current_rdf_graph
        classes = post_ontology_rdf_examples_request.classes

        try:
            drop_outcome = await app.designer_rag.chunk_entity_relation_graph.drop()
            if drop_outcome["status"] == "success":
                vdb_load_result = await app.designer_rag.ainsert_kg_from_gscape(graph, False)
            else:
                raise HTTPException(status_code=404, detail={"message": "Dropping graph error: {drop_outcome['message']}"})

            if vdb_load_result["status"] != "error":
                query_response = await app.designer_rag.aGetRDFExample(classes)
            else:
                error_message = f"VectorDB loading failed: {vdb_load_result['message']}"
                raise HTTPException(status_code=404, detail={"message": error_message})

            if query_response:
                return query_response
            else:
                raise HTTPException(status_code=404, detail={"message": "Generating the RDF examples resulted in an error"})
        finally:
            drop_outcome = await app.designer_rag.chunk_entity_relation_graph.drop()
            if drop_outcome["status"] == "error":
                raise HTTPException(status_code=404, detail={"message": "Dropping graph error: {drop_outcome['message']}"})

    async def post_ontology_summary(
            self,
            post_ontology_summary_request: Optional[PostOntologySummaryRequest],
    ) -> str:
        from ..main import app

        graph = post_ontology_summary_request.current_rdf_graph

        try:
            drop_outcome = await app.designer_rag.chunk_entity_relation_graph.drop()
            if drop_outcome["status"] == "success":
                vdb_load_result = await app.designer_rag.ainsert_kg_from_gscape(graph, False)
            else:
                raise HTTPException(status_code=404, detail={"message": "Dropping graph error: {drop_outcome['message']}"})

            if vdb_load_result["status"] != "error":
                query_response = await app.designer_rag.aGetOntologySummary()
            else:
                error_message = f"VectorDB loading failed: {vdb_load_result['message']}"
                raise HTTPException(status_code=404, detail={"message": error_message})

            if query_response:
                return query_response
            else:
                raise HTTPException(status_code=404, detail={"message": "Generating the ontology summary resulted in an error"})
        finally:
            drop_outcome = await app.designer_rag.chunk_entity_relation_graph.drop()
            if drop_outcome["status"] == "error":
                raise HTTPException(status_code=404, detail={"message": "Dropping graph error: {drop_outcome['message']}"})

