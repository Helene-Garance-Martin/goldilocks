from urllib.parse import unquote


def parse_snaplogic_url(url: str) -> dict:
    """
    Parse a SnapLogic Designer or Manager URL.

    Returns:
    - org
    - project_path
    - decoded_url
    """

    decoded = unquote(url.strip())

    if "/designer/" in decoded:
        path_part = decoded.split("/designer/", 1)[1]
    elif "/asset/" in decoded:
        path_part = decoded.split("/asset/", 1)[1]
    else:
        raise ValueError("Unsupported SnapLogic URL format")

    path_part = path_part.split("?", 1)[0]
    parts = [part for part in path_part.split("/") if part]

    if len(parts) < 2:
        raise ValueError("Invalid SnapLogic path")

    org = parts[0]
    project_path = "/".join(parts[1:])

    export_url = (
    "https://emea.snaplogic.com/api/1/rest/public/project/export/"
    f"{org}/{project_path}?asset_types=Pipeline"
    )

    return {
    "org": org,
    "project_path": project_path,
    "decoded_url": decoded,
    "export_url": export_url,
    }