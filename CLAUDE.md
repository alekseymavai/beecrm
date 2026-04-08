# Claude Context — BEECRM

Общайся по-русски. Имя пользователя: Алексей.

---

## GitHub

- Всегда пушить от `alekseymavai`:
  ```
  gh auth switch -u alekseymavai && gh auth setup-git
  git push origin main
  ```
- После работы вернуть если нужно: `gh auth switch -u gaveron18`

---

## Работа командой AgentForge

Каждая задача проходит полный цикл — не пропускать шаги:

```
Scout → Architect → Security → ConsensusReport → код → тесты → push → деплой
```

---

## Деплой

После каждого push:

```bash
ssh ai-agent@178.253.39.215 "cd ~/BEECRM && git pull && sudo systemctl restart beecrm"
```
