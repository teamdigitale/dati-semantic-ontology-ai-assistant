from typing import Dict, Set, List, Optional

from .gscape import RDFS_LITERAL
from .jvm.java import *
from .jvm.owlapi import *
from .server.models.class_instance_entity import ClassInstanceEntity
from .server.models.data_property_value import DataPropertyValue
from .server.models.function_properties_enum import FunctionPropertiesEnum
from .server.models.mwsx_metadata_object import MWSXMetadataObject
from .server.models.mwsx_metadata_triple import MWSXMetadataTriple
from .server.models.mwsx_ontology_catalog_ontology_metadata_set import MWSXOntologyCatalogOntologyMetadataSet
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
    acceptedAxioms: set = set()

    # Metodi di utilità (statici in Java)

    def __init__(self, ontology: OWLOntology):
        self.ontology = ontology
        self.nodesIds = {}
        self.nodesCount = 0
        self.edgesCount = 0
        self.addedThing = False
        self.acceptedAxioms = set()

    def add_lang_to_rdfgraph_metadata(self, lang: str, rdf_graph: RDFGraph):
        metadata = rdf_graph.metadata
        if metadata.languages is None:
            metadata.languages = []
        if lang and (metadata.languages is None or lang not in metadata.languages):
            metadata.languages.append(lang)

    def get_node_id(self, te: TypesEnum, iri: Optional[str]) -> str:
        if iri is None:
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
                self.acceptedAxioms.add(dca)
                return True
        return False


    def get_disjoint_subclasses(self, exprSup: OWLClassExpression, exprSub: OWLClassExpression):
        ret = set()
        axioms_to_add = set()
        if (isinstance(exprSup, OWLClass) and isinstance(exprSub, OWLClass)):
            disjointClassesAxioms = self.ontology.getDisjointClassesAxioms(exprSub.asOWLClass())
            for disjointClassAxiom in disjointClassesAxioms:
                for disjointClass in disjointClassAxiom.getClassExpressions():
                    for sub in self.ontology.getSubClassAxiomsForSuperClass(exprSup.asOWLClass()):
                        if (isinstance(disjointClass, OWLClass)
                                and sub.getSubClass().asOWLClass().equals(disjointClass.asOWLClass())
                                and sub not in self.acceptedAxioms):
                            axioms_to_add.add(disjointClassAxiom)
                            axioms_to_add.add(sub)
                            ret.add(disjointClass.asOWLClass())
        if len(ret) > 1:
            self.acceptedAxioms.update(axioms_to_add)

        return ret


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
            complete: bool,
            axiom: OWLAxiom
    ):
        if isinstance(ce, OWLClass) and complete:
            oc: OWLClass = ce
            edge = Edge(
                type=TypesEnum.EQUIVALENCE,
                id=f"{self.edgesPrefix}{self.edgesCount}",
                sourceId=self.get_node_id(TypesEnum.CLASS, owl_class.getIRI().toString()),
                targetId=self.get_node_id(TypesEnum.CLASS, oc.getIRI().toString())
            )
            self.edgesCount += 1
            d.edges.append(edge)
            self.acceptedAxioms.add(axiom)
        # OWLObjectSomeValuesFrom (osvf)
        elif isinstance(ce, OWLObjectSomeValuesFrom):
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
                    self.acceptedAxioms.add(axiom)
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
                    self.acceptedAxioms.add(axiom)
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
                self.acceptedAxioms.add(axiom)
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
                    self.acceptedAxioms.add(axiom)

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
                self.acceptedAxioms.add(axiom)

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
        import_declarations = []
        for i in self.ontology.getImportsDeclarations():
            import_declarations.append(str(i.getIRI().toString()))
        rdf_graph = RDFGraph(
            modelType='ontology',
            metadata=metadata,
            diagrams=[],
            entities=[],
            classInstanceEntities=[],
            importDeclarations=import_declarations
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
                self.acceptedAxioms.update(self.ontology.getDeclarationAxioms(annotation.getProperty()))
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
                    self.acceptedAxioms.add(annotation)
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
                    self.acceptedAxioms.add(annotation)
            # Proprietà Dati
            if isinstance(oe, OWLDataProperty):
                prop_data = oe.asOWLDataProperty()
                # Funzionale
                fdpas: Set[OWLAxiom] = self.ontology.getFunctionalDataPropertyAxioms(prop_data)
                if not fdpas.isEmpty():
                    e.is_data_property_functional = (True)
                    self.acceptedAxioms.update(fdpas)
                # Range
                ranges: Set[OWLDataPropertyRangeAxiom] = self.ontology.getDataPropertyRangeAxioms(prop_data)
                for odpra in ranges:
                    range_expr: OWLDataRange = odpra.getRange()
                    if isinstance(range_expr, OWLDatatype):
                        e.datatype = str(range_expr.asOWLDatatype().getIRI().toString())
                        self.acceptedAxioms.add(odpra)
                        break  # Prende il primo Datatype trovato

            # Proprietà Oggetto
            if isinstance(oe, OWLObjectProperty):
                prop_object = oe.asOWLObjectProperty()
                # Aggiunge le proprietà funzionali (Java JSet.isEmpty() -> Python not JSet)
                fopas = self.ontology.getFunctionalObjectPropertyAxioms(prop_object)
                if not fopas.isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.FUNCTIONAL)
                    self.acceptedAxioms.update(fopas)
                ifopas = self.ontology.getInverseFunctionalObjectPropertyAxioms(prop_object)
                if not ifopas.isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.INVERSEFUNCTIONAL)
                    self.acceptedAxioms.update(ifopas)
                sopas = self.ontology.getSymmetricObjectPropertyAxioms(prop_object)
                if not sopas.isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.SYMMETRIC)
                    self.acceptedAxioms.update(sopas)
                aopas = self.ontology.getAsymmetricObjectPropertyAxioms(prop_object)
                if not aopas.isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.ASYMMETRIC)
                    self.acceptedAxioms.update(aopas)
                ropas = self.ontology.getReflexiveObjectPropertyAxioms(prop_object)
                if not ropas.isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.REFLEXIVE)
                    self.acceptedAxioms.update(ropas)
                iopas = self.ontology.getIrreflexiveObjectPropertyAxioms(prop_object)
                if not iopas.isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.IRREFLEXIVE)
                    self.acceptedAxioms.update(iopas)
                topas = self.ontology.getTransitiveObjectPropertyAxioms(prop_object)
                if not topas.isEmpty():
                    e.function_properties.append(FunctionPropertiesEnum.TRANSITIVE)
                    self.acceptedAxioms.update(topas)

            rdf_graph.entities.append(e)

        # Creazione dei Diagrammi
        d = Diagram(id=0, name="Ontology", nodes=[], edges=[])
        rdf_graph.diagrams.append(d)
        d2 = Diagram(id=-1, name="Annotations", nodes=[], edges=[])
        rdf_graph.diagrams.append(d2)

        # NODES
        for c in self.ontology.getClassesInSignature(Imports.EXCLUDED):
            self.acceptedAxioms.update(self.ontology.getDeclarationAxioms(c))
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
        for ax in self.ontology.getAxioms(Imports.EXCLUDED):
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
                                                                   True,  # complete = True per Equivalenza
                                                                   ax)

            # OWLSubClassOfAxiom
            elif isinstance(ax, OWLSubClassOfAxiom):
                sbco: OWLSubClassOfAxiom = ax
                exprSup = sbco.getSuperClass()
                exprSub = sbco.getSubClass()
                # DISJOINT HIERARCHIES
                disjoint_subclasses: Set[OWLAxiom] = self.get_disjoint_subclasses(exprSup, exprSub)
                if len(disjoint_subclasses) > 1:
                    self.acceptedAxioms.add(ax)
                    u = Node(
                        id=self.get_node_id(TypesEnum.DISJOINT_UNION, None),
                        type=TypesEnum.DISJOINT_UNION,
                    )
                    edge = Edge(
                        id=f"{self.edgesPrefix}{self.edgesCount}",
                        type=TypesEnum.DISJOINT_UNION,
                        sourceId=u.id,
                        targetId=self.get_node_id(TypesEnum.CLASS, exprSup.asOWLClass().getIRI().toString()),
                    )
                    self.edgesCount += 1
                    d.nodes.append(u)
                    d.edges.append(edge)

                    for n in disjoint_subclasses:
                        e = Edge(
                            id=f"{self.edgesPrefix}{self.edgesCount}",
                            type=TypesEnum.INPUT,
                            sourceId=self.get_node_id(TypesEnum.CLASS, n.asOWLClass().getIRI().toString()),
                            targetId=u.id,
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
                        False,
                        ax
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
                        False,
                        ax
                    )

            # OWLDisjointUnionAxiom
            elif isinstance(ax, OWLDisjointUnionAxiom):
                self.acceptedAxioms.add(ax)
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
                self.acceptedAxioms.add(ax)
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
        # TRANSLATE REMAINING SUBCLASSOF
        for ax in self.ontology.getAxioms(AxiomType.SUBCLASS_OF):
            if ax in self.acceptedAxioms:
                continue
            exprSup = ax.getSuperClass()
            exprSub = ax.getSubClass()
            if isinstance(exprSup, OWLClass) and isinstance(exprSub, OWLClass):
                self.acceptedAxioms.add(ax)
                e = Edge(
                    id=f"{self.edgesPrefix}{self.edgesCount}",
                    sourceId=self.get_node_id(TypesEnum.CLASS, exprSub.asOWLClass().getIRI().toString()),
                    targetId=self.get_node_id(TypesEnum.CLASS, exprSup.asOWLClass().getIRI().toString()),
                    type=TypesEnum.INCLUSION
                )
                self.edgesCount += 1
                d.edges.append(e)

        # 8. OBJECT PROPERTIES (Edges)
        for op in self.ontology.getObjectPropertiesInSignature(Imports.EXCLUDED):
            self.acceptedAxioms.update(self.ontology.getDeclarationAxioms(op))
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
                self.acceptedAxioms.add(dom)
                domain_class = dom.getDomain().asOWLClass() if dom.getDomain().isNamed() else self.thing
                domain_part.append((domain_class, TypedParticipationEnum.TYPED))
            for rng in ranges:
                self.acceptedAxioms.add(rng)
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
        for dp in self.ontology.getDataPropertiesInSignature(Imports.EXCLUDED):
            self.acceptedAxioms.update(self.ontology.getDeclarationAxioms(dp))
            n = Node(
                id= self.get_node_id(TypesEnum.DATA_PROPERTY, dp.getIRI().toString()),
                iri=str(dp.getIRI().toString()),
                type=TypesEnum.DATA_PROPERTY,
            )
            d.nodes.append(n)
            # SUB DATA PROPERTY AXIOMS
            sdpas = self.ontology.getDataSubPropertyAxiomsForSubProperty(dp)
            for sdpa in sdpas:
                sup = sdpa.getSuperProperty()
                if isinstance(sup, OWLDataProperty):
                    e = Edge(
                        id=f"{self.edgesPrefix}{self.edgesCount}",
                        sourceId=n.id,
                        targetId=self.get_node_id(TypesEnum.DATA_PROPERTY, sup.asOWLDataProperty().getIRI().toString()),
                        type=TypesEnum.INCLUSION,
                    )
                    self.edgesCount += 1
                    d.edges.append(e)
                    self.acceptedAxioms.add(sdpa)

            domains: Set[OWLDataPropertyDomainAxiom] = self.ontology.getDataPropertyDomainAxioms(dp)
            domain_data_part = domain_data_participation.get(dp)
            if domain_data_part is None: domain_data_part = []

            # Converte gli assiomi di dominio espliciti in partecipazione
            for dom in domains:
                self.acceptedAxioms.add(dom)
                domain_class = dom.getDomain().asOWLClass() if dom.getDomain().isNamed() else self.thing
                domain_data_part.append((domain_class, TypedParticipationEnum.TYPED))

            if not domain_data_part:
                domain_data_part.append((self.thing, TypedParticipationEnum.TYPED))
            dpCount = 0
            for ddp in domain_data_part:
                dpCount += 1
                source: OWLClass = ddp[0]

                if dpCount > 1:
                    # Logica per accoppiamento esistente
                    found_edges = [
                        e for e in d.edges
                        if e.type == TypesEnum.ATTRIBUTE_EDGE
                           and e.source_id == self.get_node_id(TypesEnum.CLASS, source.getIRI().toString())
                           and e.target_id == n.id
                    ]

                    if found_edges:
                        found_edge = found_edges[0]
                        found_edge.domain_typed = found_edge.domain_typed or TypedParticipationEnum.isTyped(
                            ddp[1])
                        found_edge.domain_mandatory = found_edge.domain_mandatory or TypedParticipationEnum.isParticipated(
                            ddp[1])
                        continue

                e = Edge(
                    id=f"{self.edgesPrefix}{self.edgesCount}",
                    sourceId=self.get_node_id(TypesEnum.CLASS, source.getIRI().toString()),
                    targetId=n.id,
                    type=TypesEnum.ATTRIBUTE_EDGE,
                )
                self.edgesCount += 1
                if source.equals(self.thing): self.add_thing_to_entities_and_nodes(rdf_graph, d)
                e.domain_typed = TypedParticipationEnum.isTyped(ddp[1])
                e.domain_mandatory = TypedParticipationEnum.isParticipated(ddp[1])
                d.edges.append(e)

        # 10. INDIVIDUALS (Nodi)
        for i in self.ontology.getIndividualsInSignature(Imports.EXCLUDED):
            self.acceptedAxioms.update(self.ontology.getDeclarationAxioms(i))
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
        for s in self.ontology.getIndividualsInSignature(Imports.EXCLUDED):
            for opa in self.ontology.getObjectPropertyAssertionAxioms(s):
                t: OWLIndividual = opa.getObject()
                if isinstance(t, OWLNamedIndividual):
                    self.acceptedAxioms.add(opa)
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

            dpas = self.ontology.getDataPropertyAssertionAxioms(s)
            if not dpas.isEmpty():
                self.acceptedAxioms.update(dpas)
                cie = ClassInstanceEntity(
                    fullIri=str(s.getIRI().toString()),
                    dataProperties=[]
                )
                for dpa in dpas:
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

    def get_rejected_axioms_as_ontology(self) -> OWLOntology:
        manager: OWLOntologyManager = OWLManager.createOWLOntologyManager()
        originalIRI = self.ontology.getOntologyID().getOntologyIRI().get().toString() if self.ontology.getOntologyID().getOntologyIRI().isPresent() else "http://obdasystems.com/example"
        id: OWLOntologyID = OWLOntologyID(
            IRI.create(originalIRI + "/rejectedAxioms#"),
        )
        owlOntology: OWLOntology = manager.createOntology(id)
        rejectedAxioms = HashSet(self.ontology.getAxioms())
        rejectedAxioms.removeAll(self.acceptedAxioms)
        owlOntology.addAxioms(rejectedAxioms)
        return owlOntology

    def update_metadata(self, metadata: MWSXOntologyCatalogOntologyMetadataSet | None, new_version: str | None):
        manager: OWLOntologyManager = OWLManager.createOWLOntologyManager()
        new_ontology: OWLOntology = manager.copyOntology(self.ontology, OntologyCopy.DEEP)
        ontology_iri = new_ontology.getOntologyID().getOntologyIRI()
        ontology_iri = ontology_iri.get() if ontology_iri.isPresent() else IRI.create("http://obdasystems.com/example")
        change = SetOntologyID(
            new_ontology,
            OWLOntologyID(
                ontology_iri,
                IRI.create(new_version),
            )
        )
        new_ontology.getOWLOntologyManager().applyChange(change)
        df = OWLManager.getOWLDataFactory()
        if metadata is not None:
            for tr in metadata.metadata_triples or []:
                self.remove_metadata_annotations(new_ontology, ontology_iri.toString(), tr, df)
            for tr in metadata.metadata_triples or []:
                self.add_metadata_annotations(new_ontology, ontology_iri.toString(), tr, df)
        return new_ontology

    def remove_metadata_annotations(self, ontology: OWLOntology, ontology_iri: str, triple: MWSXMetadataTriple, df: OWLDataFactory):
        predicate = triple.predicate
        annotation_property = df.getOWLAnnotationProperty(IRI.create(predicate.iri))
        subject = triple.subject
        remove_annotations = []
        if subject is not None:
            if subject.iri == ontology_iri:
                annotations = ontology.getAnnotations()
                for annotation in annotations:
                    if annotation.getProperty() == annotation_property:
                        remove_annotations.append(RemoveOntologyAnnotation(ontology, annotation))
                for remove_annotation in remove_annotations:
                    ontology.applyChange(remove_annotation)
            else:
                annotations = ontology.getAnnotationAssertionAxioms(IRI.create(subject.iri), Imports.EXCLUDED)
                for annotation in annotations:
                    if annotation.getProperty() == annotation_property:
                        remove_annotations.append(annotation)
                for remove_annotation in remove_annotations:
                    ontology.removeAxiom(remove_annotation)

    def add_metadata_annotations(self, ontology: OWLOntology, ontology_iri: str, triple: MWSXMetadataTriple, df: OWLDataFactory):
        predicate = triple.predicate
        annotation_property = df.getOWLAnnotationProperty(IRI.create(predicate.iri))
        subject = triple.subject
        object = triple.object
        filler = self.get_metadata_annotation_filler(object, df)
        if subject.iri == ontology_iri:
            ann = df.getOWLAnnotation(annotation_property, filler)
            aoa = AddOntologyAnnotation(ontology, ann)
            ontology.applyChange(aoa)
        else:
            ax = df.getOWLAnnotationAssertionAxiom(annotation_property, IRI.create(subject.iri), filler)
            ontology.addAxiom(ax)

    def get_metadata_annotation_filler(self, object: MWSXMetadataObject, df):
        if object.is_iri: return IRI.create(object.iri)
        else:
            lit: OWLLiteral
            lang = object.lang
            if lang is not None:
                lit = df.getOWLLiteral(object.value, lang)
            else:
                datatype = object.datatype_iri if object.datatype_iri is not None else RDFS_LITERAL
                lit = df.getOWLLiteral(object.value, df.getOWLDatatype(IRI.create(datatype)))
            return lit

def parse_ontology(owl_file: bytes):
    return (OWLManager.createOWLOntologyManager()
            .loadOntologyFromOntologyDocument(ByteArrayInputStream(owl_file)))
