
For Raspberry Pi
* update to bookworm
* sudo apt-get install libatlas-base-dev
* sudo apt-get install libgeos-dev
* sudo apt-get install libpq-dev
* sudo apt-get install libopenblas-dev

numpy issues:
pip uninstall numpy
https://stackoverflow.com/questions/14570011/explain-why-numpy-should-not-be-imported-from-source-directory

modify pyproject.toml extra index to use piwheels:

[[tool.uv.index]]
url = "https://www.piwheels.org/simple"

remove dev dependencies as ipykernel causes issues

uv sync needs to be run manually on the rpi to set up venv




