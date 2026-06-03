# AI Assistant : an AI assistant for the ontology designer

## Installation

Project installation follows standard Python packaging guidelines:

```bash
# create and activate a Python virtual environment (optional yet recommended)
python3 -m venv <venv-path>
source <venv-path>/bin/activate

# Install through the pip package manager
pip install .
```

Supported Python versions are 3.9 or later. Other available dependency profiles
are `dev` for development and `tests` for unit tests, e.g.:

```bash
pip install -e .[dev,tests]
```

where the `-e` option installs in development mode.

Copy `env.example` file into a new file called `.env` and set the value of the variables.

The following table describes the role of environment variables:

| **Variable** | **Explanation** | **Mandatory** | **Type** | **Default value** |
|--------------|-----------------|---------------|----------|-------------------|
|**WORKING_DIR**|Storage location of data/file|Yes (only for no public version)|string|current working directory|
|**GRAPH_FILE_EXT**|Format of the file containing the graph|No|string|gscape|
|**LOG_LEVEL**|Log tracking level|No|string|INFO|
|**LOG_DIR**|Log file location|No|string|current working directory|
|**VERBOSE**|Log verbosity level|No|boolean|False|
|**LOG_MAX_BYTES**|Log file max size in bytes|No|integer|10485760|
|**LOG_BACKUP_COUNT**|Number of backup files to keep|No|integer|5|
|**NO_AUTH**|Authentication required notice|Yes|boolean|False|
|**WEB_CONCURRENCY**|Number of possible concurrent workers|No|string|1|
|**ENABLE_LLM_CACHE**|Enables caching for LLM responses to avoid redundant computations|No|boolean|False|
|**ENABLE_LLM_CACHE_FOR_EXTRACT**|Enables caching for ontology extraction steps to reduce LLM costs|No|boolean|False|
|**ENABLE_VDB_LOAD**|Enables Vector DB loading|No|boolean|True|
|**ENABLE_VDB_LOAD_FOR_EXTRACT**|Enables Vector DB loading after ontology extraction|No|boolean|False|
|**ENABLE_DISK_PERSIST**|Enables disk data storage|No|boolean|False|
|**PROMPTS_LANGUAGE**|Prompt language, possible values: Italian or English|No|string|Italian|
|**SUMMARY_LANGUAGE**|Ontology annotation language (specify in `PROMPTS_LANGUAGE`)|No|string|italiano|
|**IRI_LANGUAGE**|Language of ontology entities identification name (specify in `PROMPTS_LANGUAGE`)|No|string|inglese|
|**IRI_FORMAT**|Style of ontology entities identification name, possible values: camelCase or snake_case_|No|string|camelCase|
|**COSINE_THRESHOLD**|Cosine threshold of vector DB retrieval for entity types, relations and chunks|No|decimal|0.2|
|**ENABLE_RERANK**|Enables rerank function|No|boolean|True|
|**RERANK_MODEL**|Model of rerank function|Yes|string|no default|
|**RERANK_BINDING_HOST**|Rerank API endpoint|Yes|string|no default|
|**RERANK_BINDING_API_KEY**|Rerank API key|Yes|string|no default|
|**LLM_MODEL**|LLM model|Yes|string|no default|
|**LLM_BINDING**|LLM model type|No|string|openai|
|**LLM_BINDING_HOST**|LLM API endpoint|Yes|string|no default|
|**LLM_BINDING_API_KEY**|LLM API key|Yes|string|no default|
|**TEMPERATURE**|LLM temperature parameter|No|decimal|0.5|
|**SEED**|LLM seed parameter|No|integer|not set|
|**TIMEOUT**|Maximum waiting time for a LLM response|No|integer|not set|
|**EMBEDDING_MODEL**|Embedding model|Yes|string|no default|
|**EMBEDDING_BINDING**|Embedding model type|No|string|openai|
|**EMBEDDING_BINDING_HOST**|Embedding API endpoint|Yes|string|no default|
|**EMBEDDING_BINDING_API_KEY**|Embedding API key|Yes|string|no default|
|**EMBEDDING_DIM**|Embedding vector dimensions|Yes|integer|1024|
|**MAX_EMBED_TOKENS**|Embedding maximum input length|Yes|integer|8192|

## Usage

Once installed you can start the FastAPI backend through the `ai_assistant` command:

```bash
ai_assistant server run
```

You can use the `-h` (or `--help`) option to list the available configuration options for the backend, e.g.:

```bash
ai_assistant server run -b 0.0.0.0 -m /ai-assistant -p 8200 -d cache_dir
```

where:
* `-b` sets the host to bind to (default is localhost)
* `-m` sets the mount path of the backend (default is `/`)
* `-p` sets the port to listen to (default is `8200`)
* `-d` sets the directory to store the vector db files (defaults to the current folder)

## Specification

<details>
<summary> Model graph formats </summary>

*  Nodes:

| **Parameter** | **Explanation** | **Value/Spec** |
|--------------|-----------------|----------------|
| **node_id** | Unique node identifier | Matches the class/data_property simple name |
| **namespace** | The namespace of the IRI of the entity | If IRI = 'http://obda.com/Datore_di_Lavoro' then namespace = 'http://obda.com/' |
| **node_type** | The node type | Possible values: "entity_type" (for class), "characteristic" (for data_property) |
| **datatype** | The data_property datatype | Only for node_type = "characteristic" |
| **label** | The node label | Matches the class/data_property label annotations. It's a dictionary with language tag key |
| **description** | The node description | Matches the class/data_property comment annotations. It's a dictionary with language tag key |
| **frozen** | If present tells if the node is modifiable (False) or not (True)| If not present, the node is modifiable |
| **source_id** | (List of) Unique document ID in the entities vdb | Link the node to the texts provenance |
| **file_paths** | (List of) Document file path | Link the node to the files provenance |

* Edges:

| **Parameter** | **Explanation** | **Value/Spec** |
|--------------|-----------------|----------------|
| **src_id** | Edge source node | If node_type == "relationship", matches the object_property domain label else if node_type == "characteristic" is the data_property class and if node_type == "subclass", is the subclass label |
| **tgt_id** | Edge target node | If node_type == "relationship", matches the object_property range label else if node_type == "characteristic" is the data_property label and if node_type == "subclass", is the superclass label |
| **edge_id** | Unique node identifier (key) for the edges from source to target | Matches the object_property label. If edge_type == "characteristic" or "subclass" then edge_id = "0" |
| **namespace** | The namespace of the IRI of the relationship | If IRI = 'http://obda.com/ha_datore_di_lavoro' then namespace = 'http://obda.com/' |
| **node_type** | Edge type | Possible values: "relationship" (for object_property), "characteristic" (for data_property), "subclass" (for isa relationship) |
| **label** | The edge label | Matches the object_property label annotation. It's a dictionary with language tag key. Absent for edge_type == "characteristic" or "subclass"|
| **description** | The edge description | Matches the object_property comment annotation. It's a dictionary with language tag key. Absent for edge_type == "characteristic" or "subclass"|
| **frozen** | If present tells if the edge is modifiable (False) or not (True)| If not present, the edge is modifiable |
| **source_id** | (List of) Unique document ID in the relationships vdb | Link the edge to the texts provenance |
| **file_paths** | (List of) Document file path | Link the edge to the files provenance |

</details>

## Server API/Model Code Generation
Just execute the code generation script from the root of the project in a bash shell:
```
 scripts/update-codegen.sh
```

It requires openapi-generator-cli command installed:
https://openapi-generator.tech/docs/installation/