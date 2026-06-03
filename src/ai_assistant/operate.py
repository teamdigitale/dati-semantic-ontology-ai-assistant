from __future__ import annotations
from functools import partial

import asyncio
import json
import re
import regex
import os
import time
import copy
from collections import Counter, defaultdict
import networkx as nx

from .jvm.java import *
from .jvm.owlapi import *

from lightrag.utils import (
    clean_str,
    compute_mdhash_id,
    is_float_regex,
    pack_user_ass_to_openai_messages,
    split_string_by_multi_markers,
    truncate_list_by_token_size,
    process_combine_contexts,
    compute_args_hash,
    handle_cache,
    save_to_cache,
    CacheData,
    use_llm_func_with_cache,
    update_chunk_cache_list,
)

from .utils import (
    inv_languages,
    logger,
    DEFAULT_LANGUAGE,
    DEFAULT_IRI_LANGUAGE,
    is_name_regex,
    is_text_regex,
    simple_name_to_label,
    get_namespace_from_iri,
    iri_add_simple_name,
)

from lightrag.base import (
    BaseGraphStorage,
    BaseKVStorage,
    BaseVectorStorage,
    TextChunkSchema,
)
from .prompt import PROMPTS
from lightrag.constants import (
    GRAPH_FIELD_SEP,
    DEFAULT_TOP_K,
    DEFAULT_MAX_ENTITY_TOKENS,
    DEFAULT_MAX_RELATION_TOKENS,
    DEFAULT_MAX_TOTAL_TOKENS,
    DEFAULT_RELATED_CHUNK_NUMBER,
)
from lightrag.kg.shared_storage import get_storage_keyed_lock
from lightrag.operate import (
    _handle_entity_relation_summary as lightrag_handle_entity_relation_summary,
    get_keywords_from_query,
    apply_rerank_if_enabled,
    process_chunks_unified,
)

from .gscape import (
    RDFS_SUBCLASS,
    RDFS_COMMENT,
    RDFS_LABEL,
    DATATYPES, 
    write_gscape, 
    rdf_graph_to_owl, 
    serialize_owl,
)

ENTITY_FOR_VDB = ["entity_type", "characteristic"]

DCT_TITLE = "http://purl.org/dc/terms/title"
DCT_DESCRIPTION = "http://purl.org/dc/terms/description"
DCT_IDENTIFIER = "http://purl.org/dc/terms/identifier"
DCAT_KEYWORD = "http://www.w3.org/ns/dcat#keyword"
ADMS_HASKEYCLASS = "https://w3id.org/italia/onto/ADMS/hasKeyClass"

async def _handle_entity_relation_summary(
    entity_or_relation_name: str,
    description: str,
    global_config: dict,
    llm_response_cache: BaseKVStorage | None = None,
) -> str:
    """Handle entity relation summary
    For each entity or relation, input is the combined description of already existing description and new description.
    If too long, use LLM to summarize.
    """
    summary = await lightrag_handle_entity_relation_summary(
        entity_or_relation_name,
        description,
        global_config,
        llm_response_cache,
    )

    # Delete any premises to the result (e.g. "The summary is: ")
    match = regex.fullmatch(r"^(?:\p{Latin}| )*:(?: |\n)*(\".*\")", summary)
    if match:
        summary = match.group(1)

    return summary

