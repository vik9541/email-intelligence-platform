# 🚀 MONDAY LAUNCH CHECKLIST (14 Dec 2025, 9:00 AM)

## 1. GITHUB VERIFICATION (5 мин)
- [ ] Репозиторий создан: github.com/vik9541/email-intelligence-platform
- [ ] Main ветка защищена (branch protection enabled)
- [ ] Все секреты добавлены (DOCKER_REGISTRY, DOCKER_USERNAME, DOCKER_PASSWORD, KUBECONFIG)
- [ ] test.yml passing (Actions tab зелёный ✅)
- [ ] deploy.yml готов к ручному запуску
- [ ] release.yml готов для тагов

## 2. CODE QUALITY (5 мин)
- [ ] 33 тестов passing (pytest)
- [ ] Coverage >= 60% (текущий 72%)
- [ ] Ruff linting clean (0 errors)
- [ ] MyPy type hints OK
- [ ] Docker build успешен (< 500MB)

## 3. INFRASTRUCTURE (10 мин)
- [ ] K8s кластер доступен (kubectl get nodes)
- [ ] 8 манифестов в k8s/ папке
- [ ] Deployment yaml синтаксически корректен
- [ ] Service конфиг правильный
- [ ] PersistentVolume claims определены

## 4. SECRETS & CONFIG (5 мин)
- [ ] .env.example существует
- [ ] KUBECONFIG добавлен в GitHub Secrets
- [ ] DOCKER_PASSWORD валиден (PAT с write:packages)
- [ ] SLACK_WEBHOOK_URL добавлен (если нужен)
- [ ] Все sensitive данные в .gitignore

## 5. DEPLOYMENT SCRIPTS (5 мин)
- [ ] MONDAY_DEPLOYMENT_SCRIPT.sh существует и executable
- [ ] healthcheck.sh готов
- [ ] Все paths в скриптах правильные
- [ ] Скрипты протестированы локально (dry-run)

## 6. DOCUMENTATION (5 мин)
- [ ] README.md с Quick Start
- [ ] DEPLOYMENT.md полный и понятный
- [ ] GO_LIVE_CHECKLIST.md подробный
- [ ] WEEK7_PLAN.md синхронизирован
- [ ] Все ссылки рабочие (не 404)

## 7. MONITORING & ALERTS (5 мин)
- [ ] Prometheus конфиг правильный
- [ ] Grafana dashboard импортирован
- [ ] Alert rules определены
- [ ] Slack уведомления настроены
- [ ] Log aggregation готова (ELK/Loki)

## 8. DATABASE (5 мин)
- [ ] PostgreSQL миграции готовы
- [ ] Redis кластер доступен
- [ ] pgvector расширение установлено
- [ ] Backup strategy документирована

## 9. FINAL SMOKE TESTS (10 мин)
- [ ] curl http://localhost:8000/health (локально)
- [ ] Docker image собирается: docker build -t test .
- [ ] K8s deployment dry-run: kubectl apply -f k8s/ --dry-run=client
- [ ] GitHub Actions все job'ы passing
- [ ] Release workflow готов (git tag v1.0.0 --dry-run)

## 10. TEAM COMMUNICATION (5 мин)
- [ ] GitHub репо ссылка отправлена команде
- [ ] Документация доступна всем
- [ ] Slack канал создан для уведомлений
- [ ] Contingency план согласован (rollback process)
- [ ] Ответственные за мониторинг назначены

## TOTAL TIME: 60 мин

## ✅ ACCEPTANCE
Все чекбоксы должны быть отмечены перед 21:00 (воскресенье)
После 21:00 → зелёная линия для понедельника 9:00 AM

---

## 📋 VERIFICATION COMMANDS

### GitHub Verification
```bash
gh repo view vik9541/email-intelligence-platform
gh secret list
```

### Code Quality
```bash
cd C:\Projects\email-service
python -m pytest tests/ -v --cov=app
python -m ruff check app/ tests/
python -m mypy app/ --ignore-missing-imports
docker build -t email-service:test .
```

### Infrastructure
```bash
kubectl get nodes
kubectl get pods -n default
ls -la k8s/
kubectl apply -f k8s/ --dry-run=client
```

### Scripts Check
```bash
ls -la scripts/
bash scripts/MONDAY_DEPLOYMENT_SCRIPT.sh --dry-run
bash scripts/healthcheck.sh
```

### Documentation
```bash
ls -la docs/
grep -r "TODO" docs/ README.md DEPLOYMENT.md
```

