### Recommended VS Code Settings

Add the following to your `./vscode/settings.json` for a better development experience:

```jsonc
{
  "editor.formatOnSave": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "python.analysis.typeCheckingMode": "basic",
  "mypy-type-checker.args": ["--config-file=pyproject.toml"]
}
```
