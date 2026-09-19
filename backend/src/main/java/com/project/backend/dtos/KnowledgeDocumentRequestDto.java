package com.project.backend.dtos;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeDocumentRequestDto {

    @NotBlank
    @Size(max = 255)
    private String title;

    @NotBlank
    @Size(max = 500)
    private String source;

    @Size(max = 1000)
    private String url;

    @NotBlank
    @Pattern(regexp = "^(official|verified_community|community|reference)$")
    private String sourceType;

    @NotBlank
    @Pattern(regexp = "^[a-z]{2,3}(?:-[A-Z]{2})?$")
    private String language;

    @NotBlank
    @Size(max = 50)
    private String gameVersion;

    @Min(1)
    @Max(5)
    private short reliability;

    @NotEmpty
    private List<String> topics;

    @NotBlank
    @Size(max = 20_971_520)
    private String content;

    private Instant publishedAt;
}
