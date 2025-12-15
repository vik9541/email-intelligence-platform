# 🧪 Инструкция: Подключиться, Протестировать и Получить Отчет

## 🚀 Быстрый старт (3 шага)

### Шаг 1: Получить credentials из GitHub Secrets

1. Откройте ваш GitHub репозиторий
2. **Settings** → **Secrets and variables** → **Actions**
3. Скопируйте значения:
   - `DO_SSH_HOST` - IP адрес сервера
   - `DO_SSH_USER` - Username (обычно `root`)
   - `DO_SSH_PRIVATE_KEY` - Приватный SSH ключ

### Шаг 2: Настроить локально

**Windows PowerShell:**
```powershell
# Установить переменные окружения
$env:DO_SSH_HOST = "123.45.67.89"  # Ваш IP из GitHub Secret
$env:DO_SSH_USER = "root"          # Из GitHub Secret

# Создать SSH ключ
mkdir $HOME\.ssh -ErrorAction SilentlyContinue
notepad $HOME\.ssh\digitalocean_key
# Вставить содержимое DO_SSH_PRIVATE_KEY и сохранить
```

**Linux/Mac:**
```bash
# Установить переменные окружения
export DO_SSH_HOST="123.45.67.89"  # Ваш IP
export DO_SSH_USER="root"

# Создать SSH ключ
cat > ~/.ssh/digitalocean_key << 'EOF'
[вставить DO_SSH_PRIVATE_KEY из GitHub]
EOF

chmod 600 ~/.ssh/digitalocean_key
```

### Шаг 3: Запустить тестирование

**Windows PowerShell:**
```powershell
cd C:\Projects\email-service

# Запустить автоматическое тестирование
.\deploy\scripts\test-and-report.ps1
```

**Linux/Mac:**
```bash
cd /path/to/email-service

# Дать права
chmod +x deploy/scripts/test-and-report.sh

# Запустить
./deploy/scripts/test-and-report.sh
```

---

## 📊 Что произойдет

Скрипт автоматически выполнит:

1. ✅ **Проверит credentials** (DO_SSH_HOST, DO_SSH_USER, SSH ключ)
2. ✅ **Протестирует подключение** к серверу
3. ✅ **Запустит Quick Check** (~30 секунд):
   - System info (OS, kernel, uptime)
   - CPU & Memory usage
   - Disk usage
   - Docker status
   - Running containers
   - Network connectivity
4. ✅ **Соберет информацию Docker**:
   - Версия Docker
   - Запущенные контейнеры
   - Docker images
   - Disk usage
5. ✅ **Соберет системную информацию**:
   - Детали ОС
   - CPU cores & load
   - Memory usage
   - Disk partitions
6. ✅ **Сгенерирует детальный отчет** в Markdown формате
7. ✅ **Сохранит отчет локально**: `server-test-report-YYYYMMDD-HHMMSS.md`

---

## 📄 Пример отчета

После выполнения вы получите файл типа `server-test-report-20251215-143022.md`:

```markdown
# Server Test Report

**Date:** 2025-12-15 14:30:22
**Server:** 123.45.67.89
**User:** root

## 📋 Executive Summary

- **OS:** Ubuntu 22.04 LTS
- **Kernel:** 5.15.0-99-generic
- **Uptime:** up 45 days
- **CPU:** 4 cores, Load: 0.87
- **Memory:** 3.2Gi / 8Gi (40%)
- **Disk:** 45G / 160G (29%)
- **Docker:** 5 running containers
- **Health:** ✅ All systems operational

## 🖥️ Quick Check Results

[Детальный вывод quick-check.sh]

## 🐳 Docker Environment

Docker version 24.0.6
5 running containers:
- postgres: postgres:16.1
- redis: redis:7.2
- nginx: nginx:1.25
...

## ✅ Recommendations

- ✅ All systems operating within normal parameters
- ✅ Continue regular monitoring
```

---

## 🎯 Просмотр отчета

### Вариант 1: В терминале
```bash
cat server-test-report-*.md
# или
less server-test-report-*.md
```

### Вариант 2: В редакторе
```bash
# Linux
gedit server-test-report-*.md

# Mac
open -a TextEdit server-test-report-*.md

# Windows
notepad server-test-report-*.md
```

