# Third-party notices

OpsMind is MIT-licensed (see `LICENSE`). The following third-party
dependencies are redistributed at runtime via `requirements.txt`; each is
governed by its own licence, which prevails over anything in this file.

This document is informational — it is not a substitute for reading the
upstream licences. The SPDX identifiers come from PyPI / the projects'
own metadata.

## Runtime dependencies

| Package                  | Version (min) | SPDX            | Upstream                                                         |
| ------------------------ | ------------- | --------------- | ---------------------------------------------------------------- |
| streamlit                | >=1.30.0      | Apache-2.0      | https://github.com/streamlit/streamlit                           |
| langgraph                | >=0.3         | MIT             | https://github.com/langchain-ai/langgraph                        |
| langchain                | >=0.1.0       | MIT             | https://github.com/langchain-ai/langchain                        |
| langchain-community      | >=0.0.10      | MIT             | https://github.com/langchain-ai/langchain                        |
| langchain-core           | >=0.1.0       | MIT             | https://github.com/langchain-ai/langchain                        |
| langchain-mcp-adapters   | >=0.2.0       | MIT             | https://github.com/langchain-ai/langchain-mcp-adapters           |
| sqlalchemy               | >=2.0.0       | MIT             | https://github.com/sqlalchemy/sqlalchemy                         |
| chromadb                 | >=0.4.0       | Apache-2.0      | https://github.com/chroma-core/chroma                            |
| sentence-transformers    | >=2.2.0       | Apache-2.0      | https://github.com/UKPLab/sentence-transformers                  |
| pandas                   | >=2.0.0       | BSD-3-Clause    | https://github.com/pandas-dev/pandas                             |
| plotly                   | >=5.18.0      | MIT             | https://github.com/plotly/plotly.py                              |
| pypdf                    | >=3.17.0      | BSD-3-Clause    | https://github.com/py-pdf/pypdf                                  |
| openpyxl                 | >=3.1.0       | MIT             | https://foss.heptapod.net/openpyxl/openpyxl                      |
| ollama                   | >=0.1.0       | MIT             | https://github.com/ollama/ollama-python                          |
| pyodbc                   | >=5.0.0       | MIT-0           | https://github.com/mkleehammer/pyodbc                            |
| pgvector                 | >=0.3         | MIT             | https://github.com/pgvector/pgvector-python                      |
| psycopg2-binary          | >=2.9         | LGPL-3.0-or-later with exceptions | https://github.com/psycopg/psycopg2                    |
| pyyaml                   | >=6.0         | MIT             | https://github.com/yaml/pyyaml                                   |
| sqlparse                 | >=0.5.0       | BSD-3-Clause    | https://github.com/andialbrecht/sqlparse                         |
| sentry-sdk               | >=2.22        | MIT             | https://github.com/getsentry/sentry-python                       |
| fastmcp                  | >=2.0.0       | Apache-2.0      | https://github.com/jlowin/fastmcp                                |

## Development dependencies

| Package    | Version (min) | SPDX        | Upstream                                |
| ---------- | ------------- | ----------- | --------------------------------------- |
| pytest     | >=7.0.0       | MIT         | https://github.com/pytest-dev/pytest    |
| ruff       | >=0.11        | MIT         | https://github.com/astral-sh/ruff       |
| mypy       | >=1.15        | MIT         | https://github.com/python/mypy          |
| ty         | (pinned in CI)| MIT         | https://github.com/astral-sh/ty         |

## Model weights

OpsMind does not redistribute any model weights. It expects the user to
fetch them locally via Ollama:

```
ollama pull gemma3:12b
```

Gemma 3 is licensed by Google under the Gemma Terms of Use
(<https://ai.google.dev/gemma/terms>). Use of the model is governed by
those terms; OpsMind's MIT grant does not extend to it.

## How to report a licence issue

Open a confidential security advisory at
<https://github.com/Pawansingh3889/OpsMind/security/advisories/new> if
you believe a dependency has been mis-attributed or a licence obligation
has been missed.
