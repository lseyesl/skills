---
title: Retry Client Spec
source_type: internal-spec
---

# Retry Client Spec

当响应包含合法的 `Retry-After` 时，客户端使用 `max(jittered_backoff, Retry-After)` 作为候选等待时间，然后用全局 `max_delay` 截断。无法解析或为负数的 `Retry-After` 被忽略。所有重试仍受总时间预算限制。
