# coding: utf-8

import json
from typing import Any, Optional

from networkx import MultiDiGraph

from collections import defaultdict

from .jvm.java import *
from .jvm.owlapi import *
from .server.models.diagram import Diagram
from .server.models.edge import Edge
from .server.models.element_ai_generated import ElementAiGenerated
from .server.models.function_properties_enum import FunctionPropertiesEnum
from .server.models.grapholscape_annotation import GrapholscapeAnnotation as Annotation
from .server.models.grapholscape_entity import GrapholscapeEntity
from .server.models.namespace import Namespace
from .server.models.node import Node
from .server.models.rdf_graph import RDFGraph
from .server.models.rdf_graph_config import RDFGraphConfig
from .server.models.rdf_graph_metadata import RDFGraphMetadata
from .server.models.types_enum import TypesEnum
from .utils import (
    get_namespace_from_iri,
    inv_languages,
    DEFAULT_LANGUAGE,
    iri_add_simple_name,
)

DEFAULT_NAMESPACE = "http://obdasystems.com/ai/"
RDFS_SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
RDFS_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_LITERAL = "http://www.w3.org/2000/01/rdf-schema#Literal"
XML_STRING = "http://www.w3.org/2001/XMLSchema#string"
XML_DECIMAL = "http://www.w3.org/2001/XMLSchema#decimal"
XML_BOOLEAN = "http://www.w3.org/2001/XMLSchema#boolean"
XML_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"

DATATYPES = dict(
    string = XML_STRING,
    number = XML_DECIMAL,
    boolean = XML_BOOLEAN,
    datetime = XML_DATETIME,
)

def load_gscape(rdf_graph: RDFGraph) -> MultiDiGraph:
    default_language = inv_languages[DEFAULT_LANGUAGE]
    language = default_language
    creator = "ai_assistant"
    if rdf_graph.config is not None:
        language = rdf_graph.config.to_dict().get("language", default_language)
    if rdf_graph.creator is not None:
        creator = rdf_graph.creator
    G = MultiDiGraph(
        metadata=rdf_graph.metadata.to_dict(),
        config=dict({"language": language}),
        creator=creator
    )

    def get_gscape_annotations(
        entity: GrapholscapeEntity,
        elem_data: dict[str, str],
    ) -> dict[str, str]:

        descriptions = defaultdict(list)
        labels = defaultdict(list)
        
        if entity.annotations:
            for annotation in entity.annotations:
                if annotation.var_property == RDFS_COMMENT:
#                     if annotation.language not in descriptions:
#                         descriptions[annotation.language] = list()
                    description_text = annotation.value or annotation.lexical_form
                    descriptions[annotation.language].append(description_text)
                if annotation.var_property == RDFS_LABEL:
#                     if annotation.language not in labels:
#                         labels[annotation.language] = list()
                    label_text = annotation.value or annotation.lexical_form
                    labels[annotation.language].append(label_text)
        
            elem_data["description"] = {k:v[0] for k,v in descriptions.items()}     
            elem_data["label"] = {k:v[0] for k,v in labels.items()}     
        
        return elem_data

    entities_dict = {x.full_iri: x for x in rdf_graph.entities}

    for diagram in rdf_graph.diagrams:
        nodes_dict: dict[str, Any] = {x.id: x for x in diagram.nodes}
        hierarchies: dict[str, Any] = {}
        for node in diagram.nodes:
            if node.iri is not None:
                namespace = get_namespace_from_iri(node.iri)
                if node.type == TypesEnum.CLASS:
                    node_type = "entity_type"
                elif node.type == TypesEnum.DATA_PROPERTY:
                    node_type = "characteristic"
                else:
                    node_type = node.type
                n: any = {
                    "node_id": node.iri,  # 'Datore_di_Lavoro'
                    "namespace": namespace,  # 'http://obda.com/'
                    "node_type": node_type,
                    "frozen": True if node.ai_generated is None else False,
                }
                entity = entities_dict[node.iri]
                if "datatype" in entity.to_dict():
                    n["datatype"] = entity.datatype
                else:
                    if node.type == TypesEnum.DATA_PROPERTY:
                        n["datatype"] = RDFS_LITERAL

                n = get_gscape_annotations(entity, n)

                G.add_node(node.iri, **n)

        for edge in diagram.edges:
            source_node = nodes_dict.get(edge.source_id)
            target_node = nodes_dict.get(edge.target_id)
            namespace = None
            if source_node and target_node:
                # G.add_edge(source_node.iri, target_node.iri)
                if edge.iri:
                    namespace = get_namespace_from_iri(edge.iri)

                if edge.type == TypesEnum.OBJECT_PROPERTY:
                    edge_type = "relationship"
                    edge_id = edge.iri
                elif edge.type == TypesEnum.INCLUSION:
                    edge_type = "subclass"
                    edge_id = "0"
                elif edge.type == TypesEnum.ATTRIBUTE_EDGE:
                    edge_type = "characteristic"
                    edge_id = "0"
                elif (edge.type == TypesEnum.COMPLETE_UNION or
                      edge.type == TypesEnum.DISJOINT_UNION or
                      edge.type == TypesEnum.COMPLETE_DISJOINT_UNION or
                      edge.type == TypesEnum.UNION):
                    hierarchy = hierarchies.get(source_node.id)
                    if hierarchy is None:
                        hierarchy = {
                            "type": source_node.type,
                            "inputs": [],
                            "superclasses": [],
                        }
                        hierarchies[source_node.id] = hierarchy

                    hierarchy["superclasses"].append({
                        "class_iri": target_node.iri,
                        "edge_type": edge.type,
                    })
                    continue

                elif edge.type == TypesEnum.INPUT:
                    hierarchy = hierarchies.get(target_node.id)
                    if hierarchy is None:
                        hierarchy = {
                            "type": target_node.type,
                            "inputs": [],
                            "superclasses": [],
                        }
                        hierarchies[target_node.id] = hierarchy

                    hierarchy["inputs"].append(source_node.iri)
                    continue

                else:
                    continue

                edge_data = {
                    "src_id": source_node.iri,
                    "tgt_id": target_node.iri,
                    "edge_id": edge_id,
                    "edge_type": edge_type,
                    "frozen": True if edge.ai_generated is None else False,
                }

                if namespace is not None:
                    edge_data["namespace"] = namespace

                if edge.iri is not None:
                    entity = entities_dict[edge.iri]
                    edge_data = get_gscape_annotations(entity, edge_data)

                G.add_edge(
                    source_node.iri,
                    target_node.iri,
                    edge_id,
                    **edge_data,
                )

        for hierarchy in hierarchies.values():
            for superclass_edge in hierarchy.get("superclasses", []):
                superclass_node = G.nodes[superclass_edge["class_iri"]]
                if "hierarchies" not in superclass_node:
                    superclass_node["hierarchies"] = [hierarchy]
                else:
                    superclass_node["hierarchies"].append(hierarchy)

                for input_class_iri in hierarchy.get("inputs", []):
                    G.add_edge(input_class_iri, superclass_edge["class_iri"], "0", **{
                        "src_id": input_class_iri,
                        "tgt_id": superclass_edge["class_iri"],
                        "edge_id": "0",
                        "edge_type": "subclass",
                        "frozen": True,
                        "from_hierarchy": True,
                    })
    return G