### Вариант 3: В браузере (красиво)
```bash
# Если установлен pandoc
pandoc server-test-report-*.md -o report.html
xdg-open report.html  # Linux
open report.html      # Mac
start report.html     # Windows
```

---

## 🔧 Ручное выполнение команд

Если нужно выполнить команды вручную:

### 1. Подключиться к серверу

```bash
# Через SSH ключ
ssh -i ~/.ssh/digitalocean_key root@$DO_SSH_HOST

# Или через SSH config
ssh do-email
```

### 2. На сервере выполнить

```bash
# Перейти в проект
cd /opt/email-service

# Быстрый тест
./deploy/scripts/quick-check.sh

# Полный анализ
./deploy/scripts/00-analyze-server.sh

# Проверить Docker
docker ps
docker stats --no-stream

# Проверить ресурсы
free -h
df -h
uptime
```

### 3. Скачать результаты

```bash
# С сервера на локальную машину
scp -i ~/.ssh/digitalocean_key root@$DO_SSH_HOST:/tmp/server-analysis-*.txt ./
```

---

## 📋 Checklist полного тестирования

- [ ] **Получить credentials** из GitHub Secrets
- [ ] **Создать SSH ключ** локально
- [ ] **Установить переменные** окружения (DO_SSH_HOST, DO_SSH_USER)
- [ ] **Запустить test-and-report** скрипт
- [ ] **Дождаться завершения** (~2-3 минуты)
- [ ] **Открыть отчет** (server-test-report-*.md)
- [ ] **Проверить Health Status** (✅ ⚠️ 🔴)
- [ ] **Прочитать Recommendations**
- [ ] **Выполнить необходимые действия**
- [ ] **Сохранить отчет** для истории

---

## ⚠️ Troubleshooting

### Ошибка: "Environment variables not set"

```bash
# Убедитесь что установлены
echo $DO_SSH_HOST
echo $DO_SSH_USER

# Установите снова
export DO_SSH_HOST="123.45.67.89"
export DO_SSH_USER="root"
```

### Ошибка: "SSH key not found"

```bash
# Проверьте наличие
ls -la ~/.ssh/digitalocean_key

# Создайте если нет
cat > ~/.ssh/digitalocean_key << 'EOF'
[вставить ключ]
EOF

chmod 600 ~/.ssh/digitalocean_key
```

### Ошибка: "Cannot connect to server"

```bash
# Проверьте доступность
ping $DO_SSH_HOST

# Проверьте порт SSH
nmap -p 22 $DO_SSH_HOST

# Попробуйте verbose режим
ssh -v -i ~/.ssh/digitalocean_key root@$DO_SSH_HOST
```

### Ошибка: "Project not found"

```bash
# Подключитесь к серверу
ssh -i ~/.ssh/digitalocean_key root@$DO_SSH_HOST

# Клонируйте проект
cd /opt
git clone https://github.com/[username]/email-service.git

# Выдайте права
chmod +x email-service/deploy/scripts/*.sh
```

---

## 📞 Дополнительная информация

- **Документация сервера:** [docs/DIGITALOCEAN_SERVER.md](../docs/DIGITALOCEAN_SERVER.md)
- **Анализ сервера:** [docs/SERVER_ANALYSIS.md](../docs/SERVER_ANALYSIS.md)
- **Как подключиться:** [deploy/HOW_TO_CONNECT.md](HOW_TO_CONNECT.md)

---

## 🎓 FAQ

**Q: Как часто запускать тестирование?**  
A: Рекомендуется раз в неделю или после деплоя.

**Q: Что делать с отчетом?**  
A: Сохранить в Git, проверить рекомендации, выполнить необходимые действия.

**Q: Безопасно ли запускать скрипт?**  
A: Да, все команды READ-ONLY, ничего не изменяют на сервере.

**Q: Нужен ли sudo?**  
A: Нет, если подключаетесь как root. Если как обычный пользователь - некоторые команды могут требовать sudo.

**Q: Где хранить SSH ключи?**  
A: В `~/.ssh/` с правами 600. Никогда не коммитить в Git!

---

**Last Updated:** 15 декабря 2025  
**Version:** 1.0
