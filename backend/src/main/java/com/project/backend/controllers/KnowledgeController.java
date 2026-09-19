package com.project.backend.controllers;

import com.fasterxml.jackson.databind.JsonNode;
import com.project.backend.dtos.KnowledgeDocumentDto;
import com.project.backend.dtos.KnowledgeDocumentRequestDto;
import com.project.backend.services.implementations.KnowledgeService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/admin/knowledge")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN')")
public class KnowledgeController {

    private final KnowledgeService service;

    @GetMapping("/documents")
    public ResponseEntity<List<KnowledgeDocumentDto>> list() {
        return ResponseEntity.ok(service.list());
    }

    @GetMapping("/documents/indexed")
    public ResponseEntity<JsonNode> listIndexed() {
        return ResponseEntity.ok(service.listIndexedDocuments());
    }

    @PostMapping("/documents")
    public ResponseEntity<KnowledgeDocumentDto> create(
            @Valid @RequestBody KnowledgeDocumentRequestDto request) {
        KnowledgeDocumentDto created = service.create(request);
        return ResponseEntity.created(URI.create("/api/admin/knowledge/documents/" + created.getId()))
                .body(created);
    }

    @PostMapping("/documents/{id}/index")
    public ResponseEntity<KnowledgeDocumentDto> index(@PathVariable UUID id) {
        return ResponseEntity.ok(service.index(id));
    }

    @DeleteMapping("/documents/{id}")
    public ResponseEntity<Void> delete(@PathVariable UUID id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
