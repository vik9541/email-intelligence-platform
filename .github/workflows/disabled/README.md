# Security Scanning - Временно отключен

Security scan workflow (`security-scan.yml`) временно перемещён в `.github/workflows/disabled/`.

## Причина

Security scans требуют:
1. GitHub Advanced Security (платная фича для приватных репо)
2. Правильную конфигурацию SARIF upload
3. Обновлённые версии actions

## Текущие проблемы

- ❌ `actions/upload-artifact@v3` устарел (нужен v4)
- ❌ Secret scanning требует включения в настройках репо
- ❌ CodeQL требует больше времени для анализа
- ❌ Некоторые scans требуют платные фичи

## Что работает вместо этого

✅ **Основные проверки:**
- `test.yml` - unit тесты (33 passing)
- `lint.yml` - Ruff linting
- Pre-commit hooks (`.pre-commit-config.yaml`)

✅ **Локальный security scanning:**
```bash
# Запусти локально перед коммитом
bandit -r app/
ruff check app/
pip-audit
```

## Когда включить обратно

Перед production deploy:
1. Обнови actions в security-scan.yml до v4
2. Включи GitHub Advanced Security (Settings → Security)
3. Настрой SARIF upload правильно
4. Верни файл: `mv .github/workflows/disabled/security-scan.yml .github/workflows/`

## Альтернатива

Используй локальные инструменты из `scripts/pre-commit-security-check.sh`:
```bash
bash scripts/pre-commit-security-check.sh
```

---

**Статус:** Security scanning отключен временно, но основные проверки (тесты + линтинг) работают.
