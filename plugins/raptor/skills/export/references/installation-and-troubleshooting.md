# Installation and troubleshooting

## Check First
Run `which sc-compose && sc-compose --version`, `which python3 && python3 --version`, and `python3 -c 'import pydantic; print(pydantic.__version__)'`.

## Find Existing Install
Check `$HOME/.local/bin/sc-compose`, `$HOME/.venvs/sc-compose/bin/sc-compose`, the Python user-base `bin`, and `/opt/homebrew/bin/sc-compose` before installing another copy.

## Install
Install sc-compose using its supported package or release for the platform. On macOS/Linux run `python3 -m venv .venv`; on Windows run `py -3.11 -m venv .venv`. Activate it and install `pydantic>=2.10,<3`.

## Minimum Version
Require sc-compose in the range declared by `plugin-manifest.json`, Python 3.11+, and Pydantic `>=2.10,<3`.

## PATH Troubleshooting
Hosted shells may omit interactive PATH additions. Use the discovered full sc-compose path or add its directory for this session.

## Validation
Repeat all checks and run the vendor check. Never substitute an installed `raptor_schema`.

## Known Issues
Missing, unparseable, pre-1.6.1, and 2.x sc-compose versions fail closed. Pydantic 1.x and a source-checkout `raptor_schema` are intentionally rejected.
