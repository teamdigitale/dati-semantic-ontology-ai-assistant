# coding: utf-8

import asyncio
import threading
import os
import errno
import time
from dataclasses import (
    asdict,
    dataclass,
    field,
)
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import (
    Any, 
    Optional,
    cast,
    List,
)
from dotenv import load_dotenv
import regex
import json
import re
from functools import partial

import tempfile

from lightrag.lightrag import (
    LightRAG,
    QueryParam as lightrag_QueryParam,
    StorageNameSpace,
)

from lightrag.constants import (
    DEFAULT_ENABLE_RERANK,
)

from lightrag.namespace import NameSpace

from lightrag.utils import (
    EmbeddingFunc,
    get_env_value,
    always_get_an_event_loop,
    compute_mdhash_id,
    use_llm_func_with_cache,
    split_string_by_multi_markers,
)

from lightrag.kg.shared_storage import (
    get_namespace_data,
    get_pipeline_status_lock,
    initialize_pipeline_status,
)

from lightrag.rerank import custom_rerank, RerankModel

from .operate import (
    merge_nodes_and_edges as ai_assistant_merge_nodes_and_edges,
    kg_query as ai_assistant_kg_query,
    ENTITY_FOR_VDB,
    extract_entity_types,
)

# viene sovra-definita la funzione merge_nodes_and_edges di lightrag.operate
# con la corrispettiva versione presente in ai_assistant.operate
import importlib

from .server.models.vector_db_status import VectorDBStatus

importlib.import_module('lightrag.operate').merge_nodes_and_edges = ai_assistant_merge_nodes_and_edges
importlib.import_module('lightrag.operate').kg_query = ai_assistant_kg_query
importlib.reload(importlib.import_module('lightrag.lightrag'))

from lightrag.operate import merge_nodes_and_edges, extract_keywords_only

from .llm.openai import stub_embed, vllm_model_complete, vllm_embed
from .prompt import (
    PROMPTS_LANGUAGE,
    PROMPTS,
)
from .utils import (
    logger,
    DEFAULT_LANGUAGE,
    DEFAULT_IRI_LANGUAGE,
    inv_languages,
    get_namespace_from_iri,
)

from networkx import write_graphml
from .gscape import write_gscape, load_gscape, RDFGraph

@dataclass
class QueryParam(lightrag_QueryParam):
    """Additional configuration parameters for query execution in AI Assistant."""

    query_pattern: str = field(default="ontology_query")
    """The query template. The main actual differences are in the presence of a user question in the query
        - ontology_query (with user question)
        - instantiation_query (without user question, only system prompt)
        - summary_query (without user question, only system prompt)
    """

    prompt_to_use: str = field(default="rag_response")
    """Model prompt to resolve the query"""

    query_context_type: str = field(default="annotation")
    """
    Context type entered in the prompt:
    - annotation (default): the context is a collection of ontology annotations
    - owl: the context is an ontology in owl/ttl format
    """
    
    query_language: str | None = None
    """The language in which the query is expressed."""
    
    classes: list[str] | None = None
    """List of classes to build the context."""

