package com.project.backend.clients;

import com.fasterxml.jackson.databind.JsonNode;
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

    public RagClient(
            RestClient.Builder builder,
            @Value("${app.ai.rag-base-url}") String baseUrl,
            @Value("${app.ai.connect-timeout-ms}") int connectTimeoutMs,
            @Value("${app.ai.read-timeout-ms}") int readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        this.client = builder.clone().baseUrl(baseUrl).requestFactory(factory).build();
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

    public void deleteDocument(String source) {
        try {
            client.delete()
                    .uri(uriBuilder -> uriBuilder.path("/documents/{source}").build(source))
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientResponseException ex) {
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
            return client.post().uri(path).body(body).retrieve().body(JsonNode.class);
        } catch (RestClientResponseException ex) {
            throw downstreamFailure(ex);
        } catch (ResourceAccessException ex) {
            throw timeout();
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
