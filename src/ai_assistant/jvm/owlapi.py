# coding: utf-8

"""Wrapper for OWLAPI imported through the JVM."""

from ..jvm import startJVM
from ..logging import logger

__all__ = []

try:
    # Make sure JVM is running before performing imports
    startJVM()

    # Import used owlapi interface in this module scope
    import org.semanticweb.owlapi.apibinding.OWLManager as OWLManager
    import org.semanticweb.owlapi.formats.FunctionalSyntaxDocumentFormat as FunctionalSyntaxDocumentFormat
    import org.semanticweb.owlapi.formats.RDFXMLDocumentFormat as RDFXMLDocumentFormat
    import org.semanticweb.owlapi.formats.TurtleDocumentFormat as TurtleDocumentFormat
    import org.semanticweb.owlapi.formats.PrefixDocumentFormat as PrefixDocumentFormat
    import org.semanticweb.owlapi.io.StringDocumentTarget as StringDocumentTarget
    import org.semanticweb.owlapi.model.AddOntologyAnnotation as AddOntologyAnnotation
    import org.semanticweb.owlapi.model.IRI as IRI
    import org.semanticweb.owlapi.model.OWLAnnotation as OWLAnnotation
    import org.semanticweb.owlapi.model.OWLAnnotationProperty as OWLAnnotationProperty
    import org.semanticweb.owlapi.model.OWLAnnotationValue as OWLAnnotationValue
    import org.semanticweb.owlapi.model.OWLAxiom as OWLAxiom
    import org.semanticweb.owlapi.model.OWLClass as OWLClass
    import org.semanticweb.owlapi.model.OWLClassExpression as OWLClassExpression
    import org.semanticweb.owlapi.model.OWLDataFactory as OWLDataFactory
    import org.semanticweb.owlapi.model.OWLDataPropertyExpression as OWLDataPropertyExpression
    import org.semanticweb.owlapi.model.OWLEntity as OWLEntity
    import org.semanticweb.owlapi.model.OWLIndividual as OWLIndividual
    import org.semanticweb.owlapi.model.OWLNamedIndividual as OWLNamedIndividual
    import org.semanticweb.owlapi.model.OWLObjectPropertyExpression as OWLObjectPropertyExpression
    import org.semanticweb.owlapi.model.OWLOntology as OWLOntology
    import org.semanticweb.owlapi.model.OWLOntologyID as OWLOntologyID
    import org.semanticweb.owlapi.model.OWLOntologyManager as OWLOntologyManager
    import org.semanticweb.owlapi.vocab.OWL2Datatype as OWL2Datatype
    import org.semanticweb.owlapi.model.OWLAnnotationAssertionAxiom as OWLAnnotationAssertionAxiom
    import org.semanticweb.owlapi.model.OWLObjectProperty as OWLObjectProperty
    import org.semanticweb.owlapi.model.OWLDataProperty as OWLDataProperty
    import org.semanticweb.owlapi.model.OWLObjectSomeValuesFrom as OWLObjectSomeValuesFrom
    import org.semanticweb.owlapi.model.OWLDataSomeValuesFrom as OWLDataSomeValuesFrom
    import org.semanticweb.owlapi.model.OWLObjectInverseOf as OWLObjectInverseOf
    import org.semanticweb.owlapi.model.OWLObjectUnionOf as OWLObjectUnionOf
    import org.semanticweb.owlapi.model.OWLLiteral as OWLLiteral
    import org.semanticweb.owlapi.model.parameters.Imports as Imports
    import org.semanticweb.owlapi.model.OWLDataRange as OWLDataRange
    import org.semanticweb.owlapi.model.OWLDatatype as OWLDatatype
    import org.semanticweb.owlapi.model.OWLDataPropertyRangeAxiom as OWLDataPropertyRangeAxiom
    import org.semanticweb.owlapi.model.OWLEquivalentClassesAxiom as OWLEquivalentClassesAxiom
    import org.semanticweb.owlapi.model.OWLSubClassOfAxiom as OWLSubClassOfAxiom
    import org.semanticweb.owlapi.model.OWLDisjointUnionAxiom as OWLDisjointUnionAxiom
    import org.semanticweb.owlapi.model.OWLClassAssertionAxiom as OWLClassAssertionAxiom
    import org.semanticweb.owlapi.model.OWLObjectPropertyDomainAxiom as OWLObjectPropertyDomainAxiom
    import org.semanticweb.owlapi.model.OWLObjectPropertyRangeAxiom as OWLObjectPropertyRangeAxiom
    import org.semanticweb.owlapi.model.OWLDataPropertyDomainAxiom as OWLDataPropertyDomainAxiom

    __all__ += [
        "AddOntologyAnnotation",
        "FunctionalSyntaxDocumentFormat",
        "RDFXMLDocumentFormat",
        "TurtleDocumentFormat",
        "IRI",
        "OWL2Datatype",
        "OWLAnnotation",
        "OWLAnnotationProperty",
        "OWLAnnotationValue",
        "OWLAxiom",
        "OWLClass",
        "OWLClassExpression",
        "OWLDataFactory",
        "OWLDataPropertyExpression",
        "OWLEntity",
        "OWLIndividual",
        "OWLNamedIndividual",
        "OWLManager",
        "OWLObjectPropertyExpression",
        "OWLOntology",
        "OWLOntologyID",
        "OWLOntologyManager",
        "PrefixDocumentFormat",
        "StringDocumentTarget",
        "OWLAnnotationAssertionAxiom",
        "OWLObjectProperty",
        "OWLDataProperty",
        "OWLObjectSomeValuesFrom",
        "OWLDataSomeValuesFrom",
        "OWLObjectInverseOf",
        "OWLObjectUnionOf",
        "OWLLiteral",
        "Imports",
        "OWLDataRange",
        "OWLDatatype",
        "OWLDataPropertyRangeAxiom",
        "OWLEquivalentClassesAxiom",
        "OWLSubClassOfAxiom",
        "OWLDisjointUnionAxiom",
        "OWLClassAssertionAxiom",
        "OWLObjectPropertyDomainAxiom",
        "OWLObjectPropertyRangeAxiom",
        "OWLDataPropertyDomainAxiom",
    ]
except TypeError as e:
    logger.error("Cannot start JVM", e)