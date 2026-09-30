package com.project.backend.controllers;

import com.fasterxml.jackson.databind.JsonNode;
import com.project.backend.dtos.KnowledgeDocumentDto;
import com.project.backend.dtos.KnowledgeDocumentRequestDto;
import com.project.backend.services.implementations.KnowledgeService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

import java.net.URI;
import java.time.Instant;
import java.util.Arrays;
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

    @PostMapping(value = "/documents/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<KnowledgeDocumentDto> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam("title") String title,
            @RequestParam("source") String source,
            @RequestParam(value = "url", required = false) String url,
            @RequestParam("sourceType") String sourceType,
            @RequestParam("language") String language,
            @RequestParam("gameVersion") String gameVersion,
            @RequestParam("reliability") short reliability,
            @RequestParam("topics") String topics) {
        List<String> topicList = Arrays.stream(topics.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
        validateUploadMetadata(title, source, sourceType, language, gameVersion, reliability, topicList);
        KnowledgeDocumentDto created = service.createFromFile(file, title.trim(), source.trim(),
                url == null || url.isBlank() ? null : url.trim(), sourceType, language, gameVersion.trim(),
                reliability, topicList, null);
        return ResponseEntity.created(URI.create("/api/admin/knowledge/documents/" + created.getId()))
                .body(created);
    }

    private void validateUploadMetadata(String title, String source, String sourceType, String language,
            String gameVersion, short reliability, List<String> topics) {
        if (title == null || title.isBlank() || title.trim().length() > 255
                || source == null || source.isBlank() || source.trim().length() > 500
                || gameVersion == null || gameVersion.isBlank() || gameVersion.trim().length() > 50
                || !sourceType.matches("^(official|verified_community|community|reference)$")
                || !language.matches("^[a-z]{2,3}(?:-[A-Z]{2})?$")
                || reliability < 1 || reliability > 5
                || topics.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid document metadata");
        }
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
