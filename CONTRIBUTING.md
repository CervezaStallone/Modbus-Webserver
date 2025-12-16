# Contributing to Modbus Web Server

Thank you for your interest in contributing to Modbus Web Server! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior by opening an issue.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Provide specific examples to demonstrate the steps
- Describe the behavior you observed and what you expected to see
- Include screenshots if relevant
- Include your environment details (OS, Python version, browser)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- Use a clear and descriptive title
- Provide a detailed description of the suggested enhancement
- Explain why this enhancement would be useful
- List any similar features in other applications if applicable

### Code Contributions

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Write or update tests as needed
5. Ensure all tests pass
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Redis server
- Git

### Setting Up Your Development Environment

```bash
# Clone your fork
git clone https://github.com/your-username/modbus-webserver.git
cd modbus-webserver

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Copy environment variables
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

In separate terminals, start the required services:

```bash
# Celery worker
celery -A modbus_webserver worker -l info

# Celery beat
celery -A modbus_webserver beat -l info
```

## Coding Standards

### Python Style Guide

- Follow PEP 8 style guide
- Use meaningful variable and function names
- Maximum line length of 120 characters
- Use type hints where applicable
- Write docstrings for functions and classes

### Django Best Practices

- Follow Django coding style
- Use Django ORM instead of raw SQL when possible
- Keep views thin, move business logic to services
- Use Django's built-in security features
- Keep templates DRY (Don't Repeat Yourself)

### Code Quality

Before submitting your code:

```bash
# Format code with black
black modbus_app/

# Check code style with flake8
flake8 modbus_app/

# Sort imports with isort
isort modbus_app/

# Run type checking with mypy (if configured)
mypy modbus_app/
```

### Testing

- Write tests for new features
- Update tests when modifying existing features
- Ensure all tests pass before submitting PR
- Aim for high code coverage

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=modbus_app --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py
```

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Changes to build process or auxiliary tools

### Examples

```
feat(dashboard): add real-time gauge widget

Add a new gauge widget type to the dashboard that displays
real-time values with configurable min/max ranges and color zones.

Closes #123
```

```
fix(modbus): resolve TCP connection timeout issue

Increase default timeout and add retry logic for TCP connections
to improve reliability with slow responding devices.

Fixes #456
```

## Pull Request Process

1. **Update Documentation**: Update the README.md or relevant documentation with details of changes if applicable.

2. **Update Tests**: Add or update tests to cover your changes.

3. **Follow Code Style**: Ensure your code follows the project's coding standards.

4. **Commit Messages**: Use clear and descriptive commit messages following our guidelines.

5. **Pull Request Description**: Provide a clear description of the changes:
   - What problem does this solve?
   - How does it solve it?
   - Any breaking changes?
   - Related issues?

6. **Review Process**: 
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Once approved, a maintainer will merge your PR

7. **CI/CD**: Ensure all continuous integration checks pass.

### Pull Request Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code comments added where needed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No new warnings generated
```

## Project Structure

Understanding the project structure will help you navigate the codebase:

```
modbus_app/
├── models.py          # Database models
├── views.py           # View logic
├── serializers.py     # API serializers
├── consumers.py       # WebSocket consumers
├── tasks.py           # Celery background tasks
├── services/          # Business logic layer
│   ├── modbus_driver.py
│   ├── connection_manager.py
│   └── alarm_checker.py
├── utils/             # Utility functions
└── templates/         # HTML templates
```

## Getting Help

- Check existing issues and pull requests
- Read the documentation in the `/docs` folder
- Review the README.md for basic setup and usage
- Ask questions by opening an issue with the "question" label

## Recognition

Contributors will be recognized in our README.md file. Thank you for helping make this project better!

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).
