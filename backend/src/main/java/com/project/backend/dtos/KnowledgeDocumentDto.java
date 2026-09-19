package com.project.backend.dtos;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeDocumentDto {
    private UUID id;
    private String title;
    private String source;
    private String url;
    private String sourceType;
    private String language;
    private String gameVersion;
    private short reliability;
    private String status;
    private String contentHash;
    private List<String> topics;
    private Instant publishedAt;
    private Instant collectedAt;
    private int qdrantChunks;
    private String lastError;
    private Instant createdAt;
    private Instant updatedAt;
}
