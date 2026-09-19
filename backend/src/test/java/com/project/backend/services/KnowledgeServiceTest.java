package com.project.backend.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.project.backend.clients.RagClient;
import com.project.backend.dtos.KnowledgeDocumentRequestDto;
import com.project.backend.entities.KnowledgeDocument;
import com.project.backend.repositories.KnowledgeDocumentRepository;
import com.project.backend.services.implementations.KnowledgeService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class KnowledgeServiceTest {

    @Mock private KnowledgeDocumentRepository repository;
    @Mock private RagClient ragClient;

    private KnowledgeService service;

    @BeforeEach
    void setUp() {
        service = new KnowledgeService(repository, ragClient, new ObjectMapper());
    }

    @Test
    void duplicateContentIsRejected() {
        when(repository.findByContentHash(anyString()))
                .thenReturn(Optional.of(KnowledgeDocument.builder().build()));

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.create(validRequest()));
        assertEquals(409, error.getStatusCode().value());
    }

    @Test
    void indexingStoresQdrantChunkCountAndActiveStatus() {
        KnowledgeDocument document = KnowledgeDocument.builder()
                .title("Guide test")
                .source("guide-test.md")
                .sourceType("official")
                .language("fr")
                .gameVersion("test")
                .reliability((short) 5)
                .status(KnowledgeDocument.Status.PENDING)
                .contentHash("0123456789abcdef0123456789abcdef")
                .content("Contenu documentaire suffisamment précis.")
                .collectedAt(java.time.Instant.now())
                .topics(JsonNodeFactory.instance.arrayNode().add("test"))
                .build();
        document.setId(UUID.randomUUID());
        when(repository.findById(document.getId())).thenReturn(Optional.of(document));
        when(repository.save(any(KnowledgeDocument.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(ragClient.ingestText(anyString(), anyMap()))
                .thenReturn(JsonNodeFactory.instance.objectNode().put("ingested_chunks", 3));

        var result = service.index(document.getId());

        assertEquals("active", result.getStatus());
        assertEquals(3, result.getQdrantChunks());
    }

    private KnowledgeDocumentRequestDto validRequest() {
        return KnowledgeDocumentRequestDto.builder()
                .title("Guide test")
                .source("guide-test.md")
                .sourceType("official")
                .language("fr")
                .gameVersion("test")
                .reliability((short) 5)
                .topics(List.of("test"))
                .content("Contenu documentaire suffisamment précis.")
                .build();
    }
}
