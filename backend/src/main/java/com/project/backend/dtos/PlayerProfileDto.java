package com.project.backend.dtos;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PlayerProfileDto {

    @Pattern(regexp = "^[a-z]{2,3}(?:-[A-Z]{2})?$")
    private String language;

    @Size(max = 50)
    private String gameVersion;

    @Size(max = 100)
    private String playerLevel;

    @Size(max = 100)
    private String playStyle;

    @Size(max = 100)
    private String kingdom;

    private JsonNode additionalContext;
}
