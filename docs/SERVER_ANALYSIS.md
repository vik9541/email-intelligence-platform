# Server Analysis & Diagnostics Guide

**Project:** 97v.ru Email Intelligence Platform  
**Date:** 15 декабря 2025  
**Purpose:** Безопасный анализ существующей инфраструктуры  

---

## ⚠️ SAFE MODE ANALYSIS

**Все команды в этом руководстве:**
- ✅ Только для чтения (READ-ONLY)
- ✅ НЕ изменяют систему
- ✅ НЕ требуют sudo (большинство)
- ✅ Безопасны для production сервера

---

## 📋 Quick Start

### Быстрая проверка (30 секунд)

```bash
cd /path/to/email-service
chmod +x deploy/scripts/quick-check.sh
./deploy/scripts/quick-check.sh
```

### Полный анализ (2-3 минуты)

```bash
chmod +x deploy/scripts/00-analyze-server.sh
./deploy/scripts/00-analyze-server.sh

# Сохранится в: /tmp/server-analysis-YYYYMMDD-HHMMSS.txt
```

---

## 📊 Секции Анализа

### 1. System Information

```bash
# OS информация
cat /etc/os-release

# Kernel
uname -a

# Uptime
uptime
```

**Ожидаемый вывод:**
```
PRETTY_NAME="Ubuntu 22.04.3 LTS"
Linux servername 5.15.0-99-generic #109-Ubuntu SMP x86_64 GNU/Linux
10:45:23 up 45 days, 3:21, 2 users, load average: 1.23, 0.98, 0.87
```

---

### 2. Hardware Resources

```bash
# CPU
lscpu | grep -E "Model|Architecture|CPU\(s\)|Cores|MHz"

# Быстрый вывод CPU
echo "Cores: $(grep -c '^processor' /proc/cpuinfo)"
grep "^model name" /proc/cpuinfo | head -1

# Memory
free -h

# Disk
df -h / /home /var
```

**Интерпретация:**
- **Load average:** должен быть < количества CPU ядер
- **Memory:** Available > 20% от Total
- **Disk:** Usage < 80%

---

### 3. Docker Environment

```bash
# Установлен ли Docker
docker --version

# Docker info
docker info | head -20

# Активные контейнеры
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Все контейнеры (включая остановленные)
docker ps -a

# Образы
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Использование диска Docker
docker system df
```

**Критические проверки:**
- ✅ Docker version >= 24.0
- ✅ Docker Compose version >= 2.20
- ✅ Storage Driver: overlay2
- ✅ Cgroup Driver: systemd

---

### 4. Network & Ports

```bash
# Открытые порты
sudo ss -tlnp | grep LISTEN

# Более читаемый формат
sudo ss -tlnp | grep LISTEN | awk '{print $4, $7}' | column -t

# Проверить конкретные порты
for port in 22 80 443 5432 6379 8000; do
  if ss -tln | grep -q ":$port "; then
    echo "✅ Port $port: OPEN"
  else
    echo "❌ Port $port: CLOSED"
  fi
done
```

**Критические порты для платформы:**
- `22` - SSH (обязательно)
- `80/443` - HTTP/HTTPS (если Nginx на хосте)
- `5432` - PostgreSQL (если на хосте)
- `6379` - Redis (если на хосте)
- `8000` - FastAPI application
- `9090` - Metrics/monitoring

---

### 5. Database Services

```bash
# PostgreSQL - Docker
docker ps | grep postgres

# PostgreSQL - System
systemctl status postgresql
psql --version

# MySQL - Docker
docker ps | grep mysql

# Redis - Docker
docker ps | grep redis

# Подключения к PostgreSQL (если есть доступ)
sudo -u postgres psql -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Размер БД
sudo -u postgres psql -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database ORDER BY pg_database_size DESC;"
```

---

### 6. Web Servers

```bash
# Nginx
systemctl status nginx
nginx -v
docker ps | grep nginx

# Apache
systemctl status apache2
docker ps | grep apache

# Конфигурация Nginx
sudo nginx -t
sudo cat /etc/nginx/sites-enabled/default
```

---

### 7. Security

```bash
# SSH конфигурация
sudo grep -E "^Port|^PermitRootLogin" /etc/ssh/sshd_config

# Firewall (UFW)
sudo ufw status verbose

# Активные пользователи
who
last | head -10

# SSL сертификаты
sudo find /etc -name "*.crt" 2>/dev/null | head -10

# Проверка сертификата
openssl x509 -in /path/to/cert.crt -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After:"
```

---

### 8. Running Services

```bash
# Активные systemd сервисы
systemctl list-units --type=service --state=running --no-pager

# Failed сервисы
systemctl list-units --type=service --state=failed

# Top процессы по памяти
ps aux --sort=-%mem | head -10

# Top процессы по CPU
ps aux --sort=-%cpu | head -10
```

---

### 9. Directory Structure

```bash
# Что в /opt
ls -lah /opt/

# Docker volumes
docker volume ls

# Найти docker-compose файлы
find /opt /home /srv -name "docker-compose.yml" 2>/dev/null

# Git репозитории
find /opt /home /srv -name ".git" -type d 2>/dev/null

# Использование диска (top 10)
du -sh /* 2>/dev/null | sort -rh | head -10
```

---

### 10. Resource Usage

```bash
# Load average
uptime

# Детальный мониторинг
top -bn1 | head -30

# Memory детально
cat /proc/meminfo | head -20

# Какой процесс занимает больше всего памяти
ps aux --sort=-%mem | head -5

# Swap
free -h | grep Swap

# Disk I/O (если доступен iostat)
iostat -x 2 2
```

---

### 11. Connectivity Tests

