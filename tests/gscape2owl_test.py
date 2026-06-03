from ai_assistant.jvm.owlapi import *

from ai_assistant.server.models.diagram import Diagram
from ai_assistant.server.models.edge import Edge
from ai_assistant.server.models.function_properties_enum import FunctionPropertiesEnum
from ai_assistant.server.models.grapholscape_entity import GrapholscapeEntity
from ai_assistant.server.models.node import Node
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.server.models.rdf_graph_metadata import RDFGraphMetadata
from ai_assistant.server.models.types_enum import TypesEnum
from ai_assistant.gscape import rdf_graph_to_owl

# Assumiamo che le classi del modello (RDFGraph, Node, Edge, TypesEnum, FunctionPropertiesEnum, ecc.)
# e le importazioni JPype (IRI, JOWLClassImpl, ecc.) siano già disponibili.

class TestGscape2OWL:

    # --- Utilità per la creazione del grafo base ---
    @staticmethod
    def create_base_graph() -> RDFGraph:
        """Crea la struttura base RDFGraph per i test."""
        metadata = RDFGraphMetadata(
            iri="https://obdasystems.com/ontologies/test/",
            version="https://obdasystems.com/ontologies/test/1.0",
            namespaces=[]
        )
        return RDFGraph(metadata=metadata, diagrams=[], entities=[], modelType='ontology')

    # ----------------------------------------------------------------------
    ## Test 1: Dichiarazioni (Re-incluso per completezza)
    # ----------------------------------------------------------------------
    def test_declarations(self):
        rdfGraph = self.create_base_graph()
        diagram = Diagram(
            id=0,
            name='',
            nodes=[],
            edges=[],
        )
        rdfGraph.diagrams.append(diagram)

        # Node Class (c)
        c = Node(id="n0", type=TypesEnum.CLASS, iri="https://obdasystems.com/ontologies/test/C")
        diagram.nodes.append(c)

        # Node Data Property (dp) - ID assegnato al volo
        iri_dp = "https://obdasystems.com/ontologies/test/dp"
        dp = Node(id="n1", type=TypesEnum.DATA_MINUS_PROPERTY, iri=iri_dp)
        diagram.nodes.append(dp)

        # Edge Object Property (op)
        op_edge = Edge(
            id="e0",
            sourceId="n0",
            targetId="n0",
            iri="https://obdasystems.com/ontologies/test/op",
            type=TypesEnum.OBJECT_MINUS_PROPERTY
        )
        diagram.edges.append(op_edge)

        o = rdf_graph_to_owl(rdfGraph)

        assert o.getClassesInSignature().size() == 1
        assert o.getObjectPropertiesInSignature().size() == 1
        assert o.getDataPropertiesInSignature().size() == 1

    # ----------------------------------------------------------------------
    ## Test 2: Gerarchie (Union/Disjoint Union)
    # ----------------------------------------------------------------------
    def test_hierarchies(self):
        rdfGraph = self.create_base_graph()
        diagram = Diagram(
            id=0,
            name="",
            nodes=[],
            edges=[]
        )
        rdfGraph.diagrams.append(diagram)

        # IRIs
        iriRoot = "https://obdasystems.com/ontologies/test/Root"
        iriChild2 = "https://obdasystems.com/ontologies/test/Child2"
        iriGrandChild1 = "https://obdasystems.com/ontologies/test/grandChild1"

        # Nodi
        root = Node(id="n0", type=TypesEnum.CLASS, iri=iriRoot)
        du = Node(id="du", type=TypesEnum.COMPLETE_MINUS_DISJOINT_MINUS_UNION)
        child1 = Node(id="n1", type=TypesEnum.CLASS, iri="https://obdasystems.com/ontologies/test/Child1")
        child2 = Node(id="n2", type=TypesEnum.CLASS, iri=iriChild2)
        du1 = Node(id="du1", type=TypesEnum.DISJOINT_MINUS_UNION)
        grandChild1 = Node(id="n3", type=TypesEnum.CLASS, iri=iriGrandChild1)
        grandChild2 = Node(id="n4", type=TypesEnum.CLASS, iri="https://obdasystems.com/ontologies/test/grandChild2")

        diagram.nodes.append(root)
        diagram.nodes.append(du)
        diagram.nodes.append(child1)
        diagram.nodes.append(child2)
        diagram.nodes.append(du1)
        diagram.nodes.append(grandChild1)
        diagram.nodes.append(grandChild2)

        # Bordi (Completa Disgiunzione principale)
        e1 = Edge(
            id="e1",
            sourceId="du",
            targetId="n0",
            type=TypesEnum.COMPLETE_MINUS_DISJOINT_MINUS_UNION,
        )
        e2 = Edge(id='e2', sourceId="n1", targetId="du", type=TypesEnum.INPUT)
        e3 = Edge(id='e3', sourceId="n2", targetId="du", type=TypesEnum.INPUT)
        diagram.edges.append(e1)
        diagram.edges.append(e2)
        diagram.edges.append(e3)

        # Bordi (Disgiunzione secondaria)
        e4 = Edge(id="e4", sourceId="du1", targetId="n2", type=TypesEnum.DISJOINT_MINUS_UNION)
        e5 = Edge(id="e5", sourceId="n3", targetId="du1", type=TypesEnum.INPUT)
        e6 = Edge(id="e6", sourceId="n4", targetId="du1", type=TypesEnum.INPUT)
        diagram.edges.append(e4)
        diagram.edges.append(e5)
        diagram.edges.append(e6)

        o = rdf_graph_to_owl(rdfGraph)

        # IRIs Java per le asserzioni
        classRoot = OWLManager.getOWLDataFactory().getOWLClass(IRI.create(iriRoot))
        classChild2 = OWLManager.getOWLDataFactory().getOWLClass(IRI.create(iriChild2))
        classGrandChild1 = OWLManager.getOWLDataFactory().getOWLClass(IRI.create(iriGrandChild1))

        # Asserzioni
        assert o.getClassesInSignature().size() == 5
        assert o.getLogicalAxiomCount() == 7

        # Child2 deve avere SubClassAxioms (dall'Unione)
        assert isinstance(o.getSubClassAxiomsForSuperClass(classChild2).iterator().next().getSubClass(), OWLClass)

        assert o.getDisjointClassesAxioms(classChild2).size() == 1
        assert o.getDisjointClassesAxioms(classGrandChild1).size() == 1
        assert o.getEquivalentClassesAxioms(classRoot).size() == 1

    # ----------------------------------------------------------------------
    ## Test 3: Proprietà Dati (Funzionalità e Mandatory)
    # ----------------------------------------------------------------------
    def test_data_properties(self):
        rdfGraph = self.create_base_graph()
        diagram = Diagram(
            id=0,
            name="",
            nodes=[],
            edges=[])
        rdfGraph.diagrams.append(diagram)

        # IRIs
        iriC = "https://obdasystems.com/ontologies/test/C"
        iriDP = "https://obdasystems.com/ontologies/test/dp"
        iriFunc = "https://obdasystems.com/ontologies/test/functional"

        # Nodi
        c = Node(id="n0", type=TypesEnum.CLASS, iri=iriC)
        dp = Node(id="dp", type=TypesEnum.DATA_MINUS_PROPERTY, iri=iriDP)
        func = Node(id="f", type=TypesEnum.DATA_MINUS_PROPERTY, iri=iriFunc)
        diagram.nodes.append(c)
        diagram.nodes.append(dp)
        diagram.nodes.append(func)

        # Bordi
        edge = Edge(id="e0", sourceId="n0", targetId="dp", type=TypesEnum.ATTRIBUTE_MINUS_EDGE)
        edge.domain_mandatory=True
        edge2 = Edge(id="e1", sourceId="n0", targetId="f", type=TypesEnum.ATTRIBUTE_MINUS_EDGE)
        diagram.edges.append(edge)
        diagram.edges.append(edge2)

        # Entità (Per definire la Proprietà Funzionale)
        entity_func = GrapholscapeEntity(fullIri=iriFunc)
        entity_func.is_data_property_functional=True
        rdfGraph.entities.append(entity_func)

        o = rdf_graph_to_owl(rdfGraph)

        # IRIs Java per le asserzioni
        owlDP = OWLManager.getOWLDataFactory().getOWLDataProperty(IRI.create(iriDP))
        owlFunc = OWLManager.getOWLDataFactory().getOWLDataProperty(IRI.create(iriFunc))
        owlC = OWLManager.getOWLDataFactory().getOWLClass(IRI.create(iriC))

        # Asserzioni
        assert o.getClassesInSignature().size() == 1
        assert o.getDataPropertiesInSignature().size() == 2
        assert o.getFunctionalDataPropertyAxioms(owlFunc).size() == 1
        assert o.getFunctionalDataPropertyAxioms(owlDP).size() == 0

        # Verifica della restrizione Mandatory (OWLDataSomeValuesFrom)
        subclass_axiom = o.getSubClassAxiomsForSubClass(owlC).iterator().next()
        super_class = subclass_axiom.getSuperClass()
        assert isinstance(super_class, OWLDataSomeValuesFrom)
        assert super_class.getProperty().equals(owlDP)

    # ----------------------------------------------------------------------
    ## Test 4: Proprietà Oggetto (Funzionalità e Partecipazione)
    # ----------------------------------------------------------------------
    def test_object_properties(self):
        rdfGraph = self.create_base_graph()
        diagram = Diagram(
            id=0,
            name="",
            nodes=[],
            edges=[]
        )
        rdfGraph.diagrams.append(diagram)

        # IRIs
        iriA = "https://obdasystems.com/ontologies/test/A"
        iriB = "https://obdasystems.com/ontologies/test/B"
        iriFunc = "https://obdasystems.com/ontologies/test/functional"
        iriInvFunc = "https://obdasystems.com/ontologies/test/inv_functional"
        iriSym = "https://obdasystems.com/ontologies/test/symmetric"
        iriAsym = "https://obdasystems.com/ontologies/test/asymmetric"
        iriTrans = "https://obdasystems.com/ontologies/test/transitive"
        iriPart = "https://obdasystems.com/ontologies/test/participated"

        # Nodi
        a = Node(id="a", type=TypesEnum.CLASS, iri=iriA)
        b = Node(id="b", type=TypesEnum.CLASS, iri=iriB)
        diagram.nodes.append(a)
        diagram.nodes.append(b)

        # Bordi e Entità (per le proprietà strutturali)
        props = [
            (iriFunc, FunctionPropertiesEnum.FUNCTIONAL),
            (iriInvFunc, FunctionPropertiesEnum.INVERSEFUNCTIONAL),
            (iriSym, FunctionPropertiesEnum.SYMMETRIC),
            (iriAsym, FunctionPropertiesEnum.ASYMMETRIC),
            (iriTrans, FunctionPropertiesEnum.TRANSITIVE),
        ]

        for iri, prop_enum in props:
            edge = Edge(id="e0", iri=iri, sourceId="a", targetId="b", type=TypesEnum.OBJECT_MINUS_PROPERTY)
            diagram.edges.append(edge)
            # Simula l'oggetto Entity usando il costruttore se supportato o un oggetto con attributi
            entity = GrapholscapeEntity(fullIri=iri)
            entity.function_properties = [prop_enum]
            rdfGraph.entities.append(entity)

        # Bordo Partecipato (Mandatory Domain/Range)
        e6 = Edge(
            id="e6",
            iri=iriPart,
            sourceId="a",
            targetId="b",
            type=TypesEnum.OBJECT_MINUS_PROPERTY,
        )
        e6.domain_typed = False
        e6.domain_mandatory = True
        e6.range_typed = False
        e6.range_mandatory = True
        diagram.edges.append(e6)

        o = rdf_graph_to_owl(rdfGraph)

        # IRIs Java per le asserzioni
        owlA = OWLManager.getOWLDataFactory().getOWLClass(IRI.create(iriA))
        owlB = OWLManager.getOWLDataFactory().getOWLClass(IRI.create(iriB))
        owlFunc = OWLManager.getOWLDataFactory().getOWLObjectProperty(IRI.create(iriFunc))
        owlInvFunc = OWLManager.getOWLDataFactory().getOWLObjectProperty(IRI.create(iriInvFunc))
        owlSym = OWLManager.getOWLDataFactory().getOWLObjectProperty(IRI.create(iriSym))
        owlAsym = OWLManager.getOWLDataFactory().getOWLObjectProperty(IRI.create(iriAsym))
        owlTrans = OWLManager.getOWLDataFactory().getOWLObjectProperty(IRI.create(iriTrans))
        owlPart = OWLManager.getOWLDataFactory().getOWLObjectProperty(IRI.create(iriPart))

        # Asserzioni
        assert o.getClassesInSignature().size() == 3
        assert o.getObjectPropertiesInSignature().size() == 6
        assert o.getFunctionalObjectPropertyAxioms(owlFunc).size() == 1
        assert o.getInverseFunctionalObjectPropertyAxioms(owlInvFunc).size() == 1
        assert o.getSymmetricObjectPropertyAxioms(owlSym).size() == 1
        assert o.getAsymmetricObjectPropertyAxioms(owlAsym).size() == 1
        assert o.getTransitiveObjectPropertyAxioms(owlTrans).size() == 1

        # Verifica restrizione Mandatory Domain (A)
        subclass_a = o.getSubClassAxiomsForSubClass(owlA).iterator().next().getSuperClass()
        assert isinstance(subclass_a, OWLObjectSomeValuesFrom)
        assert subclass_a.getProperty().equals(owlPart)

        # Verifica restrizione Mandatory Range (B)
        subclass_b = o.getSubClassAxiomsForSubClass(owlB).iterator().next().getSuperClass()
        assert isinstance(subclass_b, OWLObjectSomeValuesFrom)
        # Deve essere uguale a OWLObjectInverseOf(owlPart)
        assert subclass_b.getProperty().equals(OWLManager.getOWLDataFactory().getOWLObjectInverseOf(owlPart))
