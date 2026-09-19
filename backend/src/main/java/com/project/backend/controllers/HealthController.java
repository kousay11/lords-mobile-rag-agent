package com.project.backend.controllers;

import com.fasterxml.jackson.databind.JsonNode;
import com.project.backend.clients.AgentClient;
import com.project.backend.clients.RagClient;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/health")
@RequiredArgsConstructor
public class HealthController {

    private final AgentClient agentClient;
    private final RagClient ragClient;

    @GetMapping
    public ResponseEntity<Map<String, Object>> health() {
        JsonNode agent = agentClient.health();
        JsonNode rag = ragClient.health();
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "ok");
        response.put("service", "lords-mobile-guide-backend");
        response.put("agent", isHealthy(agent) ? "online" : "offline");
        response.put("rag", isHealthy(rag) ? "online" : "offline");
        response.put("read_only", true);
        return ResponseEntity.ok(response);
    }

    private boolean isHealthy(JsonNode health) {
        return health != null && "ok".equals(health.path("status").asText());
    }
}
