from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "manuscript" / "mdpi_jmse" / "template.tex"
OUT_JSON = ROOT / "audit" / "reference_verification_20260514_v2.json"
OUT_MD = ROOT / "audit" / "reference_verification_20260514_v2.md"


def parse_refs() -> list[dict[str, object]]:
    text = TEX.read_text(encoding="utf-8")
    block = text.split(r"\begin{thebibliography}{999}", 1)[1].split(r"\end{thebibliography}", 1)[0]
    parts = re.split(r"\\bibitem\{([^}]+)\}", block)[1:]
    refs: list[dict[str, object]] = []
    for key, body in zip(parts[0::2], parts[1::2]):
        one = " ".join(body.strip().split())
        doi_match = re.search(r"doi:([^\s.]+(?:\.[^\s.]+)*(?:/[^\s]+)?)", one)
        if not doi_match:
            doi_match = re.search(r"doi:([0-9][^\s]+)", one)
        doi = doi_match.group(1).rstrip(".,;)") if doi_match else None
        url_match = re.search(r"\\url\{([^}]+)\}", one)
        refs.append(
            {
                "key": key,
                "text": one,
                "doi": doi,
                "url": url_match.group(1) if url_match else None,
                "has_et_al": "et al." in one,
            }
        )
    return refs


def fetch_crossref(doi: str) -> dict[str, object]:
    api = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    request = urllib.request.Request(
        api,
        headers={
            "User-Agent": "geo-auv-bathymetry-benchmark-reference-check/1.0 (mailto:example@example.com)"
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=14) as response:
            payload = json.loads(response.read().decode("utf-8"))
        message = payload.get("message", {})
        return {
            "ok": True,
            "status": "verified_crossref",
            "title": "; ".join(message.get("title") or []),
            "container": "; ".join(message.get("container-title") or []),
            "issued": message.get("issued", {}),
            "type": message.get("type"),
            "publisher": message.get("publisher"),
            "doi_crossref": message.get("DOI"),
        }
    except Exception as exc:
        return {"ok": False, "status": "crossref_failed", "error": str(exc)}


def fetch_doi_resolution(doi: str) -> dict[str, object]:
    url = "https://doi.org/" + doi
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    redirect_request = urllib.request.Request(
        url,
        headers={"User-Agent": "geo-auv-bathymetry-benchmark-reference-check/1.0"},
        method="HEAD",
    )
    try:
        urllib.request.build_opener(NoRedirect).open(redirect_request, timeout=14)
    except urllib.error.HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308} and exc.headers.get("Location"):
            return {
                "ok": True,
                "status": "verified_doi_redirects",
                "doi_url": url,
                "resolved_url": exc.headers.get("Location"),
                "http_status": exc.code,
            }
    except Exception:
        pass
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "geo-auv-bathymetry-benchmark-reference-check/1.0"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=14) as response:
                return {
                    "ok": True,
                    "status": "verified_doi_resolves",
                    "doi_url": url,
                    "resolved_url": response.geturl(),
                    "http_status": response.status,
                }
        except Exception as exc:
            last_error = str(exc)
    return {"ok": False, "status": "doi_resolution_failed", "doi_url": url, "error": last_error}


def fetch_url(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "geo-auv-bathymetry-benchmark-reference-check/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=14) as response:
            return {"ok": True, "status": f"url_http_{response.status}"}
    except Exception as exc:
        return {"ok": False, "status": "url_failed", "error": str(exc)}


def main() -> None:
    refs = parse_refs()
    results = []
    for ref in refs:
        result = dict(ref)
        doi = ref.get("doi")
        url = ref.get("url")
        if isinstance(doi, str) and doi:
            crossref_result = fetch_crossref(doi)
            result.update(crossref_result)
            if not crossref_result.get("ok"):
                doi_result = fetch_doi_resolution(doi)
                result.update(
                    {
                        "crossref_status": crossref_result.get("status"),
                        "crossref_error": crossref_result.get("error"),
                    }
                )
                result.update(doi_result)
            time.sleep(0.12)
        elif isinstance(url, str) and url:
            result.update(fetch_url(url))
        else:
            result.update({"ok": False, "status": "no_doi_or_url"})
        results.append(result)

    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Reference verification 2026-05-14 v2\n\n",
        "| # | Key | DOI/URL status | Crossref/URL title | Flags |\n",
        "|---:|---|---|---|---|\n",
    ]
    for index, result in enumerate(results, 1):
        flags = []
        if not result.get("ok"):
            flags.append("VERIFY_FAILED")
        if result.get("has_et_al"):
            flags.append("contains et al.")
        title = str(result.get("title") or result.get("url") or result.get("resolved_url") or "").replace("|", "/")[:140]
        lines.append(
            f"| {index} | `{result['key']}` | {result.get('status')} | {title} | {', '.join(flags)} |\n"
        )
    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(OUT_JSON)
    print(OUT_MD)
    print(
        "total",
        len(results),
        "failed",
        sum(1 for item in results if not item.get("ok")),
        "et_al",
        sum(1 for item in results if item.get("has_et_al")),
    )
    for result in results:
        if (not result.get("ok")) or result.get("has_et_al"):
            print(result["key"], result.get("status"), result.get("doi") or result.get("url"), result.get("error", ""))


if __name__ == "__main__":
    main()