@dataclass
class OntoRAG(LightRAG):
    """OntoRAG: AI-based ontology RAG assistant."""

    # Directory
    # ---

    working_dir: str = field(
        default=f"../output/ai_assistant_cache_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
    )
    """Directory where cache and temporary files are stored."""

    # LLM Configuration
    # ---

    llm_model_name: str = field(default=None)
    """Name of the LLM model used for generating responses."""

    # Rerank Configuration
    # ---

    enable_rerank: bool = field(
        default=get_env_value("ENABLE_RERANK", DEFAULT_ENABLE_RERANK, bool)
    )

    # Extensions
    # ---

    addon_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Dictionary for additional parameters and extensions."""
        # Override networkx storage implementation
        # This must be done before super's __post_init__ call
        from lightrag.lightrag import STORAGES as lightrag_STORAGES
        from .kg import STORAGES

        for k, v in STORAGES.items():
            lightrag_STORAGES[k] = v

        if "language" not in self.addon_params:
            self.addon_params["language"]=get_env_value("SUMMARY_LANGUAGE", DEFAULT_LANGUAGE, str).lower()

        if "iri_language" not in self.addon_params:
            self.addon_params["iri_language"]=get_env_value("IRI_LANGUAGE", DEFAULT_IRI_LANGUAGE, str).lower()

        if "iri_format" not in self.addon_params:
            self.addon_params["iri_format"]=get_env_value("IRI_FORMAT", "camelCase", str)

        super().__post_init__()

        # Initialize document status storage

        self.entities_vdb.meta_fields = {
            "entity_name",
            "node_type",
            "datatype",
            "lang_tag",
            "content",
            "source_id",
            "file_path",
        }
        self.relationships_vdb.meta_fields = {
            "edge_type",
            "src_id",
            "tgt_id",
            "edge_id",
            "lang_tag",
            "content",
            "source_id",
            "file_path",
        }
        self.status = VectorDBStatus(
            status='NOT_INITIALIZED',
            percentage=0
        )

    def insert(
            self,
            input: str | list[str],
            split_by_character: str | None = None,
            split_by_character_only: bool = False,
            ids: str | list[str] | None = None,
            file_paths: str | list[str] | None = None,
    ) -> None:
        """Sync Insert documents with checkpoint support

        Args:
            input: Single document string or list of document strings
            split_by_character: if split_by_character is not None, split the string by character, if chunk longer than
            chunk_token_size, it will be split again by token size.
            split_by_character_only: if split_by_character_only is True, split the string by character only, when
            split_by_character is None, this parameter is ignored.
            ids: single string of the document ID or list of unique document IDs, if not provided, MD5 hash IDs will be generated
            file_paths: single string of the file path or list of file paths, used for citation
        """

        loop = always_get_an_event_loop()
        loop.run_until_complete(
            self.ainsert(
                input, split_by_character, split_by_character_only, ids, file_paths
            )
        )

    async def ainsert(
            self,
            input: str | list[str],
            split_by_character: str | None = None,
            split_by_character_only: bool = False,
            ids: str | list[str] | None = None,
            file_paths: str | list[str] | None = None,
    ) -> None:
        """Async Insert documents with checkpoint support

        Args:
            input: Single document string or list of document strings
            split_by_character: if split_by_character is not None, split the string by character, if chunk longer than
            chunk_token_size, it will be split again by token size.
            split_by_character_only: if split_by_character_only is True, split the string by character only, when
            split_by_character is None, this parameter is ignored.
            ids: list of unique document IDs, if not provided, MD5 hash IDs will be generated
            file_paths: list of file paths corresponding to each document, used for citation
        """

        await self.apipeline_enqueue_documents(input, ids, file_paths)
        await self.apipeline_process_enqueue_documents(
            split_by_character, split_by_character_only
        )

    def insert_kg_from_gscape_file(self, gscape_file_path: str):
        if os.path.exists(gscape_file_path):
            with open(gscape_file_path) as f:
                graph_text = f.read()
            rdfGraph = RDFGraph.from_dict(json.loads(graph_text))
            self.insert_kg_from_gscape(self, rdfGraph)
        else:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), gscape_file_path)

    def insert_kg_from_gscape(self, rdfGraph: RDFGraph) -> dict[str,str]:
        loop = always_get_an_event_loop()
        return loop.run_until_complete(self.ainsert_kg_from_gscape(rdfGraph))

    async def ainsert_kg_from_gscape(self, rdfGraph: RDFGraph, detached: bool = True
    ) -> dict[str,str]:
        if detached:
            executionTime = time.time()
            self.status = VectorDBStatus(
                status='INITIALIZING',
                percentage=1,
                executionTime=0
            )
        update_storage = False
        entities_vdb_storage = await self.entities_vdb.client_storage
        entities_vdb_data = entities_vdb_storage["data"]
        if entities_vdb_data:
            storage_status = dict(status="charged", message="VectorDB has already data")
        else:
            storage_status = dict(status="empty", message="VectorDB is empty")

        class GraphNotNullError(Exception):
            def __init__(self, msg="The current graph is not null. Need to merge with input graph."):
                self.msg = msg
                super().__init__(self.msg)

            def __str__(self):
                return f'{self.msg}'

        try:
            # check if current graph is null
            current_graph = await self.chunk_entity_relation_graph.get_graph()
            if len(list(current_graph.nodes()))>0:
                raise GraphNotNullError()

            graph = load_gscape(rdfGraph)

            # load input graph
            await self.chunk_entity_relation_graph.set_graph(graph)

            # extract entities from graph
            all_entities_data = [dict(node_data, node_id = node_id) 
                for node_id,node_data in list(graph.nodes(data=True))
                    if node_data["node_type"] in ENTITY_FOR_VDB]

            if self.addon_params["enable_vdb_load"] and all_entities_data:
                # Delete old entity e relationship from vdb 
                if entities_vdb_data:
                    data_items = defaultdict(list)
                    for data in entities_vdb_data:
                        data_items[data["entity_name"]].append(data["__id__"])
                    entities_vdb_set = set(sorted(list(data_items.keys())))
                    entities_graph = await self.chunk_entity_relation_graph.get_all_labels()
                    entities_vdb_to_delete = list(entities_vdb_set.difference(entities_graph))
                    ids_to_delete = []
                    for e in entities_vdb_to_delete:
                        ids_to_delete.extend(data_items[e])
                    if ids_to_delete:
                        await self.entities_vdb.delete(ids_to_delete)
                        for e in entities_vdb_to_delete:
                            await self.relationships_vdb.delete_entity_relation(e)

                # Insert entities into vector storage with consistent format
                data_for_vdb = dict()
                for dp in all_entities_data:
                    if "label" in dp:
                        labels = dict(dp["label"])
                    else:
                        labels = dict()
                    if "description" in dp:
                        descriptions = dict(dp["description"])
                    else:
                        descriptions = dict()
                    contents = labels
                    contents.update({key: f"{labels[key]}\n{descriptions[key]}" if key in descriptions else labels[key] for key in labels})
                    contents.update({key: descriptions[key] for key in descriptions if key not in labels})
                    if contents:
                        data_for_vdb.update({
                            (
                                compute_mdhash_id(dp["node_id"], prefix="ent-"+lang_tag+"-")
                                if dp["node_type"] == "entity_type"
                                else compute_mdhash_id(dp["node_id"], prefix="cha-"+lang_tag+"-")
                            ): {"entity_name": dp["node_id"], "node_type": dp["node_type"]}
                            | (
                                {"datatype": dp["datatype"]}
                                if dp["node_type"] == "characteristic" and "datatype" in dp
                                else {}
                            )
                            | {
                                "lang_tag": lang_tag,
                                "content": content,
                                "source_id": dp.get("source_id", "UNKNOWN"),
                                "file_path": dp.get("file_path", "UNKNOWN"),
                            }
                            for lang_tag, content in contents.items()
                        })
                if data_for_vdb:
                    await self.entities_vdb.upsert(data_for_vdb)

                update_storage = True

            if detached:
                self.status.percentage = 60

            # extract relationship from graph
            all_relationships_data = [dict(edge_data, src_id = src_id, tgt_id = tgt_id, edge_id = edge_id) 
                for src_id, tgt_id, edge_id, edge_data in list(graph.edges(data=True,keys=True))
                    if edge_data["edge_type"]== "relationship"]

            # Insert relationships into vector storage with consistent format
            if update_storage and self.addon_params["enable_vdb_load"] and all_relationships_data:
                data_for_vdb = dict()
                for dp in all_relationships_data:
                    if "label" in dp:
                        labels = dict(dp["label"])
                    else:
                        labels = dict()
                    if "description" in dp:
                        descriptions = dict(dp["description"])
                    else:
                        descriptions = dict()
                    contents = labels
                    contents.update({key: f"{labels[key]}\n{descriptions[key]}" if key in descriptions else labels[key] for key in labels})
                    contents.update({key: descriptions[key] for key in descriptions if key not in labels})
                    if contents:
                        data_for_vdb.update({
                            (
                                compute_mdhash_id(dp["src_id"] + dp["tgt_id"] + dp["edge_id"], prefix="rel-"+lang_tag+"-")
                            ): {"edge_type": dp["edge_type"], 
                                "src_id": dp["src_id"], 
                                "tgt_id": dp["tgt_id"],
                                "edge_id": dp["edge_id"],
                                "lang_tag": lang_tag,
                                "content": content,
                                "source_id": dp.get("source_id","UNKNOWN"),
                                "file_path": dp.get("file_path", "UNKNOWN"),
                            }
                            for lang_tag, content in contents.items()
                        })
                if data_for_vdb:
                    await self.relationships_vdb.upsert(data_for_vdb)

                if detached:
                    self.status.percentage = 90

        except Exception as e:
            error_message = f"Error in insert_kg_from_gscape: {e}"
            logger.error(error_message)
            update_storage = False
            storage_status = dict(status="error", message=error_message)
            if detached:
                self.status = VectorDBStatus(
                    status='ERROR',
                    percentage=100,
                    executionTime=int(time.time() - executionTime),
                    errorMessage=error_message
                )

        finally:
            if update_storage:
                await self._insert_done()
                # save rdfGraph in gscape file
                if self.addon_params["enable_disk_persist"]:
                    graph_file_path = os.path.join(
                        self.working_dir,
                        f"graph_{NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION}.gscape",
                    )
                    with open(graph_file_path, "w") as f:
                        f.write(json.dumps(rdfGraph.to_dict()))
                    logger.info(
                        f"Writing graph with {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges to {graph_file_path}"
                    )
            if detached and self.status.status != 'ERROR':
                self.status = VectorDBStatus(
                    status='FINISHED',
                    percentage=100,
                    executionTime=int(time.time() - executionTime)
                )
            return storage_status

    async def _insert_done(
        self, pipeline_status=None, pipeline_status_lock=None
    ) -> None:
        if self.addon_params["enable_disk_persist"]:
            tasks = [
                cast(StorageNameSpace, storage_inst).index_done_callback()
                for storage_inst in [  # type: ignore
                    self.full_docs,
                    self.doc_status,
                    self.text_chunks,
                    self.llm_response_cache,
                    self.entities_vdb,
                    self.relationships_vdb,
                    self.chunks_vdb,
                    self.chunk_entity_relation_graph,
                ]
                if storage_inst is not None
            ]
            await asyncio.gather(*tasks)
    
            log_message = "In memory DB persist to disk"
        else:
            log_message = "Persist to disk not enabled"

        logger.info(log_message)

        if pipeline_status is not None and pipeline_status_lock is not None:
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = log_message
                pipeline_status["history_messages"].append(log_message)

    async def _drop_all(
        self, pipeline_status=None, pipeline_status_lock=None
    ) -> None:

        tasks = [
            cast(StorageNameSpace, storage_inst).drop()
            for storage_inst in [  # type: ignore
                self.full_docs,
                self.doc_status,
                self.text_chunks,
                self.llm_response_cache,
                self.entities_vdb,
                self.relationships_vdb,
                self.chunks_vdb,
                self.chunk_entity_relation_graph,
            ]
            if storage_inst is not None
        ]
        
        results = await asyncio.gather(*tasks)

        if all(s=="success" for s in [r["status"] for r in results]):
            log_message = "Dropped all objects"
        else:
            log_message = "Not all objects were dropped"

        logger.info(log_message)

        if pipeline_status is not None and pipeline_status_lock is not None:
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = log_message
                pipeline_status["history_messages"].append(log_message)

    def graph_to_disk(self, export_type=None) -> None:
        """Save graph to disk

        Args:
            export_type: "gscape" or "graphml"
        """
        graph = self.threading_asyncio_run(self.chunk_entity_relation_graph.get_graph())
        graph_file_ext = os.getenv("GRAPH_FILE_EXT", "gscape")
        if export_type is not None:
            graph_file_ext = export_type
        graph_file_path = os.path.join(
            self.working_dir,
            f"graph_{NameSpace.GRAPH_STORE_CHUNK_ENTITY_RELATION}.{graph_file_ext}",
        )
        if graph_file_ext == "gscape":
            write_gscape(graph, graph_file_path)
        else:
            write_graphml(graph, graph_file_path)
        logger.info(
            f"Writing graph with {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges to {graph_file_path}"
        )

    def threading_asyncio_run(self, func):
        def wrapper_asyncio_run(func):
            outcome = asyncio.run(func)
            threading.current_thread().return_value = outcome

        th = threading.Thread(target=wrapper_asyncio_run, args=(func,))
        th.start()
        th.join()

        return th.return_value

    def reinitialize_doc_status(self) -> dict[str, str]:
        return self.threading_asyncio_run(self.doc_status.drop())

    def queryOnOntology(
        self,
        query_text:str,
    ) -> tuple[str,list]:

        if PROMPTS_LANGUAGE == "Italian":
            response_type = "formato JSON con due keys: 'Response' e 'References'"
        else:
            response_type = "JSON format with two keys: 'Response' and 'References'"
    
        param = QueryParam(
            mode="hybrid", 
            query_pattern="ontology_query",
            prompt_to_use="rag_response",
            query_context_type="annotation",
            response_type=response_type, 
        )
        
        res = self.query(query_text,param=param)

        try:
            res = res.replace("```json", "").replace("```", "").lstrip("\n")
            try:
                data = json.loads(res)
            except ValueError as e:
                data = dict(Text=res, References=dict())

            if "Response" in data:
                text = data["Response"]
                if "References" in data and isinstance(data["References"], dict):
                    references = data["References"]
                else:
                    references = dict()
            else:
#                 text = PROMPTS["repeat_response"]
                text = res
                references = dict()

            return (text, references)
        except Exception as e:
            error_msg = f"Failed to resolve the query: {query_text}: \n LLM response: {res} \n error: {str(e)}"
            logger.error(error_msg)
            raise e

    async def aqueryOnOntology(
        self,
        query_text:str,
    ) -> tuple[str,list]:

        if PROMPTS_LANGUAGE == "Italian":
            response_type = "formato JSON con due keys: 'Response' e 'References'"
        else:
            response_type = "JSON format with two keys: 'Response' and 'References'"

        param = QueryParam(
            mode="hybrid", 
            query_pattern="ontology_query",
            prompt_to_use="rag_response",
            query_context_type="annotation",
            response_type=response_type, 
        )
        
        res = await self.aquery(query_text,param=param)

        try:
            res = res.replace("```json", "").replace("```", "")
            try:
                data = json.loads(res)
            except ValueError as e:
                data = dict(Text=res, References=dict())

            if "Response" in data:
                text = data["Response"]
                if "References" in data and isinstance(data["References"], dict):
                    references = data["References"]
                else:
                    references = dict()
            else:
#                 text = PROMPTS["repeat_response"]
                text = res
                references = dict()

            return (text, references)
        except Exception as e:
            error_msg = f"Failed to resolve the query: {query_text}: \n LLM response: {res} \n error: {str(e)}"
            logger.error(error_msg)
            raise e

    def getRDFExample(
        self,
        classes:list[str],
    ) -> str:

        if PROMPTS_LANGUAGE == "Italian":
            response_type = "formato RDF Turtle"
        else:
            response_type = "RDF Turtle format"

        param = QueryParam(
            mode="local", 
            query_pattern="instantiation_query",
            prompt_to_use="rag_RDF_example",
            query_context_type="owl",
            response_type=response_type, 
            classes=classes,
        )

        return self.query("",param=param)

    async def aGetRDFExample(
        self,
        classes:list[str],
    ) -> str:

        if PROMPTS_LANGUAGE == "Italian":
            response_type = "formato RDF Turtle"
        else:
            response_type = "RDF Turtle format"

        param = QueryParam(
            mode="local", 
            query_pattern="instantiation_query",
            prompt_to_use="rag_RDF_example",
            query_context_type="owl",
            response_type=response_type, 
            classes=classes,
        )

        res = await self.aquery("",param=param)
        
        if res:
            res = res.replace("```ttl", "").replace("```", "").lstrip("\n")

        return res

    def getOntologySummary(
        self,
    ) -> str:

        if PROMPTS_LANGUAGE == "Italian":
            response_type = "Paragrafi multipli"
        else:
            response_type = "Multiple Paragraphs"

        param = QueryParam(
            mode="local", # start from entities
            query_pattern="summary_query",
            prompt_to_use="rag_ontology_summary",
            query_context_type="annotation",
            response_type=response_type,
        )

        return self.query("",param=param)

    async def aGetOntologySummary(
        self,
    ) -> str:

        if PROMPTS_LANGUAGE == "Italian":
            response_type = "Paragrafi multipli"
        else:
            response_type = "Multiple Paragraphs"

        param = QueryParam(
            mode="local", # start from entities
            query_pattern="summary_query",
            prompt_to_use="rag_ontology_summary",
            query_context_type="annotation",
            response_type=response_type,
        )

        return await self.aquery("",param=param)

    async def _process_entity_relation_graph(
            self, chunk: dict[str, Any], pipeline_status=None, pipeline_status_lock=None
    ) -> list:
        seen_docs=dict()
        
        async def _find_doc_language(text: str) -> str:
            use_llm_func: callable = self.llm_model_func
            use_llm_func = partial(use_llm_func, _priority=8)
            prompt_template = PROMPTS["find_doc_language"]
            context_base = dict(
                language=DEFAULT_LANGUAGE,
                text=text,
            )
            use_prompt = prompt_template.format(**context_base)

             # Use LLM function without cache (higher priority for language retrive)
            result = await use_llm_func_with_cache(
                use_prompt,
                use_llm_func,
            )
            pattern = "|".join(list(inv_languages.keys()))
            match = re.search(pattern,result.lower())
            if match:
                language = match.group(0)
            else:
                language = "UNKNOWN"
            return language
       
        try:
            for chunk_id, chunk_content in chunk.items():
                if not chunk_content["content"]:
                    continue
                doc_id = chunk_content["full_doc_id"]
                if doc_id not in seen_docs:
                    status_doc = await self.doc_status.get_by_id(doc_id)
                    doc_summary = status_doc["content_summary"]
                    language = await _find_doc_language(doc_summary)
                    lang_tag = inv_languages[language]
                    status_doc["lang_tag"] = lang_tag
                    full_doc = await self.full_docs.get_by_id(doc_id)
                    full_doc["lang_tag"] = lang_tag
                    await self.full_docs.upsert({doc_id:full_doc})
                    seen_docs[doc_id]=lang_tag
                chunk[chunk_id]["lang_tag"] = seen_docs[doc_id]

            chunk_results = await extract_entity_types(
                chunk,
                global_config=asdict(self),
                pipeline_status=pipeline_status,
                pipeline_status_lock=pipeline_status_lock,
                llm_response_cache=self.llm_response_cache,
                text_chunks_storage=self.text_chunks,
            )
            return chunk_results
        except Exception as e:
            error_msg = f"Failed to extract entities and relationships: {str(e)}"
            logger.error(error_msg)
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = error_msg
                pipeline_status["history_messages"].append(error_msg)
            raise e

async def initialize_ontorag(**kwargs):
    load_dotenv(
        override=False
    )  # the OS environment variables take precedence over the .env file
    cwd = kwargs.get("working_dir", tempfile.mkdtemp(prefix="designer-"))

    rerank_model = RerankModel(
        rerank_func=custom_rerank,
        kwargs={
            "model": str(os.getenv("RERANK_MODEL")),
            "base_url": str(os.getenv("RERANK_BINDING_HOST")),
            "api_key": str(os.getenv("RERANK_BINDING_API_KEY")),
        },
    )

    designer = OntoRAG(
        working_dir=cwd,
        llm_model_name=os.getenv("LLM_MODEL"),
        llm_model_func=vllm_model_complete,
        llm_model_kwargs=(
            {"temperature": float(os.getenv("TEMPERATURE", 0.5))}
            | {"seed": int(os.getenv("SEED"))}
            if os.getenv("SEED") is not None
            else {} | {"timeout": float(os.getenv("TIMEOUT"))}
            if os.getenv("TIMEOUT") is not None
            else {}
        ),
        enable_llm_cache=os.getenv("ENABLE_LLM_CACHE", "False").strip().lower() == "true",
        enable_llm_cache_for_entity_extract=os.getenv(
            "ENABLE_LLM_CACHE_FOR_EXTRACT", "False"
        ).strip().lower() == "true",
        addon_params={
            "example_number": 0,
            "enable_vdb_load_for_extract": os.getenv("ENABLE_VDB_LOAD_FOR_EXTRACT", "False").strip().lower() == "true",
            "enable_vdb_load": os.getenv("ENABLE_VDB_LOAD", "True").strip().lower() == "true",
            "enable_disk_persist": os.getenv("ENABLE_DISK_PERSIST", "False").strip().lower() == "true",
        },
        entity_extract_max_gleaning=0,
        embedding_func=EmbeddingFunc(
            embedding_dim=int(os.getenv("EMBEDDING_DIM", 1024)),
            max_token_size=int(os.getenv("MAX_EMBED_TOKENS", 8192)),
            func=vllm_embed,
        ),

        # Rerank Configuration - provide the rerank function
        rerank_model_func=rerank_model.rerank,  # Method 2

    )
    await designer.initialize_storages()
    await initialize_pipeline_status()
    # Initialize graph
    if kwargs.get("entity_relation_graph"):
        await designer.chunk_entity_relation_graph.set_graph(
            kwargs["entity_relation_graph"]
        )
    return designer
