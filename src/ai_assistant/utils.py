# coding: utf-8

from __future__ import annotations

import asyncio
import logging

import regex
import re
import os

logger = logging.getLogger("ai_assistant")

languages_en = {
    "en": "english",
    "it": "italian",
    "fr": "french",
    "es": "spanish",
    "pt": "portuguese",
    "de": "german",
}

languages_it = {
    "en": "inglese",
    "it": "italiano",
    "fr": "francese",
    "es": "spagnolo",
    "pt": "portoghese",
    "de": "tedesco",
}

prompt_language = os.getenv("PROMPTS_LANGUAGE", "Italian").capitalize()
if prompt_language == "Italian":
    languages = languages_it
    DEFAULT_LANGUAGE = "italiano"
    DEFAULT_IRI_LANGUAGE = "inglese"
else:
    languages = languages_en
    DEFAULT_LANGUAGE = "italian"
    DEFAULT_IRI_LANGUAGE = "english"

inv_languages = {v: k for k, v in languages.items()}

def is_name_regex(value: str) -> bool:
    return bool(regex.match(r"^(?:\p{Latin}|_|'| )*$", value))


def is_text_regex(value: str) -> bool:
    return bool(regex.match(r"^(?:\p{Latin}|\p{Common})*$", value))


def get_namespace_from_iri(iri: str) -> str:
    last_separator_slash = iri.rfind("/")
    last_separator_hashtag = iri.rfind("#")

    if last_separator_hashtag is not None and last_separator_slash is not None:
        last_sep_index = (
            last_separator_slash
            if last_separator_slash > last_separator_hashtag
            else last_separator_hashtag
        )
    elif last_separator_hashtag is not None or last_separator_hashtag is not None:
        last_sep_index = last_separator_hashtag or last_separator_slash
    else:
        last_sep_index = 0

    return iri[:last_sep_index + 1]

def simple_name_to_label(simple_name: str, simple_name_format: str|None = None) -> str:
    label = simple_name
    if simple_name_format is None or simple_name_format == "snake_case":
        label = simple_name.replace("_", " ")
    if simple_name_format is None or simple_name_format == "camelCase":
        label = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', lambda x: ' '+x.group(1).lower(), label)
    return label

def iri_add_simple_name(iri: str, simple_name: str) -> str:
    if simple_name.startswith('/') or simple_name.startswith('#'):
        sep = simple_name[0:1]
        simple_name = simple_name[1:]
    else:
        sep = '/'
    if not iri or iri.endswith('/') or iri.endswith('#'):
        return iri + simple_name
    else:
        return iri + sep + simple_name

def execute_async(coroutine, *args) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coroutine(*args))
    loop.close()
