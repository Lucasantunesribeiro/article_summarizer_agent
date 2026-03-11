"""Locust load test for Article Summarizer Agent API."""
from __future__ import annotations

from locust import HttpUser, between, task


class SummarizerUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(2)
    def get_stats(self):
        self.client.get("/api/estatisticas")

    @task(1)
    def submit_summarize(self):
        response = self.client.post(
            "/api/sumarizar",
            json={
                "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
                "method": "extractive",
                "length": "short",
            },
        )
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            if task_id:
                # Poll once for status
                self.client.get(f"/api/tarefa/{task_id}", name="/api/tarefa/[id]")
