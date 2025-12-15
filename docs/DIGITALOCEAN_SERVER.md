# DigitalOcean Server - Email Intelligence Platform

**Дата:** 15 декабря 2025  
**Проект:** 97v.ru Email Intelligence Platform  
**Провайдер:** DigitalOcean  

---

## 🔑 Доступ к серверу

### Credentials Location

**⚠️ ВАЖНО:** Все credentials хранятся в **GitHub Secrets** репозитория.

Путь к настройкам:
```
GitHub Repository → Settings → Secrets and variables → Actions
```

### Необходимые Secrets

```bash
# SSH доступ
DO_SSH_HOST          # IP адрес или hostname сервера
DO_SSH_USER          # Username (обычно root или ubuntu)
DO_SSH_PORT          # SSH порт (по умолчанию 22)
DO_SSH_PRIVATE_KEY   # Private SSH key для подключения

# API доступ (опционально)
DO_API_TOKEN         # DigitalOcean API token
```

---

## 🖥️ Подключение к серверу

### Вариант 1: SSH с использованием ключа из GitHub Secrets

```bash
# 1. Получить SSH ключ из GitHub Secrets (вручную скопировать)
# GitHub → Settings → Secrets → DO_SSH_PRIVATE_KEY

# 2. Сохранить ключ локально
cat > ~/.ssh/digitalocean_key << 'EOF'
[вставить содержимое DO_SSH_PRIVATE_KEY]
EOF

# 3. Установить правильные permissions
chmod 600 ~/.ssh/digitalocean_key

# 4. Подключиться
ssh -i ~/.ssh/digitalocean_key $DO_SSH_USER@$DO_SSH_HOST
```

### Вариант 2: Добавить в SSH config

```bash
# Создать/редактировать ~/.ssh/config
cat >> ~/.ssh/config << 'EOF'
Host do-email-service
    HostName [IP из DO_SSH_HOST]
    User [значение DO_SSH_USER]
    Port [значение DO_SSH_PORT, обычно 22]
    IdentityFile ~/.ssh/digitalocean_key
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF

# Подключение теперь просто:
ssh do-email-service
```

### Вариант 3: Через DigitalOcean Console

```
1. Зайти на https://cloud.digitalocean.com/
2. Droplets → Выбрать сервер
3. Access → Launch Droplet Console
```

---

## 🧪 Тестирование сервера

### Шаг 1: Подключиться к серверу

```bash
ssh do-email-service
```

### Шаг 2: Клонировать репозиторий (если еще не сделано)

```bash
# Проверить, есть ли уже проект
ls -la /opt/email-service || ls -la ~/email-service

# Если нет - клонировать
cd /opt
sudo git clone https://github.com/[your-username]/email-service.git
# или
cd ~
git clone https://github.com/[your-username]/email-service.git
```

### Шаг 3: Запустить Quick Check

```bash
cd /opt/email-service  # или ~/email-service

# Дать права на выполнение
chmod +x deploy/scripts/*.sh

# Быстрая проверка
./deploy/scripts/quick-check.sh
```

**Ожидаемый вывод (30 секунд):**
```
================================
⚡ QUICK SERVER CHECK
================================

=== SYSTEM ===
OS: Ubuntu 22.04 LTS
Kernel: 5.15.0-99-generic
Uptime: up 45 days

=== CPU ===
Cores: 4
Load: 0.87, 0.92, 0.85

=== MEMORY ===
Total: 8Gi, Used: 3.2Gi (40%), Available: 4.5Gi

=== DISK ===
Total: 160G, Used: 45G (29%), Free: 110G

=== DOCKER ===
✅ Installed: Docker version 24.0.6
Containers: 5 running / 8 total

Running:
  postgres: postgres:16.1
  redis: redis:7.2-alpine
  nginx: nginx:1.25
  api: email-service:latest
  worker: email-service:latest

=== DOCKER COMPOSE ===
✅ Docker Compose version v2.20.0

=== LISTENING PORTS ===
22 80 443 5432 6379 8000

=== CRITICAL SERVICES ===
✅ ssh: running
✅ nginx: running (Docker)
✅ postgresql: running (Docker)
✅ redis: running (Docker)

=== NETWORK ===
Hostname: email-service-prod
IP: 167.99.123.45
✅ Internet: OK
✅ DNS: OK

=== TOP PROCESSES (by memory) ===
  postgres   8.5%   1.2G  postgres
  python     5.2%   680M  uvicorn
  redis      2.1%   280M  redis-server

=== HEALTH STATUS ===
✅ Disk: 29%
✅ Memory: 40%
✅ Load: 0.87 avg (4 cores)

================================
```

