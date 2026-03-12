"""Locust load test for Article Summarizer Agent API."""

from __future__ import annotations

import os

from locust import HttpUser, between, task


class SummarizerUser(HttpUser):
    wait_time = between(1, 3)
    token: str | None = None

    def on_start(self):
        username = os.getenv("LOCUST_ADMIN_USER", os.getenv("ADMIN_USER", "admin"))
        password = os.getenv("LOCUST_ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))
        if not password:
            return

        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            name="/api/auth/login",
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(2)
    def get_stats(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/api/estatisticas", headers=headers)

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
                self.client.get(f"/api/tarefa/{task_id}", name="/api/tarefa/[id]")
