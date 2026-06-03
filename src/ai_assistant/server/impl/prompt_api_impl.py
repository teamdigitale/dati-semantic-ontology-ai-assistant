# coding: utf-8

import json
import os
from typing import Optional, List

from fastapi import HTTPException
from lightrag.llm.openai import openai_complete_if_cache

from .prompt_templates import (
    get_auto_chart_config,
    get_chart_description,
    get_data_properties_for_class_prompt,
    get_entity_description_prompt,
    get_individual_description_prompt,
    get_language_prompt,
    get_sparql_query_description_prompt,
    get_subclasses_prompt, text_2_parql_prompt,
)
from ..apis.prompt_api import BasePromptApi
from ..models.auto_chart_request import AutoChartRequest
from ..models.chart_configuration import ChartConfiguration
from ..models.describe_chart_request import DescribeChartRequest
from ..models.describe_individual_request import DescribeIndividualRequest
from ..models.describe_ontology_entity_request import DescribeOntologyEntityRequest
from ..models.describe_sparql_query_request import DescribeSparqlQueryRequest
from ..models.suggest_class_data_properties_request import SuggestClassDataPropertiesRequest
from ..models.text2sparql_request import Text2sparqlRequest


class PromptApiImpl(BasePromptApi):
    async def describe_individual(
            self,
            describe_individual_request: Optional[DescribeIndividualRequest]
    ) -> str:
        try:
            return await openai_complete_if_cache(
                model=os.getenv("LLM_MODEL", "velvet"),
                prompt=get_individual_description_prompt(
                    describe_individual_request.individual_name,
                    describe_individual_request.context,
                    describe_individual_request.individual_types
                ),
                system_prompt=get_language_prompt(describe_individual_request.language),
                history_messages=None,
                api_key=os.getenv("LLM_BINDING_API_KEY"),
                base_url=os.getenv("LLM_BINDING_HOST"),
                max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})

    async def describe_ontology_entity(
            self,
            describe_ontology_entity_request: Optional[DescribeOntologyEntityRequest],
    ) -> str:
        try:
            return await openai_complete_if_cache(
                model=os.getenv("LLM_MODEL", "velvet"),
                prompt=get_entity_description_prompt(
                    describe_ontology_entity_request.entity_name,
                    describe_ontology_entity_request.entity_type,
                    describe_ontology_entity_request.context,
                    describe_ontology_entity_request.property_info,
                ),
                system_prompt=get_language_prompt(describe_ontology_entity_request.language),
                history_messages=None,
                api_key=os.getenv("LLM_BINDING_API_KEY"),
                base_url=os.getenv("LLM_BINDING_HOST"),
                max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})

    async def describe_sparql_query(
            self,
            describe_sparql_query_request: Optional[DescribeSparqlQueryRequest],
    ) -> str:
        try:
            return await openai_complete_if_cache(
                model=os.getenv("LLM_MODEL", "velvet"),
                prompt=get_sparql_query_description_prompt(describe_sparql_query_request.query_code),
                system_prompt=get_language_prompt(describe_sparql_query_request.language),
                history_messages=None,
                api_key=os.getenv("LLM_BINDING_API_KEY"),
                base_url=os.getenv("LLM_BINDING_HOST"),
                max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})

    async def suggest_class_data_properties(
            self,
            suggest_class_data_properties_request: Optional[SuggestClassDataPropertiesRequest],
    ) -> List[str]:
        try:
            str_result = await openai_complete_if_cache(
                model=os.getenv("LLM_MODEL", "velvet"),
                prompt=get_data_properties_for_class_prompt(
                    suggest_class_data_properties_request.class_name,
                    suggest_class_data_properties_request.context,
                    suggest_class_data_properties_request.number_results,
                ),
                system_prompt=f"You are building an ER diagram."
                              f"\n{get_language_prompt(suggest_class_data_properties_request.language)}",
                history_messages=None,
                api_key=os.getenv("LLM_BINDING_API_KEY"),
                base_url=os.getenv("LLM_BINDING_HOST"),
                max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})
        try:
            return json.loads(str_result.replace('```json', '').replace('```', ''))
        except:
            raise HTTPException(status_code=500, detail={"message": "Unable to parse JSON response from LLM."})

    async def suggest_class_subclasses(
            self,
            suggest_class_data_properties_request: Optional[SuggestClassDataPropertiesRequest],
    ) -> List[str]:
        try:
            str_result = await openai_complete_if_cache(
                model=os.getenv("LLM_MODEL", "velvet"),
                prompt=get_subclasses_prompt(
                    suggest_class_data_properties_request.class_name,
                    suggest_class_data_properties_request.context,
                    suggest_class_data_properties_request.number_results
                ),
                system_prompt=f"You are building an ER diagram."
                              f"\n{get_language_prompt(suggest_class_data_properties_request.language)}",
                history_messages=None,
                api_key=os.getenv("LLM_BINDING_API_KEY"),
                base_url=os.getenv("LLM_BINDING_HOST"),
                max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail={"message": str(e)})
        try:
            return json.loads(str_result.replace('```json', '').replace('```', ''))
        except:
            raise HTTPException(status_code=500, detail={"message": "Unable to parse JSON response from LLM."})

    async def auto_chart(
        self,
        auto_chart_request: Optional[AutoChartRequest],
    ) -> ChartConfiguration:
        str_result = await openai_complete_if_cache(
            model=os.getenv("LLM_MODEL", "velvet"),
            prompt=get_auto_chart_config(
                auto_chart_request.query_code,
            ),
            history_messages=None,
            api_key=os.getenv("LLM_BINDING_API_KEY"),
            base_url=os.getenv("LLM_BINDING_HOST"),
            max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
        )
        return json.loads(str_result.replace('```json', '').replace('```', ''))

    async def describe_chart(
        self,
        describe_chart_request: Optional[DescribeChartRequest],
    ) -> str:
        query_description = describe_chart_request.query_description
        # if query_description is None:
        #     query_description = await self.describe_sparql_query(DescribeSparqlQueryRequest(
        #         queryCode=describe_chart_request.query_code,
        #         language=describe_chart_request.language,
        #     ))
        return await openai_complete_if_cache(
            model=os.getenv("LLM_MODEL", "velvet"),
            prompt=get_chart_description(
                describe_chart_request.query_code,
                describe_chart_request.chart_configuration,
                query_description,
            ),
            system_prompt=get_language_prompt(describe_chart_request.language),
            history_messages=None,
            api_key=os.getenv("LLM_BINDING_API_KEY"),
            base_url=os.getenv("LLM_BINDING_HOST"),
            max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
        )

    async def text2sparql(
        self,
        text2sparql_request: Optional[Text2sparqlRequest],
    ) -> str:
        return await openai_complete_if_cache(
            model=os.getenv("LLM_MODEL", "velvet"),
            prompt=text_2_parql_prompt(text2sparql_request),
            system_prompt='Produce only the SPARQL code without any further comment.',
            history_messages=None,
            api_key=os.getenv("LLM_BINDING_API_KEY"),
            base_url=os.getenv("LLM_BINDING_HOST"),
            max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS"))
        )