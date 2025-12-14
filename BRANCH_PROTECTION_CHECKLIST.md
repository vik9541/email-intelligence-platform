# ✅ Branch Protection Checklist

Используйте этот чеклист при настройке Branch Protection Rule.

---

## 📍 URL для настройки
```
https://github.com/vik9541/email-intelligence-platform/settings/branches
```

---

## ✅ Настройки (отмечайте по мере выполнения)

### Базовые настройки

- [ ] Открыл страницу Settings → Branches
- [ ] Нажал "Add branch protection rule"
- [ ] Ввёл **Branch name pattern:** `main`

---

### Require a pull request before merging

- [ ] ✅ **Включил** "Require a pull request before merging"
- [ ] Установил **Require approvals:** `0` (т.к. один разработчик)
- [ ] ✅ **Включил** "Dismiss stale pull request approvals when new commits are pushed"
- [ ] ❌ **ВЫКЛЮЧИЛ** "Require review from Code Owners" (важно!)

---

### Require status checks to pass before merging

- [ ] ✅ **Включил** "Require status checks to pass before merging"
- [ ] ✅ **Включил** "Require branches to be up to date before merging"
- [ ] ✅ Добавил **Required status checks:**
  - [ ] `test-python`
  - [ ] `lint`
  - [ ] `test-docker`
  - [ ] `security`
  - [ ] `all-checks`

💡 **Как добавить:** В поле "Search for status checks" введите название и выберите из списка

---

### Require conversation resolution before merging

- [ ] ✅ **Включил** "Require conversation resolution before merging"

---

### Other restrictions

- [ ] ❌ **ВЫКЛЮЧИЛ** "Require deployments to succeed" (деплой ручной)
- [ ] ❌ **ВЫКЛЮЧИЛ** "Require signed commits" (опционально)
- [ ] ❌ **ВЫКЛЮЧИЛ** "Require linear history" (разрешаем merge commits)
- [ ] ❌ **ВЫКЛЮЧИЛ** "Include administrators" (нужен экстренный доступ)

---

### Rules applied to everyone

- [ ] ❌ **НЕ включал** "Do not allow bypassing the above settings"

---

### Allow force pushes / deletions

- [ ] ❌ **НЕ включал** "Allow force pushes"
- [ ] ❌ **НЕ включал** "Allow deletions"

---

### Сохранение

- [ ] Нажал **"Create"** внизу страницы
- [ ] Увидел сообщение об успешном создании правила

---

## 📋 Дополнительно: Auto-delete branches

**Settings → General → Pull Requests:**

- [ ] Прокрутил вниз до секции "Pull Requests"
- [ ] ✅ **Включил** "Automatically delete head branches"
- [ ] Нажал **"Save"**

---

## ✅ Тестирование (выполните все 3 теста)

### Тест 1: Push в main отклонён

```powershell
cd C:\Projects\email-service
git checkout -b test-protection
echo "test" > test.txt
git add test.txt
git commit -m "test: branch protection"
git push origin test-protection:main
```

**Ожидаемый результат:**
```
remote: error: GH006: Protected branch rule violations found
! [remote rejected] test-protection -> main (protected branch hook declined)
```

- [ ] ✅ Push в main отклонён

---

### Тест 2: PR требует checks

```powershell
# Push в feature ветку
git push origin test-protection
```

Затем на GitHub:
1. Перейдите в **Pull Requests**
2. Нажмите **"New pull request"**
3. base: `main` ← compare: `test-protection`
4. Нажмите **"Create pull request"**

**Проверьте:**

- [ ] Кнопка "Merge pull request" **СЕРАЯ** (неактивна)
- [ ] Видно статус: "All checks have passed" (или "Some checks haven't completed yet")
- [ ] После прохождения всех 5 checks → кнопка стала **ЗЕЛЁНОЙ**
- [ ] Можно нажать "Merge pull request"

---

### Тест 3: Auto-delete

После merge PR:

- [ ] Feature-ветка `test-protection` **исчезла** из списка веток
- [ ] Осталась только ветка `main`

---

## 🎉 Финальная проверка

**Откройте:**
```
https://github.com/vik9541/email-intelligence-platform/settings/branch_protection_rules
```

**Должно быть:**

- [ ] Есть правило для `main`
- [ ] Статус: ✅ Active
- [ ] 5 required status checks
- [ ] Require pull request reviews (0 approvals)

---

## ✅ Acceptance Criteria (финальная проверка)

- [ ] Нельзя push напрямую в main (только через PR)
- [ ] PR требует passing всех 5 checks
- [ ] PR НЕ требует approval (т.к. вы один)
- [ ] Dismiss stale approvals включен
- [ ] После merge ветка удаляется автоматически
- [ ] Conversation resolution обязателен
- [ ] Force push и deletion запрещены

---

## 📸 Итоговый скриншот настроек

После сохранения ваша страница должна выглядеть так:

```
Branch protection rule

Branch name pattern: main

✅ Require a pull request before merging
   Require approvals: 0
   ✅ Dismiss stale pull request approvals
   
✅ Require status checks to pass before merging
   ✅ Require branches to be up to date
   Required status checks in the past week:
   ✓ test-python
   ✓ lint
   ✓ test-docker
   ✓ security
   ✓ all-checks
   
✅ Require conversation resolution before merging

❌ Do not allow bypassing the above settings
```

---

## 🚀 Готово!

Если все пункты отмечены ✅ — защита настроена правильно!

**Время выполнения:** ~5 минут  
**Сложность:** Низкая  
**Статус:** ✅ Production-ready
