# Как подключиться к серверу DigitalOcean

## 🚀 Быстрый старт

### 1. Получить credentials из GitHub

1. Зайдите в GitHub репозиторий
2. **Settings** → **Secrets and variables** → **Actions**
3. Найдите secrets:
   - `DO_SSH_HOST` - IP адрес сервера
   - `DO_SSH_USER` - Username (обычно `root`)
   - `DO_SSH_PRIVATE_KEY` - SSH ключ

### 2. Настроить SSH ключ

**На Windows (PowerShell):**
```powershell
# Создать директорию (если нет)
mkdir $HOME\.ssh -ErrorAction SilentlyContinue

# Сохранить ключ (скопировать из GitHub Secret DO_SSH_PRIVATE_KEY)
notepad $HOME\.ssh\digitalocean_key

# В блокноте вставить содержимое ключа и сохранить
```

**На Linux/Mac:**
```bash
# Сохранить ключ
cat > ~/.ssh/digitalocean_key << 'EOF'
[вставить содержимое DO_SSH_PRIVATE_KEY]
EOF

# Установить права
chmod 600 ~/.ssh/digitalocean_key
```

### 3. Подключиться

**Вариант A: Прямое подключение**
```bash
ssh -i ~/.ssh/digitalocean_key root@[IP_ИЗ_DO_SSH_HOST]
```

**Вариант B: Использовать helper скрипт**
```bash
# Установить переменные окружения
export DO_SSH_HOST="[IP из GitHub Secret]"
export DO_SSH_USER="root"

# Подключиться
chmod +x deploy/scripts/connect-to-server.sh
./deploy/scripts/connect-to-server.sh
```

**Вариант C: SSH config (удобнее)**
```bash
# Добавить в ~/.ssh/config
cat >> ~/.ssh/config << 'EOF'
Host do-email
    HostName [IP из DO_SSH_HOST]
    User root
    IdentityFile ~/.ssh/digitalocean_key
    StrictHostKeyChecking accept-new
EOF

# Теперь можно просто:
ssh do-email
```

---

## 🧪 Запуск анализа сервера

### На сервере (после подключения)

```bash
# 1. Перейти в проект
cd /opt/email-service

# 2. Быстрая проверка (30 сек)
./deploy/scripts/quick-check.sh

# 3. Полный анализ (2-3 мин)
./deploy/scripts/00-analyze-server.sh
```

### С локальной машины (remote execution)

```bash
# Установить переменные
export DO_SSH_HOST="[IP]"
export DO_SSH_USER="root"

# Запустить быстрый анализ
./deploy/scripts/run-remote-analysis.sh quick

# Запустить полный анализ
./deploy/scripts/run-remote-analysis.sh full
```

---

## 📋 Что проверяется

### Quick Check (30 секунд)
- ✅ System (OS, kernel, uptime)
- ✅ CPU & Memory
- ✅ Disk usage
- ✅ Docker status
- ✅ Running containers
- ✅ Listening ports
- ✅ Critical services
- ✅ Network connectivity
- ✅ Health status

### Full Analysis (2-3 минуты)
Всё из Quick Check плюс:
- ✅ Hardware details
- ✅ Docker storage analysis
- ✅ Database services
- ✅ Web servers
- ✅ Top processes
- ✅ Systemd services
- ✅ Security check
- ✅ Detailed recommendations
- 📄 **Сохраняет отчет в `/tmp/server-analysis-*.txt`**

---

## 🔑 Windows PowerShell версия

```powershell
# Установить переменные
$env:DO_SSH_HOST = "[IP из GitHub Secret]"
$env:DO_SSH_USER = "root"

# Подключиться
ssh -i $HOME\.ssh\digitalocean_key root@$env:DO_SSH_HOST

# После подключения
cd /opt/email-service
./deploy/scripts/quick-check.sh
```

---

## ⚠️ Troubleshooting

### Ошибка: Permission denied (publickey)

```bash
# Проверить права на ключ
ls -la ~/.ssh/digitalocean_key

# Должно быть: -rw------- (600)
chmod 600 ~/.ssh/digitalocean_key
```

### Ошибка: Connection refused

```bash
# Проверить доступность сервера
ping [DO_SSH_HOST]

# Проверить порт SSH
nmap -p 22 [DO_SSH_HOST]
```

### Ошибка: Host key verification failed

```bash
# Удалить старый ключ
ssh-keygen -R [DO_SSH_HOST]

# Подключиться снова
ssh -i ~/.ssh/digitalocean_key root@[DO_SSH_HOST]
```

---

## 📞 Поддержка

- GitHub Issues: https://github.com/[username]/email-service/issues
- Документация: [DIGITALOCEAN_SERVER.md](../docs/DIGITALOCEAN_SERVER.md)
- Server Analysis: [SERVER_ANALYSIS.md](../docs/SERVER_ANALYSIS.md)
