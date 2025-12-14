# Contributing to Email Intelligence Platform

First off, thank you for considering contributing to Email Intelligence Platform! 🎉

This document provides guidelines and steps for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Getting Help](#getting-help)

---

## 📜 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to conduct@example.com.

### Our Standards

- **Be respectful**: Treat everyone with respect and consideration
- **Be constructive**: Provide helpful feedback and suggestions
- **Be collaborative**: Work together towards common goals
- **Be inclusive**: Welcome newcomers and help them get started

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- A GitHub account

### Types of Contributions

We welcome many types of contributions:

- 🐛 **Bug fixes**: Found a bug? We'd love a fix!
- ✨ **New features**: Have an idea? Let's discuss it!
- 📚 **Documentation**: Help improve our docs
- 🧪 **Tests**: More tests are always welcome
- 🎨 **UI/UX**: Improvements to developer experience
- 🔧 **Tooling**: Build, CI/CD, developer tools

---

## 💻 Development Setup

### 1. Fork and Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/email-intelligence-platform.git
cd email-intelligence-platform

# Add upstream remote
git remote add upstream https://github.com/username/email-intelligence-platform.git
```

### 2. Set Up Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Install Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### 4. Verify Setup

```bash
# Run tests
pytest

# Run linting
ruff check app/

# Run type checking
mypy app/
```

---

## 🔧 Making Changes

### 1. Create a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bugs
git checkout -b fix/bug-description
```

### Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/description` | `feature/add-sentiment-analysis` |
| Bug Fix | `fix/description` | `fix/kafka-connection-timeout` |
| Documentation | `docs/description` | `docs/update-api-reference` |
| Refactor | `refactor/description` | `refactor/extract-base-class` |
| Test | `test/description` | `test/add-classifier-tests` |

### 2. Make Your Changes

- Write clean, readable code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific tests
pytest tests/unit/test_analyzer.py -v

# Run linting
ruff check app/

# Run type checking
mypy app/
```

---

## 📝 Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style changes (formatting, etc.) |
| `refactor` | Code refactoring |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |
| `perf` | Performance improvements |
| `ci` | CI/CD changes |

### Examples

```bash
# Feature
git commit -m "feat(analyzer): add multi-language sentiment analysis"

# Bug fix
git commit -m "fix(kafka): handle connection timeout gracefully"

# Documentation
git commit -m "docs(readme): add deployment section"

# With body
git commit -m "feat(api): add batch processing endpoint

- Add POST /api/v1/batch endpoint
- Support up to 1000 emails per request
- Include progress tracking

Closes #123"
```

---

## 🔀 Pull Request Process

### 1. Before Submitting

- [ ] Tests pass locally (`pytest`)
- [ ] Code is linted (`ruff check app/`)
- [ ] Types check (`mypy app/`)
- [ ] Documentation updated (if needed)
- [ ] Commits follow conventions
- [ ] Branch is up to date with `main`

### 2. Create Pull Request

1. Push your branch to your fork
2. Go to the original repository
3. Click "New Pull Request"
4. Select your branch
5. Fill out the PR template

### 3. PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing
How has this been tested?

## Checklist
- [ ] Tests pass
- [ ] Code is linted
- [ ] Documentation updated
- [ ] Conventional commits used
```

### 4. Review Process

1. **Automated checks** must pass
2. **Code review** by at least one maintainer
3. **Address feedback** if requested
4. **Squash and merge** when approved

### 5. After Merge

```bash
# Update your local main
git checkout main
git pull upstream main

# Delete feature branch
git branch -d feature/your-feature-name
```

---

## 🎨 Code Style

### Python Style Guide

We use **Ruff** for linting and **Black** for formatting.

```python
# Good ✅
def analyze_email(
    email: Email,
    options: AnalysisOptions | None = None,
) -> AnalysisResult:
    """Analyze an email for sentiment and intent.
    
    Args:
        email: The email to analyze
        options: Optional analysis configuration
        
    Returns:
        Analysis result with sentiment, urgency, and intent
        
    Raises:
        ValidationError: If email is invalid
    """
    if options is None:
        options = AnalysisOptions()
    
    sentiment = self._analyze_sentiment(email.body)
    urgency = self._detect_urgency(email.subject, email.body)
    
    return AnalysisResult(
        sentiment=sentiment,
        urgency=urgency,
        confidence=0.95,
    )


# Bad ❌
def analyze_email(email,options=None):
    if options==None:
        options={}
    sentiment=self._analyze_sentiment(email.body)
    urgency=self._detect_urgency(email.subject,email.body)
    return {"sentiment":sentiment,"urgency":urgency}
```

### Key Style Points

1. **Type hints**: Required for all functions
2. **Docstrings**: Required for public functions/classes
3. **Line length**: Max 88 characters (Black default)
4. **Imports**: Sorted with isort
5. **Naming**: snake_case for functions/variables, PascalCase for classes

### Running Style Checks

```bash
# Format code
black app/ tests/

# Check linting
ruff check app/ tests/

# Fix auto-fixable issues
ruff check --fix app/ tests/

# Type checking
mypy app/
```

---

## 🧪 Testing

### Test Structure

```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_analyzer.py
│   ├── test_classifier.py
│   └── test_executor.py
├── integration/       # Tests with dependencies
│   ├── test_kafka.py
│   └── test_database.py
└── e2e/              # Full flow tests
    └── test_email_flow.py
```

### Writing Tests

```python
import pytest
from app.services.email_analyzer import EmailAnalyzer


class TestEmailAnalyzer:
    """Tests for EmailAnalyzer service."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return EmailAnalyzer()
    
    def test_analyze_positive_sentiment(self, analyzer):
        """Should detect positive sentiment in happy email."""
        # Arrange
        email = Email(
            subject="Thank you!",
            body="Great service, very happy with my order!",
        )
        
        # Act
        result = analyzer.analyze(email)
        
        # Assert
        assert result.sentiment == "positive"
        assert result.confidence >= 0.8
    
    @pytest.mark.parametrize("body,expected_urgency", [
        ("Please help ASAP!", "critical"),
        ("Urgent matter", "high"),
        ("When you have time", "low"),
    ])
    def test_urgency_detection(self, analyzer, body, expected_urgency):
        """Should detect correct urgency level."""
        email = Email(subject="Test", body=body)
        result = analyzer.analyze(email)
        assert result.urgency == expected_urgency
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific file
pytest tests/unit/test_analyzer.py

# Specific test
pytest tests/unit/test_analyzer.py::TestEmailAnalyzer::test_analyze_positive_sentiment

# With markers
pytest -m "not slow"

# Verbose
pytest -v
```

---

## 📚 Documentation

### Where to Document

| What | Where |
|------|-------|
| API endpoints | Docstrings + OpenAPI |
| Functions/Classes | Docstrings |
| Architecture | `docs/` folder |
| Usage examples | README.md |
| Deployment | `docs/DEPLOYMENT.md` |

### Docstring Format

We use Google-style docstrings:

```python
def process_email(
    email: Email,
    timeout: float = 30.0,
) -> ProcessingResult:
    """Process an email through the analysis pipeline.
    
    This function runs the email through sentiment analysis,
    classification, and action execution.
    
    Args:
        email: The email to process.
        timeout: Maximum processing time in seconds.
        
    Returns:
        ProcessingResult containing analysis and any executed actions.
        
    Raises:
        TimeoutError: If processing exceeds timeout.
        ValidationError: If email format is invalid.
        
    Example:
        >>> email = Email(subject="Help", body="Need assistance")
        >>> result = process_email(email)
        >>> print(result.category)
        'SUPPORT'
    """
```

---

## ❓ Getting Help

### Questions?

- 💬 **Slack**: #email-intelligence-platform
- 📧 **Email**: dev-team@example.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/username/email-intelligence-platform/issues)

### First Time Contributing?

Look for issues labeled:
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `documentation` - Documentation improvements

### Response Times

- **Issues**: 1-2 business days
- **PRs**: 2-3 business days
- **Security issues**: 24 hours

---

## 🏆 Recognition

Contributors are recognized in:
- README.md Contributors section
- Release notes
- Annual contributor highlights

---

Thank you for contributing! 🙏

*Last updated: December 2025*
