package com.project.backend.dtos;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
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

    @NotBlank
    @Pattern(regexp = "^(fr|en|ar)$")
    private String language;

    @NotBlank
    @Pattern(regexp = "^(short|standard|detailed)$")
    private String responseLength;

    @JsonProperty(access = JsonProperty.Access.READ_ONLY)
    private boolean setupCompleted;

    @Size(max = 100)
    private String playerLevel;

    @Size(max = 100)
    private String playStyle;

    private JsonNode additionalContext;
}
