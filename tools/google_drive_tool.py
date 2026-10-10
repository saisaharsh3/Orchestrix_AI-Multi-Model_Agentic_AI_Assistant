"""
google_drive_tool.py - Google Drive file search and listing
Uses same OAuth credentials. Enable "Drive API" in Google Cloud Console.
"""

from googleapiclient.errors import HttpError

from tools.google_auth import get_service

MIME_LABELS = {
    "application/vnd.google-apps.document":     "Google Doc",
    "application/vnd.google-apps.spreadsheet":  "Google Sheet",
    "application/vnd.google-apps.presentation": "Google Slides",
    "application/vnd.google-apps.folder":       "Folder",
    "application/pdf":                           "PDF",
    "image/jpeg":                                "Image",
    "image/png":                                 "Image",
}


def _escape(value: str) -> str:
    # Drive query strings are single-quoted; escape backslashes and quotes.
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _get_service():
    return get_service("drive", "v3")


def _format_file(f: dict) -> str:
    name      = f.get("name", "Untitled")
    mime      = f.get("mimeType", "")
    label     = MIME_LABELS.get(mime, "File")
    modified  = f.get("modifiedTime", "")[:10]
    link      = f.get("webViewLink", "")
    return (
        f"- {name} [{label}]\n"
        f"  Modified: {modified}\n"
        + (f"  Link: {link}" if link else "")
    )


def search_drive(query: str, max_results: int = 8) -> str:
    try:
        service = _get_service()
        results = service.files().list(
            q=f"name contains '{_escape(query)}' and trashed=false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        if not files:
            return f"No files found matching '{query}' in your Drive."

        lines = [f"Found {len(files)} file(s) for '{query}':\n"]
        for f in files:
            lines.append(_format_file(f))

        return "\n".join(lines)

    except HttpError as e:
        return f"Error searching Drive: {e}"
    except Exception as e:
        return f"Error: {e}"


def list_recent_files(max_results: int = 8) -> str:
    try:
        service = _get_service()
        results = service.files().list(
            q="trashed=false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        if not files:
            return "No recent files found in your Drive."

        lines = [f"Recent files in Drive ({len(files)}):\n"]
        for f in files:
            lines.append(_format_file(f))

        return "\n".join(lines)

    except HttpError as e:
        return f"Error listing files: {e}"
    except Exception as e:
        return f"Error: {e}"


def list_shared_files(max_results: int = 8) -> str:
    try:
        service = _get_service()
        results = service.files().list(
            q="sharedWithMe=true and trashed=false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink, owners)",
            orderBy="modifiedTime desc",
        ).execute()

        files = results.get("files", [])
        if not files:
            return "No files shared with you."

        lines = [f"Files shared with you ({len(files)}):\n"]
        for f in files:
            owners = f.get("owners", [])
            owner  = owners[0].get("displayName", "Unknown") if owners else "Unknown"
            lines.append(
                _format_file(f) + f"\n  Owner: {owner}"
            )

        return "\n".join(lines)

    except HttpError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: {e}"