### Шаг 4: Запустить Full Analysis

```bash
# Полный анализ (2-3 минуты)
./deploy/scripts/00-analyze-server.sh

# Результат сохранится в:
# /tmp/server-analysis-YYYYMMDD-HHMMSS.txt

# Посмотреть результат
cat /tmp/server-analysis-*.txt | less

# Или скачать на локальную машину
scp do-email-service:/tmp/server-analysis-*.txt ./
```

---

## 📊 Интерпретация результатов

### ✅ Здоровый сервер (всё хорошо)

```
✅ Disk: 29%           # < 80% - OK
✅ Memory: 40%         # < 80% - OK  
✅ Load: 0.87 avg      # < количества cores - OK
✅ Internet: OK
✅ DNS: OK
✅ All services running normally
```

### ⚠️ Требует внимания

```
⚠️  WARNING: Disk usage is high (85%)
⚠️  WARNING: Memory usage is high (88%)
⚠️  WARNING: System load is high (6.5 avg, 4 cores)
```

**Действия:**
1. **Disk > 80%:** Очистить Docker images, логи
2. **Memory > 80%:** Проверить утечки памяти, перезапустить сервисы
3. **Load > CPU count:** Оптимизировать процессы

### 🔴 Критическая ситуация

```
🔴 CRITICAL: Disk usage is very high (95%)
❌ Internet connectivity: FAILED
❌ DNS resolution: FAILED
⚠️  Failed services: 3
```

**Немедленные действия:**
1. Освободить место на диске
2. Проверить сетевое подключение
3. Перезапустить failed сервисы

---

## 🔧 Типичные команды для диагностики

### Проверка Docker контейнеров

```bash
# Все контейнеры
docker ps -a

# Логи конкретного контейнера
docker logs api
docker logs postgres

# Перезапуск контейнера
docker restart api

# Использование ресурсов
docker stats --no-stream
```

### Проверка дискового пространства

```bash
# Основное
df -h

# Детально по директориям
du -sh /* | sort -rh | head -10
du -sh /var/lib/docker

# Очистка Docker
docker system prune -af
docker volume prune -f
```

### Проверка логов

```bash
# System logs
sudo journalctl -xe

# Nginx logs
sudo journalctl -u nginx

# Docker logs
docker logs --tail 100 api
docker logs --tail 100 postgres
```

### Проверка сети

```bash
# Открытые порты
sudo ss -tlnp | grep LISTEN

# Проверка конкретного порта
sudo lsof -i :8000

# Тест подключения
curl http://localhost:8000/health
curl https://api.97v.ru/health
```

---

## 🚀 Деплой через GitHub Actions

### Автоматический деплой

При push в `main` ветку:

```yaml
# .github/workflows/deploy.yml
- Запускается CI/CD
- Билдится Docker образ
- Деплоится на сервер через SSH
- Перезапускаются контейнеры
```

### Ручной деплой

```bash
# На локальной машине
git push origin main

# GitHub Actions автоматически:
# 1. Собирает образ
# 2. Подключается к серверу (используя DO_SSH_* secrets)
# 3. Обновляет код
# 4. Перезапускает docker-compose
```

---

## 📋 Checklist после подключения

```bash
# 1. Проверить систему
./deploy/scripts/quick-check.sh

# 2. Проверить Docker
docker ps
docker-compose ps

# 3. Проверить логи
docker-compose logs --tail=50

# 4. Проверить health endpoint
curl http://localhost:8000/health

# 5. Проверить базу данных
docker exec -it postgres psql -U postgres -c "SELECT version();"

# 6. Проверить Redis
docker exec -it redis redis-cli ping

# 7. Проверить диск
df -h

# 8. Проверить память
free -h

# 9. Проверить процессы
top -bn1 | head -20

# 10. Проверить сеть
ping -c 3 google.com
```

