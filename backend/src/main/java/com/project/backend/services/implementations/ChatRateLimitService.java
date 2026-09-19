package com.project.backend.services.implementations;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatRateLimitService {

    private final StringRedisTemplate redisTemplate;

    @Value("${app.rate-limit.chat-requests-per-minute:30}")
    private int requestsPerMinute;

    public void check(UUID userId) {
        long minute = Instant.now().getEpochSecond() / 60;
        String key = "rate-limit:lords-mobile-chat:" + userId + ":" + minute;
        try {
            Long count = redisTemplate.opsForValue().increment(key);
            if (count != null && count == 1) {
                redisTemplate.expire(key, Duration.ofMinutes(2));
            }
            if (count != null && count > requestsPerMinute) {
                throw new ResponseStatusException(
                        HttpStatus.TOO_MANY_REQUESTS,
                        "Chat rate limit exceeded; retry in the next minute");
            }
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (RuntimeException ex) {
            // Redis must not make authenticated chat unavailable.
            log.warn("Chat rate limit unavailable; allowing request: {}", ex.getMessage());
        }
    }
}
