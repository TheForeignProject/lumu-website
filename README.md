# LUMU website

This is the production repository for the LUMU website at [lumu.sg](https://lumu.sg). The site is a static Tumult Hype export; it has no application build step.

Pushes to `main` automatically deploy the website to GitHub Pages through [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml). The workflow publishes only `index.html` and `lumu website.hyperesources/`.

For a future designer export, replace `index.html` and the entire `lumu website.hyperesources/` directory with the new export, review the changes, and commit them to `main`. Preserve the generated directory name and structure exactly, including its space: the HTML and Hype scripts refer to those paths.
