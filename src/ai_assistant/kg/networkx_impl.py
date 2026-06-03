import os
from dataclasses import dataclass
from typing import Union, Tuple, Optional


from ai_assistant.utils import logger

import pipmaster as pm

if not pm.is_installed("networkx"):
    pm.install("networkx")

import networkx as nx

from lightrag.kg.networkx_impl import NetworkXStorage as LightRAGNetworkXStorage

@dataclass
class NetworkXStorage(LightRAGNetworkXStorage):
    def __post_init__(self):
        self._storage_lock = None
        self.storage_updated = None
        language = self.global_config["addon_params"]["language"]
        self._graph = nx.MultiDiGraph(
            config=dict({"language": language}),
        )
        logger.info("Created new empty graph")

    async def set_graph(self, graph: nx.MultiDiGraph) -> bool:
        # Acquire lock and update internal graph
        async with self._storage_lock:
            try:
                # Update the graph
                self._graph = graph
                if self._graph.number_of_nodes() > 0:
                    logger.info(
                        f"Initialized graph with {self._graph.number_of_nodes()} nodes, {self._graph.number_of_edges()} edges"
                    )
                return True  # Return success
            except Exception as e:
                logger.error(f"Error update graph for {self.namespace}: {e}")
                return False  # Return error

    #         return True

    async def get_graph(self) -> nx.MultiDiGraph:
        # Acquire lock and return internal graph
        async with self._storage_lock:
            return self._graph

    async def _get_graph(self):
        """Check if the storage should be reloaded"""
        # Acquire lock to prevent concurrent read and write
        async with self._storage_lock:
            return self._graph

    async def node_degree_edge_filter_batch(
        self, node_ids: list[str], edge_data: str, data_value: str
    ) -> dict[str, int]:
        result = {}
        for node_id in node_ids:
            degree = await self.node_degree_edge_filter(node_id,edge_data,data_value)
            result[node_id] = degree
        return result

    async def node_degree_edge_filter(
        self, node_id: str, edge_data: str, data_value: str
    ) -> int:
        graph = await self._get_graph()       
        return sum([
            sum(e[2]==data_value for e in graph.out_edges(node_id, data=edge_data)),
            sum(e[2]==data_value for e in graph.in_edges(node_id, data=edge_data))
        ])

    async def has_edge(
        self, source_node_id: str, target_node_id: str, edge_id: Optional[str] = None
    ) -> bool:
        graph = await self._get_graph()
        if edge_id:
            check = graph.has_edge(source_node_id, target_node_id, edge_id)
        else:
            check = graph.has_edge(source_node_id, target_node_id)
        return check

    async def get_edge(
        self, source_node_id: str, target_node_id: str, edge_id: Optional[str] = None
    ) -> dict[str, str] | None:
        graph = await self._get_graph()
        if edge_id:
            edge_data = graph.edges.get((source_node_id, target_node_id, edge_id))
        else:
            edges_data = graph.get_edge_data(source_node_id, target_node_id)
            if edges_data is not None:
                if len(edges_data) == 1: # se c'è un solo arco tra i due nodi restituisco quello
                    edge_data = list(edges_data.values())[0]
                else: # altrimenti restituisco l'arco con peso maggiore (a parità il primo)
                    edge_id = max(edges_data, key=lambda k: edges_data[k].get("weight",0.0))
                    logger.warning(f"More edges from {source_node_id} to {target_node_id}, taken the one with greater 'weight'")
                    return edges_data[edge_id]
            else:
                edge_data = None
        return edge_data

    async def get_edges_batch(
        self, pairs: list[dict[str, str]]
    ) -> dict[tuple[str, str, str], dict]:
        """Get edges as a batch using UNWIND

        The implementation fetches edges one by one.
        """
        result = {}
        for pair in pairs:
            src_id = pair["src"]
            tgt_id = pair["tgt"]
            if "key" in pair:
                edge_id = pair["key"]
                edge = await self.get_edge(src_id, tgt_id, edge_id)
            else:
                edge = await self.get_edge(src_id, tgt_id)
                if edge is not None:
                    edge_id = edge["edge_id"]
            if edge is not None:
                result[(src_id, tgt_id, edge_id)] = edge
        return result

    async def get_node_edges(
        self, source_node_id: str
    ) -> list[tuple[str, str, str]] | None:
        """
            Get all edges (out + in) of the node as list of 3-ples (src, tgt, key)
        """
        graph = await self._get_graph()
        if graph.has_node(source_node_id):
            all_edges = list()
            out_edges = graph.out_edges(source_node_id, keys=True)
            all_edges.extend(out_edges)
            in_edges = graph.in_edges(source_node_id, keys=True)
            all_edges.extend(in_edges)
            return all_edges