async def _handle_single_entity_type_extraction(
    record_attributes: list[str],
    chunk_key: str,
    file_path: str = "unknown_source",
):
    if len(record_attributes) < 3 or record_attributes[0].strip('"') != "entity_type":
        return None

    # Clean and validate entity name
    entity_type_name = clean_str(record_attributes[1]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not entity_type_name.strip() or not is_name_regex(entity_type_name):
        logger.warning(
            f"Entity type extraction error: empty or incorrect entity type name in: {record_attributes}"
        )
        return None

    # Clean and validate description
    entity_type_description = clean_str(record_attributes[2]).lstrip('"< ').rstrip(' ">')
    if not is_text_regex(entity_type_description):
        logger.warning(
            f"Entity type extraction error: empty or incorrect description for type entity '{entity_type_name}'"
        )
        return None

    # il nome della classe ha sempre l'iniziale maiuscola
    entity_type_name = entity_type_name[:1].upper() + entity_type_name[1:]

    return dict(
        node_id=entity_type_name,
        node_type="entity_type",
        description=entity_type_description,
        source_id=chunk_key,
        file_path=file_path,
    )


async def _handle_single_relationship_extraction(
    record_attributes: list[str],
    chunk_key: str,
    file_path: str = "unknown_source",
    datatypes: list | None = None,
):
    if datatypes is None:
        datatypes = list()

    if len(record_attributes) < 5 or record_attributes[0].strip('"') != "relationship":
        return None
    # add this record as edge
    relationship_name = clean_str(record_attributes[1]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not is_name_regex(relationship_name):
        return None
    source = clean_str(record_attributes[2]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not source.strip() or not is_name_regex(source):
        return None
    target = clean_str(record_attributes[3]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not target.strip() or not is_name_regex(target):
        return None
    # a relationship can't have a node named as a datatype
    if source.lower() in datatypes or target.lower() in datatypes:
        return None
    edge_description = clean_str(record_attributes[4]).lstrip('"< ').rstrip(' ">')
    if not is_text_regex(edge_description):
        return None
    # i nomi delle classi hanno sempre l'iniziale maiuscola
    source = source[:1].upper() + source[1:]
    target = target[:1].upper() + target[1:]
    # il nome della relazione ha sempre l'iniziale minuscola
    relationship_name = relationship_name[:1].lower() + relationship_name[1:]
    weight = (
        float(record_attributes[-1].strip('"'))
        if is_float_regex(record_attributes[-1])
        else 0.0
    )
    return dict(
        src_id=source,
        tgt_id=target,
        edge_type="relationship",
        weight=weight,
        relationship_name=relationship_name,
        description=edge_description,
        source_id=chunk_key,
        file_path=file_path,
    )

async def _handle_single_characteristic_extraction(
    record_attributes: list[str],
    chunk_key: str,
    file_path: str = "unknown_source",
    datatypes: list | None = None,
):
    if datatypes is None:
        datatypes = list()

    if len(record_attributes) < 5 or record_attributes[0].strip('"') != "characteristic":
        return None, None
    # add this record as node
    characteristic_name = clean_str(record_attributes[1]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not characteristic_name.strip() or not is_name_regex(characteristic_name):
        return None, None

    characteristic_datatype = clean_str(record_attributes[3].lstrip('"< ').rstrip(' ">').lower())

    # Reject the unexpected characteristic datatype
    if characteristic_datatype not in datatypes:
        return None, None
    else:
        datatype = DATATYPES[characteristic_datatype]

    characteristic_description = clean_str(record_attributes[4]).lstrip('"< ').rstrip(' ">')
    if not is_text_regex(characteristic_description):
        return None, None

    # add this record as edge
    entity_type = clean_str(record_attributes[2]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not entity_type.strip() or not is_name_regex(entity_type):
        return None, None

    # il nome della classe ha sempre l'iniziale maiuscola
    entity_type = entity_type[:1].upper() + entity_type[1:]
    # il nome dell'attributo ha sempre l'iniziale minuscola
    characteristic_name = characteristic_name[:1].lower() + characteristic_name[1:]

    characteristic_node = dict(
        node_id=characteristic_name,
        node_type="characteristic",
        datatype=datatype,
        description=characteristic_description,
        source_id=chunk_key,
        file_path=file_path,
    )
    characteristic_edge = dict(
        src_id=entity_type,         # from class
        tgt_id=characteristic_name, # to data_property
        edge_type="characteristic",
        source_id=chunk_key,
        file_path=file_path,
    )
    return characteristic_node, characteristic_edge


async def _handle_single_subclass_extraction(
    record_attributes: list[str],
    chunk_key: str,
    file_path: str = "unknown_source",
    datatypes: list | None = None,
):
    if datatypes is None:
        datatypes = list()

    if len(record_attributes) < 3 or record_attributes[0].strip('"') != "subclass":
        return None
    # add this record as edge
    source = clean_str(record_attributes[1]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not source.strip() or not is_name_regex(source):
        return None
    target = clean_str(record_attributes[2]).lstrip('"< ').rstrip(' ">').replace(" ","")
    if not target.strip() or not is_name_regex(target):
        return None
    # a subclass relationship can't have a node named as a datatype
    if source.lower() in datatypes or target.lower() in datatypes:
        return None
    # a subclass relationship can't be on the same node
    if source == target:
        return None

    # i nomi delle classi hanno sempre l'iniziale maiuscola
    source = source[:1].upper() + source[1:]
    target = target[:1].upper() + target[1:]

    return dict(
        src_id=source, # child
        tgt_id=target, # father
        edge_type="subclass",
        source_id=chunk_key,
        file_path=file_path,
    )

async def _merge_nodes_then_upsert(
    node_type: str,
    node_id: str,
    nodes_data: list[dict],
    knowledge_graph_inst: BaseGraphStorage,
    global_config: dict,
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
):
    """
    Get existing nodes from knowledge graph use name,if exists, merge data,
    else create, then upsert.
    """
    already_source_ids = []
    already_description = []
    already_datatypes = []
    already_file_paths = []
    
    language = global_config["addon_params"].get(
        "language", DEFAULT_LANGUAGE
    )
    lang_tag = inv_languages[language]
    iri_language = global_config["addon_params"].get(
        "iri_language", DEFAULT_IRI_LANGUAGE
    )
    iri_lang_tag = inv_languages[iri_language]
    iri_format = global_config["addon_params"].get("iri_format", "camelCase")

    node_id_without_iri = node_id[len(get_namespace_from_iri(node_id)) :]
    current_graph = await knowledge_graph_inst.get_graph()
    already_edge_ids = [(i, j, k) for i, j, k in current_graph.edges if k == node_id]
    if len(already_edge_ids) > 0:
        logger.warning(
            f"There is already an entity with name {node_id}. Discarded the second."
        )
        return None

    already_node = await knowledge_graph_inst.get_node(node_id)
    node_frozen = False
    description = dict()
    if already_node is not None:
        already_node_type = already_node["node_type"]
        node_frozen = already_node["frozen"] if "frozen" in already_node else False
        if not (already_node_type == node_type):
            logger.warning(
                f"There is already the node {node_id} but has {already_node_type} and not {node_type} type. Discarded the second."
            )
            return None

        # Update pipeline status when a node that needs merging is found
        status_message = f"Merging entity: {node_id}"
        logger.info(status_message)
        if pipeline_status is not None and pipeline_status_lock is not None:
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = status_message
                pipeline_status["history_messages"].append(status_message)

        # Get source_id with empty string default if missing or None
        if "source_id" in already_node and already_node["source_id"] is not None:
            already_source_ids.extend(
                split_string_by_multi_markers(
                    already_node["source_id"], [GRAPH_FIELD_SEP]
                )
            )
        # Get file_path with empty string default if missing or unknown_source
        if (
            "file_path" in already_node
            and already_node["file_path"] is not None
            and already_node["file_path"] != "unknown_source"
        ):
            already_file_paths.extend(
                split_string_by_multi_markers(
                    already_node["file_path"], [GRAPH_FIELD_SEP]
                )
            )
        # Get description with empty string default if missing or None
        if "description" in already_node:
            description = dict(already_node["description"])
            if (
                not node_frozen
                and lang_tag in already_node["description"]
                and already_node["description"][lang_tag] is not None
            ):
                already_description.append(already_node["description"][lang_tag])

        if node_type == "characteristic":
            already_datatypes.append(already_node["datatype"])

    if (not node_frozen
        or (node_frozen and len(already_description)==0)
    ):
        description_text = GRAPH_FIELD_SEP.join(
            sorted(set([dp["description"] for dp in nodes_data if dp.get("description")] + already_description))
        )

        force_llm_summary_on_merge = global_config["force_llm_summary_on_merge"]

        num_fragment = description_text.count(GRAPH_FIELD_SEP) + 1
        num_new_fragment = len(set([dp["description"] for dp in nodes_data if dp.get("description")]))

        if num_fragment > 1:
            if num_fragment >= force_llm_summary_on_merge:
                status_message = f"LLM merge N: {node_id} | {num_new_fragment}+{num_fragment-num_new_fragment}"
                logger.info(status_message)
                if pipeline_status is not None and pipeline_status_lock is not None:
                    async with pipeline_status_lock:
                        pipeline_status["latest_message"] = status_message
                        pipeline_status["history_messages"].append(status_message)
                description_text = await _handle_entity_relation_summary(
                    node_id_without_iri,
                    description_text,
                    global_config,
                    llm_response_cache,
                )
            else:
                status_message = f"Merge N: {node_id} | {num_new_fragment}+{num_fragment-num_new_fragment}"
                logger.info(status_message)
                if pipeline_status is not None and pipeline_status_lock is not None:
                    async with pipeline_status_lock:
                        pipeline_status["latest_message"] = status_message
                        pipeline_status["history_messages"].append(status_message)
        description[lang_tag] = description_text

    source_id = GRAPH_FIELD_SEP.join(
        set([dp["source_id"] for dp in nodes_data] + already_source_ids)
    )

    file_path = GRAPH_FIELD_SEP.join(
        set([dp["file_path"] for dp in nodes_data] + already_file_paths)
    )

    node_data = dict(
        node_type=node_type,
        description=description,
        source_id=source_id,
        file_path=file_path,
    )

    if node_id != node_id_without_iri:
        node_data["namespace"] = get_namespace_from_iri(node_id)

    if node_frozen:
        node_data["frozen"] = node_frozen

    if node_type == "characteristic":
        if already_datatypes and already_datatypes[0] not in DATATYPES.values():
            datatype = already_datatypes[0]
        else:
            datatype = sorted(
                Counter([dp["datatype"] for dp in nodes_data] + already_datatypes).items(),
                key=lambda x: x[1],
                reverse=True,
            )[0][0]
        node_data["datatype"] = datatype

    if (already_node is not None 
        and "label" in already_node
    ):
        node_data["label"] = dict(already_node["label"])
    else:
        node_data["label"] = dict()
    if (lang_tag not in node_data["label"]
        or node_data["label"][lang_tag] is None
    ):
        if iri_lang_tag not in node_data["label"]:
            iri_lang_label = simple_name_to_label(node_id_without_iri, iri_format)
            node_data["label"][iri_lang_tag] = iri_lang_label
        if iri_lang_tag != lang_tag:
            iri_lang_label = node_data["label"][iri_lang_tag]
            lang_label = await _label_translate(iri_lang_label, iri_language, language, global_config)
            node_data["label"][lang_tag] = lang_label

    await knowledge_graph_inst.upsert_node(
        node_id,
        node_data=node_data,
    )

    node_data["node_id"] = node_id

    return node_data

async def _merge_edges_then_upsert(
    edge_type: str,
    src_id: str,
    tgt_id: str,
    edge_id: str,
    edges_data: list[dict],
    knowledge_graph_inst: BaseGraphStorage,
    global_config: dict,
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
):
    already_weights = []
    already_source_ids = []
    already_description = []
    already_file_paths = []
    already_edge = None

    language = global_config["addon_params"].get(
        "language", DEFAULT_LANGUAGE
    )
    lang_tag = inv_languages[language]
    iri_language = global_config["addon_params"].get(
        "iri_language", DEFAULT_IRI_LANGUAGE
    )
    iri_lang_tag = inv_languages[iri_language]
    iri_format = global_config["addon_params"].get("iri_format", "camelCase")

    src_id_without_iri = src_id[len(get_namespace_from_iri(src_id)) :]
    tgt_id_without_iri = tgt_id[len(get_namespace_from_iri(tgt_id)) :]
    edge_id_without_iri = edge_id[len(get_namespace_from_iri(edge_id)) :]

    if edge_type == "relationship":
        # Valuto la presenza di archi con lo stesso identificativo, nel caso scarto questo in esame
        current_graph = await knowledge_graph_inst.get_graph()
        already_edge_ids = [(i, j, k) for i, j, k in current_graph.edges if k == edge_id and (i != src_id or j != tgt_id)]
        if len(already_edge_ids) > 0:
            logger.warning(
                f"There is already a relationship with name {edge_id}. Discarded the second."
            )
            return None
        if await knowledge_graph_inst.has_node(edge_id):
            logger.warning(
                f"There is already an entity with name {edge_id}. Discarded the second."
            )
            return None

    already_src = await knowledge_graph_inst.get_node(src_id)
    # Valuto la compatibilità di source e target della relazione
    if already_src is not None and already_src["node_type"] != "entity_type":
        logger.warning(
            f"The relationship has the source node {src_id} that is not an entity type"
        )
        return None
        # Valuto la compatibilità di source e target della relazione
    already_tgt = await knowledge_graph_inst.get_node(tgt_id)
    if already_tgt is not None:
        if (edge_type == "relationship" or edge_type == "subclass") and already_tgt["node_type"] != "entity_type":
            logger.warning(
                f"The relationship has the target node {tgt_id} that is not an entity type"
            )
            return None
        if edge_type == "characteristic" and already_tgt["node_type"] != "characteristic":
            logger.warning(
                f"The relationship has the target node {tgt_id} that is not a characteristic"
            )
            return None

    if await knowledge_graph_inst.has_edge(src_id, tgt_id, edge_id):
        # Update pipeline status when an edge that needs merging is found
        status_message = f"Merging edge::: {src_id} - {tgt_id}"
        logger.info(status_message)
        if pipeline_status is not None and pipeline_status_lock is not None:
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = status_message
                pipeline_status["history_messages"].append(status_message)

        already_edge = await knowledge_graph_inst.get_edge(src_id, tgt_id, edge_id)
        # Handle the case where get_edge returns None or missing fields
        if already_edge:
            # Get source_id with empty string default if missing or None
            if "source_id" in already_edge and already_edge["source_id"] is not None:
                already_source_ids.extend(
                    split_string_by_multi_markers(
                        already_edge["source_id"], [GRAPH_FIELD_SEP]
                    )
                )

            # Get file_path with empty string default if missing or None
            if (
                "file_path" in already_edge
                and already_edge["file_path"] is not None
                and already_edge["file_path"] != "unknown_source"
            ):
                already_file_paths.extend(
                    split_string_by_multi_markers(
                        already_edge["file_path"], [GRAPH_FIELD_SEP]
                    )
                )

    source_id = GRAPH_FIELD_SEP.join(
        set(
            [dp["source_id"] for dp in edges_data if dp.get("source_id")]
            + already_source_ids
        )
    )

    file_path = GRAPH_FIELD_SEP.join(
        set(
            [dp["file_path"] for dp in edges_data if dp.get("file_path")]
            + already_file_paths
        )
    )
    workspace = global_config.get("workspace", "")
    namespace = f"{workspace}:GraphDB" if workspace else "GraphDB"
    need_insert_nodes = []
    need_insert_vdb_entities = []

    if edge_type == "relationship":
        description = dict()
        edge_frozen = False
        if already_edge:
            edge_frozen = already_edge["frozen"] if "frozen" in already_edge else False
            # Get weight with default 0.0 if missing
            if "weight" in already_edge:
                already_weights.append(already_edge["weight"])
            else:
                logger.warning(
                    f"The edge {edge_id} between {src_id} and {tgt_id} missing weight field"
                )
                already_weights.append(0.0)

            # Get description with empty string default if missing or None
            if "description" in already_edge:
                description = dict(already_edge["description"])
                if (
                    not edge_frozen
                    and lang_tag in already_edge["description"]
                    and already_edge["description"][lang_tag] is not None
                ):
                    already_description.append(already_edge["description"][lang_tag])

        # Process edges_data with None checks
        weight = sum([dp["weight"] for dp in edges_data] + already_weights)

        if (not edge_frozen
            or (edge_frozen and len(already_description)==0)
        ):
            description_text = GRAPH_FIELD_SEP.join(
                sorted(
                    set(
                        [
                            dp["description"]
                            for dp in edges_data
                            if dp.get("description")
                        ]
                        + already_description
                    )
                )
            )

            force_llm_summary_on_merge = global_config["force_llm_summary_on_merge"]

            num_fragment = description_text.count(GRAPH_FIELD_SEP) + 1
            num_new_fragment = len(
                set([dp["description"] for dp in edges_data if dp.get("description")])
            )

            if num_fragment > 1:
                if num_fragment >= force_llm_summary_on_merge:
                    status_message = f"LLM merge {edge_id}: {src_id} - {tgt_id} | {num_new_fragment}+{num_fragment-num_new_fragment}"
                    logger.info(status_message)
                    if pipeline_status is not None and pipeline_status_lock is not None:
                        async with pipeline_status_lock:
                            pipeline_status["latest_message"] = status_message
                            pipeline_status["history_messages"].append(status_message)
                    description_text = await _handle_entity_relation_summary(
                        f"({src_id_without_iri}, {tgt_id_without_iri}, {edge_id_without_iri})",  # viene inserito anche il nome della relazione
                        description_text,
                        global_config,
                        llm_response_cache,
                    )
                else:
                    status_message = f"Merge {edge_id}: {src_id} - {tgt_id} | {num_new_fragment}+{num_fragment-num_new_fragment}"
                    logger.info(status_message)
                    if pipeline_status is not None and pipeline_status_lock is not None:
                        async with pipeline_status_lock:
                            pipeline_status["latest_message"] = status_message
                            pipeline_status["history_messages"].append(status_message)

            description[lang_tag] = description_text

        need_insert_nodes.extend([
            (src_id, src_id_without_iri),
            (tgt_id, tgt_id_without_iri),
        ])

        edge_data = dict(
            edge_type=edge_type,
            description=description,
            weight=weight,
            source_id=source_id,
            file_path=file_path,
        )

        if edge_id != edge_id_without_iri:
            edge_data["namespace"] = get_namespace_from_iri(edge_id)

        if edge_frozen:
            edge_data["frozen"] = edge_frozen

    elif edge_type == "characteristic":
        # inserisco solo il nodo padre, l'attributo è stato definito contestualmente all'arco
        need_insert_nodes.append((src_id, src_id_without_iri))
        
        edge_data = dict(
            edge_type=edge_type,
            source_id=source_id,
            file_path=file_path,
        )

    elif edge_type == "subclass":
        need_insert_nodes.extend([
            (src_id, src_id_without_iri),
            (tgt_id, tgt_id_without_iri),
        ])

        edge_data = dict(
            edge_type=edge_type,
            source_id=source_id,
            file_path=file_path,
        )

    else:
        edge_data = None

    for need_insert in need_insert_nodes:
        async with get_storage_keyed_lock(
            [need_insert[0]], namespace=namespace, enable_logging=False
        ):
            if not (await knowledge_graph_inst.has_node(need_insert[0])):
                need_insert_label = dict()
                iri_lang_label = simple_name_to_label(need_insert[1], iri_format)
                need_insert_label[iri_lang_tag] = iri_lang_label
                if iri_lang_tag != lang_tag:
                    lang_label = await _label_translate(iri_lang_label, iri_language, language, global_config)
                    need_insert_label[lang_tag] = lang_label
                node_data={
                    "node_type": "entity_type",
                    "label": need_insert_label,
                    "description": dict(),
                    "source_id": source_id,
                    "file_path": file_path,
                }
                need_insert_vdb_entities.append(tuple((need_insert[0],node_data)))
                await knowledge_graph_inst.upsert_node(
                    need_insert[0],
                    node_data=node_data,
                )

    if edge_data:
        # aggiungo la label se già presente per quell'arco
        if (already_edge is not None 
            and "label" in already_edge
        ):
            edge_data["label"] = dict(already_edge["label"])
        else:
            # aggiungo la label solo per il tipo relationship
            if edge_type == "relationship":
                edge_data["label"] = dict()
        if ("label" in edge_data and
            (lang_tag not in edge_data["label"]
            or edge_data["label"][lang_tag] is None)
        ):
            if iri_lang_tag not in edge_data["label"]:
                iri_lang_label = simple_name_to_label(edge_id_without_iri, iri_format)
                edge_data["label"][iri_lang_tag] = iri_lang_label
            if iri_lang_tag != lang_tag:
                iri_lang_label = edge_data["label"][iri_lang_tag]
                lang_label = await _label_translate(iri_lang_label, iri_language, language, global_config)
                edge_data["label"][lang_tag] = lang_label

        await knowledge_graph_inst.upsert_edge(
            src_id, tgt_id, edge_id, edge_data=edge_data
        )
        edge_data["src_id"] = src_id
        edge_data["tgt_id"] = tgt_id
        edge_data["edge_id"] = edge_id
        edge_data["need_insert_node"] = need_insert_vdb_entities

    return edge_data

async def _label_translate(
    text: str,
    in_language: str,
    out_language: str,
    global_config: dict
) -> str:
    use_llm_func: callable = global_config["llm_model_func"]
    use_llm_func = partial(use_llm_func, _priority=8)
    prompt_template = PROMPTS["label_translate"]
    context_base = dict(
        in_language=in_language,
        out_language=out_language,
        descriptor=text,
    )
    use_prompt = prompt_template.format(**context_base)

     # Use LLM function with cache (higher priority for language retrive)
    result = await use_llm_func_with_cache(
        use_prompt,
        use_llm_func,
#                 llm_response_cache= self.llm_response_cache,
#                 cache_type="extract",
    )
    return result

async def merge_nodes_and_edges(
    chunk_results: list,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict[str, str],
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
    current_file_number: int = 0,
    total_files: int = 0,
    file_path: str = "unknown_source",
) -> None:
    """Merge nodes and edges from extraction results

    Args:
        chunk_results: List of tuples (maybe_nodes, maybe_edges) containing extracted entities and relationships
        knowledge_graph_inst: Knowledge graph storage
        entity_vdb: Entity vector database
        relationships_vdb: Relationship vector database
        global_config: Global configuration
        pipeline_status: Pipeline status dictionary
        pipeline_status_lock: Lock for pipeline status
        llm_response_cache: LLM response cache
    """

    # Collect all nodes and edges from all chunks
    all_nodes = defaultdict(list)
    all_edges = defaultdict(list)

    language = global_config["addon_params"].get("language", "italiano")
    lang_tag = inv_languages[language]
    enable_vdb_load_for_extract = global_config["addon_params"].get("enable_vdb_load_for_extract", True)

    for maybe_nodes, maybe_edges in chunk_results:
        # Collect nodes
        for entity_name, entities in maybe_nodes.items():
            all_nodes[entity_name].extend(entities)

        # Collect edges with sorted keys for multi-directed graph
        for edge_key, edges in maybe_edges.items():
            #             sorted_edge_key = tuple(sorted(edge_key))
            all_edges[edge_key].extend(edges)

    # Centralized processing of all nodes and edges
    total_entities_count = len(all_nodes)
    total_relations_count = len(all_edges)

    # Merge nodes and edges
    log_message = f"Merging stage {current_file_number}/{total_files}: {file_path}"
    logger.info(log_message)
    async with pipeline_status_lock:
        pipeline_status["latest_message"] = log_message
        pipeline_status["history_messages"].append(log_message)

    # Get max async tasks limit from global_config for semaphore control
    graph_max_async = global_config.get("llm_model_max_async", 4) * 2
    semaphore = asyncio.Semaphore(graph_max_async)

    # Process and update all entities and relationships in parallel
    log_message = f"Processing: {total_entities_count} entities and {total_relations_count} relations (async: {graph_max_async})"
    logger.info(log_message)
    async with pipeline_status_lock:
        pipeline_status["latest_message"] = log_message
        pipeline_status["history_messages"].append(log_message)

    async def _locked_process_entity_name(entity_name, entities, merge=True):
        async with semaphore:
            workspace = global_config.get("workspace", "")
            namespace = f"{workspace}:GraphDB" if workspace else "GraphDB"
            async with get_storage_keyed_lock(
                [entity_name], namespace=namespace, enable_logging=False
            ):
                node_id = entity_name[1]
                node_type = entity_name[0]
                logger.debug(
                    f"entity name: {node_id} , entity type: {node_type}"
                
                )
                if merge:
                    try:
                        entity_data = await _merge_nodes_then_upsert(
                            node_type,
                            node_id,
                            entities,
                            knowledge_graph_inst,
                            global_config,
                            pipeline_status,
                            pipeline_status_lock,
                            llm_response_cache,
                        )
                    except Exception as exception:
                        log_message = (
                            f"Merging {entity_name} return an unexpected {exception = }"
                        )
                        logger.error(log_message)
                        return None
                else:
                    entity_data = entities

                if entity_data is None or node_type not in ENTITY_FOR_VDB:
                    return None

                if enable_vdb_load_for_extract and entity_vdb is not None:
                    if "label" in entity_data:
                        labels = dict(entity_data["label"])
                    else:
                        labels = dict()
                    if "description" in entity_data:
                        descriptions = dict(entity_data["description"])
                    else:
                        descriptions = dict()
                    contents = labels
                    contents.update({key: f"{labels[key]}\n{descriptions[key]}" if key in descriptions else labels[key] for key in labels})
                    contents.update({key: descriptions[key] for key in descriptions if key not in labels})
                    if not contents:
                        return None
                    data_for_vdb = {
                        (
                            compute_mdhash_id(node_id, prefix="ent-"+lang_tag+"-")
                            if node_type == "entity_type"
                            else compute_mdhash_id(node_id, prefix="cha-"+lang_tag+"-")
                        ): {"entity_name": node_id, "node_type": node_type}
                        | (
                            {"datatype": entity_data["datatype"]}
                            if node_type == "characteristic" and "datatype" in entity_data
                            else {}
                        )
                        | {
                            "lang_tag": lang_tag,
                            "content": content,
                            "source_id": entity_data.get("source_id", "unknown_source"),
                            "file_path": entity_data.get("file_path", "unknown_source"),
                        }
                        for lang_tag, content in contents.items()
                    }
                    await entity_vdb.upsert(data_for_vdb)
                return entity_data

    async def _locked_process_edges(edge_key, edges, merge=True):
        async with semaphore:
            workspace = global_config.get("workspace", "")
            namespace = f"{workspace}:GraphDB" if workspace else "GraphDB"
            async with get_storage_keyed_lock(
                f"{edge_key[1]}-{edge_key[2]}-{edge_key[3]}",
                namespace=namespace,
                enable_logging=False,
            ):
                if merge:
                    try:
                        edge_data = await _merge_edges_then_upsert(
                            edge_key[0],
                            edge_key[1],
                            edge_key[2],
                            edge_key[3],
                            edges,
                            knowledge_graph_inst,
                            global_config,
                            pipeline_status,
                            pipeline_status_lock,
                            llm_response_cache,
                        )
                    except Exception as exception:
                        log_message = (
                            f"Merging {edge_key} return an unexpected {exception = }"
                        )
                        logger.error(log_message)
                        return None
                else:
                    edge_data = edges

                if edge_data is None:
                    return None

                edge_type = edge_key[0]
                src_id = edge_key[1]
                tgt_id = edge_key[2]
                edge_id = edge_key[3]

                # le classi mancanti ma utilizzate dalle relazioni sono caricate nel db delle entità
                # tutte le classi hanno la descrizione vuota
                if "need_insert_node" in edge_data and len(edge_data["need_insert_node"]) > 0:
                    if enable_vdb_load_for_extract and entity_vdb is not None:
                        for (need_insert_id, need_insert_data) in edge_data["need_insert_node"]:
                            entity_vdb_contents = dict()
                            if 'label' in need_insert_data:
                                entity_vdb_contents = need_insert_data["label"]
                            entity_vdb_id = compute_mdhash_id(need_insert_id, prefix="ent-")
                            data_for_vdb = {
                                compute_mdhash_id(need_insert_id, prefix="ent-"+lang_tag+"-"): 
                                {
                                    "entity_name": need_insert_id,
                                    "node_type": "entity_type",
                                    "content": content,
                                    "source_id": need_insert_data["source_id"],
                                    "file_path": need_insert_data["file_path"],
                                }
                                for lang_tag, content in entity_vdb_contents.items()
                            }
                            async with get_storage_keyed_lock(
                                [("entity_type", need_insert_id)], namespace=namespace, enable_logging=False,
                            ):
                                await entity_vdb.upsert(data_for_vdb)

                if enable_vdb_load_for_extract and relationships_vdb is not None:
                    if edge_type == "relationship":
                        if "label" in edge_data:
                            labels = dict(edge_data["label"])
                        else:
                            labels = dict()
                        if "description" in edge_data:
                            descriptions = dict(edge_data["description"])
                        else:
                            descriptions = dict()
                        contents = labels
                        contents.update({key: f"{labels[key]}\n{descriptions[key]}" if key in descriptions else labels[key] for key in labels})
                        contents.update({key: descriptions[key] for key in descriptions if key not in labels})
                        if not contents:
                            return None
                        data_for_vdb = {
                            (
                                compute_mdhash_id(src_id + tgt_id + edge_id, prefix="rel-"+lang_tag+"-")
                            ): {"edge_type": edge_type, "src_id": src_id, "tgt_id": tgt_id}
                            |(
                                {"edge_id": edge_id,}
                                if edge_type == "relationship" else {} 
                            )        
                            | {
                                "lang_tag": lang_tag,
                                "content": content,
                                "source_id": edge_data.get("source_id", "unknown_source"),
                                "file_path": edge_data.get("file_path", "unknown_source"),
                            }
                            for lang_tag, content in contents.items()
                        }
                        await relationships_vdb.upsert(data_for_vdb)
                return edge_data

    # Create two tasks queue for entities and edges
    entities_tasks = []
    edges_coros = []

    nodes_to_namespaces = await nodes_without_iri(knowledge_graph_inst)

    if enable_vdb_load_for_extract and entity_vdb is not None:
        # check and delete element of the graph from vdb
        entities_graph = [iri_add_simple_name(ns, node_id) 
            for (node_type, node_id), nss in nodes_to_namespaces.items() 
                for ns in nss 
                    if node_type in ENTITY_FOR_VDB]
        entities_graph_set = set(sorted(entities_graph))
        entities_vdb_storage = await entity_vdb.client_storage
        entities_vdb_data = entities_vdb_storage["data"]
        ent_data_items = defaultdict(list)
        for data in entities_vdb_data:
            ent_data_items[data["entity_name"]].append(data["__id__"])
        entities_vdb_set = set(sorted(list(ent_data_items.keys())))
        entities_vdb_to_delete = list(entities_vdb_set.difference(entities_graph_set))
        ids_to_delete = []
        for e in entities_vdb_to_delete:
            ids_to_delete.extend(ent_data_items[e])
        if ids_to_delete:
            await entity_vdb.delete(ids_to_delete)
            for e in entities_vdb_to_delete:
                await relationships_vdb.delete_entity_relation(e)

        # check and insert node of the graph in vdb
        entities_graph_to_insert = list(entities_graph_set.difference(entities_vdb_set))
        for e in entities_graph_to_insert:
            e_data = await knowledge_graph_inst.get_node(e)
            e_type = e_data["node_type"]
            entities_tasks.append(
                asyncio.create_task(
                    _locked_process_entity_name((e_type, e), e_data, merge=False)
                )
            )

    # Add entity processing tasks
    for entity_name, entities in all_nodes.items():
        node_type = entity_name[0]
        node_id = entity_name[1]
        if node_id not in [t[1] for t in nodes_to_namespaces.keys()]:
            nodes_to_namespaces[(node_type, node_id)] = list(("",))

        node_namespaces = nodes_to_namespaces.get((node_type, node_id))
        if node_namespaces:
            for ns in node_namespaces:
                node_with_iri = iri_add_simple_name(ns, node_id)
                entity_name_with_iri = tuple((node_type, node_with_iri))
                entities_tasks.append(
                    asyncio.create_task(
                        _locked_process_entity_name(entity_name_with_iri, entities)
                    )
                )

    edges_to_namespaces = await edges_without_iri(knowledge_graph_inst)

    if enable_vdb_load_for_extract and relationships_vdb is not None:
        # check and insert edge of the graph in vdb
        edges_graph = [ed for (edge_type, _, _, _), eds in edges_to_namespaces.items() for ed in eds if edge_type == "relationship"]
        edges_graph_set = set(sorted(edges_graph))
        relationships_vdb_storage = await relationships_vdb.client_storage
        relationships_vdb_data = relationships_vdb_storage["data"]
        rel_data_items = defaultdict(list)
        for data in relationships_vdb_data:
            rel_data_items[(data["src_id"], data["tgt_id"], data["edge_id"])].append(data["__id__"])
        relationships_vdb_set = set(sorted(list(rel_data_items.keys())))
        relationships_graph_to_insert = list(edges_graph_set.difference(relationships_vdb_set))
        for r_src, r_tgt, r_id in relationships_graph_to_insert:
            r_data = await knowledge_graph_inst.get_edge(r_src, r_tgt, r_id)
            r_type = r_data["edge_type"]
            edges_coros.append(
                    _locked_process_edges((r_type, r_src, r_tgt, r_id), r_data, merge=False)
            )
 
    # Add edge processing tasks
    for edge_key, edges in all_edges.items():
        edge_type = edge_key[0]
        src_id = edge_key[1]
        tgt_id = edge_key[2]
        edge_id = edge_key[3]

        if (src_id, tgt_id, edge_id) not in [t[1:] for t in edges_to_namespaces.keys()]:
            edge_with_iri_ls = list()
            if ("entity_type", src_id) in nodes_to_namespaces:
                src_id_ns_ls = nodes_to_namespaces[("entity_type", src_id)]
            elif src_id not in [t[1] for t in nodes_to_namespaces.keys()]:
                src_id_ns_ls = list(("",))
                nodes_to_namespaces[("entity_type", src_id)] = list(("",))
            else:
                continue
            if edge_type == "characteristic":
                tgt_type = "characteristic"
            else:
                tgt_type = "entity_type"
            if (tgt_type, tgt_id) in nodes_to_namespaces:
                tgt_id_ns_ls = nodes_to_namespaces[(tgt_type, tgt_id)]
            elif tgt_id not in [t[1] for t in nodes_to_namespaces.keys()]:
                tgt_id_ns_ls = list(("",))
                nodes_to_namespaces[(tgt_type, tgt_id)] = list(("",))
            else:
                continue
            for ns1 in src_id_ns_ls:
                src_id_with_iri = iri_add_simple_name(ns1, src_id)
                for ns2 in tgt_id_ns_ls:
                    tgt_id_with_iri = iri_add_simple_name(ns2, tgt_id)
                    edge_with_iri_ls.append((src_id_with_iri, tgt_id_with_iri, edge_id))
            edges_to_namespaces[(edge_type,src_id, tgt_id, edge_id)] = edge_with_iri_ls

        if (edge_type == "relationship" and
           any((k == edge_id and (i != src_id or j != tgt_id)) for edge_type, i, j, k in edges_to_namespaces.keys())):
            logger.warning(
                f"There is already a relationship with name {edge_id}. Discarded the second."
            )
            continue

        edge_with_namespaces = edges_to_namespaces.get((edge_type, src_id, tgt_id, edge_id))
        if edge_with_namespaces:
            for src_id_iri, tgt_id_iri, edge_id_iri in edge_with_namespaces:
                edge_key_with_iri = tuple((edge_type, src_id_iri, tgt_id_iri, edge_id_iri))
                edges_coros.append(
                        _locked_process_edges(edge_key_with_iri, edges)
                )

    # Execute all tasks in parallel with semaphore control
    if entities_tasks:
        await asyncio.gather(*entities_tasks)
    if edges_coros:
        await asyncio.gather(*edges_coros)

async def nodes_without_iri(
    graphStorage: BaseGraphStorage
) -> dict[tuple[str, str], list[str]]:
    graph = await graphStorage.get_graph()
    nodes_without_iri = dict()
    for node in graph.nodes():
        if "namespace" in graph.nodes[node]:
            namespace = graph.nodes[node]["namespace"]
            node_name = node.removeprefix(namespace)
        else:
            node_name = node
            namespace = ""
        node_type = graph.nodes[node]["node_type"]
        if (node_type,node_name) in nodes_without_iri:
            if namespace not in nodes_without_iri[(node_type,node_name)]:
                nodes_without_iri[(node_type,node_name)].append(namespace)
        else:
            nodes_without_iri[(node_type,node_name)] = list((namespace,))
    return nodes_without_iri

async def edges_without_iri(
    graphStorage: BaseGraphStorage,
) -> dict[tuple[str, str, str, str], list[tuple[str, str, str]]]:
    graph = await graphStorage.get_graph()
    edges_without_iri = dict()
    for u, v, k, d in graph.edges(keys=True, data=True):
        simple_u = u.removeprefix(
            graph.nodes[u]["namespace"] if "namespace" in graph.nodes[u] else ""
        )
        simple_v = v.removeprefix(
            graph.nodes[v]["namespace"] if "namespace" in graph.nodes[v] else ""
        )
        if k != "0" and "namespace" in d:
            simple_k = k.removeprefix(d["namespace"])
        else:
            simple_k = k
        edge_type = graph.edges[(u, v, k)]["edge_type"]
        if (edge_type, simple_u, simple_v, simple_k) in edges_without_iri:
            if (u, v, k) not in edges_without_iri[(edge_type, simple_u, simple_v, simple_k)]:
                edges_without_iri[(edge_type, simple_u, simple_v, simple_k)].append((u, v, k))
        else:
            edges_without_iri[(edge_type, simple_u, simple_v, simple_k)] = list(((u, v, k),))
    return edges_without_iri

async def extract_entity_types(
    chunks: dict[str, TextChunkSchema],
    global_config: dict[str, str],
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
    text_chunks_storage: BaseKVStorage | None = None,
) -> list:
    use_llm_func: callable = global_config["llm_model_func"]
    entity_extract_max_gleaning = global_config["entity_extract_max_gleaning"]

    ordered_chunks = list(chunks.items())
    # add language and example number params to prompt
    language = global_config["addon_params"].get(
        "language", DEFAULT_LANGUAGE
    )
    iri_language = global_config["addon_params"].get(
        "iri_language", DEFAULT_IRI_LANGUAGE
    )
    datatypes = global_config["addon_params"].get(
        "datatypes", PROMPTS["DEFAULT_DATATYPES"]
    )
    example_number = global_config["addon_params"].get("example_number", None)
    iri_format = global_config["addon_params"].get("iri_format", "camelCase")
    if iri_format == "camelCase":
        prompt_examples = PROMPTS["entity_extraction_CC_examples"]
    else:
        prompt_examples = PROMPTS["entity_extraction_SC_examples"]
    if example_number and example_number < len(prompt_examples):
        examples = "\n".join(
            prompt_examples[: int(example_number)]
        )
    else:
        examples = "\n".join(prompt_examples)

    example_context_base = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        datatypes=", ".join(datatypes),
        language=language,
    )
    # add example's format
    examples = examples.format(**example_context_base)

    entity_extract_prompt = PROMPTS["entity_extraction"]
    context_base = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        datatypes=", ".join(datatypes),
#         examples=examples,
        language=language,
        iri_language=iri_language,
        iri_format=iri_format,
    )

    continue_prompt = PROMPTS["entity_continue_extraction"].format(**context_base)
    if_loop_prompt = PROMPTS["entity_if_loop_extraction"]

    processed_chunks = 0
    total_chunks = len(ordered_chunks)

    async def _process_extraction_result(
        result: str, chunk_key: str, file_path: str = "unknown_source"
    ):
        """Process a single extraction result (either initial or gleaning)
        Args:
            result (str): The extraction result to process
            chunk_key (str): The chunk key for source tracking
            file_path (str): The file path for citation
        Returns:
            tuple: (nodes_dict, edges_dict) containing the extracted entities and relationships
        """
        maybe_nodes = defaultdict(list)
        maybe_edges = defaultdict(list)

        # Delete any premises to the result (e.g. "Result: ", "Output: ")
        match = regex.fullmatch(r"^(?:\p{Latin}| )*:(?: |\n)*(.*)", result)
        if match:
            result = match.group(1)

        if not re.search(re.escape(context_base["completion_delimiter"])+"$", result):
            logger.warning(
                "Not all entities extracted from the chunk %s are in completion.",
                chunk_key,
            )

        records = split_string_by_multi_markers(
            result,
            [context_base["record_delimiter"], context_base["completion_delimiter"],"\n"],
        )

        for record in records:
            record = re.search(r"\((.*)\)", record)
            if record is None:
                continue
            record = record.group(1)
            # eventuale correzione del tuple_delimiter nel caso in cui quest'ultimo è valorizzato con "<|>"
            if context_base["tuple_delimiter"] == "<|>":
                record_temp = record
                record, nsub = re.subn(r"(?<!<)\|>|<\|(?!>)", "<|>", record)
                if nsub > 0:
                    logger.warning(
                        f"Updated {nsub} tuple delimiter\n\tfrom: {record_temp}\n\tto: {record}"
                    )
            record_attributes = split_string_by_multi_markers(
                record, [context_base["tuple_delimiter"]]
            )

            if_entities = await _handle_single_entity_type_extraction(
                record_attributes, chunk_key, file_path
            )
            if if_entities is not None:
                maybe_nodes[("entity_type", if_entities["node_id"])].append(if_entities)
                continue

            if_relation = await _handle_single_relationship_extraction(
                record_attributes, chunk_key, file_path, datatypes
            )
            if if_relation is not None:
                maybe_edges[
                    (
                        "relationship",
                        if_relation["src_id"],
                        if_relation["tgt_id"],
                        if_relation["relationship_name"],
                    )
                ].append(if_relation)

            if_relation = await _handle_single_subclass_extraction(
                record_attributes, chunk_key, file_path, datatypes
            )
            if if_relation is not None:
                maybe_edges[
                    (
                        "subclass",
                        if_relation["src_id"],
                        if_relation["tgt_id"],
                        "0",
                    )
                ].append(if_relation)

            (
                if_characteristic,
                if_relation,
            ) = await _handle_single_characteristic_extraction(
                record_attributes, chunk_key, file_path, datatypes
            )
            if if_characteristic is not None:
                maybe_nodes[("characteristic", if_characteristic["node_id"])].append(
                    if_characteristic
                )
                maybe_edges[
                    (
                        "characteristic",
                        if_relation["src_id"],
                        if_relation["tgt_id"],
                        "0",
                    )
                ].append(if_relation)

        return maybe_nodes, maybe_edges

    async def _process_single_content(chunk_key_dp: tuple[str, TextChunkSchema]):
        """ "Prpocess a single chunk
        Args:
            chunk_key_dp (tuple[str, TextChunkSchema]):
                ("chunk-xxxxxx", {"tokens": int, "content": str, "full_doc_id": str, "chunk_order_index": int})
        Returns:
            tuple: (maybe_nodes, maybe_edges) containing extracted entities and relationships
        """
        nonlocal processed_chunks
        chunk_key = chunk_key_dp[0]
        chunk_dp = chunk_key_dp[1]
        content = chunk_dp["content"]
        # Get file path from chunk data or use default
        file_path = chunk_dp.get("file_path", "unknown_source")

        # Create cache keys collector for batch processing
        cache_keys_collector = []

        # Get initial extraction
        hint_prompt = entity_extract_prompt.format(
            **{**context_base, "input_text": content}
        )

        final_result = await use_llm_func_with_cache(
            hint_prompt,
            use_llm_func,
            llm_response_cache=llm_response_cache,
            cache_type="extract",
            chunk_id=chunk_key,
            cache_keys_collector=cache_keys_collector,
        )

        logger.debug(
            f"LLM result:\n{final_result}"
        )

        # Store LLM cache reference in chunk (will be handled by use_llm_func_with_cache)
        history = pack_user_ass_to_openai_messages(hint_prompt, final_result)

        # Process initial extraction
        maybe_nodes, maybe_edges = await _process_extraction_result(
            final_result, chunk_key, file_path
        )

        # Process additional gleaning results
        for now_glean_index in range(entity_extract_max_gleaning):
            glean_result = await use_llm_func_with_cache(
                continue_prompt,
                use_llm_func,
                llm_response_cache=llm_response_cache,
                history_messages=history,
                cache_type="extract",
                chunk_id=chunk_key,
                cache_keys_collector=cache_keys_collector,
            )

            history += pack_user_ass_to_openai_messages(continue_prompt, glean_result)

            # Process gleaning result separately with file path
            glean_nodes, glean_edges = await _process_extraction_result(
                glean_result, chunk_key, file_path
            )

            # Merge results - only add entities and edges with new names
            for entity_name, entities in glean_nodes.items():
                if (
                    entity_name not in maybe_nodes
                ):  # Only accetp entities with new name in gleaning stage
                    maybe_nodes[entity_name].extend(entities)
            for edge_key, edges in glean_edges.items():
                if (
                    edge_key not in maybe_edges
                ):  # Only accetp edges with new name in gleaning stage
                    maybe_edges[edge_key].extend(edges)

            if now_glean_index == entity_extract_max_gleaning - 1:
                break

            if_loop_result: str = await use_llm_func_with_cache(
                if_loop_prompt,
                use_llm_func,
                llm_response_cache=llm_response_cache,
                history_messages=history,
                cache_type="extract",
                cache_keys_collector=cache_keys_collector,
            )
            if_loop_result = if_loop_result.strip().strip('"').strip("'").lower()
            if if_loop_result != "yes":
                break

        # Batch update chunk's llm_cache_list with all collected cache keys
        if cache_keys_collector and text_chunks_storage:
            await update_chunk_cache_list(
                chunk_key,
                text_chunks_storage,
                cache_keys_collector,
                "entity_extraction",
            )

        processed_chunks += 1
        entities_count = len(maybe_nodes)
        relations_count = len(maybe_edges)
        log_message = f"Chunk {processed_chunks} of {total_chunks} extracted {entities_count} Ent + {relations_count} Rel"
        logger.info(log_message)
        if pipeline_status is not None:
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = log_message
                pipeline_status["history_messages"].append(log_message)

        # Return the extracted nodes and edges for centralized processing
        return maybe_nodes, maybe_edges

    # Get max async tasks limit from global_config
    chunk_max_async = global_config.get("llm_model_max_async", 4)
    semaphore = asyncio.Semaphore(chunk_max_async)

    async def _process_with_semaphore(chunk):
        async with semaphore:
            return await _process_single_content(chunk)

    tasks = []
    for c in ordered_chunks:
        task = asyncio.create_task(_process_with_semaphore(c))
        tasks.append(task)

    if not tasks:
        return []

    # Wait for tasks to complete or for the first exception to occur
    # This allows us to cancel remaining tasks if any task fails
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

    # Check if any task raised an exception
    for task in done:
        if task.exception():
            # If a task failed, cancel all pending tasks
            # This prevents unnecessary processing since the parent function will abort anyway
            for pending_task in pending:
                pending_task.cancel()

            # Wait for cancellation to complete
            if pending:
                await asyncio.wait(pending)

            # Re-raise the exception to notify the caller
            raise task.exception()

    # If all tasks completed successfully, collect results
    chunk_results = [task.result() for task in tasks]

    # Return the chunk_results for later processing in merge_nodes_and_edges
    return chunk_results

async def kg_query(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
    system_prompt: str | None = None,
    chunks_vdb: BaseVectorStorage = None,
) -> str | AsyncIterator[str]:

    if query_param.query_pattern == "ontology_query" or query_param.query_pattern == "sparql_query":
        if not query or query is None:
            return PROMPTS["null_response"]
    
        # Handle cache
        args_hash = compute_args_hash(query_param.mode, query)
        cached_response, quantized, min_val, max_val = await handle_cache(
            hashing_kv, args_hash, query, query_param.mode, cache_type="query"
        )
        if cached_response is not None:
            return cached_response
    
        hl_keywords, ll_keywords = await get_keywords_from_query(
            query, query_param, global_config, hashing_kv
        )
    
        logger.debug(f"High-level keywords: {hl_keywords}")
        logger.debug(f"Low-level  keywords: {ll_keywords}")
    
        # Handle empty keywords
        if hl_keywords == [] and ll_keywords == []:
            logger.warning("low_level_keywords and high_level_keywords is empty")
            return PROMPTS["fail_response"]
        if ll_keywords == [] and query_param.mode in ["local", "hybrid"]:
            logger.warning(
                "low_level_keywords is empty, switching from %s mode to global mode",
                query_param.mode,
            )
            query_param.mode = "global"
        if hl_keywords == [] and query_param.mode in ["global", "hybrid"]:
            logger.warning(
                "high_level_keywords is empty, switching from %s mode to local mode",
                query_param.mode,
            )
            query_param.mode = "local"
    
        hl_keywords_str = ", ".join(hl_keywords) if hl_keywords else ""
        ll_keywords_str = "\n".join(ll_keywords) if ll_keywords else ""
    else:
        hl_keywords_str = ""
        ll_keywords_str = ""

    # Build context
    context = await _build_query_context(
        query,
        ll_keywords_str,
        hl_keywords_str,
        knowledge_graph_inst,
        entities_vdb,
        relationships_vdb,
        text_chunks_db,
        query_param,
        global_config,
        chunks_vdb,
    )

    if query_param.only_need_context:
        return context if context is not None else PROMPTS["fail_response"]
    if context is None:
        return PROMPTS["fail_response"]

    # Process conversation history
    history_context = ""
    if query_param.conversation_history:
        history_context = get_conversation_turns(
            query_param.conversation_history, query_param.history_turns
        )

    # Build system prompt
    user_prompt = (
        query_param.user_prompt
        if query_param.user_prompt
        else PROMPTS["DEFAULT_USER_PROMPT"]
    )

    sys_prompt_temp = system_prompt if system_prompt else PROMPTS[query_param.prompt_to_use]
    sys_prompt = sys_prompt_temp.format(
        context_data=context,
        response_type=query_param.response_type,
        history=history_context,
        user_prompt=user_prompt,
        class_list=query_param.classes, # if query_param.prompt_to_use == "rag_RDF_example"
        language=DEFAULT_LANGUAGE, # if query_param.prompt_to_use == "rag_ontology_summary"
    )

    if query_param.only_need_prompt:
        return sys_prompt

    if query_param.model_func:
        use_model_func = query_param.model_func
    else:
        use_model_func = global_config["llm_model_func"]
        # Apply higher priority (5) to query relation LLM function
        use_model_func = partial(use_model_func, _priority=5)

    tokenizer: Tokenizer = global_config["tokenizer"]

    if query_param.query_pattern == "ontology_query" or query_param.query_pattern == "sparql_query":
        len_of_prompts = len(tokenizer.encode(query + sys_prompt))
        logger.debug(
            f"[kg_query] Sending to LLM: {len_of_prompts:,} tokens (Query: {len(tokenizer.encode(query))}, System: {len(tokenizer.encode(sys_prompt))})"
        )

        response = await use_model_func(
            query,
            system_prompt=sys_prompt,
            stream=query_param.stream,
        )
    else:
        len_of_prompts = len(tokenizer.encode(sys_prompt))
        logger.debug(
            f"[kg_query] Sending to LLM: {len_of_prompts} tokens"
        )

        response = await use_model_func(
            sys_prompt,
            stream=query_param.stream,
        )

    if isinstance(response, str) and len(response) > len(sys_prompt):
        response = (
            response.replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )

    if hashing_kv.global_config.get("enable_llm_cache"):
        # Save to cache
        await save_to_cache(
            hashing_kv,
            CacheData(
                args_hash=args_hash,
                content=response,
                prompt=query,
                quantized=quantized,
                min_val=min_val,
                max_val=max_val,
                mode=query_param.mode,
                cache_type="query",
            ),
        )

    return response

async def _build_query_context(
    query: str,
    ll_keywords: str,
    hl_keywords: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    chunks_vdb: BaseVectorStorage = None,
):
    logger.info(f"Process {os.getpid()} building query context...")

    context_type = query_param.query_context_type
    
    if query_param.query_pattern == "ontology_query" or query_param.query_pattern == "sparql_query":
        query_language = await _find_text_language(query, global_config)
        if query_language is None:
            query_language = DEFAULT_LANGUAGE
    else:
        query_language = DEFAULT_LANGUAGE
    query_lang_tag = inv_languages[query_language]
    query_param.query_language = query_lang_tag

    # Collect all chunks from different sources
    all_chunks = []
    entities_context = []
    relations_context = []

    # Store original data for later text chunk retrieval
    original_node_datas = []
    original_edge_datas = []

    # Handle local and global modes
    if query_param.mode == "local":
        (
            entities_context,
            relations_context,
            node_datas,
            use_relations,
        ) = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            query_param,
            global_config,
        )
        original_node_datas = node_datas
        original_edge_datas = use_relations

    elif query_param.mode == "global":
        (
            entities_context,
            relations_context,
            edge_datas,
            use_entities,
        ) = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            query_param,
            global_config,
        )
        original_edge_datas = edge_datas
        original_node_datas = use_entities

    else:  # hybrid or mix mode
        ll_data = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            query_param,
            global_config,
        )
        hl_data = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            query_param,
            global_config,
        )

        (ll_entities_context, ll_relations_context, ll_node_datas, ll_edge_datas) = (
            ll_data
        )
        (hl_entities_context, hl_relations_context, hl_edge_datas, hl_node_datas) = (
            hl_data
        )

        # Get vector chunks first if in mix mode
        if query and query_param.mode == "mix" and chunks_vdb:
            vector_chunks = await _get_vector_context(
                query,
                chunks_vdb,
                query_param,
            )
            all_chunks.extend(vector_chunks)

        original_node_datas = ll_node_datas
        if hl_node_datas:
            ll_entity_names = {e["entity_name"] for e in ll_node_datas}
            for node in hl_node_datas:
                name = node.get("entity_name")
                if name not in ll_entity_names:
                    if "score" not in node:
                        node["score"] = 0.0
                    original_node_datas.append(node)
            original_node_datas = sorted(
                original_node_datas, key=lambda x: (x["score"], x["rank"]), reverse=True
            )
 
        original_edge_datas = hl_edge_datas
        if ll_edge_datas:
            hl_relation_pairs = {(r["src_id"], r["tgt_id"], r["edge_id"]) for r in hl_edge_datas}
            for edge in ll_edge_datas:
                src, tgt, key = edge.get("src_id"), edge.get("tgt_id"), edge.get("edge_id")
                if src is None or tgt is None:
                    src, tgt, key = edge.get("src_tgt", (None, None, None))

                pair = (src, tgt, key)
                if pair != (None, None, None) and pair not in hl_relation_pairs:
                    if "score" not in edge:
                        edge["score"] = 0.0
                    original_edge_datas.append(edge)

            original_edge_datas = sorted(
                original_edge_datas, key=lambda x: (x["score"], x["rank"], x["weight"]), reverse=True
            )

        # Combine entities and relations contexts
        entities_context = process_combine_contexts(
            ll_entities_context, hl_entities_context
        )

        relations_context = process_combine_contexts(
            hl_relations_context, ll_relations_context
        )

    if context_type == "annotation":
        message = f"Initial context: {len(entities_context)} entities, {len(relations_context)} relations, {len(all_chunks)} chunks"
    else:
        message = f"Initial context: {len(original_node_datas)} entities, {len(original_edge_datas)} relations"
    logger.info(message)

    # Unified token control system - Apply precise token limits to entities and relations
    tokenizer = text_chunks_db.global_config.get("tokenizer")
    if tokenizer and context_type == "annotation":
        # Get new token limits from query_param (with fallback to global_config)
        max_entity_tokens = getattr(
            query_param,
            "max_entity_tokens",
            text_chunks_db.global_config.get(
                "max_entity_tokens", DEFAULT_MAX_ENTITY_TOKENS
            ),
        )
        max_relation_tokens = getattr(
            query_param,
            "max_relation_tokens",
            text_chunks_db.global_config.get(
                "max_relation_tokens", DEFAULT_MAX_RELATION_TOKENS
            ),
        )
        max_total_tokens = getattr(
            query_param,
            "max_total_tokens",
            text_chunks_db.global_config.get(
                "max_total_tokens", DEFAULT_MAX_TOTAL_TOKENS
            ),
        )

        # Truncate entities based on complete JSON serialization
        if entities_context:
            original_entity_count = len(entities_context)

            # Process entities context to replace GRAPH_FIELD_SEP with : in file_path fields
            for entity in entities_context:
                if "file_path" in entity and entity["file_path"]:
                    entity["file_path"] = entity["file_path"].replace(
                        GRAPH_FIELD_SEP, ";"
                    )

            entities_context = truncate_list_by_token_size(
                entities_context,
                key=lambda x: json.dumps(x, ensure_ascii=False),
                max_token_size=max_entity_tokens,
                tokenizer=tokenizer,
            )
            if len(entities_context) < original_entity_count:
                logger.debug(
                    f"Truncated entities: {original_entity_count} -> {len(entities_context)} (entity max tokens: {max_entity_tokens})"
                )

        # Truncate relations based on complete JSON serialization
        if relations_context:
            original_relation_count = len(relations_context)

            # Process relations context to replace GRAPH_FIELD_SEP with : in file_path fields
            for relation in relations_context:
                if "file_path" in relation and relation["file_path"]:
                    relation["file_path"] = relation["file_path"].replace(
                        GRAPH_FIELD_SEP, ";"
                    )

            relations_context = truncate_list_by_token_size(
                relations_context,
                key=lambda x: json.dumps(x, ensure_ascii=False),
                max_token_size=max_relation_tokens,
                tokenizer=tokenizer,
            )
            if len(relations_context) < original_relation_count:
                logger.debug(
                    f"Truncated relations: {original_relation_count} -> {len(relations_context)} (relation max tokens: {max_relation_tokens})"
                )

    # After truncation, get text chunks based on final entities and relations
#     logger.info("Getting text chunks based on truncated entities and relations...")

    # Create filtered data based on truncated context DA MIGLORARE 
    if context_type == "annotation":
        final_node_datas = []
        if entities_context and original_node_datas:
            final_entity_names = {e["entity"] for e in entities_context}
            seen_nodes = set()
            for node in original_node_datas:
                name = node.get("entity_name")
                if name in final_entity_names and name not in seen_nodes:
                    final_node_datas.append(node)
                    seen_nodes.add(name)
        final_edge_datas = []
        if relations_context and original_edge_datas:
            final_relation_pairs = {(r["entity1"], r["entity2"], r["relationship"]) for r in relations_context}
            seen_edges = set()
            for edge in original_edge_datas:
                src, tgt, key = edge.get("src_id"), edge.get("tgt_id"), edge.get("edge_id")
                if src is None or tgt is None:
                    src, tgt, key = edge.get("src_tgt", (None, None, None))
    
                pair = (src, tgt, key)
                if pair in final_relation_pairs and pair not in seen_edges:
                    final_edge_datas.append(edge)
                    seen_edges.add(pair)

    else:
        final_node_datas = original_node_datas
        final_edge_datas = original_edge_datas

    original_attributes_datas, attributes_context = await _find_most_related_attributes_from_entities(
        final_node_datas,
        query_param,
        knowledge_graph_inst,
    )

    if context_type == "annotation":
        message = f"Final context: {len(entities_context)} entities, {len(relations_context)} relations, {len(attributes_context)} attributes, {len(all_chunks)} chunks"
    else:
        message = f"Final context: {len(final_node_datas)} entities, {len(final_edge_datas)} relations, {len(original_attributes_datas)} attributes"
    logger.info(message)

    # Definisco il contesto con l'ontologia ridotta
    if context_type == "owl":
        if not final_node_datas and not final_edge_datas:
            return None
    
        relations_list = [(
            e["src_id"],
            e["tgt_id"],
            e["edge_id"],
            {
                'edge_type': e['edge_type'],
                'frozen': e['frozen'],
                'weight': e['weight']
            }|(
            {
                'namespace': e['namespace'],
                'label': e.get('label',{}),
                'description': e.get('description',{}),
            } if e['edge_type'] == "relationship" else {})
            ) 
            for e in final_edge_datas]
        
        attribute_edges_list = []
        attribute_nodes_list = []
        for e in original_attributes_datas:
            attribute_edges_list.append((
                e["src_tgt"][0],
                e["src_tgt"][1],
                "0",
                {
                    'edge_type': e['edge_type'],
                    'frozen': e['frozen'], 
                })
            )
            attribute_node_data = await knowledge_graph_inst.get_node(e["src_tgt"][1])
            attribute_nodes_list.append(
                {
                    'node_id': e["src_tgt"][1],
                    'node_type': e['edge_type'], 
                    'frozen': e['frozen'], 
                    'namespace': attribute_node_data.get('namespace',""),
                    'label': attribute_node_data.get('label',{}),
                    'description': attribute_node_data.get('description',{}),
                    'datatype': attribute_node_data['datatype']}
            )

        # creo il grafo di contesto a partire dagli archi: relazioni e attributi
        graph = await knowledge_graph_inst.get_graph()
        graph_metadata = graph.graph["metadata"]
        # VERIFICARE
        metadatas_excluded = [
            "annotations",
            "annotationProperties"
        ]
        for metadata in metadatas_excluded:
            graph_metadata.pop(metadata, None)
        context_graph = nx.MultiDiGraph(relations_list+attribute_edges_list, metadata=graph_metadata)
        
        # integro il grafo con le informazioni su i nodi delle entità
        context_graph.add_nodes_from(
            list(
                (
                    n["node_id"],
                    dict(
                        node_type=n["node_type"],
                        namespace=n["namespace"],
                        label=n.get("label",{}),
                        description=n.get("description",{}),
                        frozen=n["frozen"]
                    )
                ) for n in final_node_datas
            )
        )
    
        # integro il grafo con le informazioni su i nodi degli attributi
        context_graph.add_nodes_from(
            list(
                (
                    a["node_id"],
                    dict(
                        node_type=a["node_type"],
                        datatype=a["datatype"],
                        namespace=a["namespace"],
                        label=a.get("label",{}),
                        description=a.get("description",{}),
                        frozen=a["frozen"]
                    )
                ) for a in attribute_nodes_list
            )
        )

        context_rdfGraph = write_gscape(context_graph)
        context_ontology = rdf_graph_to_owl(context_rdfGraph)
        context_ontology_text = serialize_owl(context_ontology, "turtle")

        # elimino l'ultimo commento "Generated by ..."
        pos = context_ontology_text.rfind("###")
        if pos > -1 and context_ontology_text[pos+5:pos+5+12] == "Generated by":
            context_ontology_text = context_ontology_text[:pos-1]
        result = f"""
```ttl
{context_ontology_text}
```"""
        return result

    ontology_context = dict()
    # Get ontology context description (only for summary)
    if query_param.query_pattern == "summary_query":
        graph = await knowledge_graph_inst.get_graph()
        graph_annotations = graph.graph["metadata"]["annotations"]
        annotations = defaultdict(list)
        temp_graph_annotations = copy.deepcopy(graph_annotations)
        # costruisco un dict in cui le key sono le property e value è la lista dei possibili assegnazioni
        for item in temp_graph_annotations:
            annotations[item.pop("property")].append(item)
        if RDFS_LABEL in annotations:
            label = next((ann["value"] for ann in annotations[RDFS_LABEL] if ann['language'] == query_lang_tag), None)
            if label is None:
                label = next((ann["value"] for ann in annotations[RDFS_LABEL] if ann['language'] == "en"), None)
        elif DCT_TITLE in annotations:
            label = next((ann["value"] for ann in annotations[DCT_TITLE] if ann['language'] == query_lang_tag), None)
            if label is None:
                label = next((ann["value"] for ann in annotations[DCT_TITLE] if ann['language'] == "en"), None)
        else:
            label = None
        if RDFS_COMMENT in annotations:
            description = next((ann["value"] for ann in annotations[RDFS_COMMENT] if ann['language'] == query_lang_tag), None)
            if description is None:
                description = next((ann["value"] for ann in annotations[RDFS_COMMENT] if ann['language'] == "en"), None)
        elif DCT_DESCRIPTION in annotations:
            description = next((ann["value"] for ann in annotations[DCT_DESCRIPTION] if ann['language'] == query_lang_tag), None)
            if description is None:
                description = next((ann["value"] for ann in annotations[DCT_DESCRIPTION] if ann['language'] == "en"), None)
        else:
            description = None

        ontology_context = ontology_context | (
            {"identifier" : annotations[DCT_IDENTIFIER][0]["value"]} if DCT_IDENTIFIER in annotations else {}) | (
            {"label" : label} if label is not None else {}) | (
            {"description" : description} if description is not None else {})

    # Get text chunks based on final filtered data
    text_chunk_tasks = []

    if final_node_datas:
        text_chunk_tasks.append(
            _find_most_related_text_unit_from_entities(
                final_node_datas,
                query_param,
                text_chunks_db,
                knowledge_graph_inst,
            )
        )

    if final_edge_datas:
        text_chunk_tasks.append(
            _find_related_text_unit_from_relationships(
                final_edge_datas,
                query_param,
                text_chunks_db,
            )
        )

    # Execute text chunk retrieval in parallel
    if text_chunk_tasks:
        text_chunk_results = await asyncio.gather(*text_chunk_tasks)
        for chunks in text_chunk_results:
            if chunks:
                all_chunks.extend(chunks)

    # Apply token processing to chunks if tokenizer is available
    text_units_context = []
    if tokenizer and all_chunks:
        # Calculate dynamic token limit for text chunks
        entities_str = json.dumps(entities_context, ensure_ascii=False)
        relations_str = json.dumps(relations_context, ensure_ascii=False)
        attributes_str = json.dumps(attributes_context, ensure_ascii=False)
        if ontology_context:
            ontology_str = json.dumps(ontology_context, ensure_ascii=False)
            kg_context_template = """-----Ontology(KG)-----

```json
{ontology_str}
```

"""
        else:
            kg_context_template = ""

        # Calculate base context tokens (entities + relations + template)
        kg_context_template = kg_context_template + """-----Entities(KG)-----

```json
{entities_str}
```

-----Attributes(KG)-----

```json
{attributes_str}
```

-----Relationships(KG)-----

```json
{relations_str}
```

-----Document Chunks(DC)-----

```json
[]
```
"""
        kg_context = kg_context_template.format(
            entities_str=entities_str, relations_str=relations_str, attributes_str=attributes_str,ontology_str=ontology_str
        )
        kg_context_tokens = len(tokenizer.encode(kg_context))

        # Calculate actual system prompt overhead dynamically
        # 1. Calculate conversation history tokens
        history_context = ""
        if query_param.conversation_history:
            history_context = get_conversation_turns(
                query_param.conversation_history, query_param.history_turns
            )
        history_tokens = (
            len(tokenizer.encode(history_context)) if history_context else 0
        )

        # 2. Calculate system prompt template tokens (excluding context_data)
        user_prompt = query_param.user_prompt if query_param.user_prompt else ""
        response_type = (
            query_param.response_type
            if query_param.response_type
            else "Multiple Paragraphs"
        )

        # Get the system prompt template from PROMPTS
        sys_prompt_template = text_chunks_db.global_config.get(
            "system_prompt_template", PROMPTS["rag_response"]
        )

        # Create a sample system prompt with placeholders filled (excluding context_data)
        sample_sys_prompt = sys_prompt_template.format(
            history=history_context,
            context_data="",  # Empty for overhead calculation
            response_type=response_type,
            user_prompt=user_prompt,
        )
        sys_prompt_template_tokens = len(tokenizer.encode(sample_sys_prompt))

        # Total system prompt overhead = template + query tokens
        query_tokens = len(tokenizer.encode(query))
        sys_prompt_overhead = sys_prompt_template_tokens + query_tokens

        buffer_tokens = 100  # Safety buffer as requested

        # Calculate available tokens for text chunks
        used_tokens = kg_context_tokens + sys_prompt_overhead + buffer_tokens
        available_chunk_tokens = max_total_tokens - used_tokens

        logger.debug(
            f"Token allocation - Total: {max_total_tokens}, History: {history_tokens}, SysPrompt: {sys_prompt_overhead}, KG: {kg_context_tokens}, Buffer: {buffer_tokens}, Available for chunks: {available_chunk_tokens}"
        )

        logger.debug(f"all chunks: {all_chunks}")

        # Re-process chunks with dynamic token limit
        if all_chunks:
            # Create a temporary query_param copy with adjusted chunk token limit
            temp_chunks = [
                {"content": chunk["content"], "file_path": chunk["file_path"]}
                for chunk in all_chunks
            ]

            logger.debug(f"temp chunks: {temp_chunks}")

            # Apply token truncation to chunks using the dynamic limit
            truncated_chunks = await process_chunks_unified(
                query=query,
                chunks=temp_chunks,
                query_param=query_param,
                global_config=text_chunks_db.global_config,
                source_type="mixed",
                chunk_token_limit=available_chunk_tokens,  # Pass dynamic limit
            )

            # Rebuild text_units_context with truncated chunks
            for i, chunk in enumerate(truncated_chunks):
                text_units_context.append(
                    {
                        "id": i + 1,
                        "content": chunk["content"],
                        "file_path": chunk.get("file_path", "unknown_source"),
                    }
                )

            logger.debug(
                f"Re-truncated chunks for dynamic token limit: {len(temp_chunks)} -> {len(text_units_context)} (chunk available tokens: {available_chunk_tokens})"
            )

    logger.info(
        f"Final context: {len(entities_context)} entities, {len(relations_context)} relations, {len(text_units_context)} chunks"
    )

    # not necessary to use LLM to generate a response
    if not entities_context and not relations_context:
        return None

    entities_str = json.dumps(entities_context, ensure_ascii=False)
    relations_str = json.dumps(relations_context, ensure_ascii=False)
    attributes_str = json.dumps(attributes_context, ensure_ascii=False)
    text_units_str = json.dumps(text_units_context, ensure_ascii=False)
    if ontology_context:
        ontology_str = json.dumps(ontology_context, ensure_ascii=False)
        result = f"""-----Ontology(KG)-----

```json
{ontology_str}
```

"""
    else:
        result = ""

    result = result + f"""-----Entities(KG)-----

```json
{entities_str}
```

-----Attributes(KG)-----

```json
{attributes_str}
```

-----Relationships(KG)-----

```json
{relations_str}
```

-----Document Chunks(DC)-----

```json
{text_units_str}
```
"""
    return result

async def _get_node_data(
    keywords: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
):
    if query_param.query_pattern == "ontology_query" or query_param.query_pattern == "sparql_query":
        # get similar entities
        logger.info(
            f"Query nodes: {repr(keywords)}, top_k: {query_param.top_k}, cosine: {entities_vdb.cosine_better_than_threshold}"
        )
    
        try:
            results = await entities_vdb.query(
                keywords, top_k=query_param.top_k, ids=query_param.ids, filter_lambda=lambda x: x["node_type"] == "entity_type"
            )
        # se il filtro non seleziona nulla (indice vuoto) c'è un problema in nano vectordb
        except IndexError:
            results = []
        
        logger.debug(f"entity extraction: {[r['entity_name'] for r in results]}")
    
        if not len(results):
            return "", "", [], []
    
        # rerank delle entità
        if query_param.enable_rerank and keywords and results:
            rerank_top_k = query_param.chunk_top_k or len(results)
            results = await apply_rerank_if_enabled(
                query=keywords,
                retrieved_docs=results,
                global_config=global_config,
                enable_rerank=query_param.enable_rerank,
                top_k=rerank_top_k,
            )
            logger.debug(f"Rerank: {len(results)} entities (source: 'entity')")
    
        # Apply top_k limiting if specified
        if query_param.top_k is not None and query_param.top_k > 0:
            if len(results) > query_param.top_k:
                results = results[: query_param.top_k]
                logger.debug(
                    f"Entity top-k limiting: kept {len(results)} entities (top_k={query_param.top_k})"
                )
    
        # Extract all entity IDs from your results list
        results_dict = {r["entity_name"]:r for r in results}
        node_ids = list(results_dict.keys())
    elif query_param.query_pattern == "instantiation_query":
        results_dict = dict()
        node_ids = list(query_param.classes)

    else: # query_param.query_pattern == "summary_query"
        results_dict = dict()
        nx_graph = await knowledge_graph_inst.get_graph()
        nx_view = nx.subgraph_view(nx_graph, filter_edge=lambda u, v, k: nx_graph[u][v][k].get('edge_type') in ['relationship', 'subclass'])
        central_nodes = nx.degree_centrality(nx_view)
        # Se presenti, recupero dal grafo le key class dichiarate nell'ontologia
        nx_graph_annotations = nx_graph.graph["metadata"]["annotations"]
        key_classes = [ann["value"] for ann in nx_graph_annotations if ann['property'] == ADMS_HASKEYCLASS]
        # inserisco/aggiorno le key class al valore di centralità massimo 1.0
        for kc in key_classes:
            central_nodes[kc] = 1.0
        desc_central_nodes = {k: v for k, v in sorted(central_nodes.items(), key=lambda item: item[1],reverse=True)}
        if query_param.top_k is not None and query_param.top_k > 0:
            central_nodes_limit = query_param.top_k
        else:
            central_nodes_limit = DEFAULT_TOP_K
        node_ids = [k for i, (k, v) in enumerate(desc_central_nodes.items()) if i<central_nodes_limit and v>0]

    graph = await knowledge_graph_inst.get_graph()
    ancestor_nodes = set(node_ids)
    ancestor_edges = set()
    for n in node_ids:
        ns, es = _find_ancestor(graph,n)
        ancestor_nodes = ancestor_nodes.union(set(ns))
        ancestor_edges = ancestor_edges.union(set(es))

    node_ids = list(ancestor_nodes)

    # Call the batch node retrieval and degree functions concurrently.
    nodes_dict, degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_nodes_batch(node_ids),
        knowledge_graph_inst.node_degree_edge_filter_batch(node_ids,"edge_type","relationship"),
    )

    # Now, if you need the node data and degree in order:
    node_datas = [nodes_dict.get(nid) for nid in node_ids]
    node_degrees = [degrees_dict.get(nid, 0) for nid in node_ids]
    node_results = [results_dict.get(nid, {}) for nid in node_ids]

    if not all([n is not None for n in node_datas]):
        logger.warning("Some nodes are missing, maybe the storage is damaged")

    node_datas = [
        {
            **n,
            "entity_name": k.get("entity_name", node_id),
            "rank": d,
            "score": k.get("rerank_score",0.0),
            "created_at": k.get("created_at","UNKNOWN"),
        }
        for k, n, d, node_id in zip(node_results, node_datas, node_degrees, node_ids)
        if n is not None
    ]

    use_relations = await _find_most_related_edges_from_entities(
        node_datas,
        query_param,
        knowledge_graph_inst,
        list(ancestor_edges),
    )
    # semplifico i dati ottenuti
    short_use_relations = [{"src_id": e["src_tgt"][0],"tgt_id": e["src_tgt"][1],"edge_id": e["src_tgt"][2]}
        for e in use_relations
    ]
    # identifico i nodi terminali ovvero i nodi collegati dalle relazioni individuate
    terminal_nodes = await _find_most_related_entities_from_relationships(
        short_use_relations,
        query_param,
        knowledge_graph_inst,
    )
    
    # considero solo i nuovi nodi
    present_nodes = [n["entity_name"] for n in node_datas]
