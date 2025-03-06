
For Raspberry Pi
* update to bookworm
* sudo apt-get install libatlas-base-dev
* sudo apt-get install libgeos-dev
* sudo apt-get install libpq-dev

modify pyproject.toml extra index to use piwheels:

[[tool.uv.index]]
url = "https://www.piwheels.org/simple"

remove dev dependencies as ipykernel causes issues

uv sync needs to be run manually on the rpi to set up venv




