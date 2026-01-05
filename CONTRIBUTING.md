# Contributing to AcATaMa

Thank you for your interest in contributing to AcATaMa! This document provides guidelines for contributing to the project, reporting issues, and seeking support.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

If you encounter a bug or unexpected behavior:

1. **Search existing issues** — Check the [GitHub Issues](https://github.com/SMByC/AcATaMa/issues) to see if the problem has already been reported.
2. **Create a new issue** — If not already reported, open a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the problem
   - Expected vs. actual behavior
   - Your environment details (QGIS version, operating system, AcATaMa version)
   - Screenshots or full error message if applicable
   - Sample data to replicate the issue (if possible)

### Suggesting Features

We welcome feature suggestions! To propose a new feature:

1. **Check existing issues** — Your idea may already be under discussion.
2. **Open a feature request** — Create a new issue with the label `enhancement` and include:
   - A clear description of the proposed feature
   - The use case or problem it addresses
   - Any implementation ideas you may have

### Contributing Code

#### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/SMByC/AcATaMa.git
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Run tests
5. Open a pull request (PR) against `main`

#### Development Setup

AcATaMa is a QGIS plugin. To set up your development environment:

1. Link or copy the `AcATaMa` directory to your QGIS plugins folder:
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows**: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS and enable the plugin via `Plugins` → `Manage and Install Plugins…`
3. (Optional) Install the [plugin reloader](https://plugins.qgis.org/plugins/plugin_reloader) for easier plugin development.

#### Running Tests

First, install the test dependencies using UV:

```bash
uv sync --extra test
```

Then run the test suite:

```bash
uv run pytest tests/
```

### Contributing Documentation

Documentation improvements are always welcome! You can:

- Fix typos or clarify existing documentation
- Add examples or tutorials
- Improve the user guide

Documentation source files are in the `docs/` directory and use Jupyter Book (MyST Markdown).

## Seeking Support

If you need help using AcATaMa:

1. **Read the documentation** — Visit [https://smbyc.github.io/AcATaMa](https://smbyc.github.io/AcATaMa).
2. **Check existing issues or open a new support issue** — Search to see if your question has already been answered. If not, create a new issue.

## Contact

For direct inquiries:

- **Xavier C. Llano** — <xavier.corredor.llano@gmail.com>

## License

By contributing to AcATaMa, you agree that your contributions will be licensed under the [GNU General Public License v3.0](LICENSE).
