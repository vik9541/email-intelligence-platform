# 🚀 Инструкция по ручному деплою

## ✅ Текущий статус CI/CD

| Pipeline | Статус | Триггер |
|----------|--------|---------|
| Test Suite | ✅ Автоматически | Push в main, PR |
| Deploy | 🔧 Вручную | workflow_dispatch |

---

## 🎯 Зачем ручной deploy?

На этапе первичной настройки deploy запускается **только вручную**, чтобы:
- ✅ Убедиться что Kubernetes кластер доступен
- ✅ Проверить правильность всех секретов
- ✅ Протестировать Docker registry
- ✅ Избежать автоматических ошибок деплоя

---

## 🚀 Как запустить deploy вручную

### Шаг 1: Откройте GitHub Actions

https://github.com/vik9541/email-intelligence-platform/actions

### Шаг 2: Выберите workflow

Слева выберите: **"Deploy to Kubernetes"**

### Шаг 3: Запустите workflow

1. Нажмите **"Run workflow"** (справа сверху)
2. Заполните параметры:
   - **Branch:** `main`
   - **Environment:** `staging` (для теста)
   - **Image tag:** `latest`
   - **Dry run:** ✅ `true` (для первого запуска!)
3. Нажмите **"Run workflow"**

---

## 🧪 Первый запуск (Dry Run)

**Dry run** — это "холостой прогон" без реальных изменений.

Он покажет:
- ✅ Какие команды будут выполнены
- ✅ Доступен ли Kubernetes кластер
- ✅ Корректны ли манифесты
- ❌ Ошибки (если есть) БЕЗ реального деплоя

**После успешного dry run** можно запустить реальный deploy с `Dry run: false`.

---

## 📋 Что происходит при deploy

### Build Job (только для push)
- Собирает Docker образ
- Пушит в `ghcr.io/vik9541/email-service`
- Тегирует как `sha-<commit>` и `latest`

### Deploy Job
```bash
1. Подключается к Kubernetes
2. Применяет манифесты:
   - namespace.yaml
   - configmap.yaml
   - networkpolicy.yaml
   - deployment.yaml
   - service.yaml
   - ingress.yaml
   - hpa.yaml
3. Ждёт rollout (макс 5 мин)
4. Проверяет health endpoints
5. Создаёт аннотацию с версией
```

---

## 🔍 Проверка после deploy

### 1. Проверить поды
```bash
kubectl get pods -n email-service
```

### 2. Проверить логи
```bash
kubectl logs -n email-service -l app.kubernetes.io/name=email-service --tail=50
```

### 3. Проверить сервис
```bash
kubectl get svc -n email-service
```

### 4. Тест health endpoint
```bash
kubectl port-forward svc/email-service 8080:8000 -n email-service
curl http://localhost:8080/health
```

---

## ⚠️ Troubleshooting

### Deploy failed: "connection refused"

**Проблема:** GitHub Actions не может подключиться к кластеру

**Решение:**
```bash
# 1. Проверьте что кластер запущен
doctl kubernetes cluster list

# 2. Обновите kubeconfig
doctl kubernetes cluster kubeconfig save 3fbf1852-b6c2-437f-b86e-9aefe81d2ec6

# 3. Перегенерируйте base64 и обновите KUBECONFIG в GitHub Secrets
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("$env:USERPROFILE\.kube\config"))
```

---

### Docker push failed: "unauthorized"

**Проблема:** Не хватает прав для push в ghcr.io

**Решение:**
1. Проверьте что PAT токен имеет `write:packages`
2. Обновите `DOCKER_PASSWORD` в GitHub Secrets
3. Запустите workflow снова

---

### Pods в CrashLoopBackOff

**Проблема:** Приложение не стартует

**Решение:**
```bash
# Посмотрите логи
kubectl logs -n email-service <pod-name>

# Часто это из-за отсутствия переменных окружения
# Проверьте configmap.yaml и secrets.yaml
```

---

## 🔄 Включить автоматический deploy

Когда всё работает стабильно, можно включить авто-deploy:

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches:
      - main  # Добавьте эту секцию обратно
  workflow_dispatch:
    # ...
```

---

## 📚 Полезные ссылки

- **GitHub Actions:** https://github.com/vik9541/email-intelligence-platform/actions
- **Kubernetes Dashboard:** https://cloud.digitalocean.com/kubernetes/clusters
- **Container Registry:** https://github.com/vik9541?tab=packages

---

## ✅ Чеклист перед первым deploy

- [ ] Test Suite проходит ✅
- [ ] Все 4 GitHub Secrets добавлены
- [ ] Kubernetes кластер запущен в DigitalOcean
- [ ] KUBECONFIG актуален
- [ ] Запущен dry run успешно
- [ ] Проверены логи dry run
- [ ] Готов к реальному deploy

**После выполнения всех пунктов** → запускайте с `Dry run: false`! 🚀
