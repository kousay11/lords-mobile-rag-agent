package com.project.backend.clients;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import com.project.backend.exceptions.DownstreamServiceException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.util.List;
import java.util.Map;

@Component
public class AgentClient {

    private static final Logger log = LoggerFactory.getLogger(AgentClient.class);

    private final RestClient client;

    public AgentClient(
            RestClient.Builder builder,
            @Value("${app.ai.agent-base-url}") String baseUrl,
            @Value("${app.ai.connect-timeout-ms}") int connectTimeoutMs,
            @Value("${app.ai.read-timeout-ms}") int readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        this.client = builder.clone().baseUrl(baseUrl).requestFactory(factory).build();
    }

    public AgentChatResponse chat(AgentChatRequest request) {
        try {
            AgentChatResponse response = client.post()
                    .uri("/chat")
                    .body(request)
                    .retrieve()
                    .body(AgentChatResponse.class);
            if (response == null) {
                throw new DownstreamServiceException(HttpStatus.BAD_GATEWAY, "Agent returned an empty response");
            }
            return response;
        } catch (RestClientResponseException ex) {
            log.warn("Lords Mobile agent rejected chat request (status {}): {}",
                    ex.getStatusCode().value(), truncatedBody(ex));
            throw new DownstreamServiceException(
                    HttpStatus.BAD_GATEWAY,
                    "Lords Mobile agent rejected the request (status " + ex.getStatusCode().value() + ")");
        } catch (ResourceAccessException ex) {
            throw new DownstreamServiceException(HttpStatus.GATEWAY_TIMEOUT, "Lords Mobile agent timed out");
        }
    }

    public JsonNode health() {
        try {
            return client.get().uri("/health").retrieve().body(JsonNode.class);
        } catch (Exception ex) {
            return null;
        }
    }

    private static String truncatedBody(RestClientResponseException ex) {
        try {
            String body = ex.getResponseBodyAsString();
            if (body == null) {
                return "<empty>";
            }
            return body.length() > 2000 ? body.substring(0, 2000) + "…" : body;
        } catch (Exception ignored) {
            return "<unreadable>";
        }
    }

    public void deleteThread(String threadId) {
        try {
            client.delete().uri("/threads/{threadId}", threadId).retrieve().toBodilessEntity();
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().value() != 404) {
                throw new DownstreamServiceException(HttpStatus.BAD_GATEWAY, "Unable to delete agent thread");
            }
        } catch (ResourceAccessException ex) {
            throw new DownstreamServiceException(HttpStatus.GATEWAY_TIMEOUT, "Lords Mobile agent timed out");
        }
    }

    public record AgentChatRequest(
            String message,
            @JsonProperty("thread_id") String threadId,
            @JsonProperty("user_id") String userId,
            String language,
            @JsonProperty("player_context") Map<String, Object> playerContext,
            @JsonProperty("search_type") String searchType,
            @JsonProperty("top_k") int topK) {
    }

    public record AgentChatResponse(
            @JsonProperty("thread_id") String threadId,
            String response,
            String model,
            String provider,
            String intent,
            String language,
            JsonNode sources,
            double confidence,
            @JsonProperty("needs_clarification") boolean needsClarification,
            @JsonProperty("search_type") String searchType,
            @JsonProperty("rewritten_queries") List<String> rewrittenQueries,
            @JsonProperty("generation_mode") String generationMode,
            @JsonProperty("read_only") boolean readOnly) {
    }
}
