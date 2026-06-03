# coding: utf-8

import textwrap

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from ai_assistant.gscape import DEFAULT_NAMESPACE
from ai_assistant.server.models.initialize_vector_db_request import InitializeVectorDBRequest
from ai_assistant.server.models.namespace import Namespace
from ai_assistant.server.models.put_ontology_draft_ai_request import PutOntologyDraftAIRequest
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.server.models.rdf_graph_metadata import RDFGraphMetadata


def test_post_rag_initialize_vdb(app: FastAPI, headers: dict, monkeypatch):
    with open("tests/resources/transfmkt.gscape") as ingraph:
        graph = RDFGraph.from_json(ingraph.read())
        req = InitializeVectorDBRequest(baseGraph=graph, highlightedGraph=graph)
        name = "transfmkt"
        with TestClient(app) as client:
            # async def insert_kg_stub(*_args, **_kwargs): return True
            # monkeypatch.setattr('ai_assistant.rag.OntoRAG.ainsert_kg_from_gscape', insert_kg_stub)
            response = client.post(
                f"/ai/rag/{name}/vectorDB/initialize",
                headers=headers,
                content=req.to_json(),
            )
            assert response.status_code == 200


@pytest.mark.skip
def test_put_rag_ontology_draft(app: FastAPI, headers: dict):
    """Test case for put_ontology_draft_ai

    Ask for AI support in ontology design.
    """
    put_ontology_draft_ai_request = PutOntologyDraftAIRequest(
        text=textwrap.dedent("""
        Il contratto individuale di lavoro è il contratto mediante il quale il lavoratore si obbliga a prestare
        la propria attività lavorativa alle dipendenze e sotto la direzione e la vigilanza del datore di lavoro,
        in cambio di una controprestazione ossia la retribuzione (art. 2099 cod.civ.).
        La prestazione dell’opera del lavoratore può essere sia di carattere manuale, sia di carattere intellettuale.
        Ai fini della validità del contratto è necessario che vi sia la compresenza dei seguenti elementi essenziali:
        - il consenso delle parti
        - la causa
        - l’oggetto
        - la forma.
        Il contratto di lavoro deve contenere nell’oggetto l’attività della prestazione lavorativa che il lavoratore
        deve effettuare, purché ovviamente sia lecita, possibile e determinata ovvero determinabile, attraverso
        il riferimento alla categoria contrattuale di appartenenza.
        La durata del contratto può essere a tempo indeterminato oppure a tempo determinato: in quest’ultimo caso,
        la durata dell’intero rapporto lavorativo non può essere superiore a tre anni dalla stipulazione del primo
        contratto di lavoro. Il lavoratore, nello svolgimento del rapporto lavorativo è tenuto ad usare la diligenza richiesta
        dalla prestazione dovuta, osservare le disposizioni per l’esecuzione e per la disciplina del lavoro impartite
        dal datore di lavoro; è altresì tenuto all’obbligo di fedeltà, ossia non deve trattare affari, per conto
        proprio o di terzi che siano in concorrenza con il datore di lavoro, ovvero divulgare notizie attinenti
        l’organizzazione dell’azienda al fine di recare ad essa pregiudizio. (artt. 2104 e 2105 c.c.).
        Le modifiche contrattuali possono essere stabilite solo dalla legge, dai contratti collettivi o dalla volontà
        di entrambe le Parti.
        """),
        currentRdfGraph=RDFGraph(
            creator="ai_assistant",
            modelType="ontology",
            diagrams=[],
            entities=[],
            metadata=RDFGraphMetadata(
                iri=DEFAULT_NAMESPACE,
                namespaces=[Namespace(value=DEFAULT_NAMESPACE, prefixes=["AI:"])],
            ),
        )
    )

    name = "test"

    with TestClient(app) as client:
        response = client.put(
            f"/ai/rag/ontologyDraft/{name}",
            headers=headers,
            content=put_ontology_draft_ai_request.to_json(),
        )
        assert response.status_code == 200
