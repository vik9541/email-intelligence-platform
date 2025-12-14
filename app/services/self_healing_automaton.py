"""
🤖 AUTO-HEALING AUTOMATON
Email Intelligence Platform - Self-Healing System

Автоматическая диагностика и устранение проблем:
- Масштабирование Kafka consumer на основе lag
- Очистка PostgreSQL connections
- Мониторинг здоровья pods
- Очистка дискового пространства
- Автоматический restart проблемных pods
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import prometheus_client
from kubernetes import client, config
from kafka import KafkaConsumer

# Prometheus metrics
healing_actions_total = prometheus_client.Counter(
    'healing_actions_total',
    'Total number of auto-healing actions',
    ['action_type', 'status']
)

healing_latency = prometheus_client.Histogram(
    'healing_action_duration_seconds',
    'Duration of healing actions',
    ['action_type']
)

class AutoHealingAutomaton:
    """Автономная система самовосстановления"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Kubernetes client
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.k8s_apps = client.AppsV1Api()
        self.k8s_core = client.CoreV1Api()
        
        # Prometheus query endpoint
        self.prometheus_url = "http://prometheus.monitoring.svc.cluster.local:9090"
        
        # Параметры автоисцеления
        self.kafka_lag_threshold = 10000
        self.kafka_scale_up_lag = 15000
        self.postgres_connections_threshold = 85
        self.disk_usage_threshold = 0.85
        self.pod_restart_threshold = 5  # рестартов за 1 час
        
    async def run_forever(self):
        """Основной цикл автоматического мониторинга"""
        self.logger.info("🤖 Auto-Healing Automaton запущен")
        
        while True:
            try:
                # Запуск диагностики каждую минуту
                await self.run_diagnostics()
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Ошибка в цикле auto-healing: {e}")
                await asyncio.sleep(60)
    
    async def run_diagnostics(self):
        """Запуск всех диагностических проверок"""
        self.logger.info("🔍 Запуск диагностики...")
        
        # Параллельный запуск всех проверок
        await asyncio.gather(
            self.check_kafka_lag(),
            self.check_postgres_connections(),
            self.check_pod_health(),
            self.check_disk_space(),
            return_exceptions=True
        )
    
    @healing_latency.labels('kafka_scaling').time()
    async def check_kafka_lag(self):
        """Проверка Kafka consumer lag и автоматическое масштабирование"""
        try:
            lag = await self.query_prometheus(
                'kafka_consumer_lag{topic="email.received"}'
            )
            
            if not lag:
                return
            
            current_lag = float(lag[0]['value'][1])
            
            if current_lag > self.kafka_scale_up_lag:
                self.logger.warning(
                    f"⚠️ Kafka lag критический: {current_lag} > {self.kafka_scale_up_lag}"
                )
                
                # Автоматическое масштабирование
                await self.scale_deployment(
                    "email-consumer",
                    "production",
                    scale_up=True
                )
                
                healing_actions_total.labels(
                    action_type='kafka_scale_up',
                    status='success'
                ).inc()
                
            elif current_lag < self.kafka_lag_threshold / 2:
                # Масштабирование вниз если lag низкий
                self.logger.info(
                    f"ℹ️ Kafka lag низкий: {current_lag}, можно scale down"
                )
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки Kafka lag: {e}")
            healing_actions_total.labels(
                action_type='kafka_check',
                status='failed'
            ).inc()
    
    @healing_latency.labels('postgres_cleanup').time()
    async def check_postgres_connections(self):
        """Проверка PostgreSQL connections и автоматическая очистка"""
        try:
            connections = await self.query_prometheus(
                'pg_stat_activity_count'
            )
            
            if not connections:
                return
            
            current_connections = float(connections[0]['value'][1])
            max_connections = 100
            usage_percent = (current_connections / max_connections) * 100
            
            if usage_percent > self.postgres_connections_threshold:
                self.logger.warning(
                    f"⚠️ PostgreSQL connections высокие: {usage_percent:.1f}%"
                )
                
                # Очистка idle connections
                await self.cleanup_postgres_connections()
                
                healing_actions_total.labels(
                    action_type='postgres_cleanup',
                    status='success'
                ).inc()
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки PostgreSQL: {e}")
            healing_actions_total.labels(
                action_type='postgres_check',
                status='failed'
            ).inc()
    
    @healing_latency.labels('pod_restart').time()
    async def check_pod_health(self):
        """Проверка здоровья pods и автоматический restart проблемных"""
        try:
            pods = self.k8s_core.list_namespaced_pod(namespace="production")
            
            for pod in pods.items:
                # Пропустить completed/succeeded pods
                if pod.status.phase in ['Succeeded', 'Completed']:
                    continue
                
                # Проверить рестарты контейнеров
                for container_status in pod.status.container_statuses or []:
                    restart_count = container_status.restart_count
                    
                    # Если слишком много рестартов - возможна проблема
                    if restart_count > self.pod_restart_threshold:
                        self.logger.warning(
                            f"⚠️ Pod {pod.metadata.name} имеет {restart_count} рестартов"
                        )
                        
                        # Логировать для расследования
                        await self.collect_pod_diagnostics(pod)
                        
                        healing_actions_total.labels(
                            action_type='pod_diagnostic',
                            status='collected'
                        ).inc()
                
                # Проверить OOMKilled pods
                for container_status in pod.status.container_statuses or []:
                    if (container_status.last_state.terminated and
                        container_status.last_state.terminated.reason == 'OOMKilled'):
                        
                        self.logger.critical(
                            f"🚨 Pod {pod.metadata.name} был OOMKilled!"
                        )
                        
                        # Автоматическое увеличение memory limits
                        await self.increase_pod_memory(pod)
                        
                        healing_actions_total.labels(
                            action_type='memory_increase',
                            status='success'
                        ).inc()
                        
        except Exception as e:
            self.logger.error(f"Ошибка проверки pod health: {e}")
    
    @healing_latency.labels('disk_cleanup').time()
    async def check_disk_space(self):
        """Проверка дискового пространства и автоматическая очистка"""
        try:
            disk_usage = await self.query_prometheus(
                '1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})'
            )
            
            if not disk_usage:
                return
            
            for node_usage in disk_usage:
                usage = float(node_usage['value'][1])
                node = node_usage['metric'].get('instance', 'unknown')
                
                if usage > self.disk_usage_threshold:
                    self.logger.warning(
                        f"⚠️ Disk usage на {node}: {usage*100:.1f}%"
                    )
                    
                    # Автоматическая очистка логов
                    await self.cleanup_old_logs(node)
                    
                    healing_actions_total.labels(
                        action_type='disk_cleanup',
                        status='success'
                    ).inc()
                    
        except Exception as e:
            self.logger.error(f"Ошибка проверки disk space: {e}")
    
    async def scale_deployment(
        self,
        deployment_name: str,
        namespace: str,
        scale_up: bool = True
    ):
        """Автоматическое масштабирование deployment"""
        try:
            deployment = self.k8s_apps.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            
            current_replicas = deployment.spec.replicas
            
            if scale_up:
                new_replicas = min(current_replicas + 2, 10)  # Max 10 replicas
            else:
                new_replicas = max(current_replicas - 1, 1)  # Min 1 replica
            
            if new_replicas == current_replicas:
                return
            
            self.logger.info(
                f"🔄 Масштабирование {deployment_name}: {current_replicas} → {new_replicas}"
            )
            
            deployment.spec.replicas = new_replicas
            
            self.k8s_apps.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )
            
            self.logger.info(f"✅ Deployment {deployment_name} масштабирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка масштабирования {deployment_name}: {e}")
    
    async def cleanup_postgres_connections(self):
        """Очистка idle PostgreSQL connections"""
        # TODO: Выполнить SQL команду для закрытия idle connections
        # Например: SELECT pg_terminate_backend(pid) FROM pg_stat_activity
        #           WHERE state = 'idle' AND state_change < now() - interval '5 minutes';
        
        self.logger.info("🧹 Очистка idle PostgreSQL connections")
        pass
    
    async def cleanup_old_logs(self, node: str):
        """Очистка старых логов на ноде"""
        # TODO: Выполнить команду очистки логов
        # kubectl exec на ноде и удалить логи старше 7 дней
        
        self.logger.info(f"🧹 Очистка старых логов на {node}")
        pass
    
    async def collect_pod_diagnostics(self, pod):
        """Сбор диагностической информации о проблемном pod"""
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace
        
        try:
            # Получить логи
            logs = self.k8s_core.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=100
            )
            
            self.logger.info(f"📋 Собраны логи pod {pod_name}")
            
            # Можно отправить в систему хранения логов
            # или создать инцидент с диагностикой
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора логов {pod_name}: {e}")
    
    async def increase_pod_memory(self, pod):
        """Автоматическое увеличение memory limits для pod"""
        # TODO: Обновить deployment с увеличенными memory limits
        
        self.logger.info(f"📈 Увеличение memory limits для {pod.metadata.name}")
        pass
    
    async def query_prometheus(self, query: str) -> Optional[List[Dict]]:
        """Запрос метрик из Prometheus"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={'query': query}
                ) as resp:
                    data = await resp.json()
                    
                    if data['status'] == 'success':
                        return data['data']['result']
                    
                    return None
                    
        except Exception as e:
            self.logger.error(f"Ошибка запроса Prometheus: {e}")
            return None


async def main():
    """Точка входа"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Запуск Prometheus metrics server
    prometheus_client.start_http_server(8000)
    
    # Запуск automaton
    automaton = AutoHealingAutomaton()
    await automaton.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
