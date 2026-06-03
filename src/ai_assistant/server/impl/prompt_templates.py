from typing import List, Optional

from ai_assistant.server.models.chart_configuration import ChartConfiguration
from ai_assistant.server.models.describe_ontology_entity_request_property_info import \
    DescribeOntologyEntityRequestPropertyInfo
from ai_assistant.server.models.text2sparql_request import Text2sparqlRequest
from ai_assistant.utils import languages


def get_individual_description_prompt(individual_name: str, context: str, individual_types: Optional[List[str]]) -> str:
    """
    Assemble a prompt for an AI LLM model to get the description
    of an individual given its name (typically its label) and the
    list of types it assigned to (typically its parent classes).
    Example: to describe the racing team Ferrari [individualName: Scuderia Ferrari, individualTypes: [Team, Organization]]

    :param individual_name: the name of the individual entity to describe
    :param context: the context, typically the ontology name
    :param individual_types: the list of rdfs:type assigned to the individual
    :return:
    """
    prompt = f'Provide a short description of the entity "{individual_name}" '
    if individual_types is not None:
        prompt += f' which is a {", and a ".join(individual_types)}'

    prompt += f' {get_context_prompt(context)}'
    return prompt


def get_entity_description_prompt(entity_name: str, entity_type: str, context: str,
                                  property_info: Optional[DescribeOntologyEntityRequestPropertyInfo]):
    """
    Assemble a prompt for an AI LLM model to get the description
    of an entity given its name (typically its label) and the
    info about its domain and range in case it's a data/object property
    :param entity_name: the name of the entity to describe
    :param entity_type: the type of the entity to describe
    :param context: the context, typically the ontology name
    :param property_info: info about domain/range in case of a property
    :return:
    """
    prompt = f'Provide a short description of the entity "{entity_name}" which is a {entity_type}'
    if entity_type == 'attribute' and property_info is not None:
        prompt += f'of {property_info.domain_name} and its datatype is {property_info.range_name}'
    elif entity_type == 'relationship' and property_info is not None:
        prompt += f'between {property_info.domain_name} and {property_info.range_name}'

    prompt += f'\n{get_context_prompt(context)}\n'
    return prompt


def get_sparql_query_description_prompt(query_code: str):
    prompt = f'Provide a short explaination of the following SPARQL query: '
    prompt += f'\n\n{query_code}\n\n ---\n'
    return prompt


def get_data_properties_for_class_prompt(class_name: str, context: str, n=5):
    return (f'Return a JSON list of {n} attributes of the class "{class_name}".\n{get_context_prompt(context)}'
            f'\nProvide only the name without any explanation.')


def get_subclasses_prompt(class_name: str, context: str, n=5):
    return (f'Return a JSON list of {n} subclasses of the class "{class_name}".\n{get_context_prompt(context)}'
            f'\nProvide only the name without any explanation.')


def get_context_prompt(context: str) -> str:
    return f"\n\nThe Context is \"{context}\".\nUse the context only if it's applicable."


def get_language_prompt(language: str):
    return f"Answer in {languages.get(language, languages.get('en'))}."

def get_auto_chart_config(query_code: str):
    return (f"I want to create a chart for the following SPARQL query:"
            f"```sparql\n{query_code}\n```"
            f"Which column should I use as x, which one as y and which one as series?"
            f"Consider that the chart types are the following:"
            f"- columns"
            f"- columns-stacked"
            f"- lines"
            f"- bars"
            f"- bars-stacked"
            f"- pie"
            f"- sunburst"
            f"- cMap"
            f"- clusterMap"
            f"Answer only with json following this type:"
            f"```\n{{"
            f"  chartType: string,"
            f"  xVariable: string,"
            f"  yVariables: string[],"
            f"  series: string,"
            f"}}\n```")

def get_chart_description(query_code: str, chart_config: ChartConfiguration, query_description:str | None = None) -> str:
    result = (f"Given the following SPARQL query:\n"
            f"```sparql\n{query_code}\n```\n")
    if query_description is not None:
        result += f'The query description: \n{query_description}\n'

    result += (f"and this chart configuration:\n"
               f"{chart_config.to_str()}\n"
               f"Give a short explaination of the purpose of the chart.")

    return result

def text_2_parql_prompt(req: Optional[Text2sparqlRequest]) -> str:

    return f'Generate a SPARQL query from the following text:\n{req.text}\n' # TEMPORARY PROMPT