#            return list(graph.edges(source_node_id, keys=True))
        return None

    async def get_node_filter_edges(
        self, 
        source_node_id: str, 
        edge_direction: str = "all", 
        edge_type=None, 
    ) -> list[tuple[str, str, str]] | None:
        """
            Get the edges (all or out or in) of the node with edge type as list of 3-ples (src, tgt, key)
        """
        graph = await self._get_graph()
        if graph.has_node(source_node_id):
            all_edges = list()
            if edge_direction == "out" or edge_direction == "all":
                if edge_type is not None:
                    filter_edges = [(e[0],e[1],e[2]) for e in graph.out_edges(source_node_id, data="edge_type", keys=True) if e[3]==edge_type]
                    all_edges.extend(filter_edges)
                else:
                    all_edges.extend(graph.out_edges(source_node_id, keys=True))
            if edge_direction == "in" or edge_direction == "all":
                if edge_type is not None:
                    filter_edges = [(e[0],e[1],e[2]) for e in graph.in_edges(source_node_id, data="edge_type", keys=True) if e[3]==edge_type]
                    all_edges.extend(filter_edges)
                else:
                    all_edges.extend(graph.in_edges(source_node_id, keys=True))
            return all_edges
        return None

    async def get_nodes_edges_batch(
        self, node_ids: list[str]
    ) -> dict[str, list[tuple[str, str, str]]]:
        """Get nodes edges as a batch using UNWIND

        The implementation fetches node edges one by one.
        """
        result = {}
        for node_id in node_ids:
            edges = await self.get_node_edges(node_id)
            result[node_id] = edges if edges is not None else []
        return result

    async def get_nodes_filter_edges_batch(
        self, 
        node_ids: list[str],
        edge_direction: str = "all", 
        edge_type=None,         
    ) -> dict[str, list[tuple[str, str, str]]]:
        """Get nodes edges filtered as a batch using UNWIND

        The implementation fetches node edges one by one.
        """
        result = {}
        for node_id in node_ids:
            edges = await self.get_node_filter_edges(node_id, edge_direction, edge_type=edge_type)
            result[node_id] = edges if edges is not None else []
        return result

    async def edge_degrees_batch(
        self, edge_pairs: list[tuple[str, str, str]]
    ) -> dict[tuple[str, str, str], int]:
        result = {}
        for src_id, tgt_id, edge_id in edge_pairs:
            degree = await self.edge_degree(src_id, tgt_id)
            result[(src_id, tgt_id, edge_id)] = degree
        return result

    async def edge_degrees_filter_batch(
        self, edge_pairs: list[tuple[str, str, str]], edge_data: str, data_value: str
    ) -> dict[tuple[str, str, str], int]:
        result = {}
        for src_id, tgt_id, edge_id in edge_pairs:
            degree = await self.edge_degree_filter(src_id, tgt_id, edge_data, data_value)
            result[(src_id, tgt_id, edge_id)] = degree
        return result

    async def edge_degree_filter(
        self, src_id: str, tgt_id: str, edge_data: str, data_value: str
    ) -> int:
        graph = await self._get_graph()
        src_degree = await self.node_degree_edge_filter(src_id, edge_data, data_value) if graph.has_node(src_id) else 0
        tgt_degree = await self.node_degree_edge_filter(tgt_id, edge_data, data_value) if graph.has_node(tgt_id) else 0
        return src_degree + tgt_degree

    async def upsert_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_id: Optional[str] = None,
        edge_data: Optional[dict[str, str]] = None,
    ) -> None:
        graph = await self._get_graph()
        if edge_id:
            graph.add_edge(source_node_id, target_node_id, key=edge_id, **edge_data)
        else:
            graph.add_edge(source_node_id, target_node_id, **edge_data)

    async def remove_edges(
        self, edges: list[Union[Tuple[str, str], Tuple[str, str, str]]]
    ):
        """Delete multiple edges

        Args:
            edges: List of edges to be deleted, each edge is a (source, target, id) tuple
                   or (source, target) and, in this case, it will delete all edge from
                   source to target
        """
        graph = await self._get_graph()
        for edge in edges:
            if edge[2]:
                ks = [edge[2]]
            else:
                ks = list(graph[edge[0]][edge[1]])
            for k in ks:
                if graph.has_edge(edge[0], edge[1], k):
                    graph.remove_edge(edge[0], edge[1], key=k)

    async def index_done_callback(self) -> bool:
        return True

    async def drop(self) -> dict[str, str]:
        """Drop all graph data from storage and clean up resources

        This method will:
        1. Reset the graph to an empty state
        2. Update flags to notify other processes

        Returns:
            dict[str, str]: Operation status and message
            - On success: {"status": "success", "message": "data dropped"}
            - On failure: {"status": "error", "message": "<error details>"}
        """
        try:
            async with self._storage_lock:
                self._graph = nx.MultiDiGraph()
                logger.info(f"Process {os.getpid()} drop graph {self.namespace}")
            return {"status": "success", "message": "data dropped"}
        except Exception as e:
            logger.error(f"Error dropping graph {self.namespace}: {e}")
            return {"status": "error", "message": str(e)}
