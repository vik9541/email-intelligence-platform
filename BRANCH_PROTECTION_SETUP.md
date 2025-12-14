# 🛡️ ТЗ-3: Branch Protection & Code Review Rules

## 📋 Quick Start (2 минуты)

### Шаг 1: Откройте настройки

**Прямая ссылка:**
```
https://github.com/vik9541/email-intelligence-platform/settings/branches
```

---

### Шаг 2: Добавьте правило

Нажмите **"Add branch protection rule"**

---

### Шаг 3: Настройте правило

#### 🎯 Branch name pattern
```
main
```

#### ✅ Protect matching branches

##### 1. Require a pull request before merging
- ✅ **Включить**
- **Require approvals:** `0` (т.к. вы работаете один)
  - ⚠️ Если будет команда → поставьте `1` или `2`
- ✅ **Dismiss stale pull request approvals when new commits are pushed**
- ❌ **Require review from Code Owners** — ВЫКЛЮЧИТЬ (иначе заблокируетесь)
  - ⚠️ Включите позже когда будет команда

##### 2. Require status checks to pass before merging
- ✅ **Включить**
- ✅ **Require branches to be up to date before merging**

**Required status checks** (добавьте ВСЕ):
```
✓ test-python
✓ lint  
✓ test-docker
✓ security
✓ all-checks
```

⚠️ **Важно:** Эти названия должны совпадать с `name:` в workflows!

##### 3. Require conversation resolution before merging
- ✅ **Включить**

##### 4. Require deployments to succeed before merging
- ❌ **Выключить** (пока деплой ручной)

##### 5. Require signed commits
- ❌ **Выключить** (опционально, можно позже)

##### 6. Require linear history
- ❌ **Выключить** (разрешаем merge commits)

##### 7. Require merge queue
- ❌ **Выключить** (для малых проектов не нужно)

#### 🔒 Rules applied to everyone including administrators

- ❌ **НЕ включать** — администраторы должны иметь доступ в экстренных ситуациях

#### 🗑️ Other settings

##### Allow force pushes
- ❌ **НЕ включать** — запрещаем force push в main

##### Allow deletions
- ❌ **НЕ включать** — запрещаем удаление main

---

### Шаг 4: Дополнительные настройки репозитория

**Settings → General → Pull Requests:**

```
☑ Automatically delete head branches
```

Это удалит feature-ветку автоматически после merge PR.

---

### Шаг 5: Сохраните

Нажмите **"Create"** внизу страницы.

---

## ✅ Проверка настройки

### Тест 1: Push в main отклонен

```bash
cd C:\Projects\email-service
git checkout -b test-protection
echo "test" > test.txt
git add test.txt
git commit -m "test: branch protection"
git push origin test-protection:main
```

**Ожидаемый результат:**
```
remote: error: GH006: Protected branch rule violations found for refs/heads/main.
! [remote rejected] test-protection -> main (protected branch hook declined)
```

✅ Отлично! Protection работает.

---

### Тест 2: Создание PR

```bash
# Push в feature ветку
git push origin test-protection

# На GitHub:
# 1. Перейдите в Pull Requests
# 2. Нажмите "New pull request"
# 3. base: main ← compare: test-protection
# 4. Создайте PR
```

**Что должно быть:**
- 🟡 Кнопка "Merge" **НЕактивна** (серая)
- 📋 Под ней: "All checks have passed" (или waiting)
- ✅ После прохождения всех checks → кнопка станет зелёной

---

### Тест 3: Auto-delete branches

После merge PR:
- ✅ Feature-ветка `test-protection` должна исчезнуть автоматически
- ✅ Только `main` остаётся

---

## 🎯 Что защищено

| Действие | До Protection | После Protection |
|----------|---------------|-------------------|
| `git push origin main` | ✅ Разрешено | ❌ Запрещено |
| Merge PR без checks | ✅ Разрешено | ❌ Запрещено |
| Merge PR с failing tests | ✅ Разрешено | ❌ Запрещено |
| Force push в main | ✅ Разрешено | ❌ Запрещено |
| Удаление main | ✅ Разрешено | ❌ Запрещено |
| Создание PR | ✅ Разрешено | ✅ Разрешено |
| Merge PR с passing checks | ✅ Разрешено | ✅ Разрешено |

---

## 🔧 Настройки для разных сценариев

### 🧑‍💻 Один разработчик (сейчас)

```yaml
Require approvals: 0
Require review from Code Owners: NO
Require status checks: YES (all 5)
```

### 👥 Маленькая команда (2-3 человека)

```yaml
Require approvals: 1
Require review from Code Owners: YES
Require status checks: YES (all 5)
```

### 🏢 Большая команда (4+ человека)

```yaml
Require approvals: 2
Require review from Code Owners: YES
Require status checks: YES (all 5)
Require linear history: YES
```

---

## 📚 Проверка настроек

После сохранения откройте:
```
https://github.com/vik9541/email-intelligence-platform/settings/branch_protection_rules/<rule-id>
```

Должно быть:
```
✅ Branch name pattern: main
✅ Require pull request reviews before merging
✅ Require status checks to pass before merging
  ✓ test-python
  ✓ lint
  ✓ test-docker
  ✓ security
  ✓ all-checks
✅ Require conversation resolution before merging
❌ Do not allow bypassing the above settings
```

---

## 🚨 Экстренный доступ

Если нужно срочно исправить main (production bug):

### Вариант 1: Через PR (рекомендуется)
```bash
git checkout -b hotfix/critical-bug
# Исправляете баг
git commit -m "fix: critical bug"
git push origin hotfix/critical-bug
# Создайте PR, дождитесь checks, merge
```

### Вариант 2: Временно отключить protection (только админ)
1. Settings → Branches → Edit rule
2. Снимите галочки
3. Push в main
4. **ОБЯЗАТЕЛЬНО** верните галочки обратно!

---

## 📊 GitHub Actions Integration

Protection rule автоматически интегрируется с workflows:

```yaml
# .github/workflows/test.yml
jobs:
  test-python:    # ← Required check
  lint:           # ← Required check  
  test-docker:    # ← Required check
  security:       # ← Required check
  all-checks:     # ← Required check (gate)
```

Если **хотя бы один** провалится → merge **невозможен**.

---

## ✅ Acceptance Criteria

- [ ] Push напрямую в main запрещён
- [ ] PR создаётся без проблем
- [ ] PR требует passing всех 5 checks
- [ ] После прохождения checks → merge доступен
- [ ] После merge → feature-ветка удаляется
- [ ] Conversation resolution обязателен
- [ ] Force push в main запрещён

---

## 🎓 Best Practices

1. **Всегда создавайте feature-ветки:**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Регулярно sync с main:**
   ```bash
   git checkout main
   git pull
   git checkout feature/new-feature
   git merge main
   ```

3. **Пишите понятные commit messages:**
   ```bash
   git commit -m "feat: add email parsing"
   git commit -m "fix: handle null values"
   git commit -m "docs: update README"
   ```

4. **Проверяйте локально перед push:**
   ```bash
   pytest tests/ -v
   ruff check app/
   ```

5. **Используйте Draft PR для WIP:**
   - GitHub → New PR → "Create draft pull request"
   - Checks запустятся, но merge ещё недоступен

---

## 🔗 Полезные ссылки

- **Branch Protection Rules:** https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- **Status Checks:** https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks
- **CODEOWNERS:** https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners

---

**⏱️ Время выполнения:** 2 минуты  
**🔧 Сложность:** Низкая  
**✅ Готово к production:** Да
