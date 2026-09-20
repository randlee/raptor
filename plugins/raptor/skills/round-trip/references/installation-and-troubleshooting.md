# Installation and troubleshooting

## Check First
Run `which python3 && python3 --version` and `python3 -c 'import pydantic; print(pydantic.__version__)'`.

## Find Existing Install
Check the active virtual environment, Python user-base, `/usr/local/bin`, and `/opt/homebrew/bin`.

## Install
Create and activate a virtual environment (`python3 -m venv .venv` on macOS/Linux; `py -3.11 -m venv .venv` on Windows), then install `pydantic>=2.10,<3`.

## Minimum Version
Require Python 3.11+ and Pydantic `>=2.10,<3`.

## PATH Troubleshooting
Hosted shells may omit interactive PATH additions; activate the environment or add its executable directory.

## Validation
Repeat both checks and run the vendor check. Vendored `raptor_schema` is mandatory.

## Known Issues
Pydantic 1.x and ambient `raptor_schema` imports fail closed.