#     terminal_nodes = [dict(n, score=0.0)
    terminal_nodes = [n for n in terminal_nodes if n["entity_name"] not in present_nodes]
    
    # aggiungo i nodi terminali ai nodi originali prima di ordinarli
    node_datas = sorted(
        node_datas+terminal_nodes, key=lambda x: (x["score"], x["rank"]), reverse=True
    )
    
    logger.info(
        f"Local query: {len(node_datas)} entites, {len(use_relations)} relations"
    )

    query_lang_tag = query_param.query_language

    # build prompt
    entities_context = []
    for i, n in enumerate(node_datas):
        created_at = n.get("created_at", "UNKNOWN")
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from node data
        file_path = n.get("file_path", "unknown_source")

        labels = n.get("label",{})
        descriptions = n.get("description",{})
        annotation = list()
        for j, item in enumerate([labels, descriptions]):
            if item:
                if query_lang_tag in item:
                    elem = item[query_lang_tag]
                else:
                    # in assenza, viene preso il primo valore disponibile
                    elem = list(item.values())[0]
            else:
                if j == 0:
                    entity_name_without_iri = n["entity_name"][len(get_namespace_from_iri(n["entity_name"])) :]
                    elem = simple_name_to_label(entity_name_without_iri)
                else:
                    elem = "UNKNOWN"
            annotation.append(elem)

        entities_context.append(
            {
                "id": i + 1,
                "entity": n["entity_name"],
                "type": n.get("node_type", "UNKNOWN"),
                "label": annotation[0],
                "description": annotation[1],
#                 "created_at": created_at,
#                 "file_path": file_path,
            }
        )

    relations_context = []
    i = 0
    for e in use_relations:
        created_at = e.get("created_at", "UNKNOWN")
        # Convert timestamp to readable format
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from edge data
        file_path = e.get("file_path", "unknown_source")

        labels = e.get("label",{})
        descriptions = e.get("description",{})
        annotation = list()
        for j, item in enumerate([labels, descriptions]):
            if item:
                if query_lang_tag in item:
                    elem = item[query_lang_tag]
                else:
                    # in assenza, viene preso il primo valore disponibile
                    elem = list(item.values())[0]
            else:
                if j == 0 and e.get("edge_type")=="relationship":
                    edge_without_iri = e["src_tgt"][2][len(get_namespace_from_iri(e["src_tgt"][2])) :]
                    elem = simple_name_to_label(edge_without_iri)
                elif j == 1 and e.get("edge_type")=="subclass":
                    entity1_without_iri = e["src_tgt"][0][len(get_namespace_from_iri(e["src_tgt"][0])) :]
                    entity2_without_iri = e["src_tgt"][1][len(get_namespace_from_iri(e["src_tgt"][1])) :]
                    if query_lang_tag == "it":
                        elem = f"{entity1_without_iri} è sottoclasse di {entity2_without_iri}"
                    else:
                        elem = f"{entity1_without_iri} is a subclass of {entity2_without_iri}"
                else:
                    elem = "UNKNOWN"
            annotation.append(elem)

        edge_type = e.get("edge_type", "UNKNOWN")

        i += 1
        relations_context.append(
            {
                "id": i,
                "entity1": e["src_tgt"][0],
                "entity2": e["src_tgt"][1],
                "relationship": e["src_tgt"][2] if edge_type=="relationship" 
                    else RDFS_SUBCLASS if edge_type=="subclass" 
                    else "UNKNOWN",
                "type": edge_type,
                "label": annotation[0],
                "description": annotation[1],
#                 "created_at": created_at,
#                 "file_path": file_path,
            }
        )

    return entities_context, relations_context, node_datas, use_relations

