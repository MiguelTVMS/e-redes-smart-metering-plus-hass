# Contributing

Contributions are welcome! Please follow these guidelines:

## Development Setup

1. Fork the repository
2. Clone your fork
3. Install development dependencies:

   ```bash
   pip install -r requirements_dev.txt
   ```

## Code Quality

Before submitting a pull request, ensure your code passes all quality checks:

```bash
# Format code
black custom_components/
isort custom_components/

# Lint code
ruff check custom_components/

# Run tests
pytest tests/
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Follow the existing code style
4. Write clear commit messages
5. Submit a pull request with a clear description

## Reporting Issues

Please use the GitHub issue tracker to report bugs or request features.
Include as much detail as possible:

- Home Assistant version
- Integration version
- Steps to reproduce
- Error logs (if applicable)

Thank you for contributing!
