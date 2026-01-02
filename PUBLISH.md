# How to Publish to PyPI

## Prerequisites

```bash
pip install build twine
```

## Build the Package

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build
python -m build
```

This creates:
- `dist/liteq-0.1.0.tar.gz` (source distribution)
- `dist/liteq-0.1.0-py3-none-any.whl` (wheel)

## Test on TestPyPI (Optional but Recommended)

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ liteq
```

## Publish to PyPI

```bash
# Upload to PyPI
python -m twine upload dist/*
```

You'll be prompted for your PyPI credentials.

## After Publishing

Users can install with:

```bash
pip install liteq
```

## Update Version

1. Update version in `pyproject.toml`
2. Update version in `liteq/__init__.py`
3. Rebuild and republish

## Tips

- Test thoroughly before publishing
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases in git: `git tag v0.1.0 && git push --tags`
- Keep CHANGELOG.md updated
