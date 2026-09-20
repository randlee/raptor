# Installation and troubleshooting

## Check First
Run `which sc-compose && sc-compose --version`, `which python3 && python3 --version`, and `python3 -c 'import pydantic; print(pydantic.__version__)'`.

## Find Existing Install
Check `$HOME/.local/bin/sc-compose`, `$HOME/.venvs/sc-compose/bin/sc-compose`, the Python user-base `bin`, and `/opt/homebrew/bin/sc-compose`.

## Install
Install sc-compose using its supported package or release. Create and activate a virtual environment (`python3 -m venv .venv` on macOS/Linux; `py -3.11 -m venv .venv` on Windows), then install `pydantic>=2.10,<3`.

## Minimum Version
Require the sc-compose range declared by `plugin-manifest.json`, Python 3.11+, and Pydantic `>=2.10,<3`.

## PATH Troubleshooting
Hosted shells may omit interactive PATH additions; use the discovered full sc-compose path or add its directory.

## Validation
Repeat all checks and run the vendor check. Vendored `raptor_schema` is mandatory.

## Known Issues
Missing, unparseable, pre-1.6.1, and 2.x sc-compose versions fail closed. Pydantic 1.x and ambient `raptor_schema` imports fail closed.
