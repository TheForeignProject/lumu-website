# LUMU website

This is the production repository for the LUMU website at [lumu.sg](https://lumu.sg). The site is a static Tumult Hype export. A Python standard-library script prepares it for publication; no application build or package installation is needed.

Pushes to `main` automatically deploy the website to GitHub Pages through [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml). The workflow runs the publishing tests, then [`scripts/prepare_site.py`](scripts/prepare_site.py). Only the prepared `_site/` directory is published: the branded `index.html`, the unchanged `lumu website.hyperesources/` directory, the root favicon files, and `hype-hash-router.js`.

For a future designer export, replace `index.html` and the entire `lumu website.hyperesources/` directory with the new export, review the changes, and commit them to `main` after the local checks below. Preserve the generated directory name and structure exactly, including its space: the HTML and Hype scripts refer to those paths. Keep `site/`, the publishing script, and its tests when importing updates.

## Production branding

[`site/seo-head.html`](site/seo-head.html) is the source of truth for the production title, Open Graph brand metadata, canonical URL and `WebSite` JSON-LD. The publishing script replaces the export's title and conflicting brand tags without modifying the original export or its page body. Keep this template and `site/icons/` when importing designer updates. If an export includes a `WebSite` entity inside a mixed JSON-LD graph, the script fails explicitly so the graph can be merged deliberately without losing other entities.

[`site/icons/`](site/icons/) contains the full original LUMU wordmark (`lumu-logo.svg`), a 96×96 PNG, and an ICO with 16×16, 32×32 and 48×48 versions. Both raster files use the black logo, proportionally centered on the website's `#EAEBD5` background. The PNG has an 80-pixel-wide wordmark inside the 96-pixel square; the ICO sizes are downsampled from it. Icons are published at stable `/favicon.png` and `/favicon.ico` URLs, independently of the Hype resource directory.

[`site/hype-hash-router.js`](site/hype-hash-router.js) restores Hype scenes from URL hashes and browser history, returning restored pages to the top. Preparation copies it to the published root and adds one blocking script at the end of the prepared head, before the generated Hype script. It discovers scenes from the current export; `data-hype-route-aliases` can supply a JSON object mapping additional hashes to scene names, and `data-hype-route-exclude` supplies a JSON array of overlay scenes. The prepared LUMU page excludes `dh`, so opening and closing that overlay keeps the underlying page's route. Maintain these company files when adapting routing to a new export; keep generated designer files unchanged.

## Local verification and preview

Run with Python 3.9 or newer from this repository:

```sh
python -m unittest discover -s tests -v
python scripts/prepare_site.py
python -m http.server 8000 --directory _site
```

If Node.js is already installed, `node tests/test_hype_hash_router.cjs` also checks the runtime's routing, history, and scroll behavior without installing packages.

Open `http://localhost:8000/` to preview the actual published website, including its title, favicon, and routing. Viewing the raw export directly still shows the designer's original metadata. Preparation rebuilds only the generated `_site/` directory, removing obsolete files from previous previews. Do not put hand-maintained files there.

Before pushing a designer update, use the actual navigation in desktop and mobile previews. Check scene and hash agreement, refresh and direct URLs, Back/Forward, and rapid navigation while scrolled down; each selected page should start at the top. Open and close the `dh` overlay, and check an existing animation and external link. Fix any routing compatibility issue in `site/hype-hash-router.js` or its prepared configuration, then repeat the checks. If browser verification cannot be completed, report that before pushing. Repeat these navigation checks on the live site after deployment.

## Google Search follow-up

After a successful Pages deployment, check `https://lumu.sg/`, `/favicon.png` and `/favicon.ico` for HTTP 200 responses and verify the live page's title is `LUMU Singapore`. Validate the homepage's `WebSite` JSON-LD with [Schema Markup Validator](https://validator.schema.org/); Google's Rich Results Test does not support site names.

The owner of the `lumu.sg` [Google Search Console](https://search.google.com/search-console) property should:

1. Inspect `https://lumu.sg/` with URL Inspection.
2. Run **Test live URL** and confirm the homepage is crawlable and its rendered HTML includes the new brand metadata.
3. Select **Request indexing** after the live test succeeds.
4. Check the search result after Google recrawls, including the title, site name and icon.

If the property is not verified, the domain owner must first verify it using the method Search Console provides. The website changes work independently of Search Console access. Google may take days to weeks to recrawl and process the update, and selects the final title, site name and favicon automatically: [title links](https://developers.google.com/search/docs/appearance/title-link), [site names](https://developers.google.com/search/docs/appearance/site-names), [favicon requirements](https://developers.google.com/search/docs/appearance/favicon-in-search).
