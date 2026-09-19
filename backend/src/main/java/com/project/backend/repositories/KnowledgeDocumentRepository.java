package com.project.backend.repositories;

import com.project.backend.entities.KnowledgeDocument;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface KnowledgeDocumentRepository extends JpaRepository<KnowledgeDocument, UUID> {
    List<KnowledgeDocument> findAllByOrderByUpdatedAtDesc();

    Optional<KnowledgeDocument> findByContentHash(String contentHash);
}