---

## 🔐 Безопасность

### SSH ключи

```bash
# Проверить текущие SSH ключи на сервере
cat ~/.ssh/authorized_keys

# Добавить новый ключ (если нужно)
echo "ssh-rsa AAAA..." >> ~/.ssh/authorized_keys

# Проверить права
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### Firewall

```bash
# Проверить статус UFW
sudo ufw status

# Открыть порты (если нужно)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Включить firewall
sudo ufw enable
```

### SSL сертификаты

```bash
# Проверить сертификаты Let's Encrypt
sudo certbot certificates

# Обновить сертификаты
sudo certbot renew --dry-run
```

---

## 📁 Структура на сервере

### Предполагаемая структура

```
/opt/email-service/              # Основной проект
├── app/                         # FastAPI приложение
├── deploy/                      # Deployment скрипты
│   ├── docker/                  # Docker configs
│   └── scripts/                 # Utility scripts
├── docs/                        # Документация
├── tests/                       # Тесты
├── docker-compose.yml           # Docker Compose config
├── Dockerfile                   # Docker image definition
└── requirements.txt             # Python dependencies

/var/lib/docker/                 # Docker data
├── containers/                  # Контейнеры
├── images/                      # Образы
└── volumes/                     # Volumes (БД данные)

/var/log/                        # Логи
├── nginx/                       # Nginx логи
└── docker/                      # Docker логи
```

---

## 🆘 Troubleshooting

### Проблема: Не могу подключиться по SSH

```bash
# Проверить доступность сервера
ping [DO_SSH_HOST]

# Проверить порт SSH
nmap -p 22 [DO_SSH_HOST]

# Проверить права на ключ
ls -la ~/.ssh/digitalocean_key
# Должно быть: -rw------- (600)

# Verbose режим SSH
ssh -v -i ~/.ssh/digitalocean_key user@host
```

### Проблема: Контейнеры не запускаются

```bash
# Проверить логи
docker-compose logs

# Проверить конфигурацию
docker-compose config

# Пересоздать контейнеры
docker-compose down
docker-compose up -d

# Проверить порты
sudo ss -tlnp | grep LISTEN
```

### Проблема: Нет места на диске

```bash
# Очистить Docker
docker system prune -af --volumes

# Очистить логи
sudo journalctl --vacuum-time=7d

# Найти большие файлы
find / -type f -size +100M 2>/dev/null

# Удалить старые образы
docker image prune -af
```

### Проблема: High Memory Usage

```bash
# Найти процессы
ps aux --sort=-%mem | head -10

# Перезапустить Docker
sudo systemctl restart docker

# Ограничить память контейнера
# В docker-compose.yml:
services:
  api:
    mem_limit: 512m
```

---

## 📊 Мониторинг

### Real-time мониторинг

```bash
# System resources
htop

# Docker stats
docker stats

# Network traffic
iftop

# Disk I/O
iotop
```

### Логи в реальном времени

```bash
# Все контейнеры
docker-compose logs -f

# Конкретный контейнер
docker-compose logs -f api

# System logs
sudo journalctl -f
```

---

## 🎯 Быстрые команды

```bash
# Алиасы для удобства (добавить в ~/.bashrc)
alias dps='docker ps'
alias dc='docker-compose'
alias dcl='docker-compose logs'
alias dcu='docker-compose up -d'
alias dcd='docker-compose down'
alias dcr='docker-compose restart'

# Перезагрузка после изменений
source ~/.bashrc
```

---

## 📞 Контакты и поддержка

**GitHub Repository:** https://github.com/[username]/email-service  
**DigitalOcean Console:** https://cloud.digitalocean.com/  
**Документация:** `/opt/email-service/docs/`  

---

## 📝 История изменений

| Дата | Событие | Статус |
|------|---------|--------|
| 15.12.2025 | Создана документация доступа | ✅ |
| -- | Первый деплой | Pending |
| -- | Production запуск | Pending |

---

**Last Updated:** 15 декабря 2025  
**Maintainer:** Email Intelligence Platform Team