async def _find_most_related_text_unit_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    text_chunks_db: BaseKVStorage,
    knowledge_graph_inst: BaseGraphStorage,
):
    logger.debug(f"Searching text chunks for {len(node_datas)} entities")

    text_units = [
        split_string_by_multi_markers(dp["source_id"], [GRAPH_FIELD_SEP])[
            : text_chunks_db.global_config.get(
                "related_chunk_number", DEFAULT_RELATED_CHUNK_NUMBER
            )
        ]
        for dp in node_datas
        if dp.get("source_id") is not None
    ]

    node_names = [dp["entity_name"] for dp in node_datas]
    batch_edges_dict = await knowledge_graph_inst.get_nodes_edges_batch(node_names)
    # Build the edges list in the same order as node_datas.
    edges = [batch_edges_dict.get(name, []) for name in node_names]

    all_one_hop_nodes = set()
    for this_edges in edges:
        if not this_edges:
            continue
        all_one_hop_nodes.update([e[1] for e in this_edges])

    all_one_hop_nodes = list(all_one_hop_nodes)

    # Batch retrieve one-hop node data using get_nodes_batch
    all_one_hop_nodes_data_dict = await knowledge_graph_inst.get_nodes_batch(
        all_one_hop_nodes
    )
    all_one_hop_nodes_data = [
        all_one_hop_nodes_data_dict.get(e) for e in all_one_hop_nodes
    ]

    # Add null check for node data
    all_one_hop_text_units_lookup = {
        k: set(split_string_by_multi_markers(v["source_id"], [GRAPH_FIELD_SEP]))
        for k, v in zip(all_one_hop_nodes, all_one_hop_nodes_data)
        if v is not None and "source_id" in v  # Add source_id check
    }

    all_text_units_lookup = {}
    tasks = []

    for index, (this_text_units, this_edges) in enumerate(zip(text_units, edges)):
        for c_id in this_text_units:
            if c_id not in all_text_units_lookup:
                all_text_units_lookup[c_id] = index
                tasks.append((c_id, index, this_edges))

    # Process in batches tasks at a time to avoid overwhelming resources
    batch_size = 5
    results = []

    for i in range(0, len(tasks), batch_size):
        batch_tasks = tasks[i : i + batch_size]
        batch_results = await asyncio.gather(
            *[text_chunks_db.get_by_id(c_id) for c_id, _, _ in batch_tasks]
        )
        results.extend(batch_results)

    for (c_id, index, this_edges), data in zip(tasks, results):
        all_text_units_lookup[c_id] = {
            "data": data,
            "order": index,
            "relation_counts": 0,
        }

        if this_edges:
            for e in this_edges:
                if (
                    e[1] in all_one_hop_text_units_lookup
                    and c_id in all_one_hop_text_units_lookup[e[1]]
                ):
                    all_text_units_lookup[c_id]["relation_counts"] += 1

    # Filter out None values and ensure data has content
    all_text_units = [
        {"id": k, **v}
        for k, v in all_text_units_lookup.items()
        if v is not None and v.get("data") is not None and "content" in v["data"]
    ]

    if not all_text_units:
        logger.warning("No valid text units found")
        return []

    # Sort by relation counts and order, but don't truncate
    all_text_units = sorted(
        all_text_units, key=lambda x: (x["order"], -x["relation_counts"])
    )

    logger.debug(f"Found {len(all_text_units)} entity-related chunks")

    # Add source type marking and return chunk data
    result_chunks = []
    for t in all_text_units:
        chunk_data = t["data"].copy()
        chunk_data["source_type"] = "entity"
        result_chunks.append(chunk_data)

    return result_chunks

