package com.project.backend.services;

import com.project.backend.services.implementations.ChatRateLimitService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ChatRateLimitServiceTest {

    @Mock private StringRedisTemplate redisTemplate;
    @Mock private ValueOperations<String, String> valueOperations;

    @Test
    void rejectsRequestsAboveConfiguredLimit() {
        ChatRateLimitService service = serviceWithLimit(30);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.increment(anyString())).thenReturn(31L);

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.check(UUID.randomUUID()));
        assertEquals(429, error.getStatusCode().value());
    }

    @Test
    void failsOpenWhenRedisIsUnavailable() {
        ChatRateLimitService service = serviceWithLimit(30);
        when(redisTemplate.opsForValue()).thenThrow(new IllegalStateException("redis offline"));

        assertDoesNotThrow(() -> service.check(UUID.randomUUID()));
    }

    private ChatRateLimitService serviceWithLimit(int limit) {
        ChatRateLimitService service = new ChatRateLimitService(redisTemplate);
        ReflectionTestUtils.setField(service, "requestsPerMinute", limit);
        return service;
    }
}
