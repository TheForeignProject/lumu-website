"""Stage the Hype export with production branding, using only the stdlib."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import sys


RESOURCES = "lumu website.hyperesources"
HYPE_SCRIPT = "lumuwebsite_hype_generated_script.js"
ROUTER_SCRIPT = "hype-hash-router.js"
ROUTER_TAG = f'<script src="{ROUTER_SCRIPT}" data-hype-route-exclude=\'["dh"]\'></script>'
ICONS = ("favicon.png", "favicon.ico")
FLAGS = re.IGNORECASE | re.DOTALL


class TagAttributes(HTMLParser):
    def handle_starttag(self, tag, attrs):
        self.tag = tag
        self.attrs = dict(attrs)


def attributes(tag):
    parser = TagAttributes()
    parser.feed(tag)
    return parser.tag, parser.attrs


def brand_head(html, template):
    """Replace only brand metadata; preserve the rest of the export verbatim."""
    heads = list(re.finditer(r"<head\b[^>]*>(.*?)</head\s*>", html, FLAGS))
    if len(heads) != 1 or len(re.findall(r"</?head\b", html, FLAGS)) != 2:
        raise ValueError("Expected exactly one complete <head> in the Hype export")
    head = heads[0]
    content = head.group(1)
    titles = re.findall(r"<title\b[^>]*>.*?</title\s*>", content, FLAGS)
    if len(titles) != 1 or len(re.findall(r"</?title\b", html, FLAGS)) != 2:
        raise ValueError("Expected exactly one complete <title> in the Hype export head")
    content = re.sub(r"<title\b[^>]*>.*?</title\s*>", "", content, flags=FLAGS)

    def remove_old_tag(match):
        tag, attrs = attributes(match.group(0))
        if tag == "meta" and (attrs.get("property") or attrs.get("name") or "").lower() in {"og:title", "og:site_name", "og:url"}:
            return ""
        if tag == "link" and set((attrs.get("rel") or "").lower().split()) & {"canonical", "icon"}:
            return ""
        return match.group(0)

    content = re.sub(r"<(?:meta|link)\b[^>]*>", remove_old_tag, content, flags=FLAGS)

    def is_website(node):
        types = node.get("@type") if isinstance(node, dict) else None
        return types == "WebSite" or isinstance(types, list) and "WebSite" in types

    def remove_old_website(match):
        _, attrs = attributes(match.group(1))
        if (attrs.get("type") or "").lower() != "application/ld+json":
            return match.group(0)
        data = json.loads(match.group(2))
        if is_website(data):
            return ""
        # A mixed graph needs deliberate merging so unrelated entities survive.
        nodes = data.get("@graph", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        if any(is_website(node) for node in nodes):
            raise ValueError("Existing WebSite in a JSON-LD graph: merge it into site/seo-head.html before publishing")
        return match.group(0)

    content = re.sub(r"(<script\b[^>]*>)(.*?)</script\s*>", remove_old_website, content, flags=FLAGS)
    return html[:head.start(1)] + content + "\n" + template.rstrip() + "\n" + ROUTER_TAG + "\n" + html[head.end(1):]


def prepare_site(source):
    """Publish to source/_site; never edit the input index or resource files."""
    source = Path(source).resolve()
    output = source / "_site"
    required = [source / "index.html", source / RESOURCES / HYPE_SCRIPT,
                source / "site" / "seo-head.html", source / "site" / ROUTER_SCRIPT]
    required.extend(source / "site" / "icons" / name for name in ICONS)
    for path in required:
        if not path.is_file():
            label = "Hype script" if path.name == HYPE_SCRIPT else "required file"
            raise ValueError(f"Missing {label}: {path}")

    # read_bytes preserves the generated export's original line endings.
    original = (source / "index.html").read_bytes().decode("utf-8")
    template = (source / "site" / "seo-head.html").read_bytes().decode("utf-8")
    published = brand_head(original, template).encode("utf-8")
    if f"{RESOURCES.replace(' ', '%20')}/{HYPE_SCRIPT}" not in original:
        raise ValueError("Hype script reference is missing from index.html")

    # All input checks precede cleanup. Never follow a redirected output path.
    if output.is_symlink() or output.resolve() != output:
        raise ValueError("Refusing to replace a redirected _site directory")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    shutil.copytree(source / RESOURCES, output / RESOURCES)
    (output / "index.html").write_bytes(published)
    shutil.copyfile(source / "site" / ROUTER_SCRIPT, output / ROUTER_SCRIPT)
    for name in ICONS:
        shutil.copyfile(source / "site" / "icons" / name, output / name)
    return output


if __name__ == "__main__":
    try:
        destination = prepare_site(Path(__file__).resolve().parents[1])
    except (ValueError, OSError) as error:
        print(f"Site preparation failed: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"Prepared production website: {destination}")
