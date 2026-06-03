from typing import Dict, Set, List, Optional
from .jvm.java import *
from .jvm.owlapi import *
from .server.models.class_instance_entity import ClassInstanceEntity
from .server.models.data_property_value import DataPropertyValue
from .server.models.function_properties_enum import FunctionPropertiesEnum
from .server.models.namespace import Namespace

from .server.models.rdf_graph import RDFGraph
from .server.models.types_enum import TypesEnum
from .server.models.diagram import Diagram
from .server.models.grapholscape_entity import GrapholscapeEntity
from .server.models.node import Node
from .server.models.edge import Edge
from .server.models.rdf_graph_metadata import RDFGraphMetadata
from .server.models.grapholscape_annotation import GrapholscapeAnnotation


class TypedParticipationEnum:
    """
    Simulazione della logica dell'enum Java TypedParticipationEnum.

    TYPED(True, False)
    PARTICIPATED(False, True)
    TYPED_AND_PARTICIPATED(True, True)
    """

    def __init__(self, typed: bool, participated: bool):
        self._typed = typed
        self._participated = participated

    def isParticipated(self) -> bool:
        """Restituisce il valore del campo 'participated'."""
        return self._participated

    def isTyped(self) -> bool:
        """Restituisce il valore del campo 'typed'."""
        return self._typed


# Definizione delle istanze statiche (i membri dell'Enum)
TypedParticipationEnum.TYPED = TypedParticipationEnum(True, False)
TypedParticipationEnum.PARTICIPATED = TypedParticipationEnum(False, True)
TypedParticipationEnum.TYPED_AND_PARTICIPATED = TypedParticipationEnum(True, True)


# Esempio di utilizzo:
# if TypedParticipationEnum.TYPED.isParticipated():
#     print("È Partecipato")

