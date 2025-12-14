# ТЗ-001: DNS + MX Records Setup Guide

**Цель:** Настроить почтовый сервер для приема писем на info@97v.ru

**Сервер:** 45.129.141.198 (VPS)  
**Домен:** 97v.ru  
**Email:** info@97v.ru  
**Status:** 🔴 Not Started

---

## Шаг 1: Установка Postfix на VPS

```bash
# SSH в VPS
ssh root@45.129.141.198

# Обновить систему
apt update && apt upgrade -y

# Установить Postfix
apt install -y postfix postfix-pcre

# Выбрать "Internet Site" при установке
# Указать mail name: mail.97v.ru
```

---

## Шаг 2: Конфигурация Postfix

Редактировать `/etc/postfix/main.cf`:

```bash
# Main config
myhostname = mail.97v.ru
mydomain = 97v.ru
myorigin = $mydomain

# Network settings
inet_interfaces = all
inet_protocols = ipv4

# Mail delivery
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain
home_mailbox = Maildir/

# Virtual domains (if needed)
virtual_alias_domains = 97v.ru
virtual_alias_maps = hash:/etc/postfix/virtual

# TLS settings (будут настроены в Шаге 4)
smtpd_tls_cert_file = /etc/letsencrypt/live/mail.97v.ru/fullchain.pem
smtpd_tls_key_file = /etc/letsencrypt/live/mail.97v.ru/privkey.pem
smtpd_use_tls = yes
smtpd_tls_session_cache_database = btree:${data_directory}/smtpd_scache
smtp_tls_session_cache_database = btree:${data_directory}/smtp_scache

# SMTP Auth
smtpd_sasl_auth_enable = yes
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth

# Restrictions
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    reject_unauth_destination
```

Создать virtual aliases:

```bash
# /etc/postfix/virtual
info@97v.ru    info
support@97v.ru support
sales@97v.ru   sales

# Apply changes
postmap /etc/postfix/virtual
systemctl restart postfix
```

---

## Шаг 3: Установка Dovecot (IMAP)

```bash
# Установить Dovecot
apt install -y dovecot-core dovecot-imapd

# Конфигурация /etc/dovecot/dovecot.conf
protocols = imap

# /etc/dovecot/conf.d/10-mail.conf
mail_location = maildir:~/Maildir

# /etc/dovecot/conf.d/10-auth.conf
disable_plaintext_auth = no  # Только для тестирования!
auth_mechanisms = plain login

# /etc/dovecot/conf.d/10-master.conf
service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0666
    user = postfix
    group = postfix
  }
}

# Перезапуск
systemctl restart dovecot
```

---

## Шаг 4: Let's Encrypt SSL Certificate

```bash
# Установить certbot
apt install -y certbot

# Получить сертификат
certbot certonly --standalone -d mail.97v.ru

# Сертификаты будут в:
# /etc/letsencrypt/live/mail.97v.ru/fullchain.pem
# /etc/letsencrypt/live/mail.97v.ru/privkey.pem

# Auto-renewal (cron)
certbot renew --dry-run

# Добавить в crontab для auto-renewal:
# 0 3 * * * certbot renew --quiet && systemctl reload postfix dovecot
```

---

## Шаг 5: Настройка DNS Records (DigitalOcean)

Зайти в DigitalOcean DNS console для домена `97v.ru`:

### MX Record
```
Type: MX
Name: @
Priority: 10
Value: mail.97v.ru
TTL: 3600
```

### A Record для mail subdomain
```
Type: A
Name: mail
Value: 45.129.141.198
TTL: 3600
```

### SPF Record
```
Type: TXT
Name: @
Value: v=spf1 ip4:45.129.141.198 include:mail.97v.ru ~all
TTL: 3600
```

### DMARC Record
```
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@97v.ru; pct=100
TTL: 3600
```

---

## Шаг 6: DKIM Setup

