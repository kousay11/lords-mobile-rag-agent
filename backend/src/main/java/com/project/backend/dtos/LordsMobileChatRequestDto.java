package com.project.backend.dtos;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LordsMobileChatRequestDto {

    @NotBlank
    @Size(max = 8000)
    private String message;

    private UUID threadId;

    @Pattern(regexp = "^[a-z]{2,3}(?:-[A-Z]{2})?$")
    private String language;

    private Map<String, Object> playerContext;

    @Pattern(regexp = "^(hybrid|semantic|keyword)$")
    private String searchType;

    @Min(1)
    @Max(20)
    private Integer topK;
}
