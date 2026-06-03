#!/usr/bin/env sh
######################################################################
## Utility script to perform update for codegen for the ai_assistant
##
## Executed steps are:
##   1) Check for requirements
##   2) Perform generation
##   3) Apply post-gen fixes that are not made by the generator
######################################################################

# Global variables setup
OPENAPI_EXEC="${OPENAPI_EXEC:-"`command -v openapi-generator-cli`"}"
OPENAPI_SPEC="${OPENAPI_SPEC:-"../swaggers/bundled/ai-assistant.yaml"}"
OUTPUT_DIR="${OUTPUT_DIR:-"`mktemp -d -t ai_assistant.gen-XXX`"}"

# Check if the generator is present
if [ ! -x "$OPENAPI_EXEC" ]; then
    echo "ERROR: Missing openapi-generator-cli command from PATH" >&2
    echo "       See https://openapi-generator.tech/docs/installation/ for installation instructions" >&2
    exit 1
fi

# Run generator
echo "########################################"
echo "## RUN OPENAPI GENERATOR"
echo "########################################"
echo

"${OPENAPI_EXEC}" generate \
    -g python-fastapi \
    -i "${OPENAPI_SPEC}"\
    -o "${OUTPUT_DIR}" \
    --additional-properties="packageName=ai_assistant.server,fastapiImplementationPackage=impl"

# Update generated files
echo "########################################"
echo "## UPDATE GENERATED PACKAGES"
echo "########################################"
echo

# momentary fix waiting https://github.com/OpenAPITools/openapi-generator/issues/20115
echo "Remove convert_api.py and convert_api_base.py from generation"
rm "${OUTPUT_DIR}/src/ai_assistant/server/apis/convert_api.py" "${OUTPUT_DIR}/src/ai_assistant/server/apis/convert_api_base.py"

echo "* Copying apis package..."
mv "${OUTPUT_DIR}/src/ai_assistant/server/apis/"* "./src/ai_assistant/server/apis/"
echo "* Copying models package..."
rm ./src/ai_assistant/server/models/*
mv "${OUTPUT_DIR}/src/ai_assistant/server/models/"* "./src/ai_assistant/server/models/"

echo "########################################"
echo "## GENERATION COMPLETED"
echo "########################################"
