# Contributing to OpsMind

Thanks for your interest in contributing.

## How to contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run the test suite (`make test`)
5. Commit your changes
6. Push to your fork and open a pull request

## Development setup

```bash
git clone https://github.com/YOUR_USERNAME/OpsMind.git
cd OpsMind
make setup
make test
make run
```

## Code style

- Follow existing patterns in the codebase
- Add tests for new functionality in `tests/test_core.py`
- Keep modules focused — one responsibility per file

## Reporting bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behaviour
- Python version and OS

## Feature requests

Open an issue describing the use case and why it would be useful for manufacturing operations.
