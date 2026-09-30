package com.project.backend.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.project.backend.clients.RagClient;
import com.project.backend.dtos.PlayerProfileDto;
import com.project.backend.services.implementations.ProfileVersionService;
import jakarta.validation.Validation;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ProfilePreferencesTest {
    @Test
    void requiredPreferencesAreValidatedAndCompletionCannotBeForged() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        var forged = mapper.readValue("{\"setupCompleted\":true}", PlayerProfileDto.class);
        assertFalse(forged.isSetupCompleted());
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            var validator = factory.getValidator();
            assertEquals(3, validator.validate(forged).size());
            var valid = PlayerProfileDto.builder().language("ar").versionMode("unknown")
                    .responseLength("short").build();
            assertTrue(validator.validate(valid).isEmpty());
            valid.setLanguage("xx");
            valid.setResponseLength("unlimited");
            valid.setVersionMode("automatic");
            assertEquals(3, validator.validate(valid).size());
        }
    }

    @Test
    void versionOptionsIncludeAllIndexedCorporaWithHonestLabels() throws Exception {
        RagClient rag = mock(RagClient.class);
        when(rag.listDocuments()).thenReturn(new ObjectMapper().readTree("""
            {"data":[
              {"game_version":"2.18","status":"deprecated","reliability":5},
              {"game_version":"2.18","status":"active","reliability":4},
              {"game_version":"2026-review","status":"active","reliability":5},
              {"game_version":"official-guide-2019-04-15","status":"active","reliability":4},
              {"game_version":"3.0","status":"needs_review","reliability":5},
              {"game_version":"4.0","status":"active","reliability":3}
            ]}
            """));
        var service = new ProfileVersionService(rag);
        assertEquals(List.of("2.18", "2026-review", "3.0", "4.0", "official-guide-2019-04-15"), service.supportedVersions());
        var options = service.versionOptions();
        assertEquals(2, options.get(0).documentCount());
        assertEquals("review", options.get(1).kind());
        assertEquals("Corpus 2026 — sources avec réserves", options.get(1).label());
        assertEquals(1, options.get(2).needsReviewCount());
        assertEquals("guide", options.get(4).kind());
    }
}
