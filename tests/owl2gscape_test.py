import json
from pathlib import Path

from ai_assistant.jvm.java import *
from ai_assistant.jvm.owlapi import *

from ai_assistant.server.models.edge import Edge
from ai_assistant.server.models.rdf_graph import RDFGraph
from ai_assistant.owl import OWL2Gscape


class TestOWL2RdfGraph:
    # Percorso base per le risorse del test (adatta al tuo ambiente)
    RESOURCES_DIR = Path("tests/resources")

    # ----------------------------------------------------------------------
    ## Test 1: Conversione Completa (Verifica di parità JSON)
    # ----------------------------------------------------------------------
    def test_convert(self):
        manager = OWLManager.createOWLOntologyManager()

        # 1. Carica l'Ontologia (Necessita del file Books.owl nel CLASSPATH o percorso)
        owl_file_path = self.RESOURCES_DIR / "books.owl"
        if not owl_file_path.exists():
            raise RuntimeError(f"File risorsa non trovato: {owl_file_path}")

        # JPype non gestisce bene Files.readAllBytes e Paths.get direttamente come in Java
        # Carichiamo il file usando un approccio Python standard e poi lo passiamo
        with open(owl_file_path, 'rb') as f:
            owl_bytes = f.read()

        owl_is = ByteArrayInputStream(owl_bytes)
        o: OWLOntology = manager.loadOntologyFromOntologyDocument(owl_is)

        # 2. Conversione da OWL a RDFGraph
        converted: RDFGraph = OWL2Gscape(o).owl_to_rdf_graph()

        # 3. Carica il file RDFGraph atteso (json)
        expected_json_path = self.RESOURCES_DIR / "books.json"
        if not expected_json_path.exists():
            raise RuntimeError(f"File risorsa attesa non trovato: {expected_json_path}")

        # In Python usiamo la libreria json standard
        with open(expected_json_path, 'rb') as f:
            expected: RDFGraph = RDFGraph.from_dict(json.load(f))

        assert len(expected.diagrams[0].nodes) == len(converted.diagrams[0].nodes)
        assert len(expected.diagrams[0].edges) == len(converted.diagrams[0].edges)
        assert len(expected.entities) == len(converted.entities)

    def test_convert_CLV(self):
        manager = OWLManager.createOWLOntologyManager()

        owl_file_path = self.RESOURCES_DIR / "CLV.owl"
        if not owl_file_path.exists():
            raise RuntimeError(f"File risorsa non trovato: {owl_file_path}")

        with open(owl_file_path, 'rb') as f:
            owl_bytes = f.read()

        owl_is = ByteArrayInputStream(owl_bytes)
        o: OWLOntology = manager.loadOntologyFromOntologyDocument(owl_is)

        converted: RDFGraph = OWL2Gscape(o).owl_to_rdf_graph()
        converted_entities_annotations = 0
        owl_entities_annotations = 0
        for e in converted.entities:
            if e.annotations is not None: converted_entities_annotations += len(e.annotations)
            owl_annotations = o.getAnnotationAssertionAxioms(IRI.create(e.full_iri))
            if owl_annotations is not None: owl_entities_annotations += len(owl_annotations)

        assert converted_entities_annotations == owl_entities_annotations
        assert len(converted.metadata.annotations) == len(o.getAnnotations())

    # ----------------------------------------------------------------------
    ## Funzione di utilità per creare Ontologie vuote
    # ----------------------------------------------------------------------
    def create_ontology_with_axiom(self, axiom: OWLAxiom) -> OWLOntology:
        man = OWLManager.createOWLOntologyManager()
        o: OWLOntology = man.createOntology()
        o.addAxiom(axiom)
        return o

    # ----------------------------------------------------------------------
    ## Test 2: Data Property - Partecipazione e Tipizzazione (Equivalenza)
    # C <=> ∃OP.xsd:string
    # Aspettato: isDomainTyped=True, isDomainMandatory=True
    # ----------------------------------------------------------------------
    def test_convert_data_property_participation_and_typing(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: C EquivalentTo DataSomeValuesFrom(OP, xsd:string)
        axiom = df.getOWLEquivalentClassesAxiom([
            df.getOWLClass(IRI.create("C")),
            df.getOWLDataSomeValuesFrom(df.getOWLDataProperty(IRI.create("OP")),
                                        OWL2Datatype.XSD_STRING.getDatatype(df))
        ])
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == True

    # ----------------------------------------------------------------------
    ## Test 3: Data Property - Tipizzazione (Dominio)
    # DataPropertyDomain(OP, C)
    # Aspettato: isDomainTyped=True, isDomainMandatory=False
    # ----------------------------------------------------------------------
    def test_convert_data_property_typing(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: DataPropertyDomain(OP, C)
        axiom = df.getOWLDataPropertyDomainAxiom(
            df.getOWLDataProperty(IRI.create("OP")),
            df.getOWLClass(IRI.create("C"))
        )
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == False

    # ----------------------------------------------------------------------
    ## Test 4: Data Property - Partecipazione (Sottoclasse)
    # C SubClassOf ∃OP.xsd:string
    # Aspettato: isDomainTyped=False, isDomainMandatory=True
    # ----------------------------------------------------------------------
    def test_convert_data_property_participation(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: C SubClassOf DataSomeValuesFrom(OP, xsd:string)
        axiom = df.getOWLSubClassOfAxiom(
            df.getOWLClass(IRI.create("C")),
            df.getOWLDataSomeValuesFrom(df.getOWLDataProperty(IRI.create("OP")),
                                        OWL2Datatype.XSD_STRING.getDatatype(df))
        )
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == False
        assert convertedEdge.domain_mandatory == True

    # ----------------------------------------------------------------------
    ## Test 5: Object Property - Dominio TP (Equivalenza)
    # C <=> ∃OP.Thing
    # Aspettato: isDomainTyped=True, isDomainMandatory=True
    # ----------------------------------------------------------------------
    def test_convert_object_property_domain_participation_and_typing(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: C EquivalentTo ObjectSomeValuesFrom(OP, Thing)
        axiom = df.getOWLEquivalentClassesAxiom([
            df.getOWLClass(IRI.create("C")),
            df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
        ])
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == True

    # ----------------------------------------------------------------------
    ## Test 6: Object Property - Dominio T (Dominio)
    # ObjectPropertyDomain(OP, C)
    # Aspettato: isDomainTyped=True, isDomainMandatory=False
    # ----------------------------------------------------------------------
    def test_convert_object_property_domain_typing(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: ObjectPropertyDomain(OP, C)
        axiom = df.getOWLObjectPropertyDomainAxiom(
            df.getOWLObjectProperty(IRI.create("OP")),
            df.getOWLClass(IRI.create("C"))
        )
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == False

    # ----------------------------------------------------------------------
    ## Test 7: Object Property - Dominio P (Sottoclasse)
    # C SubClassOf ∃OP.Thing
    # Aspettato: isDomainTyped=False, isDomainMandatory=True
    # ----------------------------------------------------------------------
    def test_convert_object_property_domain_participation(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: C SubClassOf ObjectSomeValuesFrom(OP, Thing)
        axiom = df.getOWLSubClassOfAxiom(
            df.getOWLClass(IRI.create("C")),
            df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
        )
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == False
        assert convertedEdge.domain_mandatory == True

    # ----------------------------------------------------------------------
    ## Test 8: Object Property - Range TP (Equivalenza Inversa)
    # C <=> ∃OP⁻¹.Thing
    # Aspettato: isRangeTyped=True, isRangeMandatory=True
    # ----------------------------------------------------------------------
    def test_convert_object_property_range_participation_and_typing(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: C EquivalentTo ObjectSomeValuesFrom(inverse(OP), Thing)
        axiom = df.getOWLEquivalentClassesAxiom([
            df.getOWLClass(IRI.create("C")),
            df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                          df.getOWLThing())
        ])
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == True

    # ----------------------------------------------------------------------
    ## Test 9: Object Property - Range T (Range)
    # ObjectPropertyRange(OP, C)
    # Aspettato: isRangeTyped=True, isRangeMandatory=False
    # ----------------------------------------------------------------------
    def test_convert_object_property_range_typing(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: ObjectPropertyRange(OP, C)
        axiom = df.getOWLObjectPropertyRangeAxiom(
            df.getOWLObjectProperty(IRI.create("OP")),
            df.getOWLClass(IRI.create("C"))
        )
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == False

    # ----------------------------------------------------------------------
    ## Test 10: Object Property - Range P (Sottoclasse Inversa)
    # C SubClassOf ∃OP⁻¹.Thing
    # Aspettato: isRangeTyped=False, isRangeMandatory=True
    # ----------------------------------------------------------------------
    def test_convert_object_property_range_participation(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()

        # Assioma: C SubClassOf ObjectSomeValuesFrom(inverse(OP), Thing)
        axiom = df.getOWLSubClassOfAxiom(
            df.getOWLClass(IRI.create("C")),
            df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                          df.getOWLThing())
        )
        o = self.create_ontology_with_axiom(axiom)

        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.range_typed == False
        assert convertedEdge.range_mandatory == True

    # ----------------------------------------------------------------------
    ## Test 11-19: Combinazioni di Dominio (T, P, TP) e Range (T, P, TP)
    # ----------------------------------------------------------------------

    # Utilità per aggiungere assiomi multipli
    def create_ontology_with_axioms(self, axioms):
        man = OWLManager.createOWLOntologyManager()
        o = man.createOntology()
        for axiom in axioms:
            o.addAxiom(axiom)
        return o

    # TP_TP: Dominio(TP) e Range(TP)
    # Aspettato: DT=True, DM=True, RT=True, RM=True
    def test_convert_object_property_tp_tp(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio TP: C1 <=> ∃OP.Thing
            df.getOWLEquivalentClassesAxiom([
                df.getOWLClass(IRI.create("C1")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
            ]),
            # Range TP: C2 <=> ∃OP⁻¹.Thing
            df.getOWLEquivalentClassesAxiom([
                df.getOWLClass(IRI.create("C2")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                              df.getOWLThing())
            ])
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == True
        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == True

    # TP_T: Dominio(TP) e Range(T)
    # Aspettato: DT=True, DM=True, RT=True, RM=False
    def test_convert_object_property_tp_t(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio TP: C1 <=> ∃OP.Thing
            df.getOWLEquivalentClassesAxiom([
                df.getOWLClass(IRI.create("C1")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
            ]),
            # Range T: ObjectPropertyRange(OP, C2)
            df.getOWLObjectPropertyRangeAxiom(
                df.getOWLObjectProperty(IRI.create("OP")),
                df.getOWLClass(IRI.create("C2"))
            )
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == True
        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == False

    # TP_P: Dominio(TP) e Range(P)
    # Aspettato: DT=True, DM=True, RT=False, RM=True
    def test_convert_object_property_tp_p(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio TP: C1 <=> ∃OP.Thing
            df.getOWLEquivalentClassesAxiom([
                df.getOWLClass(IRI.create("C1")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
            ]),
            # Range P: C2 SubClassOf ∃OP⁻¹.Thing
            df.getOWLSubClassOfAxiom(
                df.getOWLClass(IRI.create("C2")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                              df.getOWLThing())
            )
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == True
        assert convertedEdge.range_typed == False
        assert convertedEdge.range_mandatory == True

    # T_TP: Dominio(T) e Range(TP)
    # Aspettato: DT=True, DM=False, RT=True, RM=True
    def test_convert_object_property_t_tp(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio T: ObjectPropertyDomain(OP, C1)
            df.getOWLObjectPropertyDomainAxiom(
                df.getOWLObjectProperty(IRI.create("OP")),
                df.getOWLClass(IRI.create("C1"))
            ),
            # Range TP: C2 <=> ∃OP⁻¹.Thing
            df.getOWLEquivalentClassesAxiom([
                df.getOWLClass(IRI.create("C2")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                              df.getOWLThing())
            ])
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == False
        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == True

    # T_T: Dominio(T) e Range(T)
    # Aspettato: DT=True, DM=False, RT=True, RM=False
    def test_convert_object_property_t_t(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio T: ObjectPropertyDomain(OP, C1)
            df.getOWLObjectPropertyDomainAxiom(
                df.getOWLObjectProperty(IRI.create("OP")),
                df.getOWLClass(IRI.create("C1"))
            ),
            # Range T: ObjectPropertyRange(OP, C2)
            df.getOWLObjectPropertyRangeAxiom(
                df.getOWLObjectProperty(IRI.create("OP")),
                df.getOWLClass(IRI.create("C2"))
            )
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == False
        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == False

    # T_P: Dominio(T) e Range(P)
    # Aspettato: DT=True, DM=False, RT=False, RM=True
    def test_convert_object_property_t_p(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio T: ObjectPropertyDomain(OP, C1)
            df.getOWLObjectPropertyDomainAxiom(
                df.getOWLObjectProperty(IRI.create("OP")),
                df.getOWLClass(IRI.create("C1"))
            ),
            # Range P: C2 SubClassOf ∃OP⁻¹.Thing
            df.getOWLSubClassOfAxiom(
                df.getOWLClass(IRI.create("C2")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                              df.getOWLThing())
            )
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == True
        assert convertedEdge.domain_mandatory == False
        assert convertedEdge.range_typed == False
        assert convertedEdge.range_mandatory == True

    # P_TP: Dominio(P) e Range(TP)
    # Aspettato: DT=False, DM=True, RT=True, RM=True
    def test_convert_object_property_p_tp(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio P: C1 SubClassOf ∃OP.Thing
            df.getOWLSubClassOfAxiom(
                df.getOWLClass(IRI.create("C1")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
            ),
            # Range TP: C2 <=> ∃OP⁻¹.Thing
            df.getOWLEquivalentClassesAxiom([
                df.getOWLClass(IRI.create("C2")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                              df.getOWLThing())
            ])
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == False
        assert convertedEdge.domain_mandatory == True
        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == True

    # P_T: Dominio(P) e Range(T)
    # Aspettato: DT=False, DM=True, RT=True, RM=False
    def test_convert_object_property_p_t(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio P: C1 SubClassOf ∃OP.Thing
            df.getOWLSubClassOfAxiom(
                df.getOWLClass(IRI.create("C1")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
            ),
            # Range T: ObjectPropertyRange(OP, C2)
            df.getOWLObjectPropertyRangeAxiom(
                df.getOWLObjectProperty(IRI.create("OP")),
                df.getOWLClass(IRI.create("C2"))
            )
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == False
        assert convertedEdge.domain_mandatory == True
        assert convertedEdge.range_typed == True
        assert convertedEdge.range_mandatory == False

    # P_P: Dominio(P) e Range(P)
    # Aspettato: DT=False, DM=True, RT=False, RM=True
    def test_convert_object_property_p_p(self):
        df: OWLDataFactory = OWLManager.getOWLDataFactory()
        axioms = [
            # Dominio P: C1 SubClassOf ∃OP.Thing
            df.getOWLSubClassOfAxiom(
                df.getOWLClass(IRI.create("C1")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectProperty(IRI.create("OP")), df.getOWLThing())
            ),
            # Range P: C2 SubClassOf ∃OP⁻¹.Thing
            df.getOWLSubClassOfAxiom(
                df.getOWLClass(IRI.create("C2")),
                df.getOWLObjectSomeValuesFrom(df.getOWLObjectInverseOf(df.getOWLObjectProperty(IRI.create("OP"))),
                                              df.getOWLThing())
            )
        ]
        o = self.create_ontology_with_axioms(axioms)
        converted = OWL2Gscape(o).owl_to_rdf_graph()
        convertedEdge: Edge = converted.diagrams[0].edges[0]

        assert convertedEdge.domain_typed == False
        assert convertedEdge.domain_mandatory == True
        assert convertedEdge.range_typed == False
        assert convertedEdge.range_mandatory == True
