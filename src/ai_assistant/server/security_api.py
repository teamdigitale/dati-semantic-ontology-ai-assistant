# coding: utf-8

import json
import os

from dotenv import load_dotenv
from fastapi import Depends, Security, HTTPException  # noqa: F401
from fastapi.openapi.models import OAuthFlowImplicit, OAuthFlows  # noqa: F401
from fastapi.security import (  # noqa: F401
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    OAuth2,
    OAuth2AuthorizationCodeBearer,
    OAuth2PasswordBearer,
    SecurityScopes,
)
from fastapi.security.api_key import APIKeyCookie, APIKeyHeader, APIKeyQuery  # noqa: F401

from ai_assistant.server.models.extra_models import TokenModel

bearer_auth = HTTPBearer()


def get_token_jwt(credentials: HTTPAuthorizationCredentials = Depends(bearer_auth)) -> TokenModel | None:
    """
    Check and retrieve authentication information from custom bearer token.

    :param credentials: Credentials provided by Authorization header
    :return: Decoded token information or raise 401 if token is invalid
    """
    load_dotenv(override=False)
#     if os.getenv("NO_AUTH"):
    if os.getenv("NO_AUTH", "").strip().lower() == "true":
        return None
    mastro_home = os.getenv("MASTRO_HOME", os.curdir)
    with open(os.path.join(mastro_home, "mastro.passwd")) as pwdfile:
        passwds = json.load(pwdfile)
        for k, v in passwds.items():
            if credentials.credentials.upper() == v.upper():
                return TokenModel(sub=k)
    raise HTTPException(status_code=401, detail="Unauthorized")

