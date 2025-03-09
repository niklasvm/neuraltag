
from pprint import pp
import requests
import toml

def trigger_gha(
    inputs: dict,
    workflow_file: str,
    repo: str,
    ref: str,
    github_user: str,
    github_pat: str,
) -> None:
    """Triggers a GitHub Actions workflow dispatch.

    This function retrieves necessary environment variables (GITHUB_USER, REPO,
    GITHUB_PAT, WORKFLOW_FILE) and uses them to construct the API endpoint for
    triggering a workflow dispatch. It then sends a POST request to the GitHub API
    with the required headers and data to initiate the workflow run.  The function
    checks the response status code and prints a success or failure message
    accordingly.

    Raises:
        KeyError: If any of the required environment variables are not set.
        requests.exceptions.RequestException: If the API request fails.
    """

    endpoint = f"https://api.github.com/repos/{github_user}/{repo}/actions/workflows/{workflow_file}/dispatches"

    headers = {
        "Authorization": f"Bearer {github_pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    data = {
        "ref": f"{ref}",
        "inputs": inputs,
    }

    response = requests.post(endpoint, headers=headers, json=data)

    if response.status_code == 204:
        print("Workflow dispatch triggered successfully.")
    else:
        print(
            f"Failed to trigger workflow dispatch. Status code: {response.status_code}, Response: {response.text}"
        )
        raise requests.exceptions.RequestException(
            f"Failed to trigger workflow dispatch. Status code: {response.status_code}, Response: {response.text}"
        )
    

def generate_rpi_pyproject_toml(pyproject_toml:str):
    # load
    with open(pyproject_toml, "r") as f:
        data = toml.load(f)

    # remove dev dependencies
    del data["dependency-groups"]["dev"]

    # add piwheels index
    data["tool"]["uv"]["index"] = [{"url": "https://www.piwheels.org/simple"}]

    # write
    with open(pyproject_toml, "w") as f:
        toml.dump(data, f, encoder=toml.TomlPreserveInlineDictEncoder())


if __name__ == "__main__":
    generate_rpi_pyproject_toml("pyproject.toml")