async def _find_most_related_edges_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    knowledge_graph_inst: BaseGraphStorage,
    init_edges: list[tuple(str, str, str)] | None = None
):
    if init_edges is None:
        init_edges = list()

    node_names = [dp["entity_name"] for dp in node_datas]
    # prendo solo le relazioni
    batch_edges_dict = await knowledge_graph_inst.get_nodes_filter_edges_batch(node_names, edge_type="relationship")

    all_edges = init_edges
    seen = set(init_edges)

    # togliere, non ha senso perché gli archi sono orientati
    for node_name in node_names:
        this_edges = batch_edges_dict.get(node_name, [])
        for e in this_edges:
            sorted_edge = e
            if sorted_edge not in seen: 
                seen.add(sorted_edge)
                all_edges.append(sorted_edge)

    # Prepare edge pairs in two forms:
    # For the batch edge properties function, use dicts.
    edge_pairs_dicts = [{"src": e[0], "tgt": e[1], "key": e[2]} for e in all_edges]
    # For edge degrees, use tuples.
    edge_pairs_tuples = list(all_edges)  # all_edges is already a list of tuples

    # Call the batched functions concurrently.
    edge_data_dict, edge_degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_edges_batch(edge_pairs_dicts),
        knowledge_graph_inst.edge_degrees_filter_batch(edge_pairs_tuples,"edge_type","relationship"),
    )

    # Reconstruct edge_datas list in the same order as the deduplicated results.
    all_edges_data = []
    for pair in all_edges:
        edge_props = edge_data_dict.get(pair)
        if edge_props is not None:
            if "weight" not in edge_props:
                edge_props["weight"] = 0.0

            combined = {
                "src_tgt": pair,
                "rank": edge_degrees_dict.get(pair, 0),
                "score": 0.0,
                **edge_props,
            }
            all_edges_data.append(combined)

    all_edges_data = sorted(
        all_edges_data, key=lambda x: (x["rank"], x["weight"]), reverse=True
    )

    return all_edges_data