def write_gscape(nx_graph: MultiDiGraph, file_name: str | None = None) -> RDFGraph:
    """
    :rtype: object
    """
    diagram = Diagram(
        **{
            "id": 0,
            "name": "aiGenerated",
            "edges": [],
            "nodes": [],
        }
    )
    rdf_graph = RDFGraph(
        creator="ai_assistant",
        modelType="ontology",
        diagrams=[diagram],
        entities=[],
        metadata=RDFGraphMetadata(namespaces=[]),
        config=RDFGraphConfig(
            language="en"
        ),
        selectedDiagramId=0,
    )

    if "metadata" in nx_graph.graph:
        rdf_graph.metadata = rdf_graph.metadata.from_dict(nx_graph.graph["metadata"])
    rdf_graph.metadata.namespaces.append(Namespace(value=DEFAULT_NAMESPACE, prefixes=["AI"]))
    ontology_namespace = rdf_graph.metadata.iri if rdf_graph.metadata.iri is not None else DEFAULT_NAMESPACE
    if "config" in nx_graph.graph:
        rdf_graph.config = rdf_graph.config.from_dict(nx_graph.graph["config"])
    if "creator" in nx_graph.graph:
        rdf_graph.creator = nx_graph.graph["creator"]

    added_nodes = {}
    added_entities = dict()

    def add_node(node_id, node_data):
        gscape_node = get_gscape_node(node_id, node_data)
        if gscape_node is None:
            return
        if not added_nodes.get(gscape_node.iri):
            diagram.nodes.append(gscape_node)
            added_nodes[gscape_node.iri] = gscape_node
            if not added_entities.get(gscape_node.iri):
                if node_data["node_type"] == "characteristic":
                    if "datatype" not in node_data:
                        node_data["datatype"] = RDFS_LITERAL
                entity = get_gscape_entity(gscape_node.iri, node_data)
                rdf_graph.entities.append(entity)
                added_entities[gscape_node.iri] = entity
        else:
            gscape_node = added_nodes.get(gscape_node.iri)
        return gscape_node

    def get_gscape_node(node_id: str, nx_node) -> Node:
        iri = node_id
        aiGenerated = None
        if "namespace" not in nx_node:
            aiGenerated = ElementAiGenerated(isNew=True, chunkId="")
            iri = iri_add_simple_name(ontology_namespace, node_id)
        if nx_node["node_type"] == "entity_type":
            node_type = TypesEnum.CLASS
        elif nx_node["node_type"] == "characteristic":
            node_type = TypesEnum.DATA_PROPERTY
        elif "node_type" in nx_node and nx_node["node_type"] is not None:
            node_type = nx_node["node_type"]
        else:
            return

        return Node(
            id="n" + str(len(added_nodes)),
            # originalId=node_id,  # shouldn't be necessary
            type=node_type,
            iri=iri,
            diagramId=0,
            aiGenerated=aiGenerated,
        )

    def add_edge(source_id, target_id, edge_id, edge_data):
        if edge_data.get("from_hierarchy"):  # skip inclusion edges generated from hierarchy nodes
            return
        if edge_data["edge_type"] == "relationship":
            edge_type = TypesEnum.OBJECT_PROPERTY
        elif edge_data["edge_type"] == "characteristic":
            edge_type = TypesEnum.ATTRIBUTE_EDGE
        elif edge_data["edge_type"] == "subclass":
            edge_type = TypesEnum.INCLUSION
        elif "edge_type" in edge_data and edge_data["edge_type"] is not None:
            edge_type = edge_data["edge_type"]
        else:
            return

        iri = None
        aiGenerated = None
        if edge_id != "0":
            iri = edge_id
            if "namespace" not in edge_data:
                aiGenerated = ElementAiGenerated(isNew=True, chunkId="")
                iri = iri_add_simple_name(ontology_namespace, edge_id)
                displayedName = edge_id
            else:
                displayedName = edge_id.removeprefix(edge_data["namespace"])

        gscape_edge = Edge(
            id=f"e{len(rdf_graph.diagrams[0].edges)}",
            originalId=f"e{len(rdf_graph.diagrams[0].edges)}",  # shouldn't be necessary
            iri=iri,
            displayedName=displayedName if edge_id != "0" else None,
            diagramId=0,
            type=edge_type,
            sourceId=source_id,
            targetId=target_id,
            aiGenerated=aiGenerated,
        )
        diagram.edges.append(gscape_edge)
        entity = added_entities.get(gscape_edge.iri)
        if not entity and gscape_edge.iri is not None:
            entity = get_gscape_entity(gscape_edge.iri, edge_data)
            rdf_graph.entities.append(entity)
            added_entities[gscape_edge.iri] = entity

    def add_hierarchy(hierarchy):
        hierarchy_node_id = "n" + str(len(rdf_graph.diagrams[0].nodes))

        diagram.nodes.append(Node(
            id=hierarchy_node_id,
            type=hierarchy["type"],
            diagramId=0,
            aiGenerated=None,
        ))

        for input_class_iri in hierarchy["inputs"]:
            input_class = added_nodes.get(input_class_iri)
            add_edge(input_class.id, hierarchy_node_id, "0", {"edge_type": TypesEnum.INPUT})
        for superclass_edge in hierarchy["superclasses"]:
            superclass_node = added_nodes.get(superclass_edge["class_iri"])
            add_edge(hierarchy_node_id, superclass_node.id, "0", {"edge_type": superclass_edge["edge_type"]})

    def get_gscape_entity(iri, elem_data) -> GrapholscapeEntity:
        annotations = []
        if elem_data.get("description"):
            for lang_tag, text in elem_data.get("description").items():
                if text: 
                    annotations.append(
                        Annotation(
                            property=RDFS_COMMENT,
                            value=text,
                            datatype="xsd:string",
                            language=lang_tag,
                        ),
                    )

        if elem_data.get("label"):
            for lang_tag, text in elem_data.get("label").items():
                if text: 
                    annotations.append(
                        Annotation(
                            property=RDFS_LABEL,
                            value=text,
                            datatype="xsd:string",
                            language=lang_tag,
                        ),
                    )

        return GrapholscapeEntity(
            fullIri=iri,
            datatype=elem_data.get("datatype", None),
            annotations=annotations,
        )

    for u, v, k in list(nx_graph.edges):
        source_node_data = nx_graph.nodes[u]
        target_node_data = nx_graph.nodes[v]
        edge_data = nx_graph.edges[u, v, k]

        gscape_src_node = add_node(u, source_node_data)
        gscape_tgt_node = add_node(v, target_node_data)
        if gscape_src_node is not None and gscape_tgt_node is not None:
            add_edge(gscape_src_node.id, gscape_tgt_node.id, k, edge_data)

    for n in list(nx_graph.nodes):
        if nx_graph.degree(n) == 0:  # add nodes without connected edges
            isolated = add_node(n, nx_graph.nodes[n])
            if isolated is None:
                continue
        hierarchies = nx_graph.nodes[n].get("hierarchies")
        if hierarchies is not None:
            for h in hierarchies:
                add_hierarchy(h)

    if file_name:
        with open(file_name, "w") as f:
            f.write(json.dumps(rdf_graph.to_dict()))

    return rdf_graph

