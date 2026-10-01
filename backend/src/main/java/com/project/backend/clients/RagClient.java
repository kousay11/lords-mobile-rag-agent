package com.project.backend.clients;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.project.backend.exceptions.DownstreamServiceException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.util.Map;

@Component
public class RagClient {

    private final RestClient client;
    private final ObjectMapper objectMapper;

    public RagClient(
            RestClient.Builder builder,
            @Value("${app.ai.rag-base-url}") String baseUrl,
            @Value("${app.ai.connect-timeout-ms}") int connectTimeoutMs,
            @Value("${app.ai.read-timeout-ms}") int readTimeoutMs,
            ObjectMapper objectMapper) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        this.client = builder.clone().baseUrl(baseUrl).requestFactory(factory).build();
        this.objectMapper = objectMapper;
    }

    public JsonNode ingestText(String text, Map<String, Object> metadata) {
        return post("/ingest/text", Map.of("text", text, "metadata", metadata));
    }

    public JsonNode listDocuments() {
        try {
            return client.get().uri("/documents").retrieve().body(JsonNode.class);
        } catch (RestClientResponseException ex) {
            throw downstreamFailure(ex);
        } catch (ResourceAccessException ex) {
            throw timeout();
        }
    }

    public void deleteDocumentById(String documentId) {
        try {
            client.delete()
                    .uri(uriBuilder -> uriBuilder.path("/documents/{documentId}").build(documentId))
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode() == HttpStatus.NOT_FOUND) {
                return;
            }
            throw downstreamFailure(ex);
        } catch (ResourceAccessException ex) {
            throw timeout();
        }
    }

    public JsonNode health() {
        try {
            return client.get().uri("/health").retrieve().body(JsonNode.class);
        } catch (Exception ex) {
            return null;
        }
    }

    private JsonNode post(String path, Object body) {
        try {
            // Read as String first: immune to a wrong or missing response content type.
            String raw = client.post().uri(path).body(body).retrieve().body(String.class);
            if (raw == null || raw.isBlank()) {
                throw new DownstreamServiceException(HttpStatus.BAD_GATEWAY, "RAG service returned an empty body");
            }
            return objectMapper.readTree(raw);
        } catch (RestClientResponseException ex) {
            throw downstreamFailure(ex);
        } catch (ResourceAccessException ex) {
            throw timeout();
        } catch (DownstreamServiceException ex) {
            throw ex;
        } catch (Exception ex) {
            throw new DownstreamServiceException(HttpStatus.BAD_GATEWAY,
                    "RAG service returned an unreadable response");
        }
    }

    private DownstreamServiceException downstreamFailure(RestClientResponseException ex) {
        return new DownstreamServiceException(
                HttpStatus.BAD_GATEWAY,
                "RAG service rejected the request (status " + ex.getStatusCode().value() + ")");
    }

    private DownstreamServiceException timeout() {
        return new DownstreamServiceException(HttpStatus.GATEWAY_TIMEOUT, "RAG service timed out");
    }
}
