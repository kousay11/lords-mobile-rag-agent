package com.project.backend.services.implementations;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.project.backend.clients.RagClient;
import com.project.backend.dtos.KnowledgeDocumentDto;
import com.project.backend.dtos.KnowledgeDocumentRequestDto;
import com.project.backend.entities.KnowledgeDocument;
import com.project.backend.exceptions.ResourceNotFoundException;
import com.project.backend.repositories.KnowledgeDocumentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class KnowledgeService {

    private static final TypeReference<List<String>> STRING_LIST_TYPE = new TypeReference<>() {
    };

    private final KnowledgeDocumentRepository repository;
    private final RagClient ragClient;
    private final ObjectMapper objectMapper;

    @Transactional
    public KnowledgeDocumentDto create(KnowledgeDocumentRequestDto request) {
        String hash = sha256(request.getContent());
        if (repository.findByContentHash(hash).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "This document content already exists");
        }
        Instant now = Instant.now();
        KnowledgeDocument document = KnowledgeDocument.builder()
                .title(request.getTitle().trim())
                .source(request.getSource().trim())
                .url(blankToNull(request.getUrl()))
                .sourceType(request.getSourceType())
                .language(request.getLanguage())
                .gameVersion(request.getGameVersion())
                .reliability(request.getReliability())
                .status(KnowledgeDocument.Status.PENDING)
                .contentHash(hash)
                .content(request.getContent())
                .publishedAt(request.getPublishedAt())
                .collectedAt(now)
                .topics(objectMapper.valueToTree(request.getTopics()))
                .qdrantChunks(0)
                .build();
        return toDto(repository.save(document));
    }

    public KnowledgeDocumentDto index(UUID id) {
        KnowledgeDocument document = find(id);
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("document_id", document.getId().toString());
        metadata.put("title", document.getTitle());
        metadata.put("source", document.getSource());
        metadata.put("source_type", document.getSourceType());
        metadata.put("language", document.getLanguage());
        metadata.put("game_version", document.getGameVersion());
        metadata.put("reliability", document.getReliability());
        metadata.put("status", "active");
        metadata.put("collected_at", document.getCollectedAt().toString());
        metadata.put("topics", objectMapper.convertValue(document.getTopics(), STRING_LIST_TYPE));
        metadata.put("content_hash", document.getContentHash());
        if (document.getUrl() != null) {
            metadata.put("url", document.getUrl());
        }
        if (document.getPublishedAt() != null) {
            metadata.put("published_at", document.getPublishedAt().atZone(ZoneOffset.UTC).toLocalDate().toString());
        }

        try {
            JsonNode response = ragClient.ingestText(document.getContent(), metadata);
            document.setQdrantChunks(response == null ? 0 : response.path("ingested_chunks").asInt(0));
            document.setStatus(KnowledgeDocument.Status.ACTIVE);
            document.setLastError(null);
            return toDto(repository.save(document));
        } catch (RuntimeException ex) {
            document.setStatus(KnowledgeDocument.Status.NEEDS_REVIEW);
            document.setLastError(limit(ex.getMessage(), 2000));
            repository.save(document);
            throw ex;
        }
    }

    @Transactional(readOnly = true)
    public List<KnowledgeDocumentDto> list() {
        return repository.findAllByOrderByUpdatedAtDesc().stream().map(this::toDto).toList();
    }

    public JsonNode listIndexedDocuments() {
        return ragClient.listDocuments();
    }

    public void delete(UUID id) {
        KnowledgeDocument document = find(id);
        if (document.getStatus() == KnowledgeDocument.Status.ACTIVE) {
            ragClient.deleteDocument(document.getSource());
        }
        repository.delete(document);
    }

    private KnowledgeDocument find(UUID id) {
        return repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Knowledge document not found"));
    }

    private KnowledgeDocumentDto toDto(KnowledgeDocument document) {
        return KnowledgeDocumentDto.builder()
                .id(document.getId())
                .title(document.getTitle())
                .source(document.getSource())
                .url(document.getUrl())
                .sourceType(document.getSourceType())
                .language(document.getLanguage())
                .gameVersion(document.getGameVersion())
                .reliability(document.getReliability())
                .status(document.getStatus().name().toLowerCase())
                .contentHash(document.getContentHash())
                .topics(objectMapper.convertValue(document.getTopics(), STRING_LIST_TYPE))
                .publishedAt(document.getPublishedAt())
                .collectedAt(document.getCollectedAt())
                .qdrantChunks(document.getQdrantChunks())
                .lastError(document.getLastError())
                .createdAt(document.getCreatedAt())
                .updatedAt(document.getUpdatedAt())
                .build();
    }

    private String sha256(String content) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(content.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is unavailable", ex);
        }
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String limit(String value, int maxLength) {
        if (value == null || value.length() <= maxLength) {
            return value;
        }
        return value.substring(0, maxLength);
    }
}
