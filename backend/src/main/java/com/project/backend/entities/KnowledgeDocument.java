package com.project.backend.entities;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "knowledge_documents")
public class KnowledgeDocument extends BaseEntity {

    public enum Status {
        PENDING,
        ACTIVE,
        DEPRECATED,
        NEEDS_REVIEW
    }

    @Column(nullable = false, length = 255)
    private String title;

    @Column(nullable = false, length = 500)
    private String source;

    @Column(length = 1000)
    private String url;

    @Column(name = "source_type", nullable = false, length = 50)
    private String sourceType;

    @Column(nullable = false, length = 16)
    private String language;

    @Column(nullable = false)
    private short reliability;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private Status status;

    @Column(name = "content_hash", nullable = false, unique = true, length = 128)
    private String contentHash;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(name = "published_at")
    private Instant publishedAt;

    @Column(name = "collected_at", nullable = false)
    private Instant collectedAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb", nullable = false)
    private JsonNode topics;

    @Column(name = "qdrant_chunks", nullable = false)
    private int qdrantChunks;

    @Column(name = "last_error", columnDefinition = "TEXT")
    private String lastError;
}
