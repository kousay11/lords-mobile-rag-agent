package com.project.backend.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.project.backend.dtos.PlayerProfileDto;
import jakarta.validation.Validation;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ProfilePreferencesTest {
    @Test
    void requiredPreferencesAreValidatedAndCompletionCannotBeForged() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        var forged = mapper.readValue("{\"setupCompleted\":true}", PlayerProfileDto.class);
        assertFalse(forged.isSetupCompleted());
        try (var factory = Validation.buildDefaultValidatorFactory()) {
            var validator = factory.getValidator();
            assertEquals(2, validator.validate(forged).size());
            var valid = PlayerProfileDto.builder().language("ar")
                    .responseLength("short").build();
            assertTrue(validator.validate(valid).isEmpty());
            valid.setLanguage("xx");
            valid.setResponseLength("unlimited");
            assertEquals(2, validator.validate(valid).size());
        }
    }
}
