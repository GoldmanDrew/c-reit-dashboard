# GitHub Pages setup

This repo is a static dashboard. If GitHub Pages is enabled for the repository, it can serve directly from the `main` branch root.

Recommended Pages settings:

```text
Source: Deploy from a branch
Branch: main
Folder: / (root)
```

The OAuth token available during initial setup did not include GitHub's `workflow` scope, so this repo intentionally avoids committing a GitHub Actions workflow file.