### Final Smoke Test
```bash
# Local Docker test
docker run -d -p 8000:8000 email-service:test
sleep 5
curl http://localhost:8000/health
docker ps | grep email-service
```

---

## 🚨 CRITICAL PATHS TO VERIFY

### 1. GitHub Actions Must Be Green
- Navigate to: https://github.com/vik9541/email-intelligence-platform/actions
- Check latest workflow run
- All 5 jobs must pass: ✅ test-python ✅ lint ✅ test-docker ✅ security ✅ all-checks

### 2. Branch Protection Active
- Settings → Branches → main
- "Require pull request reviews before merging" = ON
- "Require status checks to pass" = ON (5 checks selected)
- "Require linear history" = ON

### 3. Secrets Configuration
Required secrets in GitHub Settings → Secrets and variables → Actions:
- `DOCKER_REGISTRY`: ghcr.io
- `DOCKER_USERNAME`: vik9541
- `DOCKER_PASSWORD`: ghp_XXXXXXXXXX (GitHub PAT with write:packages)
- `KUBECONFIG`: [base64 encoded kubeconfig]

### 4. K8s Cluster Readiness
```bash
kubectl cluster-info
kubectl get nodes
kubectl get namespaces
kubectl get all -n default
```

---

## 🎯 MONDAY MORNING PROCEDURE (9:00 AM)

### Step 1: Final Verification (5 min)
```bash
cd C:\Projects\email-service
git pull origin main
python -m pytest tests/ -v
```

### Step 2: Execute Deployment (10 min)
```bash
bash ./scripts/MONDAY_DEPLOYMENT_SCRIPT.sh
```

### Step 3: Monitor Deployment (15 min)
```bash
kubectl get pods -w
kubectl logs -f deployment/email-service
curl http://<EXTERNAL-IP>/health
```

### Step 4: Verify All Services (10 min)
- ✅ PostgreSQL: Connected
- ✅ Redis: Connected
- ✅ Prometheus: Scraping metrics
- ✅ Grafana: Dashboard visible
- ✅ API: Responding to /health

---

## 📅 TIMELINE

### ВОСКРЕСЕНЬЕ 19:04 (СЕЙЧАС)
- [x] Create MONDAY_LAUNCH_CHECKLIST.md
- [ ] Run all verification commands
- [ ] Mark all checkboxes ✅
- [ ] Commit and push

### ВОСКРЕСЕНЬЕ 21:00 (DEADLINE)
- [ ] All GitHub Actions green
- [ ] All checklist items verified
- [ ] Sleep well 😴

### ПОНЕДЕЛЬНИК 09:00 (DEPLOY)
- [ ] Execute MONDAY_DEPLOYMENT_SCRIPT.sh
- [ ] Monitor deployment
- [ ] Verify all services

### ПЯТНИЦА 10:00 (GO LIVE)
- [ ] Create release tag: `git tag v1.0.0`
- [ ] Push tag: `git push --tags`
- [ ] Release automation triggers
- [ ] 🎉 PRODUCTION LIVE!

---

## 🔄 ROLLBACK PLAN (IF NEEDED)

If deployment fails on Monday:
```bash
# 1. Rollback K8s deployment
kubectl rollout undo deployment/email-service

# 2. Check previous version
kubectl rollout history deployment/email-service

# 3. Scale down if needed
kubectl scale deployment email-service --replicas=0

# 4. Investigate logs
kubectl logs -f deployment/email-service --previous

# 5. Fix and redeploy
# (fix code, commit, push, re-run deployment script)
```

---

## 📞 CONTACTS & ESCALATION

**Project Owner**: vik9541  
**Repository**: github.com/vik9541/email-intelligence-platform  
**Monitoring**: Grafana Dashboard  
**Alerts**: Slack #email-service-alerts  

**Escalation Path**:
1. Check logs: `kubectl logs -f deployment/email-service`
2. Check metrics: Grafana dashboard
3. Review GitHub Actions: Recent workflow runs
4. Execute rollback if critical
5. Document incident in GitHub Issues

---

## ✅ SIGN-OFF

- [ ] **DevOps Lead**: All infrastructure ready
- [ ] **Tech Lead**: All code quality checks passed
- [ ] **Product Owner**: Documentation complete
- [ ] **Security**: All secrets configured
- [ ] **QA**: All tests passing

**Date**: ____________  
**Approved by**: ____________  
**Status**: 🟢 READY FOR MONDAY DEPLOYMENT