```bash
# Установить OpenDKIM
apt install -y opendkim opendkim-tools

# Генерировать DKIM ключи
mkdir -p /etc/opendkim/keys/97v.ru
cd /etc/opendkim/keys/97v.ru
opendkim-genkey -s mail -d 97v.ru

# Это создаст:
# - mail.private (приватный ключ)
# - mail.txt (публичный ключ для DNS)

# Посмотреть публичный ключ
cat mail.txt

# Пример вывода:
# mail._domainkey  IN  TXT  ( "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNA..." )

# Конфигурация OpenDKIM
# /etc/opendkim.conf
Domain                  97v.ru
KeyFile                 /etc/opendkim/keys/97v.ru/mail.private
Selector                mail
Socket                  inet:8891@localhost

# Интеграция с Postfix
# Добавить в /etc/postfix/main.cf:
milter_default_action = accept
milter_protocol = 6
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891

# Перезапуск
systemctl restart opendkim postfix
```

### DKIM DNS Record (DigitalOcean)
```
Type: TXT
Name: mail._domainkey
Value: v=DKIM1; k=rsa; p=<публичный_ключ_из_mail.txt>
TTL: 3600
```

---

## Шаг 7: Проверка и Тестирование

### Проверить DNS propagation
```bash
# MX Record
dig MX 97v.ru

# Ожидаемый вывод:
# 97v.ru.  3600  IN  MX  10 mail.97v.ru.

# A Record
dig A mail.97v.ru

# SPF
dig TXT 97v.ru | grep spf

# DKIM
dig TXT mail._domainkey.97v.ru

# DMARC
dig TXT _dmarc.97v.ru
```

### Проверить Postfix
```bash
systemctl status postfix
postfix status

# Проверить порты
netstat -tlnp | grep :25    # SMTP
netstat -tlnp | grep :587   # Submission
netstat -tlnp | grep :993   # IMAPS
```

### Проверить Dovecot
```bash
systemctl status dovecot

# Тест IMAP login
telnet localhost 993
# или
openssl s_client -connect mail.97v.ru:993
```

### Отправить тестовое письмо
```bash
# Локально на сервере
echo "Test email body" | mail -s "Test Email" info@97v.ru

# Проверить логи
tail -f /var/log/mail.log

# Проверить mailbox
ls -la /home/info/Maildir/new/
```

---

## Шаг 8: Firewall Rules

```bash
# Открыть порты
ufw allow 25/tcp    # SMTP
ufw allow 587/tcp   # Submission
ufw allow 993/tcp   # IMAPS
ufw allow 80/tcp    # HTTP (для Let's Encrypt)
ufw allow 443/tcp   # HTTPS

ufw enable
ufw status
```

---

## Acceptance Criteria Checklist

- [ ] DNS MX record propagated (`dig MX 97v.ru`)
- [ ] SPF record published (`dig TXT 97v.ru`)
- [ ] DKIM key generated and DNS published
- [ ] DMARC policy configured
- [ ] Postfix running (`systemctl status postfix`)
- [ ] Dovecot running (`systemctl status dovecot`)
- [ ] SSL certificate valid (`openssl s_client -connect mail.97v.ru:993`)
- [ ] Test email received successfully
- [ ] Ports 25, 587, 993 open

---

## Troubleshooting

### Postfix не стартует
```bash
# Проверить конфигурацию
postfix check

# Посмотреть логи
tail -f /var/log/mail.log
journalctl -u postfix -f
```

### DNS не propagated
```bash
# Проверить TTL и подождать
# Использовать публичные DNS для проверки
nslookup -type=MX 97v.ru 8.8.8.8
```

### SSL certificate ошибки
```bash
# Проверить сертификат
openssl x509 -in /etc/letsencrypt/live/mail.97v.ru/fullchain.pem -text -noout

# Проверить права доступа
ls -la /etc/letsencrypt/live/mail.97v.ru/
```

---

## Полезные команды

```bash
# Перезапустить все сервисы
systemctl restart postfix dovecot opendkim

# Проверить логи в реальном времени
tail -f /var/log/mail.log

# Проверить очередь писем
mailq

# Очистить очередь
postsuper -d ALL

# Тест отправки
telnet localhost 25
HELO mail.97v.ru
MAIL FROM: test@97v.ru
RCPT TO: info@97v.ru
DATA
Subject: Test
Test body
.
QUIT
```

---

**Estimated Time:** 1.5 hours  
**Complexity:** MEDIUM  
**Dependencies:** DigitalOcean DNS access, VPS SSH access

**Next Steps:** After completion → ТЗ-002 (IMAP Listener)