async def _find_most_related_attributes_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    knowledge_graph_inst: BaseGraphStorage,
):
    node_names = [dp["entity_name"] for dp in node_datas]
    batch_edges_dict = await knowledge_graph_inst.get_nodes_filter_edges_batch(node_names, edge_type="characteristic")

    # lista delle tuple delle caratteristiche di tutti i nodi in node_names
    all_edges = [e for node_name in node_names for e in batch_edges_dict.get(node_name, [])]

    edge_pairs_dicts = [{"src": e[0], "tgt": e[1], "key": e[2]} for e in all_edges]

    edge_data_dict = await knowledge_graph_inst.get_edges_batch(edge_pairs_dicts)

    # Reconstruct edge_datas list in the same order as the deduplicated results.
    all_edges_data = []
    for pair in all_edges:
        edge_props = edge_data_dict.get(pair)
        if edge_props is not None:
            combined = {
                "src_tgt": pair,
                **edge_props,
            }
            all_edges_data.append(combined)

    query_lang_tag = query_param.query_language

    attributes_context = []
    for i, e in enumerate(all_edges_data):
        attribute_node_data = await knowledge_graph_inst.get_node(e["src_tgt"][1])

        labels = attribute_node_data.get("label",{})
        descriptions = attribute_node_data.get("description",{})
        annotation = list()
        for j, item in enumerate([labels, descriptions]):
            if item:
                if query_lang_tag in item:
                    elem = item[query_lang_tag]
                else:
                    # in assenza, viene preso il primo valore disponibile
                    elem = list(item.values())[0]
            else:
                if j == 0:
                    attribute_name_without_iri = e["src_tgt"][1][len(get_namespace_from_iri(e["src_tgt"][1])) :]
                    elem = simple_name_to_label(attribute_name_without_iri)
                else:
                    elem = "UNKNOWN"
            annotation.append(elem)

        attributes_context.append(
            {
                "id": i + 1,
                "entity": e["src_tgt"][0],
                "attribute": e["src_tgt"][1],
                "type": attribute_node_data["datatype"],
                "label": annotation[0],
                "description": annotation[1],
            }
        )

    return all_edges_data, attributes_context