class OWL2Gscape:
    nodesPrefix = "n"
    edgesPrefix = "e"
    thing: OWLClass = OWLManager.getOWLDataFactory().getOWLThing()

    nodesIds: Dict[str, str] = {}
    nodesCount: int = 0
    edgesCount: int = 0
    addedThing: bool = False

    # Metodi di utilità (statici in Java)

    def __init__(self, ontology: OWLOntology):
        self.ontology = ontology
        self.nodesIds = {}
        self.nodesCount = 0
        self.edgesCount = 0
        self.addedThing = False

    def add_lang_to_rdfgraph_metadata(self, lang: str, rdf_graph: RDFGraph):
        metadata = rdf_graph.metadata
        if metadata.languages is None:
            metadata.languages = []
        if lang and (metadata.languages is None or lang not in metadata.languages):
            metadata.languages.append(lang)

    def get_node_id(self, te: TypesEnum, iri: Optional[str]) -> str:
        if te == TypesEnum.UNION or te == TypesEnum.DISJOINT_UNION:
            id_val = f"{self.nodesPrefix}{self.nodesCount}"
            self.nodesCount += 1
            return id_val

        key = f"{te}_{iri}"
        if key not in self.nodesIds:
            id_val = f"{self.nodesPrefix}{self.nodesCount}"
            self.nodesIds[key] = id_val
            self.nodesCount += 1
        return self.nodesIds[key]

    def add_thing_to_entities_and_nodes(self, rdf_graph: RDFGraph, d: Diagram):
        if not self.addedThing:
            self.addedThing = True
            e = GrapholscapeEntity(fullIri=str(self.thing.getIRI().toString()))
            rdf_graph.entities.append(e)

            n = Node(
                id=self.get_node_id(TypesEnum.CLASS, self.thing.getIRI().toString()),
                type=TypesEnum.CLASS,
                iri=str(self.thing.getIRI().toString())
            )
            d.nodes.append(n)

    def are_disjoint(self, operands: set[OWLClass]) -> bool:
        if not operands: return False
        # Otteniamo l'Iterator e prendiamo il primo elemento in Python
        first_operand = next(iter(operands))
        # Chiamata al metodo Java getDisjointClassesAxioms
        dca_set = self.ontology.getDisjointClassesAxioms(first_operand)

        # JPype Set (Java Set) iterabile in Python
        for dca in dca_set:
            # Usiamo getOperands() che restituisce un JList
            ops_list = dca.getClassExpressionsAsList()
            ops = set(ops_list)  # Conversione in Set Python per il confronto

            # Confronto se gli insiemi di classi sono gli stessi
            if operands == ops:
                return True
        return False

    def add_annotations_edges(self, annotations: set[OWLAnnotationAssertionAxiom],
                              rdf_graph: RDFGraph, n: Node):
        # Il diagramma delle annotazioni è sempre il secondo nella lista
        annotation_diagram: Diagram = rdf_graph.diagrams[1]

        for annotation in annotations:
            # annotation.getValue().asIRI().isPresent() -> accesso tramite JPype
            if annotation.getValue().asIRI().isPresent():
                iri: IRI = annotation.getValue().asIRI().get()
                targetIRI = str(iri.toString())
                tId: str
                n_type: TypesEnum

                # Chiama i metodi contains*InSignature (Java boolean)
                if self.ontology.containsClassInSignature(iri):
                    tId = self.get_node_id(TypesEnum.CLASS, targetIRI)
                    n_type = TypesEnum.CLASS
                elif self.ontology.containsIndividualInSignature(iri):
                    tId = self.get_node_id(TypesEnum.INDIVIDUAL, targetIRI)
                    n_type = TypesEnum.INDIVIDUAL
                else:
                    tId = self.get_node_id(TypesEnum.INDIVIDUAL, targetIRI)
                    n_type = TypesEnum.IRI  # Tipo generico per IRIs non definite

                t = Node(
                    id=tId,
                    iri=targetIRI,
                    type=n_type,
                )

                e = Edge(
                    id=f"{self.edgesPrefix}{self.edgesCount}",
                    iri=str(annotation.getProperty().getIRI().toString()),
                    type=TypesEnum.ANNOTATION_PROPERTY,
                    sourceId=n.id,
                    targetId=tId,
                )
                self.edgesCount += 1

                # Aggiunge i nodi e il bordo al diagramma delle annotazioni
                # Nota: duplicati di nodi nel diagramma sono permessi dalla logica Java
                annotation_diagram.nodes.append(n)
                annotation_diagram.nodes.append(t)
                annotation_diagram.edges.append(e)

    def add_ontology_annotations_edges(self, annotations: set[OWLAnnotation],
                              rdf_graph: RDFGraph, n: Node):
        # Il diagramma delle annotazioni è sempre il secondo nella lista
        annotation_diagram: Diagram = rdf_graph.diagrams[1]

        for annotation in annotations:
            # annotation.getValue().asIRI().isPresent() -> accesso tramite JPype
            if annotation.getValue().asIRI().isPresent():
                iri: IRI = annotation.getValue().asIRI().get()
                targetIRI = str(iri.toString())
                tId: str
                n_type: TypesEnum

                # Chiama i metodi contains*InSignature (Java boolean)
                if self.ontology.containsClassInSignature(iri):
                    tId = self.get_node_id(TypesEnum.CLASS, targetIRI)
                    n_type = TypesEnum.CLASS
                elif self.ontology.containsIndividualInSignature(iri):
                    tId = self.get_node_id(TypesEnum.INDIVIDUAL, targetIRI)
                    n_type = TypesEnum.INDIVIDUAL
                else:
                    tId = self.get_node_id(TypesEnum.INDIVIDUAL, targetIRI)
                    n_type = TypesEnum.IRI  # Tipo generico per IRIs non definite

                t = Node(
                    id=tId,
                    iri=targetIRI,
                    type=n_type,
                )

                e = Edge(
                    id=f"{self.edgesPrefix}{self.edgesCount}",
                    iri=str(annotation.getProperty().getIRI().toString()),
                    type=TypesEnum.ANNOTATION_PROPERTY,
                    sourceId=n.id,
                    targetId=tId,
                )
                self.edgesCount += 1

                # Aggiunge i nodi e il bordo al diagramma delle annotazioni
                # Nota: duplicati di nodi nel diagramma sono permessi dalla logica Java
                annotation_diagram.nodes.append(n)
                annotation_diagram.nodes.append(t)
                annotation_diagram.edges.append(e)

    def compute_participation_and_hierarchies(
            self,
            owl_class: OWLClass,
            ce: OWLClassExpression,
            domain_participation: dict[OWLObjectProperty, list[tuple[OWLClass, TypedParticipationEnum]]],
            domain_data_participation: dict[OWLDataProperty, list[tuple[OWLClass, TypedParticipationEnum]]],
            range_participation: dict[OWLObjectProperty, list[tuple[OWLClass, TypedParticipationEnum]]],
            d: Diagram,
            complete: bool):

        # OWLObjectSomeValuesFrom (osvf)
        if isinstance(ce, OWLObjectSomeValuesFrom):
            osvf: OWLObjectSomeValuesFrom = ce

            # OWLObjectInverseOf
            if isinstance(osvf.getProperty(), OWLObjectInverseOf):
                property_expr: OWLObjectPropertyExpression = osvf.getProperty().getInverseProperty()
                if isinstance(property_expr, OWLObjectProperty):
                    prop = property_expr.asOWLObjectProperty()
                    enum_val = TypedParticipationEnum.TYPED_AND_PARTICIPATED if complete else TypedParticipationEnum.PARTICIPATED
                    pair = (owl_class, enum_val)
                    if prop not in range_participation:
                        range_participation[prop] = [pair]
                    else:
                        range_participation[prop].append(pair)
            else:  # Proprietà diretta
                property_expr: OWLObjectPropertyExpression = osvf.getProperty()
                if isinstance(property_expr, OWLObjectProperty):
                    prop = property_expr.asOWLObjectProperty()
                    enum_val = TypedParticipationEnum.TYPED_AND_PARTICIPATED if complete else TypedParticipationEnum.PARTICIPATED
                    pair = (owl_class, enum_val)
                    if prop not in domain_participation:
                        domain_participation[prop] = [pair]
                    else:
                        domain_participation[prop].append(pair)

        # OWLDataSomeValuesFrom (dsvf)
        elif isinstance(ce, OWLDataSomeValuesFrom):
            dsvf: OWLDataSomeValuesFrom = ce
            property_expr: OWLDataPropertyExpression = dsvf.getProperty()
            if isinstance(property_expr, OWLDataProperty):
                prop = property_expr.asOWLDataProperty()
                enum_val = TypedParticipationEnum.TYPED_AND_PARTICIPATED if complete else TypedParticipationEnum.PARTICIPATED
                pair = (owl_class, enum_val)
                if prop not in domain_data_participation:
                    domain_data_participation[prop] = [pair]
                else:
                    domain_data_participation[prop].append(pair)

        # OWLObjectUnionOf (ouo)
        elif isinstance(ce, OWLObjectUnionOf):
            ouo: OWLObjectUnionOf = ce
            uNodes: List[Node] = []
            operands: Set[OWLClass] = set()

            for uCe in ouo.getOperands():  # JSet iterabile
                if isinstance(uCe, OWLClass):
                    op: OWLClass = uCe.asOWLClass()
                    operands.add(op)
                    n = Node(
                        id=self.get_node_id(TypesEnum.CLASS, op.getIRI().toString()),
                        iri=str(op.getIRI().toString()),
                        type=TypesEnum.CLASS,
                    )
                    uNodes.append(n)

            if len(uNodes) != 0:
                u = Node(
                    id=self.get_node_id(TypesEnum.UNION, None),
                    type=TypesEnum.UNION,
                )
                edge = Edge(
                    id=f"{self.edgesPrefix}{self.edgesCount}",
                    type=TypesEnum.UNION,
                    sourceId=u.id,
                    targetId=self.get_node_id(TypesEnum.CLASS, owl_class.getIRI().toString()),
                )
                self.edgesCount += 1

                disjoint = self.are_disjoint(operands)

                if disjoint:
                    u.type = TypesEnum.DISJOINT_UNION
                else:
                    u.type = TypesEnum.UNION

                d.nodes.append(u)

                # Tipi di bordo
                if disjoint:
                    edge.type = TypesEnum.COMPLETE_DISJOINT_UNION if complete else TypesEnum.DISJOINT_UNION
                else:
                    edge.type = TypesEnum.COMPLETE_UNION if complete else TypesEnum.UNION

                d.edges.append(edge)

                for n in uNodes:
                    e = Edge(
                        id=f"{self.edgesPrefix}{self.edgesCount}",
                        type=TypesEnum.INPUT,
                        sourceId=n.id,
                        targetId=u.id,
                    )
                    self.edgesCount += 1
                    d.nodes.append(n)
                    d.edges.append(e)

    # Metodo principale di conversione
    def owl_to_rdf_graph(self) -> RDFGraph:

        manager = self.ontology.getOWLOntologyManager()
        oId: OWLOntologyID = self.ontology.getOntologyID()

        # Metadata IRI/Version
        if oId.getOntologyIRI().isPresent():
            iri = str(oId.getOntologyIRI().get().toString())
        else:
            iri = ""
        if oId.getVersionIRI().isPresent():
            version = str(oId.getVersionIRI().get().toString())
        else:
            version = ""
        metadata = RDFGraphMetadata(
            iri=iri,
            version=version,
            annotation_properties=[],
            namespaces=[],
            annotations=[]
        )
        rdf_graph = RDFGraph(
            modelType='ontology',
            metadata=metadata,
            diagrams=[],
            entities=[],
            classInstanceEntities=[],
        )
        # Annotazioni dell'Ontologia
        for annotation in self.ontology.getAnnotations():  # JSet iterabile
            # asLiteral().isPresent()
            if annotation.getValue().asLiteral().isPresent():
                value_literal: OWLLiteral = annotation.getValue().asLiteral().get()
                iri = str(annotation.getProperty().getIRI().toString())
                if iri not in metadata.annotation_properties:
                    metadata.annotation_properties.append(iri)
                a = GrapholscapeAnnotation(
                    property=iri,
                    value=str(value_literal.getLiteral()),
                    language=str(value_literal.getLang()),
                    datatype=str(value_literal.getDatatype().getIRI().toString()),
                )
                self.add_lang_to_rdfgraph_metadata(a.language, rdf_graph)
                metadata.annotations.append(a)
            if annotation.getValue().asIRI().isPresent():
                value: IRI = annotation.getValue().asIRI().get()
                iri = str(annotation.getProperty().getIRI().toString())
                if iri not in metadata.annotation_properties:
                    metadata.annotation_properties.append(iri)
                a = GrapholscapeAnnotation(
                    property=iri,
                    value=str(value.toString()),
                    hasIriValue=True
                )
                metadata.annotations.append(a)
        # Namespace (Prefissi)
        onto_format = manager.getOntologyFormat(self.ontology)
        if isinstance(onto_format, PrefixDocumentFormat):
            pdf: PrefixDocumentFormat = onto_format
            for pName in pdf.getPrefixName2PrefixMap().keySet():  # JSet iterabile
                namespace: Namespace
                value = pdf.getPrefixName2PrefixMap().get(pName)

                # Logica per riutilizzare l'oggetto Namespace (Java Stream, FindFirst)
                found_n = next((na for na in metadata.namespaces if na.value == value), None)
                if found_n:
                    namespace = found_n
                else:
                    namespace = Namespace(value=str(value), prefixes=[])

                # pName finisce con ':' che va rimosso (pName.substring(0, pName.length() - 1))
                namespace.prefixes += [pName[:-1]]

                if not found_n:
                    metadata.namespaces.append(namespace)

        # Elaborazione delle Entity (Assiomi di Funzionalità/Range/Annotazioni)
        for oe in self.ontology.getSignature(Imports.INCLUDED):
            e = GrapholscapeEntity(
                fullIri=str(oe.getIRI().toString())
            )
            e.annotations = []
            e.function_properties = []
            # Annotazioni dell'Entità
            annotations: Set[OWLAnnotationAssertionAxiom] = self.ontology.getAnnotationAssertionAxioms(oe.getIRI())
            for annotation in annotations:  # JSet iterabile
                if annotation.getValue().asLiteral().isPresent():
                    value_literal: OWLLiteral = annotation.getValue().asLiteral().get()
                    iri = str(annotation.getProperty().getIRI().toString())
                    if iri not in metadata.annotation_properties:
                        metadata.annotation_properties.append(iri)
                    a = GrapholscapeAnnotation(
                        property=iri,
                        value=str(value_literal.getLiteral()),
                        language=str(value_literal.getLang()),
                        datatype=str(value_literal.getDatatype().getIRI().toString()),
                    )
                    self.add_lang_to_rdfgraph_metadata(a.language, rdf_graph)
                    e.annotations.append(a)
                if annotation.getValue().asIRI().isPresent():
                    value: IRI = annotation.getValue().asIRI().get()
                    iri = str(annotation.getProperty().getIRI().toString())
                    if iri not in metadata.annotation_properties:
                        metadata.annotation_properties.append(iri)
                    a = GrapholscapeAnnotation(
                        property=iri,
                        value=str(value.toString()),
                        hasIriValue=True
                    )
                    e.annotations.append(a)

            # Proprietà Dati
            if isinstance(oe, OWLDataProperty):
                prop_data = oe.asOWLDataProperty()
                # Funzionale
                if not self.ontology.getFunctionalDataPropertyAxioms(prop_data).isEmpty():
                    e.is_data_property_functional = (True)
                # Range
                ranges: Set[OWLDataPropertyRangeAxiom] = self.ontology.getDataPropertyRangeAxioms(prop_data)
                for odpra in ranges:
                    range_expr: OWLDataRange = odpra.getRange()
                    if isinstance(range_expr, OWLDatatype):
                        e.datatype = str(range_expr.asOWLDatatype().getIRI().toString())
                        break  # Prende il primo Datatype trovato

            # Proprietà Oggetto
            if isinstance(oe, OWLObjectProperty):
                prop_object = oe.asOWLObjectProperty()
                # Aggiunge le proprietà funzionali (Java JSet.isEmpty() -> Python not JSet)
                if not self.ontology.getFunctionalObjectPropertyAxioms(prop_object).isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.FUNCTIONAL)
                if not self.ontology.getInverseFunctionalObjectPropertyAxioms(prop_object).isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.INVERSEFUNCTIONAL)
                if not self.ontology.getSymmetricObjectPropertyAxioms(prop_object).isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.SYMMETRIC)
                if not self.ontology.getAsymmetricObjectPropertyAxioms(prop_object).isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.ASYMMETRIC)
                if not self.ontology.getReflexiveObjectPropertyAxioms(prop_object).isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.REFLEXIVE)
                if not self.ontology.getIrreflexiveObjectPropertyAxioms(prop_object).isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.IRREFLEXIVE)
                if not self.ontology.getTransitiveObjectPropertyAxioms(prop_object).isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.TRANSITIVE)

            rdf_graph.entities.append(e)

        # Creazione dei Diagrammi
        d = Diagram(id=0, name="Ontology", nodes=[], edges=[])
        rdf_graph.diagrams.append(d)
        d2 = Diagram(id=-1, name="Annotations", nodes=[], edges=[])
        rdf_graph.diagrams.append(d2)

        # NODES (Classi)
        for c in self.ontology.getClassesInSignature(Imports.INCLUDED):
            node = Node(
                id=self.get_node_id(TypesEnum.CLASS, c.getIRI().toString()),
                iri=str(c.getIRI().toString()),
                type=TypesEnum.CLASS,
            )
            d.nodes.append(node)
            # Aggiunge i bordi di Annotazione
            self.add_annotations_edges(self.ontology.getAnnotationAssertionAxioms(c.getIRI()),
                                       rdf_graph, node)

        # Mappe per Partecipazione
        domain_participation: dict[OWLObjectProperty, list[tuple[OWLClass, TypedParticipationEnum]]] = {}
        domain_data_participation: dict[OWLDataProperty, list[tuple[OWLClass, TypedParticipationEnum]]] = {}
        range_participation: dict[OWLObjectProperty, list[tuple[OWLClass, TypedParticipationEnum]]] = {}

        # EDGES (Assiomi complessi e Sottoclassi)
        for ax in self.ontology.getAxioms(Imports.INCLUDED):
            # OWLEquivalentClassesAxiom
            if isinstance(ax, OWLEquivalentClassesAxiom):
                eca: OWLEquivalentClassesAxiom = ax
                owlClass: Optional[OWLClass] = None
                others: Set[OWLClassExpression] = set()

                for ce in eca.getClassExpressions():  # JSet iterabile
                    if owlClass is None and isinstance(ce, OWLClass):
                        owlClass = ce.asOWLClass()
                    else:
                        others.add(ce)

                if owlClass is not None:
                    for ce in others:
                        self.compute_participation_and_hierarchies(owlClass, ce,
                                                                   domain_participation, domain_data_participation,
                                                                   range_participation, d,
                                                                   True  # complete = True per Equivalenza
                                                                   )

            # OWLSubClassOfAxiom
            elif isinstance(ax, OWLSubClassOfAxiom):
                sbco: OWLSubClassOfAxiom = ax
                exprSup = sbco.getSuperClass()
                exprSub = sbco.getSubClass()

                if isinstance(exprSup, OWLClass) and isinstance(exprSub, OWLClass):
                    # Assioma di Inclusione (SubClassOf)
                    e = Edge(
                        id=f"{self.edgesPrefix}{self.edgesCount}",
                        sourceId=str(self.get_node_id(TypesEnum.CLASS,
                                                      exprSub.asOWLClass().getIRI().toString())),
                        targetId=str(self.get_node_id(TypesEnum.CLASS,
                                                      exprSup.asOWLClass().getIRI().toString())),
                        type=TypesEnum.INCLUSION
                    )
                    self.edgesCount += 1
                    d.edges.append(e)
                elif isinstance(exprSup, OWLClass):
                    # SuperClasse è una Classe, Sottoclasse è una restrizione (computeParticipationAndHierarchies)
                    self.compute_participation_and_hierarchies(
                        exprSup.asOWLClass(),
                        exprSub,
                        domain_participation,
                        domain_data_participation,
                        range_participation,
                        d,
                        False
                    )
                elif isinstance(exprSub, OWLClass):
                    # Sottoclasse è una Classe, SuperClasse è una restrizione (computeParticipationAndHierarchies)
                    self.compute_participation_and_hierarchies(
                        exprSub.asOWLClass(),
                        exprSup,
                        domain_participation,
                        domain_data_participation,
                        range_participation,
                        d,
                        False
                    )

            # OWLDisjointUnionAxiom
            elif isinstance(ax, OWLDisjointUnionAxiom):
                dua: OWLDisjointUnionAxiom = ax

                # Nodo per l'Unione
                du = Node(
                    id=self.get_node_id(TypesEnum.UNION, None),
                    type=TypesEnum.DISJOINT_UNION,
                )
                d.nodes.append(du)

                # Bordo dal Target (Classe) al Nodo Unione (COMPLETE_DISJOINT_UNION)
                e_incl = Edge(
                    id=f"{self.edgesPrefix}{self.edgesCount}",
                    type=TypesEnum.COMPLETE_DISJOINT_UNION,
                    sourceId=str(self.get_node_id(TypesEnum.CLASS, dua.getOWLClass().getIRI().toString())),
                    targetId=du.id,
                )
                self.edgesCount += 1
                d.edges.append(e_incl)

                # Bordi di Input (membri dell'Unione)
                # Nota: qui in Java è usato un forEach, in Python un ciclo normale
                for ce in dua.getClassExpressions():
                    if isinstance(ce, OWLClass):
                        e = Edge(
                            id=f"{self.edgesPrefix}{self.edgesCount}",
                            type=TypesEnum.INPUT,
                            sourceId=self.get_node_id(TypesEnum.CLASS, ce.asOWLClass().getIRI().toString()),
                            targetId=du.id,
                        )
                        self.edgesCount += 1
                        d.edges.append(e)

            # OWLClassAssertionAxiom (Instance Of)
            elif isinstance(ax, OWLClassAssertionAxiom):
                caa: OWLClassAssertionAxiom = ax

                if isinstance(caa.getIndividual(), OWLNamedIndividual) and caa.getClassExpression().isNamed():
                    e = Edge(
                        id=f"{self.edgesPrefix}{self.edgesCount}",
                        sourceId=self.get_node_id(TypesEnum.INDIVIDUAL,
                                                  caa.getIndividual().asOWLNamedIndividual().getIRI().toString()),
                        targetId=self.get_node_id(TypesEnum.CLASS,
                                                  caa.getClassExpression().asOWLClass().getIRI().toString()),
                        type=TypesEnum.INSTANCE_OF,
                    )
                    self.edgesCount += 1
                    d.edges.append(e)

        # 8. OBJECT PROPERTIES (Edges)
        for op in self.ontology.getObjectPropertiesInSignature(Imports.INCLUDED):
            domains: Set[OWLObjectPropertyDomainAxiom] = self.ontology.getObjectPropertyDomainAxioms(op)
            ranges: Set[OWLObjectPropertyRangeAxiom] = self.ontology.getObjectPropertyRangeAxioms(op)

            # Inizializza o recupera le liste di partecipazione
            domain_part = domain_participation.get(op)
            if domain_part is None: domain_part = []
            range_part = range_participation.get(op)
            if range_part is None: range_part = []

            # Aggiunge Domini e Range espliciti dagli assiomi alla lista di partecipazione
            for dom in domains:
                # dom.getDomain().isNamed() -> Python boolean
                domain_class = dom.getDomain().asOWLClass() if dom.getDomain().isNamed() else self.thing
                domain_part.append((domain_class, TypedParticipationEnum.TYPED))
            for rng in ranges:
                range_class = rng.getRange().asOWLClass() if rng.getRange().isNamed() else self.thing
                range_part.append((range_class, TypedParticipationEnum.TYPED))

            # Assicurarsi che ci sia sempre un'accoppiata (minimo Thing)
            if not domain_part:
                domain_part.append((self.thing, TypedParticipationEnum.TYPED))
            if not range_part:
                range_part.append((self.thing, TypedParticipationEnum.TYPED))

            opCount = 0
            for dp in domain_part:
                for rp in range_part:
                    opCount += 1
                    source: OWLClass = dp[0]
                    target: OWLClass = rp[0]

                    # Logica per l'accoppiamento esistente (opCount > 0 e Edge trovato)
                    if opCount > 1:
                        found_edges = [
                            e for e in d.edges
                            if e.type == TypesEnum.OBJECT_PROPERTY
                               and e.source_id == self.get_node_id(TypesEnum.CLASS,
                                                                   source.getIRI().toString())
                               and e.target_id == self.get_node_id(TypesEnum.CLASS,
                                                                   target.getIRI().toString())
                        ]

                        if found_edges:
                            found_edge = found_edges[0]
                            # Aggiorna gli attributi booleani (logica OR)
                            found_edge.domain_typed = found_edge.domain_typed or TypedParticipationEnum.isTyped(
                                dp[1])
                            found_edge.domain_mandatory = found_edge.domain_mandatory or TypedParticipationEnum.isParticipated(
                                dp[1])
                            found_edge.range_typed = found_edge.range_typed or TypedParticipationEnum.isTyped(
                                rp[1])
                            found_edge.range_mandatory = found_edge.range_mandatory or TypedParticipationEnum.isParticipated(
                                rp[1])
                            continue

                    # Creazione di un nuovo Edge
                    e = Edge(
                        id=f"{self.edgesPrefix}{self.edgesCount}",
                        iri=str(op.getIRI().toString()),
                        sourceId=self.get_node_id(TypesEnum.CLASS, source.getIRI().toString()),
                        targetId=self.get_node_id(TypesEnum.CLASS, target.getIRI().toString()),
                        type=TypesEnum.OBJECT_PROPERTY,
                    )
                    e.domain_mandatory = TypedParticipationEnum.isParticipated(dp[1])
                    e.domain_typed = TypedParticipationEnum.isTyped(dp[1])
                    e.range_mandatory = TypedParticipationEnum.isParticipated(rp[1])
                    e.range_typed = TypedParticipationEnum.isTyped(rp[1])
                    self.edgesCount += 1

                    if source.equals(self.thing) or target.equals(self.thing):
                        self.add_thing_to_entities_and_nodes(rdf_graph, d)

                    d.edges.append(e)

        # 9. DATA PROPERTIES (Attribute Edges)
        for dp in self.ontology.getDataPropertiesInSignature(Imports.INCLUDED):
            domains: Set[OWLDataPropertyDomainAxiom] = self.ontology.getDataPropertyDomainAxioms(dp)
            domain_data_part = domain_data_participation.get(dp)
            if domain_data_part is None: domain_data_part = []

            # Converte gli assiomi di dominio espliciti in partecipazione
            for dom in domains:
                domain_class = dom.getDomain().asOWLClass() if dom.getDomain().isNamed() else self.thing
                domain_data_part.append((domain_class, TypedParticipationEnum.TYPED))

            dpCount = 0
            for ddp in domain_data_part:
                dpCount += 1
                source: OWLClass = ddp[0]

                nId = self.get_node_id(TypesEnum.DATA_PROPERTY, dp.getIRI().toString())

                if dpCount > 1:
                    # Logica per accoppiamento esistente
                    finalNId = nId
                    found_edges = [
                        e for e in d.edges
                        if e.type == TypesEnum.ATTRIBUTE_EDGE
                           and e.source_id == self.get_node_id(TypesEnum.CLASS, source.getIRI().toString())
                           and e.target_id == finalNId
                    ]

                    if found_edges:
                        found_edge = found_edges[0]
                        found_edge.domain_typed = found_edge.domain_typed or TypedParticipationEnum.isTyped(
                            ddp[1])
                        found_edge.domain_mandatory = found_edge.domain_mandatory or TypedParticipationEnum.isParticipated(
                            ddp[1])
                        continue
                    else:
                        # Se non trovato, genera un nuovo ID (simulazione del bug/logica del codice Java)
                        # Nota: il codice Java sembra avere un bug qui, genera un nuovo nId anche se è per la stessa DP
                        nId = f"{self.nodesPrefix}{self.nodesCount}"
                        self.nodesCount += 1

                n = Node(
                    id=nId,
                    iri=str(dp.getIRI().toString()),
                    type=TypesEnum.DATA_PROPERTY,
                )
                d.nodes.append(n)

                e = Edge(
                    id=f"{self.edgesPrefix}{self.edgesCount}",
                    sourceId=self.get_node_id(TypesEnum.CLASS, source.getIRI().toString()),
                    targetId=nId,
                    type=TypesEnum.ATTRIBUTE_EDGE,
                )
                self.edgesCount += 1
                if source.equals(self.thing): self.add_thing_to_entities_and_nodes(rdf_graph, d)
                e.domain_typed = TypedParticipationEnum.isTyped(ddp[1])
                e.domain_mandatory = TypedParticipationEnum.isParticipated(ddp[1])
                d.edges.append(e)

        # 10. INDIVIDUALS (Nodi)
        for i in self.ontology.getIndividualsInSignature(Imports.INCLUDED):
            n = Node(
                id=self.get_node_id(TypesEnum.INDIVIDUAL, i.getIRI().toString()),
                iri=str(i.getIRI().toString()),
                type=TypesEnum.INDIVIDUAL,
            )
            d.nodes.append(n)
            if self.ontology.getOntologyID().getOntologyIRI().isPresent() and i.getIRI().equals(self.ontology.getOntologyID().getOntologyIRI().get()):
                self.add_ontology_annotations_edges(
                    self.ontology.getAnnotations(),
                    rdf_graph,
                    n)
            else:
                self.add_annotations_edges(
                    self.ontology.getAnnotationAssertionAxioms(i.getIRI()),
                    rdf_graph,
                    n)

        # 11. OBJECT PROPERTIES ASSERTIONS (Bordi tra Individui)
        for s in self.ontology.getIndividualsInSignature(Imports.INCLUDED):
            for opa in self.ontology.getObjectPropertyAssertionAxioms(s):
                t: OWLIndividual = opa.getObject()
                if isinstance(t, OWLNamedIndividual):
                    e = Edge(
                        id=f"{self.edgesPrefix}{self.edgesCount}",
                        iri=str(opa.getProperty().asOWLObjectProperty().getIRI().toString()),
                        sourceId=self.get_node_id(TypesEnum.INDIVIDUAL, s.getIRI().toString()),
                        targetId=self.get_node_id(TypesEnum.INDIVIDUAL,
                                                  t.asOWLNamedIndividual().getIRI().toString()),
                        type=TypesEnum.OBJECT_PROPERTY,
                    )
                    self.edgesCount += 1
                    # Valori fissi come nel codice Java
                    e.domain_typed = False
                    e.domain_mandatory = True
                    e.range_typed = False
                    e.range_mandatory = True
                    d.edges.append(e)
            if not self.ontology.getDataPropertyAssertionAxioms(s).isEmpty():
                cie = ClassInstanceEntity(
                    fullIri=str(s.getIRI().toString()),
                    dataProperties=[]
                )
                for dpa in self.ontology.getDataPropertyAssertionAxioms(s):
                    dpi = DataPropertyValue(
                        iri=str(dpa.getProperty().asOWLDataProperty().getIRI().toString()),
                        value=str(dpa.getObject().getLiteral()),
                        language=str(dpa.getObject().getLang())
                    )
                    cie.data_properties.append(dpi)
                rdf_graph.class_instance_entities.append(cie)

        # 12. Rimuove il diagramma delle annotazioni se vuoto
        # if not d2.nodes:
        # FIX 16: remove always
        rdf_graph.diagrams.pop(1)

        return rdf_graph


def parse_ontology(owl_file: bytes):
    return (OWLManager.createOWLOntologyManager()
            .loadOntologyFromOntologyDocument(ByteArrayInputStream(owl_file)))
