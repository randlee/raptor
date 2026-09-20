# Installation and troubleshooting

## Check First
Run `which python3 && python3 --version` and `python3 -c 'import pydantic; print(pydantic.__version__)'`.

## Find Existing Install
Check the active virtual environment, Python user-base, `/usr/local/bin`, and `/opt/homebrew/bin` before installing.

## Install
On macOS/Linux run `python3 -m venv .venv`; on Windows run `py -3.11 -m venv .venv`. Activate it and install `pydantic>=2.10,<3`.

## Minimum Version
Require Python 3.11+ and Pydantic `>=2.10,<3`.

## PATH Troubleshooting
Hosted shells may omit interactive PATH additions. Activate the environment or add its executable directory for this session.

## Validation
Repeat both checks and run the vendor check. Never substitute an installed `raptor_schema`.

## Known Issues
Pydantic 1.x and a source-checkout `raptor_schema` are intentionally rejected.