async def _get_edge_data(
    keywords,
    knowledge_graph_inst: BaseGraphStorage,
    relationships_vdb: BaseVectorStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
):
    if query_param.query_pattern == "ontology_query" or query_param.query_pattern == "sparql_query":
        logger.info(
            f"Query edges: {repr(keywords)}, top_k: {query_param.top_k}, cosine: {relationships_vdb.cosine_better_than_threshold}"
        )
    
        try:
            results = await relationships_vdb.query(
                keywords, top_k=query_param.top_k, ids=query_param.ids, filter_lambda=lambda x: x["edge_type"] == "relationship"
            )
        # se il filtro non seleziona nulla (indice vuoto) c'è un problema in nano vectordb
        except IndexError:
            results = []
    else:
        results = []

    logger.debug(f"relationship extraction: {results}")
    
    if not len(results):
        return "", "", [], []

    # rerank delle relazioni
    if query_param.enable_rerank and keywords and results:
        rerank_top_k = query_param.chunk_top_k or len(results)
        results = await apply_rerank_if_enabled(
            query=keywords,
            retrieved_docs=results,
            global_config=global_config,
            enable_rerank=query_param.enable_rerank,
            top_k=rerank_top_k,
        )
        logger.debug(f"Rerank: {len(results)} relationships (source: 'relationship')")

    # Apply top_k limiting if specified
    if query_param.top_k is not None and query_param.top_k > 0:
        if len(results) > query_param.top_k:
            results = results[: query_param.top_k]
            logger.debug(
                f"Relationship top-k limiting: kept {len(results)} relationships (top_k={query_param.top_k})"
            )

    graph = await knowledge_graph_inst.get_graph()
    ancestor_nodes = set()
    ancestor_edges = set()
    for r in results:
        src_ns, src_es = _find_ancestor(graph,r["src_id"])
        tgt_ns, tgt_es = _find_ancestor(graph,r["tgt_id"])
        ancestor_nodes = ancestor_nodes.union(set(src_ns),set(tgt_ns))
        ancestor_edges = ancestor_edges.union(set(src_es),set(tgt_es))

    # Prepare edge pairs in two forms:
    # l'aggiunta degli archi di sottoclasse non genera duplicati perchè in results ci sono solo archi di relazioni
    # For the batch edge properties function, use dicts.
    edge_pairs_dicts = [{"src": r["src_id"], "tgt": r["tgt_id"], "key": r["edge_id"]} for r in results]
    edge_pairs_dicts.extend([{"src": src_id, "tgt": tgt_id, "key": edge_id} for (src_id, tgt_id, edge_id) in ancestor_edges])
    # For edge degrees, use tuples.
    edge_pairs_tuples = [(r["src_id"], r["tgt_id"], r["edge_id"]) for r in results]
    edge_pairs_tuples.extend(list(ancestor_edges))

    # Call the batched functions concurrently.
    edge_data_dict, edge_degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_edges_batch(edge_pairs_dicts),
        knowledge_graph_inst.edge_degrees_filter_batch(edge_pairs_tuples,"edge_type","relationship"),
    )

    # Reconstruct edge_datas list in the same order as results.
    edge_datas = []
    for k in results:
        pair = (k["src_id"], k["tgt_id"], k["edge_id"])
        edge_props = edge_data_dict.get(pair)
        if edge_props is not None:
            if "weight" not in edge_props:
                edge_props["weight"] = 0.0

            # Use edge degree from the batch as rank.
            combined = {
                "src_id": k["src_id"],
                "tgt_id": k["tgt_id"],
                "edge_id": k["edge_id"],
                "rank": edge_degrees_dict.get(pair, k.get("rank", 0)),
                "score": k.get("rerank_score", 0.0),
                "created_at": k.get("created_at", None),
                **edge_props,
            }
            edge_datas.append(combined)

    for (src_id, tgt_id, edge_id) in ancestor_edges:
        pair = (src_id, tgt_id, edge_id)
        edge_props = edge_data_dict.get(pair)
        if edge_props is not None:
            if "weight" not in edge_props:
                edge_props["weight"] = 0.0

            # Use edge degree from the batch as rank.
            combined = {
                "src_id": src_id,
                "tgt_id": tgt_id,
                "edge_id": edge_id,
                "rank": edge_degrees_dict.get(pair, k.get("rank", 0)),
                "score": 0.0,
                "created_at": "UNKNOWN",
                **edge_props,
            }
            edge_datas.append(combined)

    edge_datas = sorted(
        edge_datas, key=lambda x: (x["score"], x["rank"], x["weight"]), reverse=True
    )

    use_entities = await _find_most_related_entities_from_relationships(
        edge_datas,
        query_param,
        knowledge_graph_inst,
        list(ancestor_nodes),
    )

    logger.info(
        f"Global query: {len(use_entities)} entites, {len(edge_datas)} relations"
    )

    query_lang_tag = query_param.query_language

    relations_context = []
    for i, e in enumerate(edge_datas):
        created_at = e.get("created_at", "UNKNOWN")
        # Convert timestamp to readable format
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from edge data
        file_path = e.get("file_path", "unknown_source")

        labels = e.get("label",{})
        descriptions = e.get("description",{})
        annotation = list()
        for j, item in enumerate([labels, descriptions]):
            if item:
                if query_lang_tag in item:
                    elem = item[query_lang_tag]
                else:
                    # in assenza, viene preso il primo valore disponibile
                    elem = list(item.values())[0]
            else:
                if j == 0 and e.get("edge_type")=="relationship":
                    edge_without_iri = e["edge_id"][len(get_namespace_from_iri(e["edge_id"])) :]
                    elem = simple_name_to_label(edge_without_iri)
                elif j == 1 and e.get("edge_type")=="subclass":
                    entity1_without_iri = e["src_id"][len(get_namespace_from_iri(e["src_id"])) :]
                    entity2_without_iri = e["tgt_id"][len(get_namespace_from_iri(e["tgt_id"])) :]
                    if query_lang_tag == "it":
                        elem = f"{entity1_without_iri} è sottoclasse di {entity2_without_iri}"
                    else:
                        elem = f"{entity1_without_iri} is a subclass of {entity2_without_iri}"
                else:
                    elem = "UNKNOWN"
            annotation.append(elem)

        edge_type = e.get("edge_type", "UNKNOWN")

        relations_context.append(
            {
                "id": i + 1,
                "entity1": e["src_id"],
                "entity2": e["tgt_id"],
                "relationship": e["edge_id"] if edge_type=="relationship" 
                    else RDFS_SUBCLASS if edge_type=="subclass" 
                    else "UNKNOWN",
                "type": edge_type,
                "label": annotation[0],
                "description": annotation[1],
#                 "created_at": created_at,
#                 "file_path": file_path,
            }
        )

    entities_context = []
    for i, n in enumerate(use_entities):
        created_at = n.get("created_at", "UNKNOWN")
        # Convert timestamp to readable format
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from node data
        file_path = n.get("file_path", "unknown_source")

        labels = n.get("label",{})
        descriptions = n.get("description",{})
        annotation = list()
        for j, item in enumerate([labels, descriptions]):
            if item:
                if query_lang_tag in item:
                    elem = item[query_lang_tag]
                else:
                    # in assenza, viene preso il primo valore disponibile
                    elem = list(item.values())[0]
            else:
                if j == 0:
                    entity_name_without_iri = n["entity_name"][len(get_namespace_from_iri(n["entity_name"])) :]
                    elem = simple_name_to_label(entity_name_without_iri)
                else:
                    elem = "UNKNOWN"
            annotation.append(elem)

        entities_context.append(
            {
                "id": i + 1,
                "entity": n["entity_name"],
                "type": n.get("node_type", "UNKNOWN"),
                "label": annotation[0],
                "description": annotation[1],
#                 "created_at": created_at,
#                 "file_path": file_path,
            }
        )

    # Return original data for later text chunk retrieval
    return entities_context, relations_context, edge_datas, use_entities