def get_classes_in_hierarchy(
        df: OWLDataFactory,
        du_node: Node,
        edges: list[Edge],
        node_map: dict[str, Node],
):
    """Trova le classi collegate per gli assiomi di Unione."""
    ces = HashSet()
    for e in edges:
        if e.type == TypesEnum.INPUT and e.target_id == du_node.id:
            source_node = node_map.get(e.source_id)
            if source_node is None:
                raise RuntimeError(f"Cannot find node {e.source_id} for edge {e.id}")
            # Chiama il metodo Java df.getOWLClass
            ces.add(df.getOWLClass(IRI.create(source_node.iri)))
    return ces

def rdf_graph_to_owl(rdf_graph: RDFGraph) -> OWLOntology:
    manager: OWLOntologyManager = OWLManager.createOWLOntologyManager()
    df: OWLDataFactory = manager.getOWLDataFactory()

    # 1. Creazione dell'OWLOntologyID
    id: OWLOntologyID
    if rdf_graph.metadata.version is not None:
        id = OWLOntologyID(
            IRI.create(rdf_graph.metadata.iri),
            IRI.create(rdf_graph.metadata.version),
        )
    else:
        id = OWLOntologyID(IRI.create(rdf_graph.metadata.iri))

    # 2. Creazione dell'Ontologia
    owlOntology: OWLOntology = manager.createOntology(id)

    # 3. Gestione delle Annotazioni dei Metadati
    if rdf_graph.metadata.annotations is not None:
        for a in rdf_graph.metadata.annotations:
            property: OWLAnnotationProperty = df.getOWLAnnotationProperty(IRI.create(a.var_property))
            v = a.value
            if v is None:
                v = a.lexical_form
            value: OWLAnnotationValue = df.getOWLLiteral(v)
            if a.language is not None:
                value: OWLAnnotationValue = df.getOWLLiteral(v, a.language)
            owlAnnotation: OWLAnnotation = df.getOWLAnnotation(property, value)
            changes = ArrayList()
            changes.add(AddOntologyAnnotation(owlOntology, owlAnnotation))
            manager.applyChanges(changes)

    # 4. Gestione dei Namespace (Prefissi)
    onto_format = manager.getOntologyFormat(owlOntology)
    # Controlliamo se l'oggetto Java è un'istanza di PrefixDocumentFormat (simile al `instanceof` e al type-casting Java)
    if isinstance(onto_format, PrefixDocumentFormat):
        pdf: PrefixDocumentFormat = onto_format
        for n in rdf_graph.metadata.namespaces:
            for p in n.prefixes:
                pdf.setPrefix(p, n.value)

    # 5. Elaborazione delle Entity (Assiomi di Funzionalità, Range, Annotazioni)
    for e in rdf_graph.entities:
        subject = IRI.create(e.full_iri)

        # Annotazioni delle Entity
        if e.annotations is not None:
            for a in e.annotations:
                property: OWLAnnotationProperty = df.getOWLAnnotationProperty(IRI.create(a.var_property))
                v = a.value
                if v is None:
                    v = a.lexical_form
                value: OWLAnnotationValue = df.getOWLLiteral(v)
                if a.language is not None:
                    value: OWLAnnotationValue = df.getOWLLiteral(v, a.language)
                # owlOntology.addAxiom
                owlOntology.addAxiom(df.getOWLAnnotationAssertionAxiom(property, subject, value))

        # Proprietà Funzionali (Object Properties)
        if e.function_properties is not None:
            prop_object = df.getOWLObjectProperty(subject)
            for f in e.function_properties:
                if f == FunctionPropertiesEnum.ASYMMETRIC:
                    owlOntology.addAxiom(df.getOWLAsymmetricObjectPropertyAxiom(prop_object))
                elif f == FunctionPropertiesEnum.SYMMETRIC:
                    owlOntology.addAxiom(df.getOWLSymmetricObjectPropertyAxiom(prop_object))
                elif f == FunctionPropertiesEnum.FUNCTIONAL:
                    owlOntology.addAxiom(df.getOWLFunctionalObjectPropertyAxiom(prop_object))
                elif f == FunctionPropertiesEnum.INVERSEFUNCTIONAL:
                    owlOntology.addAxiom(df.getOWLInverseFunctionalObjectPropertyAxiom(prop_object))
                elif f == FunctionPropertiesEnum.IRREFLEXIVE:
                    owlOntology.addAxiom(df.getOWLIrreflexiveObjectPropertyAxiom(prop_object))
                elif f == FunctionPropertiesEnum.REFLEXIVE:
                    owlOntology.addAxiom(df.getOWLReflexiveObjectPropertyAxiom(prop_object))
                elif f == FunctionPropertiesEnum.TRANSITIVE:
                    owlOntology.addAxiom(df.getOWLTransitiveObjectPropertyAxiom(prop_object))

        # Proprietà Dati Funzionale
        if e.is_data_property_functional is not None and e.is_data_property_functional:
            prop_data = df.getOWLDataProperty(subject)
            owlOntology.addAxiom(df.getOWLFunctionalDataPropertyAxiom(prop_data))

        # Range della Proprietà Dati (Datatype)
        if e.datatype is not None:
            prop_data = df.getOWLDataProperty(subject)
            datatype = df.getOWLDatatype(IRI.create(e.datatype))
            owlOntology.addAxiom(df.getOWLDataPropertyRangeAxiom(prop_data, datatype))

    # 6. Dichiarazione dei Nodi (Classes, Individuals, Properties)
    map_nodes: dict[str, Node] = {}
    for d in rdf_graph.diagrams:
        if d.nodes is not None:
            for n in d.nodes:
                map_nodes[n.id] = n
                owlEntity: Optional[OWLEntity] = None

                # Simula lo switch-case
                if n.type == TypesEnum.CLASS:
                    owlEntity = df.getOWLClass(IRI.create(n.iri))
                elif n.type in [TypesEnum.CLASS_INSTANCE, TypesEnum.INDIVIDUAL]:
                    owlEntity = df.getOWLNamedIndividual(IRI.create(n.iri))
                elif n.type == TypesEnum.OBJECT_PROPERTY:
                    owlEntity = df.getOWLObjectProperty(IRI.create(n.iri))
                elif n.type == TypesEnum.DATA_PROPERTY:
                    owlEntity = df.getOWLDataProperty(IRI.create(n.iri))

                if owlEntity is not None:
                    owlOntology.addAxiom(df.getOWLDeclarationAxiom(owlEntity))

    # 7. Elaborazione dei Bordi (Edges) e Aggiunta degli Assiomi
    for d in rdf_graph.diagrams:
        if d.edges is not None:
            for e in d.edges:
                source_node = map_nodes.get(e.source_id)
                target_node = map_nodes.get(e.target_id)

                if source_node is None:
                    raise RuntimeError(f"Cannot find node {e.source_id} for edge {e.id}")
                if target_node is None:
                    raise RuntimeError(f"Cannot find node {e.target_id} for edge {e.id}")

                # Simula lo switch-case sul tipo di bordo
                if e.type == TypesEnum.OBJECT_PROPERTY:
                    # Assiomi di Proprietà di Oggetto
                    property: OWLObjectPropertyExpression = df.getOWLObjectProperty(IRI.create(e.iri))

                    if source_node.type == TypesEnum.CLASS or target_node.type == TypesEnum.CLASS:
                        # Dominio e Range a livello di Classe
                        domain: OWLClassExpression = df.getOWLClass(IRI.create(source_node.iri))
                        range: OWLClassExpression = df.getOWLClass(IRI.create(target_node.iri))

                        if e.domain_typed:
                            owlOntology.addAxiom(df.getOWLObjectPropertyDomainAxiom(property, domain))
                        if e.domain_mandatory:
                            # Existential Restriction (SomeValuesFrom)
                            axiom = df.getOWLSubClassOfAxiom(domain, df.getOWLObjectSomeValuesFrom(property,
                                                                                                   df.getOWLThing()))
                            owlOntology.addAxiom(axiom)
                        if e.range_typed:
                            owlOntology.addAxiom(df.getOWLObjectPropertyRangeAxiom(property, range))
                        if e.range_mandatory:
                            # Existential Restriction sull'Inverso
                            inverse_property = df.getOWLObjectInverseOf(property.asOWLObjectProperty())
                            axiom = df.getOWLSubClassOfAxiom(range, df.getOWLObjectSomeValuesFrom(inverse_property,
                                                                                                  df.getOWLThing()))
                            owlOntology.addAxiom(axiom)

                    elif source_node.type in [TypesEnum.INDIVIDUAL, TypesEnum.CLASS_INSTANCE] and \
                            target_node.type in [TypesEnum.INDIVIDUAL, TypesEnum.CLASS_INSTANCE]:
                        # Asserzione tra Individui
                        subject: OWLIndividual = df.getOWLNamedIndividual(IRI.create(source_node.iri))
                        object: OWLIndividual = df.getOWLNamedIndividual(IRI.create(target_node.iri))
                        owlOntology.addAxiom(df.getOWLObjectPropertyAssertionAxiom(property, subject, object))

                elif e.type == TypesEnum.ATTRIBUTE_EDGE:
                    # Assiomi di Proprietà di Dati
                    data_property: OWLDataPropertyExpression = df.getOWLDataProperty(IRI.create(target_node.iri))
                    data_domain: OWLClassExpression = df.getOWLClass(IRI.create(source_node.iri))

                    if e.domain_typed:
                        owlOntology.addAxiom(df.getOWLDataPropertyDomainAxiom(data_property, data_domain))
                    if e.domain_mandatory:
                        # Existential Restriction (DataSomeValuesFrom) con rdfs:Literal
                        literal_datatype = df.getOWLDatatype(OWL2Datatype.RDFS_LITERAL.getIRI())
                        axiom = df.getOWLSubClassOfAxiom(data_domain, df.getOWLDataSomeValuesFrom(data_property,
                                                                                                  literal_datatype))
                        owlOntology.addAxiom(axiom)

                elif e.type == TypesEnum.ANNOTATION_PROPERTY:
                    # Assiomi di Dominio e Range delle Annotazioni
                    ann_property: OWLAnnotationProperty = df.getOWLAnnotationProperty(IRI.create(e.iri))
                    owlOntology.addAxiom(
                        df.getOWLAnnotationPropertyDomainAxiom(ann_property, IRI.create(source_node.iri)),
                    )
                    owlOntology.addAxiom(
                        df.getOWLAnnotationPropertyRangeAxiom(ann_property, IRI.create(target_node.iri))
                    )

                elif e.type == TypesEnum.EQUIVALENCE:
                    # Classi Equivalenti
                    owlOntology.addAxiom(df.getOWLEquivalentClassesAxiom(
                        df.getOWLClass(IRI.create(source_node.iri)),
                        df.getOWLClass(IRI.create(target_node.iri))
                    ))

                elif e.type == TypesEnum.INCLUSION:
                    # SubClassOf o SubDataPropertyOf
                    iri_source = IRI.create(source_node.iri)
                    iri_target = IRI.create(target_node.iri)
                    if source_node.type == TypesEnum.CLASS and target_node.type == TypesEnum.CLASS:
                        owlOntology.addAxiom(df.getOWLSubClassOfAxiom(
                            df.getOWLClass(iri_source),
                            df.getOWLClass(iri_target)))
                    elif source_node.type == TypesEnum.DATA_PROPERTY and target_node.type == TypesEnum.DATA_PROPERTY:
                        owlOntology.addAxiom(df.getOWLSubDataPropertyOfAxiom(
                            df.getOWLDataProperty(iri_source),
                            df.getOWLDataProperty(iri_target)))

                elif e.type == TypesEnum.INSTANCE_OF:
                    # Class Assertion (Individuo è istanza di Classe)
                    owlOntology.addAxiom(df.getOWLClassAssertionAxiom(
                        df.getOWLClass(IRI.create(target_node.iri)),
                        df.getOWLNamedIndividual(IRI.create(source_node.iri))
                    ))

                elif e.type in [TypesEnum.UNION, TypesEnum.DISJOINT_UNION, TypesEnum.COMPLETE_UNION,
                                TypesEnum.COMPLETE_DISJOINT_UNION]:
                    # Assiomi di Unione/Disgiunzione
                    if target_node.type == TypesEnum.CLASS:
                        owlClass: OWLClass = df.getOWLClass(IRI.create(target_node.iri))
                        ces: set[OWLClass] = get_classes_in_hierarchy(df, source_node, d.edges,
                                                                      map_nodes)
                        axioms = HashSet()
                        for i in ces:
                            axioms.add(df.getOWLSubClassOfAxiom(i, owlClass))
                        # [df.getOWLSubClassOfAxiom(i, owlClass) for i in ces]

                        if e.type == TypesEnum.DISJOINT_UNION:
                            # Aggiunge l'assioma di Disgiunzione
                            axioms.add(df.getOWLDisjointClassesAxiom(ces))
                        elif e.type == TypesEnum.COMPLETE_UNION:
                            # Aggiunge l'assioma di Equivalenza (con ObjectUnionOf)
                            equivs = HashSet()
                            equivs.add(owlClass)
                            equivs.add(df.getOWLObjectUnionOf(ces))
                            axioms.add(df.getOWLEquivalentClassesAxiom(equivs))
                        elif e.type == TypesEnum.COMPLETE_DISJOINT_UNION:
                            # Aggiunge Equivalenza (UnionOf) e Disgiunzione (Classes)
                            equivs = HashSet()
                            equivs.add(owlClass)
                            equivs.add(df.getOWLObjectUnionOf(ces))
                            axioms.add(df.getOWLEquivalentClassesAxiom(equivs))
                            axioms.add(df.getOWLDisjointClassesAxiom(ces))

                        # Aggiunge tutti gli assiomi alla volta
                        # Per JPype, convertiamo la lista Python in un Java Set
                        manager.addAxioms(owlOntology, axioms)
    # Translate class instance for data properties
    if rdf_graph.class_instance_entities is not None:
        for cie in rdf_graph.class_instance_entities:
            if cie.data_properties is not None:
                for dp in cie.data_properties:
                    owlOntology.add(
                        df.getOWLDataPropertyAssertionAxiom(
                            df.getOWLDataProperty(dp.iri),
                            df.getOWLNamedIndividual(cie.full_iri),
                            df.getOWLLiteral(
                                dp.value,
                                dp.datatype
                            )
                        ))

    return owlOntology


def serialize_owl(owl_ontology, format):
    manager = owl_ontology.getOWLOntologyManager()
    if format.lower() == 'functional syntax':
        owl_format = FunctionalSyntaxDocumentFormat()
    elif format.lower() == 'rdf/xml':
        owl_format = RDFXMLDocumentFormat()
    elif format.lower() == 'turtle':
        owl_format = TurtleDocumentFormat()
    else:
        raise RuntimeError(f"Unrecognized format {format}")
    owl_format.copyPrefixesFrom(manager.getOntologyFormat(owl_ontology).asPrefixOWLOntologyFormat())
    stream = StringDocumentTarget()
    owl_ontology.saveOntology(owl_format, stream)
    return str(stream.toString())