```bash
# Internet
ping -c 3 google.com

# DNS
nslookup google.com
nslookup api.97v.ru

# Локальные порты
nc -zv localhost 22
nc -zv localhost 80
nc -zv localhost 5432

# Проверка HTTP
curl -I http://localhost:80
curl -I https://api.97v.ru
```

---

## 🎯 Comprehensive Analysis Script

Скрипт `deploy/scripts/00-analyze-server.sh` собирает всю информацию:

```bash
# Запуск
chmod +x deploy/scripts/00-analyze-server.sh
./deploy/scripts/00-analyze-server.sh

# Результат сохраняется в:
# /tmp/server-analysis-YYYYMMDD-HHMMSS.txt

# Просмотр
cat /tmp/server-analysis-*.txt | less
```

**Что собирается:**
1. ✅ System Information (OS, kernel, uptime)
2. ✅ Hardware (CPU, memory, disk)
3. ✅ Docker status (version, containers, images)
4. ✅ Listening ports
5. ✅ Database services (PostgreSQL, MySQL, Redis)
6. ✅ Web servers (Nginx, Apache)
7. ✅ Disk usage (top 10 directories)
8. ✅ Network (hostname, IP, connectivity)
9. ✅ Security (SSH, firewall)
10. ✅ Top processes (CPU, memory)
11. ✅ Systemd services (running, failed)
12. ✅ Health check & recommendations

---

## ⚡ Quick Check Script

Для быстрой диагностики используйте `deploy/scripts/quick-check.sh`:

```bash
./deploy/scripts/quick-check.sh
```

**Вывод (~10 секунд):**
- System info
- CPU & Memory
- Disk usage
- Docker status
- Listening ports
- Critical services
- Network connectivity
- Health status

---

## 📈 Интерпретация Результатов

### ✅ Здоровая Система

```
Disk usage: 45% (OK)
Memory usage: 62% (OK)
Load: 0.87 avg (OK for 4 cores)
✅ Internet connectivity: OK
✅ DNS resolution: OK
✅ All services running normally
```

### ⚠️ Warning Signs

```
⚠️  WARNING: Disk usage is high (85%)
⚠️  WARNING: Memory usage is high (88%)
⚠️  WARNING: System load is high (6.5 avg, 4 cores)
```

**Действия:**
- Disk > 80%: Очистить логи, Docker images
- Memory > 80%: Проверить утечки памяти
- Load > CPU count: Оптимизировать процессы

### 🔴 Critical Issues

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

## 🔒 Security Checklist

```bash
# 1. SSH Security
sudo grep "^PermitRootLogin" /etc/ssh/sshd_config
# Должно быть: PermitRootLogin no

# 2. Firewall
sudo ufw status
# Должно быть: Status: active

# 3. SSL Certificates
sudo find /etc/letsencrypt -name "cert.pem" -exec openssl x509 -in {} -noout -dates \;
# Проверить Not After date

# 4. Open Ports
sudo ss -tlnp | grep LISTEN
# Убедиться, что открыты только нужные порты

# 5. Failed Login Attempts
sudo journalctl -u ssh | grep "Failed password" | tail -20
```

---

## 📊 Common Issues & Solutions

### Issue: Docker Not Installed

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Issue: High Disk Usage

```bash
# Очистить Docker
docker system prune -af --volumes

# Очистить логи
sudo journalctl --vacuum-time=7d

# Найти большие файлы
find / -type f -size +100M 2>/dev/null | head -20
```

### Issue: High Memory Usage

```bash
# Проверить топ процессы
ps aux --sort=-%mem | head -10

# Перезапустить сервис
sudo systemctl restart service-name

# Очистить кэш
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches
```

---

## 🎓 Best Practices

1. **Регулярный анализ:**
   - Запускать `quick-check.sh` ежедневно
   - Полный анализ еженедельно
   - Сохранять отчеты для истории

2. **Мониторинг:**
   - Настроить алерты для disk > 80%
   - Настроить алерты для memory > 80%
   - Мониторить failed systemd services

3. **Безопасность:**
   - Проверять открытые порты
   - Обновлять SSL сертификаты
   - Аудит SSH логов

4. **Производительность:**
   - Оптимизировать Docker images
   - Очищать старые логи
   - Мониторить load average

---

## 📝 Report Template

После анализа создайте отчет:

```markdown
## Server Analysis Report - [DATE]

### System
- OS: Ubuntu 22.04 LTS
- Kernel: 5.15.0-99-generic
- Uptime: 45 days

### Resources
- CPU: 4 cores, Load: 0.87
- Memory: 16GB total, 62% used
- Disk: 500GB total, 45% used

### Docker
- Version: 24.0.6
- Running containers: 5
- Total images: 12

### Services
- ✅ PostgreSQL: running (Docker)
- ✅ Redis: running (Docker)
- ✅ Nginx: running (system)

### Health
- ✅ Disk: OK (45%)
- ✅ Memory: OK (62%)
- ✅ Load: OK (0.87 avg)
- ✅ Internet: OK
- ✅ DNS: OK

### Recommendations
- None at this time

### Next Check
- Quick check: Daily
- Full analysis: Weekly (every Monday)
```

---

## 🔗 Related Documentation

- [Deployment Guide](DEPLOYMENT.md)
- [Docker Setup](DOCKER_SETUP.md)
- [Monitoring Guide](MONITORING.md)
- [Security Checklist](SECURITY.md)

---

## 🆘 Support

Если обнаружены критические проблемы:

1. Сохранить полный отчет анализа
2. Собрать логи: `sudo journalctl -xe > /tmp/system-logs.txt`
3. Собрать Docker логи: `docker logs [container_name]`
4. Связаться с DevOps командой

---

**Last Updated:** 15 декабря 2025  
**Maintainer:** Email Intelligence Platform Team