async def _find_most_related_entities_from_relationships(
    edge_datas: list[dict],
    query_param: QueryParam,
    knowledge_graph_inst: BaseGraphStorage,
    init_nodes: list[tuple(str, str, str)] | None = None
):
    if init_nodes is None:
        init_nodes = list()

    entity_names = init_nodes
    seen = set(init_nodes)

    for e in edge_datas:
        if e["src_id"] not in seen:
            entity_names.append(e["src_id"])
            seen.add(e["src_id"])
        if e["tgt_id"] not in seen:
            entity_names.append(e["tgt_id"])
            seen.add(e["tgt_id"])

    # Batch approach: Retrieve nodes and their degrees concurrently with one query each.
    nodes_dict, degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_nodes_batch(entity_names),
        knowledge_graph_inst.node_degree_edge_filter_batch(entity_names,"edge_type","relationship"),
    )

    # Rebuild the list in the same order as entity_names
    node_datas = []
    for entity_name in entity_names:
        node = nodes_dict.get(entity_name)
        degree = degrees_dict.get(entity_name, 0)
        if node is None:
            logger.warning(f"Node '{entity_name}' not found in batch retrieval.")
            continue
        # Combine the node data with the entity name and computed degree (as rank)
        combined = {**node, "entity_name": entity_name, "rank": degree, "score": 0.0}
        node_datas.append(combined)

    node_datas = sorted(
        node_datas, key=lambda x: (x["rank"]), reverse=True
    )

    return node_datas

async def _find_related_text_unit_from_relationships(
    edge_datas: list[dict],
    query_param: QueryParam,
    text_chunks_db: BaseKVStorage,
):
    logger.debug(f"Searching text chunks for {len(edge_datas)} relationships")

    text_units = [
        split_string_by_multi_markers(dp["source_id"], [GRAPH_FIELD_SEP])[
            : text_chunks_db.global_config.get(
                "related_chunk_number", DEFAULT_RELATED_CHUNK_NUMBER
            )
        ]
        for dp in edge_datas
        if dp.get("source_id") is not None
    ]
    all_text_units_lookup = {}

    async def fetch_chunk_data(c_id, index):
        if c_id not in all_text_units_lookup:
            chunk_data = await text_chunks_db.get_by_id(c_id)
            # Only store valid data
            if chunk_data is not None and "content" in chunk_data:
                all_text_units_lookup[c_id] = {
                    "data": chunk_data,
                    "order": index,
                }

    tasks = []
    for index, unit_list in enumerate(text_units):
        for c_id in unit_list:
            tasks.append(fetch_chunk_data(c_id, index))

    await asyncio.gather(*tasks)

    if not all_text_units_lookup:
        logger.warning("No valid text chunks found")
        return []

    all_text_units = [{"id": k, **v} for k, v in all_text_units_lookup.items()]
    all_text_units = sorted(all_text_units, key=lambda x: x["order"])

    # Ensure all text chunks have content
    valid_text_units = [
        t for t in all_text_units if t["data"] is not None and "content" in t["data"]
    ]

    if not valid_text_units:
        logger.warning("No valid text chunks after filtering")
        return []

    logger.debug(f"Found {len(valid_text_units)} relationship-related chunks")

    # Add source type marking and return chunk data
    result_chunks = []
    for t in valid_text_units:
        chunk_data = t["data"].copy()
        chunk_data["source_type"] = "relationship"
        result_chunks.append(chunk_data)

    return result_chunks

def _find_ancestor(graph: nx.MultiDiGraph, node: str) -> tuple(list[str], list[tuple(str, str, str)]):
    
    father_nodes = []
    father_edges = []
    for node,v,k,e in graph.out_edges(node,keys=True,data=True):
        if node != v and e['edge_type'] == 'subclass':
            father_nodes.append(v)
            father_edges.append((node,v,k))
        else:
            continue

    ancestor_nodes = father_nodes
    ancestor_edges = father_edges
    while father_nodes:
        new_father_nodes = set()
        new_father_edges = set()
        for n in father_nodes:
            for n,v,k,e in graph.out_edges(n,keys=True,data=True):
                if n != v and e['edge_type'] == 'subclass':
                    new_father_nodes.add(v)
                    new_father_edges.add((n,v,k))
                else:
                    continue
        real_new_father_nodes = new_father_nodes - set(ancestor_nodes)
        father_nodes = list(real_new_father_nodes)
        ancestor_nodes.extend(father_nodes)
        ancestor_edges.extend(list(new_father_edges - set(ancestor_edges)))

    return ancestor_nodes, ancestor_edges

async def _find_text_language(
        text: str,
        global_config: dict[str, str],
    ) -> str | None:
    if not text:
        return None

    use_llm_func = global_config["llm_model_func"]
#     use_llm_func: callable = self.llm_model_func
    use_llm_func = partial(use_llm_func, _priority=8)
    prompt_template = PROMPTS["find_doc_language"]
    context_base = dict(
        language=DEFAULT_LANGUAGE,
        text=text,
    )
    use_prompt = prompt_template.format(**context_base)

     # Use LLM function with cache (higher priority for language retrive)
    result = await use_llm_func_with_cache(
        use_prompt,
        use_llm_func,
#                 llm_response_cache= self.llm_response_cache,
#                 cache_type="extract",
    )
    pattern = "|".join(list(inv_languages.keys()))
    match = re.search(pattern,result.lower())
    if match:
        return match.group(0)
    else:
        return None

