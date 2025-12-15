# Contributing to EasyMart v1

Thank you for considering contributing to EasyMart! We welcome contributions from the community.

## 🤝 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/YOUR_USERNAME/easymart-v1/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Node version, etc.)
   - Screenshots if applicable

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its use case
3. Explain why it would be valuable
4. Discuss implementation approach if you have ideas

### Pull Requests

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**:
   - Follow code style guidelines
   - Add tests if applicable
   - Update documentation
4. **Commit** with clear messages:
   ```bash
   git commit -m "feat: add product recommendation feature"
   ```
5. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** against `main`

---

## 📝 Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```bash
feat(chat): add multi-turn conversation support
fix(shopify): handle rate limiting correctly
docs(readme): update installation instructions
refactor(python): simplify intent detection logic
```

---

## 💻 Development Setup

### Prerequisites
- Node.js 18+
- pnpm 8+
- Python 3.11+
- Git

### Local Setup
```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/easymart-v1.git
cd easymart-v1

# 2. Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/easymart-v1.git

# 3. Install dependencies
cd backend-node
pnpm install

cd ../backend-python
pip install -r requirements.txt

# 4. Create .env files
cp backend-node/.env.example backend-node/.env
cp backend-python/.env.example backend-python/.env
# Edit with your credentials

# 5. Run tests
cd backend-node
pnpm test

# 6. Start development server
pnpm dev
```

---

## 🧪 Testing

### Node.js Backend
```bash
cd backend-node
pnpm test           # Run all tests
pnpm test:watch     # Watch mode
pnpm test:coverage  # Coverage report
```

### Python Backend
```bash
cd backend-python
pytest              # Run all tests
pytest -v           # Verbose
pytest --cov        # Coverage
```

---

## 📋 Code Style

### Node.js/TypeScript
- Use **ESLint** and **Prettier** (configured in project)
- Run before committing:
  ```bash
  pnpm lint
  pnpm format
  ```

### Python
- Follow **PEP 8**
- Use **Black** for formatting
- Use **mypy** for type checking
- Run before committing:
  ```bash
  black .
  mypy app/
  ```

---

## 🔒 Security

### Never commit:
- ❌ API keys or tokens
- ❌ `.env` files with real credentials
- ❌ Private keys or certificates
- ❌ Personal information

### Report security vulnerabilities:
Email: security@yourproject.com (create privately, not in issues)

---

## 📚 Documentation

When adding features, please update:
- `README.md` - If it affects setup or usage
- `docs/api-contracts.md` - For API changes
- `docs/openapi-assistant.yaml` - For Python API changes
- Code comments - For complex logic
- Type definitions - `src/types/shared.ts`

---

## 🏗️ Architecture Decisions

For significant changes:
1. Open an issue for discussion first
2. Get maintainer approval
3. Document decision in `docs/architecture-decisions.md`

---

## 🌳 Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch (if used)
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates
- `refactor/*` - Code refactoring

---

## 📦 Release Process

Maintainers handle releases:
1. Bump version in `package.json`
2. Update `CHANGELOG.md`
3. Create release tag
4. Deploy to production

---

## 👥 Code Review Process

All PRs require:
- ✅ Passing CI/CD checks
- ✅ At least 1 approving review
- ✅ No merge conflicts
- ✅ Updated documentation
- ✅ Tests passing

---

## 🎯 Priority Areas

We especially welcome contributions in:
- 🐛 **Bug fixes** - Always appreciated
- 📚 **Documentation** - Improve clarity
- 🧪 **Tests** - Increase coverage
- ♿ **Accessibility** - Widget improvements
- 🌍 **Internationalization** - Multi-language support
- 🚀 **Performance** - Optimization

---

## 💬 Questions?

- Open a [Discussion](https://github.com/YOUR_USERNAME/easymart-v1/discussions)
- Join our community chat (if available)
- Email: dev@yourproject.com

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for making EasyMart better! 🙏**
