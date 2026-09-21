# Installation and troubleshooting

## Check First

Run `which python3 && python3 --version`, then `python3 -c 'import pydantic; print(pydantic.__version__)'`.

## Find Existing Install

Check the active virtual environment, the Python user base, `/usr/local/bin`, and `/opt/homebrew/bin`. Use the discovered absolute path if it is not on `PATH`.

## Install

On macOS or Linux, create a virtual environment with `python3 -m venv .venv`; on Windows use `py -3.11 -m venv .venv`. Activate it and install `pydantic>=2.10,<3`.

## Minimum Version

Raptor requires Python 3.11 or newer and Pydantic 2.10 or newer, below 3. Upgrade the environment rather than using a compatibility fallback.

## PATH Troubleshooting

Hosted shells may not load interactive shell configuration. Activate the environment or add its executable directory to `PATH` for the session.

## Validation

Repeat both checks and run `python3 plugins/raptor/scripts/vendor_schema.py --check`. Do not fall back to an installed `raptor_schema`; bootstrap always uses the verified vendor.

## Known Issues

Shell and hosted-agent `PATH` values may differ. A Pydantic 1.x environment is incompatible.
